"""Reference models for the task ``turtlebot``.

Two models are estimated on the training data of the task without the agent and written as model
files in the format of the agent's candidates, so that ``aspire evaluate`` scores them on the
sealed test data with the settings of the task:

``ReferenceUnicycle``
    The kinematic model of a unicycle with one gain per command,
    ``x_next = x + p_v*v_f*cos(phi)``, ``y_next = y + p_v*v_f*sin(phi)``,
    ``phi_next = phi + p_w*v_a``. The two gains are estimated by minimizing the root mean squared
    error of the simulated position ``x`` over consecutive segments of 25 simulated samples of the
    training trajectories (the segments of the harness for ``evaluation.horizon: 25``), with the
    Nelder-Mead method started at the sampling period, ``p_v = p_w = 0.2`` s.

``ReferenceSindy``
    Sparse identification of nonlinear dynamics in discrete time, ``pysindy.DiscreteSINDy`` with
    its default settings (polynomial library of degree 2 in the three states and the two commands,
    sequentially thresholded least squares with threshold 0.1), fitted to the one-step transitions
    of the training data. Transitions in which the logged heading wraps at +-pi are left out.

``ReferenceSindyThreshold``
    The same method with one setting changed: the threshold is the value of the grid
    ``THRESHOLDS`` with the smallest root mean squared error of the simulated ``x`` on the
    segments of the training data. With the default threshold 0.1 no term with a command is kept,
    because at the sampling period of 0.2 s every such coefficient is smaller than 0.1.

Run with the Python environment of the agent (NumPy, SciPy, pandas, PySINDy), from any folder::

    <agent-python> experiments/references/turtlebot/fit_references.py
    aspire evaluate tasks/turtlebot experiments/references/turtlebot/models \
        --out experiments/references/turtlebot/evaluation

The script reads only ``tasks/turtlebot/data/train.csv``. It never reads the test data.
"""
from __future__ import annotations

import json
import pathlib
import re

import numpy as np
import pandas as pd
import pysindy as ps
import scipy
import scipy.optimize

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
TRAIN = REPO / "tasks" / "turtlebot" / "data" / "train.csv"
MODELS = HERE / "models"
STATES = ["x", "y", "phi"]
INPUTS = ["v_f", "v_a"]
UNITS = {"x": "m", "y": "m", "phi": "rad", "v_f": "m/s", "v_a": "rad/s"}
T_S = 0.2  # s, sampling period declared by the task
HORIZON = 25  # simulated samples per segment, evaluation.horizon of the task
SCRIPT = "experiments/references/turtlebot/fit_references.py"
THRESHOLDS = (0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001)  # grid of ReferenceSindyThreshold


def load() -> list[np.ndarray]:
    """The training trajectories as arrays with the columns x, y, phi, v_f, v_a."""
    table = pd.read_csv(TRAIN)
    return [group[STATES + INPUTS].to_numpy(float)
            for _, group in table.groupby("trajectory", sort=True)]


def segments(n: int) -> list[tuple[int, int]]:
    """First and last row of the consecutive segments of a trajectory of n rows: each segment is
    initialized from its first row and simulates at most HORIZON samples; consecutive segments
    share one row (the rule of ``aspire_sysid.evaluate.data.segments`` for initialization 1)."""
    out, start = [], 0
    while start < n - 1:
        stop = min(start + HORIZON, n - 1)
        out.append((start, stop))
        start = stop
    return out


def simulated_x_errors(step, trajectories) -> np.ndarray:
    """Errors of the simulated x on all scored samples; ``step(state, command)`` returns the next
    state."""
    errors = []
    for rows in trajectories:
        for first, last in segments(len(rows)):
            state = rows[first, :3].copy()
            for k in range(first, last):
                state = step(state, rows[k, 3:])
                errors.append(state[0] - rows[k + 1, 0])
    return np.asarray(errors)


def rmse(errors: np.ndarray) -> float:
    return float(np.sqrt(np.mean(errors ** 2)))


