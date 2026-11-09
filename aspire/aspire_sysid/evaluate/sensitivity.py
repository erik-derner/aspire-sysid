"""Local rank test of the parameter sensitivity matrix.

The harness checks the local rank of the sensitivity matrix, the derivatives of the
model's fitting targets with respect to the independently fitted parameters, evaluated at the
fitted values on the fitting data (Ljung, 1999). Fixed constants are excluded; tied parameters are treated consistently with their
estimation. Rank deficiency indicates locally indistinguishable parameter combinations; it does
not distinguish structural redundancy from insufficiently informative data. The diagnostic never
excludes a candidate and never affects the ranking.

**Fitting targets.** The model file of format version 1 records the fitting criterion as text
(``estimation.criterion``) and has no structured field for the fitting target. The harness
therefore uses the fitting target implied by the formulation, and states it in the report:

- static task: the output expression ``f`` against the output column;
- continuous-time task: every state-derivative expression ``d<state>`` whose state has a
  state-derivative column in the data, against that column; expressions without
  such a column are not targets;
- discrete-time task: every next-state expression ``<state>_next`` at the measured ``x[k]`` and
  ``u[k]``, against the measured ``x[k+1]`` (the one-step target);
- NARX task: the regression ``<output>_next`` at the measured output history, against
  ``y[k+1]``.

A continuous-time task without any state-derivative column has no such target; the diagnostic
is then *unavailable*, with that reason. When an agent fitted by another criterion (for example
the simulation error), the rank of this matrix still reveals parameter combinations that the
model structure cannot separate on these data; the report states the target used.

**Fitting data.** The data named in the estimation record's ``data`` field: the training data
when an entry contains the word ``train`` or ``training`` (for example ``data/train.csv``), the
validation data when an entry contains the word ``val`` or ``validation``; the training data
when no entry names either (stated as an assumption). A negation in the text ("validation data
not used") is not interpreted; the agent is asked to list only the data it fitted on. Rows are used within
trajectories only (next-state targets never pair samples of two trajectories).

**Matrix.** ``J[i, j] = ∂r_i / ∂p_j`` at the fitted values, where ``r_i`` is the model value of
the target at row ``i`` and ``p_j`` the ``j``-th fitted parameter. The derivatives are analytic
(SymPy ``diff`` of the expression with every tied parameter replaced by its resolved tie
equation, so that the derivative with respect to a fitted parameter includes its effect through
every tie; fixed parameters and given constants at their values). Rows where a derivative or the
target value is not finite are dropped and counted. When there are several targets, the rows of
each target are divided by the population standard deviation of its measured column, so that
each target enters in comparable units. Each column is then divided by its Euclidean norm
(column scaling); a column of zeros (a parameter without influence on the targets) is left at
zero and named.

**Rank.** The singular values ``s_1 ≥ … ≥ s_n`` of the scaled matrix are computed with NumPy's
SVD. The numerical rank is the number of singular values with ``s_i / s_1 > RANK_THRESHOLD``
(:data:`RANK_THRESHOLD` = 1e-8). For every singular value at or below the threshold, the right
singular vector spans a locally indistinguishable combination; the parameters whose component
has magnitude at least :data:`GROUP_COMPONENT` in that vector are reported as a dependent group
with their components.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import sympy as sp

from ..model.checks import Candidate
from ..task.schema import TaskSpec
from .compiled import as_array, constant_values, symbols
from .data import Trajectory

RANK_THRESHOLD = 1e-8
"""Relative threshold on the singular values that defines the numerical rank."""

GROUP_COMPONENT = 0.1
"""Smallest magnitude of a null-vector component that places a parameter in a dependent group."""


@dataclass
class SensitivityResult:
    """The sensitivity rank diagnostic of one candidate."""

    available: bool
    reason: str | None = None
    targets: list[str] = field(default_factory=list)
    data: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    rows: int = 0
    rows_dropped: int = 0
    singular_values: list[float] = field(default_factory=list)
    rank: int | None = None
    deficient: bool | None = None
    zero_columns: list[str] = field(default_factory=list)
    dependent_groups: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Plain data for the JSON report (derived from the agent-visible data only)."""
        return {
            "available": self.available,
            "reason": self.reason,
            "targets": list(self.targets),
            "data": list(self.data),
            "assumptions": list(self.assumptions),
            "method": "analytic derivatives (SymPy), ties differentiated through their equations",
            "scaling": "rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm",
            "rank_threshold": f"s_i / s_1 > {RANK_THRESHOLD:g}",
            "parameters": list(self.parameters),
            "rows": self.rows,
            "rows_dropped": self.rows_dropped,
            "singular_values": list(self.singular_values),
            "rank": self.rank,
            "deficient": self.deficient,
            "zero_columns": list(self.zero_columns),
            "dependent_groups": list(self.dependent_groups),
        }


_MENTION = {
    "train": re.compile(r"(?<![a-z])train(?:ing)?(?![a-z])"),
    "val": re.compile(r"(?<![a-z])val(?:idation)?(?![a-z])"),
}


def _fitting_groups(candidate: Candidate, visible: dict[str, list[Trajectory]]) -> tuple[list[str], list[str]]:
    raw = candidate.estimation.get("data")
    entries = raw if isinstance(raw, list) else [raw]
    text = " ".join(str(e).lower() for e in entries)
    groups = [g for g in ("train", "val") if _MENTION[g].search(text) and g in visible]
    if groups:
        return groups, []
    return ["train"], ["the estimation record names neither the training nor the validation data; the training data are assumed"]


