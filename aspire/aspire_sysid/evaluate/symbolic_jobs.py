"""The symbolic jobs run by :mod:`aspire_sysid.evaluate.symbolic`.

Every job is a pure function of SymPy objects, numbers and strings, runs in the worker process
under a time limit, and returns plain data. The jobs are:

- :func:`bound_check`: whether a quantity ``q`` satisfies ``q ≤ tol`` on a box (proof,
  counterexample or inconclusive), by constant evaluation, interval arithmetic and SymPy;
- :func:`point_values`: values of an expression at given points, at 30 significant digits;
- :func:`simplify_expression`: SymPy's ``simplify``;
- :func:`limit_expression`: SymPy's ``limit``;
- :func:`sleep`: a job that only waits (tests of the time limit).

**Numbers.** Parameter values and the coordinates of points are binary64 numbers; they enter as
SymPy floats that hold them exactly, and values are computed with :data:`DIGITS` significant
digits. A comparison with the tolerance is decided only when the difference exceeds the rounding
margin (:func:`compare`); otherwise the result is inconclusive. Values are returned as SymPy
floats with 30 digits; reports convert them to binary64 numbers.
"""

from __future__ import annotations

from typing import Any

import sympy as sp
from sympy.calculus.util import maximum, minimum

DIGITS = 30
"""Significant digits of the evaluation of an expression at a point."""


def _margin(*values: sp.Float) -> sp.Float:
    return sp.Float("1e-20", DIGITS) * max([sp.Float(1, DIGITS)] + [abs(sp.Float(v, DIGITS)) for v in values])


def compare(v: sp.Float | float, tol: float) -> int:
    """Compare a value computed with :data:`DIGITS` digits with a tolerance (a binary64 number).

    Returns −1 when ``v < tol`` by more than the rounding margin ``1e-20 · max(1, |v|, |tol|)``,
    +1 when ``v > tol`` by more than the margin, and 0 otherwise (undecided).
    """
    V = sp.Float(v, DIGITS)
    T = sp.Float(tol, DIGITS)
    d = V - T
    m = _margin(V, T)
    return -1 if d < -m else (1 if d > m else 0)


def distinct(a: sp.Float | float, b: sp.Float | float) -> bool:
    """True when ``a`` and ``b`` differ by more than the rounding margin (see :func:`compare`)."""
    A, B = sp.Float(a, DIGITS), sp.Float(b, DIGITS)
    return abs(A - B) > _margin(A, B)


def evaluate_at(expr: sp.Expr, point: dict[str, float]) -> sp.Float | None:
    """``expr`` at ``point`` with :data:`DIGITS` digits; ``None`` if not real and finite."""
    sub = {s: sp.Float(point[str(s)], DIGITS) for s in expr.free_symbols if str(s) in point}
    try:
        v = sp.N(expr.xreplace(sub), DIGITS)
    except (TypeError, ValueError, ArithmeticError):
        return None
    if not isinstance(v, sp.Expr) or v.free_symbols or v.has(sp.nan, sp.zoo, sp.oo, -sp.oo):
        return None
    try:
        re_, im_ = v.as_real_imag()
        if im_ != 0 or not re_.is_number or not re_.is_finite:
            return None
        return sp.Float(re_, DIGITS)
    except (TypeError, ValueError, AttributeError):
        return None


def point_values(expr: sp.Expr, points: list[dict[str, float]]) -> list[sp.Float | None]:
    """Values of ``expr`` at ``points`` with :data:`DIGITS` digits (``None``: not real and finite)."""
    return [evaluate_at(expr, p) for p in points]


def simplify_expression(expr: sp.Expr) -> sp.Expr:
    """SymPy's ``simplify`` of ``expr``."""
    return sp.simplify(expr)


def limit_expression(expr: sp.Expr, var: str, approach: Any) -> sp.Expr:
    """SymPy's ``limit`` of ``expr`` as the real variable ``var`` approaches ``approach``.

    ``approach`` is a number or ``"oo"`` / ``"-oo"``; the limit is two-sided at a number.
    """
    s = sp.Symbol(var, real=True)
    a = {"oo": sp.oo, "-oo": -sp.oo}.get(approach, approach)
    a = a if isinstance(a, sp.Basic) else sp.Float(a, DIGITS)
    return sp.limit(expr, s, a, dir="+-") if a not in (sp.oo, -sp.oo) else sp.limit(expr, s, a)


def _center(box: dict[str, tuple[float, float]]) -> dict[str, float]:
    return {v: 0.5 * (lo + hi) for v, (lo, hi) in box.items()}


SIMPLE_OPS = 40
"""Largest operation count (SymPy ``count_ops``) for which SymPy's ``maximum`` is attempted."""


