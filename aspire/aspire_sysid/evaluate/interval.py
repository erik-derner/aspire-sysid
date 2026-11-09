"""Verified bounds of a closed-form expression on a box by interval arithmetic.

 Interval arithmetic computes, for a box of variable values, an interval that is
guaranteed to contain every value of the expression on the box (Moore, Kearfott and Cloud,
*Introduction to Interval Analysis*, SIAM, 2009). If the upper end of that enclosure does not exceed the tolerance, the requirement ``Q ≤ tol``
holds on the whole box: this is a proof, not a sample. If the lower end exceeds the tolerance,
it is violated everywhere on the box. Otherwise the box is bisected along its widest
non-degenerate side (branch and bound), up to a box budget.

Implementation: the SymPy expression is compiled into nested closures over the interval context
``mpmath.iv`` with a working precision of :data:`PRECISION` bits. Arithmetic, integer powers,
``exp``, ``log``, ``sqrt``, ``sin``, ``cos``, ``tan``, the absolute value and ``atan2`` use the
outward-rounded operations of ``mpmath.iv``. The monotone functions ``atan``, ``asin``,
``acos``, ``sinh``, ``tanh`` and ``cosh`` (monotone on each side of 0) are evaluated at the ends
of the argument interval with ``mpmath`` at the same precision and widened outward by
:data:`WIDEN` relative, which exceeds their rounding error. ``sign``, ``Min``, ``Max`` and
``Piecewise`` (with conditions decided in three-valued logic: true, false, or undecided on the
box) are supported. A value that may be undefined on the box (logarithm or square root of a
possibly negative number, division by an interval containing zero, a ``Piecewise`` without an
applicable branch) makes that box undecided. Any other function makes the procedure
unavailable for the expression.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Callable

import mpmath
import sympy as sp
from mpmath import iv

PRECISION = 80
"""Working precision of the interval arithmetic, in bits."""

WIDEN = mpmath.mpf(2) ** -70
"""Relative outward widening of an end-point evaluation of a monotone function."""


class Unsupported(ValueError):
    """The expression contains a function without an interval extension."""


class Undefined(ArithmeticError):
    """The expression may be undefined (non-real) somewhere on the box."""


Interval = Any
Env = dict[str, Interval]


_TINY = mpmath.mpf(2) ** -1000


def _widen(lo, hi):
    a = mpmath.mpf(lo)
    b = mpmath.mpf(hi)
    return iv.mpf([a - abs(a) * WIDEN - _TINY, b + abs(b) * WIDEN + _TINY])


def _monotone(fn, increasing: bool = True, lo_dom=None, hi_dom=None):
    def g(x):
        a, b = x.a, x.b
        if (lo_dom is not None and a < lo_dom) or (hi_dom is not None and b > hi_dom):
            raise Undefined(fn.__name__)
        with mpmath.workprec(PRECISION):
            fa, fb = fn(mpmath.mpf(a)), fn(mpmath.mpf(b))
        return _widen(fa, fb) if increasing else _widen(fb, fa)

    return g


def _cosh(x):
    a, b = x.a, x.b
    with mpmath.workprec(PRECISION):
        ca, cb = mpmath.cosh(mpmath.mpf(a)), mpmath.cosh(mpmath.mpf(b))
    hi = max(ca, cb)
    lo = mpmath.mpf(1) if a <= 0 <= b else min(ca, cb)
    return _widen(lo, hi)


def _sqrt(x):
    if x.a < 0:
        raise Undefined("sqrt")
    return iv.sqrt(x)


def _log(x):
    if x.a <= 0:
        raise Undefined("log")
    return iv.log(x)


def _sign(x):
    lo = -1 if x.a < 0 else (0 if x.a == 0 else 1)
    hi = 1 if x.b > 0 else (0 if x.b == 0 else -1)
    return iv.mpf([lo, hi])


def _hull(parts):
    return iv.mpf([min(p.a for p in parts), max(p.b for p in parts)])


def _minmax(parts, take_min: bool):
    if take_min:
        return iv.mpf([min(p.a for p in parts), min(p.b for p in parts)])
    return iv.mpf([max(p.a for p in parts), max(p.b for p in parts)])


_UNARY: dict[type, Callable] = {
    sp.sin: iv.sin,
    sp.cos: iv.cos,
    sp.tan: iv.tan,
    sp.exp: iv.exp,
    sp.log: _log,
    sp.Abs: iv.fabs,
    sp.sign: _sign,
    sp.atan: _monotone(mpmath.atan),
    sp.asin: _monotone(mpmath.asin, lo_dom=-1, hi_dom=1),
    sp.acos: _monotone(mpmath.acos, increasing=False, lo_dom=-1, hi_dom=1),
    sp.sinh: _monotone(mpmath.sinh),
    sp.tanh: _monotone(mpmath.tanh),
    sp.cosh: _cosh,
}


def _number(e: sp.Expr) -> Interval:
    if e is sp.pi:
        return iv.pi
    if e is sp.E:
        return iv.e
    if isinstance(e, sp.Integer):
        return iv.mpf(int(e))
    if isinstance(e, sp.Rational):
        return iv.mpf(int(e.p)) / iv.mpf(int(e.q))
    if isinstance(e, sp.Float):
        return iv.mpf(mpmath.mpf(e._mpf_))
    raise Unsupported(f"number {e!r}")


def _pow(base: Interval, e: sp.Expr, ce):
    if e.is_Integer:
        n = int(e)
        if n >= 0:
            return base ** n
        if base.a <= 0 <= base.b:
            raise Undefined("division by an interval that contains zero")
        return iv.mpf(1) / (base ** (-n))
    if e == sp.Rational(1, 2):
        return _sqrt(base)
    if e == sp.Rational(-1, 2):
        s = _sqrt(base)
        if s.a <= 0:
            raise Undefined("division by an interval that contains zero")
        return iv.mpf(1) / s
    if base.a <= 0:
        raise Undefined("non-integer power of a possibly non-positive number")
    return iv.exp(ce * iv.log(base))


def _condition(c: sp.Basic) -> Callable[[Env], bool | None]:
    """Three-valued evaluation of a ``Piecewise`` condition on a box."""
    if c is sp.true:
        return lambda env: True
    if c is sp.false:
        return lambda env: False
    if isinstance(c, sp.And):
        parts = [_condition(a) for a in c.args]

        def f_and(env):
            vals = [p(env) for p in parts]
            if any(v is False for v in vals):
                return False
            return True if all(v is True for v in vals) else None

        return f_and
    if isinstance(c, sp.Or):
        parts = [_condition(a) for a in c.args]

        def f_or(env):
            vals = [p(env) for p in parts]
            if any(v is True for v in vals):
                return True
            return False if all(v is False for v in vals) else None

        return f_or
    if isinstance(c, sp.Not):
        inner = _condition(c.args[0])

        def f_not(env):
            v = inner(env)
            return None if v is None else (not v)

        return f_not
    if isinstance(c, sp.core.relational.Relational):
        d = compile_interval(c.lhs - c.rhs)
        kind = type(c)

        def f_rel(env):
            x = d(env)
            if kind is sp.StrictLessThan:
                return True if x.b < 0 else (False if x.a >= 0 else None)
            if kind is sp.LessThan:
                return True if x.b <= 0 else (False if x.a > 0 else None)
            if kind is sp.StrictGreaterThan:
                return True if x.a > 0 else (False if x.b <= 0 else None)
            if kind is sp.GreaterThan:
                return True if x.a >= 0 else (False if x.b < 0 else None)
            if kind is sp.Equality:
                return True if (x.a == 0 and x.b == 0) else (False if (x.a > 0 or x.b < 0) else None)
            if kind is sp.Unequality:
                return False if (x.a == 0 and x.b == 0) else (True if (x.a > 0 or x.b < 0) else None)
            raise Unsupported(f"relation {kind.__name__}")

        return f_rel
    raise Unsupported(f"condition {type(c).__name__}")


def compile_interval(e: sp.Basic) -> Callable[[Env], Interval]:
    """Compile ``e`` into a function from a box (variable → interval) to an enclosure."""
    if e.is_Number or e in (sp.pi, sp.E):
        v = _number(e)
        return lambda env: v
    if isinstance(e, sp.Symbol):
        name = str(e)
        return lambda env: env[name]
    if isinstance(e, sp.Add):
        parts = [compile_interval(a) for a in e.args]

        def f_add(env):
            s = parts[0](env)
            for p in parts[1:]:
                s = s + p(env)
            return s

        return f_add
    if isinstance(e, sp.Mul):
        parts = [compile_interval(a) for a in e.args]

        def f_mul(env):
            s = parts[0](env)
            for p in parts[1:]:
                s = s * p(env)
            return s

        return f_mul
    if isinstance(e, sp.Pow):
        b = compile_interval(e.base)
        ce = None if (e.exp.is_Integer or e.exp in (sp.Rational(1, 2), sp.Rational(-1, 2))) else compile_interval(e.exp)
        ex = e.exp
        return lambda env: _pow(b(env), ex, None if ce is None else ce(env))
    if isinstance(e, sp.Piecewise):
        branches = [(compile_interval(pc.expr), _condition(pc.cond)) for pc in e.args]

        def f_pw(env):
            parts = []
            for val, cond in branches:
                c = cond(env)
                if c is False:
                    continue
                parts.append(val(env))
                if c is True:
                    return _hull(parts)
            raise Undefined("Piecewise without an applicable branch on part of the box")

        return f_pw
    if isinstance(e, (sp.Min, sp.Max)):
        parts = [compile_interval(a) for a in e.args]
        take_min = isinstance(e, sp.Min)
        return lambda env: _minmax([p(env) for p in parts], take_min)
    if isinstance(e, sp.atan2):
        y, x = compile_interval(e.args[0]), compile_interval(e.args[1])

        def f_atan2(env):
            yy, xx = y(env), x(env)
            if xx.a <= 0 and yy.a <= 0 <= yy.b:
                return iv.mpf([-iv.pi.b, iv.pi.b])
            return iv.atan2(yy, xx)

        return f_atan2
    if isinstance(e, sp.DiracDelta):
        arg = compile_interval(e.args[0])

        def f_delta(env):
            a = arg(env)
            if a.a > 0 or a.b < 0:
                return iv.mpf(0)
            raise Undefined("Dirac delta at a possible jump")

        return f_delta
    fn = _UNARY.get(type(e)) if len(e.args) == 1 else None
    if fn is None:
        raise Unsupported(f"no interval extension for {type(e).__name__}")
    arg = compile_interval(e.args[0])
    return lambda env: fn(arg(env))


def branch_and_bound(
    q: sp.Expr, box: dict[str, tuple[float, float]], tol: float, *, max_boxes: int = 4000, time_budget_s: float = 5.0
) -> dict[str, Any]:
    """Decide ``q ≤ tol`` on ``box`` by interval branch and bound (module docstring).

    Returns ``{"outcome": "proof" | "counterexample" | "inconclusive", "boxes": n, ...}``; a
    counterexample carries ``point`` (the midpoint of a box on which the enclosure lies above
    the tolerance, or a midpoint whose own enclosure does) and ``lower_bound``.
    """
    iv.prec = PRECISION
    with mpmath.workprec(PRECISION):
        try:
            f = compile_interval(q)
        except Unsupported as exc:
            return {"outcome": "unsupported", "boxes": 0, "detail": str(exc)}
        names = list(box)
        start = {v: (mpmath.mpf(lo), mpmath.mpf(hi)) for v, (lo, hi) in box.items()}
        queue: deque = deque([start])
        n = 0
        t_end = time.monotonic() + time_budget_s
        undefined = 0
        worst_upper = None
        while queue:
            b = queue.popleft()
            n += 1
            env = {v: iv.mpf([lo, hi]) for v, (lo, hi) in b.items()}
            try:
                enc = f(env)
                ok = True
            except (Undefined, ZeroDivisionError, ValueError):
                ok = False
                undefined += 1
            if ok:
                if enc.b <= tol:
                    continue
                if enc.a > tol:
                    mid = {v: float((lo + hi) / 2) for v, (lo, hi) in b.items()}
                    return {"outcome": "counterexample", "boxes": n, "point": mid, "lower_bound": float(enc.a)}
                worst_upper = enc.b if worst_upper is None else max(worst_upper, enc.b)
            # midpoint test: a point enclosure above the tolerance is a counterexample
            mid = {v: (lo + hi) / 2 for v, (lo, hi) in b.items()}
            try:
                em = f({v: iv.mpf(x) for v, x in mid.items()})
                if em.a > tol:
                    return {"outcome": "counterexample", "boxes": n, "point": {v: float(x) for v, x in mid.items()}, "lower_bound": float(em.a)}
            except (Undefined, ZeroDivisionError, ValueError):
                pass
            if n + len(queue) >= max_boxes or time.monotonic() > t_end:
                return {"outcome": "inconclusive", "boxes": n, "undefined_boxes": undefined,
                        "detail": f"the box budget ({max_boxes} boxes or {time_budget_s:g} s) was exhausted before the bound was established"}
            widths = [(b[v][1] - b[v][0], v) for v in names]
            w, v = max(widths)
            if w == 0:
                return {"outcome": "inconclusive", "boxes": n, "undefined_boxes": undefined,
                        "detail": "the expression may be undefined or exceed the tolerance at a single point"}
            lo, hi = b[v]
            m = (lo + hi) / 2
            left, right = dict(b), dict(b)
            left[v] = (lo, m)
            right[v] = (m, hi)
            queue.append(left)
            queue.append(right)
        return {"outcome": "proof", "boxes": n}


def definedness(
    exprs: list[sp.Expr], box: dict[str, tuple[float, float]], *, max_boxes: int = 4000, time_budget_s: float = 2.0
) -> dict[str, Any]:
    """Whether every expression of ``exprs`` is real and finite on the whole ``box``.

    A requirement can be proven only where the quantity it bounds is
    defined. Branch and bound with verified enclosures: a sub-box is settled when every expression
    has a finite enclosure on it without a possibly undefined operation (module docstring);
    otherwise its midpoint is tested and the box is bisected. Returns ``{"outcome": "defined"}``;
    ``{"outcome": "undefined", "point", "index"}`` for a midpoint at which expression ``index``
    was found not real or not finite (to be confirmed at high precision by the caller);
    ``{"outcome": "unknown", "detail"}`` when the budget is exhausted; or ``"unsupported"``.
    """
    iv.prec = PRECISION
    with mpmath.workprec(PRECISION):
        try:
            fs = [compile_interval(e) for e in exprs]
        except Unsupported as exc:
            return {"outcome": "unsupported", "detail": str(exc)}
        names = list(box)
        queue: deque = deque([{v: (mpmath.mpf(lo), mpmath.mpf(hi)) for v, (lo, hi) in box.items()}])
        n = 0
        t_end = time.monotonic() + time_budget_s
        while queue:
            b = queue.popleft()
            n += 1
            env = {v: iv.mpf([lo, hi]) for v, (lo, hi) in b.items()}
            settled = True
            for f in fs:
                try:
                    enc = f(env)
                except (Undefined, ZeroDivisionError, ValueError):
                    settled = False
                    break
                if not (mpmath.isfinite(enc.a) and mpmath.isfinite(enc.b)):
                    settled = False
                    break
            if settled:
                continue
            mid = {v: (lo + hi) / 2 for v, (lo, hi) in b.items()}
            for i, f in enumerate(fs):
                try:
                    em = f({v: iv.mpf(x) for v, x in mid.items()})
                    bad = not (mpmath.isfinite(em.a) and mpmath.isfinite(em.b))
                except (Undefined, ZeroDivisionError, ValueError):
                    bad = True
                if bad:
                    return {"outcome": "undefined", "point": {v: float(x) for v, x in mid.items()}, "index": i, "boxes": n}
            if n + len(queue) >= max_boxes or time.monotonic() > t_end:
                return {"outcome": "unknown", "boxes": n,
                        "detail": f"the box budget ({max_boxes} boxes or {time_budget_s:g} s) was exhausted before the expressions were shown to be real and finite on the whole domain"}
            w, v = max((b[x][1] - b[x][0], x) for x in names) if names else (0, None)
            if w == 0:
                return {"outcome": "unknown", "boxes": n, "detail": "the expressions may be undefined at a point of the domain"}
            lo, hi = b[v]
            m = (lo + hi) / 2
            left, right = dict(b), dict(b)
            left[v] = (lo, m)
            right[v] = (m, hi)
            queue.append(left)
            queue.append(right)
        return {"outcome": "defined", "boxes": n}
