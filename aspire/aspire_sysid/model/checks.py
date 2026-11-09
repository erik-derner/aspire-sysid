"""File and expression checks of ASPIRE candidate files (check_submission.py).

The checking script in the working directory: permitted expressions and the
file and expression checks, candidate contents (expressions, parameter table with fitted,
fixed and tied parameters, estimation record), four-section discussion, answers to the
discussion questions, recommendation, count of non-integer numeric literals,
model file content and default permitted functions; rules F1 to P1.

This module exists once. The harness imports it as
``aspire_sysid.model.checks``, and the working directory of every run receives a byte-identical
copy named ``check_submission.py``. It therefore depends only on the Python standard library and
SymPy and imports nothing else of the harness. Run in a working directory, it reads
``check_config.json`` (the task information that the brief also shows), the model files in
``models/`` and the training data ``data/train.csv``, prints one report per candidate with the
rule identifiers, and ends with a summary line:

    python check_submission.py            # in the working directory
    python check_submission.py <folder>   # a working directory elsewhere

The exit status is 0 when the pool file is valid and at least one candidate within the pool
limit passes every check, and 1 otherwise; 2 means that the configuration or the training data
could not be read. The harness calls the same functions in-process, with the configuration built
from the task specification and the training data read from the task store, so that an edited
copy of the configuration in the working directory has no effect on the harness's checks.

Expressions are parsed without executing arbitrary Python: the text must pass a character
whitelist and a length bound; Python's parser turns it into a syntax tree without executing it;
the tree may contain only numbers, the declared names, calls of the permitted functions, the
arithmetic operators ``+ - * / **``, and inside ``Piecewise`` conditions the comparisons
``< <= > >=``, ``Eq``, ``Ne`` and the logical operators ``& | ~``. The SymPy expression is then
built node by node from the admitted tree, with SymPy's automatic evaluation (the canonical
form, :func:`parse_expression`) and structural bounds on every node, so that no expression can
exhaust time or memory. Numerical values follow the IEEE 754 double
semantics of :func:`numeric_function`, which the evaluation of the harness shares.
"""

from __future__ import annotations

import ast
import csv
import json
import keyword
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

import sympy as sp

# ---------------------------------------------------------------------------------------------
# Constants of the file format
# ---------------------------------------------------------------------------------------------

FORMAT_VERSION = 2
"""Version of the model file format. Model files and the pool file do not state it; the
configuration file and the records do."""

CONFIG_FILE = "check_config.json"
"""Name of the configuration file in the working directory."""

MODELS_DIR = "models"
"""Folder of the model files in the working directory."""

POOL_FILE = "pool.json"
"""Name of the pool file inside :data:`MODELS_DIR`."""

TRAIN_FILE = "data/train.csv"
"""Default location of the training data in the working directory."""

MAX_EXPRESSION_LENGTH = 4000
"""Maximum number of characters of one expression or tie equation (rule E1)."""

MAX_NESTING_DEPTH = 50
"""Maximum nesting depth of one expression (rule E1). A sum or product of many terms is one
level; each function call, power, parenthesized sum inside a product and so on adds a level."""

MAX_NUMERIC_EXPONENT = 1024.0
"""Largest magnitude of a numeric exponent (rule E1)."""

MAX_NUMBER_DIGITS = 1000
"""Largest number of decimal digits of any number that the parser writes or computes while
building the canonical form (numerators, denominators, and the magnitude of floats) (rule E1)."""

MAX_MINMAX_ARGUMENTS = 32
"""Largest number of arguments of ``Min`` and ``Max``, also after nested calls are merged (rule E1)."""

MAX_PIECEWISE_PAIRS = 32
"""Largest number of (value, condition) pairs of one ``Piecewise`` (rule E1)."""

MAX_EXPRESSION_NODES = 10000
"""Largest number of distinct parts (nodes) built for one expression (rule E1)."""

MAX_MODEL_FILES = 100
"""Largest number of model files in ``models/`` that are checked; further files are reported
and not checked (rule F1)."""

MAX_FILE_BYTES = 1_000_000
"""Largest size of one model file or of the pool file, in bytes (rule F1)."""

TIE_RELATIVE_TOLERANCE = 1e-6
"""Relative tolerance between the recorded value of a tied parameter and the value that the
harness computes from its tie equation (rule E4)."""

TIE_ABSOLUTE_TOLERANCE = 1e-12
"""Absolute tolerance of the same comparison, which applies when the computed value is zero."""

_TIE_TOL_TEXT = ("%g" % TIE_RELATIVE_TOLERANCE).replace("e-0", "e-")

RULES: dict[str, str] = {
    "F1": (
        "A required field of the model file or the pool file is missing or malformed (this includes "
        "invalid JSON, an unknown field, an invalid or duplicate label, and a parameter name that is "
        "not an identifier or repeats a declared name)."
    ),
    "F2": "A label in the order of the pool file has no model file, or a model file in models/ is not listed in the order.",
    "E1": (
        "An expression does not follow the expression syntax, or contains a character, operator, name "
        "or function outside the task's permitted list."
    ),
    "E2": (
        "An expression contains a symbol that is neither a declared variable, a delayed variable, a "
        "parameter of the candidate, a given constant, pi nor E."
    ),
    "E3": "A parameter entry is not used in any expression or tie equation.",
    "E4": (
        "A tie equation refers to a name that is not a parameter or a given constant, forms a cycle, "
        "does not yield a finite real value, or disagrees with the recorded value by more than the "
        f"relative tolerance {_TIE_TOL_TEXT}."
    ),
    "E5": "The expressions do not have exactly the required keys of the formulation (one per state, or one for the output).",
    "E6": (
        "An expression yields a non-real or non-finite value on a training sample (every row of the "
        "training data is evaluated, trajectory by trajectory)."
    ),
    "P1": (
        "A parameter row (fitted, fixed or tied) has no description: what the parameter represents "
        "and, for a fixed value, where the value comes from."
    ),
}
"""The file and expression checks, printed identically by the
checking script and the harness."""

FUNCTIONS: dict[str, Any] = {
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
}
"""The available functions in SymPy spelling; the default permitted list is all of
them. ``log`` is the natural logarithm."""

DEFAULT_FUNCTIONS: tuple[str, ...] = tuple(FUNCTIONS)
"""Default permitted functions."""

ALIASES: dict[str, str] = {"abs": "Abs", "min": "Min", "max": "Max"}
"""Accepted alternative spellings: ``abs``, ``min`` and ``max`` mean
``Abs``, ``Min`` and ``Max`` and are permitted exactly when their SymPy spelling is permitted."""

CONDITION_FUNCTIONS: dict[str, Any] = {"Eq": sp.Eq, "Ne": sp.Ne}
"""Equality and inequality tests, permitted inside ``Piecewise`` conditions when ``Piecewise``
is permitted. ``==`` and ``!=`` are not accepted."""

CONSTANTS: dict[str, Any] = {"pi": sp.pi, "E": sp.E}
"""The fixed mathematical constants π (``pi``) and e (``E``)."""

_RESERVED_NAMES = frozenset(
    set(FUNCTIONS) | set(ALIASES) | set(CONDITION_FUNCTIONS) | set(CONSTANTS) | {"True", "False", "None"}
)
"""Names that a parameter may not take."""

PARAMETER_TYPES = ("fitted", "fixed", "tied")
"""Parameter type: ``fitted`` (estimated from data), ``fixed`` (chosen or known,
not estimated) or ``tied`` (computed from other parameters by an equation)."""

DISCUSSION_SECTIONS = ("family", "interpretation", "origin", "limitations")
"""The four discussion sections, in their order: the model family; what each term
represents; how the agent arrived at the expression; the limitations."""

ESTIMATION_FIELDS = ("criterion", "data", "method", "script")
"""Fields of the estimation record."""

CANDIDATE_FIELDS = ("expressions", "parameters", "estimation", "discussion")
"""Required fields of a model file ``models/<label>.json``. The label is the file name."""

CANDIDATE_FIELDS_OPTIONAL = ("answers", "predecessor")
"""``answers`` is required exactly when the task has discussion questions; ``predecessor`` names,
in a later round of interactive operation, the candidate of the previous pool version that this
candidate revises."""

PARAMETER_FIELDS_REQUIRED = ("name", "value", "unit", "type", "description")
PARAMETER_FIELDS_OPTIONAL = ("equation",)
"""Fields of a parameter row. ``description`` states what the parameter represents and, for a
fixed value, where the value comes from (rule P1); ``equation`` is required for, and only for, a
tied parameter."""

POOL_FIELDS = ("order", "recommended", "reason")
"""Fields of the pool file ``models/pool.json``. ``order`` is required. ``recommended`` (a label
of the order or ``null``) and ``reason`` (why this candidate, or why none) form the
recommendation; an error in them does not invalidate the pool file."""

LABEL_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
"""A candidate label: a letter, then up to 31 letters, digits, underscores or hyphens."""

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
"""A parameter name: a letter, then letters, digits or underscores."""

_EXPRESSION_CHARS = re.compile(r"^[A-Za-z0-9_+\-*/(),.\s<>=&|~]*$")
_NON_DECIMAL = re.compile(r"(?<![A-Za-z0-9_.])0[xXoObB]")


# ---------------------------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Issue:
    """One failed check: the rule identifier, the location and a message."""

    rule: str
    where: str
    message: str

    def text(self) -> str:
        """The report line of the issue, as printed by the script and the harness."""
        return f"[{self.rule}] {self.where}: {self.message}"


class ExpressionError(ValueError):
    """An expression violates rule ``rule`` (E1 or E2; E4 for a tie equation)."""

    def __init__(self, rule: str, message: str):
        super().__init__(message)
        self.rule = rule
        self.message = message


@dataclass(frozen=True)
class ParsedExpression:
    """A parsed expression.

    ``expr`` is the canonical SymPy expression over real symbols; ``names`` the symbols it
    contains (a name that disappears in the canonical form, as ``b`` in ``a*x + 0*b``, is not
    used); ``noninteger_literals`` the number of floating-point numbers with a non-integer value
    in the canonical form (``0.5`` and ``1e-3`` count, ``2``, ``2.0``, ``1e3`` and
    ``1/2`` do not).
    """

    text: str
    expr: sp.Expr
    names: frozenset[str]
    noninteger_literals: int


@dataclass(frozen=True)
class Delay:
    """A delayed variable of a NARX task: ``name[k] = variable[k − lag]``."""

    name: str
    variable: str
    lag: int


