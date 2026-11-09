"""Plots of measured and modeled outputs and residuals, with self-contained captions.

Each candidate report includes the measured and modeled outputs, the residuals and
any relevant trajectory plots, with units and dataset identifiers; captions state the evaluation
mode, the initialization, the interval used to compute errors, and any failed or excluded
samples; plots retain the candidate labels.

One figure per candidate and data group, with one pair of axes per trajectory: the measured and
the modeled output against time (dynamic task) or against the input (static task with one input;
sample index otherwise), and below it the residual ``ŷ − y``. Samples outside the scoring interval
and samples at or after a numerical failure carry no modeled value. Matplotlib runs with the
non-interactive Agg backend.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..task.schema import TaskSpec
from .pool import CandidateEvaluation, GroupEvaluation

GROUP_NAMES = {"train": "training data", "val": "validation data", "test": "test data (sealed)"}
"""Names of the data groups in captions."""


def _unit(task: TaskSpec, name: str) -> str:
    try:
        return task.column(name).unit
    except KeyError:
        return "-"


def mode_text(task: TaskSpec) -> str:
    """The evaluation mode and its settings in words, for captions and reports."""
    e = task.evaluation
    if task.formulation == "static":
        return "algebraic evaluation of the output expression at the measured inputs"
    dyn = task.dynamics
    if task.formulation == "continuous":
        integ = (
            f"classical fourth-order Runge-Kutta integration with {dyn.substeps} step(s) per sampling period "
            f"T_s = {dyn.sampling_period:g} s and zero-order hold of the input"
        )
    else:
        integ = f"the state-update equation at the sampling period T_s = {dyn.sampling_period:g} s"
    k0 = e.initialization - 1
    if e.mode == "simulation":
        start = (
            f"initialized once per trajectory from the measured output history of samples 0 to {k0}"
            if task.formulation == "narx"
            else f"initialized once per trajectory from the measured state at sample {k0}"
        )
        return f"simulation ({start}; {integ}; the model output is h(x[k], u[k]))"
    return f"one-step prediction (reinitialized from the measured state at every step; {integ}; the model output is h(x[k], u[k]))"


def plot_caption(task: TaskSpec, cand: CandidateEvaluation, group: GroupEvaluation) -> str:
    """The self-contained caption of the plot of one candidate on one data group."""
    y = task.output
    unit = _unit(task, y)
    e = task.evaluation
    parts = [
        f"Candidate {cand.label}, {GROUP_NAMES.get(group.group, group.group)}, trajectories "
        f"{', '.join(t.trajectory for t in group.trajectories)}.",
        f"Upper axes: measured output {y} ({unit}) and model output of {cand.label}; lower axes: residual "
        f"(model output minus measured output, {unit}).",
        f"Evaluation mode: {mode_text(task)}.",
    ]
    if e.initialization > 0:
        parts.append(
            f"Initialization: the first {e.initialization} sample(s) of each trajectory initialize the model and are excluded from the errors."
        )
    parts.append(
        "Errors are computed on the samples "
        + "; ".join(f"{t.trajectory}: {t.scoring[0]} to {t.scoring[1] - 1}" for t in group.trajectories)
        + " (0-based sample indices)."
    )
    fails = [t for t in group.trajectories if t.failure is not None]
    if fails:
        parts.append(
            "Failed samples (no model output shown): "
            + "; ".join(f"{t.trajectory} from sample {t.failure.index} ({t.failure.detail})" for t in fails)
            + "; the error on the samples before a failure is a diagnostic only."
        )
    else:
        parts.append("No numerical failure occurred.")
    if cand.excluded_by_requirements:
        parts.append(f"The candidate is excluded from ranking by the demonstrated violation of {', '.join(cand.exclusions)}.")
    return " ".join(parts)


def plot_group(task: TaskSpec, cand: CandidateEvaluation, group: GroupEvaluation, path: Path) -> Path:
    """Write the figure of one candidate on one data group to ``path`` (PNG)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    trs = [t for t in group.trajectories if t.prediction is not None]
    n = max(1, len(trs))
    ncol = min(4, n)
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(2 * nrow, ncol, figsize=(4.2 * ncol, 3.6 * nrow), squeeze=False, gridspec_kw={"height_ratios": [2, 1] * nrow})
    y = task.output
    unit = _unit(task, y)
    static_x = task.inputs[0] if task.formulation == "static" and len(task.inputs) == 1 else None
    for i, t in enumerate(trs):
        r, c = 2 * (i // ncol), i % ncol
        ax, axr = axes[r][c], axes[r + 1][c]
        pred = t.prediction
        meas = pred.measured
        yh = pred.predicted
        if task.dynamics is not None:
            x = np.arange(len(meas)) * task.dynamics.sampling_period
            xlabel = "time t (s)"
            ax.plot(x, meas, color="0.2", lw=1.0, label="measured")
            ax.plot(x, yh, color="tab:blue", lw=1.0, label=f"{cand.label}")
        else:
            if static_x is not None:
                x = t.prediction.trajectory.columns[static_x]
                xlabel = f"{static_x} ({_unit(task, static_x)})"
            else:
                x = np.arange(len(meas))
                xlabel = "sample index"
            order = np.argsort(x, kind="stable")
            ax.plot(x[order], meas[order], ".", color="0.2", ms=3, label="measured")
            ax.plot(x[order], yh[order], "-", color="tab:blue", lw=1.0, label=f"{cand.label}")
        axr.plot(x, yh - meas, ".", color="tab:red", ms=2)
        axr.axhline(0.0, color="0.5", lw=0.5)
        if t.failure is not None:
            xf = t.failure.index * task.dynamics.sampling_period if task.dynamics is not None else x[min(t.failure.index, len(x) - 1)]
            ax.axvline(xf, color="tab:red", ls="--", lw=0.8, label="failure")
        ax.set_title(f"{cand.label} - {group.group} {t.trajectory}", fontsize=9)
        ax.set_ylabel(f"{y} ({unit})", fontsize=8)
        axr.set_ylabel(f"residual ({unit})", fontsize=8)
        axr.set_xlabel(xlabel, fontsize=8)
        ax.tick_params(labelsize=7)
        axr.tick_params(labelsize=7)
        if i == 0:
            ax.legend(fontsize=7)
    for j in range(len(trs), nrow * ncol):
        r, c = 2 * (j // ncol), j % ncol
        axes[r][c].axis("off")
        axes[r + 1][c].axis("off")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
