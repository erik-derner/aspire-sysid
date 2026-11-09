"""Comparison of a candidate with the sealed reference expression.

If a sealed reference expression exists, the harness attempts to determine whether
a candidate and the reference define the same function over the declared domain under the
stated assumptions, and reports proven equivalence, established non-equivalence or an unresolved
comparison; agreement at sampled points is reported as numerical agreement, not as a proof. The
reference and the comparison results are sealed: they never reach the agent.

**Numbers (the rule of the comparison).** Every number is taken as the exact decimal number it
is written as: the numeric literals of the candidate's expressions and tie equations as written in
the model file (for example ``0.1`` is 1/10, and ``a*0.1*3*x`` with ``a = 1`` is ``3x/10``), the
numeric literals of the reference text as written, and the values of fitted and fixed parameters
and of given constants in the shortest decimal form of their binary64 value (Python ``repr``,
the form in which the model file stores them, for example ``55.56``). The candidate's texts are
parsed again with every decimal literal replaced by the exact rational *before* SymPy combines
numbers, so that its floating-point folding cannot separate two functions equal under the rule.
Consequences: ``0.30000000000000001`` and ``0.3`` are different numbers under the rule, although
they are the same binary64 number; the comparison then reports established non-equivalence and
marks that the difference is below the resolution of binary64 (relative 2^-52). Conversely,
**proven equivalence** additionally requires that the binary64 evaluation of the candidate (as
the evaluator computes it) and of the reference agree at every sampled point within the
rounding bound 1e-12 · max(1, |r|); otherwise the comparison is unresolved, with the reason.

**Procedure per expression key.** Let ``f`` be the candidate's expression (ties resolved,
numbers as above) and ``r`` the reference expression.

1. *Symbolic stage* (in the worker process, under the task's symbolic time limit): the
   difference ``d = f − r`` is simplified with SymPy; ``d`` identically zero, together with the
   binary64 agreement above, is **proven equivalence** on the domain.
2. *Points*: ``f`` and ``r`` are evaluated with 30 significant digits at the corners and centre
   of the domain box and at the sampled points of step 3 with the largest binary64 differences; a
   point with ``d ≠ 0`` beyond the rounding margin, or where exactly one of ``f`` and ``r`` is not
   real and finite, **establishes non-equivalence** (the point is recorded).
3. *Numerical agreement* (a separate measurement, never a proof): ``|d|`` in binary64 at
   :data:`REFERENCE_SAMPLES` points drawn uniformly on the domain box with NumPy's
   ``default_rng(REFERENCE_SEED)``; the maximum and root-mean-square absolute difference, the
   number of points and the domain are reported.

Otherwise the comparison is **unresolved**. For several expression keys, the candidate is
equivalent when every key is proven equivalent and non-equivalent when any key is.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import sympy as sp

from ..task.schema import TaskSpec
from ..model.checks import Candidate
from ..task.expr import parse_task_expression
from .compiled import CompiledModel, added_lambdas, constant_values, symbols
from .sealed import Reference
from .symbolic import DEFAULT_TIME_LIMIT_S, run_job
from .symbolic_jobs import distinct

REFERENCE_SAMPLES = 2000
"""Number of sampled points of the numerical agreement."""

REFERENCE_SEED = 20260925
"""Seed of the sampled points of the numerical agreement."""

CONFIRMED_POINTS = 5
"""Number of sampled points with the largest differences re-evaluated at 30 digits."""

BINARY64_AGREEMENT = 1e-12
"""Relative bound of the binary64 agreement that proven equivalence also requires."""

NUMBERS_RULE = (
    "every number is the exact decimal number it is written as: literals of the candidate's expressions, tie "
    "equations and the reference text as written; parameter values and given constants in the shortest decimal "
    "form of their binary64 value; proven equivalence additionally requires binary64 agreement at every sampled "
    "point within 1e-12 * max(1, |reference|)"
)
"""The numbers rule of the comparison, stated in every report (module docstring)."""


_DECIMAL = re.compile(r"(?<![\w.])((?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?|\d+[eE][-+]?\d+)(?![\w.])")


def _exact(x: float) -> sp.Rational:
    """The exact rational of the shortest decimal form of the binary64 number ``x``."""
    return sp.Rational(repr(float(x)))


_ALIASES = re.compile(r"\b(abs|min|max)(\s*\()")
_ALIAS_NAMES = {"abs": "Abs", "min": "Min", "max": "Max"}


def _rational_text(text: str) -> str:
    """``text`` with every decimal literal written as an exact ``Rational`` and aliases spelled out."""
    text = _ALIASES.sub(lambda m: _ALIAS_NAMES[m.group(1)] + m.group(2), text)
    return _DECIMAL.sub(lambda m: f"Rational('{m.group(1)}')", text)


def exact_candidate(task: TaskSpec, candidate: Candidate) -> dict[str, sp.Expr]:
    """The candidate's expressions under the numbers rule of the module docstring.

    The expression texts and tie equations are parsed again with every decimal literal as an
    exact rational (the texts passed the restricted parser of the checks, so they contain only
    permitted names and constructs); tied parameters are replaced by their equations, then fitted
    and fixed parameters and given constants by the exact rationals of their shortest decimal form.
    """
    params = [p.name for p in candidate.parameters]
    names = list(task.argument_names) + params + list(task.constant_names)
    added = added_lambdas(task)
    ties = {
        sp.Symbol(p.name, real=True): parse_task_expression(_rational_text(p.equation), params + list(task.constant_names), task.functions, added=added)
        for p in candidate.parameters
        if p.type == "tied"
    }
    values = {sp.Symbol(n, real=True): _exact(v) for n, v in candidate.values.items() if n not in candidate.tied}
    values.update({sp.Symbol(c.name, real=True): _exact(c.value) for c in task.constants})
    out = {}
    for k, text in candidate.expression_texts.items():
        e = parse_task_expression(_rational_text(text), names, task.functions, added=added)
        for _ in range(len(ties) + 1):
            if not (e.free_symbols & set(ties)):
                break
            e = e.xreplace(ties)
        out[k] = e.xreplace(values)
    return out


def exact_reference(task: TaskSpec, text: str) -> sp.Expr:
    """The reference expression parsed with every decimal literal as an exact rational."""
    rational_text = _rational_text(text)
    names = list(task.argument_names) + list(task.constant_names)
    e = parse_task_expression(rational_text, names, task.functions, added=added_lambdas(task))
    return e.xreplace({sp.Symbol(c.name, real=True): _exact(c.value) for c in task.constants})


@dataclass
class ReferenceComparison:
    """The comparison of one candidate with the sealed reference."""

    outcome: str  # "proven_equivalence", "established_non_equivalence", "unresolved"
    per_key: dict[str, dict[str, Any]] = field(default_factory=dict)
    domain: dict[str, Any] | None = None
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Plain data for the JSON report (sealed: never shown to the agent)."""
        return {"outcome": self.outcome, "per_key": self.per_key, "domain": self.domain, "assumptions": list(self.assumptions)}


