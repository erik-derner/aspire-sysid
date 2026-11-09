"""Reference models for the task ``fermenter-pressure``.

Three models are estimated on the training data of the task without the agent and written as
model files in the format of the agent's candidates, so that ``aspire evaluate`` scores them on
the sealed test data with the settings of the task.

``ReferencePhysical``
    Mass balance of the headspace with an inflow proportional to the air flow rate and an outflow
    through the outlet valve that follows the orifice equation with a linear valve
    characteristic, ``dp = a*flow - b*(1 - valve/100)*sqrt(Max(p - p_a, 0))``. The three
    parameters minimize the root mean squared error of the simulated pressure on the training
    trajectory (Nelder-Mead method), started from a least-squares fit of the column ``dp``. The
    structure was fixed before any estimation and was not revised afterwards.

``ReferenceSindy``
    Sparse identification of nonlinear dynamics, ``pysindy.SINDy`` with its default settings,
    fitted to the supplied derivative column ``dp``.

``ReferenceSindyThreshold``
    The same with the threshold of the optimizer selected from a grid by the root mean squared
    error of the simulated pressure on the training data.

Run with the Python environment of the agent (NumPy, SciPy, pandas, SymPy, PySINDy)::

    <agent-python> experiments/references/fermenter-pressure/fit_references.py
    aspire evaluate tasks/fermenter-pressure experiments/references/fermenter-pressure/models \
        --out experiments/references/fermenter-pressure/evaluation

The script reads only ``tasks/fermenter-pressure/data/train.csv``. It never reads the test data.
"""
from __future__ import annotations

import math
import pathlib
import sys

import numpy as np
import scipy
import scipy.optimize

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common  # noqa: E402

TASK = "fermenter-pressure"
HERE = pathlib.Path(__file__).resolve().parent
MODELS = HERE / "models"
SCRIPT = "experiments/references/fermenter-pressure/fit_references.py"
P_A_START = 1.0  # bar, starting value of the ambient pressure


def physical_derivative(a: float, b: float, p_a: float):
    def deriv(x, u):
        valve, flow = u
        return np.array([a * flow - b * (1.0 - valve / 100.0) * math.sqrt(max(x[0] - p_a, 0.0))])
    return deriv


