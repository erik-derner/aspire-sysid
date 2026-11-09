"""Renderer of the task brief ``TASK.md``.

The brief is short: it states what only this task determines. Its sections are

1. system and intended use (description, intended use, references, supporting files);
2. data (files, trajectories, sampling period, variable table, noise, given constants);
3. what the agent delivers (the expressions and their arguments, the files, the recommendation,
   the pool request, the task's questions); the permitted operators and functions are stated in
   ``FORMAT.md``, and the brief names them only when the task departs from the default list;
4. evaluation (how the harness computes the predictions, the score, numerical failures);
5. physical requirements (only when the task states any);
6. limits and completion (budget, completion message; interactive operation when it applies).

Everything that is the same for every task (the model file format, the expression syntax, one
general example, the writing rules) is in ``FORMAT.md`` (:mod:`aspire_sysid.brief.reference`),
which the brief names. The checking script reports every violation of the format with its rule.

Inputs. The brief is rendered from the public view of the task only
(:func:`aspire_sysid.task.public_view`, the agent-visible part of the specification). It never
reads the sealed part of the task or the recording names.

Decisions (documented in ``aspire/README.md``):

* **Independent of the tool configuration.** The brief does not depend on the tool configuration;
  the system prompt states the configuration of the run and its tools
  (:mod:`aspire_sysid.brief.prompts`).
* **Interactive operation.** The paragraph on ``ask_user``, analysis requests and further rounds
  is rendered only with ``interactive=True``.
* **Tolerance of a formal requirement.** The brief states the tolerance as the admissible
  violation margin in the unit of the checked quantity (tasks/README.md, Section 4); the
  evaluation applies the same reading.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

from ..model.checks import DEFAULT_FUNCTIONS
from ..task.public import public_view
from ..task.schema import UNIT_NOT_SUPPLIED, TaskSpec

__all__ = [
    "BRIEF_FILE",
    "CHECK_COMMAND",
    "DESCRIPTION_NOT_SUPPLIED",
    "FORMAT_FILE",
    "POOL_STATEMENT",
    "RECOMMENDATION_STATEMENT",
    "SECTION_TITLES",
    "pool_statement",
    "render_brief",
]

BRIEF_FILE = "TASK.md"
"""Name of the brief in the working directory; the system prompt names it."""

FORMAT_FILE = "FORMAT.md"
"""Name of the format reference in the working directory."""

CHECK_COMMAND = "python check_submission.py"
"""The checking command of ``check_submission.py``, which the brief names."""

SECTION_TITLES: tuple[str, ...] = (
    "System and intended use",
    "Data",
    "What you deliver",
    "Evaluation",
    "Physical requirements",
    "Limits and completion",
)
"""Titles of the sections of the brief, in order; "Physical requirements" appears only when the
task states a requirement, and the later section is numbered accordingly."""

POOL_STATEMENT = (
    "At most {maximum} candidates are evaluated, in the order of `models/pool.json`. Consider various "
    "identification approaches, for example physically motivated structures, symbolic-regression "
    "search or sparse regression; before fitting, list the approaches and the model families you "
    "will try. Build the pool from structurally different model families, not from variations of "
    "one form. Examine the residuals of your best candidates and try structures that can represent "
    "what they show. Include only candidates you would defend as a model of the system."
)
"""The pool request of the brief, with the placeholder ``{maximum}``."""

RECOMMENDATION_STATEMENT = "You can recommend one candidate that you consider the best-performing."
"""The recommendation sentence of the brief."""

DESCRIPTION_NOT_SUPPLIED = "not supplied"
"""Text of the Description column of the brief for a column that the task does not describe (a
blind variant of a task); a separate constant from the unit string ``UNIT_NOT_SUPPLIED``."""

_FORMULATION_NAME = {
    "static": "static model",
    "continuous": "continuous-time model",
    "discrete": "discrete-time model",
    "narx": "discrete-time model of the next output (nonlinear autoregressive model with exogenous inputs, NARX)",
}


def pool_statement(maximum: int) -> str:
    """The pool request with the task's pool limit inserted."""
    return POOL_STATEMENT.format(maximum=maximum)


