"""The format reference ``FORMAT.md``: model file format, expression syntax, example, writing rules.

``FORMAT.md`` is one fixed text, the same for every
task; the brief ``TASK.md`` names it. It is produced by plain code
from the constants of the check module, without a language model and without task information.
:func:`format_reference` refuses to render when a field of the format lacks an explanation, so
that a change of the file format cannot leave the reference behind.

The example is one general example on a small invented task (one input ``q``, one output ``z``; names that no task of the repository uses),
not an example of the task at hand, so that it cannot suggest a model structure for the task's
variables. :func:`example_check_config` and :data:`EXAMPLE_TRAINING_ROWS` describe that invented
task, so that the example can be checked against them with the file and expression checks.

The writing rules at the end of the file are a short form, for the agent, of the writing rules
of the harness's texts.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..model import checks as _checks
from .render import BRIEF_FILE, CHECK_COMMAND, FORMAT_FILE

__all__ = [
    "DISCUSSION_SECTION_TEXT",
    "ESTIMATION_FIELD_TEXT",
    "EXAMPLE_CANDIDATE",
    "EXAMPLE_LABEL",
    "EXAMPLE_POOL",
    "EXAMPLE_TRAINING_ROWS",
    "FORBIDDEN_WORDS",
    "PARAMETER_FIELD_TEXT",
    "POOL_FIELD_TEXT",
    "WRITING_RULES",
    "example_check_config",
    "format_reference",
]

PARAMETER_FIELD_TEXT: dict[str, str] = {
    "name": "the name used in the expressions: a letter, then letters, digits or `_`; it differs from every column, expression key, constant and function name",
    "value": "the numerical value",
    "unit": "the unit; `-` for a dimensionless quantity",
    "type": "`fitted` (estimated from data), `fixed` (chosen or known, not estimated) or `tied` (computed from other parameters by `equation`)",
    "description": (
        "what the parameter represents; for a fixed value, where the value comes from and why it was chosen; for a "
        "value taken over from another candidate or an earlier fit, from which one"
    ),
    "equation": "for a tied parameter only: its defining equation over other parameters, given constants and numbers",
}
"""Explanation of every field of a parameter row (:data:`checks.PARAMETER_FIELDS_REQUIRED` and
:data:`checks.PARAMETER_FIELDS_OPTIONAL`)."""

ESTIMATION_FIELD_TEXT: dict[str, str] = {
    "criterion": "what was minimized, on which variable, and why this criterion",
    "data": "the files, trajectories or rows used, and the reason when some were left out",
    "method": (
        "how the values were estimated: the estimation method by its established name and the software function, "
        "and why this method and not another; the starting values as numbers, or the statement that the method "
        "needs none, and why these starting values; whether all fitted parameters were estimated together in one "
        "step and, if not, which parameters were estimated in which step, with which criterion, and why; the seeds "
        "where they apply"
    ),
    "script": "the file in the working directory that reproduces the values",
}
"""Explanation of every field of the estimation record (:data:`checks.ESTIMATION_FIELDS`)."""

DISCUSSION_SECTION_TEXT: dict[str, str] = {
    "family": "the model family by its established name, with a reference where you know one",
    "interpretation": "what each term represents in the system; describe a term without a known physical meaning by its mathematical effect",
    "origin": (
        "how you arrived at the structure of this expression, as distinct from its parameter values, which "
        "`estimation` covers: say which of its terms, variables and operators came from physical reasoning, which "
        "from a search and which from a guess, what you tried before, and what made you change it"
    ),
    "limitations": "what the data do not determine and where the model is not expected to hold",
}
"""Explanation of every discussion section (:data:`checks.DISCUSSION_SECTIONS`), in their order."""

POOL_FIELD_TEXT: dict[str, str] = {
    "order": "the candidate labels in your order",
    "recommended": "the label of the candidate you recommend, or `null` when you recommend none",
    "reason": "why you recommend this candidate, or why you recommend none",
}
"""Explanation of every field of the pool file (:data:`checks.POOL_FIELDS`)."""

WRITING_RULES: tuple[str, ...] = (
    "Define every symbol at first use.",
    "Give every number with its unit and the data it was computed on.",
    "Name methods by their established names.",
    "Cite a reference for a model family or a method where one applies. Cite only references you are certain "
    "exist, and say when you cite from memory without having checked the source.",
    "Say what is estimated, what is assumed and what is unknown.",
    "Give a brief reason for every choice you made: a structure, a criterion, a method, a starting value, a fixed "
    "value, a term you removed.",
    "Write every expression inside a text between backticks, in the syntax of the expressions, for example "
    "`a1*q**2`; write it out, do not describe it in words. This holds also for a single parameter, column or "
    "expression name, such as `a1`, for a value given to one, such as `a1 = 0.5`, and for a range, such as "
    "`0 <= a1 <= 2`. A unit follows outside the backticks; a dimensionless value has no unit and no hyphen "
    "after it.",
    "Describe a term without a known physical meaning by its mathematical effect; do not invent a meaning.",
)
"""The writing rules for the agent's texts; the harness records their version as part of ``FORMAT.md``."""