def _decide_constant(qs: sp.Expr, Q: sp.Expr, tol: float, where: dict[str, float], method: str) -> dict[str, Any]:
    if Q == 0:
        return {"outcome": "proof", "method": method, "bound": 0.0,
                "detail": "the quantity is identically zero on the domain"}
    v = evaluate_at(Q, {})
    if v is None:
        return {"outcome": "counterexample", "method": method, "point": where, "value": None,
                "detail": f"the quantity reduces to {sp.sstr(qs)}, which is not a real finite number"}
    c = compare(v, tol)
    v = float(v)
    if c < 0:
        return {"outcome": "proof", "method": method, "bound": v,
                "detail": f"the quantity reduces to the constant {v!r}, which does not exceed the tolerance {tol!r}"}
    if c > 0:
        return {"outcome": "counterexample", "method": method, "point": where, "value": v,
                "detail": f"the quantity reduces to the constant {v!r}, which exceeds the tolerance {tol!r} at every point of the domain"}
    return {"outcome": "inconclusive", "method": method,
            "detail": f"the constant {v!r} equals the tolerance within the rounding margin"}


def bound_check(
    q: sp.Expr, box: dict[str, tuple[float, float]], tol: float, absolute: bool, time_limit_s: float, defined: list[sp.Expr] | None = None
) -> dict[str, Any]:
    """Decide whether ``Q ≤ tol`` everywhere on ``box``.

    ``Q = |q|`` when ``absolute`` is true, else ``Q = q``. ``box`` maps each variable to a closed
    interval; degenerate intervals are substituted first. The procedure has three stages, each
    tried only when the previous one did not decide:

    1. *constant*: if ``Q`` has no free variable (after SymPy's automatic evaluation), it is
       evaluated with 30 digits and compared with ``tol``; an identically zero ``Q`` is a proof;
       a constant above the tolerance is a counterexample at every point (the box centre is
       reported);
    2. *interval arithmetic*: branch and bound with verified enclosures
       (:func:`aspire_sysid.evaluate.interval.branch_and_bound`, half of the time limit);
    3. *simplification*: SymPy's ``simplify``; a constant result is decided as in stage 1; with
       one free variable and at most :data:`SIMPLE_OPS` operations, SymPy's ``maximum`` (and
       ``minimum`` for ``|q|``) over the closed interval gives the supremum; a supremum at most
       ``tol`` is a proof; above ``tol``, the interval ends and the critical points found by
       ``solveset`` are evaluated, and a point with ``Q > tol`` is a counterexample.

    *Definedness.* Before the stages, the harness establishes by interval arithmetic
    (:func:`aspire_sysid.evaluate.interval.definedness`) that ``Q`` and every expression of
    ``defined`` (the target and the other expressions the requirement involves, before SymPy
    cancels anything, for example ``sqrt(x) − sqrt(x)``) are real and finite on the whole box. A
    point at which one of them is not real or not finite, confirmed with 30 digits, is a
    counterexample. A proof of any stage is accepted only when definedness on the whole box was
    established; otherwise the result is inconclusive.

    Otherwise the result is inconclusive. Returns ``{"outcome", "method", "detail"}`` and, for a
    counterexample, ``"point"`` and ``"value"`` (``None`` when ``Q`` is not real and finite there).
    """
    fixed = {v: lo for v, (lo, hi) in box.items() if lo == hi}
    sub = {sp.Symbol(v, real=True): sp.Float(x, DIGITS) for v, x in fixed.items()}
    free_box = {v: iv for v, iv in box.items() if v not in fixed}
    where = dict(fixed, **_center(free_box))
    q0 = q.xreplace(sub)
    Q0 = sp.Abs(q0) if absolute else q0
    exprs = [Q0] + [e.xreplace(sub) for e in (defined or [])]
    dres = _definedness(exprs, free_box, fixed, 0.25 * time_limit_s)
    if dres["outcome"] == "counterexample":
        return dres
    res = _stages(q0, Q0, tol, absolute, time_limit_s, fixed, free_box, where)
    if res["outcome"] == "proof" and dres["outcome"] != "defined":
        return {"outcome": "inconclusive", "method": res["method"],
                "detail": f"{res['detail']}; but the quantity was not shown to be real and finite on the whole domain ({dres['detail']}), so this is not a proof"}
    return res


def _definedness(exprs: list[sp.Expr], free_box: dict, fixed: dict, budget: float) -> dict[str, Any]:
    """Definedness of ``exprs`` on the box (see :func:`bound_check`)."""
    from .interval import definedness

    syms = set().union(*(e.free_symbols for e in exprs))
    box = {v: iv for v, iv in free_box.items() if sp.Symbol(v, real=True) in syms}
    if not box:
        for i, e in enumerate(exprs):
            if evaluate_at(e, {}) is None:
                return {"outcome": "counterexample", "method": "evaluation at the domain", "point": dict(fixed, **_center(free_box)), "value": None,
                        "detail": f"the expression {sp.sstr(e)} is not real and finite on the domain"}
        return {"outcome": "defined", "detail": "constant"}
    d = definedness(exprs, box, time_budget_s=budget)
    if d["outcome"] == "defined":
        return {"outcome": "defined", "detail": f"shown by interval arithmetic on {d['boxes']} sub-box(es)"}
    if d["outcome"] == "undefined":
        e = exprs[d["index"]]
        if evaluate_at(e, d["point"]) is None:
            return {"outcome": "counterexample", "method": "interval arithmetic (definedness)", "point": dict(fixed, **d["point"]), "value": None,
                    "detail": f"at {d['point']} the expression {sp.sstr(e)} is not real and finite (confirmed at 30 significant digits)"}
        return {"outcome": "unknown", "detail": "a possibly undefined point was not confirmed at 30 significant digits"}
    return {"outcome": "unknown", "detail": d.get("detail", d["outcome"])}