# ---------------------------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------------------------


def _num(x: Any) -> str:
    """A number as written in the brief: integers without a decimal point, others with up to 12
    significant digits, exponents without leading zeros (``1e-6``); strings unchanged."""
    if isinstance(x, bool):
        return str(x).lower()
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if math.isinf(x):
            return "∞" if x > 0 else "-∞"
        if abs(abs(x) - math.pi) < 1e-12:
            return "π" if x > 0 else "-π"
        if x == int(x) and abs(x) < 1e15:
            return str(int(x))
        s = format(x, ".12g")
        if "e" in s:
            mant, exp = s.split("e")
            sign = "-" if exp.startswith("-") else ""
            s = f"{mant}e{sign}{exp.lstrip('+-').lstrip('0') or '0'}"
        return s
    return str(x)


def _para(text: str | None) -> str:
    """A paragraph from task text: internal line breaks folded into spaces."""
    return " ".join(str(text or "").split())


def _sentence(text: str | None) -> str:
    """Task text as a sentence: folded, first letter capitalized, final period added if missing."""
    t = _para(text)
    if not t:
        return t
    t = t[0].upper() + t[1:]
    return t if t[-1] in ".!?" else t + "."


def _codes(names: Iterable[str], last: str = "and") -> str:
    items = [f"`{n}`" for n in names]
    if not items:
        return "none"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" {last} " + items[-1]


def _cell(text: Any) -> str:
    """A table cell: one line, with the table separator escaped."""
    return " ".join(str(text).split()).replace("|", "\\|")