@dataclass(frozen=True)
class CheckConfig:
    """The task information needed by the checks; the content of ``check_config.json``.

    Every field is shown to the agent in the brief. ``columns`` maps
    each column name to its roles; ``arguments`` are the variables that expressions may use
    (inputs and states, or for NARX the output, the delayed variables and the inputs);
    ``expression_keys`` the required keys; ``constants`` the given
    constants with their values; ``functions`` the permitted functions and ``added_functions``
    the task's additional functions with their definitions; ``question_ids`` the identifiers of
    the discussion questions; ``pool_cap`` the maximum number of candidates evaluated; and
    ``pool_version`` and ``previous_labels`` the expected pool version and the labels of the
    previous pool version (interactive operation).
    """

    task_id: str
    formulation: str
    columns: dict[str, tuple[str, ...]]
    arguments: tuple[str, ...]
    expression_keys: tuple[str, ...]
    delays: tuple[Delay, ...]
    constants: dict[str, float]
    functions: tuple[str, ...]
    added_functions: tuple[tuple[str, tuple[str, ...], str], ...]
    question_ids: tuple[str, ...]
    pool_cap: int
    trajectory_column: str | None
    train_file: str = TRAIN_FILE
    pool_version: int = 1
    previous_labels: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "CheckConfig":
        """Build the configuration from the content of ``check_config.json``.

 Raises ``ValueError`` for a malformed configuration.
        """
        try:
            if d.get("format_version") != FORMAT_VERSION:
                raise ValueError(f"format_version must be {FORMAT_VERSION}")
            functions = tuple(str(f) for f in d["functions"])
            unknown = [f for f in functions if f not in FUNCTIONS]
            if unknown:
                raise ValueError(f"unknown function(s) {unknown}")
            return cls(
                task_id=str(d["task_id"]),
                formulation=str(d["formulation"]),
                columns={str(c["name"]): tuple(str(r) for r in c.get("roles", ())) for c in d["columns"]},
                arguments=tuple(str(a) for a in d["arguments"]),
                expression_keys=tuple(str(k) for k in d["expression_keys"]),
                delays=tuple(Delay(str(x["name"]), str(x["variable"]), int(x["lag"])) for x in d.get("delays", ())),
                constants={str(c["name"]): float(c["value"]) for c in d.get("constants", ())},
                functions=functions,
                added_functions=tuple(
                    (str(a["name"]), tuple(str(x) for x in a["arguments"]), str(a["definition"]))
                    for a in d.get("added_functions", ())
                ),
                question_ids=tuple(str(q) for q in d.get("discussion_questions", ())),
                pool_cap=int(d["pool_cap"]),
                trajectory_column=d.get("trajectory_column"),
                train_file=str(d.get("train_file", TRAIN_FILE)),
                pool_version=int(d.get("pool_version", 1)),
                previous_labels=tuple(str(x) for x in d.get("previous_labels", ())),
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError(f"malformed check configuration: {exc!r}") from exc

    def to_dict(self) -> dict[str, Any]:
        """The configuration as the plain data of ``check_config.json``."""
        return {
            "format_version": FORMAT_VERSION,
            "task_id": self.task_id,
            "formulation": self.formulation,
            "columns": [{"name": n, "roles": list(r)} for n, r in self.columns.items()],
            "arguments": list(self.arguments),
            "expression_keys": list(self.expression_keys),
            "delays": [{"name": x.name, "variable": x.variable, "lag": x.lag} for x in self.delays],
            "constants": [{"name": n, "value": v} for n, v in self.constants.items()],
            "functions": list(self.functions),
            "added_functions": [
                {"name": n, "arguments": list(a), "definition": dfn} for n, a, dfn in self.added_functions
            ],
            "discussion_questions": list(self.question_ids),
            "pool_cap": self.pool_cap,
            "trajectory_column": self.trajectory_column,
            "train_file": self.train_file,
            "pool_version": self.pool_version,
            "previous_labels": list(self.previous_labels),
        }


@dataclass(frozen=True)
class TrainingData:
    """The training table: column values and trajectory blocks.

    ``trajectories`` lists ``(identifier, start, stop)`` for every contiguous block of rows,
    0-based and stop-exclusive; without a trajectory column the whole table is one trajectory.
    """

    file: str
    header: tuple[str, ...]
    columns: dict[str, list[float]]
    n_rows: int
    trajectories: tuple[tuple[str, int, int], ...]


@dataclass(frozen=True)
class Parameter:
    """One row of the parameter table.

    ``value`` is the recorded value. For a tied parameter, ``equation`` is its defining equation
    over other parameters and given constants; the computed value is in
    :attr:`Candidate.values`.
    """

    name: str
    value: float
    unit: str
    type: str
    description: str
    equation: str | None = None

    @property
    def symbol(self) -> sp.Symbol:
        """The real SymPy symbol of the parameter."""
        return sp.Symbol(self.name, real=True)


@dataclass(frozen=True)
class Candidate:
    """A candidate that passed the file and expression checks.

    Every expression is in the canonical form of :func:`parse_expression` (SymPy's automatic
    evaluation); the checks, the evaluation and the exports use this form, and
    ``expression_texts`` keeps the agent's text for the record only.

    - ``expressions``: canonical SymPy expression per expression key, with the parameters and
      given constants as real symbols (tied parameters not substituted);
    - ``resolved``: the same with every tied parameter replaced by its resolved tie equation, so
      that it contains only arguments, fitted and fixed parameters and given constants; rule E6
      evaluated exactly these expressions;
    - ``tie_expressions``: for every tied parameter, its canonical equation with every tied name
      resolved;
    - ``values``: the value of every parameter; tied values are computed by the harness from the
      tie equations with :func:`numeric_function` (they agree with the recorded values within
      :data:`TIE_RELATIVE_TOLERANCE`);
    - ``arguments``: the variables of the expressions, in the order of the task;
    - ``noninteger_literals``: per expression, the number of floating-point numbers with a
      non-integer value in the canonical form.
    """

    label: str
    file: str
    expression_texts: dict[str, str]
    expressions: dict[str, sp.Expr]
    resolved: dict[str, sp.Expr]
    arguments: tuple[str, ...]
    parameters: tuple[Parameter, ...]
    tie_expressions: dict[str, sp.Expr]
    values: dict[str, float]
    constants: dict[str, float]
    estimation: dict[str, Any]
    discussion: dict[str, str]
    answers: dict[str, str]
    predecessor: str | None
    noninteger_literals: dict[str, int]

    def names(self, type: str) -> tuple[str, ...]:
        """Names of the parameters of ``type`` (``fitted``, ``fixed`` or ``tied``), in table order."""
        return tuple(p.name for p in self.parameters if p.type == type)

    @property
    def fitted(self) -> tuple[str, ...]:
        """Names of the fitted parameters."""
        return self.names("fitted")

    @property
    def fixed(self) -> tuple[str, ...]:
        """Names of the fixed parameters."""
        return self.names("fixed")

    @property
    def tied(self) -> tuple[str, ...]:
        """Names of the tied parameters."""
        return self.names("tied")

    def resolved_expressions(self) -> dict[str, sp.Expr]:
        """Canonical expressions with every tied parameter replaced by its resolved equation.

        The result contains the arguments, the fitted and fixed parameters and the given constants
        as symbols.
        """
        return dict(self.resolved)

    def numeric_expressions(self, substitute_constants: bool = True) -> dict[str, sp.Expr]:
        """The resolved expressions with every parameter (and given constant) replaced by its value.

 Each value is inserted as the SymPy float equal to its double, without
        re-evaluating the expression, so that :func:`numeric_function` of the result performs the
        same operations on the same doubles as rule E6 and :meth:`numeric_function`.
        """
        sub = {sp.Symbol(n, real=True): sp.Float(float(v)) for n, v in self.values.items() if n not in self.tie_expressions}
        if substitute_constants:
            sub.update({sp.Symbol(n, real=True): sp.Float(float(v)) for n, v in self.constants.items()})
        with sp.evaluate(False):
            return {k: e.xreplace(sub) for k, e in self.resolved.items()}

    def numeric_function(self, key: str) -> Any:
        """The function ``f(*argument_values) -> float`` of expression ``key``.

        Arguments are the values of :attr:`arguments` in their order; parameters and given
        constants are bound to their values. This is exactly the function that rule E6 evaluated,
        with the semantics of :func:`numeric_function`.
        """
        e = self.resolved[key]
        free = {str(s) for s in e.free_symbols}
        bound = [n for n in list(self.values) + list(self.constants) if n in free and n not in self.tie_expressions]
        f = numeric_function(e, list(self.arguments) + bound)
        known = {**self.values, **self.constants}
        fixed_values = [float(known[n]) for n in bound]
        return lambda *xs: f(*[float(x) for x in xs], *fixed_values)

    @property
    def total_noninteger_literals(self) -> int:
        """Total count of non-integer numeric literals over the expressions."""
        return sum(self.noninteger_literals.values())


@dataclass(frozen=True)
class Pool:
    """A valid pool file.

    ``recommendation`` is ``{"label": <label or None>, "reason": <text>}``, built from the fields
    ``recommended`` and ``reason`` of the file, or ``None`` when they are absent or invalid; their
    problems are in ``recommendation_issues`` and do not affect the candidates.
    An empty ``order`` means that the pool contains no candidate.
    ``pool_version`` is the version that the harness assigned to the round; the file does not
    state it.
    """

    file: str
    pool_version: int
    order: tuple[str, ...]
    recommendation: dict[str, Any] | None
    recommendation_issues: tuple[Issue, ...] = ()

    @property
    def recommended(self) -> str | None:
        """The recommended label; ``None`` when no recommendation is supported or it is invalid."""
        return self.recommendation.get("label") if self.recommendation is not None else None


@dataclass
class CandidateResult:
    """The outcome of the checks of one candidate.

    ``position`` is the 1-based position in the order (``None`` for a file not in the order);
    ``within_limit`` states whether the label is among the first ``pool_cap`` labels of the
    order; ``candidate`` is set when every check passed. ``diagnostics`` holds non-failing
    information (for example the count of non-integer literals).
    """

    label: str
    file: str | None
    position: int | None = None
    within_limit: bool = False
    issues: list[Issue] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    candidate: Candidate | None = None

    @property
    def passed(self) -> bool:
        """True when the candidate passed every file and expression check."""
        return not self.issues and self.candidate is not None


@dataclass
class CheckReport:
    """The outcome of the checks of one working directory.

    ``order`` is the order of the pool file, or the sorted labels of the model files when the pool
    file is missing or has no usable order (``order_from_pool`` false). The first ``pool_cap``
    labels of the order are ``within_limit``; the others are ``outside_limit``: retained, marked,
    and not evaluated. ``evaluated`` are the labels within the limit that passed every check.
    ``passed`` requires a valid pool file and at least one evaluated candidate.
    """

    config: CheckConfig
    training_rows: int
    training_trajectories: int
    pool: Pool | None
    pool_issues: list[Issue]
    candidates: dict[str, CandidateResult]
    order: list[str]
    order_from_pool: bool
    folder_issues: list[Issue] = field(default_factory=list)

    @property
    def within_limit(self) -> list[str]:
        """Labels among the first ``pool_cap`` labels of the order."""
        return self.order[: self.config.pool_cap]

    @property
    def outside_limit(self) -> list[str]:
        """Labels beyond the pool limit: retained in the record and not evaluated."""
        return self.order[self.config.pool_cap :]

    @property
    def evaluated(self) -> list[str]:
        """Labels within the limit that passed every check, in the agent's order."""
        return [lab for lab in self.within_limit if lab in self.candidates and self.candidates[lab].passed]

    @property
    def pool_ok(self) -> bool:
        """True when the pool file is present and valid."""
        return self.pool is not None and not self.pool_issues

    @property
    def passed(self) -> bool:
        """True when the pool file is valid and at least one candidate within the limit passed."""
        return self.pool_ok and bool(self.evaluated)

    @property
    def recommendation_issues(self) -> list[Issue]:
        """Issues of the recommendation; they do not affect the candidates or the round."""
        return list(self.pool.recommendation_issues) if self.pool is not None else []

    @property
    def issues(self) -> list[Issue]:
        """Every issue: the pool file's, the recommendation's, the folder's, then the candidates'."""
        out = list(self.pool_issues) + self.recommendation_issues + list(self.folder_issues)
        for r in self._ordered_results():
            out.extend(r.issues)
        return out

    def _ordered_results(self) -> list[CandidateResult]:
        seen = [self.candidates[lab] for lab in self.order if lab in self.candidates]
        rest = [r for lab, r in sorted(self.candidates.items()) if lab not in self.order]
        return seen + rest

    def text(self) -> str:
        """The report as printed by ``check_submission.py`` and ``aspire check``."""
        return format_report(self)


# ---------------------------------------------------------------------------------------------
# Expression parser (rules E1 and E2) and canonical form
# ---------------------------------------------------------------------------------------------
#
# The text is checked (characters, length), parsed by Python's own parser into a syntax tree
# (which executes nothing), and the tree is walked once: every node is admitted or rejected, and
# the SymPy expression is built bottom-up from the admitted nodes. Each node is built with SymPy's
# automatic evaluation, which defines the canonical form, and every intermediate result passes
# the structural guard of :class:`_Guard` before it is used, so that no construction can exhaust
# time or memory: numbers are bounded in size, powers of numbers are bounded before they are
# computed, Min, Max and Piecewise are bounded in their number of arguments, and the number of
# distinct nodes is bounded. No wall-clock limit is needed.

_ARITY: dict[str, int] = {
    "sin": 1, "cos": 1, "tan": 1, "asin": 1, "acos": 1, "atan": 1, "atan2": 2, "sinh": 1,
    "cosh": 1, "tanh": 1, "exp": 1, "log": 1, "sqrt": 1, "Abs": 1, "sign": 1, "Eq": 2, "Ne": 2,
}
"""Number of arguments of each permitted function; ``Min`` and ``Max`` take 1 to
:data:`MAX_MINMAX_ARGUMENTS`, ``Piecewise`` 1 to :data:`MAX_PIECEWISE_PAIRS` pairs."""

_ARITY_HINTS = {
    "log": "log takes one argument and is the natural logarithm; write log(x)/log(b) for the logarithm to base b",
    "sqrt": "sqrt takes one argument; write x**(1/n) for another root",
}

_COMPARE_OPS = {ast.Lt: sp.Lt, ast.LtE: sp.Le, ast.Gt: sp.Gt, ast.GtE: sp.Ge}
_OP_HINTS = {
    ast.BitXor: "'^' is not a power operator; write ** for a power",
    ast.Mod: "the operator % is not permitted",
    ast.FloorDiv: "the operator // is not permitted; write / for a division",
    ast.MatMult: "the operator @ is not permitted",
    ast.LShift: "the operator << is not permitted",
    ast.RShift: "the operator >> is not permitted",
}
_LOG2_10 = 3.321928094887362
_MAX_NUMBER_BITS = int(MAX_NUMBER_DIGITS * _LOG2_10) + 1
_BOOLEAN_TYPES = (sp.logic.boolalg.Boolean, sp.core.relational.Relational)


def _is_condition(e: Any) -> bool:
    return isinstance(e, _BOOLEAN_TYPES) and not isinstance(e, sp.Expr)


def _number_bits(n: sp.Basic) -> int:
    """Size of a SymPy number in bits: numerator or denominator, or the binary exponent of a float."""
    if isinstance(n, sp.Integer):
        return abs(int(n.p)).bit_length()
    if isinstance(n, sp.Rational):
        return max(abs(int(n.p)).bit_length(), int(n.q).bit_length())
    if isinstance(n, sp.Float):
        _, man, exp, bc = n._mpf_
        if man == 0 and bc == 0:  # zero, or a non-finite special value
            return 0
        return max(0, exp + bc)
    return 0


class _Guard:
    """Structural bounds on every SymPy node that the parser or a substitution builds (rule E1)."""

    def __init__(self) -> None:
        self.seen: set[Any] = set()

    def check(self, e: Any) -> Any:
        stack = [e]
        while stack:
            n = stack.pop()
            if n in self.seen:
                continue
            self.seen.add(n)
            if len(self.seen) > MAX_EXPRESSION_NODES:
                raise ExpressionError("E1", f"the expression is too large: it has more than {MAX_EXPRESSION_NODES} distinct parts")
            if isinstance(n, (sp.Integer, sp.Rational, sp.Float)) and _number_bits(n) > _MAX_NUMBER_BITS:
                raise ExpressionError("E1", f"a number in the expression, or one computed from its numbers, exceeds 10^{MAX_NUMBER_DIGITS} in magnitude")
            if isinstance(n, (sp.Min, sp.Max)) and len(n.args) > MAX_MINMAX_ARGUMENTS:
                raise ExpressionError("E1", f"{type(n).__name__} has more than {MAX_MINMAX_ARGUMENTS} arguments after simplification")
            if isinstance(n, sp.Piecewise) and len(n.args) > MAX_PIECEWISE_PAIRS:
                raise ExpressionError("E1", f"Piecewise has more than {MAX_PIECEWISE_PAIRS} pairs")
            stack.extend(n.args)
        return e

    def pow_precheck(self, base: Any, exponent: Any) -> None:
        if not getattr(exponent, "is_number", False):
            return
        if exponent.is_real is False or exponent.has(sp.I):
            raise ExpressionError("E1", f"an exponent evaluates to {exponent}, which is not a real number")
        if not isinstance(exponent, (sp.Integer, sp.Rational, sp.Float)):
            return
        mag = abs(float(exponent))
        if mag > MAX_NUMERIC_EXPONENT:
            raise ExpressionError(
                "E1", f"the numeric exponent {exponent} exceeds {MAX_NUMERIC_EXPONENT:g} in magnitude; write the power with a parameter or rescale the expression"
            )
        bits = max((_number_bits(a) for a in sp.preorder_traversal(base) if isinstance(a, (sp.Integer, sp.Rational))), default=0)
        if bits * mag > 2 * _MAX_NUMBER_BITS:
            raise ExpressionError("E1", f"a power of the numbers in the expression would exceed 10^{MAX_NUMBER_DIGITS} in magnitude")

    def build(self, func: Any, *args: Any) -> Any:
        if func is sp.Pow:
            self.pow_precheck(*args)
        try:
            e = func(*args)
        except ExpressionError:
            raise
        except (TypeError, ValueError, ArithmeticError, RecursionError, AttributeError) as exc:
            raise ExpressionError("E1", f"the terms cannot be combined by {getattr(func, '__name__', func)} ({type(exc).__name__})") from None
        return self.check(e)


def rebuild(expr: Any, mapping: Mapping[Any, Any], guard: _Guard | None = None) -> Any:
    """Substitute ``mapping`` (symbol → expression) in ``expr`` and re-evaluate bottom-up.

    Every rebuilt node passes the structural guard of the parser; this is the substitution used
    for tie equations and added functions. Raises :class:`ExpressionError` (E1) when a bound is
    exceeded.
    """
    guard = guard or _Guard()
    memo: dict[Any, Any] = {}

    def walk(e: Any) -> Any:
        if e in mapping:
            return mapping[e]
        if not e.args:
            return e
        if e in memo:
            return memo[e]
        args = [walk(a) for a in e.args]
        r = e if all(a is b for a, b in zip(args, e.args)) else guard.build(e.func, *args)
        memo[e] = r
        return r

    return guard.check(walk(expr))


class _Builder:
    """Admit the nodes of a Python syntax tree and build the canonical SymPy expression (E1, E2)."""

    def __init__(self, names: set[str], callables: dict[str, Any], all_functions: set[str], hints: Mapping[str, str]):
        self.names = names
        self.callables = callables
        self.all_functions = all_functions
        self.hints = hints
        self.guard = _Guard()

    # -- helpers ---------------------------------------------------------------------------
    def value(self, node: ast.AST, depth: int) -> sp.Expr:
        e = self.node(node, depth)
        if not isinstance(e, sp.Expr):
            raise ExpressionError("E1", "a condition is used as a value; conditions are permitted only inside Piecewise and combined with &, |, ~")
        return e

    def condition(self, node: ast.AST, depth: int) -> Any:
        e = self.node(node, depth)
        if not _is_condition(e):
            raise ExpressionError(
                "E1", "a Piecewise condition must be a comparison (<, <=, >, >=, Eq, Ne), True, or such comparisons combined with &, |, ~; a number or an expression is not a condition"
            )
        return e

    @staticmethod
    def chain(node: ast.AST, ops: tuple[type, ...], inverse: type | None) -> list[tuple[bool, ast.AST]]:
        """Operands of a flat chain of the operators ``ops`` (left to right); True marks an inverse."""
        out: list[tuple[bool, ast.AST]] = []
        stack: list[tuple[ast.AST, bool]] = [(node, False)]
        while stack:
            n, inv = stack.pop()
            if isinstance(n, ast.BinOp) and isinstance(n.op, ops):
                right_inv = (not inv) if (inverse is not None and isinstance(n.op, inverse)) else inv
                stack.append((n.right, right_inv))
                stack.append((n.left, inv))
            else:
                out.append((inv, n))
        return out

    # -- nodes -----------------------------------------------------------------------------
    def node(self, node: ast.AST, depth: int) -> Any:
        if depth > MAX_NESTING_DEPTH:
            raise ExpressionError("E1", f"the expression is nested more than {MAX_NESTING_DEPTH} levels deep (sums and products of many terms do not count as nesting)")
        d = depth + 1
        g = self.guard
        if isinstance(node, ast.Expression):
            return self.value(node.body, depth)
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                return sp.true if v else sp.false
            if isinstance(v, int):
                if abs(v).bit_length() > _MAX_NUMBER_BITS:
                    raise ExpressionError("E1", f"a number literal exceeds 10^{MAX_NUMBER_DIGITS} in magnitude")
                return sp.Integer(v)
            if isinstance(v, float):
                if not math.isfinite(v):
                    raise ExpressionError("E1", "a number literal exceeds the double-precision range (about 1.8e308)")
                return sp.Float(v)
            raise ExpressionError("E1", f"the literal {v!r} is not a real number")
        if isinstance(node, ast.Name):
            return self.name(node.id)
        if isinstance(node, ast.BinOp):
            op = type(node.op)
            if op in _OP_HINTS:
                raise ExpressionError("E1", _OP_HINTS[op])
            if op in (ast.Add, ast.Sub):
                terms = []
                for neg, n in self.chain(node, (ast.Add, ast.Sub), ast.Sub):
                    t = self.value(n, d)
                    terms.append(g.build(sp.Mul, sp.Integer(-1), t) if neg else t)
                return g.build(sp.Add, *terms)
            if op in (ast.Mult, ast.Div):
                factors = []
                for inv, n in self.chain(node, (ast.Mult, ast.Div), ast.Div):
                    f = self.value(n, d)
                    factors.append(g.build(sp.Pow, f, sp.Integer(-1)) if inv else f)
                return g.build(sp.Mul, *factors)
            if op is ast.Pow:
                return g.build(sp.Pow, self.value(node.left, d), self.value(node.right, d))
            if op in (ast.BitAnd, ast.BitOr):
                if "Piecewise" not in self.callables:
                    raise ExpressionError("E1", "& and | combine Piecewise conditions, and Piecewise is not permitted in this task")
                ops = (ast.BitAnd,) if op is ast.BitAnd else (ast.BitOr,)
                parts = [self.condition(n, d) for _, n in self.chain(node, ops, None)]
                return g.build(sp.And if op is ast.BitAnd else sp.Or, *parts)
            raise ExpressionError("E1", f"the operator {op.__name__} is not permitted")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                raise ExpressionError("E1", "'not' is not permitted; write ~(condition)")
            if isinstance(node.op, ast.Invert):
                return g.build(sp.Not, self.condition(node.operand, d))
            v = self.value(node.operand, d)
            return g.build(sp.Mul, sp.Integer(-1), v) if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BoolOp):
            raise ExpressionError("E1", "'and' and 'or' are not permitted; write (a) & (b) and (a) | (b)")
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1:
                raise ExpressionError("E1", "chained or unparenthesized comparisons are not permitted; write (x > 0) & (x < 1)")
            op = type(node.ops[0])
            if op in (ast.Eq, ast.NotEq):
                raise ExpressionError("E1", "write equality tests as Eq(a, b) and Ne(a, b), not == or !=")
            if op not in _COMPARE_OPS:
                raise ExpressionError("E1", f"the comparison {op.__name__} is not permitted")
            if "Piecewise" not in self.callables:
                raise ExpressionError("E1", "comparisons are permitted only in Piecewise conditions, and Piecewise is not permitted in this task")
            return g.build(_COMPARE_OPS[op], self.value(node.left, d), self.value(node.comparators[0], d))
        if isinstance(node, ast.Call):
            return self.call(node, d)
        if isinstance(node, ast.Tuple):
            raise ExpressionError("E1", "a parenthesized list (a, b) is permitted only as a (value, condition) pair of Piecewise")
        if isinstance(node, ast.Attribute):
            raise ExpressionError("E1", "attribute access ('.') is not permitted")
        if isinstance(node, ast.Lambda):
            raise ExpressionError("E1", "lambda expressions are not permitted")
        if isinstance(node, ast.IfExp):
            raise ExpressionError("E1", "'if ... else' is not permitted; write Piecewise((a, condition), (b, True))")
        raise ExpressionError("E1", f"the construct {type(node).__name__} is not permitted")

    def name(self, name: str) -> Any:
        if name in CONSTANTS:
            return CONSTANTS[name]
        if name in self.callables or name in self.all_functions:
            raise ExpressionError("E1", f"{name} is a function; call it with its arguments, for example {name}(x)")
        if name not in self.names:
            hint = self.hints.get(name)
            raise ExpressionError("E2", f"undeclared symbol {name}" + (f" ({hint})" if hint else ""))
        return sp.Symbol(name, real=True)

    def call(self, node: ast.Call, d: int) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ExpressionError("E1", "only the permitted functions may be called, by their plain names")
        fname = node.func.id
        if fname not in self.callables:
            if fname in self.names:
                raise ExpressionError("E1", f"{fname} is not a function; write {fname}*(...) for a product")
            if fname in self.all_functions:
                raise ExpressionError("E1", f"the function {fname} is not permitted in this task")
            raise ExpressionError("E1", f"the function {fname} is not in the permitted list")
        if node.keywords:
            raise ExpressionError("E1", f"keyword arguments are not permitted in {fname}(...)")
        if any(isinstance(a, ast.Starred) for a in node.args):
            raise ExpressionError("E1", f"starred arguments are not permitted in {fname}(...)")
        canonical = ALIASES.get(fname, fname)
        n = len(node.args)
        g = self.guard
        if canonical == "Piecewise":
            if not 1 <= n <= MAX_PIECEWISE_PAIRS:
                raise ExpressionError("E1", f"Piecewise takes 1 to {MAX_PIECEWISE_PAIRS} pairs (value, condition)")
            pairs = []
            for a in node.args:
                if not (isinstance(a, ast.Tuple) and len(a.elts) == 2):
                    raise ExpressionError("E1", "each argument of Piecewise must be a pair (value, condition)")
                pairs.append((self.value(a.elts[0], d + 1), self.condition(a.elts[1], d + 1)))
            return g.build(sp.Piecewise, *pairs)
        if canonical in ("Min", "Max"):
            if not 1 <= n <= MAX_MINMAX_ARGUMENTS:
                raise ExpressionError("E1", f"{fname} takes 1 to {MAX_MINMAX_ARGUMENTS} arguments")
            return g.build(FUNCTIONS[canonical], *[self.value(a, d) for a in node.args])
        func = self.callables[fname]
        if isinstance(func, sp.Lambda):
            if n != len(func.variables):
                raise ExpressionError("E1", f"{fname} takes {len(func.variables)} argument(s)")
            args = [self.value(a, d) for a in node.args]
            return rebuild(func.expr, dict(zip(func.variables, args)), g)
        if n != _ARITY[canonical]:
            hint = _ARITY_HINTS.get(canonical, f"{fname} takes {_ARITY[canonical]} argument(s)")
            raise ExpressionError("E1", hint)
        return g.build(func, *[self.value(a, d) for a in node.args])