FORBIDDEN_WORDS: tuple[str, ...] = (
    "theta", "omega", "domega", "dtheta", "kappa", "valve", "flow", "dp",
    "Stribeck", "Karnopp", "LuGre", "Dahl", "Coulomb", "friction", "pendulum", "fermenter", "fermentation",
    "headspace", "tire", "tyre", "magic formula", "Pacejka", "slip", "angle", "angular", "motor", "voltage",
    "turtlebot", "robot", "odometry", "heading", "phi", "v_f", "v_a", "unicycle",
)
"""Words of the tasks (column names, model families, systems) that must not occur in a text given
to every task, checked case-insensitively as whole words: ``FORMAT.md`` and the checking script
are provisioned into the working directories of described and blind tasks alike, so they
may not name any task. :func:`format_reference` refuses to render otherwise."""

EXAMPLE_LABEL = "M01"
"""Label of the candidate of the example."""

EXAMPLE_CANDIDATE: dict[str, Any] = {
    "expressions": {"z": "a1*q + b1*q**2/n0"},
    "parameters": [
        {"name": "a1", "value": 0.5, "unit": "-", "type": "fitted", "description": "coefficient of `q`"},
        {"name": "n0", "value": 2.0, "unit": "-", "type": "fixed",
         "description": "normalisation of the quadratic term; chosen as the largest value of `q` in the training data, so that `b1` has the scale of `a1`"},
        {"name": "b1", "value": 1.0, "unit": "-", "type": "tied", "equation": "2*a1",
         "description": "coefficient of `q**2/n0`, tied to `a1` by the assumption stated in the discussion"},
    ],
    "estimation": {
        "criterion": "sum of squared differences between the expression `z` and the column `z`, because the expression gives `z` directly and no row is known to be more accurate than another",
        "data": "data/train.csv, all rows",
        "method": (
            "The value of `a1` was estimated by ordinary least squares with numpy.linalg.lstsq. With `b1 = 2*a1` the "
            "expression is linear in the one fitted parameter `a1`, so the least-squares solution is obtained directly "
            "and an iterative method is not needed; for the same reason the method needs no starting values. `a1` is "
            "the only fitted parameter and was estimated in one step. The method uses no random numbers, so that no "
            "seed applies."
        ),
        "script": "fit_M01.py",
    },
    "discussion": {
        "family": "State the model family by its established name.",
        "interpretation": "State what each term represents.",
        "origin": "State how you arrived at this expression.",
        "limitations": "State what the data do not determine and where the model is not expected to hold.",
    },
}
"""The example candidate: one fitted, one fixed and one tied parameter."""

EXAMPLE_POOL: dict[str, Any] = {
    "order": [EXAMPLE_LABEL],
    "recommended": EXAMPLE_LABEL,
    "reason": "State why you recommend this candidate, or why you recommend none.",
}
"""The example pool file."""

EXAMPLE_TRAINING_ROWS = "q,z\n0.0,0.0\n0.5,0.5\n1.0,1.5\n"
"""A training table of the invented task of the example (for checking the example)."""


def example_check_config() -> _checks.CheckConfig:
    """The check configuration of the invented task of the example: input ``q``, output ``z``."""
    return _checks.CheckConfig(
        task_id="format-example",
        formulation="static",
        columns={"q": ("input",), "z": ("output",)},
        arguments=("q",),
        expression_keys=("z",),
        delays=(),
        constants={},
        functions=_checks.DEFAULT_FUNCTIONS,
        added_functions=(),
        question_ids=(),
        pool_cap=10,
        trajectory_column=None,
    )


def _explained(fields: tuple[str, ...], texts: dict[str, str], what: str) -> list[str]:
    missing = [f for f in fields if f not in texts]
    if missing or set(texts) - set(fields):
        raise RuntimeError(f"the explanations of the {what} do not match its fields: {missing or sorted(set(texts) - set(fields))}")
    return [f"  - `{f}`: {texts[f]};" for f in fields[:-1]] + [f"  - `{fields[-1]}`: {texts[fields[-1]]}."]


def _json(data: Any) -> list[str]:
    return ["```json"] + json.dumps(data, indent=2, ensure_ascii=False).splitlines() + ["```"]