def _table(header: Sequence[str], rows: Iterable[Sequence[Any]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows]
    return out


def _unit(unit: str | None) -> str:
    return unit if unit else "-"


def _with_unit(value: Any, unit: str | None) -> str:
    u = _unit(unit)
    return _num(value) if u == "-" else f"{_num(value)} {u}"


def _plural(n: int, word: str, plural: str | None = None) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {plural or word + 's'}"


def _output(view: Mapping[str, Any]) -> Mapping[str, Any]:
    return next(c for c in view["columns"] if "output" in c["roles"])


# ---------------------------------------------------------------------------------------------
# Section 1: system and intended use
# ---------------------------------------------------------------------------------------------


def _system(view: Mapping[str, Any]) -> list[str]:
    out = [f"## 1 {SECTION_TITLES[0]}", ""]
    out += [_para(view["description"]) if view.get("description") else "The task gives no description of the system.", ""]
    out += [_para(view["intended_use"]) if view.get("intended_use") else "The task states no intended use of the model.", ""]
    if view["literature"]:
        out += ["References supplied with the task:", ""]
        out += [f"{i}. {_para(ref)}" for i, ref in enumerate(view["literature"], 1)] + [""]
    if view["context"]:
        out += ["Supporting files in the working directory, with the user's explanation:", ""]
        out += [f"- `{c['file']}`: {_para(c['note'])}" for c in view["context"]] + [""]
    return out


# ---------------------------------------------------------------------------------------------
# Section 2: data
# ---------------------------------------------------------------------------------------------


def _file_sentence(f: Mapping[str, Any], what: str, dynamic: bool, tc: str | None) -> str:
    text = f"`{f['file']}` holds {_plural(f['samples'], 'sample')}{what}"
    if not dynamic:
        return text + "."
    lengths = list(f["trajectory_lengths"])
    n = f["trajectories"]
    if n == 1:
        return text + ": one trajectory of consecutive samples."
    if len(set(lengths)) == 1:
        text += f": {n} trajectories of {lengths[0]} consecutive samples"
    else:
        text += f": {n} trajectories of {', '.join(str(x) for x in lengths)} consecutive samples"
    return text + (f"; the column `{tc}` holds the trajectory number." if tc else ".")


def _role_text(c: Mapping[str, Any], static: bool) -> str:
    words = []
    for r in c["roles"]:
        if r == "output":
            words.append("output" if static else "scored output")
        elif r == "state_derivative":
            words.append(f"sampled time derivative of `{c.get('derivative_of')}`")
        else:
            words.append(r)
    return ", ".join(words)


def _data(view: Mapping[str, Any]) -> list[str]:
    out = [f"## 2 {SECTION_TITLES[1]}", ""]
    form = view["formulation"]
    dyn = view.get("dynamics")
    data = view["data"]
    tc = data.get("trajectory_column")
    lines = [_file_sentence(data["train"], " of training data" if "val" in data else "", bool(dyn), tc)]
    if "val" in data:
        lines.append(
            _file_sentence(data["val"], " of validation data", bool(dyn), tc)
            + " Whether and how you use the validation data is your decision."
        )
    if dyn:
        lines.append("Row k+1 of a trajectory is the sample that follows row k; different trajectories are separate experiments.")
        lines.append(f"The sampling period is T_s = {_num(dyn['sampling_period'])} s.")
    else:
        lines.append("Each row is one sample; the order of the rows carries no information.")
    out += [" ".join(lines), ""]
    rows = []
    for c in view["columns"]:
        rng = c.get("range")
        rows.append(
            [
                f"`{c['name']}`",
                _role_text(c, form == "static"),
                _unit(c.get("unit")),
                f"{_num(rng[0])} to {_num(rng[1])}" if rng else "not declared",
                _para(c.get("description")) or DESCRIPTION_NOT_SUPPLIED,
            ]
        )
    out += _table(["Column", "Role", "Unit", "Training range", "Description"], rows) + [""]
    notes = []
    units = [c.get("unit") for c in view["columns"]]
    if all(u == UNIT_NOT_SUPPLIED for u in units):
        notes.append("The task does not state the units.")
    elif "-" in units:
        notes.append("The unit `-` denotes a dimensionless quantity or a unit that was not supplied.")
    if not any(_para(c.get("description")) for c in view["columns"]):
        notes.append("The task does not describe the columns.")
    if view.get("roles_defaulted"):
        notes.append("The task declares no roles; the last column is the output and the other columns are the inputs.")
    if data.get("noise"):
        notes.append(f"Noise: {_sentence(data['noise'])}")
    if data.get("preprocessing"):
        notes.append(f"Preprocessing: {_sentence(data['preprocessing'])}")
    if notes:
        out += [" ".join(notes), ""]
    if view["constants"]:
        out += ["Given constants, which expressions may use by name:", ""]
        out += _table(
            ["Name", "Value", "Unit", "Source"],
            [[f"`{c['name']}`", _num(c["value"]), _unit(c["unit"]), c["source"]] for c in view["constants"]],
        ) + [""]
    return out


# ---------------------------------------------------------------------------------------------
# Section 3: what the agent delivers
# ---------------------------------------------------------------------------------------------


def _deliver(view: Mapping[str, Any]) -> list[str]:
    out = [f"## 3 {SECTION_TITLES[2]}", ""]
    form = view["formulation"]
    dyn = view.get("dynamics")
    keys = list(view["expression_keys"])
    args = list(view["arguments"])
    what = _FORMULATION_NAME[form]
    n = len(keys)
    count = "one closed-form expression" if n == 1 else f"{n} closed-form expressions"
    if form == "static":
        text = f"A candidate is a {what} of {count}, `{keys[0]}`: the output as a function of {_codes(args)}."
    elif form == "continuous":
        text = (
            f"A candidate is a {what} of {count}, {_codes(keys)}: the time "
            f"{'derivative of the state' if n == 1 else 'derivatives of the states'} {_codes(dyn['states'])} as "
            f"{'a function' if n == 1 else 'functions'} of {_codes(args)}."
        )
    elif form == "discrete":
        text = (
            f"A candidate is a {what} of {count}, {_codes(keys)}: the "
            f"{'state' if n == 1 else 'states'} {_codes(dyn['states'])} at sample k+1 as "
            f"{'a function' if n == 1 else 'functions'} of {_codes(args)} at sample k."
        )
    else:
        delays = dyn.get("delays", [])
        text = (
            f"A candidate is a {what} of {count}, `{keys[0]}`: the output at sample k+1 as a function of "
            f"{_codes(args)} at sample k. The delayed variables are "
            + "; ".join(f"`{d['name']}`[k] = `{d['variable']}`[k − {d['lag']}]" for d in delays)
            + ". You build them from the data within each trajectory."
        )
    lines = [text]
    columns = {c["name"]: c for c in view["columns"]}
    for c in view["columns"]:
        if c.get("derivative_of"):
            lines.append(
                f"The column `{c['name']}` is a possible fitting target for the derivative of `{c['derivative_of']}`; "
                "it is not an argument of the expressions."
            )
    if dyn and dyn["measurement"] not in columns:
        lines.append(f"The model output is `{dyn['measurement']}`, computed from the model state; this equation is given and not estimated.")
    lines.append(f"`{FORMAT_FILE}` states how an expression is written and what it may contain.")
    funcs = list(view["functions"])
    if tuple(funcs) != tuple(DEFAULT_FUNCTIONS):
        lines.append(
            "In this task an expression may use only these functions: " + " ".join(f"`{f}`" for f in funcs) + "."
            if funcs
            else "In this task an expression may use no functions, only the arithmetic operators."
        )
    out += [" ".join(lines), ""]
    if view["added_functions"]:
        out += ["The task adds these functions:", ""]
        out += _table(
            ["Function", "Definition", "Domain"],
            [[f"`{a['name']}({', '.join(a['arguments'])})`", f"`{a['definition']}`", a["domain"]] for a in view["added_functions"]],
        ) + [""]
    out += [
        f"Write one file per candidate, `models/<label>.json`; `{FORMAT_FILE}` describes the file and gives an "
        "example. Write also `models/pool.json`, which lists the labels of your candidates in the order in which "
        f"they are to be evaluated. {RECOMMENDATION_STATEMENT} `models/pool.json` then names that candidate and "
        f"gives your reason. Run `{CHECK_COMMAND}` to check your files: it prints every error with its location, "
        "so that you can correct it.",
        "",
        pool_statement(view["pool_cap"]),
        "",
    ]
    if view["discussion_questions"]:
        out += ["Answer these questions for every candidate, in the field `answers` of its file:", ""]
        out += [f"- **{q['id']}**: {_para(q['text'])}" for q in view["discussion_questions"]] + [""]
    return out


# ---------------------------------------------------------------------------------------------
# Section 4: evaluation
# ---------------------------------------------------------------------------------------------


def _evaluation(view: Mapping[str, Any]) -> list[str]:
    out = [f"## 4 {SECTION_TITLES[3]}", ""]
    form = view["formulation"]
    dyn = view.get("dynamics")
    ev = view["evaluation"]
    oc = _output(view)
    output, unit = oc["name"], _unit(oc.get("unit"))
    m = ev["initialization"]
    intro = "The harness, the software that runs this task, evaluates every candidate on test data that you cannot access."
    if form == "static":
        how = f"It computes `{view['expression_keys'][0]}` from the inputs of every test sample and compares it with the measured `{output}`."
        word, scope = "predicted", "over all test samples"
    else:
        first = "the first logged state" if m == 1 else f"the first {m} logged samples"
        if form == "narx":
            first = f"the logged output of the first {_plural(m, 'sample')}"
        if form == "continuous":
            sub = dyn.get("substeps", 1)
            step = "one step" if sub == 1 else f"{sub} equal steps"
            propagate = (
                "integrates the expressions with the classical fourth-order Runge–Kutta method, "
                f"{step} per sampling period, with the logged inputs held constant between samples"
            )
        else:
            propagate = "applies the expression" + ("" if len(view["expression_keys"]) == 1 else "s") + " repeatedly with the logged inputs"
        if ev["mode"] == "simulation":
            how = (
                f"For each test trajectory it starts from {first} and {propagate}; a simulated "
                + ("output" if form == "narx" else "state")
                + " is never replaced by a later measurement."
            )
            word = "simulated"
        else:
            start = "the logged outputs" if form == "narx" else "the logged state"
            how = (
                f"For every test sample it starts from {start} of the previous sample and "
                + (propagate.replace(" repeatedly", " once") if form != "continuous" else propagate + " over one sampling period")
                + "; the prediction is one step ahead and restarts from the measurements at every sample."
            )
            word = "predicted"
        after = "the first" if m == 1 else f"the first {m}"
        scope = f"over all test samples after {after} of each trajectory"
    score = (
        f"The score is the root mean squared error (RMSE) between {word} and logged `{output}`"
        + ("" if unit in ("-", UNIT_NOT_SUPPLIED) else f", in {unit},")
        + f" {scope}."
    )
    limits = [
        f"`{fl['variable']}` leaves [{_num(fl['lower'])}, {_num(fl['upper'])}]" + ("" if _unit(fl["unit"]) in ("-", UNIT_NOT_SUPPLIED) else f" {fl['unit']}")
        for fl in ev["failure_limits"]
    ]
    failure = "An evaluation fails when a value is not finite" + (", when " + " or ".join(limits) if limits else "")
    failure += f", or when it takes longer than {_num(ev['time_limit_s'])} s."
    out += [" ".join([intro, how, score, failure]), ""]
    return out


# ---------------------------------------------------------------------------------------------
# Section 5: physical requirements (only when the task states any)
# ---------------------------------------------------------------------------------------------


def _var_unit(view: Mapping[str, Any], name: str) -> str | None:
    for c in view["columns"]:
        if c["name"] == name:
            return c.get("unit")
    return None


def _domain_text(view: Mapping[str, Any], dom: Mapping[str, Any]) -> str:
    if "points" in dom:
        pts = []
        for pt in dom["points"]:
            pts.append("(" + ", ".join(f"{k} = {_with_unit(v, _var_unit(view, k))}" for k, v in pt.items()) + ")")
        word = "the point" if len(pts) == 1 else "the points"
        return f"{word} " + "; ".join(pts)
    box = dom.get("box", {})
    parts = []
    for k, (lo, hi) in box.items():
        unit = _unit(_var_unit(view, k))
        if lo == hi:
            parts.append(f"{k} = {_num(lo)}" + ("" if unit == "-" else f" {unit}"))
        else:
            parts.append(f"{k} ∈ [{_num(lo)}, {_num(hi)}]" + ("" if unit == "-" else f" {unit}"))
    return ", ".join(parts) if parts else "the declared ranges of the variables"


def _condition_text(r: Mapping[str, Any]) -> str:
    t = r["target"]
    typ = r["type"]
    if typ == "equation":
        return f"`{t}` = `{r['equals']}`"
    if typ == "exact_value":
        return f"`{t}` = {_num(r['value'])}"
    if typ == "inequality":
        return f"`{r['relation']}`"
    if typ == "monotonicity":
        return f"`{t}` is {r['direction']} in `{r['variable']}`"
    if typ == "curvature":
        return f"`{t}` is {r['sign']} in `{r['variable']}`"
    if typ == "symmetry":
        tr = ", ".join(f"{k} → {v}" for k, v in r["transform"].items())
        factor = "" if r["factor"] == 1 else "−"
        return f"`{t}` with the substitution {tr} equals {factor}`{t}`"
    if typ == "parity":
        flip = r.get("flip") or r.get("variables")
        return f"`{t}` is {r['parity']} under the joint sign change of {', '.join(flip)}"
    if typ == "limit":
        a = r["approach"]
        a_text = {"oo": "+∞", "-oo": "−∞"}.get(str(a), _num(a))
        return f"the limit of `{t}` as {r['variable']} → {a_text} equals {_num(r['value'])}"
    if typ == "relation_at_points":
        return f"`{r['relation']}`, where at1, at2, … are the values of `{t}` at the listed points in their order"
    return f"type `{typ}`"


def _requirements(view: Mapping[str, Any], number: int) -> list[str]:
    reqs, nl = view["requirements"], view["requirements_nl"]
    out = [f"## {number} {SECTION_TITLES[4]}", ""]
    if reqs:
        out += [
            "A formal requirement is a condition on one expression over a domain of its arguments. The tolerance is "
            "the admissible violation margin. The harness checks each requirement symbolically or at sampled points; "
            "a check at sampled points that finds no violation is not a proof. A demonstrated violation excludes the "
            "candidate from the ranking, unless stated otherwise below.",
            "",
        ]
        for r in reqs:
            line = f"- **{r['id']}**"
            if r.get("statement"):
                line += f" ({_para(r['statement'])})"
            tol = r["tolerance"]
            line += f": {_condition_text(r)}; domain: {_domain_text(view, r['domain'])}; tolerance {_with_unit(tol['value'], tol['unit'])}"
            if not r["exclude_on_violation"]:
                ex = r.get("exception") or {}
                line += "; a violation is reported without exclusion, by the explicit instruction of the user" + (
                    f" ({ex.get('stated_by')}, {ex.get('date')}" + (f": {_para(ex['note'])}" if ex.get("note") else "") + ")" if ex else ""
                )
            out.append(line + ".")
        out.append("")
    if nl:
        out += [
            "Requirements stated in words. A human assesses them; address each one in the discussion of every "
            "candidate to which it applies.",
            "",
        ]
        out += [f"- **{r['id']}**: {_para(r['text'])}" for r in nl] + [""]
    return out


# ---------------------------------------------------------------------------------------------
# Last section: limits and completion
# ---------------------------------------------------------------------------------------------


def _limits_text(b: Mapping[str, Any]) -> str:
    return f"{_plural(int(b['turns']), 'turn')}, {_num(b['seconds'])} s of execution time, {_num(b['usd'])} USD"


def _limits(view: Mapping[str, Any], number: int, interactive: bool) -> list[str]:
    budget = view["budget"]
    out = [
        f"## {number} {SECTION_TITLES[5]}",
        "",
        f"One round: {_limits_text(budget['round'])}; a turn is one response of yours. When the files pass the check, "
        "send the exact message DONE. If the harness's check of the files then fails, you receive its report and may "
        "correct the files once. If a limit ends the round earlier, the complete candidate files are evaluated.",
        "",
    ]
    if interactive:
        text = (
            "This is an interactive session. You may ask the user with `ask_user` when the answer would change a "
            "modeling choice. After a round the user may request an analysis, which you answer without changing the "
            f"pool, or start a further round. The session as a whole is limited to {_limits_text(budget['session'])}"
        )
        if budget.get("analysis_exchange"):
            text += f", and one analysis request to {_limits_text(budget['analysis_exchange'])}"
        out += [text + ".", ""]
    return out


# ---------------------------------------------------------------------------------------------
# The brief
# ---------------------------------------------------------------------------------------------


def render_brief(task: TaskSpec, *, interactive: bool = False) -> str:
    """The text of ``TASK.md`` for ``task``.

    Rendered from the public view of the task only. ``interactive`` adds the paragraph on
    interactive operation. The text ends with one newline and does not depend on the
    tool configuration.
    """
    view = public_view(task)
    out = [f"# Task: {_para(view['title'])}", ""]
    out += _system(view) + _data(view) + _deliver(view) + _evaluation(view)
    number = 5
    if view["requirements"] or view["requirements_nl"]:
        out += _requirements(view, number)
        number += 1
    out += _limits(view, number, interactive)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"
