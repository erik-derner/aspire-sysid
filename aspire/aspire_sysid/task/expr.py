"""Parsing of expressions written by the task author.

The task specification contains expressions of its own: the measurement equation ``h`` of
the measurement equation, the shift equations of a NARX task, the relations and equations of formal
requirements, the definitions of added functions and the sealed reference expression. They
are parsed here with SymPy over the declared names and the permitted functions only; an
unknown name or function is an error. The candidate expressions of the agent are parsed by the
restricted parser of ``aspire_sysid.model``, not by this module.
"""

from __future__ import annotations

from typing import Iterable

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations

_SYMPY_FUNCTIONS: dict[str, object] = {
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "atan2": sp.atan2,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "exp": sp.exp,
    "log": sp.log,
    "sqrt": sp.sqrt,
    "Abs": sp.Abs,
    "sign": sp.sign,
    "Min": sp.Min,
    "Max": sp.Max,
    "Piecewise": sp.Piecewise,
    "Eq": sp.Eq,
    "Ne": sp.Ne,
}
"""SymPy objects of the available functions (``Eq``/``Ne`` for conditions)."""


class ExpressionError(ValueError):
    """A task expression cannot be parsed or uses an undeclared name or function."""


def parse_task_expression(
    text: str,
    names: Iterable[str],
    functions: Iterable[str],
    *,
    added: dict[str, sp.Lambda] | None = None,
    allow_relational: bool = False,
) -> sp.Basic:
    """Parse ``text`` over the declared ``names`` and permitted ``functions``.

    ``names`` become real SymPy symbols; ``pi`` and ``E`` are the constants π and e. ``added``
    maps the names of added functions to their definitions. A relation (``<=`` and so on) is
    accepted only with ``allow_relational``. Raises :class:`ExpressionError`.
    """
    if not isinstance(text, str) or not text.strip():
        raise ExpressionError("expression is empty or not a string")
    names = list(names)
    local = {n: sp.Symbol(n, real=True) for n in names}
    glob: dict[str, object] = {
        "Symbol": sp.Symbol,
        "Integer": sp.Integer,
        "Float": sp.Float,
        "Rational": sp.Rational,
        "pi": sp.pi,
        "E": sp.E,
        "__builtins__": {},
    }
    for f in functions:
        if f in _SYMPY_FUNCTIONS:
            glob[f] = _SYMPY_FUNCTIONS[f]
    for cond in ("Eq", "Ne"):
        if "Piecewise" in functions:
            glob[cond] = _SYMPY_FUNCTIONS[cond]
    for name, lam in (added or {}).items():
        glob[name] = lam
    try:
        expr = parse_expr(text, local_dict=local, global_dict=glob, transformations=standard_transformations, evaluate=True)
    except Exception as exc:  # SyntaxError, TypeError (calling an unknown name), ...
        raise ExpressionError(f"cannot parse {text!r}: {exc}") from exc
    if not isinstance(expr, sp.Basic):
        raise ExpressionError(f"{text!r} is not an expression")
    is_rel = isinstance(expr, (sp.core.relational.Relational, sp.logic.boolalg.Boolean)) and not isinstance(
        expr, sp.Expr
    )
    if is_rel and not allow_relational:
        raise ExpressionError(f"{text!r} is a relation or condition where an expression is required")
    if allow_relational and not is_rel:
        raise ExpressionError(f"{text!r} is not a relation")
    allowed = set(local.values())
    unknown = sorted(str(s) for s in expr.free_symbols if s not in allowed)
    if unknown:
        raise ExpressionError(f"{text!r} uses undeclared name(s) {', '.join(unknown)}")
    undeclared_funcs = sorted(
        {type(f).__name__ for f in expr.atoms(sp.core.function.AppliedUndef)}
    )
    if undeclared_funcs:
        raise ExpressionError(f"{text!r} uses undeclared function(s) {', '.join(undeclared_funcs)}")
    return expr


def known_function_names() -> tuple[str, ...]:
    """Function names this parser can map to SymPy: """
    return tuple(n for n in _SYMPY_FUNCTIONS if n not in ("Eq", "Ne"))