def _target_rows(task: TaskSpec, key: str, traj: Trajectory) -> tuple[dict[str, np.ndarray], np.ndarray] | None:
    """Argument values and measured target values of ``key`` on one trajectory, or ``None``."""
    cols = traj.columns
    n = traj.n
    if task.formulation == "static":
        return {a: cols[a] for a in task.argument_names}, cols[task.output]
    if task.formulation == "continuous":
        state = key[1:]
        dcol = next((c.name for c in task.columns if "state_derivative" in c.roles and c.derivative_of == state), None)
        if dcol is None or dcol not in cols:
            return None
        return {a: cols[a] for a in task.argument_names}, cols[dcol]
    if n < 2:
        return {a: np.zeros(0) for a in task.argument_names}, np.zeros(0)
    j = np.arange(0, n - 1)
    if task.formulation == "discrete":
        state = key[: -len("_next")]
        return {a: cols[a][j] for a in task.argument_names}, cols[state][j + 1]
    # narx: arguments at k from the measured history, target y[k+1]
    lag = max((d.lag for d in task.dynamics.delays), default=0)
    j = np.arange(lag, n - 1)
    vals = {task.output: cols[task.output][j]}
    for d in task.dynamics.delays:
        vals[d.name] = cols[d.variable][j - d.lag]
    for u in task.inputs:
        vals[u] = cols[u][j]
    return vals, cols[task.output][j + 1]


def sensitivity(task: TaskSpec, candidate: Candidate, visible: dict[str, list[Trajectory]]) -> SensitivityResult:
    """The local rank test for one candidate (module docstring)."""
    fitted = list(candidate.fitted)
    res = SensitivityResult(available=False, parameters=fitted)
    groups, notes = _fitting_groups(candidate, visible)
    res.data = groups
    res.assumptions = notes + ["the fitting target is the one implied by the formulation (the model file has no structured field for it)"]
    if not fitted:
        res.reason = "the candidate has no fitted parameter"
        return res
    resolved = candidate.resolved_expressions()
    values = {sp.Symbol(n, real=True): sp.Float(v, 17) for n, v in candidate.values.items() if n not in candidate.tied}
    consts = constant_values(task)
    psyms = [sp.Symbol(p, real=True) for p in fitted]
    blocks = []
    for key in task.expression_keys:
        per_traj = [(tr, _target_rows(task, key, tr)) for g in groups for tr in visible[g]]
        if any(r is None for _, r in per_traj):
            continue
        e = resolved[key].xreplace(consts)
        derivs = [sp.diff(e, p).xreplace(values) for p in psyms]
        fvals = e.xreplace(values)
        fn = sp.lambdify(symbols(task.argument_names), [fvals] + derivs, modules="numpy")
        rows_j, meas = [], []
        for _, (args, target) in per_traj:
            m = len(target)
            if m == 0:
                continue
            with np.errstate(all="ignore"):
                out = fn(*[args[a] for a in task.argument_names])
            cols = np.stack([as_array(v, m) for v in out], axis=1)
            rows_j.append(cols)
            meas.append(np.asarray(target, dtype=float))
        if not rows_j:
            continue
        mat = np.concatenate(rows_j)
        y = np.concatenate(meas)
        ok = np.all(np.isfinite(mat), axis=1) & np.isfinite(y)
        res.rows_dropped += int(np.sum(~ok))
        mat, y = mat[ok], y[ok]
        if mat.shape[0] == 0:
            continue
        sd = float(np.std(y))
        scale = sd if sd > 0 else 1.0
        blocks.append(mat[:, 1:] / scale)
        res.targets.append(key)
    if not blocks:
        res.reason = (
            "no fitting target is available: the task supplies no state-derivative column"
            if task.formulation == "continuous"
            else "no fitting target could be evaluated on the fitting data"
        )
        return res
    J = np.concatenate(blocks)
    res.rows = int(J.shape[0])
    norms = np.linalg.norm(J, axis=0)
    res.zero_columns = [p for p, nrm in zip(fitted, norms) if nrm == 0]
    Js = J / np.where(norms > 0, norms, 1.0)
    _, s, vt = np.linalg.svd(Js, full_matrices=True)
    s_full = np.zeros(len(fitted))
    s_full[: len(s)] = s
    res.singular_values = [float(x) for x in s_full]
    s1 = s_full[0] if s_full.size else 0.0
    small = [i for i, x in enumerate(s_full) if s1 == 0 or x / s1 <= RANK_THRESHOLD]
    res.rank = len(fitted) - len(small)
    res.deficient = bool(small)
    for i in small:
        v = vt[i]
        members = [(fitted[j], float(v[j])) for j in range(len(fitted)) if abs(v[j]) >= GROUP_COMPONENT]
        sgn = 1.0 if members and members[0][1] >= 0 else -1.0
        res.dependent_groups.append(
            {
                "singular_value": float(s_full[i]),
                "relative": float(s_full[i] / s1) if s1 > 0 else None,
                "parameters": [m[0] for m in members],
                "components": {m[0]: sgn * m[1] for m in members},
            }
        )
    res.available = True
    return res