def format_reference() -> str:
    """The text of ``FORMAT.md``: one fixed text."""
    if tuple(_checks.CANDIDATE_FIELDS) != ("expressions", "parameters", "estimation", "discussion") or tuple(
        _checks.CANDIDATE_FIELDS_OPTIONAL
    ) != ("answers", "predecessor"):
        raise RuntimeError("the format reference does not describe the candidate fields of the check module")
    parameter_fields = tuple(_checks.PARAMETER_FIELDS_REQUIRED) + tuple(_checks.PARAMETER_FIELDS_OPTIONAL)
    out = [
        "# Model file format",
        "",
        f"This file is the same for every task. `{BRIEF_FILE}` names the expression keys, the variables and the "
        "permitted functions of your task.",
        "",
        "## Candidate file `models/<label>.json`",
        "",
        "Write one JSON file per candidate. The label is the file name: a letter, then up to 31 letters, digits, "
        "`_` or `-`. The file has these fields and no others:",
        "",
        f"- `expressions`: one expression text per expression key named in `{BRIEF_FILE}`.",
        "- `parameters`: one row per parameter. A parameter is a constant of the expressions that you name yourself, "
        "for example `a1`. Its row has",
    ]
    out += _explained(parameter_fields, PARAMETER_FIELD_TEXT, "parameter row")
    out += ["- `estimation`: how the values of the fitted parameters of this candidate were obtained and why in this "
            "way; for every fitted parameter it must be clear how its value was found. Write the record for this "
            "candidate model, not for the run as a whole: its own criterion, data, method and starting values, with "
            "the reasons that apply to this candidate. The record has"]
    out += _explained(tuple(_checks.ESTIMATION_FIELDS), ESTIMATION_FIELD_TEXT, "estimation record")
    out += ["- `discussion`: four texts, in this order:"]
    out += _explained(tuple(_checks.DISCUSSION_SECTIONS), DISCUSSION_SECTION_TEXT, "discussion")
    out += [
        f"- `answers`: only when `{BRIEF_FILE}` asks questions about the candidates: one text per question identifier.",
        "- `predecessor`: only in a later round of an interactive session, and optional: the label of the candidate "
        "of the previous pool that this candidate revises.",
        "",
        "## Expressions",
        "",
        "An expression is a text in Python syntax. It may contain:",
        "",
        f"- the variables that `{BRIEF_FILE}` names as the arguments of the expression;",
        "- your parameters, each with a row in `parameters`;",
        f"- the constants `pi` and `E`, the given constants that `{BRIEF_FILE}` lists, and numbers;",
        f"- these operators and functions, unless `{BRIEF_FILE}` states another list: "
        + " ".join(f"`{name}`" for name in ("+", "-", "*", "/", "**") + tuple(_checks.DEFAULT_FUNCTIONS))
        + ".",
        "",
        "`**` is the power (not `^`), and `log` is the natural logarithm. `Piecewise` takes pairs `(value, condition)` "
        "and ends with a pair `(value, True)`, for example `Piecewise((a1*q, (q > 0) & (q < 1)), (0, True))`. A "
        "condition is a comparison `<`, `<=`, `>`, `>=`, `Eq(a, b)` or `Ne(a, b)`, each in parentheses, combined with "
        "`&`, `|` and `~`.",
        "",
        "A number that fixes the form of the expression, such as 2 in `q**2`, may be written directly. A value "
        "obtained by estimation is a parameter with a row in `parameters`, never a number written into the "
        "expression. Every parameter row must be used in an expression or in a tie equation.",
        "",
        "## Pool file `models/pool.json`",
        "",
    ]
    pool = _explained(tuple(_checks.POOL_FIELDS), POOL_FIELD_TEXT, "pool file")
    out += [line[2:] for line in pool]
    out += [
        "",
        "Every file `models/<label>.json` must be listed in `order`.",
        "",
        "## Example",
        "",
        "An invented task with one input `q` and one output `z`, whose expression key is `z`. The example shows the "
        "format only: its model is not a proposal, and its discussion texts say what your texts must contain.",
        "",
        f"`models/{EXAMPLE_LABEL}.json`:",
        "",
    ]
    out += _json(EXAMPLE_CANDIDATE)
    out += ["", "`models/pool.json`:", ""]
    out += _json(EXAMPLE_POOL)
    out += [
        "",
        "## Checking",
        "",
        f"`{CHECK_COMMAND}` checks every file against these rules and evaluates each expression on the training "
        "data. It names each error with its rule. Correct the errors and run it again.",
        "",
        "## Writing",
        "",
    ]
    out += [f"- {rule}" for rule in WRITING_RULES]
    text = "\n".join(out) + "\n"
    found = [w for w in FORBIDDEN_WORDS if re.search(rf"(?<![A-Za-z0-9_]){re.escape(w)}(?![A-Za-z0-9_])", text, re.I)]
    if found:
        raise RuntimeError(f"the format reference names a task: {found}")
    return text


assert FORMAT_FILE == "FORMAT.md"