def unicycle_step(p_v: float, p_w: float):
    def step(state, command):
        x, y, phi = state
        v_f, v_a = command
        return np.array([x + p_v * v_f * np.cos(phi), y + p_v * v_f * np.sin(phi), phi + p_w * v_a])
    return step


def fit_unicycle(trajectories) -> dict:
    def criterion(p):
        return rmse(simulated_x_errors(unicycle_step(p[0], p[1]), trajectories))

    start = np.array([T_S, T_S])
    result = scipy.optimize.minimize(criterion, start, method="Nelder-Mead",
                                     options={"xatol": 1e-9, "fatol": 1e-12, "maxiter": 2000})
    assert result.success, result.message
    p_v, p_w = (float(v) for v in result.x)
    n = len(simulated_x_errors(unicycle_step(p_v, p_w), trajectories))
    print(f"unicycle: p_v = {p_v:.6f} s, p_w = {p_w:.6f} s, training RMSE of simulated x = "
          f"{result.fun:.5f} m on {n} samples, {result.nit} iterations; at the start "
          f"{criterion(start):.5f} m")
    return {
        "expressions": {
            "x_next": "x + p_v*v_f*cos(phi)",
            "y_next": "y + p_v*v_f*sin(phi)",
            "phi_next": "phi + p_w*v_a",
        },
        "parameters": [
            {"name": "p_v", "value": p_v, "unit": "s", "type": "fitted",
             "description": "Gain of the forward velocity command `v_f`: the commanded velocity "
                            "times `p_v` is the displacement along the heading in one sample. It "
                            "would equal the sampling period `0.2` s if the robot executed the "
                            "command exactly and the pose were logged without error."},
            {"name": "p_w", "value": p_w, "unit": "s", "type": "fitted",
             "description": "Gain of the angular velocity command `v_a`: the commanded angular "
                            "velocity times `p_w` is the change of the heading in one sample. It "
                            "would equal the sampling period `0.2` s under the same conditions."},
        ],
        "estimation": {
            "criterion": "Root mean squared error of the simulated position `x` in m, because the "
                         "task scores the simulated `x` and the intended use is simulation over "
                         "about 5 s. The simulated `y` and `phi` do not enter the criterion.",
            "data": f"data/train.csv, all three trajectories. Each trajectory is cut into "
                    f"consecutive segments of at most `{HORIZON}` simulated samples; a segment "
                    f"starts from the logged pose of its first row, and every row after the first "
                    f"of a trajectory is scored once ({n} scored samples). No row is left out.",
            "method": f"Nelder-Mead simplex method, scipy.optimize.minimize with "
                      f"method='Nelder-Mead' (SciPy {scipy.__version__}), xatol `1e-9`, fatol "
                      f"`1e-12`. The method needs no derivative of the simulation error, and the "
                      f"model has two parameters, for which a simplex search is sufficient. "
                      f"Starting values `p_v = 0.2` s and `p_w = 0.2` s, the sampling period, "
                      f"which is the value of both gains for an ideal robot. Both parameters were "
                      f"estimated together. The method uses no random numbers.",
            "script": SCRIPT,
        },
        "discussion": {
            "family": "Kinematic model of a unicycle (differential-drive robot without slip), "
                      "discretized with the forward Euler method, with one gain per command. "
                      "Reference model written by hand; it is not a candidate of the agent.",
            "interpretation": "`p_v*v_f*cos(phi)` and `p_v*v_f*sin(phi)` are the components of "
                              "the displacement of one sample along the heading `phi`; "
                              "`p_w*v_a` is the change of the heading in one sample.",
            "origin": "The structure is the textbook kinematics of a differential-drive robot. "
                      "The two gains replace the sampling period, because the logged motion per "
                      "sample is smaller than the commanded velocity times the sampling period. "
                      "No other structure was tried for this reference model.",
            "limitations": "The model has no delay between a command and the motion, no "
                           "dependence of the gains on time or speed, and no model of the "
                           "odometry error. The heading enters the criterion only through its "
                           "effect on `x`, so that `p_w` is not an estimate of the heading gain.",
        },
    }


