"""Numerical form of the candidate expressions and of the task's own expressions.

The expressions are over the declared variables, with parameters and given
constants; non-real or non-finite values are reported; tied parameters are determined by their
equations; the harness computes every prediction used in evaluation.

A candidate's expressions are evaluated with every tied parameter replaced by its resolved tie
equation and every parameter and given constant replaced by its recorded value
(:meth:`aspire_sysid.model.Candidate.numeric_expressions`, values inserted with 17 significant
digits, which reproduces each binary64 value exactly). SymPy's ``lambdify`` with the NumPy module
turns them into functions that accept scalars or arrays. A non-real intermediate result (square
root or logarithm of a negative number, a non-integer power of a negative number) and an
undefined ``Piecewise`` (no branch applies) yield NaN, which the evaluation reports as a
non-finite value.

These are the numerical semantics of rule E6 (:func:`aspire_sysid.model.checks.numeric_function`):
IEEE 754 doubles, intermediate overflow to ±inf without error, only the final value judged. The
evaluator uses NumPy under ``numpy.errstate(all="ignore")`` because it evaluates whole
trajectories at once; its verdicts (finite or not) agree with ``Candidate.numeric_function``, and
its values agree to rounding.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence

import numpy as np
import sympy as sp

from ..model.checks import Candidate
from ..task.expr import parse_task_expression
from ..task.schema import TaskSpec


def added_lambdas(task: TaskSpec) -> dict[str, sp.Lambda]:
    """SymPy ``Lambda`` objects of the task's added functions."""
    out: dict[str, sp.Lambda] = {}
    for a in task.added_functions:
        body = parse_task_expression(a.definition, a.arguments, task.functions)
        out[a.name] = sp.Lambda(tuple(sp.Symbol(x, real=True) for x in a.arguments), body)
    return out


def constant_values(task: TaskSpec) -> dict[sp.Symbol, sp.Float]:
    """The given constants as a substitution of real symbols by 17-digit floats."""
    return {sp.Symbol(c.name, real=True): sp.Float(c.value, 17) for c in task.constants}


def parse_task_text(task: TaskSpec, text: str, names: Iterable[str], *, relational: bool = False) -> sp.Basic:
    """Parse an expression written by the task author over ``names`` and the given constants.

 The
    given constants are substituted by their values.
    """
    names = list(dict.fromkeys(list(names) + list(task.constant_names)))
    expr = parse_task_expression(text, names, task.functions, added=added_lambdas(task), allow_relational=relational)
    return expr.xreplace(constant_values(task))


def symbols(names: Sequence[str]) -> list[sp.Symbol]:
    """Real SymPy symbols of ``names``, as used by the parsers."""
    return [sp.Symbol(n, real=True) for n in names]


def vector_function(args: Sequence[str], exprs: Sequence[sp.Expr]) -> Callable[..., list[Any]]:
    """``lambdify`` of several expressions over ``args`` with the NumPy module."""
    return sp.lambdify(symbols(args), list(exprs), modules="numpy")


def as_array(value: Any, n: int) -> np.ndarray:
    """``value`` (scalar or array) as a float vector of length ``n``; non-real values become NaN."""
    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        arr = np.asarray(value, dtype=complex)
        arr = np.where(np.imag(arr) == 0, np.real(arr), np.nan)
    return np.broadcast_to(arr, (n,)).astype(float, copy=True) if arr.ndim == 0 else arr.astype(float, copy=False)


class CompiledModel:
    """Numerical functions of one candidate and of the task's measurement equation.

    ``f(*arguments)`` returns the list of values of the expressions in
    the order of ``keys`` (the task's expression keys), with the arguments in the order of
    ``args`` (the task's argument names). For a dynamic task, ``h(*values)`` evaluates the
    measurement equation over ``h_args`` (the states, then the inputs).
    """

    def __init__(self, task: TaskSpec, candidate: Candidate):
        num = candidate.numeric_expressions(substitute_constants=True)
        self._setup(task, candidate.label, num)

    @classmethod
    def from_expressions(cls, task: TaskSpec, label: str, exprs: dict[str, sp.Expr]) -> "CompiledModel":
        """The numerical form of expressions that are already numeric (parameters and constants
        substituted), one per expression key of ``task``, over its argument symbols.

 Used for the requirement diagnostic of blind candidates: the expressions of a blind
        candidate, renamed to the described task's names, assessed against the described task's
        requirements (:mod:`aspire_sysid.evaluate.blind`).
        """
        self = cls.__new__(cls)
        self._setup(task, label, exprs)
        return self

    def _setup(self, task: TaskSpec, label: str, num: dict[str, sp.Expr]) -> None:
        self.task = task
        self.label = label
        self.args: tuple[str, ...] = tuple(task.argument_names)
        self.keys: tuple[str, ...] = tuple(task.expression_keys)
        self.exprs: dict[str, sp.Expr] = {k: num[k] for k in self.keys}
        self.f = vector_function(self.args, [self.exprs[k] for k in self.keys])
        if task.dynamics is not None:
            self.h_args: tuple[str, ...] = tuple(task.states) + tuple(task.inputs)
            self.h_expr = parse_task_text(task, task.dynamics.measurement, self.h_args)
            self.h = vector_function(self.h_args, [self.h_expr])
        else:
            self.h_args = ()
            self.h_expr = None
            self.h = None

    def evaluate(self, values: dict[str, np.ndarray], n: int) -> dict[str, np.ndarray]:
        """Every expression on the argument ``values`` (arrays of length ``n``)."""
        with np.errstate(all="ignore"):
            out = self.f(*[values[a] for a in self.args])
        return {k: as_array(v, n) for k, v in zip(self.keys, out)}

    def measure(self, values: dict[str, np.ndarray], n: int) -> np.ndarray:
        """The measurement equation ``ŷ = h(x, u)`` on arrays of length ``n``."""
        with np.errstate(all="ignore"):
            out = self.h(*[values[a] for a in self.h_args])
        return as_array(out[0], n)
