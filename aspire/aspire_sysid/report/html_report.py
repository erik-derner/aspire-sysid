"""Static HTML report of an experiment.

An experiment is one task, run one or more times with identical settings
(:mod:`aspire_sysid.experiment.config`). The report is written for the user of ASPIRE: it shows
the assignment, how it was run, the models that were found and what the agent did. It is
generated from the stored records only; it adds no computation of its own except formatting, the
mean and the sample standard deviation over the runs, and the typesetting of the expressions
(as they are written in the model files). Pages:

* ``index.html``: the assignment (``TASK.md`` as the agent received it), the configuration (model,
  tools, limits, runs, date; the system prompt, ``FORMAT.md`` and the first message, collapsed),
  the results (one table row per run, a row with the mean and the sample standard deviation
  when there are two or more runs, and the recommended model of every run) and the files;
* ``r<NN>.html``: one page per run with the models (a table, the agent's recommendation
  with its reason, and one card per model with its equations, parameter values and errors; the
  details of a model are collapsed), the course of the run (one line per turn, which unfolds to
  the reasoning summary, the agent's text, the commands and files, and the outputs) and the files.

In the agent's texts, a fragment between backticks is typeset as an expression when it is one in
the syntax of ``FORMAT.md`` (the writing rule of ``FORMAT.md`` asks the agent for the backticks);
any other fragment between backticks is shown as code.

The two error columns are kept apart by one caption: the agent recommends a model from the
training data, and the model with the lowest test error is found with the test data, which the
agent cannot access (oracle-based selection, stated with the pool size). The plots
and files are linked from the run folders (relative paths), not copied. The pages need no server
and no network access; the expressions use MathML, which current browsers render natively.
"""

from __future__ import annotations

import ast
import html
import json
import math
import os
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..paths import HARNESS_DIR

__all__ = ["build_report", "run_page_name"]

E = html.escape

# ---------------------------------------------------------------------------------------------
# loading


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


_VISIBLE_GROUPS = {"train": "training data", "val": "validation data"}
"""The agent-visible data groups of the evaluation records; every other group of a record is
sealed. The report reads stored evaluation records only, never a task folder's data."""


def _sealed_group(sealed: dict[str, Any]) -> dict[str, Any] | None:
    """The stored errors on the sealed data: the entry of ``evaluation.candidates[].sealed`` that
    holds trajectories."""
    return next((g for g in sealed.values() if isinstance(g, dict) and "trajectories" in g), None)


def _latest_version(folder: Path) -> int | None:
    versions = [int(p.name[1:]) for p in folder.glob("v*") if p.is_dir() and p.name[1:].isdigit()] if folder.is_dir() else []
    return max(versions) if versions else None


def _relpath(target: Path, start: Path) -> str:
    return Path(os.path.relpath(target.resolve(), start.resolve())).as_posix()


@dataclass
class Candidate:
    """One model of a run: its entry of the evaluation report, its model file and its plots."""

    label: str
    ev: dict[str, Any]
    file: dict[str, Any] | None
    plots: list[tuple[str, str]]  # (data group, path relative to the report folder)

    @property
    def evaluated(self) -> bool:
        return self.ev.get("status") == "evaluated"

    @property
    def train(self) -> float | None:
        return ((self.ev.get("visible") or {}).get("train") or {}).get("pooled_rmse")

    @property
    def val(self) -> float | None:
        return ((self.ev.get("visible") or {}).get("val") or {}).get("pooled_rmse")

    @property
    def test(self) -> float | None:
        return (self.ev.get("sealed") or {}).get("score_S")

    @property
    def eligible(self) -> bool:
        return bool((self.ev.get("sealed") or {}).get("eligible"))


@dataclass
class Run:
    """One run of the experiment, read from its run folder."""

    run_id: str
    folder: Path
    record: dict[str, Any]
    evaluation: dict[str, Any] | None
    pool_version: int | None
    candidates: list[Candidate]
    events: list[dict[str, Any]]

    @property
    def fields(self) -> dict[str, Any]:
        """The fields of the experiment in the run record (``extra.experiment_run``)."""
        return (self.record.get("extra") or {}).get("experiment_run") or {}

    @property
    def index(self) -> int:
        idx = self.fields.get("run_index")
        return idx if isinstance(idx, int) else int(self.run_id[1:]) if self.run_id[1:].isdigit() else 0

    @property
    def recommended(self) -> str | None:
        rec = (self.evaluation or {}).get("recommendation") or {}
        return (rec.get("agent") or {}).get("label") if rec.get("present", True) else None

    @property
    def reason(self) -> str:
        return str((((self.evaluation or {}).get("recommendation") or {}).get("agent") or {}).get("reason") or "")

    @property
    def best(self) -> Candidate | None:
        """The eligible model with the lowest test error (oracle-based selection on test data)."""
        entries = ((((self.evaluation or {}).get("sealed") or {}).get("ranking") or {}).get("entries")) or []
        return self.candidate(entries[0]["label"]) if entries else None

    @property
    def output(self) -> tuple[str, str]:
        out = self.fields.get("output") or {}
        return str(out.get("name") or "y"), unit_text(out.get("unit"))

    @property
    def leak_findings(self) -> list[dict[str, Any]]:
        return list((((self.record.get("extra") or {}).get("leak_scan") or {}).get("findings")) or [])

    def candidate(self, label: str | None) -> Candidate | None:
        return next((c for c in self.candidates if c.label == label), None)


def _load_run(folder: Path, report_dir: Path, *, version: int | None = None, record: dict[str, Any] | None = None,
              events: list[dict[str, Any]] | None = None, run_id: str | None = None) -> Run:
    """Read one run folder. The keyword arguments serve the rounds of an interactive session
    (:mod:`aspire_sysid.report.session_report`): one pool ``version`` of the folder, with the
    ``record`` and the ``events`` of that round in place of the run record and the whole transcript."""
    if record is None:
        record = _json(folder / "run_record.json")
    if version is None:
        version = _latest_version(folder / "evaluation")
    evaluation = _json(folder / "evaluation" / f"v{version}" / "evaluation.json") if version else None
    candidates: list[Candidate] = []
    if evaluation:
        models = folder / "pools" / f"v{version}" / "models"
        plots_dir = folder / "evaluation" / f"v{version}" / "plots"
        for c in sorted(evaluation["candidates"], key=lambda c: c.get("position") or 10**6):
            lab = c["label"]
            f = models / f"{lab}.json"
            try:
                file = _json(f) if f.is_file() else None
            except ValueError:
                file = None
            # the plots of the evaluation report, <label>_<data group>.png; sealed data first
            plots = sorted(((p.stem[len(lab) + 1:], _relpath(p, report_dir)) for p in plots_dir.glob(f"{lab}_*.png")),
                           key=lambda gp: (gp[0] in _VISIBLE_GROUPS, gp[0]))
            candidates.append(Candidate(lab, c, file if isinstance(file, dict) else None, plots))
    if events is None:
        events = []
        tp = folder / "transcript.jsonl"
        if tp.is_file():
            for line in tp.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except ValueError:
                    continue
    return Run(run_id or folder.name, folder, record, evaluation, version, candidates, events)


def _load_task(root: Path, task_id: str | None) -> dict[str, Any] | None:
    if not task_id:
        return None
    p = root / task_id / "task.yaml"
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) if p.is_file() else None
    except (OSError, yaml.YAMLError):
        return None


# ---------------------------------------------------------------------------------------------
# formatting


