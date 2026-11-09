"""Shared functions of the reference-model scripts.

A reference model is a model of a task that is obtained without the agent and scored by the
harness with ``aspire evaluate`` on the same sealed test data as the candidates of the agent.
The functions here read the training data of a task, simulate a model on them in the way the
harness does, and write model files in the format of the agent's candidates. They never read the
test data. The module needs NumPy, pandas and SymPy only, so that it runs in the Python
environment of the agent and in the environment that holds PySR.

Simulation as in ``aspire_sysid.evaluate.predict._simulate`` for ``evaluation.mode: simulation``
with ``initialization: 1``: the state starts from the measured state at the first sample of a
trajectory; a discrete-time model maps the state and the inputs of sample k to the state of
sample k + 1; a continuous-time model is integrated by one step of the classical fourth-order
Runge-Kutta method per sampling period with the inputs of sample k held constant; every sample
after the first is scored. With ``evaluation.horizon: H`` the training trajectories are cut into
consecutive segments of at most H simulated samples (``aspire_sysid.evaluate.data.segments``).
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd
import sympy as sp

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]

# The fields of tasks/<task>/task.yaml that the scripts need.
TASKS: dict[str, dict] = {
    "turtlebot": {
        "formulation": "discrete", "states": ["x", "y", "phi"], "inputs": ["v_f", "v_a"],
        "output": "x", "t_s": 0.2, "horizon": 25, "keys": ["x_next", "y_next", "phi_next"],
        "limits": {"x": 100.0, "y": 100.0, "phi": 1000.0}, "derivative": {},
        "units": {"x": "m", "y": "m", "phi": "rad", "v_f": "m/s", "v_a": "rad/s"},
        "files": {"train": "data/train.csv"},
    },
    "fermenter-pressure": {
        "formulation": "continuous", "states": ["p"], "inputs": ["valve", "flow"],
        "output": "p", "t_s": 5.0, "horizon": None, "keys": ["dp"],
        "limits": {"p": 100.0}, "derivative": {"p": "dp"},
        "units": {"p": "bar", "valve": "% closed", "flow": "l/min", "dp": "bar/s"},
        "files": {"train": "data/train.csv", "val": "data/val.csv"},
    },
    "friction-driven": {
        "formulation": "continuous", "states": ["theta", "omega"], "inputs": ["u"],
        "output": "theta", "t_s": 0.01, "horizon": None, "keys": ["dtheta", "domega"],
        "limits": {"theta": 1000.0, "omega": 1000.0}, "derivative": {"omega": "domega"},
        "units": {"theta": "rad", "omega": "rad/s", "u": "V", "domega": "rad/s^2"},
        "files": {"train": "data/train.csv", "val": "data/val.csv"},
    },
}


def load(task: str, group: str = "train") -> list[dict[str, np.ndarray]]:
    """The trajectories of a data file of the task, each as a mapping from column name to array.

    ``group`` is ``train`` or ``val``; the test data are not reachable through this function.
    """
    spec = TASKS[task]
    if group not in spec["files"]:
        raise ValueError(f"the task {task} has no {group} data")
    table = pd.read_csv(REPO / "tasks" / task / spec["files"][group])
    columns = [c for c in table.columns if c != "trajectory"]
    if "trajectory" in table.columns:
        groups = [g for _, g in table.groupby("trajectory", sort=True)]
    else:
        groups = [table]
    return [{c: g[c].to_numpy(float) for c in columns} for g in groups]


def segments(n: int, horizon: int | None) -> list[tuple[int, int]]:
    """First and last row of the segments of a trajectory of n rows (initialization 1)."""
    if horizon is None:
        return [(0, n - 1)]
    out, start = [], 0
    while start < n - 1:
        stop = min(start + horizon, n - 1)
        out.append((start, stop))
        start = stop
    return out


def _rk4(deriv, x, u, h):
    k1 = deriv(x, u)
    k2 = deriv(x + 0.5 * h * k1, u)
    k3 = deriv(x + 0.5 * h * k2, u)
    k4 = deriv(x + h * k3, u)
    return x + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def simulated_errors(task: str, trajectories, fun) -> np.ndarray | None:
    """Errors of the simulated output on all scored samples of the trajectories.

    ``fun(x, u)`` takes the state vector and the input vector and returns the next state
    (discrete-time task) or the time derivative of the state (continuous-time task). ``None`` is
    returned when a simulated state is not finite or leaves the failure limits of the task, which
    is a numerical failure for the harness.
    """
    spec = TASKS[task]
    states, inputs, out = spec["states"], spec["inputs"], spec["states"].index(spec["output"])
    bounds = np.array([spec["limits"][s] for s in states])
    discrete = spec["formulation"] == "discrete"
    errors = []
    with np.errstate(all="ignore"):
        for traj in trajectories:
            xs = np.column_stack([traj[s] for s in states])
            us = np.column_stack([traj[a] for a in inputs])
            for first, last in segments(len(xs), spec["horizon"]):
                x = xs[first].copy()
                for k in range(first, last):
                    x = np.asarray(fun(x, us[k]), float) if discrete else _rk4(fun, x, us[k], spec["t_s"])
                    if not np.all(np.isfinite(x)) or np.any(np.abs(x) > bounds):
                        return None
                    errors.append(x[out] - xs[k + 1, out])
    return np.asarray(errors)


def rmse(errors: np.ndarray | None) -> float:
    """Root mean squared error; infinite for a failed simulation."""
    if errors is None or len(errors) == 0:
        return float("inf")
    return float(np.sqrt(np.mean(errors ** 2)))


_NUMPY_NAMES = {"Abs": np.abs, "sign": np.sign, "Max": np.maximum, "Min": np.minimum}


def compile_expressions(task: str, expressions: dict[str, str], parameters: dict[str, float]):
    """``fun(x, u)`` for :func:`simulated_errors` from expression texts and parameter values.

    The expressions use the column names of the task, the parameter names and the functions of
    the model file format.
    """
    spec = TASKS[task]
    names = spec["states"] + spec["inputs"]
    symbols = {n: sp.Symbol(n) for n in names + list(parameters)}
    table = dict(symbols)
    table.update({"Abs": sp.Abs, "sign": sp.sign, "Max": sp.Max, "Min": sp.Min})
    values = {symbols[n]: v for n, v in parameters.items()}
    functions = []
    for key in spec["keys"]:
        expr = sp.sympify(expressions[key], locals=table).subs(values)
        functions.append(sp.lambdify([symbols[n] for n in names], expr, modules=[_NUMPY_NAMES, "numpy"]))

    def fun(x, u):
        return np.array([float(f(*x, *u)) for f in functions])

    return fun


def training_error(task: str, expressions: dict[str, str], parameters: dict[str, float],
                   group: str = "train") -> float:
    """RMSE of the simulated output on a data file of the task, as the harness computes it."""
    return rmse(simulated_errors(task, load(task, group), compile_expressions(task, expressions, parameters)))


def write_model(folder: pathlib.Path, label: str, content: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{label}.json").write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_pool(folder: pathlib.Path, order: list[str], reason: str) -> None:
    pool = {"order": order, "recommended": None, "reason": reason}
    (folder / "pool.json").write_text(json.dumps(pool, indent=2) + "\n", encoding="utf-8", newline="\n")


THRESHOLDS = tuple(m * 10.0 ** e for e in range(1, -7, -1) for m in (1.0, 0.5, 0.2))
"""Grid of the threshold of ``ReferenceSindyThreshold`` for the continuous-time tasks: the values
1, 0.5 and 0.2 times the powers of ten from 10 to 1e-6, that is 10, 5, 2, 1, ..., 2e-7, in
decreasing order."""


def fit_sindy_continuous(task: str, select_threshold: bool, script: str, fixed: dict[str, str] | None = None) -> dict:
    """A model file content found by sparse regression on the supplied derivative column(s).

    ``pysindy.SINDy`` is fitted to the training data with the states and inputs of the task as
    variables and, as the derivative of each state, the derivative column that the task supplies
    (for a state without such a column, the expression of ``fixed``, evaluated on the data).
    ``fixed`` maps an expression key to an expression that the task prescribes; its key is
    written as prescribed and the regression result for it is discarded. With
    ``select_threshold`` the threshold of the optimizer is the value of :data:`THRESHOLDS` with
    the smallest RMSE of the simulated output on the training data (the largest such value);
    otherwise the default settings of the package are used.
    """
    import pysindy as ps

    spec = TASKS[task]
    fixed = fixed or {}
    states, inputs, units = spec["states"], spec["inputs"], spec["units"]
    trajectories = load(task)
    xs = [np.column_stack([t[s] for s in states]) for t in trajectories]
    us = [np.column_stack([t[a] for a in inputs]) for t in trajectories]
    table = {n: sp.Symbol(n) for n in states + inputs}

    def derivative(traj, state):
        if state in spec["derivative"]:
            return traj[spec["derivative"][state]]
        f = sp.lambdify([table[n] for n in states + inputs], sp.sympify(fixed[f"d{state}"], locals=table), "numpy")
        return np.broadcast_to(f(*[traj[n] for n in states + inputs]), traj[state].shape).astype(float)

    xdots = [np.column_stack([derivative(t, s) for s in states]) for t in trajectories]
    rows = sum(len(x) for x in xs)

    def fitted(threshold):
        optimizer = None if threshold is None else ps.STLSQ(threshold=threshold)
        model = ps.SINDy(optimizer=optimizer)
        model.fit(xs, t=spec["t_s"], x_dot=xdots, u=us, feature_names=states + inputs)
        expressions, parameters = {}, []
        names, coefficients = model.get_feature_names(), model.coefficients()
        for i, state in enumerate(states):
            key = f"d{state}"
            if key in fixed:
                expressions[key] = fixed[key]
                continue
            terms = []
            for j, name in enumerate(names):
                value = float(coefficients[i, j])
                if value == 0.0:
                    continue
                parameter = f"c_{state}_{len(terms) + 1}"
                expression = term_expression(name)
                terms.append(parameter + ("*" + expression if expression else ""))
                target_unit = units.get(spec["derivative"].get(state, ""), f"{units[state]}/s")
                parameters.append({
                    "name": parameter, "value": value, "unit": term_unit(units, target_unit, name),
                    "type": "fitted",
                    "description": f"Coefficient of the library term `{expression or '1'}` in the "
                                   f"expression `{key}`.",
                })
            expressions[key] = " + ".join(terms) if terms else "0"
        error = training_error(task, expressions, {r["name"]: r["value"] for r in parameters})
        return model, expressions, parameters, error

    out = spec["output"]
    if select_threshold:
        scan = {}
        for th in THRESHOLDS:
            scan[th] = fitted(th)[3]
            print(f"  threshold {th:g}: training RMSE of the simulated {out} = {scan[th]:.6g} {units[out]}")
        threshold = min(scan, key=lambda th: (scan[th], -th))
        model, expressions, parameters, train = fitted(threshold)
    else:
        model, expressions, parameters, train = fitted(None)
    optimizer = model.optimizer
    print(f"sindy {task} (threshold {optimizer.threshold:g}): {len(parameters)} nonzero coefficients; "
          f"{rows} rows; training RMSE of the simulated {out} = {train:.6g} {units[out]}")
    for key, value in expressions.items():
        if len(value) < 200:
            print("  ", key, "=", value)
    regressed = [f"d{s}" for s in states if f"d{s}" not in fixed]
    targets = ", ".join(f"`{spec['derivative'][s]}` for `d{s}`" for s in states if f"d{s}" not in fixed)
    grid = f"{THRESHOLDS[0]:g}, {THRESHOLDS[1]:g}, {THRESHOLDS[2]:g}, ..., {THRESHOLDS[-1]:g}"
    if select_threshold:
        setting = (f"its default settings except the threshold of the optimizer, which was selected "
                   f"from the grid `{grid}` (the values 1, 0.5 and 0.2 times the powers of ten) as "
                   f"the largest value with the smallest root mean squared error of the simulated "
                   f"`{out}` on the training data; the selected threshold is `{optimizer.threshold:g}`")
        reason = ("The threshold was selected because the default `0.1` is an absolute bound on the "
                  "coefficients and does not depend on the units of the variables. The selection "
                  "uses the training data only.")
    else:
        setting = "its default settings"
        reason = ("The defaults were used because the model is a reference for what the tool gives "
                  "without tuning.")
    prescribed = ""
    if fixed:
        prescribed = " " + " ".join(
            f"The expression `{k}` is `{v}`, as the task prescribes; the regression result for it "
            f"was discarded." for k, v in fixed.items())
    return {
        "expressions": expressions,
        "parameters": parameters,
        "estimation": {
            "criterion": f"Sum of squared differences between the library expansion and the "
                         f"supplied derivative column ({targets}), with a ridge penalty; this is "
                         f"the criterion of the default optimizer of the package and is not the "
                         f"simulation error that the task scores. It was kept because the "
                         f"reference model is the result of the tool as it is delivered.",
            "data": f"data/train.csv, all `{rows}` rows of all `{len(trajectories)}` "
                    f"trajectories. The validation data were not used.",
            "method": f"Sparse identification of nonlinear dynamics (SINDy; Brunton, Proctor and "
                      f"Kutz, 2016), pysindy.SINDy (PySINDy {ps.__version__}) with {setting}: the "
                      f"library of all polynomial terms up to degree "
                      f"`{model.feature_library.degree}` in "
                      f"{', '.join('`' + n + '`' for n in states + inputs)} with a constant term, "
                      f"and sequentially thresholded least squares (STLSQ) with threshold "
                      f"`{optimizer.threshold:g}`, ridge parameter `{optimizer.alpha}` and at most "
                      f"`{optimizer.max_iter}` iterations. The derivative was not computed by the "
                      f"package; the derivative column of the task was passed to it. {reason}"
                      f"{prescribed} The method needs no starting values and uses no random "
                      f"numbers. All coefficients of one expression were estimated together.",
            "script": script,
        },
        "discussion": {
            "family": "Polynomial continuous-time state-space model found by sparse regression "
                      "(SINDy). Reference model; it is not a candidate of the agent.",
            "interpretation": f"The expression{'s' if len(regressed) > 1 else ''} "
                              f"{', '.join('`' + k + '`' for k in regressed)} "
                              f"{'are' if len(regressed) > 1 else 'is'} a linear combination of "
                              f"the polynomial library terms that the thresholding kept. The "
                              f"terms have no assigned physical meaning.",
            "origin": "The structure was selected by the sparse-regression algorithm from the "
                      "polynomial library; no physical reasoning entered, and no other library "
                      "was tried.",
            "limitations": "The polynomial library of degree 2 contains no other function of the "
                           "variables. The criterion is the error of the derivative, not the "
                           "simulation error, so that a small error of the derivative does not "
                           "bound the error of a long simulation. Outside the range of the "
                           "training data a polynomial is not expected to hold.",
        },
    }


def term_expression(name: str) -> str:
    """A PySINDy feature name such as ``x phi`` or ``v_f^2`` as an expression of the task."""
    import re

    if name == "1":
        return ""
    return "*".join(re.sub(r"\^(\d+)", r"**\1", factor) for factor in name.split(" "))


def term_unit(units: dict[str, str], target_unit: str, name: str) -> str:
    """The unit of the coefficient of a PySINDy library term in an expression with ``target_unit``."""
    if name == "1":
        return target_unit
    factors = []
    for factor in name.split(" "):
        base, _, power = factor.partition("^")
        factors.append(f"({units[base]})" + (f"^{power}" if power else ""))
    return f"{target_unit} / (" + " ".join(factors) + ")"