def term_expression(name: str) -> str:
    """A PySINDy feature name such as ``x phi`` or ``v_f^2`` as an expression of the task."""
    if name == "1":
        return ""
    return "*".join(re.sub(r"\^(\d+)", r"**\1", factor) for factor in name.split(" "))


def term_unit(target: str, name: str) -> str:
    if name == "1":
        return UNITS[target]
    factors = []
    for factor in name.split(" "):
        base, _, power = factor.partition("^")
        factors.append(f"({UNITS[base]})" + (f"^{power}" if power else ""))
    return f"{UNITS[target]} / (" + " ".join(factors) + ")"


def sindy_transitions(trajectories):
    """One-step transitions of the training data without those in which the heading wraps."""
    x, x_next, u, omitted = [], [], [], 0
    for rows in trajectories:
        keep = np.abs(np.diff(rows[:, 2])) < np.pi  # the logged heading does not wrap
        omitted += int((~keep).sum())
        x.append(rows[:-1, :3][keep])
        x_next.append(rows[1:, :3][keep])
        u.append(rows[:-1, 3:][keep])
    return x, x_next, u, omitted


def sindy_model(trajectories, threshold: float | None):
    """The fitted model and its training RMSE of the simulated x; ``None`` is the default."""
    x, x_next, u, _ = sindy_transitions(trajectories)
    optimizer = None if threshold is None else ps.STLSQ(threshold=threshold)
    model = ps.DiscreteSINDy(optimizer=optimizer)
    model.fit(x, t=T_S, x_next=x_next, u=u, feature_names=STATES + INPUTS)

    def step(state, command):
        return model.predict(state[None, :], u=command[None, :])[0]

    with np.errstate(all="ignore"):
        error = rmse(simulated_x_errors(step, trajectories))
    return model, error