def _callables(functions: Iterable[str], added: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in functions:
        out[f] = FUNCTIONS[f]
    for alias, target in ALIASES.items():
        if target in out:
            out[alias] = FUNCTIONS[target]
    if "Piecewise" in out:
        out.update(CONDITION_FUNCTIONS)
    out.update(added)
    return out


def _noninteger_floats(expr: Any) -> int:
    return sum(1 for a in sp.preorder_traversal(expr) if isinstance(a, sp.Float) and not a.is_integer)


def parse_expression(
    text: Any,
    names: Iterable[str],
    functions: Iterable[str] = DEFAULT_FUNCTIONS,
    added: Mapping[str, Any] | None = None,
    hints: Mapping[str, str] | None = None,
) -> ParsedExpression:
    """Parse one candidate expression into its canonical SymPy form (rules E1, E2).

    ``names`` are the admissible symbols (variables, parameters, given constants); they become
    real SymPy symbols. ``functions`` are the permitted functions (SymPy spelling); ``added`` maps added function names to SymPy ``Lambda`` objects; ``hints`` maps
    likely mistakes to explanations for the E2 message. ``pi`` and ``E`` are the constants π and
    e. Number literals become exact integers or double-precision floats.

    The **canonical form** is the expression that SymPy's automatic evaluation produces when the
    expression is built node by node: numbers are folded (``2*3`` → ``6``, ``sin(0)`` → ``0``),
    like terms and factors are combined (``x/x`` → ``1``, ``x + x`` → ``2*x``, ``0*b`` → ``0``),
    and simple identities are applied (``sqrt(x**2)`` → ``Abs(x)`` for real ``x``). The checks,
    the evaluation and the exports use the canonical form; the agent's text is kept only for the
    record. Raises :class:`ExpressionError` with rule E1 (syntax, character, operator, function,
    or a size bound) or E2 (undeclared symbol).
    """
    if not isinstance(text, str):
        raise ExpressionError("E1", "the expression must be a string")
    if not text.strip():
        raise ExpressionError("E1", "the expression is empty")
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise ExpressionError("E1", f"the expression has {len(text)} characters; the limit is {MAX_EXPRESSION_LENGTH}")
    if "^" in text:
        raise ExpressionError("E1", "'^' is not a power operator; write ** for a power")
    if not _EXPRESSION_CHARS.match(text):
        bad = sorted({ch for ch in text if not _EXPRESSION_CHARS.match(ch)})
        raise ExpressionError("E1", f"the character(s) {' '.join(ascii(c) for c in bad)} are not permitted")
    if "__" in text:
        raise ExpressionError("E1", "a double underscore '__' is not permitted")
    if _NON_DECIMAL.search(text):
        raise ExpressionError("E1", "only decimal number literals are permitted")
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError as exc:
        raise ExpressionError("E1", f"syntax error: {exc.msg}") from None
    except (ValueError, RecursionError, MemoryError):
        raise ExpressionError("E1", "the expression cannot be read; it is too deeply nested") from None
    added = dict(added or {})
    callables = _callables(functions, added)
    all_functions = set(FUNCTIONS) | set(ALIASES) | set(CONDITION_FUNCTIONS) | set(added)
    builder = _Builder(set(names), callables, all_functions, hints or {})
    try:
        expr = builder.node(tree, 0)
    except RecursionError:
        raise ExpressionError("E1", "the expression is too deeply nested") from None
    used = frozenset(str(s) for s in expr.free_symbols)
    return ParsedExpression(text=text, expr=expr, names=used, noninteger_literals=_noninteger_floats(expr))


def added_function_lambdas(config: CheckConfig) -> dict[str, sp.Lambda]:
    """SymPy ``Lambda`` objects of the task's added functions.

    Each definition is parsed with the restricted parser over its own arguments and the
    permitted functions.
    """
    out: dict[str, sp.Lambda] = {}
    for name, args, definition in config.added_functions:
        body = parse_expression(definition, args, config.functions).expr
        out[name] = sp.Lambda(tuple(sp.Symbol(a, real=True) for a in args), body)
    return out


# ---------------------------------------------------------------------------------------------
# Numerical evaluation (rule E6; shared with the evaluation of the harness)
# ---------------------------------------------------------------------------------------------

_INF = math.inf
_NAN = math.nan


def _odd_integer(b: float) -> bool:
    return math.isfinite(b) and b.is_integer() and int(b) % 2 == 1


def _ieee_div(a: float, b: float) -> float:
    try:
        return a / b
    except ZeroDivisionError:
        if a != a or a == 0:
            return _NAN
        return math.copysign(_INF, a) * math.copysign(1.0, b)


def _ieee_pow(a: float, b: float) -> float:
    try:
        return math.pow(a, b)
    except OverflowError:
        return -_INF if (a < 0 and _odd_integer(b)) else _INF
    except ValueError:
        if a == 0 and b < 0:
            return -_INF if (math.copysign(1.0, a) < 0 and _odd_integer(b)) else _INF
        return _NAN


def _ieee1(f: Any, on_overflow: Any = None) -> Any:
    def g(x: float) -> float:
        try:
            return f(x)
        except OverflowError:
            return on_overflow(x) if on_overflow is not None else _INF
        except ValueError:
            return _NAN

    return g


def _ieee_log(x: float) -> float:
    if x == 0:
        return -_INF
    if not x > 0:  # negative or NaN
        return _NAN
    return math.log(x)


def _ieee_sqrt(x: float) -> float:
    if x < 0 or x != x:
        return _NAN
    return math.sqrt(x)


def _ieee_sign(x: float) -> float:
    if x != x:
        return _NAN
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)


