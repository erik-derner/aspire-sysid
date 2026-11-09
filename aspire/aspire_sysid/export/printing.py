"""Printing of canonical candidate expressions as Matlab and NumPy code, and a restricted
translator that evaluates the generated Matlab statements in Python.

The exports contain the equations; the Matlab files follow the ``[y, info]`` form of
``srProvenance``, and every M-file is re-verified numerically. This module writes its own
printer instead of SymPy's ``octave_code``, because SymPy's Octave printer writes
floating-point numbers with 15 significant digits, the relation ``!=`` (which Matlab rejects) and
multi-line ``Piecewise`` code.

**Printer.** :func:`matlab_code` and :func:`numpy_code` print the node types that the check module
admits: numbers, symbols, ``pi``, ``E``, ``+``, ``*``, ``**``, the functions
``sin cos tan asin acos atan atan2 sinh cosh tanh exp log sqrt Abs sign Min Max``, ``Piecewise``
with relations (``< <= > >= Eq Ne``) and the logical operators ``& | ~``. A number is written in
the shortest spelling that reads back as the same double (Python's ``repr``); a rational number
``p/q`` as the division ``p/q``, which gives the nearest double. Every operation is
parenthesized, so that the precedence of the target language never matters.

**Semantics of the printed code**, compared with the numerical semantics of the harness
(:func:`aspire_sysid.model.checks.numeric_function`; ``aspire/README.md``):

* NumPy code follows the harness exactly in its choice of values: ``Piecewise`` selects the first
  pair whose condition holds (``numpy.select``, NaN when none holds), ``Min`` and ``Max`` return
  NaN when an argument is NaN (``numpy.minimum``/``numpy.maximum``), a non-real result is NaN.
* Matlab code is element-wise over the rows of ``x``: a ``Piecewise`` becomes an auxiliary variable
  that starts as NaN and receives, from the last pair to the first, the value of each pair on the
  rows where its condition holds (:func:`matlab_statements`); the first true pair wins, as in the
  harness, and a value that is not selected never enters the result. Matlab's ``min`` and ``max``
  ignore NaN arguments; ``log``, ``sqrt``, ``asin``, ``acos`` and a power of a negative base
  return complex numbers in Matlab where the harness gives NaN. These differences concern only
  arguments outside the domain on which the expression is real and finite; the numerical
  re-verification (:func:`matlab_evaluate`, Octave) detects them at the sampled points.

**Translator.** :func:`matlab_evaluate` parses the generated Matlab statements with a small
recursive-descent parser (assignments ``name = expr;`` of expressions over numbers, names,
``x(:,k)``, ``ones``/``zeros``/``true``/``NaN`` of ``(size(x,1),1)``, the functions above, and the
masked assignment ``a(m) = b(m);`` of a ``Piecewise``, ``min``/``max``, element-wise operators, relations
and logical operators with Matlab's precedence) and evaluates them with NumPy under Matlab's
rules for ``min``/``max`` (NaN ignored). It executes nothing else and rejects any
other construct.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import numpy as np
import sympy as sp

__all__ = [
    "MATLAB_RESERVED",
    "ExportPrintError",
    "number_text",
    "matlab_code",
    "matlab_statements",
    "PIECEWISE_PREFIX",
    "numpy_code",
    "matlab_evaluate",
    "MatlabSyntaxError",
    "ascii_text",
]


class ExportPrintError(ValueError):
    """An expression contains a node that the exporters cannot print. """


MATLAB_RESERVED: frozenset[str] = frozenset(
    {
        # Matlab keywords (iskeyword)
        "break", "case", "catch", "classdef", "continue", "else", "elseif", "end", "for", "function", "global", "if",
        "otherwise", "parfor", "persistent", "return", "spmd", "switch", "try", "while",
        # names used by the generated files and by srProvenance
        "x", "y", "info", "nargout", "ones", "size", "struct", "theta__", "true", "false",
        "pi", "Inf", "inf", "NaN", "nan", "eps", "i", "j",
        "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sinh", "cosh", "tanh", "exp", "log", "sqrt", "abs",
        "sign", "min", "max",
    }
)
"""Names a parameter must not keep in a generated M-file (it is renamed; Matlab ``iskeyword`` and
the names the generated files use)."""


def number_text(value: Any) -> str:
    """The shortest spelling of a double that reads back as the same double (``Inf``/``NaN`` for Matlab). """
    v = float(value)
    if math.isnan(v):
        return "NaN"
    if math.isinf(v):
        return "Inf" if v > 0 else "-Inf"
    t = repr(v)
    return t


_ASCII = str.maketrans({
    "–": "-", "—": " - ", "−": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "→": "->", "±": "+/-", "≤": "<=", "≥": ">=", "≈": "~", "×": "x",
    "°": " deg", "²": "^2", "³": "^3", "·": "*", "θ": "theta", "ω": "omega",
    "κ": "kappa", "τ": "tau", "π": "pi", "μ": "mu", "σ": "sigma", "Δ": "Delta",
    "∂": "d", "√": "sqrt", "∑": "sum", "∈": " in ", "→": "->", "á": "a", "é": "e",
    "í": "i", "š": "s", "ž": "z", "ř": "r", "č": "c", "ě": "e", "ů": "u", "ý": "y",
})


def ascii_text(text: Any) -> str:
    """``text`` in ASCII for Matlab comments (Matlab on Windows reads M-files in the ANSI code
    page): common symbols are spelled out, other characters become ``?``. """
    return str(text).translate(_ASCII).encode("ascii", "replace").decode("ascii")


# ---------------------------------------------------------------------------------------------
# Printers
# ---------------------------------------------------------------------------------------------

_FUNCS_MATLAB = {
    sp.sin: "sin", sp.cos: "cos", sp.tan: "tan", sp.asin: "asin", sp.acos: "acos", sp.atan: "atan",
    sp.atan2: "atan2", sp.sinh: "sinh", sp.cosh: "cosh", sp.tanh: "tanh", sp.exp: "exp", sp.log: "log",
    sp.Abs: "abs", sp.sign: "sign",
}
_FUNCS_NUMPY = {
    sp.sin: "numpy.sin", sp.cos: "numpy.cos", sp.tan: "numpy.tan", sp.asin: "numpy.arcsin", sp.acos: "numpy.arccos",
    sp.atan: "numpy.arctan", sp.atan2: "numpy.arctan2", sp.sinh: "numpy.sinh", sp.cosh: "numpy.cosh",
    sp.tanh: "numpy.tanh", sp.exp: "numpy.exp", sp.log: "numpy.log", sp.Abs: "numpy.abs", sp.sign: "numpy.sign",
}
_REL = {sp.StrictLessThan: "<", sp.LessThan: "<=", sp.StrictGreaterThan: ">", sp.GreaterThan: ">="}


PIECEWISE_PREFIX = "aspire_pw"
"""Prefix of the auxiliary variables of a ``Piecewise`` in a generated M-file (parameters never take it)."""


class _Printer:
    def __init__(self, names: Mapping[str, str], dialect: str, counter: list[int] | None = None) -> None:
        self.names = dict(names)
        self.m = dialect == "matlab"
        self.pre: list[str] = []
        self.counter = counter if counter is not None else [0]

    def num(self, e: Any) -> str:
        if isinstance(e, sp.Rational) and not isinstance(e, sp.Integer):
            if self.m and abs(e.p) < 2**53 and e.q < 2**53:
                return f"({e.p}/{e.q})"
            return f"({number_text(float(e))})"
        if isinstance(e, sp.Integer):
            v = int(e)
            t = str(v) if abs(v) < 2**53 else number_text(float(v))
            if not self.m and abs(v) < 2**53:
                t = number_text(float(v))
        else:
            t = number_text(float(e))
            if not self.m and t in ("NaN", "Inf", "-Inf"):
                t = {"NaN": "numpy.nan", "Inf": "numpy.inf", "-Inf": "(-numpy.inf)"}[t]
        return f"({t})" if t.startswith("-") else t

    def p(self, e: Any) -> str:  # noqa: C901 - one branch per node type
        m = self.m
        if e.is_Symbol:
            try:
                return self.names[e.name]
            except KeyError:
                raise ExportPrintError(f"the symbol {e.name} has no mapping") from None
        if e is sp.pi:
            return "pi" if m else "numpy.pi"
        if e is sp.E:
            return "exp(1)" if m else "numpy.e"
        if e is sp.oo:
            return "Inf" if m else "numpy.inf"
        if e is -sp.oo:
            return "(-Inf)" if m else "(-numpy.inf)"
        if e in (sp.nan, sp.zoo):
            return "NaN" if m else "numpy.nan"
        if e is sp.true:
            return "true" if m else "True"
        if e is sp.false:
            return "false" if m else "False"
        if isinstance(e, (sp.Integer, sp.Rational, sp.Float)):
            return self.num(e)
        if isinstance(e, sp.Add):
            return "(" + " + ".join(self.p(a) for a in e.args) + ")"
        if isinstance(e, sp.Mul):
            if e.args[0] == -1 and len(e.args) > 1:
                return f"(-{self.p(sp.Mul(*e.args[1:], evaluate=False))})"
            num, den = [], []
            for a in e.args:
                if isinstance(a, sp.Pow) and isinstance(a.exp, (sp.Integer, sp.Rational, sp.Float)) and a.exp < 0:
                    den.append(sp.Pow(a.base, -a.exp, evaluate=False))
                else:
                    num.append(a)
            mul = " .* " if m else " * "
            n_text = "(" + mul.join(self.p(a) for a in num) + ")" if num else ("1" if m else "1.0")
            if not den:
                return n_text
            d_text = "(" + mul.join(self.p(a) for a in den) + ")"
            return f"({n_text} ./ {d_text})" if m else f"({n_text} / {d_text})"
        if isinstance(e, sp.Pow):
            b, x = e.args
            if x == sp.Rational(1, 2):
                return f"sqrt({self.p(b)})" if m else f"numpy.sqrt({self.p(b)})"
            if isinstance(x, (sp.Integer, sp.Rational, sp.Float)) and x < 0:
                inv = sp.Pow(b, -x, evaluate=False)
                return f"(1 ./ {self.p(inv)})" if m else f"(1.0 / {self.p(inv)})"
            return f"({self.p(b)} .^ {self.p(x)})" if m else f"numpy.power({self.p(b)}, {self.p(x)})"
        if isinstance(e, sp.Piecewise):
            return self.piecewise(e)
        if type(e) in _REL:
            return f"({self.p(e.args[0])} {_REL[type(e)]} {self.p(e.args[1])})"
        if isinstance(e, sp.Eq):
            return f"({self.p(e.args[0])} == {self.p(e.args[1])})"
        if isinstance(e, sp.Ne):
            return f"({self.p(e.args[0])} {'~=' if m else '!='} {self.p(e.args[1])})"
        if isinstance(e, sp.And):
            if m:
                return "(" + " & ".join(self.p(a) for a in e.args) + ")"
            return self.nest("numpy.logical_and", [self.p(a) for a in e.args])
        if isinstance(e, sp.Or):
            if m:
                return "(" + " | ".join(self.p(a) for a in e.args) + ")"
            return self.nest("numpy.logical_or", [self.p(a) for a in e.args])
        if isinstance(e, sp.Not):
            return f"(~{self.p(e.args[0])})" if m else f"numpy.logical_not({self.p(e.args[0])})"
        if isinstance(e, (sp.Min, sp.Max)):
            fname = ("min" if isinstance(e, sp.Min) else "max") if m else ("numpy.minimum" if isinstance(e, sp.Min) else "numpy.maximum")
            return self.nest(fname, [self.p(a) for a in e.args])
        table = _FUNCS_MATLAB if m else _FUNCS_NUMPY
        if e.func in table:
            return f"{table[e.func]}(" + ", ".join(self.p(a) for a in e.args) + ")"
        raise ExportPrintError(f"the operation {type(e).__name__} cannot be exported")

    @staticmethod
    def nest(fname: str, parts: list[str]) -> str:
        if len(parts) == 1:
            return parts[0]
        out = parts[-1]
        for a in reversed(parts[:-1]):
            out = f"{fname}({a}, {out})"
        return out

    def piecewise(self, e: sp.Piecewise) -> str:
        pairs = [(pc.expr, pc.cond) for pc in e.args]
        if not self.m:
            conds = ", ".join(self.p(c) for _, c in pairs)
            vals = ", ".join(self.p(v) for v, _ in pairs)
            return f"_piecewise([{conds}], [{vals}])"
        # Matlab: auxiliary statements; the branches are assigned in reverse order, so that the first
        # pair whose condition holds wins; rows where no condition holds keep NaN
        self.counter[0] += 1
        name = f"{PIECEWISE_PREFIX}{self.counter[0]}"
        stmts = [f"{name} = NaN(size(x,1),1);"]
        for v, c in reversed(pairs):
            ct = self.p(c)
            vt = self.p(v)
            stmts += [
                f"{name}_m = ({ct}) & true(size(x,1),1);",
                f"{name}_v = ({vt}) + zeros(size(x,1),1);",
                f"{name}({name}_m) = {name}_v({name}_m);",
            ]
        self.pre += stmts
        return name


def matlab_code(expr: Any, names: Mapping[str, str]) -> str:
    """Matlab text of an expression without ``Piecewise``; ``names`` maps every symbol name to its
    Matlab text (module docstring).  An expression with ``Piecewise``
    needs auxiliary statements: :func:`matlab_statements`."""
    pr = _Printer(names, "matlab")
    code = pr.p(expr)
    if pr.pre:
        raise ExportPrintError("a Piecewise expression needs auxiliary statements; use matlab_statements")
    return code


def matlab_statements(expr: Any, names: Mapping[str, str], target: str, counter: list[int] | None = None) -> list[str]:
    """Matlab statements that assign ``expr`` to ``target``, element-wise over the rows of ``x``.

 Every ``Piecewise`` becomes the
    auxiliary variable ``aspire_pw<n>``: it starts as NaN (no condition holds) and receives the
    value of each pair, from the last pair to the first, on the rows where its condition holds, so
    that the first true pair wins; a value is never multiplied by a mask, and a value that is not
    selected (infinite or NaN) cannot change the result. ``counter`` numbers the auxiliary variables
    across the statements of one file.
    """
    pr = _Printer(names, "matlab", counter)
    code = pr.p(expr)
    return pr.pre + [f"{target} = {code};"]


def numpy_code(expr: Any, names: Mapping[str, str]) -> str:
    """NumPy text of ``expr`` (uses ``numpy`` and a helper ``_piecewise``); see the module docstring. """
    return _Printer(names, "numpy").p(expr)


# ---------------------------------------------------------------------------------------------
# Restricted Matlab translator
# ---------------------------------------------------------------------------------------------


class MatlabSyntaxError(ValueError):
    """A generated Matlab statement contains a construct outside the translated subset. """


_TOKEN = re.compile(
    r"\s*(?:(?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)|(?P<name>[A-Za-z][A-Za-z0-9_]*)"
    r"|(?P<op>\.\*|\./|\.\^|<=|>=|==|~=|[-+*/^<>~&|(),:=;]))"
)

_MATLAB_FUNCS: dict[str, Callable[..., Any]] = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan, "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
    "atan2": np.arctan2, "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh, "exp": np.exp, "log": np.log,
    "sqrt": np.sqrt, "abs": np.abs, "sign": np.sign,
    # Matlab's min and max return the other argument when one is NaN
    "min": np.fmin, "max": np.fmax,
}


def _tokens(text: str) -> list[str]:
    pos, out = 0, []
    text = text.rstrip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise MatlabSyntaxError(f"unexpected text {text[pos:pos + 20]!r}")
        out.append(m.group("num") or m.group("name") or m.group("op"))
        pos = m.end()
    return out


@dataclass
class _Parser:
    toks: list[str]
    env: dict[str, Any]
    x: np.ndarray
    i: int = 0

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self, want: str | None = None) -> str:
        t = self.peek()
        if t is None or (want is not None and t != want):
            raise MatlabSyntaxError(f"expected {want or 'a token'}, found {t!r}")
        self.i += 1
        return t

    # precedence, lowest first: | & relations +- .*./ unary .^
    def expr(self) -> Any:
        a = self.and_()
        while self.peek() == "|":
            self.take()
            b = self.and_()
            a = np.logical_or(_truth(a), _truth(b))
        return a

    def and_(self) -> Any:
        a = self.rel()
        while self.peek() == "&":
            self.take()
            b = self.rel()
            a = np.logical_and(_truth(a), _truth(b))
        return a

    def rel(self) -> Any:
        a = self.add()
        ops = {"<": np.less, "<=": np.less_equal, ">": np.greater, ">=": np.greater_equal, "==": np.equal, "~=": np.not_equal}
        while self.peek() in ops:
            f = ops[self.take()]
            a = f(_num(a), _num(self.add()))
        return a

    def add(self) -> Any:
        a = self.mul()
        while self.peek() in ("+", "-"):
            op = self.take()
            b = self.mul()
            a = _num(a) + _num(b) if op == "+" else _num(a) - _num(b)
        return a

    def mul(self) -> Any:
        a = self.unary()
        while self.peek() in (".*", "./", "*", "/"):
            op = self.take()
            b = self.unary()
            if op in ("*", "/") and np.ndim(a) and np.ndim(b):
                raise MatlabSyntaxError("matrix product or division of two arrays")
            a = _num(a) * _num(b) if op in (".*", "*") else _num(a) / _num(b)
        return a

    def unary(self) -> Any:
        t = self.peek()
        if t == "-":
            self.take()
            return -_num(self.unary())
        if t == "+":
            self.take()
            return _num(self.unary())
        if t == "~":
            self.take()
            return np.logical_not(_truth(self.unary()))
        return self.power()

    def power(self) -> Any:
        a = self.atom()
        while self.peek() in (".^", "^"):
            op = self.take()
            if self.peek() in ("-", "+"):
                sign = -1.0 if self.take() == "-" else 1.0
                b = sign * _num(self.atom())
            else:
                b = self.atom()
            if op == "^" and (np.ndim(a) or np.ndim(b)):
                raise MatlabSyntaxError("matrix power")
            a = np.power(_num(a), _num(b))
        return a

    def args(self) -> list[Any]:
        self.take("(")
        out = [self.expr()]
        while self.peek() == ",":
            self.take()
            out.append(self.expr())
        self.take(")")
        return out

    def atom(self) -> Any:
        t = self.take()
        if t == "(":
            v = self.expr()
            self.take(")")
            return v
        if re.fullmatch(r"(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", t):
            return float(t)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", t):
            raise MatlabSyntaxError(f"unexpected {t!r}")
        if t == "x":
            self.take("(")
            self.take(":")
            self.take(",")
            k = self.take()
            self.take(")")
            col = int(k)
            if not 1 <= col <= self.x.shape[1]:
                raise MatlabSyntaxError(f"x(:,{col}) is outside the {self.x.shape[1]} columns")
            return self.x[:, col - 1]
        if t in ("ones", "zeros", "true", "NaN") and self.peek() == "(":
            for want in ("(", "size", "(", "x", ",", "1", ")", ",", "1", ")"):
                self.take(want)
            n = self.x.shape[0]
            return {"ones": np.ones(n), "zeros": np.zeros(n), "true": np.ones(n, dtype=bool), "NaN": np.full(n, np.nan)}[t]
        consts = {"pi": math.pi, "Inf": math.inf, "NaN": math.nan, "true": True, "false": False}
        if t in consts:
            return consts[t]
        if t in _MATLAB_FUNCS:
            a = self.args()
            if t == "exp" and len(a) == 1:
                return np.exp(_num(a[0]))
            return _MATLAB_FUNCS[t](*[_num(v) for v in a])
        if t in self.env:
            return self.env[t]
        raise MatlabSyntaxError(f"unknown name {t!r}")


def _num(v: Any) -> Any:
    if isinstance(v, (bool, np.bool_)):
        return float(v)
    arr = np.asarray(v)
    if arr.dtype == bool:
        return arr.astype(float)
    return arr.astype(float) if arr.ndim else float(arr)


def _truth(v: Any) -> Any:
    arr = np.asarray(v)
    return arr != 0 if arr.dtype != bool else arr


def matlab_evaluate(statements: list[str], x: np.ndarray) -> dict[str, Any]:
    """Evaluate generated Matlab assignment statements ``name = expr;`` on the regressor matrix
    ``x`` (rows × columns) and return the variables (module docstring: restricted translator).

    Raises :class:`MatlabSyntaxError` for any construct outside the translated subset.

    """
    env: dict[str, Any] = {}
    x = np.atleast_2d(np.asarray(x, dtype=float))
    masked = re.compile(r"^\s*([A-Za-z]\w*)\(([A-Za-z]\w*)\)\s*=\s*([A-Za-z]\w*)\(\2\)\s*;\s*$")
    with np.errstate(all="ignore"):
        for st in statements:
            mm = masked.match(st)
            if mm:
                dst, mask, src = mm.groups()
                if dst not in env or mask not in env or src not in env:
                    raise MatlabSyntaxError(f"undefined variable in {st!r}")
                m = np.asarray(env[mask]) != 0
                out = np.array(env[dst], dtype=float, copy=True)
                out[m] = np.asarray(env[src], dtype=float)[m]
                env[dst] = out
                continue
            toks = _tokens(st)
            if len(toks) < 4 or toks[1] != "=" or toks[-1] != ";" or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", toks[0]):
                raise MatlabSyntaxError(f"not an assignment statement: {st!r}")
            parser = _Parser(toks[2:-1], env, x)
            val = parser.expr()
            if parser.i != len(parser.toks):
                raise MatlabSyntaxError(f"unexpected {parser.toks[parser.i]!r} in {st!r}")
            env[toks[0]] = _num(val)
    return env
