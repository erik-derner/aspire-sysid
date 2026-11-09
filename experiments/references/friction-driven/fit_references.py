"""Reference models for the task ``friction-driven``.

Three models are estimated on the training data of the task without the agent and written as
model files in the format of the agent's candidates, so that ``aspire evaluate`` scores them on
the sealed test data with the settings of the task. In all of them the expression ``dtheta`` is
``omega``, the kinematic identity that the task prescribes as requirement R1.

``ReferencePhysical``
    A pendulum with viscous and Coulomb friction driven by a motor torque proportional to the
    voltage, ``domega = -a*sin(theta) - b*omega - c*tanh(s*omega) + k*u``, with the steepness
    ``s = 10`` s/rad of the smoothed sign function fixed. This is the structure of the model
    recorded in ``tasks/friction-driven/provenance.md``; its four gains are estimated again here.
    They minimize the root mean squared error of the simulated angle on the training
    trajectories (Nelder-Mead method), started from the least-squares fit of the column
    ``domega``.

``ReferenceSindy``
    Sparse identification of nonlinear dynamics, ``pysindy.SINDy`` with its default settings,
    fitted to the supplied derivative column ``domega``.

``ReferenceSindyThreshold``
    The same with the threshold of the optimizer selected from a grid by the root mean squared
    error of the simulated angle on the training data.

Run with the Python environment of the agent (NumPy, SciPy, pandas, SymPy, PySINDy)::

    <agent-python> experiments/references/friction-driven/fit_references.py
    aspire evaluate tasks/friction-driven experiments/references/friction-driven/models \
        --out experiments/references/friction-driven/evaluation

The script reads only ``tasks/friction-driven/data/train.csv``. It never reads the test data.
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

TASK = "friction-driven"
HERE = pathlib.Path(__file__).resolve().parent
MODELS = HERE / "models"
SCRIPT = "experiments/references/friction-driven/fit_references.py"
STEEPNESS = 10.0  # s/rad, fixed steepness of the smoothed sign function


def physical_derivative(a: float, b: float, c: float, k: float):
    def deriv(x, u):
        theta, omega = x
        return np.array([omega, -a * math.sin(theta) - b * omega - c * math.tanh(STEEPNESS * omega) + k * u[0]])
    return deriv


def fit_physical(trajectories) -> dict:
    theta = np.concatenate([t["theta"] for t in trajectories])
    omega = np.concatenate([t["omega"] for t in trajectories])
    u = np.concatenate([t["u"] for t in trajectories])
    domega = np.concatenate([t["domega"] for t in trajectories])
    regressors = np.column_stack([-np.sin(theta), -omega, -np.tanh(STEEPNESS * omega), u])
    start, *_ = np.linalg.lstsq(regressors, domega, rcond=None)
    derivative_rmse = float(np.sqrt(np.mean((regressors @ start - domega) ** 2)))

    def criterion(p):
        return common.rmse(common.simulated_errors(TASK, trajectories, physical_derivative(*p)))

    at_start = criterion(start)
    result = scipy.optimize.minimize(criterion, start, method="Nelder-Mead",
                                     options={"xatol": 1e-6, "fatol": 1e-9, "maxiter": 4000})
    assert result.success, result.message
    a, b, c, k = (float(v) for v in result.x)
    n = len(common.simulated_errors(TASK, trajectories, physical_derivative(a, b, c, k)))
    print(f"physical: start (least squares on domega, RMSE {derivative_rmse:.4f} rad/s^2) "
          f"a, b, c, k = {np.round(start, 4)}, training RMSE of the simulated theta {at_start:.5f} rad")
    print(f"physical: a = {a:.5f}, b = {b:.5f}, c = {c:.5f}, k = {k:.5f}; training RMSE of the "
          f"simulated theta = {result.fun:.5f} rad on {n} samples, {result.nit} iterations")
    s0 = ", ".join(f"`{name} = {value:.4f}`" for name, value in zip("abck", start))
    return {
        "expressions": {
            "dtheta": "omega",
            "domega": "-a*sin(theta) - b*omega - c*tanh(s*omega) + k*u",
        },
        "parameters": [
            {"name": "a", "value": a, "unit": "rad/s^2", "type": "fitted",
             "description": "Gain of the gravity torque divided by the moment of inertia; for a "
                            "pendulum it equals the mass times the gravitational acceleration "
                            "times the distance of the centre of mass from the axis, divided by "
                            "the moment of inertia."},
            {"name": "b", "value": b, "unit": "1/s", "type": "fitted",
             "description": "Coefficient of viscous friction divided by the moment of inertia."},
            {"name": "c", "value": c, "unit": "rad/s^2", "type": "fitted",
             "description": "Coulomb (dry) friction torque divided by the moment of inertia."},
            {"name": "s", "value": STEEPNESS, "unit": "s/rad", "type": "fixed",
             "description": "Steepness of `tanh(s*omega)`, the smooth replacement of the sign "
                            "of the angular velocity; chosen as `10` s/rad, the value of the "
                            "model recorded in tasks/friction-driven/provenance.md, and not "
                            "estimated, so that the reference model is not tuned."},
            {"name": "k", "value": k, "unit": "rad/(s^2 V)", "type": "fitted",
             "description": "Gain of the motor voltage `u`: the motor torque per volt divided "
                            "by the moment of inertia."},
        ],
        "estimation": {
            "criterion": "Root mean squared error of the simulated angle `theta` in rad over all "
                         "scored samples of the training trajectories, because the task scores "
                         "the simulated `theta` and the intended use is simulation. The simulated "
                         "`omega` does not enter the criterion.",
            "data": f"data/train.csv, all `{len(trajectories)}` trajectories, each simulated as a "
                    f"whole from its first sample ({n} scored samples). The validation data were "
                    f"not used.",
            "method": f"Nelder-Mead simplex method, scipy.optimize.minimize with "
                      f"method='Nelder-Mead' (SciPy {scipy.__version__}), xatol `1e-6`, fatol "
                      f"`1e-9`. The method needs no derivative of the simulation error with "
                      f"respect to the parameters, and four parameters are few enough for a "
                      f"simplex search. Starting values {s0}: the ordinary least-squares fit "
                      f"(numpy.linalg.lstsq) of the column `domega` by the four terms, which is "
                      f"linear in the four gains and needs no starting values itself. The "
                      f"simulation uses one step of the classical fourth-order Runge-Kutta method "
                      f"per sampling period with the voltage held constant, as the evaluation of "
                      f"the task does. The four gains were estimated together in the second "
                      f"step. The method uses no random numbers.",
            "script": SCRIPT,
        },
        "discussion": {
            "family": "Pendulum with viscous and Coulomb friction and a voltage-proportional "
                      "drive; the sign function of the Coulomb term is replaced by a hyperbolic "
                      "tangent, a smooth approximation. Friction models of this kind are "
                      "surveyed in European Journal of Control 4(3), 176-195 (reference listed "
                      "in tasks/friction-driven/provenance.md; the smooth approximation is not "
                      "taken from it). Reference model written by hand; it is not a candidate "
                      "of the agent.",
            "interpretation": "`-a*sin(theta)` is the gravity torque that restores the hanging "
                              "equilibrium `theta = 0`; `-b*omega` is viscous friction; "
                              "`-c*tanh(s*omega)` is dry friction of constant magnitude `c` that "
                              "opposes the motion and passes through zero continuously; `k*u` is "
                              "the motor torque. All terms are divided by the moment of inertia.",
            "origin": "The structure is taken from tasks/friction-driven/provenance.md, where it "
                      "is recorded with the values of an earlier estimation; the four gains were "
                      "estimated again on the present training data. No other structure was "
                      "tried for this reference model.",
            "limitations": "The smoothed sign function gives no sticking: at rest the model "
                           "creeps towards `theta = 0` instead of staying inside a stick band. "
                           "The model has no Stribeck effect, no offset and no dynamics of the "
                           "motor current. The steepness `s` was not estimated.",
        },
    }


def main() -> None:
    np.set_printoptions(precision=6, suppress=True)
    trajectories = common.load(TASK)
    print("training trajectories:", [len(t["theta"]) for t in trajectories])
    fixed = {"dtheta": "omega"}
    files = {"ReferencePhysical": fit_physical(trajectories),
             "ReferenceSindy": common.fit_sindy_continuous(TASK, False, SCRIPT, fixed),
             "ReferenceSindyThreshold": common.fit_sindy_continuous(TASK, True, SCRIPT, fixed)}
    for label, content in files.items():
        common.write_model(MODELS, label, content)
    common.write_pool(MODELS, list(files), "Reference models estimated without the agent; none is recommended.")
    print("written:", ", ".join(sorted(p.name for p in MODELS.iterdir())))


if __name__ == "__main__":
    main()