def _ieee_min(*xs: float) -> float:
    return _NAN if any(x != x for x in xs) else min(xs)


def _ieee_max(*xs: float) -> float:
    return _NAN if any(x != x for x in xs) else max(xs)


def _ieee_add(*xs: float) -> float:
    s = xs[0]
    for x in xs[1:]:
        s = s + x
    return s


def _ieee_mul(*xs: float) -> float:
    s = xs[0]
    for x in xs[1:]:
        s = s * x
    return s


_NUMERIC_FUNCTIONS: dict[Any, tuple[str, Any]] = {
    sp.sin: ("_sin", _ieee1(math.sin)),
    sp.cos: ("_cos", _ieee1(math.cos)),
    sp.tan: ("_tan", _ieee1(math.tan)),
    sp.asin: ("_asin", _ieee1(math.asin)),
    sp.acos: ("_acos", _ieee1(math.acos)),
    sp.atan: ("_atan", _ieee1(math.atan)),
    sp.atan2: ("_atan2", math.atan2),
    sp.sinh: ("_sinh", _ieee1(math.sinh, lambda x: math.copysign(_INF, x))),
    sp.cosh: ("_cosh", _ieee1(math.cosh)),
    sp.tanh: ("_tanh", _ieee1(math.tanh)),
    sp.exp: ("_exp", _ieee1(math.exp)),
    sp.log: ("_log", _ieee_log),
    sp.Abs: ("_abs", math.fabs),
    sp.sign: ("_sign", _ieee_sign),
    sp.Min: ("_min", _ieee_min),
    sp.Max: ("_max", _ieee_max),
}
_NUMERIC_NAMESPACE: dict[str, Any] = {name: f for name, f in _NUMERIC_FUNCTIONS.values()}
_NUMERIC_NAMESPACE.update(
    _div=_ieee_div, _pow=_ieee_pow, _sqrt=_ieee_sqrt, _add=_ieee_add, _mul=_ieee_mul, _inf=_INF, _nan=_NAN,
    _pi=math.pi, _e=math.e,
)
_RELATIONS = {
    sp.StrictLessThan: "<", sp.LessThan: "<=", sp.StrictGreaterThan: ">", sp.GreaterThan: ">=",
    sp.Equality: "==", sp.Unequality: "!=",
}