def _stages(q0, Q0, tol, absolute, time_limit_s, fixed, free_box, where) -> dict[str, Any]:
    """Stages 1 to 3 of :func:`bound_check`."""
    from .interval import branch_and_bound

    if not q0.free_symbols:
        return _decide_constant(q0, Q0, tol, where, "evaluation of a constant")
    notes = []
    bb_box = {v: iv for v, iv in free_box.items() if sp.Symbol(v, real=True) in q0.free_symbols}
    bb = branch_and_bound(Q0, bb_box, tol, time_budget_s=0.5 * time_limit_s)
    if bb["outcome"] == "proof":
        return {"outcome": "proof", "method": "interval arithmetic (branch and bound)",
                "detail": f"verified enclosures on {bb['boxes']} sub-box(es) covering the domain do not exceed the tolerance {tol!r}"}
    if bb["outcome"] == "counterexample":
        pt = dict(fixed, **bb["point"])
        val = evaluate_at(Q0, bb["point"])
        return {"outcome": "counterexample", "method": "interval arithmetic (branch and bound)", "point": pt, "value": None if val is None else float(val),
                "detail": f"on a sub-box around {bb['point']} the verified lower bound {bb['lower_bound']!r} of the quantity exceeds the tolerance {tol!r}"}
    notes.append(f"interval arithmetic: {bb.get('detail', bb['outcome'])}")
    qs = sp.simplify(q0)
    Q = sp.Abs(qs) if absolute else qs
    free = sorted(str(s) for s in qs.free_symbols)
    if not free:
        return _decide_constant(qs, Q, tol, where, "symbolic simplification")
    if len(free) == 1 and free[0] in free_box and sp.count_ops(qs) <= SIMPLE_OPS:
        name = free[0]
        x = sp.Symbol(name, real=True)
        lo, hi = free_box[name]
        ivl = sp.Interval(sp.Float(lo, DIGITS), sp.Float(hi, DIGITS))
        try:
            if absolute:
                sup = sp.Max(sp.Abs(maximum(qs, x, ivl)), sp.Abs(minimum(qs, x, ivl)))
            else:
                sup = maximum(qs, x, ivl)
        except (NotImplementedError, ValueError, TypeError) as exc:
            notes.append(f"SymPy could not determine the extremum over {name}: {exc}")
            sup = None
        s = None if sup is None else evaluate_at(sup, {})
        if s is not None and compare(s, tol) < 0:
            s = float(s)
            return {"outcome": "proof", "method": "SymPy maximum over the interval", "bound": s,
                    "detail": f"the supremum over {name} in [{lo!r}, {hi!r}] is {s!r}, which does not exceed the tolerance {tol!r}"}
        if s is not None and compare(s, tol) > 0:
            cands = [float(lo), float(hi)]
            try:
                crit = sp.solveset(sp.diff(qs, x), x, ivl)
                if isinstance(crit, sp.FiniteSet):
                    cands += [float(c) for c in crit if evaluate_at(c, {}) is not None]
            except Exception:  # noqa: BLE001 - critical points are optional
                pass
            best = None
            for c in cands:
                val = evaluate_at(Q, {name: c})
                if val is not None and (best is None or val > best[1]):
                    best = (c, val)
            if best is not None and compare(best[1], tol) > 0:
                return {"outcome": "counterexample", "method": "SymPy maximum over the interval", "point": dict(fixed, **{name: best[0]}),
                        "value": float(best[1]), "detail": f"the quantity is {float(best[1])!r} at {name} = {best[0]!r}, above the tolerance {tol!r}"}
            notes.append(f"the supremum is {float(s)!r}, but no point above the tolerance was located")
    else:
        notes.append(f"after simplification the quantity depends on {', '.join(free)} with {sp.count_ops(qs)} operations; no further symbolic procedure applies")
    return {"outcome": "inconclusive", "method": "interval arithmetic and symbolic simplification", "detail": "; ".join(notes)}


def sleep(seconds: float) -> float:
    """Wait ``seconds`` seconds and return them; used to test the time limit of the worker."""
    import time

    time.sleep(seconds)
    return seconds


JOBS = {
    "bound_check": bound_check,
    "point_values": point_values,
    "simplify": simplify_expression,
    "limit": limit_expression,
    "sleep": sleep,
}
"""Registry of the jobs by name."""