def fit_sindy(trajectories, select_threshold: bool = False) -> dict:
    x, _, _, omitted = sindy_transitions(trajectories)
    transitions = sum(len(a) for a in x)
    if select_threshold:
        scan = {th: sindy_model(trajectories, th)[1] for th in THRESHOLDS}
        for th, error in scan.items():
            print(f"  threshold {th}: training RMSE of simulated x = {error:.5f} m")
        threshold = min(scan, key=lambda th: (not np.isfinite(scan[th]), scan[th]))
        model, train = sindy_model(trajectories, threshold)
    else:
        model, train = sindy_model(trajectories, None)
    names = model.get_feature_names()
    coefficients = model.coefficients()
    optimizer = model.optimizer
    expressions, parameters = {}, []
    for i, target in enumerate(STATES):
        terms = []
        for j, name in enumerate(names):
            value = float(coefficients[i, j])
            if value == 0.0:
                continue
            parameter = f"c_{target}_{len(terms) + 1}"
            expression = term_expression(name)
            terms.append(parameter + ("*" + expression if expression else ""))
            parameters.append({
                "name": parameter, "value": value, "unit": term_unit(target, name),
                "type": "fitted",
                "description": f"Coefficient of the library term `{expression or '1'}` in the "
                               f"expression of `{target}_next`.",
            })
        expressions[f"{target}_next"] = " + ".join(terms) if terms else "0"

    print(f"sindy (threshold {optimizer.threshold}): {len(parameters)} nonzero coefficients of "
          f"{coefficients.size}; {transitions} transitions, {omitted} omitted; training RMSE of "
          f"simulated x = {train:.5f} m")
    if len(parameters) <= 6:
        for key, value in expressions.items():
            print("  ", key, "=", value)
    if select_threshold:
        setting = (f"its default settings except the threshold of the optimizer, which was "
                   f"selected from the grid `{', '.join(str(th) for th in THRESHOLDS)}` as the "
                   f"value with the smallest root mean squared error of the simulated `x` on "
                   f"the training data, cut into segments of `{HORIZON}` simulated samples; the "
                   f"selected threshold is `{optimizer.threshold}`")
        reason = ("The threshold was changed because with the default `0.1` no term that "
                  "contains a command is kept: at the sampling period of `0.2` s every such "
                  "coefficient is smaller than `0.1`. The selection uses the training data "
                  "only.")
    else:
        setting = "its default settings"
        reason = ("The defaults were used because the model is a reference for what the tool "
                  "gives without tuning.")
    return {
        "expressions": expressions,
        "parameters": parameters,
        "estimation": {
            "criterion": "Sum of squared one-step prediction errors of each next state (`x` in "
                         "m, `y` in m, `phi` in rad), each state fitted separately, with a "
                         "ridge penalty; this is the criterion of the default optimizer of the "
                         "package and is not the simulation error that the task scores. It "
                         "was kept because the reference model is the result of the tool as it "
                         "is delivered.",
            "data": f"data/train.csv, all three trajectories, as one-step transitions from a row "
                    f"to the next row of the same trajectory: `{transitions}` transitions. "
                    f"`{omitted}` transitions in which the logged heading `phi` wraps at pi were "
                    f"left out, because the wrapped next heading is not a continuous function of "
                    f"the present state.",
            "method": f"Sparse identification of nonlinear dynamics (SINDy; Brunton, Proctor and "
                      f"Kutz, 2016) in discrete time, pysindy.DiscreteSINDy (PySINDy "
                      f"{ps.__version__}) with {setting}: the library of all "
                      f"polynomial terms up to degree `{model.feature_library.degree}` in `x`, "
                      f"`y`, `phi`, `v_f` and `v_a` with a constant term, and sequentially "
                      f"thresholded least squares (STLSQ) with threshold "
                      f"`{optimizer.threshold}`, ridge parameter `{optimizer.alpha}` and at most "
                      f"`{optimizer.max_iter}` iterations. {reason} The method needs no "
                      f"starting values and uses no random numbers. All coefficients of one "
                      f"state were estimated together.",
            "script": SCRIPT,
        },
        "discussion": {
            "family": "Polynomial discrete-time state-space model found by sparse regression "
                      "(SINDy). Reference model; it is not a candidate of the agent.",
            "interpretation": "Each expression is a linear combination of the polynomial library "
                              "terms that the thresholding kept. The terms have no assigned "
                              "physical meaning; a coefficient of the present state close to 1 "
                              "carries the state over to the next sample, and the terms with "
                              "`v_f` or `v_a` add the effect of the commands.",
            "origin": "The structure was selected by the sparse-regression algorithm from the "
                      "polynomial library; no physical reasoning entered, and no other library "
                      "was tried.",
            "limitations": "A polynomial library of degree 2 contains no trigonometric function "
                           "of the heading, so that the model cannot represent the rotation of "
                           "the displacement with the heading. The criterion is the one-step "
                           "prediction error, not the simulation error. The polynomial in `phi` "
                           "is not periodic and is fitted on headings between -pi and pi.",
        },
    }


def main() -> None:
    np.set_printoptions(precision=6, suppress=True)
    trajectories = load()
    print("training trajectories:", [len(t) for t in trajectories])
    MODELS.mkdir(parents=True, exist_ok=True)
    files = {"ReferenceUnicycle": fit_unicycle(trajectories),
             "ReferenceSindy": fit_sindy(trajectories),
             "ReferenceSindyThreshold": fit_sindy(trajectories, select_threshold=True)}
    for label, content in files.items():
        (MODELS / f"{label}.json").write_text(json.dumps(content, indent=2) + "\n",
                                              encoding="utf-8", newline="\n")
    pool = {"order": list(files), "recommended": None,
            "reason": "Reference models estimated without the agent; none is recommended."}
    (MODELS / "pool.json").write_text(json.dumps(pool, indent=2) + "\n", encoding="utf-8",
                                      newline="\n")
    print("written:", ", ".join(sorted(p.name for p in MODELS.iterdir())))


if __name__ == "__main__":
    main()