def _to_double(n: Any) -> float:
    try:
        return float(n)
    except (OverflowError, TypeError):
        return _INF if n > 0 else -_INF


def _numeric_code(e: Any, index: Mapping[str, str], consts: list[float]) -> str:
    if e.is_Symbol:
        try:
            return index[e.name]
        except KeyError:
            raise ValueError(f"the symbol {e.name} has no value") from None
    if e is sp.pi:
        return "_pi"
    if e is sp.E:
        return "_e"
    if e in (sp.oo,):
        return "_inf"
    if e in (-sp.oo,):
        return "(-_inf)"
    if e in (sp.nan, sp.zoo, sp.I):
        return "_nan"
    if isinstance(e, (sp.Integer, sp.Rational, sp.Float)):
        consts.append(_to_double(e))
        return f"_k[{len(consts) - 1}]"
    if e is sp.true:
        return "True"
    if e is sp.false:
        return "False"
    if isinstance(e, sp.Add):
        return "_add(" + ", ".join(_numeric_code(a, index, consts) for a in e.args) + ")"
    if isinstance(e, sp.Mul):
        num, den = [], []
        for a in e.args:
            if isinstance(a, sp.Pow) and isinstance(a.exp, (sp.Integer, sp.Rational, sp.Float)) and a.exp < 0:
                den.append(sp.Pow(a.base, -a.exp, evaluate=False))
            else:
                num.append(a)
        code = lambda xs: (_numeric_code(xs[0], index, consts) if len(xs) == 1 else "_mul(" + ", ".join(_numeric_code(x, index, consts) for x in xs) + ")")
        if not den:
            return code(num)
        consts.append(1.0)
        n_code = code(num) if num else f"_k[{len(consts) - 1}]"
        return f"_div({n_code}, {code(den)})"
    if isinstance(e, sp.Pow):
        b, x = e.args
        if x == sp.Rational(1, 2):
            return f"_sqrt({_numeric_code(b, index, consts)})"
        if isinstance(x, (sp.Integer, sp.Rational, sp.Float)) and x < 0:
            consts.append(1.0)
            one = f"_k[{len(consts) - 1}]"
            return f"_div({one}, {_numeric_code(sp.Pow(b, -x, evaluate=False), index, consts)})"
        return f"_pow({_numeric_code(b, index, consts)}, {_numeric_code(x, index, consts)})"
    if isinstance(e, sp.Piecewise):
        code = "_nan"
        for pair in reversed(e.args):
            code = f"({_numeric_code(pair.expr, index, consts)} if {_numeric_code(pair.cond, index, consts)} else {code})"
        return code
    if type(e) in _RELATIONS:
        return f"({_numeric_code(e.args[0], index, consts)} {_RELATIONS[type(e)]} {_numeric_code(e.args[1], index, consts)})"
    if isinstance(e, sp.And):
        return "(" + " and ".join(_numeric_code(a, index, consts) for a in e.args) + ")"
    if isinstance(e, sp.Or):
        return "(" + " or ".join(_numeric_code(a, index, consts) for a in e.args) + ")"
    if isinstance(e, sp.Not):
        return f"(not {_numeric_code(e.args[0], index, consts)})"
    if e.func in _NUMERIC_FUNCTIONS:
        return f"{_NUMERIC_FUNCTIONS[e.func][0]}(" + ", ".join(_numeric_code(a, index, consts) for a in e.args) + ")"
    raise ValueError(f"the operation {type(e).__name__} has no numerical definition")


def numeric_function(expr: Any, names: Iterable[str]) -> Any:
    """Compile ``expr`` into a Python function of the values of ``names``.

    ``numeric_function(expr, names)(*values) -> float``, with ``values`` in the order of
    ``names``. This is the numerical semantics of the harness, used by rule E6, by the tie
    values (rule E4), and available to the evaluation:

    - every value is an IEEE 754 double; numbers of the expression are rounded to the nearest
      double (a number beyond the double range becomes ±inf);
    - ``+``, ``-``, ``*`` and ``/`` are IEEE operations: an overflow gives ±inf, a division of a
      nonzero number by zero gives ±inf, ``0/0``, ``inf - inf`` and ``0*inf`` give NaN; a product
      with negative powers is computed as numerator / denominator;
    - ``a**b`` is the C99 ``pow``: an overflow gives ±inf, ``0**b`` with ``b < 0`` gives inf, a
      negative base with a non-integer exponent gives NaN; ``sqrt(a)`` of a negative ``a`` is NaN;
    - ``exp``, ``sinh``, ``cosh`` overflow to ±inf; ``log(0)`` is -inf and ``log`` of a negative
      number NaN; ``asin`` and ``acos`` outside [-1, 1], and ``sin``, ``cos``, ``tan`` of ±inf
      give NaN; ``atan``, ``atan2``, ``tanh`` and ``Abs`` follow C99;
    - ``sign`` is -1, 0 or 1 (NaN for NaN); ``Min`` and ``Max`` return NaN when an argument is
      NaN;
    - ``Piecewise`` returns the value of the first pair whose condition holds, and NaN when none
      holds; a comparison with NaN is false; ``Eq``/``Ne`` compare exactly.

    Intermediate values may be infinite or NaN without error; only the final value is judged:
    rule E6 requires it to be finite (neither ±inf nor NaN). NumPy with float64 arrays and
    ``numpy.errstate(all="ignore")`` follows the same rules, so an evaluator in NumPy reaches the
    same verdicts, with values that can differ in the last bits where the order of operations
    differs. Raises ``ValueError`` for a symbol without a value or an operation without a
    numerical definition.
    """
    names = list(names)
    index = {n: f"_v{i}" for i, n in enumerate(names)}
    consts: list[float] = []
    body = _numeric_code(expr, index, consts)
    ns = dict(_NUMERIC_NAMESPACE)
    ns["_k"] = tuple(consts)
    ns["__builtins__"] = {}
    try:
        return eval(f"lambda {', '.join(index.values())}: {body}", ns)  # the code is generated above, never taken from input
    except (SyntaxError, RecursionError, MemoryError):
        raise ValueError("the expression is too deeply nested for numerical evaluation") from None


def is_finite_value(y: Any) -> bool:
    """True when ``y`` is a finite real number: the acceptance criterion of rule E6."""
    return isinstance(y, float) and math.isfinite(y) or (isinstance(y, int) and not isinstance(y, bool))


def evaluate_expression(expr: Any, values: Mapping[str, float]) -> float:
    """Evaluate ``expr`` once at ``values`` (name → value) with :func:`numeric_function` semantics."""
    names = sorted(str(s) for s in expr.free_symbols)
    return float(numeric_function(expr, names)(*[float(values[n]) for n in names]))


# ---------------------------------------------------------------------------------------------
# Reading files
# ---------------------------------------------------------------------------------------------


class _DuplicateKey(ValueError):
    pass


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise _DuplicateKey(f"the key {k!r} occurs twice")
        out[k] = v
    return out


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not permitted in a model file; write a finite number")


def read_json(path: Path) -> Any:
    """Read a JSON file strictly: UTF-8, no duplicate keys, no NaN or Infinity (rule F1)."""
    text = path.read_text(encoding="utf-8-sig")
    return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)


def read_training_data(path: Path, trajectory_column: str | None, display_name: str = TRAIN_FILE) -> TrainingData:
    """Read the training table and split it into trajectories.

    Raises ``ValueError`` for a malformed table.
    """
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.reader(fh)]
    if not rows:
        raise ValueError(f"{display_name}: empty file")
    header = tuple(h.strip() for h in rows[0])
    body = [r for r in rows[1:] if r and any(c.strip() for c in r)]
    cols: dict[str, list[float]] = {h: [] for h in header}
    for i, r in enumerate(body):
        if len(r) != len(header):
            raise ValueError(f"{display_name}: data row {i + 1} has {len(r)} values, the header has {len(header)}")
        for h, cell in zip(header, r):
            cols[h].append(float(cell))
    n = len(body)
    blocks: list[tuple[str, int, int]] = []
    if trajectory_column is not None:
        if trajectory_column not in cols:
            raise ValueError(f"{display_name}: no trajectory column {trajectory_column!r}")
        ids = cols[trajectory_column]
        start = 0
        for k in range(1, n + 1):
            if k == n or ids[k] != ids[start]:
                v = ids[start]
                blocks.append((str(int(v)) if float(v).is_integer() else str(v), start, k))
                start = k
    elif n:
        blocks.append(("1", 0, n))
    return TrainingData(file=display_name, header=header, columns=cols, n_rows=n, trajectories=tuple(blocks))


def load_config(path: Path) -> CheckConfig:
    """Read ``check_config.json``."""
    return CheckConfig.from_dict(read_json(Path(path)))


# ---------------------------------------------------------------------------------------------
# Candidate checks
# ---------------------------------------------------------------------------------------------