def sig(x: Any, n: int = 4) -> str:
    """``x`` with ``n`` significant digits; an en dash for a missing value."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        # a value with more than n digits before the decimal point is rounded to an integer, not written with an exponent
        return f"{x:.0f}" if abs(x) >= 10 ** n else f"{x:.{n}g}"
    return E(str(x))


def unit_text(u: Any) -> str:
    return "unit not supplied" if u in (None, "", "not supplied") else str(u)


def with_unit(value: str, unit: str) -> str:
    """A formatted value followed by its unit; no unit for a dimensionless quantity."""
    return value if unit in ("-", "unit not supplied", "") or value == "–" else f"{value} {E(unit)}"


def clock(seconds: Any) -> str:
    """Execution time as minutes and seconds, ``m:ss``."""
    if not isinstance(seconds, (int, float)):
        return ""
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def thousands(x: Any) -> str:
    return "–" if x is None else f"{int(x):,}"


def mean_sd(values: list[Any], digits: int = 4) -> str:
    """Mean ± sample standard deviation over the finite values, with their number when it is
    smaller than the number of runs; an en dash without a finite value."""
    v = [float(x) for x in values if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)]
    if not v:
        return "–"
    note = "" if len(v) == len(values) else f" <span class=muted>({len(v)} of {len(values)} runs)</span>"
    if len(v) == 1:
        return f"{sig(v[0], digits)}{note}"
    return f"{sig(statistics.mean(v), digits)} ± {sig(statistics.stdev(v), 2)}{note}"


_INLINE_CODE = re.compile(r"`([^`]+)`")


def _plain_inline(text: str) -> str:
    """Escaped text with `code` and **bold** rendered."""
    out = []
    for i, part in enumerate(_INLINE_CODE.split(text)):
        if i % 2:
            out.append(f"<code>{E(part)}</code>")
        else:
            out.append(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", E(part)))
    return "".join(out)


def markdown(text: str, inline: Any = None) -> str:
    """Markdown as HTML: headings, paragraphs, bulleted and numbered lists with nested items, tables,
    fenced code, quotations, rules, and the inline constructs of ``inline`` (default: `code` and
    **bold**, for the texts the harness gives the agent, ``TASK.md`` and ``FORMAT.md``;
    :func:`agent_markdown` passes the inline constructs of the agent's texts). The wording is
    unchanged; a construct that is not recognized is shown as a paragraph."""
    _inline = inline or _plain_inline
    lines = text.splitlines()
    out: list[str] = []
    depth: list[int] = []  # indents of the open lists
    tags: list[str] = []   # their elements: ul or ol
    i = 0

    def close_lists(to: int = 0) -> None:
        while len(depth) > to:
            out.append(f"</li></{tags.pop()}>")
            depth.pop()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            close_lists()
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            out.append("<pre>" + E("\n".join(lines[i + 1:j])) + "</pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            close_lists()
            level = min(len(m.group(1)) + 2, 6)
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            close_lists()
            cells = lambda s: [c.strip() for c in s.strip().strip("|").split("|")]  # noqa: E731
            head = cells(stripped)
            j = i + 2
            rows = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(cells(lines[j]))
                j += 1
            out.append("<div class=tw><table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>" for row in rows)
                       + "</tbody></table></div>")
            i = j
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            close_lists()
            out.append("<hr>")
            i += 1
            continue
        if stripped.startswith(">"):
            close_lists()
            quoted = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quoted.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>" + _inline(" ".join(q for q in quoted if q)) + "</blockquote>")
            continue
        m = re.match(r"^(\s*)(?:[-*+]|(\d+)[.)])\s+(.*)$", line)
        if m:
            indent = len(m.group(1))
            while depth and indent < depth[-1]:
                out.append(f"</li></{tags.pop()}>")
                depth.pop()
            if depth and indent == depth[-1]:
                out.append("</li><li>")
            else:
                depth.append(indent)
                tags.append("ol" if m.group(2) else "ul")
                out.append(f"<ol start={int(m.group(2))}><li>" if m.group(2) else "<ul><li>")
            out.append(_inline(m.group(3)))
            i += 1
            continue
        if not stripped:
            close_lists()
            i += 1
            continue
        if depth and line.startswith(" "):  # continuation of a list item
            out.append(" " + _inline(stripped))
            i += 1
            continue
        close_lists()
        para = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(\s*(?:[-*+]|\d+[.)])\s+|\s*#{1,4}\s|\s*```|\s*\||\s*>)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>" + _inline(" ".join(para)) + "</p>")
    close_lists()
    return "".join(out)


# ---------------------------------------------------------------------------------------------
# expressions (text of the model file -> MathML)

_ATOM, _POW, _MUL, _UNARY, _ADD, _CMP, _BOOL = 6, 5, 4, 3, 2, 1, 0
_COMPARE = {ast.Lt: "&lt;", ast.LtE: "≤", ast.Gt: "&gt;", ast.GtE: "≥", ast.Eq: "=", ast.NotEq: "≠"}


def _mo(text: str) -> str:
    return f"<mo>{text}</mo>"


def _paren(body: str) -> str:
    return f"<mrow><mo>(</mo>{body}<mo>)</mo></mrow>"


def _number(v: float) -> tuple[str, int]:
    """A non-negative number with at most 4 significant digits and its precedence; a number in
    exponent notation is written as a product with a power of ten."""
    text = f"{v:.4g}" if isinstance(v, float) else str(v)
    if "e" in text:
        mantissa, exponent = text.split("e")
        power = f"<msup><mn>10</mn><mn>{int(exponent)}</mn></msup>"
        return (power, _POW) if mantissa == "1" else (f"<mrow><mn>{mantissa}</mn><mo>·</mo>{power}</mrow>", _MUL)
    return f"<mn>{text}</mn>", _ATOM


def _ml(node: ast.AST, values: dict[str, float] | None) -> tuple[str, int]:
    """Presentation MathML of one node of an expression and its precedence. The expression is typeset
    as it is written: the order of the terms and the names are those of the model file (``phi``
    stays ``phi`` and ``v_f`` stays ``v_f``), a product has a visible dot, a quotient is a fraction.
    With ``values``, a parameter named there is replaced by its value with 4 significant digits.
    Raises ``ValueError`` for a construct outside the expression syntax of ``FORMAT.md``."""
    if isinstance(node, ast.Expression):
        return _ml(node.body, values)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return f"<mtext>{'true' if node.value else 'false'}</mtext>", _ATOM
        if isinstance(node.value, (int, float)):
            return _number(node.value)
        raise ValueError("constant")
    if isinstance(node, ast.Name):
        if values is not None and node.id in values:
            v = values[node.id]
            return _number(float(v)) if v >= 0 else (_mo("−") + _number(float(-v))[0], _UNARY)
        if node.id == "pi":
            return "<mi>π</mi>", _ATOM
        if node.id == "E":
            return "<mi mathvariant=normal>e</mi>", _ATOM
        return f"<mi>{E(node.id)}</mi>", _ATOM
    if isinstance(node, ast.UnaryOp):
        body, prec = _ml(node.operand, values)
        if isinstance(node.op, ast.UAdd):
            return body, prec
        if isinstance(node.op, ast.USub):
            return _mo("−") + (body if prec >= _MUL else _paren(body)), _UNARY
        if isinstance(node.op, (ast.Invert, ast.Not)):
            return "<mtext>not </mtext>" + (body if prec >= _ATOM else _paren(body)), _BOOL
        raise ValueError("unary operator")
    if isinstance(node, ast.BinOp):
        left, lp = _ml(node.left, values)
        right, rp = _ml(node.right, values)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            sub = isinstance(node.op, ast.Sub)
            if lp < _ADD:
                left = _paren(left)
            if rp < _ADD or rp == _UNARY or (sub and rp == _ADD):
                right = _paren(right)
            return f"<mrow>{left}{_mo('−' if sub else '+')}{right}</mrow>", _ADD
        if isinstance(node.op, ast.Mult):
            if lp < _MUL and lp != _UNARY:
                left = _paren(left)
            if rp < _MUL:
                right = _paren(right)
            return f"<mrow>{left}{_mo('·')}{right}</mrow>", _MUL if lp != _UNARY else _UNARY
        if isinstance(node.op, ast.Div):
            return f"<mfrac><mrow>{left}</mrow><mrow>{right}</mrow></mfrac>", _MUL
        if isinstance(node.op, ast.Pow):
            if lp < _ATOM:
                left = _paren(left)
            return f"<msup>{left if left.startswith('<mrow>') or lp >= _ATOM else '<mrow>' + left + '</mrow>'}<mrow>{right}</mrow></msup>", _POW
        if isinstance(node.op, (ast.BitAnd, ast.BitOr)):
            word = "and" if isinstance(node.op, ast.BitAnd) else "or"
            if lp < _CMP:
                left = _paren(left)
            if rp < _CMP:
                right = _paren(right)
            return f"<mrow>{left}<mtext>&nbsp;{word}&nbsp;</mtext>{right}</mrow>", _BOOL
        raise ValueError("binary operator")
    if isinstance(node, ast.Compare):
        parts = [_ml(node.left, values)[0]]
        for op, comp in zip(node.ops, node.comparators):
            if type(op) not in _COMPARE:
                raise ValueError("comparison")
            parts.append(_mo(_COMPARE[type(op)]) + _ml(comp, values)[0])
        return f"<mrow>{''.join(parts)}</mrow>", _CMP
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        name = node.func.id
        args = [_ml(a, values)[0] for a in node.args if not isinstance(a, ast.Tuple)]
        if name == "sqrt" and len(args) == 1:
            return f"<msqrt>{args[0]}</msqrt>", _ATOM
        if name == "Abs" and len(args) == 1:
            return f"<mrow><mo>|</mo>{args[0]}<mo>|</mo></mrow>", _ATOM
        if name in ("Eq", "Ne") and len(args) == 2:
            return f"<mrow>{args[0]}{_mo('=' if name == 'Eq' else '≠')}{args[1]}</mrow>", _CMP
        if name == "Piecewise":
            rows = []
            for pair in node.args:
                if not isinstance(pair, ast.Tuple) or len(pair.elts) != 2:
                    raise ValueError("Piecewise")
                value = _ml(pair.elts[0], values)[0]
                cond = pair.elts[1]
                when = ("<mtext>otherwise</mtext>" if isinstance(cond, ast.Constant) and cond.value is True
                        else "<mtext>if&nbsp;</mtext>" + _ml(cond, values)[0])
                rows.append(f"<mtr><mtd>{value}</mtd><mtd>{when}</mtd></mtr>")
            return f"<mrow><mo>{{</mo><mtable displaystyle=true columnalign='left left'>{''.join(rows)}</mtable></mrow>", _ATOM
        if len(args) != len(node.args):
            raise ValueError("call")
        shown = {"Min": "min", "Max": "max", "asin": "arcsin", "acos": "arccos", "atan": "arctan", "log": "ln"}.get(name, name)
        return f"<mrow><mi>{E(shown)}</mi><mo>(</mo>{_mo(',').join(args)}<mo>)</mo></mrow>", _ATOM
    raise ValueError(type(node).__name__)


def _mathml_rhs(text: str, values: dict[str, float] | None = None) -> str | None:
    """The right-hand side of an expression as presentation MathML (:func:`_ml`), or ``None`` when
    the text is not an expression in the syntax of ``FORMAT.md`` (it is then shown as text). The
    text is only parsed into Python's syntax tree, never evaluated."""
    try:
        return _ml(ast.parse(text.strip(), mode="eval"), values)[0]
    except (SyntaxError, ValueError, RecursionError):
        return None


_MD_SPAN = re.compile(
    r"`([^`]+)`"                                                    # a fragment between backticks
    r"|\[([^\]\n]+)\]\((https?://[^\s)]+)\)"                      # [text](address)
    r"|(https?://[^\s<>\"'\])]+)"                                   # a bare address
    r"|(?<![\w)*])\*\*(?=\S)(.+?)(?<=\S)\*\*(?![\w(*])"             # **bold**
    r"|(?<![\w*])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![\w*])"       # *italic*
)


def _md_spans(text: str) -> str:
    """Escaped text with the inline constructs of the agent's prose rendered: fragments between
    backticks (:func:`_backticked`), links, **bold**, *italic*; a bold or italic span may contain
    the others. An asterisk of an expression written without backticks, as in ``a*b`` or
    ``x**2 + y**2``, is not a mark: a mark does not follow a letter or a digit."""
    out = []
    pos = 0
    for m in _MD_SPAN.finditer(text):
        out.append(E(text[pos:m.start()]))
        if m.group(1) is not None:
            out.append(_backticked(m.group(1)))
        elif m.group(3):
            out.append(f"<a href='{E(m.group(3), quote=True)}' target=_blank rel=noopener>{_md_spans(m.group(2))}</a>")
        elif m.group(4):
            url = m.group(4).rstrip(".,;:")
            out.append(f"<a href='{E(url, quote=True)}' target=_blank rel=noopener>{E(url)}</a>{E(m.group(4)[len(url):])}")
        elif m.group(5) is not None:
            out.append(f"<b>{_md_spans(m.group(5))}</b>")
        else:
            out.append(f"<i>{_md_spans(m.group(6))}</i>")
        pos = m.end()
    out.append(E(text[pos:]))
    return "".join(out)


def _backticked(part: str) -> str:
    """A fragment between backticks: typeset as an expression when it is one, else shown as code."""
    body = None
    try:
        # an equality `b1 = 2*a1` is typeset side by side; `==`, `<=`, `>=` and `!=` are comparisons
        sides = re.split(r"(?<![=<>!])=(?!=)", part)
        trees = [ast.parse(side.strip(), mode="eval") for side in sides]
        if len(trees) <= 2 and (len(trees) == 2 or not isinstance(trees[0].body, (ast.Name, ast.Constant))):
            body = _mo("=").join(_ml(tree, None)[0] for tree in trees)
    except (SyntaxError, ValueError, RecursionError):
        body = None
    return (f"<code>{E(part)}</code>" if body is None
            else f"<math class=inl title='{E(part, quote=True)}'><mrow>{body}</mrow></math>")


def agent_text(text: Any) -> str:
    """A text written by the agent, for a place inside a line: escaped, with the fragments between
    backticks rendered and the inline Markdown of prose (links, **bold**, *italic*). A fragment
    between backticks that is an expression in the syntax of ``FORMAT.md`` with at least one
    operator, function or comparison is typeset as an expression (the written form is shown on
    hover); any other fragment (a name, a number, a file name) is shown as code. ``FORMAT.md`` asks
    the agent to write an expression inside a text between backticks."""
    return _md_spans(str(text))


def agent_markdown(text: Any) -> str:
    """A text written by the agent or by the vendor's summarizer, as a block: Markdown rendered
    (headings, paragraphs, lists, tables, code, quotations, links, **bold**, *italic*) with the
    fragments between backticks treated as in :func:`agent_text`. Language models write their
    answers in Markdown; the wording is never changed."""
    return f"<div class=md>{markdown(str(text), inline=agent_text)}</div>"


def _mathml_lhs(key: str, spec: dict[str, Any] | None) -> str:
    cols = {c["name"]: c for c in (spec or {}).get("columns") or [] if isinstance(c, dict) and "name" in c}
    c = cols.get(key)
    if c and "state_derivative" in (c.get("roles") or []) and c.get("derivative_of"):
        s = E(c["derivative_of"])
        return f"<mfrac><mrow><mi mathvariant=normal>d</mi><mi>{s}</mi></mrow><mrow><mi mathvariant=normal>d</mi><mi>t</mi></mrow></mfrac>"
    if key.endswith("_next"):
        return f"<mi>{E(key[:-5])}</mi><mo stretchy=false>[</mo><mi>k</mi><mo>+</mo><mn>1</mn><mo stretchy=false>]</mo>"
    return f"<mi>{E(key)}</mi>"


def equation(key: str, rhs: str, spec: dict[str, Any] | None, values: dict[str, float] | None = None) -> str:
    body = _mathml_rhs(rhs, values)
    if body is None:
        return f"<div class=eq><code>{E(key)} = {E(rhs)}</code></div>"
    # inline math in display style: left-aligned like the text, fractions at full size
    return f'<div class=eq><math displaystyle=true style="math-style:normal"><mrow>{_mathml_lhs(key, spec)}<mo>=</mo>{body}</mrow></math></div>'


def _parameter_values(c: Candidate) -> dict[str, float]:
    out = {}
    for p in (c.file or {}).get("parameters") or []:
        if isinstance(p, dict) and isinstance(p.get("value"), (int, float)) and not isinstance(p.get("value"), bool):
            out[str(p.get("name"))] = float(p["value"])
    return out


def _values_line(c: Candidate) -> str:
    """The parameter values in one line: ``kv = 0.8231 (fitted), Ts = 0.2 s (fixed)``."""
    parts = []
    for p in (c.file or {}).get("parameters") or []:
        if not isinstance(p, dict):
            continue
        v = p.get("value")
        value = sig(v, 4) if isinstance(v, (int, float)) else E(str(v))
        parts.append(f"<span class=nw><code>{E(str(p.get('name')))}</code> = {with_unit(value, str(p.get('unit') or '-'))} "
                     f"<span class=muted>({E(str(p.get('type') or 'type not stated'))})</span></span>")
    return ", ".join(parts)


def _expressions(c: Candidate) -> dict[str, str]:
    """The expressions of a model in the order of its model file."""
    written = (c.file or {}).get("expressions")
    return dict(written) if isinstance(written, dict) and written else dict(c.ev.get("expressions") or {})


def _equations(c: Candidate, spec: dict[str, Any] | None, values: dict[str, float] | None = None) -> str:
    return "".join(equation(k, str(t), spec, values) for k, t in _expressions(c).items())


# ---------------------------------------------------------------------------------------------
# page frame

CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#6d6b66;
--grid:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,.10);--accent:#2a78d6;--accent-wash:rgba(42,120,214,.08);
--s1:#2a78d6;--s2:#eb6834;--s7:#4a3aa7;--good:#0ca30c;--warn:#b77900;--bad:#d03b3b;--code:#f1f0ec;
--harness-wash:rgba(235,104,52,.05);--reason-wash:rgba(74,58,167,.05)}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])){color-scheme:dark;--page:#0d0d0d;
--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#9a988f;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);
--accent:#3987e5;--accent-wash:rgba(57,135,229,.12);--s1:#3987e5;--s2:#d95926;--s7:#9085e9;--warn:#fab219;--code:#242422;
--harness-wash:rgba(217,89,38,.08);--reason-wash:rgba(144,133,233,.08)}}
:root[data-theme=dark]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#9a988f;
--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--accent:#3987e5;--accent-wash:rgba(57,135,229,.12);
--s1:#3987e5;--s2:#d95926;--s7:#9085e9;--warn:#fab219;--code:#242422;--harness-wash:rgba(217,89,38,.08);
--reason-wash:rgba(144,133,233,.08)}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1120px;margin:0 auto;padding:24px 16px 64px}
a{color:var(--accent)}
h1{font-size:26px;margin:4px 0 2px;font-weight:650}
h2{font-size:20px;margin:40px 0 10px;font-weight:650}
h3{font-size:16px;margin:18px 0 6px;font-weight:650}
h4,h5,h6{font-size:14.5px;margin:16px 0 4px;font-weight:650}
.sub{color:var(--ink2);margin:0 0 14px}
.muted{color:var(--muted)}
.small{font-size:13px}
.nw{white-space:nowrap}
.crumb{font-size:13px;color:var(--ink2)}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:8px}
button.theme,.bar button{background:var(--surface);color:var(--ink2);border:1px solid var(--ring);border-radius:6px;padding:3px 10px;font-size:12.5px;cursor:pointer}
.warnbox{border:1px solid var(--ring);border-left:4px solid var(--bad);background:var(--surface);padding:8px 12px;border-radius:6px;margin:10px 0}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:14px 18px;margin:10px 0}
.doc p{margin:6px 0 10px}.doc ul{margin:4px 0 10px;padding-left:22px}.doc li{margin:2px 0}
.doc h3:first-child,.doc h4:first-child{margin-top:2px}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--surface)}
.tw{overflow-x:auto;border:1px solid var(--ring);border-radius:10px;margin:8px 0}
th,td{padding:6px 10px;border-bottom:1px solid var(--grid);text-align:left;vertical-align:top}
th{font-weight:600;color:var(--ink2)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr:last-child td{border-bottom:0}
tr.mean td{background:var(--accent-wash);font-weight:600}
table.res th,table.res td{padding:6px 8px}
code,pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12.5px}
pre{white-space:pre-wrap;word-break:break-word;background:var(--code);padding:8px 10px;border-radius:6px;margin:6px 0;max-height:480px;overflow:auto}
dl.kv{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;margin:6px 0}dl.kv dt{color:var(--ink2)}dl.kv dd{margin:0}
.pill{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;border:1px solid var(--ring);color:var(--ink2);white-space:nowrap}
.pill.good::before{content:"✓ ";color:var(--good)}.pill.bad::before{content:"✗ ";color:var(--bad)}.pill.warn::before{content:"! ";color:var(--warn)}
.pill.rec{border-color:var(--accent);color:var(--accent)}.pill.best{border-color:var(--good);color:var(--good)}
.model{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:12px 18px 10px;margin:12px 0}
.model.rec{border-left:4px solid var(--accent)}
.model:target{outline:2px solid var(--accent)}
.model .head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}.model .lab{font-weight:650;font-size:17px}
.eq{overflow-x:auto;overflow-y:hidden;padding:5px 0;font-size:17px}.eq math{text-align:left;margin:0}
math.inl{font-size:1.06em}code math{font-family:inherit}
math{font-size:1.02em}
.vals{font-size:13.5px;color:var(--ink2);margin:4px 0 2px}.errs{font-size:14px;margin:6px 0 8px}
details.more{border-top:1px solid var(--grid);padding:6px 0}
details.more>summary,details.fold>summary{cursor:pointer;color:var(--ink2);font-size:13.5px}
details.more>summary:hover,details.fold>summary:hover{color:var(--ink)}
details.more .in{padding:6px 0 4px}
details.fold{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:8px 14px;margin:8px 0}
details.fold>summary{font-size:14.5px;color:var(--ink)}
.disc p{margin:2px 0 10px}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin:8px 0}
figure{margin:0;background:#fff;border:1px solid var(--ring);border-radius:8px;padding:6px}
figure img{width:100%;height:auto;display:block}figcaption{font-size:12px;color:#52514e;padding:4px 2px 0}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}
.turns{border:1px solid var(--ring);border-radius:10px;background:var(--surface);overflow:hidden}
.trow{display:grid;grid-template-columns:44px 56px 1fr 128px;gap:10px;padding:6px 12px;align-items:baseline;font-size:13.5px}
.thead{font-weight:600;color:var(--ink2);border-bottom:1px solid var(--grid)}
details.turn{border-bottom:1px solid var(--grid)}details.turn:last-child{border-bottom:0}
details.turn>summary{cursor:pointer;list-style:none}details.turn>summary::-webkit-details-marker{display:none}
details.turn>summary:hover{background:var(--accent-wash)}
details.turn[open]>summary{background:var(--accent-wash)}
details.turn.harness>summary{color:var(--ink2);background:var(--harness-wash)}
details.turn.helper>summary .act{padding-left:22px}
.trow .num{text-align:right;font-variant-numeric:tabular-nums}
.trow .act code{word-break:break-word}
.tbody{padding:8px 14px 12px 132px;border-top:1px dashed var(--axis)}
@media (max-width:760px){.tbody{padding-left:14px}.trow{grid-template-columns:34px 48px 1fr 60px}}
.say{white-space:pre-wrap;word-break:break-word;margin:4px 0 6px}
.md{word-break:break-word;margin:4px 0 6px}.md>:first-child{margin-top:0}.md>:last-child{margin-bottom:0}
.md p{margin:4px 0 8px}.md h3,.md h4,.md h5,.md h6{font-size:14.5px;margin:12px 0 4px}
.md ul,.md ol{margin:4px 0 8px;padding-left:22px}.md li{margin:2px 0}.md hr{border:0;border-top:1px solid var(--grid);margin:10px 0}
.md blockquote{margin:6px 0;padding:2px 0 2px 10px;border-left:3px solid var(--grid);color:var(--ink2)}
dl.kv dd .md{margin:0}
details.reason{margin:4px 0 8px;border-left:3px solid var(--s7);background:var(--reason-wash);border-radius:0 6px 6px 0;padding:4px 10px}
details.reason>summary{cursor:pointer;font-size:12.5px;color:var(--ink2)}
.call{margin:8px 0 4px;border:1px solid var(--ring);border-radius:8px;background:var(--code);overflow:hidden}
.callhead{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:5px 10px;font-size:12.5px;color:var(--ink2);border-bottom:1px solid var(--grid)}
.tool{font:600 12.5px ui-monospace,SFMono-Regular,Consolas,monospace;color:var(--ink);background:var(--surface);border:1px solid var(--ring);border-radius:5px;padding:0 6px}
.call pre{margin:0;border-radius:0;background:transparent;max-height:none}
.call pre.arg{padding:8px 10px;color:var(--ink)}
.call details.out,.call details.file{border-top:1px dashed var(--axis)}
.call details>summary{cursor:pointer;padding:5px 10px;font-size:12.5px;color:var(--ink2)}
.call details pre{padding:6px 10px 10px;color:var(--ink2);max-height:520px;overflow:auto}
ul.files{padding-left:20px}ul.files li{margin:2px 0}
"""

JS = """
(function(){
var root=document.documentElement;
try{var t=localStorage.getItem('aspire-report-theme');if(t)root.setAttribute('data-theme',t);}catch(e){}
document.querySelectorAll('button.theme').forEach(function(b){b.addEventListener('click',function(){
 var cur=root.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
 var nxt=cur==='dark'?'light':'dark';root.setAttribute('data-theme',nxt);try{localStorage.setItem('aspire-report-theme',nxt);}catch(e){}});});
document.querySelectorAll('[data-open]').forEach(function(b){b.addEventListener('click',function(){
 var sel=b.getAttribute('data-open'),on=b.getAttribute('data-state')!=='open';
 document.querySelectorAll(sel).forEach(function(d){d.open=on;});
 b.setAttribute('data-state',on?'open':'closed');b.textContent=b.getAttribute(on?'data-hide':'data-show');});});
function openHash(){var id=location.hash.slice(1);if(!id)return;var el=document.getElementById(id);if(!el)return;
 for(var p=el;p;p=p.parentElement){if(p.tagName==='DETAILS')p.open=true;}el.scrollIntoView({block:'start'});}
window.addEventListener('hashchange',openHash);openHash();
})();
"""


def page(title: str, body: str, *, crumb: str = "") -> str:
    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        f"<title>{E(title)}</title><style>{CSS}</style></head><body><main>"
        f'<div class=toolbar><div class=crumb>{crumb}</div><button class=theme type=button>Light / dark</button></div>'
        f"{body}</main><script>{JS}</script></body></html>"
    )


def run_page_name(run_id: str) -> str:
    """File name of the page of a run."""
    return f"{run_id}.html"


DRY_RUN_NOTE = ("<div class=warnbox><b>Dry run.</b> A scripted agent of the harness replaced the language model, to test the "
                "software without cost. The model shown is the format example, not a result.</div>")


def _generated() -> str:
    return f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"


def fold(summary: str, body: str, *, cls: str = "fold", open_: bool = False) -> str:
    return f"<details class={cls}{' open' if open_ else ''}><summary>{summary}</summary><div class=in>{body}</div></details>"


# ---------------------------------------------------------------------------------------------
# quantities of a run

OUTCOME_TEXT = {
    "completed": "Finished by the agent",
    "checks_failed_twice": "Ended because the files failed the check twice",
    "turn_limit": "Ended by the turn limit",
    "time_limit": "Ended by the time limit",
    "cost_limit": "Ended by the cost limit",
    "error": "Ended by an error",
}


def _summary(r: Run) -> dict[str, Any]:
    ev = r.evaluation or {}
    counts = ev.get("counts") or {}
    cons = r.record.get("consumption") or {}
    ranking = ((ev.get("sealed") or {}).get("ranking") or {})
    rec = r.candidate(r.recommended)
    best = r.best
    return {
        "outcome": r.record.get("outcome"),
        "turns": cons.get("turns"),
        "cost": cons.get("cost_usd"),
        "elapsed": cons.get("elapsed_s"),
        "delivered": counts.get("proposed"),
        "evaluated": counts.get("evaluated"),
        "eligible": counts.get("eligible"),
        "rec": rec,
        "rec_train": rec.train if rec and rec.evaluated else None,
        "rec_test": rec.test if rec and rec.eligible else None,
        "best": best,
        "best_test": best.test if best else None,
        "pool_size": ranking.get("pool_size", len(r.candidates) or None),
    }


def _status_line(r: Run) -> str:
    s = _summary(r)
    how = OUTCOME_TEXT.get(str(s["outcome"]), f"Ended ({E(str(s['outcome']))})")
    line = (f"{how} after {s['turns']} turns, {s['elapsed']:.0f} s of execution time and {s['cost']:.2f} USD."
            if isinstance(s["elapsed"], (int, float)) and isinstance(s["cost"], (int, float)) else f"{how}.")
    if s["delivered"] is not None:
        line += f" {s['delivered']} model{'s' if s['delivered'] != 1 else ''} delivered, {s['evaluated']} evaluated."
    else:
        line += " No model was evaluated."
    return line


def _horizon_text(group: dict[str, Any] | None, *, unit: str = "trajectory") -> str:
    """``12 trajectories of 25 samples each (298 scored samples)`` for one data group of a candidate;
    ``unit`` is ``segment`` for data that the harness cut into segments of the evaluation horizon."""
    trajs = (group or {}).get("trajectories") or []
    if not trajs:
        return "no data"
    sizes = sorted({t.get("n_samples") for t in trajs if isinstance(t.get("n_samples"), int)})
    each = (f" of {sizes[0]} samples each" if len(sizes) == 1 else f" of {sizes[0]} to {sizes[-1]} samples" if sizes else "") if len(trajs) > 1 \
        else (f" of {sizes[0]} samples" if sizes else "")
    plural = {"trajectory": "trajectories", "segment": "segments"}[unit]
    return f"{len(trajs)} {plural if len(trajs) != 1 else unit}{each} ({(group or {}).get('scored_samples', '–')} scored samples)"


def _error_caption(r: Run, *, runs: int = 0) -> str:
    """One caption for the error columns: what the errors are, on which data, and what selects the
    two marked models. ``runs``: the number of runs of the table on the experiment page (0: the
    table of one run)."""
    name, unit = r.output
    mode = ((r.evaluation or {}).get("settings") or {}).get("mode")
    first = next((c for c in r.candidates if c.evaluated), None)
    how = {"simulation": f"simulated and measured <code>{E(name)}</code>", "one_step": f"one-step-ahead predicted and measured <code>{E(name)}</code>"}.get(
        str(mode), f"computed and measured <code>{E(name)}</code>")
    text = f"Errors: root mean squared error between {how}" + (f", in {E(unit)}" if unit not in ("-", "unit not supplied") else "") + "."
    if first is not None:
        train = (first.ev.get("visible") or {}).get("train")
        test = _sealed_group(first.ev.get("sealed") or {})
        horizon = ((r.evaluation or {}).get("settings") or {}).get("horizon")
        if horizon:
            text += (f" Training data: {_horizon_text(train, unit='segment')}; the harness cuts the training trajectories into "
                     f"segments of at most {horizon} simulated samples, the length of the test trajectories, so that the two "
                     "errors are comparable.")
        else:
            text += f" Training data: {_horizon_text(train)}."
        text += f" Test data, which the agent cannot access: {_horizon_text(test)}."
        sizes = lambda g: {t.get("n_samples") for t in (g or {}).get("trajectories") or []}  # noqa: E731
        if mode == "simulation" and not horizon and sizes(train) and sizes(test) and sizes(train) != sizes(test):
            text += (" A simulation error grows with the length of the trajectory, and the training and the test trajectories "
                     "differ in length, so the two errors are not directly comparable.")
    n = len(r.candidates)
    among = "the models of each run" if runs else f"the {n} models of this run" if n != 1 else "the models of this run (here one model)"
    text += (" The agent recommends a model from the training data. The model with the lowest test error is found with the "
             f"test data, in hindsight, among {among}; the agent could not make this choice.")
    if runs >= 2:
        text += (f" First row: mean ± sample standard deviation over the {runs} runs (divisor: number of runs minus one).")
    elif runs == 1:
        text += " This is a single run; the responses of the language model vary between runs."
    return text


def _marks(r: Run, c: Candidate) -> str:
    out = []
    if c.label == r.recommended:
        out.append("<span class='pill rec'>recommended by the agent</span>")
    if r.best is not None and c.label == r.best.label:
        out.append("<span class='pill best'>lowest test error</span>")
    if not c.evaluated:
        out.append(f"<span class='pill bad'>not evaluated: {E(str(c.ev.get('status') or '').replace('_', ' '))}</span>")
    elif not c.eligible:
        out.append("<span class='pill bad'>excluded</span>")
    return " ".join(out)


# ---------------------------------------------------------------------------------------------
# index page


def _recommended_block(r: Run, spec: dict[str, Any] | None) -> str:
    """The recommended model of a run for the index: equations, values, errors, link to the run page."""
    link = f"<a href='{E(run_page_name(r.run_id))}'>all models and the course of run {r.index}</a>"
    c = r.candidate(r.recommended)
    name, unit = r.output
    if c is None:
        why = E(r.reason) if r.reason else "The record holds no reason."
        return (f"<div class=model><div class=head><span class=lab>Run {r.index}</span><span class=muted>no model recommended</span></div>"
                f"<p>{_status_line(r)} {why}</p><p class=small>{link}</p></div>")
    return (f"<div class='model rec'><div class=head><span class=lab>Run {r.index}: {E(c.label)}</span></div>"
            + _equations(c, spec) + f"<div class=vals>{_values_line(c)}</div>"
            f"<div class=errs>Training error of <code>{E(name)}</code>: {with_unit(sig(c.train), unit)} · "
            f"test error: <b>{with_unit(sig(c.test), unit)}</b></div>"
            f"<p class=small>{link}</p></div>")


def _index(exp: dict[str, Any], runs: list[Run], missing: list[str], spec: dict[str, Any] | None, format_text: str | None, exp_dir: Path, report_dir: Path) -> str:
    first = runs[0] if runs else None
    title = str(((first.record.get("task") or {}).get("title") if first else None) or (spec or {}).get("title") or exp.get("task") or exp.get("id"))
    b = [f"<h1>{E(title)}</h1>", f"<p class=sub>Experiment <code>{E(str(exp.get('id')))}</code> · {_generated()}</p>"]
    if first is None:
        b.append("<p>No run of this experiment has finished yet.</p>")
        return page(title, "".join(b))
    texts = first.record.get("texts") or {}
    if first.fields.get("dry_run"):
        b.append(DRY_RUN_NOTE)

    # 1 assignment
    b.append("<h2>1 Assignment</h2><p class=sub>The task brief <code>TASK.md</code>, as the agent received it.</p>")
    b.append(f"<div class='card doc'>{markdown(str(texts.get('brief') or ''))}</div>")

    # 2 configuration
    cfg = (first.record.get("configuration") or {}).get("settings") or {}
    req = cfg.get("requests") or {}
    rb = first.fields.get("round_budget") or {}
    dates = sorted(str(r.record.get("created_at") or "") for r in runs)
    day = dates[0][:10] if dates[0][:10] == dates[-1][:10] else f"{dates[0][:10]} to {dates[-1][:10]}"
    planned = exp.get("runs")
    runs_text = f"{len(runs)}" + (f" of {planned} planned" if isinstance(planned, int) and planned != len(runs) else "")
    runs_text += (" (each run is a separate session of the agent with identical settings; the runs differ only in the "
                  "responses of the language model)") if (planned or len(runs)) != 1 else ""
    b.append("<h2>2 Configuration</h2><div class=card><dl class=kv>"
             f"<dt>Model</dt><dd><code>{E(str((first.record.get('model') or {}).get('id')))}</code>"
             + (f", reasoning effort {E(str(req.get('reasoning_effort')))}" if req.get("reasoning_effort") else "") + "</dd>"
             f"<dt>Tools</dt><dd>{', '.join(f'<code>{E(str(t))}</code>' for t in cfg.get('tools') or []) or '–'}</dd>"
             + "".join(f"<dt><code>{E(str(k))}</code></dt><dd>{E(str(v))}</dd>" for k, v in (first.fields.get("web_backends") or {}).items())
             + f"<dt>Limits per run</dt><dd>{rb.get('turns', '–')} turns, {sig(rb.get('seconds'), 6)} s of execution time, {sig(rb.get('usd'))} USD</dd>"
             f"<dt>Runs</dt><dd>{runs_text}</dd>"
             f"<dt>Date</dt><dd>{E(day)}</dd></dl></div>")
    same_prompt = len({(r.record.get("texts") or {}).get("system_prompt_sha256") for r in runs}) == 1
    b.append(fold("System prompt" + ("" if same_prompt else " (of run 1; the runs differ)"),
                  f"<div class=say>{E(str(texts.get('system_prompt') or ''))}</div>"))
    if format_text is not None:
        b.append(fold("<code>FORMAT.md</code>, the description of the model files", f"<div class=doc>{markdown(format_text)}</div>"))
    b.append(fold("First message to the agent", f"<div class=say>{E(str(texts.get('first_user_message') or ''))}</div>"))

    # 3 results
    name, unit = first.output
    u = f" ({E(unit)})" if unit not in ("-", "unit not supplied") else ""
    sums = [_summary(r) for r in runs]
    rows = []
    if len(runs) >= 2:
        rows.append("<tr class=mean><td class=nw>Mean ± deviation</td><td></td>"
                    f"<td class=n>{mean_sd([s['rec_train'] for s in sums])}</td><td class=n>{mean_sd([s['rec_test'] for s in sums])}</td>"
                    f"<td></td><td class=n>{mean_sd([s['best_test'] for s in sums])}</td>"
                    f"<td class=n>{mean_sd([s['delivered'] for s in sums], 3)}</td><td class=n>{mean_sd([s['turns'] for s in sums], 3)}</td>"
                    f"<td class=n>{mean_sd([s['cost'] for s in sums], 3)}</td><td class=n>{mean_sd([s['elapsed'] for s in sums], 3)}</td></tr>")
    for r, s in zip(runs, sums):
        rec, best = s["rec"], s["best"]
        rows.append(f"<tr><td class=nw><a href='{E(run_page_name(r.run_id))}'>Run {r.index}</a></td>"
                    f"<td>{E(rec.label) if rec else '<span class=muted>none</span>'}</td>"
                    f"<td class=n>{sig(s['rec_train'])}</td><td class=n>{sig(s['rec_test'])}</td>"
                    f"<td>{E(best.label) if best else '<span class=muted>none</span>'}</td><td class=n>{sig(s['best_test'])}</td>"
                    f"<td class=n>{s['delivered'] if s['delivered'] is not None else '–'}</td><td class=n>{s['turns']}</td>"
                    f"<td class=n>{sig(s['cost'], 3)}</td><td class=n>{sig(s['elapsed'], 3)}</td></tr>")
    for rid in missing:
        rows.append(f"<tr><td class=nw>{E(rid)}</td><td colspan=9 class=muted>not finished: the run folder has no run record</td></tr>")
    b.append("<h2>3 Results</h2>")
    b.append("<div class=tw><table class=res><thead><tr><th rowspan=2>Run</th><th colspan=3>Model recommended by the agent</th>"
             "<th colspan=2>Model with the lowest test error</th><th rowspan=2 class=n>Models</th><th rowspan=2 class=n>Turns</th>"
             "<th rowspan=2 class=n>Cost<br>(USD)</th><th rowspan=2 class=n>Time<br>(s)</th></tr>"
             f"<tr><th>Model</th><th class=n>Training<br>error{u}</th><th class=n>Test<br>error{u}</th><th>Model</th><th class=n>Test<br>error{u}</th></tr>"
             "</thead><tbody>" + "".join(rows) + "</tbody></table></div>")
    b.append(f"<p class='muted small'>{_error_caption(first, runs=len(runs))}</p>")
    findings = [(r, f) for r in runs for f in r.leak_findings]
    if findings:
        b.append("<div class=warnbox><b>Sealed information was found in the files or the transcript of "
                 f"{len({r.run_id for r, _ in findings})} run(s).</b> The harness searches every run for test values and sealed file names; "
                 "see the run pages.</div>")
    b.append("<h3>The recommended model of each run</h3>")
    b += [_recommended_block(r, spec) for r in runs]

    # 4 files
    items = [f"<li><a href='{E(run_page_name(r.run_id))}'>Run {r.index}</a>: all models and the course of the run</li>" for r in runs]
    for label, rel in (("Statistics over the runs (Markdown)", "aggregate.md"), ("Statistics over the runs (JSON)", "aggregate.json"),
                       ("Experiment settings", "experiment.yaml")):
        if (exp_dir / rel).is_file():
            items.append(f"<li><a href='{E(_relpath(exp_dir / rel, report_dir))}' target=_blank rel=noopener>{E(label)}</a> "
                         f"<span class=muted><code>{E(rel)}</code></span></li>")
    b.append("<h2>4 Files</h2><ul class=files>" + "".join(items) + "</ul>")
    rev = ((first.record.get("harness") or {}).get("code_revision") or {})
    b.append(f"<p class='muted small'>ASPIRE harness (<code>aspire-sysid</code>) version {E(str((first.record.get('harness') or {}).get('version')))}"
             + (f", commit <code>{E(str(rev.get('commit'))[:12])}</code>" if rev.get("commit") else "") + ".</p>")
    return page(title, "".join(b))


# ---------------------------------------------------------------------------------------------
# run page: models

DISCUSSION_TITLES = [("family", "Model family"), ("interpretation", "Interpretation of the terms"),
                     ("origin", "How the agent arrived at the expression"), ("limitations", "Limitations")]


def _models_table(r: Run) -> str:
    name, unit = r.output
    u = f" ({E(unit)})" if unit not in ("-", "unit not supplied") else ""
    with_val = any(c.val is not None for c in r.candidates)
    rows = []
    for c in r.candidates:
        cx = c.ev.get("complexity") or {}
        rows.append(f"<tr><td><a href='#model-{E(c.label)}'><b>{E(c.label)}</b></a></td>"
                    f"<td class=n>{cx.get('fitted_parameters', '–')}</td><td class=n>{sig(c.train)}</td>"
                    + (f"<td class=n>{sig(c.val)}</td>" if with_val else "")
                    + f"<td class=n>{sig(c.test)}</td><td>{_marks(r, c)}</td></tr>")
    return ("<div class=tw><table><thead><tr><th>Model</th><th class=n>Fitted parameters</th>"
            f"<th class=n>Training error of <code>{E(name)}</code>{u}</th>"
            + (f"<th class=n>Validation error{u}</th>" if with_val else "")
            + f"<th class=n>Test error of <code>{E(name)}</code>{u}</th><th></th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            f"<p class='muted small'>The models are listed in the agent's order. {_error_caption(r)}</p>")


def _parameters_block(c: Candidate) -> str:
    f = c.file or {}
    parts = []
    params = [p for p in f.get("parameters") or [] if isinstance(p, dict)]
    if params:
        parts.append("<div class=tw><table><thead><tr><th>Name</th><th class=n>Value</th><th>Unit</th><th>Type</th>"
                     "<th>Description</th></tr></thead><tbody>")
        for p in params:
            v = p.get("value")
            parts.append(f"<tr><td><code>{E(str(p.get('name')))}</code></td><td class=n>{sig(v, 6) if isinstance(v, (int, float)) else E(str(v))}</td>"
                         f"<td>{E(str(p.get('unit', '')))}</td><td>{E(str(p.get('type', '')))}"
                         + (f" (<code>{E(str(p['equation']))}</code>)" if p.get("equation") else "")
                         + f"</td><td>{agent_text(p.get('description', ''))}</td></tr>")
        parts.append("</tbody></table></div>")
    est = f.get("estimation") or {}
    if isinstance(est, dict) and est:
        titles = {"criterion": "Criterion minimized", "data": "Data", "method": "Method", "script": "Script"}
        parts.append("<dl class=kv>" + "".join(f"<dt>{E(titles.get(k, k.replace('_', ' ').capitalize()))}</dt><dd>{agent_markdown(v)}</dd>"
                                               for k, v in est.items()) + "</dl>")
    return "".join(parts) or "<p class=muted>The model file holds no parameter table and no estimation record.</p>"


def _explanation_block(c: Candidate) -> str:
    disc = (c.file or {}).get("discussion") or {}
    if not isinstance(disc, dict) or not disc:
        return "<p class=muted>The model file holds no explanation.</p>"
    parts = []
    seen = set()
    for k, title in DISCUSSION_TITLES:
        if disc.get(k):
            seen.add(k)
            parts.append(f"<b>{E(title)}</b>{agent_markdown(disc[k])}")
    for k, v in disc.items():
        if k not in seen and v:
            parts.append(f"<b>{E(k.replace('_', ' ').capitalize())}</b>{agent_markdown(v)}")
    answers = (c.file or {}).get("answers") or {}
    if isinstance(answers, dict):
        for k, v in answers.items():
            parts.append(f"<b>Answer to question {E(str(k))}</b>{agent_markdown(v)}")
    return "<div class=disc>" + "".join(parts) + "</div>"


def _errors_block(r: Run, c: Candidate) -> str:
    name, unit = r.output
    sealed = c.ev.get("sealed") or {}
    parts = []
    if c.plots:
        parts.append("<div class=figs>")
        for group, rel in c.plots:
            data = _VISIBLE_GROUPS.get(group, f"{group} data")
            parts.append(f"<figure><a href='{E(rel)}' target=_blank rel=noopener><img loading=lazy src='{E(rel)}' alt='{E(c.label)}, {E(data)}'></a>"
                         f"<figcaption>{E(c.label)}, {E(data)}. Upper axes: measured output and model output; "
                         "lower axes: residual (model output minus measured output).</figcaption></figure>")
        parts.append("</div>")
    parts.append("<div class=tw><table><thead><tr><th>Data</th><th>Trajectory</th><th class=n>Scored samples</th>"
                 "<th class=n>RMSE</th><th class=n>NRMSE</th><th class=n>R²</th><th>Failure</th></tr></thead><tbody>")
    groups = [("training data", (c.ev.get("visible") or {}).get("train")), ("validation data", (c.ev.get("visible") or {}).get("val")),
              ("test data", _sealed_group(sealed))]
    for gname, g in groups:
        for t in (g or {}).get("trajectories") or []:
            m = t.get("measures") or {}
            parts.append(f"<tr><td>{E(gname)}</td><td>{E(str(t.get('trajectory')))}</td>"
                         f"<td class=n>{t.get('completed_samples')} of {t.get('required_samples')}</td>"
                         f"<td class=n>{sig(m.get('rmse'))}</td><td class=n>{sig(m.get('nrmse'))}</td>"
                         f"<td class=n>{sig(m.get('r2'))}</td><td>{E(str(t.get('failure') or 'none'))}</td></tr>")
    parts.append(f"</tbody></table></div><p class='muted small'>RMSE of <code>{E(name)}</code>"
                 + (f" in {E(unit)}" if unit not in ("-", "unit not supplied") else "")
                 + "; NRMSE = RMSE / σ and R² = 1 − SSE / Σ(y[k] − μ)², with μ and σ the mean and the population standard "
                 "deviation of the measured output on the scored samples.</p>")
    return "".join(parts)


def _requirements_block(c: Candidate) -> str:
    rows = []
    for q in c.ev.get("requirements") or []:
        outcome = q.get("outcome") if q.get("kind") == "formal" else "assessed by the human"
        rows.append(f"<tr><td>{E(str(q.get('id')))}</td><td>{E(str(q.get('statement') or ''))}</td>"
                    f"<td>{E(str(outcome))}{' (excludes the model)' if q.get('excludes') else ''}</td>"
                    f"<td>{E(str(q.get('detail') or ''))}</td></tr>")
    return ("<div class=tw><table><thead><tr><th>Requirement</th><th>Statement</th><th>Outcome</th><th>Detail</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def _model_card(r: Run, c: Candidate, spec: dict[str, Any] | None) -> str:
    name, unit = r.output
    sealed = c.ev.get("sealed") or {}
    head = f"<div class=head><span class=lab>{E(c.label)}</span>{_marks(r, c)}</div>"
    body = [_equations(c, spec)]
    values = _values_line(c)
    if values:
        body.append(f"<div class=vals>{values}</div>")
    if c.evaluated:
        body.append(f"<div class=errs>Training error of <code>{E(name)}</code>: {with_unit(sig(c.train), unit)} · "
                    + (f"validation error: {with_unit(sig(c.val), unit)} · " if c.val is not None else "")
                    + f"test error: <b>{with_unit(sig(c.test), unit)}</b></div>")
        if not c.eligible:
            why = "; ".join(str(x) for x in sealed.get("ineligibility") or []) or "no finite test error"
            body.append(f"<p><span class='pill bad'>excluded</span> {E(why)}</p>")
    else:
        issues = "; ".join(str(i) for i in ((c.ev.get("checks") or {}).get("issues") or []))
        body.append(f"<p class=muted>This model was not evaluated ({E(str(c.ev.get('status') or '').replace('_', ' '))})"
                    + (f": {E(issues)}" if issues else "") + ".</p>")
    more = []
    written = "".join(f"<pre>{E(k)} = {E(str(t))}</pre>" for k, t in _expressions(c).items())
    more.append(fold("Equations as written in the model file", written, cls="more"))
    more.append(fold("Equations with the values substituted",
                     _equations(c, spec, _parameter_values(c))
                     + "<p class='muted small'>Every parameter is replaced by its value with 4 significant digits.</p>", cls="more"))
    more.append(fold("Parameters and estimation", _parameters_block(c), cls="more"))
    more.append(fold("The agent's explanation", _explanation_block(c), cls="more"))
    if c.ev.get("requirements"):
        more.append(fold("Physical requirements", _requirements_block(c), cls="more"))
    if c.evaluated:
        more.append(fold(f"Plots of simulated and measured <code>{E(name)}</code>, and errors per trajectory" if c.plots
                         else f"Errors of <code>{E(name)}</code> per trajectory",
                         _errors_block(r, c), cls="more"))
    cls = "model rec" if c.label == r.recommended else "model"
    return f"<div class='{cls}' id='model-{E(c.label)}'>{head}{''.join(body)}{''.join(more)}</div>"


# ---------------------------------------------------------------------------------------------
# run page: course of the run

HARNESS_MESSAGES = {
    "user_message": "opening message to the agent",
    "continuation": "continuation message to the agent",
    "reminder": "budget reminder to the agent",
    "check_failure_message": "report of the failed check to the agent",
    "budget_termination": "message that a limit ended the round",
    "user_question": "question of the agent to the user",
    "user_answer": "answer of the user",
}
"""Execution messages of the harness to the agent and of interactive operation."""

SESSION_LINES = {
    "round_completion": "told the agent the results it may see: the checks and the errors on the training data",
    "user_shown_sealed_results": "showed the results of the round to the user, the test errors included",
    "permitted_results_screened": "withheld a part of the results from the agent, because it matched sealed information",
    "task_change": "the user's change of the task takes effect",
    "task_change_refused": "a change of the task was not applied",
    "brief_regenerated": "wrote TASK.md again for the changed task",
}
"""Lines of the course of a round for the events of interactive operation."""


def _status_pill(res: dict[str, Any]) -> str:
    det = res.get("details") or {}
    if not res:
        return "<span class='pill warn'>no result recorded</span>"
    if res.get("denied"):
        return "<span class='pill bad'>refused</span>"
    if det.get("timed_out"):
        return f"<span class='pill warn'>time limit of {det.get('timeout_s', 0):.0f} s reached</span>"
    if "exit_code" in det:
        return f"<span class='pill {'good' if det['exit_code'] == 0 else 'bad'}'>exit status {det['exit_code']}</span>"
    if res.get("is_error"):
        return "<span class='pill bad'>error</span>"
    return "<span class='pill good'>done</span>"


def _call_block(call: dict[str, Any], res: dict[str, Any]) -> str:
    """One tool call with its arguments and the result as sent to the agent."""
    name = str(call.get("name") or call.get("tool") or "?")
    args = call.get("arguments") or {}
    head = [f"<span class=tool>{E(name)}</span>", _status_pill(res)]
    if isinstance(res.get("duration_s"), (int, float)):
        head.append(f"<span>{res['duration_s']:.1f} s</span>")
    body = []
    if "command" in args:
        body.append(f"<pre class=arg>$ {E(str(args['command']))}</pre>")
    elif name == "write_file":
        content = str(args.get("content") or "")
        body.append(f"<pre class=arg>{E(str(args.get('path')))}</pre>"
                    f"<details class=file><summary>file content written ({len(content):,} characters)</summary>"
                    f"<pre>{E(content)}</pre></details>")
    elif "path" in args:
        rest = ", ".join(f"{k} {v}" for k, v in args.items() if k != "path")
        body.append(f"<pre class=arg>{E(str(args.get('path') or '.'))}{E(' (' + rest + ')') if rest else ''}</pre>")
    else:
        body.append(f"<pre class=arg>{E(json.dumps(args, ensure_ascii=False, indent=1))}</pre>")
    if call.get("arguments_error"):
        body.append(f"<pre class=arg>arguments could not be read: {E(str(call['arguments_error']))}\n{E(str(call.get('raw_arguments')))}</pre>")
    sent = res.get("content_sent", res.get("content"))
    if sent is not None:
        sent = str(sent)
        lines = sent.count("\n") + 1
        note = f"; shortened for the agent, the record holds {res.get('content_chars', 0):,} characters" if res.get("truncated_for_agent") else ""
        is_open = " open" if (len(sent) <= 700 and lines <= 12) else ""
        body.append(f"<details class=out{is_open}><summary>output as sent to the agent ({len(sent):,} characters, "
                    f"{lines} lines{note})</summary><pre>{E(sent)}</pre></details>")
    return f"<div class=call><div class=callhead>{''.join(head)}</div>{''.join(body)}</div>"


def _short(text: str, n: int = 90) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line if len(line) <= n else line[: n - 1] + "…"


def _action_text(e: dict[str, Any], results: dict[Any, dict[str, Any]]) -> str:
    """One line that says what a response of the agent did, derived from its tool calls: the tool,
    the file name or the first line of the command. No language model writes this line."""
    calls = e.get("tool_calls") or []
    groups: list[tuple[str, list[str]]] = []

    def add(verb: str, what: str) -> None:
        if groups and groups[-1][0] == verb:
            groups[-1][1].append(what)
        else:
            groups.append((verb, [what]))

    for w in e.get("web_searches") or []:  # searches that the model's vendor executed inside the response
        kind = str(w.get("action") or "search")
        if kind == "search":
            add("searched the web for", f"“{E(_short(str(w.get('query') or '; '.join(w.get('queries') or []))))}”")
        elif kind == "open_page":
            add("opened", f"<code>{E(_short(str(w.get('url') or '')))}</code>")
        else:
            add("searched within a page", f"(“{E(_short(str(w.get('pattern') or '')))}”)" if w.get("pattern") else "")
    for c in calls:
        name = str(c.get("name") or c.get("tool") or "?")
        args = c.get("arguments") or {}
        det = (results.get(c.get("id")) or {}).get("details") or {}
        res = results.get(c.get("id")) or {}
        if name == "read_file":
            add("read", f"<code>{E(str(args.get('path')))}</code>")
        elif name == "write_file":
            add("wrote", f"<code>{E(str(args.get('path')))}</code>")
        elif name == "list_files":
            path = str(args.get("path") or ".")
            add("listed the files", "" if path in (".", "") else f"of <code>{E(path)}</code>")
        elif name == "run_shell":
            note = ""
            if res.get("denied"):
                note = " (refused)"
            elif det.get("timed_out"):
                note = " (time limit)"
            elif det.get("exit_code") not in (None, 0):
                note = f" (exit status {det['exit_code']})"
            add("ran", f"<code>{E(_short(str(args.get('command') or '')))}</code>{note}")
        elif name == "web_fetch":
            add("fetched", f"<code>{E(_short(str(args.get('url') or '')))}</code>")
        elif name == "web_search":
            add("searched the web for", f"“{E(_short(str(args.get('query') or '')))}”")
        elif name == "install_package":
            add("installed", f"<code>{E(str(args.get('requirement') or args.get('package') or ''))}</code>")
        elif name == "start_helper":
            add("started a helper agent", f"({E(_short(str(args.get('task') or args.get('prompt') or ''), 70))})")
        elif name == "ask_user":
            add("asked the user", f"“{E(_short(str(args.get('question') or '')))}”")
        else:
            add(f"called <code>{E(name)}</code>", "")
    parts = []
    for verb, items in groups:
        items = [i for i in items if i]
        parts.append(f"{verb} {', '.join(items)}".strip() if items else verb)
    text = (e.get("text") or "").strip()
    if e.get("done"):
        parts.append("sent <code>DONE</code>")
    elif not calls and not e.get("web_searches"):
        parts.append(f"wrote a message without a tool call: “{E(_short(text, 70))}”" if text else "sent an empty response")
    line = "; ".join(parts)
    return line[0].upper() + line[1:] if line else ""


def action_text_plain(e: dict[str, Any]) -> str:
    """The line of :func:`_action_text` as plain text, for the progress lines of ``aspire session``
    on the terminal. It is derived from the response alone, before its tools have run."""
    return html.unescape(re.sub(r"<[^>]+>", "", _action_text(e, {})))


def _turn(turn: str, when: str, action: str, cost: str, body: str, *, cls: str = "") -> str:
    return (f"<details class='turn {cls}'><summary class=trow><span class=num>{turn}</span><span class=num>{when}</span>"
            f"<span class=act>{action}</span><span class=num>{cost}</span></summary><div class=tbody>{body}</div></details>")


def _course(r: Run) -> str:
    """What the agent did: one line per response of the agent and per action of the harness, in
    order; each line unfolds to the full content."""
    results = {e.get("call_id"): e for e in r.events if e.get("kind") == "tool_result"}
    rows: list[str] = []
    turn = 0
    cost = 0.0
    for e in r.events:
        kind = e.get("kind")
        agent = str(e.get("agent") or "main")
        helper = agent not in ("main", "harness", "None")
        when = clock(e.get("elapsed_s"))
        if kind in HARNESS_MESSAGES:
            who = {"user_question": "Agent", "user_answer": "User"}.get(str(kind), "Harness")
            text = e.get("text") or e.get("message") or e.get("question") or e.get("answer") or ""
            shown = agent_markdown(text) if kind == "user_question" else f"<div class=say>{E(str(text))}</div>"
            rows.append(_turn("", when, f"{who}: {E(HARNESS_MESSAGES[str(kind)])}", "", shown,
                              cls="harness" + (" helper" if helper else "")))
        elif kind == "response":
            if not helper:
                turn += 1
            cost += float(e.get("cost_usd") or 0.0)
            usage = e.get("usage") or {}
            body = [f"<p class='muted small'>{thousands(usage.get('input_tokens'))} input and {thousands(usage.get('output_tokens'))} output tokens"
                    + (f" (of which {thousands(usage.get('reasoning_tokens'))} reasoning)" if usage.get("reasoning_tokens") else "")
                    + (f"; {usage.get('web_search_calls')} web search call(s) executed by the model's vendor" if usage.get("web_search_calls") else "")
                    + f"; {float(e.get('cost_usd') or 0.0):.3f} USD for this turn.</p>"]
            summaries = [str(x) for x in e.get("reasoning") or [] if str(x).strip()]
            if summaries:
                body.append("<details class=reason open><summary>reasoning summary (written by the model provider's summarizer; "
                            "the model's own reasoning is not available)</summary>"
                            + "".join(agent_markdown(s) for s in summaries) + "</details>")
            text = (e.get("text") or "").strip()
            if text:
                body.append(agent_markdown(text))
            if e.get("refusal"):
                body.append(f"<div class=say><span class='pill bad'>refusal</span> {E(str(e['refusal']))}</div>")
            for w in e.get("web_searches") or []:
                what = w.get("query") or "; ".join(w.get("queries") or []) or w.get("url") or w.get("pattern") or ""
                sources = "".join(f"<li><code>{E(str(u))}</code></li>" for u in w.get("sources") or [])
                body.append(f"<div class=call><div class=callhead><span class=tool>web_search</span><span>executed by the model's vendor: "
                            f"{E(str(w.get('action') or 'search').replace('_', ' '))}</span></div><pre class=arg>{E(str(what))}</pre>"
                            + (f"<details class=out><summary>sources ({len(w['sources'])})</summary><ul>{sources}</ul></details>" if sources else "")
                            + "</div>")
            for c in e.get("tool_calls") or []:
                body.append(_call_block(c, results.get(c.get("id")) or {}))
            action = _action_text(e, results)
            if helper:
                action = f"Helper agent {E(agent)}: {action[0].lower() + action[1:] if action else ''}"
            rows.append(_turn("" if helper else str(turn), when, action, f"{cost:.2f}", "".join(body), cls="helper" if helper else ""))
        elif kind == "request_error":
            rows.append(_turn("", when, "Harness: a request to the language model failed", "",
                              f"<div class=say>{E(str(e.get('error') or e.get('message') or ''))}</div>", cls="harness"))
        elif kind == "check_outcome":
            n = len(e.get("candidates") or e.get("evaluated") or [])
            rows.append(_turn("", when, f"Harness: checked the files of {n} model{'s' if n != 1 else ''}: "
                              f"{'passed' if e.get('passed') else 'failed'}", "",
                              f"<pre>{E(str(e.get('report_text') or ''))}</pre>", cls="harness"))
        elif kind == "correction":
            rows.append(_turn("", when, "Harness: the agent may correct the files once", "", "<p class=muted>Start of the one permitted correction.</p>", cls="harness"))
        elif kind == "evaluation" and e.get("status") != "started":
            labels = e.get("candidates") or e.get("labels") or []
            rows.append(_turn("", when, f"Harness: evaluated {len(labels)} model{'s' if len(labels) != 1 else ''} on the training and the test data", "",
                              f"<p>{E(', '.join(str(x) for x in labels))}</p>", cls="harness"))
        elif kind in ("helper_start", "helper_end"):
            rows.append(_turn("", when, f"Harness: helper agent {E(agent)} {'started' if kind == 'helper_start' else 'ended'}", "",
                              agent_markdown(e.get("task") or e.get("text") or ""), cls="harness helper"))
        elif kind == "round_end":
            how = OUTCOME_TEXT.get(str(e.get("outcome")), str(e.get("outcome")))
            rows.append(_turn("", when, f"Harness: the round ended. {E(how)}.", f"{cost:.2f}",
                              f"<p>{E(str(r.record.get('termination_reason') or ''))}</p>", cls="harness"))
        elif kind in ("request", "tool_call", "tool_result", "transcript_start", "transcript_end", "round_start", "evaluation",
                      "session_start", "pool_version_saved", "recommendation_recorded", "workspace_archived"):
            continue
        elif kind in SESSION_LINES:  # events of interactive operation
            text = e.get("text") or e.get("note") or ""
            rows.append(_turn("", when, f"Harness: {E(SESSION_LINES[str(kind)])}", "",
                              f"<div class=say>{E(str(text))}</div>" if text else "<p class=muted>No text.</p>", cls="harness"))
        else:  # any later kinds
            text = e.get("text") or e.get("note") or ""
            rows.append(_turn("", when, f"Harness: {E(str(kind).replace('_', ' '))}", "", f"<div class=say>{E(str(text))}</div>", cls="harness"))
    head = ("<div class='trow thead'><span class=num>Turn</span><span class=num>Time</span><span>Action</span>"
            "<span class=num>Cost so far (USD)</span></div>")
    bar = ("<div class=bar><button type=button data-open='details.turn' data-show='Unfold all turns' data-hide='Fold all turns'>Unfold all turns</button>"
           "<span class='muted small'>A turn is one response of the agent. Time is the execution time since the start of the run, "
           "in minutes and seconds. Select a line to see the reasoning summary, the agent's text, the commands and files, "
           "and the outputs.</span></div>")
    return bar + f"<div class=turns>{head}{''.join(rows)}</div>"


# ---------------------------------------------------------------------------------------------
# run page


def _files(r: Run, report_dir: Path) -> str:
    v = r.pool_version
    rel = lambda p: _relpath(r.folder / p, report_dir)  # noqa: E731
    provisioned = {str(f.get("name")) for f in (r.record.get("workspace_manifest") or {}).get("files") or [] if isinstance(f, dict)}
    ws = r.folder / "workspace"
    written = []
    if ws.is_dir():
        for p in sorted(ws.rglob("*")):
            name = p.relative_to(ws).as_posix()
            if p.is_file() and name not in provisioned and not name.startswith(("data/", "models/")):
                written.append(name)
    items = []
    if written:
        items.append("<li>Files the agent wrote: " + ", ".join(f"<a href='{E(rel('workspace/' + n))}' target=_blank rel=noopener><code>{E(n)}</code></a>" for n in written) + "</li>")
    models = sorted(p.name for p in (ws / "models").glob("*.json")) if (ws / "models").is_dir() else []
    if models:
        items.append("<li>Model files: " + ", ".join(f"<a href='{E(rel('workspace/models/' + n))}' target=_blank rel=noopener><code>{E(n)}</code></a>" for n in models) + "</li>")
    exports = sorted((r.folder / "export" / "python").glob("*.py")) if (r.folder / "export" / "python").is_dir() else []
    if exports:
        items.append("<li>The models as Python functions: " + ", ".join(
            f"<a href='{E(_relpath(p, report_dir))}' target=_blank rel=noopener><code>{E(p.name)}</code></a>" for p in exports) + "</li>")
    for name, p in (("Evaluation report of the harness (Markdown)", f"evaluation/v{v}/evaluation.md"), ("Run record", "run_record.json"),
                    ("Transcript (one JSON object per line)", "transcript.jsonl"), ("Working directory of the agent", "workspace")):
        if (r.folder / p).exists():
            items.append(f"<li><a href='{E(rel(p))}' target=_blank rel=noopener>{E(name)}</a> <span class=muted><code>{E(p)}</code></span></li>")
    return "<ul class=files>" + "".join(items) + "</ul>"


def _run_page(r: Run, exp: dict[str, Any], n_runs: int, spec: dict[str, Any] | None, report_dir: Path) -> str:
    title = str((r.record.get("task") or {}).get("title") or exp.get("task") or exp.get("id"))
    b = [f"<h1>{E(title)} – run {r.index}{f' of {n_runs}' if n_runs > 1 else ''}</h1>",
         f"<p class=sub>{_generated()}</p>", f"<p>{_status_line(r)}</p>"]
    if r.fields.get("dry_run"):
        b.append(DRY_RUN_NOTE)
    if r.leak_findings:
        b.append("<div class=warnbox><b>Sealed information was found in this run.</b> The harness searches the transcript and the "
                 "files the agent wrote for test values and sealed file names:<ul>"
                 + "".join(f"<li>{E(str(f.get('kind')))} in <code>{E(str(f.get('where')))}</code>: {E(str(f.get('detail')))}</li>" for f in r.leak_findings)
                 + "</ul></div>")
    b.append("<h2>1 Models</h2>")
    if r.candidates:
        b.append(_models_table(r))
        rec = r.candidate(r.recommended)
        if rec is not None:
            b.append(f"<div class=card><b>The agent's recommendation: <a href='#model-{E(rec.label)}'>{E(rec.label)}</a>.</b> "
                     f"Its reason: <span class=say style='display:inline'>{agent_text(r.reason)}</span></div>")
        else:
            b.append("<div class=card><b>The agent recommended no model.</b>" + (f" Its reason: {agent_text(r.reason)}" if r.reason else "") + "</div>")
        b.append("<div class=bar><button type=button data-open='details.more' data-show='Unfold the details of all models' "
                 "data-hide='Fold the details of all models'>Unfold the details of all models</button></div>")
        b += [_model_card(r, c, spec) for c in r.candidates]
    else:
        b.append(f"<p>No model was evaluated in this run. {E(str(r.record.get('termination_reason') or ''))}</p>")
    b.append("<h2>2 Course of the run</h2>")
    b.append("<p class=sub>The system prompt, <code>TASK.md</code> and <code>FORMAT.md</code> that the agent received are shown on the "
             "<a href='index.html'>page of the experiment</a>.</p>")
    b.append(_course(r))
    b.append("<h2>3 Files</h2>" + _files(r, report_dir))
    crumb = "<a href='index.html'>← Experiment</a>"
    return page(f"{title} – run {r.index}", "".join(b), crumb=crumb)


# ---------------------------------------------------------------------------------------------


_RUN_FOLDER = re.compile(r"^r\d{2,}$")


def build_report(experiment_dir: str | Path, out_dir: str | Path | None = None, *, runs_base: str | Path | None = None) -> Path:
    """Write the HTML report of ``experiment_dir`` into ``out_dir`` (default ``<runs_base>/report``)
    and return the path of ``index.html`` (module docstring).

    The experiment folder holds ``experiment.yaml`` (one task, repeated runs); the run folders are
    ``<runs_base>/runs/r<NN>/``, where ``runs_base`` is the experiment folder (default) or its
    subfolder ``dry-run`` for the runs with the scripted agent. Pages of an earlier report in the
    output folder that belong to no run of the experiment are removed.
    """
    exp_dir = Path(experiment_dir)
    base = Path(runs_base) if runs_base else exp_dir
    report_dir = Path(out_dir) if out_dir else base / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    exp = yaml.safe_load((exp_dir / "experiment.yaml").read_text(encoding="utf-8")) or {}
    if "task" not in exp:
        raise ValueError(f"{exp_dir / 'experiment.yaml'} names no task: the report is written for an experiment of one task "
                         "with repeated runs (experiment.yaml with the fields task and runs)")
    tasks_root = (exp_dir / exp["tasks_root"]) if exp.get("tasks_root") else HARNESS_DIR.parent / "tasks"
    spec = _load_task(tasks_root, str(exp.get("task")))
    folders = sorted(d for d in (base / "runs").iterdir() if d.is_dir() and _RUN_FOLDER.match(d.name)) if (base / "runs").is_dir() else []
    runs = [_load_run(d, report_dir) for d in folders if (d / "run_record.json").is_file()]
    missing = [d.name for d in folders if not (d / "run_record.json").is_file()]
    format_text = None
    for r in runs:
        f = r.folder / "workspace" / "FORMAT.md"
        if f.is_file():
            format_text = f.read_text(encoding="utf-8")
            break
    keep = {"index.html"} | {run_page_name(r.run_id) for r in runs}
    for old in report_dir.glob("*.html"):
        if old.name not in keep:
            old.unlink()
    index = report_dir / "index.html"
    index.write_text(_index(exp, runs, missing, spec, format_text, base, report_dir), encoding="utf-8", newline="\n")
    for r in runs:
        (report_dir / run_page_name(r.run_id)).write_text(_run_page(r, exp, len(runs), spec, report_dir), encoding="utf-8", newline="\n")
    return index
