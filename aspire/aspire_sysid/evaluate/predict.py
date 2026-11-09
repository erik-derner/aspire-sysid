"""Predictions and simulations of one candidate on one trajectory: the evaluation modes.

Algebraic output evaluation, one-step prediction, simulation;
initialization; input treatment between samples; integration; trajectories never joined;
numerical failures (failure limits, non-real or non-finite values, evaluation time limit).

Notation (0-based sample indices): a trajectory has ``N`` samples ``k = 0, …, N − 1`` at the
times ``t_k = k T_s``; ``n_init`` is the task's number of initialization samples; the scoring
interval ``I`` is :meth:`aspire_sysid.task.schema.Evaluation.scoring_indices`.

**Algebraic evaluation (static task).** ``ŷ[k] = f(u[k])`` for every sample.

**One-step prediction.** For every ``k ∈ I`` (``k ≥ 1``), the predictor starts
from the measured state at ``k − 1``:

- discrete-time: ``x̂[k] = g_d(x[k − 1], u[k − 1])``;
- continuous-time: ``x̂[k]`` is the result of integrating ``dx/dt = g_c(x, u)``
  over ``[t_{k−1}, t_k]`` from the measured ``x[k − 1]``, with the classical fourth-order
  Runge–Kutta method in ``substeps`` equal steps of ``T_s / substeps`` and the input held at
  ``u[k − 1]`` over the interval (zero-order hold, the only input treatment of schema version 1);
- NARX: ``ŷ[k] = f(y[k − 1], y_d[k − 1], …, u[k − 1])`` with every delayed value
  taken from the measured data.

The output is ``ŷ[k] = h(x̂[k], u[k])`` (the measurement equation), with the measured input at the same index
``k``: under zero-order hold the input at ``t_k`` is the recorded ``u[k]``, which the task
declares known at that instant. The predictor is reinitialized from measurements at every step.

**Simulation.** One initial state per trajectory: the measured state at the
last initialization sample ``k_0 = n_init − 1``. The state is propagated with the recorded
inputs, ``u[k]`` held over ``[t_k, t_{k+1})``, by the state equation or by the Runge–Kutta integration
of (2), without replacement by later measurements; ``ŷ[k] = h(x̂[k], u[k])`` for ``k > k_0``,
the measurement equation with the input at the same index. A NARX model starts from the measured outputs ``y[0], …, y[n_init − 1]`` and then
uses its own simulated outputs in every delayed output variable; delayed inputs are always read
from the data. Every trajectory is simulated on its own; a trajectory is never joined to another.

**Numerical failure.** A state or output outside its failure limit, a non-real or
non-finite state or output, an exception of the numerical evaluation, or the expiry of the
evaluation time limit ends the computation on that trajectory. The failure records the data
group, the trajectory, the sample index ``k`` of the first value that could not be produced, the
time ``t_k``, the reason and the variable. The predictions of the samples before ``k`` are kept
for the prefix diagnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from ..task.schema import TaskSpec
from .compiled import CompiledModel
from .data import Trajectory

FAILURE_REASONS = ("failure_limit", "non_finite", "time_limit", "evaluation_error")
"""Reasons of a numerical failure: a value outside its declared failure limit; a
non-real or non-finite value; the evaluation time limit; an exception raised by the numerical
evaluation of an expression."""


class Deadline:
    """The evaluation time limit, measured with a monotonic clock.

    One deadline covers the computation of the predictions of one candidate on one data group
    (training, validation or test data). ``None`` means no limit.
    """

    def __init__(self, seconds: float | None):
        self.seconds = seconds
        self._end = None if seconds is None else time.monotonic() + float(seconds)

    def expired(self) -> bool:
        """True when the time limit has been exceeded."""
        return self._end is not None and time.monotonic() > self._end


@dataclass(frozen=True)
class Failure:
    """A numerical failure on one trajectory.

    ``index`` is the 0-based sample index of the first value that could not be produced;
    ``time_s`` is ``index · T_s`` for a dynamic task and ``None`` for a static dataset;
    ``reason`` is one of :data:`FAILURE_REASONS`; ``variable`` and ``value`` name the offending
    state or output and its value, where applicable.
    """

    group: str
    trajectory: str
    index: int
    time_s: float | None
    reason: str
    variable: str | None
    value: float | None
    detail: str

    def to_dict(self) -> dict:
        """Plain data for the JSON report."""
        return {
            "group": self.group,
            "trajectory": self.trajectory,
            "index": self.index,
            "time_s": self.time_s,
            "reason": self.reason,
            "variable": self.variable,
            "value": self.value,
            "detail": self.detail,
        }


@dataclass
class TrajectoryPrediction:
    """The predictions of one candidate on one trajectory.

    ``predicted`` has one entry per sample; entries that were not computed (initialization
    samples, samples at or after a failure) are NaN. ``scoring`` is the scoring interval ``I``.
    """

    trajectory: Trajectory
    mode: str
    output: str
    predicted: np.ndarray
    scoring: range
    failure: Failure | None

    @property
    def measured(self) -> np.ndarray:
        """The measured output ``y`` of the trajectory."""
        return self.trajectory.columns[self.output]

    @property
    def completed(self) -> list[int]:
        """Indices of ``I`` whose prediction was computed (all of ``I`` without a failure)."""
        stop = self.failure.index if self.failure is not None else None
        return [k for k in self.scoring if stop is None or k < stop]


def _limits(task: TaskSpec) -> dict[str, tuple[float, float]]:
    return {fl.variable: (fl.lower, fl.upper) for fl in task.evaluation.failure_limits}


def _first_bad(values: dict[str, np.ndarray], indices: np.ndarray, limits: dict[str, tuple[float, float]]):
    """First position (in ``indices`` order) where a value is non-finite or outside its limit."""
    best = None
    for var, arr in values.items():
        a = arr[indices]
        bad = ~np.isfinite(a)
        reason = np.where(bad, 1, 0)
        if var in limits:
            lo, hi = limits[var]
            with np.errstate(invalid="ignore"):
                out = np.isfinite(a) & ((a < lo) | (a > hi))
            reason = np.where(out, 2, reason)
        hits = np.nonzero(reason)[0]
        if hits.size and (best is None or hits[0] < best[0]):
            best = (int(hits[0]), var, float(a[hits[0]]), "non_finite" if reason[hits[0]] == 1 else "failure_limit")
    return best


def _failure(task, traj, k, reason, var, value, limits) -> Failure:
    ts = task.dynamics.sampling_period if task.dynamics is not None else None
    if reason == "failure_limit":
        lo, hi = limits[var]
        detail = f"{var} = {value!r} outside the failure limit [{lo!r}, {hi!r}] at sample {k}"
    elif reason == "non_finite":
        detail = f"{var} is not real and finite ({value!r}) at sample {k}"
    elif reason == "time_limit":
        detail = f"the evaluation time limit of {task.evaluation.time_limit_s!r} s was exceeded before sample {k}"
    else:
        detail = f"the numerical evaluation raised an exception at sample {k}: {value}"
        value = None
    return Failure(
        group=traj.group,
        trajectory=traj.trajectory,
        index=int(k),
        time_s=None if ts is None else float(k * ts),
        reason=reason,
        variable=var,
        value=None if value is None else float(value),
        detail=detail,
    )


def _rk4(deriv, x: np.ndarray, u: tuple, h: float) -> np.ndarray:
    k1 = deriv(x, u)
    k2 = deriv(x + 0.5 * h * k1, u)
    k3 = deriv(x + 0.5 * h * k2, u)
    k4 = deriv(x + h * k3, u)
    return x + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def _scalar_vector(values) -> np.ndarray:
    try:
        return np.array([float(v) for v in values], dtype=float)
    except (TypeError, ValueError):  # a complex result: non-real
        return np.full(len(values), np.nan)


def predict_trajectory(model: CompiledModel, traj: Trajectory, deadline: Deadline | None = None) -> TrajectoryPrediction:
    """Predictions of ``model`` on one trajectory in the task's evaluation mode.

    Static tasks use algebraic evaluation; dynamic tasks use one-step prediction
    or simulation as the task declares. Numerical failures end the computation
    and are recorded in the result; this function does not raise for them.
    """
    task = model.task
    deadline = deadline or Deadline(None)
    mode = task.evaluation.mode
    if task.formulation == "static":
        return _algebraic(model, traj, deadline)
    if mode == "one_step":
        return _one_step(model, traj, deadline)
    if mode == "simulation":
        return _simulate(model, traj, deadline)
    raise ValueError(f"evaluation mode {mode!r} is not defined for the formulation {task.formulation!r}")


def _result(model, traj, predicted, scoring, failure) -> TrajectoryPrediction:
    if failure is not None:
        predicted = predicted.copy()
        predicted[failure.index :] = np.nan
    return TrajectoryPrediction(traj, model.task.evaluation.mode, model.task.output, predicted, scoring, failure)


def _algebraic(model: CompiledModel, traj: Trajectory, deadline: Deadline) -> TrajectoryPrediction:
    task = model.task
    n = traj.n
    scoring = task.evaluation.scoring_indices(n)
    idx = np.asarray(list(scoring), dtype=int)
    limits = _limits(task)
    pred = np.full(n, np.nan)
    try:
        out = model.evaluate({a: traj.columns[a] for a in model.args}, n)
    except Exception as exc:  # noqa: BLE001 - any evaluation error is a recorded failure
        f = _failure(task, traj, idx[0] if idx.size else 0, "evaluation_error", None, f"{type(exc).__name__}: {exc}", limits)
        return _result(model, traj, pred, scoring, f)
    pred = out[task.output]
    failure = None
    bad = _first_bad({task.output: pred}, idx, limits)
    if bad is not None:
        pos, var, val, reason = bad
        failure = _failure(task, traj, int(idx[pos]), reason, var, val, limits)
    if deadline.expired():
        k = int(idx[0]) if idx.size else 0
        failure = _failure(task, traj, k, "time_limit", None, None, limits)
    return _result(model, traj, pred, scoring, failure)


def _narx_arguments(model: CompiledModel, traj: Trajectory, j: np.ndarray, own: np.ndarray | None) -> dict[str, np.ndarray]:
    """Arguments of the NARX regression at the indices ``j``.

    ``own`` is the simulated output (simulation) or ``None`` (measured outputs, one-step).
    """
    task = model.task
    y_name = task.output
    y = traj.columns[y_name] if own is None else own
    vals: dict[str, np.ndarray] = {y_name: y[j]}
    for d in task.dynamics.delays:
        src = y if d.variable == y_name else traj.columns[d.variable]
        vals[d.name] = src[j - d.lag]
    for u in task.inputs:
        vals[u] = traj.columns[u][j]
    return vals


def _one_step(model: CompiledModel, traj: Trajectory, deadline: Deadline) -> TrajectoryPrediction:
    task = model.task
    dyn = task.dynamics
    n = traj.n
    scoring = task.evaluation.scoring_indices(n)
    k = np.asarray([i for i in scoring if i >= 1], dtype=int)
    if len(k) != len(scoring):
        raise ValueError("one-step prediction needs every scored sample to have a predecessor (initialization ≥ 1)")
    limits = _limits(task)
    pred = np.full(n, np.nan)
    if k.size == 0:
        return _result(model, traj, pred, scoring, None)
    m = k.size
    j = k - 1
    states = {}
    try:
        with np.errstate(all="ignore"):
            if task.formulation == "narx":
                out = model.evaluate(_narx_arguments(model, traj, j, None), m)
                states = {task.output: out[model.keys[0]]}
            elif task.formulation == "discrete":
                args = {a: traj.columns[a][j] for a in model.args}
                out = model.evaluate(args, m)
                states = {s: out[f"{s}_next"] for s in task.states}
            else:
                x = np.stack([traj.columns[s][j] for s in task.states])
                u = [traj.columns[a][j] for a in task.inputs]

                def deriv(xv, uv):
                    vals = dict(zip(task.states, xv))
                    vals.update(zip(task.inputs, uv))
                    d = model.evaluate(vals, m)
                    return np.stack([d[f"d{s}"] for s in task.states])

                h = dyn.sampling_period / dyn.substeps
                for _ in range(dyn.substeps):
                    x = _rk4(deriv, x, u, h)
                states = {s: x[i] for i, s in enumerate(task.states)}
            meas = {s: states[s] for s in task.states}
            meas.update({a: traj.columns[a][k] for a in task.inputs})
            y_hat = model.measure(meas, m)
    except Exception as exc:  # noqa: BLE001
        f = _failure(task, traj, int(k[0]), "evaluation_error", None, f"{type(exc).__name__}: {exc}", limits)
        return _result(model, traj, pred, scoring, f)
    checked = dict(states)
    checked[task.output] = y_hat
    full = {}
    for var, arr in checked.items():
        a = np.full(n, np.nan)
        a[k] = arr
        full[var] = a
    pred[k] = y_hat
    failure = None
    bad = _first_bad(full, k, limits)
    if bad is not None:
        pos, var, val, reason = bad
        failure = _failure(task, traj, int(k[pos]), reason, var, val, limits)
    if deadline.expired():
        failure = _failure(task, traj, int(k[0]), "time_limit", None, None, limits)
    return _result(model, traj, pred, scoring, failure)


def _simulate(model: CompiledModel, traj: Trajectory, deadline: Deadline) -> TrajectoryPrediction:
    task = model.task
    dyn = task.dynamics
    n = traj.n
    scoring = task.evaluation.scoring_indices(n)
    limits = _limits(task)
    k0 = task.evaluation.initialization - 1
    pred = np.full(n, np.nan)
    if k0 < 0 or k0 >= n - 1:
        return _result(model, traj, pred, scoring, None)
    nx = len(task.states)
    xs = np.full((n, nx), np.nan)
    failure = None
    f = model.f
    inputs = np.stack([traj.columns[a] for a in task.inputs], axis=1) if task.inputs else np.zeros((n, 0))
    last = n - 1  # last index with a computed state
    current = k0 + 1  # index of the sample being computed
    try:
        if task.formulation == "narx":
            y_name = task.output
            ysim = np.full(n, np.nan)
            ysim[: k0 + 1] = traj.columns[y_name][: k0 + 1]
            xs[: k0 + 1, 0] = ysim[: k0 + 1]
            for k in range(k0 + 1, n):
                current = k
                if deadline.expired():
                    failure = _failure(task, traj, k, "time_limit", None, None, limits)
                    break
                args = _narx_arguments(model, traj, np.asarray([k - 1]), ysim)
                with np.errstate(all="ignore"):
                    val = _scalar_vector(f(*[args[a][0] for a in model.args]))[0]
                ysim[k] = val
                xs[k, 0] = val
                bad = _first_bad({y_name: np.asarray([val])}, np.asarray([0]), limits)
                if bad is not None:
                    failure = _failure(task, traj, k, bad[3], y_name, val, limits)
                    break
        else:
            x = np.asarray([traj.columns[s][k0] for s in task.states], dtype=float)
            xs[k0] = x
            if task.formulation == "discrete":

                def step(xv, uv):
                    with np.errstate(all="ignore"):
                        return _scalar_vector(f(*xv, *uv))

            else:
                h = dyn.sampling_period / dyn.substeps

                def deriv(xv, uv):
                    with np.errstate(all="ignore"):
                        return _scalar_vector(f(*xv, *uv))

                def step(xv, uv):
                    for _ in range(dyn.substeps):
                        xv = _rk4(deriv, xv, uv, h)
                    return xv

            for k in range(k0, n - 1):
                current = k + 1
                if deadline.expired():
                    failure = _failure(task, traj, k + 1, "time_limit", None, None, limits)
                    break
                with np.errstate(all="ignore"):
                    x = step(x, tuple(inputs[k]))
                xs[k + 1] = x
                bad = _first_bad({s: np.asarray([x[i]]) for i, s in enumerate(task.states)}, np.asarray([0]), limits)
                if bad is not None:
                    failure = _failure(task, traj, k + 1, bad[3], bad[1], bad[2], limits)
                    break
    except Exception as exc:  # noqa: BLE001
        at = current  # the sample whose computation raised; earlier samples are kept
        failure = _failure(task, traj, at, "evaluation_error", None, f"{type(exc).__name__}: {exc}", limits)
    if failure is not None:
        last = failure.index - 1
    idx = np.arange(k0 + 1, last + 1)
    if idx.size:
        meas = {s: xs[idx, i] for i, s in enumerate(task.states)}
        meas.update({a: traj.columns[a][idx] for a in task.inputs})
        try:
            y_hat = model.measure(meas, idx.size)
        except Exception as exc:  # noqa: BLE001
            failure = _failure(task, traj, int(idx[0]), "evaluation_error", None, f"{type(exc).__name__}: {exc}", limits)
            return _result(model, traj, pred, scoring, failure)
        pred[idx] = y_hat
        full = np.full(n, np.nan)
        full[idx] = y_hat
        bad = _first_bad({task.output: full}, idx, limits)
        if bad is not None:
            pos, var, val, reason = bad
            failure = _failure(task, traj, int(idx[pos]), reason, var, val, limits)
    return _result(model, traj, pred, scoring, failure)