def _nonempty_text(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _nonempty_record(v: Any) -> bool:
    if _nonempty_text(v):
        return True
    return isinstance(v, list) and bool(v) and all(_nonempty_text(x) for x in v)


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _finite_number(v: Any) -> bool:
    """A JSON number that converts to a finite double (a huge integer does not)."""
    if not _is_number(v):
        return False
    try:
        return math.isfinite(float(v))
    except OverflowError:
        return False


def _hints(config: CheckConfig) -> dict[str, str]:
    hints: dict[str, str] = {
        "e": "write E for Euler's number e",
        "Pi": "write pi for the constant pi",
        "PI": "write pi for the constant pi",
        "inf": "infinite values are not permitted",
        "oo": "infinite values are not permitted",
    }
    for name, roles in config.columns.items():
        if name in config.arguments:
            continue
        if "state_derivative" in roles:
            hints[name] = f"{name} is a state-derivative column (a possible fitting target), not an argument of the expressions"
        else:
            hints[name] = f"{name} is a column but not an argument of the expressions"
    if config.trajectory_column:
        hints[config.trajectory_column] = "the trajectory column is not a model variable"
    for k in config.expression_keys:
        hints.setdefault(k, f"{k} is an expression key, not a variable")
    return hints


def _row_names(rows: Any) -> set[str]:
    """Names of the parameter rows as written, valid or not (for rule E2 of the expressions)."""
    if not isinstance(rows, list):
        return set()
    return {r["name"] for r in rows if isinstance(r, dict) and isinstance(r.get("name"), str)} - _RESERVED_NAMES


def _declared_elsewhere(config: CheckConfig) -> dict[str, str]:
    taken: dict[str, str] = {}
    for n in config.columns:
        taken[n] = "a column"
    if config.trajectory_column:
        taken[config.trajectory_column] = "the trajectory column"
    for n in config.arguments:
        taken[n] = "a declared variable"
    for x in config.delays:
        taken[x.name] = "a delayed variable"
    for k in config.expression_keys:
        taken.setdefault(k, "an expression key")
    for n in config.constants:
        taken[n] = "a given constant"
    for n, _, _ in config.added_functions:
        taken[n] = "an added function"
    return taken


def _parse_parameters(rows: Any, config: CheckConfig, issues: list[Issue]) -> list[Parameter] | None:
    if not isinstance(rows, list):
        issues.append(Issue("F1", "parameters", "must be a list of parameter rows (it may be empty)"))
        return None
    taken = _declared_elsewhere(config)
    params: list[Parameter] = []
    seen: set[str] = set()
    ok = True
    for i, row in enumerate(rows):
        where = f"parameters[{i}]"
        if not isinstance(row, dict):
            issues.append(Issue("F1", where, "must be an object with the fields name, value, unit, type, description"))
            ok = False
            continue
        name = row.get("name")
        if isinstance(name, str):
            where = f"parameter {name}"
        unknown = sorted(set(row) - set(PARAMETER_FIELDS_REQUIRED) - set(PARAMETER_FIELDS_OPTIONAL))
        if unknown:
            issues.append(Issue("F1", where, f"unknown field(s) {', '.join(unknown)}"))
            ok = False
        missing = [f for f in PARAMETER_FIELDS_REQUIRED if f not in row and f != "description"]
        if missing:
            issues.append(Issue("F1", where, f"missing field(s) {', '.join(missing)}"))
            ok = False
            continue
        row_ok = True
        if not isinstance(name, str) or not NAME_PATTERN.match(name) or keyword.iskeyword(name):
            issues.append(Issue("F1", where, f"the name {name!r} is not an identifier (a letter, then letters, digits or underscores)"))
            row_ok = False
        elif name in _RESERVED_NAMES:
            what = "the name of the constant pi or e" if name in CONSTANTS else "a reserved name"
            issues.append(Issue("F1", where, f"the name {name} is {what}; choose another parameter name"))
            row_ok = False
        elif name in taken:
            issues.append(Issue("F1", where, f"the name {name} is already {taken[name]}; choose another parameter name"))
            row_ok = False
        elif name in seen:
            issues.append(Issue("F1", where, "the name occurs in more than one row; repeated uses of a parameter share a single row"))
            row_ok = False
        status = row.get("type")
        if status not in PARAMETER_TYPES:
            issues.append(Issue("F1", where, f"type must be one of fitted, fixed, tied (found {status!r})"))
            row_ok = False
        value = row.get("value")
        if not _finite_number(value):
            shown = value if not isinstance(value, int) or abs(value) < 10**20 else "an integer beyond the double-precision range"
            issues.append(Issue("F1", where, f"value must be a finite number within the double-precision range (found {shown!r})"))
            row_ok = False
        if not _nonempty_text(row.get("unit")):
            issues.append(Issue("F1", where, "unit must be a non-empty text; write \"-\" for a dimensionless quantity"))
            row_ok = False
        eq = row.get("equation")
        if status == "tied":
            if not _nonempty_text(eq):
                issues.append(Issue("F1", where, "a tied parameter needs its defining equation in the field equation"))
                row_ok = False
        elif eq is not None:
            issues.append(Issue("F1", where, "the field equation is only for tied parameters"))
            row_ok = False
        if not _nonempty_text(row.get("description")):
            what = {"fixed": "what the parameter represents and where its value comes from", "tied": "what the parameter represents and why it is tied"}.get(str(status), "what the parameter represents")
            issues.append(Issue("P1", where, f"description is missing or empty; state {what}"))
            row_ok = False
        if not row_ok:
            ok = False
            if isinstance(name, str):
                seen.add(name)
            continue
        seen.add(name)
        params.append(
            Parameter(
                name=name,
                value=float(value),
                unit=row["unit"],
                type=status,
                description=row["description"],
                equation=eq if status == "tied" else None,
            )
        )
    return params if ok else None


def _resolve_ties(
    params: list[Parameter], config: CheckConfig, added: Mapping[str, Any], issues: list[Issue]
) -> tuple[dict[str, sp.Expr], dict[str, float], dict[str, frozenset[str]]] | None:
    """Parse the tie equations, detect cycles, compute the tied values (rule E4)."""
    pnames = [p.name for p in params]
    admissible = set(pnames) | set(config.constants)
    var_hints = {v: f"{v} is a variable; a tie equation may refer only to parameters and given constants" for v in config.arguments}
    parsed: dict[str, sp.Expr] = {}
    used: dict[str, frozenset[str]] = {}
    ok = True
    for p in params:
        if p.type != "tied":
            continue
        where = f"parameter {p.name}"
        try:
            pe = parse_expression(p.equation, admissible, config.functions, added, hints=var_hints)
        except ExpressionError as exc:
            rule = "E4" if exc.rule == "E2" else exc.rule
            issues.append(Issue(rule, where, f"tie equation {p.equation!r}: {exc.message}"))
            ok = False
            continue
        parsed[p.name] = pe.expr
        used[p.name] = pe.names
    if not ok:
        return None
    tied = set(parsed)
    # cycle detection by depth-first search over the tied parameters
    state: dict[str, int] = {}
    order: list[str] = []
    cyclic: set[str] = set()

    def visit(n: str, stack: list[str]) -> None:
        state[n] = 1
        for m in sorted(used[n] & tied):
            if state.get(m) == 1:
                cyc = stack[stack.index(m):] + [m] if m in stack else [n, m]
                cyclic.update(cyc)
                issues.append(Issue("E4", f"parameter {n}", f"the tie equations form a cycle: {' -> '.join(cyc)}"))
            elif state.get(m) is None:
                visit(m, stack + [m])
        state[n] = 2
        order.append(n)

    for n in sorted(tied):
        if state.get(n) is None:
            visit(n, [n])
    if cyclic:
        return None
    values = {p.name: p.value for p in params if p.type != "tied"}
    resolved: dict[str, sp.Expr] = {}
    guard = _Guard()
    try:
        for n in order:  # dependencies first
            resolved[n] = rebuild(parsed[n], {sp.Symbol(m, real=True): resolved[m] for m in used[n] & tied}, guard)
    except ExpressionError as exc:
        issues.append(Issue("E1", f"parameter {n}", f"tie equation {next(p.equation for p in params if p.name == n)!r}: {exc.message}"))
        return None
    recorded = {p.name: p.value for p in params}
    known = {**values, **config.constants}
    for n in order:
        names = sorted(str(sy) for sy in resolved[n].free_symbols)
        try:
            z = numeric_function(resolved[n], names)(*[float(known[m]) for m in names])
        except ValueError as exc:
            issues.append(Issue("E4", f"parameter {n}", f"the tie equation cannot be evaluated: {exc}"))
            ok = False
            continue
        if not is_finite_value(z):
            issues.append(Issue("E4", f"parameter {n}", f"the tie equation yields {z}, not a finite real number"))
            ok = False
            continue
        values[n] = float(z)
        if not math.isclose(recorded[n], z, rel_tol=TIE_RELATIVE_TOLERANCE, abs_tol=TIE_ABSOLUTE_TOLERANCE):
            issues.append(
                Issue(
                    "E4",
                    f"parameter {n}",
                    f"the recorded value {recorded[n]!r} disagrees with the value {z!r} computed from the tie "
                    f"equation {next(p.equation for p in params if p.name == n)!r} (relative tolerance {_TIE_TOL_TEXT})",
                )
            )
            ok = False
    if not ok:
        return None
    return resolved, values, used


def _row_sets(config: CheckConfig, train: TrainingData) -> tuple[list[tuple[int, str, int]], dict[str, list[float | None]]]:
    """Rows at which the expressions are evaluated (rule E6) and the argument values.

    Returns ``(rows, values)``: ``rows`` lists ``(row index, trajectory id, index within the
    trajectory)``; ``values`` maps each argument to its value per row of the table (``None``
    where a delayed value is not available inside the trajectory).
    """
    n = train.n_rows
    values: dict[str, list[float | None]] = {}
    for a in config.arguments:
        if a in train.columns:
            values[a] = list(train.columns[a])
    max_lag = 0
    for dl in config.delays:
        src = train.columns[dl.variable]
        col: list[float | None] = [None] * n
        for _, start, stop in train.trajectories:
            for k in range(start + dl.lag, stop):
                col[k] = src[k - dl.lag]
        values[dl.name] = col
        max_lag = max(max_lag, dl.lag)
    rows: list[tuple[int, str, int]] = []
    for tid, start, stop in train.trajectories:
        for k in range(start + max_lag, stop):
            rows.append((k, tid, k - start))
    return rows, values


_NAN_EXPLANATION = (
    "not a number (NaN): an operation is undefined at this sample, for example the logarithm or the "
    "square root of a negative number, an inverse sine or cosine outside [-1, 1], 0/0, inf - inf, or a "
    "Piecewise in which no condition holds"
)
_INF_EXPLANATION = "infinite: a division by zero or a result beyond the double-precision range (about 1.8e308)"


def _evaluate_on_training_data(
    key: str,
    expr: sp.Expr,
    params: Mapping[str, float],
    config: CheckConfig,
    train: TrainingData,
    rows: list[tuple[int, str, int]],
    values: Mapping[str, list[float | None]],
) -> Issue | None:
    """Rule E6: evaluate ``expr`` on every training row with the semantics of
    :func:`numeric_function`; report the first failure and the number of failing rows."""
    free = {str(s) for s in expr.free_symbols}
    args = [a for a in config.arguments if a in free]
    pnames = [p for p in params if p in free]
    cnames = [c for c in config.constants if c in free]
    try:
        f = numeric_function(expr, args + pnames + cnames)
    except ValueError as exc:
        return Issue("E6", f"expression {key}", f"the expression cannot be evaluated numerically: {exc}")
    fixed = [float(params[p]) for p in pnames] + [float(config.constants[c]) for c in cnames]
    arg_cols = [values[a] for a in args]
    first: tuple[int, str, int, float] | None = None
    count = 0
    for k, tid, j in rows:
        y = f(*[float(c[k]) for c in arg_cols], *fixed)
        if not is_finite_value(y):
            count += 1
            if first is None:
                first = (k, tid, j, y)
    if first is None:
        return None
    k, tid, j, y = first
    problem = _NAN_EXPLANATION if y != y else _INF_EXPLANATION
    at = ", ".join(f"{a} = {values[a][k]!r}" for a in args)
    traj = f", trajectory {tid}, sample {j + 1} of the trajectory" if config.trajectory_column else ""
    return Issue(
        "E6",
        f"expression {key}",
        f"at data row {k + 1} of {train.file} (file line {k + 2}{traj}" + (f"; {at}" if at else "")
        + f") the value is {problem}; {count} of {len(rows)} evaluated rows fail",
    )


def check_candidate_data(
    data: Any,
    label: str,
    file: str,
    config: CheckConfig,
    train: TrainingData,
    added: Mapping[str, Any] | None = None,
) -> CandidateResult:
    """Check the content of one model file (rules F1, E1 to E6, P1).

    ``label`` is the label implied by the file name. Every rule is checked as far as the file
    allows; the evaluation on the training data (E6) runs only when the expressions and the
    parameter table passed their own checks. Returns a :class:`CandidateResult` whose
    ``candidate`` is set when every check passed.
    """
    res = CandidateResult(label=label, file=file)
    issues = res.issues
    added = added_function_lambdas(config) if added is None else added
    if not isinstance(data, dict):
        issues.append(Issue("F1", file, "the model file must contain one JSON object"))
        return res
    unknown = sorted(set(data) - set(CANDIDATE_FIELDS) - set(CANDIDATE_FIELDS_OPTIONAL))
    if unknown:
        hint = "; the label is the file name and is not repeated in the file" if "label" in unknown else ""
        issues.append(Issue("F1", file, f"unknown field(s) {', '.join(unknown)}; the fields are {', '.join(CANDIDATE_FIELDS)}{hint}"))
    missing = [f for f in CANDIDATE_FIELDS if f not in data]
    if config.question_ids and "answers" not in data:
        missing.append("answers")
    if missing:
        issues.append(Issue("F1", file, f"missing field(s) {', '.join(missing)}"))
    # estimation record
    est = data.get("estimation")
    if "estimation" in data:
        if not isinstance(est, dict):
            issues.append(Issue("F1", "estimation", "must be an object"))
        else:
            unk = sorted(set(est) - set(ESTIMATION_FIELDS))
            if unk:
                issues.append(Issue("F1", "estimation", f"unknown field(s) {', '.join(unk)}; the fields are {', '.join(ESTIMATION_FIELDS)}"))
            bad = [f for f in ESTIMATION_FIELDS if not _nonempty_record(est.get(f))]
            if bad:
                issues.append(Issue("F1", "estimation", f"missing or empty field(s) {', '.join(bad)}; each is a text or a list of texts"))
    # discussion
    disc = data.get("discussion")
    if "discussion" in data:
        if not isinstance(disc, dict):
            issues.append(Issue("F1", "discussion", f"must be an object with the sections {', '.join(DISCUSSION_SECTIONS)}"))
        else:
            unk = sorted(set(disc) - set(DISCUSSION_SECTIONS))
            if unk:
                issues.append(Issue("F1", "discussion", f"unknown section(s) {', '.join(unk)}; the sections are {', '.join(DISCUSSION_SECTIONS)}"))
            bad = [s for s in DISCUSSION_SECTIONS if not _nonempty_text(disc.get(s))]
            if bad:
                issues.append(Issue("F1", "discussion", f"missing or empty section(s) {', '.join(bad)}"))
    # answers
    ans = data.get("answers")
    if "answers" in data:
        if not isinstance(ans, dict):
            issues.append(Issue("F1", "answers", "must be an object that maps each question identifier to the answer"))
        else:
            unk = sorted(set(ans) - set(config.question_ids))
            if unk:
                issues.append(Issue("F1", "answers", f"unknown question identifier(s) {', '.join(unk)}; the task's questions are {', '.join(config.question_ids) or 'none'}"))
            bad = [q for q in config.question_ids if not _nonempty_text(ans.get(q))]
            if bad:
                issues.append(Issue("F1", "answers", f"missing or empty answer(s) to {', '.join(bad)}"))
    # predecessor
    pred = data.get("predecessor")
    if "predecessor" in data and pred is not None:
        if not isinstance(pred, str) or not LABEL_PATTERN.match(pred):
            issues.append(Issue("F1", "predecessor", "must be the label of a candidate of the previous pool version, or be left out"))
        elif config.pool_version <= 1:
            issues.append(Issue("F1", "predecessor", "must be left out in the first round (there is no earlier pool version)"))
        elif config.previous_labels and pred not in config.previous_labels:
            issues.append(Issue("F1", "predecessor", f"{pred} is not a label of the previous pool version ({', '.join(config.previous_labels)})"))
    # parameters
    params = _parse_parameters(data.get("parameters"), config, issues) if "parameters" in data else None
    # expressions
    exprs_raw = data.get("expressions")
    parsed: dict[str, ParsedExpression] = {}
    exprs_ok = False
    if "expressions" in data:
        if not isinstance(exprs_raw, dict):
            issues.append(Issue("F1", "expressions", "must be an object that maps each expression key to an expression text"))
        else:
            exprs_ok = True
            required = list(config.expression_keys)
            miss = [k for k in required if k not in exprs_raw]
            extra = [k for k in exprs_raw if k not in required]
            if miss or extra:
                msg = f"the required keys are {', '.join(required)}"
                if miss:
                    msg += f"; missing: {', '.join(miss)}"
                if extra:
                    msg += f"; not permitted: {', '.join(extra)}"
                issues.append(Issue("E5", "expressions", msg))
                exprs_ok = False
            names = set(config.arguments) | _row_names(data.get("parameters")) | set(config.constants)
            hints = _hints(config)
            for k in required:
                if k not in exprs_raw:
                    continue
                try:
                    parsed[k] = parse_expression(exprs_raw[k], names, config.functions, added, hints=hints)
                except ExpressionError as exc:
                    issues.append(Issue(exc.rule, f"expression {k}", exc.message))
                    exprs_ok = False
    # ties and unused parameters
    ties = None
    if params is not None:
        ties = _resolve_ties(params, config, added, issues)
        if exprs_ok:
            # E3 is judged on the names as written; a name that occurs only in its own tie
            # equation is not a use (and forms a cycle, rule E4).
            used_anywhere: set[str] = set()
            for pe in parsed.values():
                used_anywhere |= pe.names
            admissible = {q.name for q in params} | set(config.constants)
            for p in params:
                if p.type == "tied":
                    try:
                        used_anywhere |= parse_expression(p.equation, admissible, config.functions, added).names - {p.name}
                    except ExpressionError:
                        used_anywhere |= admissible  # already reported; do not add E3 on top
            for p in params:
                if p.name not in used_anywhere:
                    issues.append(Issue("E3", f"parameter {p.name}", "is not used in any expression or tie equation; remove the row or use the parameter"))
    nonint = {k: pe.noninteger_literals for k, pe in parsed.items()}
    res.diagnostics["noninteger_literals"] = nonint
    if params is not None:
        res.diagnostics["parameter_counts"] = {s: sum(1 for p in params if p.type == s) for s in PARAMETER_TYPES}
    # rule E6
    resolved_exprs: dict[str, sp.Expr] = {}
    if exprs_ok and params is not None and ties is not None:
        resolved, values, _ = ties
        rows, vals = _row_sets(config, train)
        res.diagnostics["training_rows_evaluated"] = len(rows)
        sub = {sp.Symbol(n, real=True): e for n, e in resolved.items()}
        num_params = {n: v for n, v in values.items() if n not in resolved}
        for k, pe in parsed.items():
            try:
                resolved_exprs[k] = rebuild(pe.expr, sub) if sub else pe.expr
            except ExpressionError as exc:
                issues.append(Issue("E1", f"expression {k}", f"after substituting the tie equations: {exc.message}"))
                continue
            iss = _evaluate_on_training_data(k, resolved_exprs[k], num_params, config, train, rows, vals)
            if iss is not None:
                issues.append(iss)
    else:
        res.notes.append("the evaluation on the training data (E6) was not run because of the errors above")
    if not issues and params is not None and ties is not None:
        resolved, values, _ = ties
        res.candidate = Candidate(
            label=label,
            file=file,
            expression_texts={k: str(exprs_raw[k]) for k in config.expression_keys},
            expressions={k: parsed[k].expr for k in config.expression_keys},
            resolved={k: resolved_exprs[k] for k in config.expression_keys},
            arguments=tuple(config.arguments),
            parameters=tuple(params),
            tie_expressions=dict(resolved),
            values=dict(values),
            constants=dict(config.constants),
            estimation=dict(est),
            discussion={s: disc[s] for s in DISCUSSION_SECTIONS},
            answers={q: ans[q] for q in config.question_ids} if config.question_ids else {},
            predecessor=pred,
            noninteger_literals=nonint,
        )
    return res


_UNEXPECTED = (
    "the checks of this file stopped at an unexpected value ({}); correct the file to the documented "
    "format; the other files are checked independently"
)


def _file_problem(path: Path, root: Path) -> str | None:
    """A reason not to read ``path``: a link leaving the working directory, or an oversized file."""
    try:
        real = path.resolve()
        if path.is_symlink() or real != path.absolute():
            try:
                real.relative_to(root.resolve())
            except ValueError:
                return "the file is a link to a location outside the working directory and is not read"
        size = real.stat().st_size
    except OSError as exc:
        return f"the file cannot be read ({type(exc).__name__})"
    if size > MAX_FILE_BYTES:
        return f"the file has {size} bytes; the limit is {MAX_FILE_BYTES}"
    return None


def check_candidate_file(
    path: Path, config: CheckConfig, train: TrainingData, added: Mapping[str, Any] | None = None, root: Path | None = None
) -> CandidateResult:
    """Read and check one model file ``models/<label>.json`` (rules F1 to P1).

    ``root`` is the working directory; a link that leaves it is not followed. Any unexpected
    error while checking this file becomes an F1 issue of this file only.
    """
    path = Path(path)
    label = path.stem
    file = f"{MODELS_DIR}/{path.name}"
    res = CandidateResult(label=label, file=file)
    if not LABEL_PATTERN.match(label):
        res.issues.append(Issue("F1", file, "the file name is not a valid label (a letter, then up to 31 letters, digits, underscores or hyphens)"))
        return res
    problem = _file_problem(path, root if root is not None else path.parent.parent)
    if problem is not None:
        res.issues.append(Issue("F1", file, problem))
        return res
    try:
        data = read_json(path)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        res.issues.append(Issue("F1", file, f"not valid JSON: {exc}"))
        return res
    except OSError as exc:
        res.issues.append(Issue("F1", file, f"the file cannot be read ({type(exc).__name__})"))
        return res
    try:
        return check_candidate_data(data, label, file, config, train, added)
    except Exception as exc:  # one candidate's error never stops the others
        res = CandidateResult(label=label, file=file)
        res.issues.append(Issue("F1", file, _UNEXPECTED.format(type(exc).__name__)))
        return res


# ---------------------------------------------------------------------------------------------
# Pool file and working directory
# ---------------------------------------------------------------------------------------------

_REC_NOTE = " (the recommendation is treated as absent; this does not affect the acceptance of the candidates)"


def _check_recommendation(data: Mapping[str, Any], usable: list[str] | None, config: CheckConfig, where: str) -> list[Issue]:
    """Issues of the recommendation: the fields ``recommended`` and ``reason`` of the
    pool file. They never affect the candidates or the round."""
    out: list[Issue] = []

    def add(msg: str) -> None:
        out.append(Issue("F1", where, msg + _REC_NOTE))

    if "recommended" not in data:
        add("the field recommended is missing: give a label of the order, or null when you recommend no candidate")
    elif data["recommended"] is not None:
        lab = data["recommended"]
        if not isinstance(lab, str) or usable is None or lab not in usable:
            add(f"the recommended label {lab!r} is not in the order")
        elif usable.index(lab) >= config.pool_cap:
            add(f"the recommended candidate {lab} is outside the pool limit of {config.pool_cap} and is not evaluated")
    if not _nonempty_text(data.get("reason")):
        add("the field reason is missing or empty: say why you recommend this candidate, or why you recommend none")
    return out


def check_pool_data(data: Any, config: CheckConfig, file: str = f"{MODELS_DIR}/{POOL_FILE}") -> tuple[Pool | None, list[Issue], list[str] | None]:
    """Check the content of the pool file (rule F1).

    Returns the pool (``None`` when the file or its order is invalid), the issues that invalidate
    it, and the usable order (the labels of ``order`` without repetitions, ``None`` when
    ``order`` is not a list of texts). An empty order is valid: the pool then contains no
    candidate. Issues of the recommendation (``recommended``, ``reason``)
    do not invalidate the pool; they are kept in :attr:`Pool.recommendation_issues`, and the
    recommendation is then treated as absent (``Pool.recommendation`` is ``None``). When the pool
    is invalid, they are appended to the returned issues.
    """
    issues: list[Issue] = []
    if not isinstance(data, dict):
        return None, [Issue("F1", file, "the pool file must contain one JSON object")], None
    unknown = sorted(set(data) - set(POOL_FIELDS))
    if unknown:
        issues.append(Issue("F1", file, f"unknown field(s) {', '.join(unknown)}; the fields are {', '.join(POOL_FIELDS)}"))
    if "order" not in data:
        issues.append(Issue("F1", file, "missing field order"))
    order = data.get("order")
    usable: list[str] | None = None
    if "order" in data:
        if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
            issues.append(Issue("F1", f"{file} order", "must be a list of candidate labels (it may be empty)"))
        else:
            usable = list(dict.fromkeys(order))
            dup = sorted({x for x in order if order.count(x) > 1})
            if dup:
                issues.append(Issue("F1", f"{file} order", f"duplicate label(s) {', '.join(dup)}"))
            bad = [x for x in order if not LABEL_PATTERN.match(x)]
            if bad:
                issues.append(Issue("F1", f"{file} order", f"invalid label(s) {', '.join(ascii(x) for x in bad)} (a letter, then up to 31 letters, digits, underscores or hyphens)"))
                usable = [x for x in usable if LABEL_PATTERN.match(x)]
    rec_issues = _check_recommendation(data, usable, config, f"{file} recommendation")
    if issues:
        return None, issues + rec_issues, usable
    pool = Pool(
        file=file,
        pool_version=config.pool_version,
        order=tuple(order),
        recommendation=None if rec_issues else {"label": data["recommended"], "reason": data["reason"]},
        recommendation_issues=tuple(rec_issues),
    )
    return pool, [], usable


def check_models(models_dir: Path, config: CheckConfig, train: TrainingData) -> CheckReport:
    """Check the pool file and every model file in ``models_dir``.

    Errors of one candidate never stop the checking of the others. Every model file is checked,
    including files outside the pool limit, which are marked and not evaluated; a label of the
    order without a file and a file outside the order are reported under rule F2. Links leaving
    the working directory are not followed, and at most :data:`MAX_MODEL_FILES` files of at most
    :data:`MAX_FILE_BYTES` bytes each are read (labels of the order first).
    """
    models_dir = Path(models_dir)
    root = models_dir.parent
    pool: Pool | None = None
    pool_issues: list[Issue] = []
    usable: list[str] | None = None
    pool_path = models_dir / POOL_FILE
    pool_file = f"{MODELS_DIR}/{POOL_FILE}"
    models_ok = models_dir.is_dir()
    if models_ok and models_dir.is_symlink():
        try:
            models_dir.resolve().relative_to(root.resolve())
        except ValueError:
            models_ok = False
            pool_issues.append(Issue("F1", f"{MODELS_DIR}/", "the folder is a link to a location outside the working directory and is not read"))
    if not models_dir.is_dir():
        pool_issues.append(Issue("F1", pool_file, f"the folder {MODELS_DIR}/ does not exist"))
    elif not models_ok:
        pass
    elif not pool_path.is_file():
        pool_issues.append(Issue("F1", pool_file, "the pool file is missing"))
    else:
        problem = _file_problem(pool_path, root)
        if problem is not None:
            pool_issues.append(Issue("F1", pool_file, problem))
        else:
            try:
                pool, pool_issues, usable = check_pool_data(read_json(pool_path), config, pool_file)
            except (ValueError, UnicodeDecodeError, RecursionError) as exc:
                pool_issues.append(Issue("F1", pool_file, f"not valid JSON: {exc}"))
            except Exception as exc:  # the candidates are still checked
                pool, usable = None, None
                pool_issues = [Issue("F1", pool_file, _UNEXPECTED.format(type(exc).__name__))]
    files: dict[str, Path] = {}
    if models_ok:
        files = {p.stem: p for p in sorted(models_dir.glob("*.json")) if p.name != POOL_FILE and (p.is_file() or p.is_symlink())}
    first = [lab for lab in (usable or []) if lab in files]
    ranked = first + [lab for lab in files if lab not in first]
    to_check = set(ranked[:MAX_MODEL_FILES])
    folder_issues: list[Issue] = []
    if len(files) > MAX_MODEL_FILES:
        folder_issues.append(Issue("F1", f"{MODELS_DIR}/", f"the folder holds {len(files)} model files; only {MAX_MODEL_FILES} are checked (the labels of the order first)"))
    added = added_function_lambdas(config)
    results: dict[str, CandidateResult] = {}
    for lab, p in files.items():
        if lab in to_check:
            results[lab] = check_candidate_file(p, config, train, added, root)
        else:
            r = CandidateResult(label=lab, file=f"{MODELS_DIR}/{p.name}")
            r.issues.append(Issue("F1", r.file, f"not checked: the folder {MODELS_DIR}/ holds more than {MAX_MODEL_FILES} model files"))
            results[lab] = r
    from_pool = usable is not None
    order = usable if usable is not None else sorted(files)
    for i, lab in enumerate(order):
        if lab not in results:
            r = CandidateResult(label=lab, file=None)
            r.issues.append(Issue("F2", f"candidate {lab}", f"listed in the order of the pool file, but {MODELS_DIR}/{lab}.json does not exist"))
            results[lab] = r
        results[lab].position = i + 1
        results[lab].within_limit = i < config.pool_cap
    if from_pool:
        for lab, r in results.items():
            if r.position is None:
                r.issues.append(Issue("F2", f"{MODELS_DIR}/{lab}.json", "the file is not listed in the order of the pool file and is not evaluated"))
    return CheckReport(
        config=config,
        training_rows=train.n_rows,
        training_trajectories=len(train.trajectories),
        pool=pool,
        pool_issues=pool_issues,
        candidates=results,
        order=list(order),
        order_from_pool=from_pool,
        folder_issues=folder_issues,
    )


def check_directory(workspace: Path, config: CheckConfig | None = None, train_path: Path | None = None) -> CheckReport:
    """Check a working directory as ``check_submission.py`` does.

    Without ``config``, ``check_config.json`` of the directory is read; without ``train_path``,
    the training data of the configuration (``data/train.csv``) in the directory are read.
    """
    ws = Path(workspace)
    cfg = config if config is not None else load_config(ws / CONFIG_FILE)
    tp = Path(train_path) if train_path is not None else ws / cfg.train_file
    train = read_training_data(tp, cfg.trajectory_column, cfg.train_file)
    return check_models(ws / MODELS_DIR, cfg, train)


# ---------------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------------


def format_report(report: CheckReport) -> str:
    """The text report: pool file, one block per candidate with rule identifiers, rules, summary.

    Errors are reported per candidate, with references to the published rules.
    """
    c = report.config
    out: list[str] = []
    out.append("File and expression checks of the candidate files (rules F1 to P1)")
    out.append(
        f"Task {c.task_id} ({c.formulation}); pool limit {c.pool_cap}; training data {c.train_file}: "
        f"{report.training_rows} rows in {report.training_trajectories} trajector{'y' if report.training_trajectories == 1 else 'ies'}"
    )
    out.append("")
    if report.pool_ok:
        p = report.pool
        if p.recommendation is None:
            rec = "invalid, treated as absent"
        elif p.recommended is None:
            rec = "none (the agent recommends no candidate)"
        else:
            rec = p.recommended
        out.append(f"Pool file {p.file}: valid (pool version {p.pool_version}, {len(p.order)} label(s) in the order, recommendation: {rec})")
        for i in p.recommendation_issues:
            out.append(f"  {i.text()}")
        if not p.order:
            out.append("  The pool contains no candidate; the round has no candidate to evaluate.")
        r = report.candidates.get(p.recommended) if p.recommended is not None else None
        if r is not None and not r.passed:
            out.append(f"  note: the recommended candidate {p.recommended} did not pass the checks below")
    else:
        out.append(f"Pool file {MODELS_DIR}/{POOL_FILE}: INVALID")
        for i in report.pool_issues:
            out.append(f"  {i.text()}")
        if not report.order_from_pool:
            out.append("  The candidate files below are listed in the order of their file names.")
    for i in report.folder_issues:
        out.append(f"  {i.text()}")
    out.append("")
    results = report._ordered_results()
    if not results:
        out.append(f"No candidate file found in {MODELS_DIR}/.")
        out.append("")
    for r in results:
        pos = f"position {r.position} of {len(report.order)}" if r.position is not None else "not in the order"
        if r.position is not None and not r.within_limit:
            status = "outside the limit (retained, not evaluated)" + ("; checks passed" if r.passed else "; checks FAILED")
        else:
            status = "passed" if r.passed else "FAILED"
        where = r.file or "no file"
        out.append(f"Candidate {r.label} ({where}, {pos}): {status}")
        for i in r.issues:
            out.append(f"  {i.text()}")
        for n in r.notes:
            out.append(f"  note: {n}")
        if r.passed:
            cand = r.candidate
            counts = r.diagnostics.get("parameter_counts", {})
            out.append(
                f"  diagnostics: {counts.get('fitted', 0)} fitted, {counts.get('fixed', 0)} fixed, {counts.get('tied', 0)} tied parameter(s); "
                f"{cand.total_noninteger_literals} non-integer numeric literal(s); evaluated on "
                f"{r.diagnostics.get('training_rows_evaluated', 0)} training rows"
            )
    violated = sorted({i.rule for i in report.issues}, key=list(RULES).index)
    if violated:
        out.append("")
        out.append("Rules violated:")
        for rid in violated:
            out.append(f"  {rid}: {RULES[rid]}")
    n_within = len(report.within_limit)
    n_pass = len(report.evaluated)
    out.append("")
    out.append(
        f"Summary: {n_pass} of {n_within} candidate(s) within the limit passed the file and expression checks"
        f" ({len(report.outside_limit)} outside the limit); pool file: {'valid' if report.pool_ok else 'invalid'};"
        f" candidates to be evaluated: {', '.join(report.evaluated) or 'none'};"
        f" result: {'PASS' if report.passed else 'FAIL'} (exit status {0 if report.passed else 1})."
    )
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run the checks in a working directory and print the report.

    Exit status: 0 when the pool file is valid and at least one candidate within the limit
    passed, 1 otherwise, 2 when the configuration or the training data cannot be read.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print("usage: python check_submission.py [working-directory]")
        print("Checks models/pool.json and models/<label>.json against the rules F1 to P1.")
        return 0
    ws = Path(args[0]) if args else Path.cwd()
    try:  # a console without UTF-8 (Windows) must not fail on a non-ASCII name in a message
        sys.stdout.reconfigure(errors="backslashreplace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass
    try:
        report = check_directory(ws)
    except (OSError, ValueError) as exc:
        print(f"error: cannot run the checks: {exc}")
        return 2
    sys.stdout.write(format_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
