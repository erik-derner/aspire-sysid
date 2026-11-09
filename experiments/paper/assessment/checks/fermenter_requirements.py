"""Numerical check of the requirements R1 to R5 of the task fermenter-pressure on the recommended
model of every run of an experiment.

Plain code, no language model. The requirements are stated in natural language (``tasks/fermenter-pressure/task.yaml``); the harness does not verify them. This script evaluates
the delivered expression ``dp = f(p, valve, flow)`` with the delivered parameter values on a grid
and prints, per requirement, the mark that follows from the rule below, with the numbers behind
it. The marks are evidence for the assessment in ``experiments/paper/assessment/``; the assessor
confirms or corrects them.

Grid (ranges that contain the training data; valve in % closed, flow in l/min, p in bar):
valve 0 to 100 in steps of 2.5, flow 0 to 31 in steps of 1, p 0.9 to 2.3 in steps of 0.05.
R1, R2 and R5 are checked for p from 1.0 to 2.3 bar, that is, at or above atmospheric pressure:
below it the air flows into the tank through the outlet valve, and closing the valve then lowers
dp in a physically correct model, which R2 does not address. R3 and R4 use the whole pressure grid.
"Open valve" is taken as valve <= 90 %; "air is supplied" as flow >= 1 l/min. The training data
cover valve from 10.3 to 92.4 %, flow from 0.10 to 30.8 l/min and p from 0.99 to 2.19 bar, so that
zero flow (R3, R4) and a fully closed valve (R5) lie outside the training data.

Rule (fixed before the runs of the experiment were read):

- R1 (dp does not decrease when flow increases): ``yes`` when no step of the flow on the grid
  lowers dp by more than 1e-9 bar/s; ``partly`` when at most 5 % of the steps do; else ``no``.
- R2 (dp does not decrease when the valve closes further): the same along the valve.
- R3 (with zero flow and an open valve, atmospheric pressure, about 1 bar, is the equilibrium):
  for every open valve position, the root p* of f(p, valve, 0) in [0.9, 2.3] bar is located (sign
  change on the grid, refined by bisection). ``yes`` when a root with |p* - 1| <= 0.05 bar exists
  at every open position; ``partly`` when at some positions; else ``no``.
- R4 (with zero flow and an open valve, the pressure tends toward atmospheric pressure): at every
  open position, dp < 0 for all grid pressures above 1.05 bar and dp > 0 for all below 0.95 bar.
  ``yes`` when this holds at every open position; ``partly`` when at some; else ``no``.
- R5 (with a fully closed valve the pressure cannot decrease when air is supplied): at
  valve = 100 %, dp >= -1e-9 bar/s for all grid pressures and all flows >= 1 l/min. ``yes`` when
  this holds at every such point; ``partly`` when at 95 % of them or more; else ``no``.

Usage, from the repository root, with the interpreter of the harness::

    .venv/Scripts/python.exe experiments/paper/assessment/checks/fermenter_requirements.py experiments/paper-fermenter-pressure

The result is written beside this script as ``<experiment>-requirements.json`` (or into the folder
given as a second argument).
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
TOL = 1e-9
VALVE = np.arange(0.0, 100.0 + 1e-9, 2.5)
FLOW = np.arange(0.0, 31.0 + 1e-9, 1.0)
P = np.arange(0.9, 2.3 + 1e-9, 0.05)
P_ABOVE = P[P >= 1.0 - 1e-9]  # at or above atmospheric pressure (R1, R2, R5)


def compiled_model(task, models_dir: pathlib.Path, label: str):
    from aspire_sysid.evaluate.compiled import CompiledModel
    from aspire_sysid.evaluate.pool import check_report

    report = check_report(task, models_dir)
    return CompiledModel(task, report.candidates[label].candidate)


def dp(model, p, valve, flow) -> np.ndarray:
    p, valve, flow = np.broadcast_arrays(np.asarray(p, float), np.asarray(valve, float), np.asarray(flow, float))
    shape = p.shape
    out = model.evaluate({"p": p.ravel(), "valve": valve.ravel(), "flow": flow.ravel()}, p.size)["dp"]
    return np.asarray(out, float).reshape(shape)


def mark_share(bad: int, total: int, partly_limit: float = 0.05) -> str:
    if bad == 0:
        return "yes"
    return "partly" if bad / total <= partly_limit else "no"


def root(model, valve: float) -> float | None:
    """A root of f(p, valve, 0) in [0.9, 2.3] bar: first sign change on the grid, refined by bisection."""
    values = dp(model, P, valve, 0.0)
    for i in range(len(P) - 1):
        a, b = values[i], values[i + 1]
        if a == 0.0:
            return float(P[i])
        if a * b < 0:
            lo, hi, flo = float(P[i]), float(P[i + 1]), a
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                fm = float(dp(model, mid, valve, 0.0))
                if fm == 0.0:
                    return mid
                if flo * fm < 0:
                    hi = mid
                else:
                    lo, flo = mid, fm
            return 0.5 * (lo + hi)
    return float(P[-1]) if values[-1] == 0.0 else None


def check(model) -> dict:
    pall, vall, fall = np.meshgrid(P, VALVE, FLOW, indexing="ij")
    out = {"finite": bool(np.isfinite(dp(model, pall, vall, fall)).all())}
    pp, vv, ff = np.meshgrid(P_ABOVE, VALVE, FLOW, indexing="ij")
    f = dp(model, pp, vv, ff)
    d_flow = np.diff(f, axis=2)
    bad = int((d_flow < -TOL).sum())
    inside = (vv[:, :, 1:] >= 10) & (vv[:, :, 1:] <= 92.5) & (ff[:, :, :-1] >= 1)
    out["R1"] = {"mark": mark_share(bad, d_flow.size), "decreasing_steps": bad, "steps": int(d_flow.size),
                 "decreasing_steps_inside_training_ranges": int(((d_flow < -TOL) & inside).sum()),
                 "largest_decrease_bar_per_s": float(-d_flow.min()) if bad else 0.0}
    d_valve = np.diff(f, axis=1)
    bad = int((d_valve < -TOL).sum())
    inside = (vv[:, :-1, :] >= 10) & (vv[:, 1:, :] <= 92.5) & (ff[:, 1:, :] >= 1)
    out["R2"] = {"mark": mark_share(bad, d_valve.size), "decreasing_steps": bad, "steps": int(d_valve.size),
                 "decreasing_steps_inside_training_ranges": int(((d_valve < -TOL) & inside).sum()),
                 "largest_decrease_bar_per_s": float(-d_valve.min()) if bad else 0.0}
    open_valves = [float(v) for v in VALVE if v <= 90.0]
    roots = {v: root(model, v) for v in open_valves}
    near = [v for v, r in roots.items() if r is not None and abs(r - 1.0) <= 0.05]
    found = [r for r in roots.values() if r is not None]
    out["R3"] = {"mark": "yes" if len(near) == len(open_valves) else ("partly" if near else "no"),
                 "open_positions": len(open_valves), "positions_with_root_within_0.05_bar_of_1": len(near),
                 "positions_without_root": sum(1 for r in roots.values() if r is None),
                 "root_min_bar": min(found) if found else None, "root_max_bar": max(found) if found else None}
    ok = []
    for v in open_valves:
        values = dp(model, P, v, 0.0)
        ok.append(bool((values[P > 1.05] < 0).all() and (values[P < 0.95] > 0).all()))
    out["R4"] = {"mark": "yes" if all(ok) else ("partly" if any(ok) else "no"),
                 "open_positions": len(open_valves), "positions_relaxing_toward_1_bar": int(sum(ok))}
    pp5, ff5 = np.meshgrid(P_ABOVE, FLOW[FLOW >= 1.0], indexing="ij")
    closed = dp(model, pp5, 100.0, ff5)
    bad = int((closed < -TOL).sum())
    out["R5"] = {"mark": mark_share(bad, closed.size), "points": int(closed.size), "points_with_decreasing_pressure": bad,
                 "lowest_dp_bar_per_s": float(closed.min()),
                 "highest_pressure_without_decrease_at_flow_1": next((float(p) for p in P_ABOVE[::-1] if float(dp(model, p, 100.0, 1.0)) >= -TOL), None)}
    return out


def main() -> None:
    from aspire_sysid.task import load_task

    exp_dir = (REPO / sys.argv[1]).resolve() if not pathlib.Path(sys.argv[1]).is_absolute() else pathlib.Path(sys.argv[1])
    agg = json.loads((exp_dir / "aggregate.json").read_text(encoding="utf-8"))
    task = load_task(REPO / "tasks" / agg["task"])
    results = {}
    for run in agg["runs"]:
        label = run.get("recommended_label")
        if not label:
            continue
        model = compiled_model(task, exp_dir / "runs" / run["run_id"] / "pools" / "v1" / "models", label)
        results[run["run_id"]] = {"label": label, **check(model)}
    out = (pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else HERE) / f"{exp_dir.name}-requirements.json"
    out.write_text(json.dumps({"written_by": "experiments/paper/assessment/checks/fermenter_requirements.py",
                               "experiment": exp_dir.name, "runs": results}, indent=1) + "\n", encoding="utf-8", newline="\n")
    for run_id, r in results.items():
        print(run_id, r["label"], "finite on the grid:", r["finite"])
        for rid in ("R1", "R2", "R3", "R4", "R5"):
            print("  ", rid, json.dumps(r[rid]))
    print("written:", out)


if __name__ == "__main__":
    main()