def compare_with_reference(task: TaskSpec, model: CompiledModel, ref: Reference, candidate: Candidate) -> ReferenceComparison:
    """Compare one candidate with the sealed reference expression (module docstring)."""
    tl = task.evaluation.symbolic_time_limit_s
    box = {v: (float(a), float(b)) for v, (a, b) in ref.domain["box"].items()}
    order = [a for a in task.argument_names if a in box]
    out = ReferenceComparison(
        outcome="unresolved",
        domain={"box": {v: [box[v][0], box[v][1]] for v in order}},
        assumptions=[
            "all variables are real and range over the reference domain",
            NUMBERS_RULE,
            "tied parameters are replaced by their tie equations",
        ],
    )
    consts = constant_values(task)
    f_exact = exact_candidate(task, candidate)
    outcomes = []
    for key in task.expression_keys:
        f = model.exprs[key]
        r = ref.parsed[key].xreplace(consts)
        d = f - r
        rec: dict[str, Any] = {"symbolic": None, "points_checked": 0}
        extra = sorted(str(s) for s in d.free_symbols if str(s) not in box)
        if extra:
            rec["outcome"] = "unresolved"
            rec["detail"] = f"the difference depends on {extra}, which the reference domain does not cover"
            out.per_key[key] = rec
            outcomes.append("unresolved")
            continue
        # numerical agreement (binary64, sampled points)
        rng = np.random.default_rng(REFERENCE_SEED)
        pts = {v: (rng.uniform(box[v][0], box[v][1], REFERENCE_SAMPLES) if box[v][0] != box[v][1] else np.full(REFERENCE_SAMPLES, box[v][0])) for v in order}
        fn = sp.lambdify(symbols(order), [f, r], modules="numpy")
        with np.errstate(all="ignore"):
            fv, rv = fn(*[pts[v] for v in order])
        fv = np.broadcast_to(np.asarray(fv, dtype=complex), (REFERENCE_SAMPLES,))
        rv = np.broadcast_to(np.asarray(rv, dtype=complex), (REFERENCE_SAMPLES,))
        diff = np.abs(fv - rv)
        ok = np.isfinite(diff) & (np.imag(fv) == 0) & (np.imag(rv) == 0)
        rec["numerical_agreement"] = {
            "points": REFERENCE_SAMPLES,
            "seed": REFERENCE_SEED,
            "procedure": f"uniform draws on the domain box with NumPy default_rng({REFERENCE_SEED}) (PCG64), variables in the order {', '.join(order)}; binary64 arithmetic",
            "points_with_finite_values": int(ok.sum()),
            "max_abs_difference": float(diff[ok].max()) if ok.any() else None,
            "rms_difference": float(np.sqrt(np.mean(diff[ok] ** 2))) if ok.any() else None,
            "note": "numerical agreement at sampled points; not a proof of equivalence",
        }
        # symbolic stage, exact numbers
        fe = f_exact[key]
        re_ = exact_reference(task, ref.expressions[key])
        jr = run_job("simplify", (fe - re_,), tl)
        rec["symbolic"] = {
            "procedure": "SymPy simplify of the difference, numbers as exact decimals",
            "time_limit_s": DEFAULT_TIME_LIMIT_S if tl is None else tl,
            "result": {"ok": "ok", "timeout": "time limit", "unavailable": "unavailable"}.get(jr.status, "error"),
        }
        if jr.status == "ok" and jr.value == 0:
            bound = BINARY64_AGREEMENT * np.maximum(1.0, np.abs(rv.real))
            f_def = np.isfinite(fv.real) & (np.imag(fv) == 0)
            r_def = np.isfinite(rv.real) & (np.imag(rv) == 0)
            both = f_def & r_def
            agree = bool(np.all(f_def == r_def)) and bool(np.all(np.abs(fv.real - rv.real)[both] <= bound[both]))
            if agree:
                rec["outcome"] = "proven_equivalence"
                rec["detail"] = "the difference simplifies to zero under the numbers rule, and the binary64 evaluations agree at every sampled point"
            else:
                rec["outcome"] = "unresolved"
                rec["detail"] = "the difference simplifies to zero under the numbers rule, but the binary64 evaluations differ beyond rounding at sampled points"
            out.per_key[key] = rec
            outcomes.append(rec["outcome"])
            continue
        # points at 30 digits: corners, centre, the largest sampled differences
        corners = [dict(zip(order, c)) for c in itertools.product(*[sorted({box[v][0], box[v][1]}) for v in order])][:64]
        centre = {v: 0.5 * (box[v][0] + box[v][1]) for v in order}
        score = np.where(ok, diff, np.inf)
        worst = [{v: float(pts[v][i]) for v in order} for i in np.argsort(-score, kind="stable")[:CONFIRMED_POINTS]]
        cand_pts = corners + [centre] + worst
        rec["points_checked"] = len(cand_pts)
        fr = run_job("point_values", (fe, cand_pts), tl)
        rr = run_job("point_values", (re_, cand_pts), tl)
        found = None
        if fr.status == "ok" and rr.status == "ok":
            for p, a, b in zip(cand_pts, fr.value, rr.value):
                if (a is None) != (b is None):
                    found = (p, a, b)
                    break
                if a is not None and distinct(a, b):
                    found = (p, a, b)
                    break
        if found is not None:
            p, a, b = found
            a = None if a is None else float(a)
            b = None if b is None else float(b)
            rec["outcome"] = "established_non_equivalence"
            rec["point"] = p
            rec["candidate_value"] = a
            rec["reference_value"] = b
            rec["below_binary64_resolution"] = bool(
                a is not None and b is not None and abs(a - b) <= 2.0**-52 * max(abs(a), abs(b))
            )
            rec["detail"] = (
                ("the difference is below the resolution of binary64 (relative 2^-52); " if rec["below_binary64_resolution"] else "")
                + f"at {p} the candidate is {'not real and finite' if a is None else repr(a)} and the reference "
                f"{'not real and finite' if b is None else repr(b)} (30 significant digits)"
            )
        else:
            rec["outcome"] = "unresolved"
            rec["detail"] = "the difference was not shown to be zero, and no point with a difference was found"
        out.per_key[key] = rec
        outcomes.append(rec["outcome"])
    if outcomes and all(o == "proven_equivalence" for o in outcomes):
        out.outcome = "proven_equivalence"
    elif any(o == "established_non_equivalence" for o in outcomes):
        out.outcome = "established_non_equivalence"
    return out
