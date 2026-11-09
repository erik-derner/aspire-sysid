"""Complexity of a candidate and the distinct model structures of a pool.

The number of independently fitted parameters, the number of non-integer numeric
literals, the expression-tree node count under a stated counting convention, and the number of
distinct model structures in the pool under a documented comparison that omits fitted values
while preserving fixed constants and repeated uses of a single parameter.

**Node count convention.** The count is taken on the candidate's expressions as SymPy represents
them after parsing (:attr:`aspire_sysid.model.Candidate.expressions`: parameters, tied
parameters and given constants as symbols; SymPy's automatic evaluation applied), summed over
the expression keys. Every node of the expression tree counts once: each operator (``Add``,
``Mul``, ``Pow``), each function application (``sin``, ``Abs``, ``Piecewise``, ...), each
relational or logical node of a ``Piecewise`` condition, each symbol (variable, parameter,
given constant) and each number, including π and e. The pairs ``(value, condition)`` inside
``Piecewise`` are containers and do not count. In SymPy's canonical form a subtraction ``a − b``
is ``Add(a, Mul(−1, b))`` and a division ``a / b`` is ``Mul(a, Pow(b, −1))``, so the count
includes the numbers −1 of these forms. Example: ``a*x + b`` has 5 nodes (``Add``, ``Mul``,
``a``, ``x``, ``b``).

**Structure comparison.** The structure of a candidate is formed from its expressions with every
tied parameter replaced by its resolved tie equation (:meth:`Candidate.resolved_expressions`),
every fixed parameter replaced by its value, the given constants kept as symbols, and the fitted
parameters as symbols; the displayed form renames the fitted parameters ``P1, …, Pn`` in the
order of their first occurrence in a preorder traversal of SymPy's canonical form of the
expressions, in the task's key order (``a*x + b`` is ``Add(b, Mul(a, x))`` and displays as
``P1 + P2*x``). Two candidates have the same structure when their structures have the same expression
keys and there is a one-to-one renaming of the fitted parameters of one onto those of the other
that makes every expression identical in SymPy's canonical form. A repeated use of one parameter
is preserved (``P1*x + P1*y`` differs from ``P1*x + P2*y``); fixed values are compared exactly;
a sign absorbed into a fitted parameter is a different structure (``P1*x`` differs from
``−P1*x``). The search over renamings is exhaustive up to :data:`MAX_PERMUTATIONS` renamings;
beyond that, the first-occurrence renaming alone is compared, which may count two equal
structures as distinct (the count is then an upper bound; the report says so).
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Iterable

import sympy as sp

from ..model.checks import Candidate

MAX_PERMUTATIONS = 40320
"""Largest number of parameter renamings tried when two structures are compared (8!)."""


def node_count(expr: sp.Basic) -> int:
    """Expression-tree node count under the convention of the module docstring."""
    n = 0
    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.functions.elementary.piecewise.ExprCondPair):
            continue
        n += 1
    return n


@dataclass(frozen=True)
class Complexity:
    """Complexity of one candidate."""

    fitted_parameters: int
    fixed_parameters: int
    tied_parameters: int
    noninteger_literals: int
    node_count: int
    node_count_per_key: dict[str, int]

    def to_dict(self) -> dict:
        """Plain data for the JSON report."""
        return {
            "fitted_parameters": self.fitted_parameters,
            "fixed_parameters": self.fixed_parameters,
            "tied_parameters": self.tied_parameters,
            "noninteger_literals": self.noninteger_literals,
            "node_count": self.node_count,
            "node_count_per_key": dict(self.node_count_per_key),
        }


def complexity(candidate: Candidate, keys: Iterable[str]) -> Complexity:
    """The complexity measures for one candidate (module docstring)."""
    per = {k: node_count(candidate.expressions[k]) for k in keys}
    return Complexity(
        fitted_parameters=len(candidate.fitted),
        fixed_parameters=len(candidate.fixed),
        tied_parameters=len(candidate.tied),
        noninteger_literals=candidate.total_noninteger_literals,
        node_count=sum(per.values()),
        node_count_per_key=per,
    )


@dataclass(frozen=True)
class Structure:
    """The structure of one candidate (module docstring)."""

    label: str
    keys: tuple[str, ...]
    exprs: tuple[sp.Expr, ...]
    fitted: tuple[sp.Symbol, ...]
    display: dict[str, str]


def _preorder(e: sp.Basic):
    """Pre-order traversal through ``.args``, whose order SymPy fixes for every node.

    ``sympy.preorder_traversal`` visits the arguments of ``Min`` and ``Max`` in the order of their
    internal set, which depends on the string hash seed of the Python process; the numbering of the
    fitted parameters would then differ between processes, and a report recomputed from a run record
    in another process would differ from the stored one.
    """
    stack = [e]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node.args))


def structure(candidate: Candidate, keys: Iterable[str]) -> Structure:
    """The structure of ``candidate`` (module docstring)."""
    keys = tuple(keys)
    resolved = candidate.resolved_expressions()
    fixed = {sp.Symbol(n, real=True): sp.Float(candidate.values[n], 17) for n in candidate.fixed}
    exprs = tuple(resolved[k].xreplace(fixed) for k in keys)
    fitted_syms = {sp.Symbol(n, real=True) for n in candidate.fitted}
    order: list[sp.Symbol] = []
    for e in exprs:
        for node in _preorder(e):
            if node in fitted_syms and node not in order:
                order.append(node)
    ren = {s: sp.Symbol(f"P{i + 1}", real=True) for i, s in enumerate(order)}
    display = {k: sp.sstr(e.xreplace(ren)) for k, e in zip(keys, exprs)}
    return Structure(candidate.label, keys, exprs, tuple(order), display)


def _skeleton(s: Structure) -> tuple:
    q = sp.Symbol("Q_fitted", real=True)
    return (s.keys, len(s.fitted), tuple(sp.srepr(e.xreplace({p: q for p in s.fitted})) for e in s.exprs))


def same_structure(a: Structure, b: Structure) -> tuple[bool, bool]:
    """``(equal, exhaustive)``: whether ``a`` and ``b`` have the same structure (module docstring).

    ``exhaustive`` is false when the renaming search was cut at :data:`MAX_PERMUTATIONS`.
    """
    if _skeleton(a) != _skeleton(b):
        return False, True
    n = len(a.fitted)
    exhaustive = math.factorial(n) <= MAX_PERMUTATIONS
    perms = itertools.permutations(b.fitted) if exhaustive else [b.fitted]
    for perm in perms:
        ren = dict(zip(a.fitted, perm))
        if all(ea.xreplace(ren) == eb for ea, eb in zip(a.exprs, b.exprs)):
            return True, exhaustive
    return False, exhaustive


def distinct_structures(structures: list[Structure]) -> tuple[list[list[str]], bool]:
    """Group candidates with the same structure.

    Returns the groups of labels (in pool order, each group in pool order) and whether every
    comparison was exhaustive (otherwise the number of groups is an upper bound).
    """
    groups: list[list[Structure]] = []
    exhaustive = True
    for s in structures:
        for g in groups:
            eq, ex = same_structure(g[0], s)
            exhaustive = exhaustive and ex
            if eq:
                g.append(s)
                break
        else:
            groups.append([s])
    return [[s.label for s in g] for g in groups], exhaustive
