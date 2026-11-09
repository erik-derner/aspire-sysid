"""Assessment of the physical requirements of a task for one candidate.

Formal requirements are of nine types with target, variables, domain, tolerance and
verification procedure; a demonstrated violation excludes the model unless the user explicitly
allowed it; requirements stated in words are assessed by the human. Symbolic
verification comes first where the requirement permits it; proof, counterexample and inconclusive
calculation are distinguished; sampling is recorded with domain, procedure, sample count, seed and
tolerance; "no violation found at the sampled points" is not a proof; inconclusive and
unavailable assessments are unresolved.

**Reduction to one quantity.** Every formal requirement is reduced to a quantity ``Q`` over the
requirement's variables that must satisfy ``Q ≤ tol`` at every point of the domain, where ``tol``
is the requirement's tolerance (in the unit of ``Q``). With ``f`` the target expression (the
candidate's expression of the target key, parameters and given constants at their values, tied
parameters substituted through their equations; or the task's measurement equation when the
target is the output of a dynamic task):

========================= ==============================================================
type                      quantity ``Q``
========================= ==============================================================
symmetry                  ``|f(T(v)) − factor · f(v)|``
parity (even / odd)       ``|f(−v_F, v_R) ∓ f(v)|``, ``v_F`` the flipped variables
exact_value               ``|f(v) − value|`` at every declared point (or on a box)
inequality ``a ≤ b``      ``a − b`` (``a ≥ b``: ``b − a``; ``a = b``: ``|a − b|``); strict and
                          non-strict relations are treated alike under the tolerance, so
                          that with tolerance 0 equality satisfies ``a < b``
curvature convex/concave  ``−∂²f/∂x²`` / ``∂²f/∂x²``
monotonicity incr./decr.  ``−∂f/∂x`` / ``∂f/∂x``
limit                     ``|lim_{x→a} f − value|`` over the box of the other variables
equation                  ``|f − g|``, ``g`` the declared expression
relation_at_points        the relation over ``at1, at2, …`` (the target values at the
                          declared points) reduced as for ``inequality``
========================= ==============================================================

**Outcomes.** ``proof`` (``Q ≤ tol`` established), ``counterexample`` (a point of the domain with
``Q > tol``, or with ``f`` not real and finite, confirmed at 30 significant digits),
``inconclusive`` (neither established, for example after a symbolic time limit, when sampling
found no violation, or when a value equals the tolerance within the rounding margin
``1e-20 · max(1, |Q|, |tol|)`` of the 30-digit evaluation; a quantity that is exactly zero after
substitution, such as a product with zero, is compared exactly) and ``unavailable`` (the assessment could not be carried out, with the
reason). ``proof`` means *satisfied*, ``counterexample`` *violated*, the other two *unresolved*.
A counterexample excludes the candidate when the requirement's ``exclude_on_violation`` is true
(the default); when it is false, the violation is reported with the recorded user instruction
(the exception) and does not exclude.

**Procedures.** ``symbolic``: the symbolic stage only; ``sampling``: the sampling stage only;
``symbolic_then_sampling``: the sampling stage runs when the symbolic stage is inconclusive.
Requirements on declared points (``exact_value`` with points, ``relation_at_points``) are
decided by evaluating the closed-form target at the points with 30 significant digits, whatever
the declared procedure. The symbolic stage (:func:`aspire_sysid.evaluate.symbolic_jobs.bound_check`)
runs in the worker process of :mod:`aspire_sysid.evaluate.symbolic` under the task's
``symbolic_time_limit_s``. The sampling stage draws the declared number of points independently
and uniformly on each non-degenerate interval of the box with NumPy's ``default_rng(seed)``
(PCG64), variables in the requirement's order, evaluates ``Q`` in binary64 arithmetic, and
re-evaluates the five largest values at 30 digits; only a confirmed value above the tolerance is
a counterexample. Dirac delta terms, which appear when a sign or absolute value is
differentiated, are set to zero at the sampled points (which lie on a jump with probability
zero); a symbolic stage that meets them is inconclusive.

**Variables outside the requirement.** When the target depends on an argument that the
requirement does not list, that argument ranges over its declared column range (for a delayed
variable, the range of its source column); the assessment records this assumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import sympy as sp

from ..task.schema import NLRequirement, Requirement, TaskSpec
from .compiled import CompiledModel, parse_task_text, symbols
from .symbolic import DEFAULT_TIME_LIMIT_S, run_job
from .symbolic_jobs import compare

OUTCOMES = ("proof", "counterexample", "inconclusive", "unavailable")
"""Outcomes of a requirement assessment."""

STATUS = {"proof": "satisfied", "counterexample": "violated", "inconclusive": "unresolved", "unavailable": "unresolved"}
"""Status of each outcome: only a proof is satisfaction, only a counterexample a violation."""

CONFIRMED_POINTS = 5
"""Number of the largest sampled values re-evaluated at 30 digits before a violation is claimed."""

ASSUMPTIONS = (
    "all variables are real",
    "parameter values and given constants enter as their recorded binary64 values, exactly",
    "tied parameters are replaced by their resolved tie equations",
)
"""Assumptions recorded with every formal assessment."""


@dataclass
class RequirementResult:
    """The assessment of one requirement for one candidate.

    ``outcome`` is one of :data:`OUTCOMES` and ``status`` its reading (satisfied, violated,
    unresolved). ``excludes`` is true for a counterexample of a requirement whose
    ``exclude_on_violation`` is true. ``symbolic`` and ``sampling`` record the two stages when they
    ran; ``counterexample`` the point and the value of ``Q`` (``None`` when ``f`` is not real and
    finite there). A natural-language requirement has ``kind`` ``natural_language``, outcome
    ``unavailable`` and status ``unresolved``: the human assesses it.
    """

    id: str
    kind: str
    type: str
    target: str | None
    statement: str | None
    outcome: str
    detail: str
    verification: str | None = None
    quantity: str | None = None
    domain: dict[str, Any] | None = None
    tolerance: dict[str, Any] | None = None
    assumptions: list[str] = field(default_factory=list)
    symbolic: dict[str, Any] | None = None
    sampling: dict[str, Any] | None = None
    counterexample: dict[str, Any] | None = None
    exclude_on_violation: bool = False
    exception: dict[str, Any] | None = None
    source: dict[str, Any] | None = None

    @property
    def status(self) -> str:
        """``satisfied``, ``violated`` or ``unresolved``."""
        return STATUS[self.outcome]

    @property
    def excludes(self) -> bool:
        """True when this result excludes the candidate from ranking and recommendation."""
        return self.kind == "formal" and self.outcome == "counterexample" and self.exclude_on_violation

    def to_dict(self) -> dict[str, Any]:
        """Plain data for the JSON report (none of it is derived from sealed data)."""
        return {
            "id": self.id,
            "kind": self.kind,
            "type": self.type,
            "target": self.target,
            "statement": self.statement,
            "outcome": self.outcome,
            "status": self.status,
            "excludes": self.excludes,
            "detail": self.detail,
            "verification": self.verification,
            "quantity": self.quantity,
            "domain": self.domain,
            "tolerance": self.tolerance,
            "assumptions": list(self.assumptions),
            "symbolic": self.symbolic,
            "sampling": self.sampling,
            "counterexample": self.counterexample,
            "exclude_on_violation": self.exclude_on_violation,
            "exception": self.exception,
            "source": self.source,
        }


def _source(src) -> dict[str, Any] | None:
    if src is None:
        return None
    return {"stated_by": src.stated_by, "date": src.date, "note": src.note}


def natural_language_result(req: NLRequirement) -> RequirementResult:
    """A requirement stated in words: unresolved, assessed by the human."""
    return RequirementResult(
        id=req.id,
        kind="natural_language",
        type="natural_language",
        target=None,
        statement=req.text,
        outcome="unavailable",
        detail=(
            "stated in natural language: the harness does not assess it; the human assesses it, and the "
            "agent's assertion alone does not count as verification"
        ),
        source=_source(req.source),
    )


def _column_range(task: TaskSpec, name: str) -> tuple[float, float] | None:
    if name in task.column_names:
        return task.column(name).range
    if task.dynamics is not None:
        for d in task.dynamics.delays:
            if d.name == name:
                return task.column(d.variable).range
    return None


def _target(task: TaskSpec, model: CompiledModel, target: str) -> sp.Expr | None:
    if target in model.exprs:
        return model.exprs[target]
    if target == task.output and model.h_expr is not None:
        return model.h_expr
    return None


def _reduce_relation(rel: sp.Basic, sub: dict) -> tuple[sp.Expr | None, bool, str]:
    """``(Q, absolute, text)`` for a relation after substituting ``sub`` (see module table)."""
    lhs, rhs = rel.lhs.xreplace(sub), rel.rhs.xreplace(sub)
    if isinstance(rel, (sp.LessThan, sp.StrictLessThan)):
        return lhs - rhs, False, "lhs − rhs"
    if isinstance(rel, (sp.GreaterThan, sp.StrictGreaterThan)):
        return rhs - lhs, False, "rhs − lhs"
    if isinstance(rel, sp.Equality):
        return lhs - rhs, True, "|lhs − rhs|"
    return None, False, "a relation '!=' cannot be reduced to a bound"


def _numpy_function(names: list[str], q: sp.Expr):
    q = q.replace(lambda e: isinstance(e, sp.DiracDelta), lambda e: sp.Integer(0))
    return sp.lambdify(symbols(names), q, modules="numpy")


def _sample(q: sp.Expr, absolute: bool, box: dict[str, tuple[float, float]], order: list[str], tol: float,
            samples: int, seed: int, time_limit: float | None, defined: list[sp.Expr] = ()) -> dict[str, Any]:
    """The sampling stage; returns the sampling record with its ``outcome``.

    A sampled point where ``Q`` or one of ``defined`` is not real and finite ranks above every
    finite value and, once confirmed at 30 digits, is a counterexample."""
    free = [v for v in order if box[v][0] != box[v][1]]
    record: dict[str, Any] = {
        "procedure": (
            "independent uniform draws on each non-degenerate interval of the box with NumPy "
            f"default_rng({seed}) (PCG64), variables drawn in the order {', '.join(free) or '(none)'}; "
            "degenerate intervals fixed at their value; Q evaluated in binary64 arithmetic; the "
            f"{CONFIRMED_POINTS} largest values re-evaluated at 30 significant digits"
        ),
        "samples": int(samples),
        "seed": int(seed),
        "domain": {v: [box[v][0], box[v][1]] for v in order},
        "tolerance": tol,
    }
    rng = np.random.default_rng(seed)
    pts = {}
    for v in order:
        lo, hi = box[v]
        pts[v] = rng.uniform(lo, hi, size=samples) if lo != hi else np.full(samples, lo)
    Q = sp.Abs(q) if absolute else q
    try:
        f = _numpy_function(order, Q)
        with np.errstate(all="ignore"):
            vals = np.asarray(f(*[pts[v] for v in order]), dtype=complex)
        vals = np.broadcast_to(vals, (samples,))
        real = np.where((np.imag(vals) == 0) & np.isfinite(vals.real), vals.real, np.inf)
        for e in defined:
            fe = _numpy_function(order, e)
            with np.errstate(all="ignore"):
                ev = np.broadcast_to(np.asarray(fe(*[pts[v] for v in order]), dtype=complex), (samples,))
            real = np.where((np.imag(ev) == 0) & np.isfinite(ev.real), real, np.inf)
    except Exception as exc:  # noqa: BLE001
        record["outcome"] = "unavailable"
        record["detail"] = f"the quantity cannot be evaluated numerically: {type(exc).__name__}: {exc}"
        return record
    order_idx = np.argsort(-real, kind="stable")[:CONFIRMED_POINTS]
    worst = [{v: float(pts[v][i]) for v in order} for i in order_idx]
    finite = real[np.isfinite(real)]
    record["max_value"] = float(finite.max()) if finite.size else None
    record["non_finite_points"] = int(np.sum(~np.isfinite(real)))
    if real[order_idx[0]] <= tol:
        record["outcome"] = "inconclusive"
        record["argmax"] = worst[0]
        record["detail"] = (
            f"no violation found at the {samples} sampled points (largest value of Q {record['max_value']!r}, "
            f"tolerance {tol!r}); this is not a proof"
        )
        return record
    res = run_job("point_values", (Q, worst), time_limit)
    checks = [run_job("point_values", (e, worst), time_limit) for e in defined]
    if res.status != "ok" or any(c.status != "ok" for c in checks):
        record["outcome"] = "inconclusive"
        record["detail"] = f"a sampled value exceeds the tolerance, but its confirmation at 30 digits failed: {res.detail}"
        return record
    for j, (p, v) in enumerate(zip(worst, res.value)):
        if any(c.value[j] is None for c in checks):
            v = None
        if v is None or compare(v, tol) > 0:
            v = None if v is None else float(v)
            record["outcome"] = "counterexample"
            record["point"] = p
            record["value"] = v
            record["detail"] = (
                f"at the sampled point {p} the quantity is {'not real and finite' if v is None else repr(v)}, "
                f"above the tolerance {tol!r} (confirmed at 30 significant digits)"
            )
            return record
    record["outcome"] = "inconclusive"
    record["detail"] = "sampled values above the tolerance were not confirmed at 30 significant digits (rounding)"
    return record


def assess_requirement(task: TaskSpec, model: CompiledModel, req: Requirement) -> RequirementResult:
    """Assess one formal requirement for one candidate (module docstring)."""
    tl = task.evaluation.symbolic_time_limit_s
    tl_eff = DEFAULT_TIME_LIMIT_S if tl is None else tl
    res = RequirementResult(
        id=req.id,
        kind="formal",
        type=req.type,
        target=req.target,
        statement=req.statement,
        outcome="unavailable",
        detail="",
        verification=req.verification,
        domain=_domain_dict(req.domain),
        tolerance={"value": req.tolerance.value, "unit": req.tolerance.unit},
        assumptions=list(ASSUMPTIONS),
        exclude_on_violation=req.exclude_on_violation,
        exception=_source(req.exception),
        source=_source(req.source),
    )
    tol = float(req.tolerance.value)
    f = _target(task, model, req.target)
    if f is None:
        res.detail = f"the target {req.target!r} is neither an expression key nor the output"
        return res
    p = req.params
    args = list(task.argument_names)
    sym = {a: sp.Symbol(a, real=True) for a in args}

    # --- requirements on declared points --------------------------------------------------
    if "points" in req.domain:
        pts = req.domain["points"]
        missing = sorted(str(s) for s in f.free_symbols if str(s) not in pts[0])
        if missing:
            res.detail = f"the target depends on {missing}, which the declared points do not fix"
            return res
        res.symbolic = {"procedure": "evaluation of the closed-form target at the declared points with 30 significant digits",
                        "time_limit_s": tl_eff}
        vr = run_job("point_values", (f, pts), tl)
        if vr.status != "ok":
            res.outcome = "inconclusive"
            res.detail = vr.detail
            res.symbolic["result"] = vr.status
            return res
        values = vr.value
        if req.type == "exact_value":
            res.quantity = "|f − value| at each declared point"
            qs = [None if v is None else abs(v - sp.Float(p["value"], 30)) for v in values]
            worst = None
            for pt, v, q in zip(pts, values, qs):
                if q is None or compare(q, tol) > 0:
                    res.outcome = "counterexample"
                    res.counterexample = {"point": pt, "value": None if q is None else float(q), "target_value": None if v is None else float(v)}
                    res.detail = (f"at {pt} the target is {'not real and finite' if v is None else repr(float(v))}; "
                                  f"|f − {p['value']!r}| exceeds the tolerance {tol!r}")
                    res.symbolic["result"] = "counterexample"
                    return res
                worst = float(q) if worst is None else max(worst, float(q))
            exact = [f.xreplace({sp.Symbol(k, real=True): sp.Float(v, 30) for k, v in pt.items()}) - sp.Float(p["value"], 30) == 0 for pt in pts]
            if all(compare(q, tol) < 0 or ex for q, ex in zip(qs, exact)):
                res.outcome = "proof"
                res.detail = f"|f − {p['value']!r}| ≤ {worst!r} at every declared point, within the tolerance {tol!r}"
            else:
                res.outcome = "inconclusive"
                res.detail = "a value equals the tolerance within the rounding margin"
            res.symbolic["result"] = res.outcome
            return res
        # relation_at_points
        if any(v is None for v in values):
            bad = [pt for pt, v in zip(pts, values) if v is None]
            res.outcome = "counterexample"
            res.counterexample = {"point": bad[0], "value": None}
            res.detail = f"the target is not real and finite at {bad[0]}"
            res.symbolic["result"] = "counterexample"
            return res
        ph = [f"at{j + 1}" for j in range(len(pts))]
        rel = parse_task_text(task, p["relation"], ph, relational=True)
        q, absolute, text = _reduce_relation(rel, {sp.Symbol(n, real=True): sp.Float(v, 30) for n, v in zip(ph, values)})
        res.quantity = f"{text} of the relation {p['relation']!r} with at_j the target values at the declared points"
        if q is None:
            res.detail = text
            return res
        qf = sp.N(abs(q) if absolute else q, 30)
        qv = float(qf)
        fvalues = [float(v) for v in values]
        res.symbolic["result"] = "evaluated"
        res.symbolic["target_values"] = fvalues
        c = compare(qf, tol)
        if c < 0:
            res.outcome, res.detail = "proof", f"Q = {qv!r} ≤ tolerance {tol!r} (target values {fvalues})"
        elif c > 0:
            res.outcome, res.detail = "counterexample", f"Q = {qv!r} > tolerance {tol!r} (target values {fvalues})"
            res.counterexample = {"point": pts, "value": qv}
        else:
            res.outcome, res.detail = "inconclusive", "Q equals the tolerance within the rounding margin"
        return res

    # --- requirements on a box --------------------------------------------------------------
    box = {v: (float(a), float(b)) for v, (a, b) in req.domain["box"].items()}
    extra = [str(s) for s in f.free_symbols if str(s) not in box and str(s) != p.get("variable")]
    for name in sorted(extra, key=lambda n: (args.index(n) if n in args else len(args), n)):
        rng_ = _column_range(task, name)
        if rng_ is None:
            res.detail = f"the target depends on {name}, which the requirement does not list and which has no declared range"
            return res
        box[name] = (float(rng_[0]), float(rng_[1]))
        res.assumptions.append(f"{name}, not listed by the requirement, ranges over its declared column range [{rng_[0]!r}, {rng_[1]!r}]")
    res.domain = {"box": {v: [lo, hi] for v, (lo, hi) in box.items()}}
    order = [v for v in args if v in box]
    absolute = False
    quantity: sp.Expr | None = None
    defined: list[sp.Expr] = [f]
    if req.type == "symmetry":
        tr = {sym[v]: parse_task_text(task, e, args) for v, e in p["transform"].items()}
        quantity, absolute = f.xreplace(tr) - int(p["factor"]) * f, True
        defined = [f, f.xreplace(tr)]
        res.quantity = f"|f(T(v)) − ({p['factor']})·f(v)| with T = {p['transform']}"
    elif req.type == "parity":
        flip = {sym[v]: -sym[v] for v in p["flip"]}
        sign = 1 if p["parity"] == "even" else -1
        quantity, absolute = f.xreplace(flip) - sign * f, True
        defined = [f, f.xreplace(flip)]
        res.quantity = f"|f(−v) − ({sign})·f(v)|, v flipped: {', '.join(p['flip'])}"
    elif req.type in ("equation", "exact_value"):
        g = parse_task_text(task, p["equals"], args) if req.type == "equation" else sp.Float(p["value"], 30)
        quantity, absolute = f - g, True
        defined = [f, g]
        res.quantity = f"|f − ({p.get('equals', p.get('value'))})|"
    elif req.type == "inequality":
        rel = parse_task_text(task, p["relation"], args + [req.target], relational=True)
        quantity, absolute, text = _reduce_relation(rel, {sp.Symbol(req.target, real=True): f})
        tsub = {sp.Symbol(req.target, real=True): f}
        defined = [f, rel.lhs.xreplace(tsub), rel.rhs.xreplace(tsub)]
        res.quantity = f"{text} of the relation {p['relation']!r} with {req.target} = f"
        if quantity is None:
            res.detail = text
            return res
    elif req.type in ("monotonicity", "curvature"):
        x = sym[p["variable"]]
        order_d = 1 if req.type == "monotonicity" else 2
        d = sp.diff(f, x, order_d)
        positive = p.get("direction") == "increasing" or p.get("sign") == "convex"
        quantity = -d if positive else d
        defined = [f, d]
        what = "∂f/∂" if order_d == 1 else "∂²f/∂"
        res.quantity = f"{'−' if positive else ''}{what}{p['variable']}{'²' if order_d == 2 else ''} (analytic derivative)"
    elif req.type == "limit":
        return _assess_limit(task, f, req, res, box, order, tol, tl, tl_eff)
    else:  # pragma: no cover - the loader admits only the nine types
        res.detail = f"unknown requirement type {req.type!r}"
        return res
    return _bound(res, quantity, absolute, box, order, tol, req, tl, tl_eff, defined)


def _domain_dict(domain: dict[str, Any]) -> dict[str, Any]:
    if "box" in domain:
        return {"box": {v: [float(a), float(b)] for v, (a, b) in domain["box"].items()}}
    return {"points": [dict(pt) for pt in domain["points"]]}


def _bound(res: RequirementResult, quantity: sp.Expr, absolute: bool, box, order, tol, req, tl, tl_eff, defined: list[sp.Expr]) -> RequirementResult:
    """Run the symbolic and sampling stages on ``Q ≤ tol`` over ``box``.

    ``defined`` are the expressions that must be real and finite on the box (the target and the
    other expressions of the requirement, before any cancellation); a point where one of them is
    not is a counterexample, and no proof is accepted unless they are shown to be defined."""
    if req.verification in ("symbolic", "symbolic_then_sampling"):
        if quantity.has(sp.DiracDelta):
            res.symbolic = {"procedure": "none", "time_limit_s": tl_eff, "result": "inconclusive",
                            "detail": "the quantity contains Dirac delta terms (a derivative at a jump)"}
        else:
            jr = run_job("bound_check", (quantity, box, tol, absolute, tl_eff, defined), tl)
            if jr.status == "ok":
                res.symbolic = {"procedure": jr.value["method"], "time_limit_s": tl_eff, "result": jr.value["outcome"], "detail": jr.value["detail"]}
                if jr.value["outcome"] == "proof":
                    res.outcome, res.detail = "proof", jr.value["detail"]
                    return res
                if jr.value["outcome"] == "counterexample":
                    res.outcome, res.detail = "counterexample", jr.value["detail"]
                    res.counterexample = {"point": jr.value["point"], "value": jr.value["value"]}
                    return res
            else:
                res.symbolic = {"procedure": "SymPy simplification and extremum", "time_limit_s": tl_eff,
                                "result": {"timeout": "time limit", "unavailable": "unavailable"}.get(jr.status, "error"),
                                "detail": jr.detail.splitlines()[0] if jr.detail else ""}
        if req.verification == "symbolic":
            if res.symbolic.get("result") == "unavailable":
                res.outcome = "unavailable"
                res.detail = f"the symbolic verification could not be run: {res.symbolic.get('detail', '')}"
                return res
            res.outcome = "inconclusive"
            res.detail = f"the symbolic verification was inconclusive: {res.symbolic.get('detail', '')}"
            return res
    s = req.params.get("sampling")
    if not s:
        res.outcome = "unavailable"
        res.detail = "no sampling settings are declared"
        return res
    rec = _sample(quantity, absolute, box, order, tol, int(s["samples"]), int(s["seed"]), tl, defined)
    res.sampling = {k: v for k, v in rec.items() if k not in ("outcome", "point", "value")}
    res.outcome = rec["outcome"]
    res.detail = rec["detail"]
    if rec["outcome"] == "counterexample":
        res.counterexample = {"point": rec["point"], "value": rec["value"]}
    return res


def _assess_limit(task, f, req, res, box, order, tol, tl, tl_eff) -> RequirementResult:
    """The limit type: symbolic limit, then the bound on ``|L − value|``."""
    p = req.params
    var = p["variable"]
    res.quantity = f"|lim_{{{var}→{p['approach']}}} f − {p['value']!r}|"
    if req.verification == "sampling":
        res.detail = "a limit cannot be verified by sampling; declare a symbolic verification"
        return res
    jr = run_job("limit", (f, var, p["approach"]), tl)
    res.symbolic = {"procedure": "SymPy limit", "time_limit_s": tl_eff,
                    "result": "ok" if jr.status == "ok" else ("time limit" if jr.status == "timeout" else "error")}
    if jr.status != "ok":
        res.outcome = "inconclusive"
        res.detail = f"the symbolic limit could not be computed ({jr.detail.splitlines()[0] if jr.detail else jr.status}); a numerical approximation of a limit is not a verification"
        return res
    L = jr.value
    res.symbolic["limit"] = sp.sstr(L)
    if L.has(sp.oo, -sp.oo, sp.zoo, sp.nan) or isinstance(L, sp.AccumBounds) or L.has(sp.AccumBounds):
        res.outcome = "counterexample"
        res.detail = f"the limit is {sp.sstr(L)}, not the finite value {p['value']!r}"
        res.counterexample = {"point": {var: p["approach"]}, "value": None, "limit": sp.sstr(L)}
        return res
    L_box = {v: box[v] for v in order if v != var and v in box}
    sub_req = Requirement(**{**req.__dict__, "verification": "symbolic_then_sampling" if "sampling" in p else "symbolic"})
    limit_record = dict(res.symbolic)
    res = _bound(res, L - sp.Float(p["value"], 30), True, L_box, [v for v in order if v in L_box], tol, sub_req, tl, tl_eff, [L])
    res.symbolic = {**limit_record, "bound_on_limit": res.symbolic}
    return res


def failed_requirement_result(req: Requirement, error: str) -> RequirementResult:
    """A formal requirement whose assessment raised: unavailable, hence unresolved."""
    return RequirementResult(
        id=req.id,
        kind="formal",
        type=req.type,
        target=req.target,
        statement=req.statement,
        outcome="unavailable",
        detail=f"the assessment failed with an error: {error}",
        verification=req.verification,
        domain=_domain_dict(req.domain),
        tolerance={"value": req.tolerance.value, "unit": req.tolerance.unit},
        exclude_on_violation=req.exclude_on_violation,
        exception=_source(req.exception),
        source=_source(req.source),
    )


def unavailable_requirements(task: TaskSpec, error: str) -> list[RequirementResult]:
    """Every requirement of ``task`` as unavailable with ``error``.

    Used when the requirement stage of a candidate fails as a whole, so that the candidate carries
    every requirement as unresolved rather than none.
    """
    out = [failed_requirement_result(r, error) for r in task.requirements]
    out += [natural_language_result(r) for r in task.requirements_nl]
    return out


def assess_requirements(task: TaskSpec, model: CompiledModel) -> list[RequirementResult]:
    """Assess every formal and natural-language requirement of ``task`` for one candidate.

 Formal requirements come first, in declared order, then the requirements
    stated in natural language (unresolved, assessed by the human). An error in the assessment of
    one requirement makes that requirement unavailable (unresolved), with the error recorded; the
    others are assessed.
    """
    out = []
    for r in task.requirements:
        try:
            out.append(assess_requirement(task, model, r))
        except Exception as exc:  # noqa: BLE001 - recorded as unavailable, never propagated
            out.append(failed_requirement_result(r, f"{type(exc).__name__}: {exc}"))
    out += [natural_language_result(r) for r in task.requirements_nl]
    return out