def fit_physical(trajectories) -> dict:
    p = np.concatenate([t["p"] for t in trajectories])
    valve = np.concatenate([t["valve"] for t in trajectories])
    flow = np.concatenate([t["flow"] for t in trajectories])
    dp = np.concatenate([t["dp"] for t in trajectories])
    regressors = np.column_stack([flow, -(1.0 - valve / 100.0) * np.sqrt(np.maximum(p - P_A_START, 0.0))])
    (a0, b0), *_ = np.linalg.lstsq(regressors, dp, rcond=None)
    start = np.array([a0, b0, P_A_START])
    derivative_rmse = float(np.sqrt(np.mean((regressors @ np.array([a0, b0]) - dp) ** 2)))

    def criterion(q):
        return common.rmse(common.simulated_errors(TASK, trajectories, physical_derivative(*q)))

    at_start = criterion(start)
    result = scipy.optimize.minimize(criterion, start, method="Nelder-Mead",
                                     options={"xatol": 1e-9, "fatol": 1e-10, "maxiter": 4000})
    assert result.success, result.message
    a, b, p_a = (float(v) for v in result.x)
    n = len(common.simulated_errors(TASK, trajectories, physical_derivative(a, b, p_a)))
    print(f"physical: start a = {a0:.6g}, b = {b0:.6g}, p_a = {P_A_START} (least squares on dp, RMSE "
          f"{derivative_rmse:.5f} bar/s), training RMSE of the simulated p {at_start:.5f} bar")
    print(f"physical: a = {a:.6g}, b = {b:.6g}, p_a = {p_a:.6g}; training RMSE of the simulated p = "
          f"{result.fun:.5f} bar on {n} samples, {result.nit} iterations")
    return {
        "expressions": {"dp": "a*flow - b*(1 - valve/c_v)*sqrt(Max(p - p_a, 0))"},
        "parameters": [
            {"name": "a", "value": a, "unit": "bar min/(l s)", "type": "fitted",
             "description": "Gain of the air flow rate `flow`: the rise of the headspace "
                            "pressure per unit of time and per unit of air flow rate; for an "
                            "ideal gas at constant temperature it is inversely proportional to "
                            "the volume of the headspace."},
            {"name": "b", "value": b, "unit": "bar^0.5/s", "type": "fitted",
             "description": "Gain of the outflow through the fully open outlet valve "
                            "(`valve = 0`): discharge coefficient and cross-section of the valve "
                            "combined with the properties of the headspace."},
            {"name": "c_v", "value": 100.0, "unit": "% closed", "type": "fixed",
             "description": "Valve position at which the valve is fully closed; `100`, given by "
                            "the description of the task (100 % = fully closed)."},
            {"name": "p_a", "value": p_a, "unit": "bar", "type": "fitted",
             "description": "Pressure downstream of the outlet valve (ambient pressure), below "
                            "which the model has no outflow."},
        ],
        "estimation": {
            "criterion": "Root mean squared error of the simulated pressure `p` in bar over all "
                         "scored samples of the training trajectory, because the task scores the "
                         "simulated `p` and the intended use is simulation.",
            "data": f"data/train.csv, the one trajectory, simulated as a whole from its first "
                    f"sample ({n} scored samples). The validation data were not used.",
            "method": f"Nelder-Mead simplex method, scipy.optimize.minimize with "
                      f"method='Nelder-Mead' (SciPy {scipy.__version__}), xatol `1e-9`, fatol "
                      f"`1e-10`. The method needs no derivative of the simulation error with "
                      f"respect to the parameters, which is not smooth in `p_a` because of the "
                      f"`Max` function, and three parameters are few enough for a simplex search. "
                      f"Starting values `a = {a0:.4g}`, `b = {b0:.4g}` and `p_a = {P_A_START}` "
                      f"bar: `p_a` was set to `1` bar, the standard atmospheric pressure rounded "
                      f"to one digit, and `a` and `b` are the ordinary least-squares fit "
                      f"(numpy.linalg.lstsq) of the column `dp` with this `p_a`, which is linear "
                      f"in `a` and `b` and needs no starting values itself. The simulation uses "
                      f"one step of the classical fourth-order Runge-Kutta method per sampling "
                      f"period with the inputs held constant, as the evaluation of the task "
                      f"does. `a`, `b` and `p_a` were estimated together in the second step. "
                      f"The method uses no random numbers.",
            "script": SCRIPT,
        },
        "discussion": {
            "family": "First-order mass balance of a gas volume with an orifice outflow (the "
                      "outflow is proportional to the square root of the pressure difference "
                      "across the valve, the equation of incompressible flow through an "
                      "orifice) and a linear valve characteristic. Reference model written by "
                      "hand; it is not a candidate of the agent. No reference is cited, because "
                      "the model was written from memory of textbook fluid mechanics and no "
                      "source was checked.",
            "interpretation": "`a*flow` is the rise of the pressure by the air fed into the "
                              "tank; `b*(1 - valve/c_v)*sqrt(Max(p - p_a, 0))` is the fall of "
                              "the pressure by the air that leaves through the outlet valve: "
                              "`1 - valve/c_v` is the open fraction of the valve, and "
                              "`sqrt(Max(p - p_a, 0))` is the dependence of the flow through an "
                              "orifice on the pressure difference, zero when the headspace "
                              "pressure is not above `p_a`.",
            "origin": "The structure was written from the description of the task (air fed in "
                      "at a controlled flow rate, outflow through a valve whose position is "
                      "given in % closed) before any estimation, and it was not changed after "
                      "the estimation. No other structure was tried for this reference model.",
            "limitations": "A linear valve characteristic and an incompressible orifice flow are "
                           "assumptions; a real valve has a nonlinear characteristic, and the "
                           "flow of air is compressible and becomes choked at a large pressure "
                           "ratio. The model has no leakage when the valve is fully closed and "
                           "no dynamics of the mass-flow controller. The headspace volume and "
                           "the temperature are taken as constant.",
        },
    }


def main() -> None:
    np.set_printoptions(precision=6, suppress=True)
    trajectories = common.load(TASK)
    print("training trajectories:", [len(t["p"]) for t in trajectories])
    files = {"ReferencePhysical": fit_physical(trajectories),
             "ReferenceSindy": common.fit_sindy_continuous(TASK, False, SCRIPT),
             "ReferenceSindyThreshold": common.fit_sindy_continuous(TASK, True, SCRIPT)}
    for label, content in files.items():
        common.write_model(MODELS, label, content)
    common.write_pool(MODELS, list(files), "Reference models estimated without the agent; none is recommended.")
    print("written:", ", ".join(sorted(p.name for p in MODELS.iterdir())))


if __name__ == "__main__":
    main()
