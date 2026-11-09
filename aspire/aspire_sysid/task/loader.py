"""Loader and validator of task specifications, schema version 1.

Columns, roles, formulations, default column order, NARX delays, task information,
withheld information, permitted functions, constants, formal
and natural-language requirements, evaluation settings and
budgets.

The loader reads ``task.yaml``, the training and validation tables and checks the paths of the
supporting files. It never resolves or opens a sealed file (test data, reference expression);
their declared locations are only checked for their lexical form here and are resolved by
``aspire_sysid.evaluate.sealed``. The complete validation of a task,
including the sealed part, is :func:`aspire_sysid.task.validate.validate_task`.
"""

from __future__ import annotations

import math
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import numpy as np
import sympy as sp
import yaml

from .expr import ExpressionError, known_function_names, parse_task_expression
from .schema import (
    DEFAULT_FUNCTIONS,
    DEFAULT_ROUND_BUDGET,
    EVALUATION_MODES,
    FORMULATIONS,
    INPUT_HOLDS,
    INTEGRATORS,
    REQUIREMENT_TYPES,
    RESERVED_NAMES,
    SEALED_FOLDERS,
    ROLES,
    SCHEMA_VERSION,
    SCORING_RULES,
    VERIFICATIONS,
    AddedFunction,
    Budget,
    Column,
    Constant,
    ContextFile,
    DataSpec,
    Delay,
    DiscussionQuestion,
    Dynamics,
    Evaluation,
    FailureLimit,
    Limits,
    NLRequirement,
    Requirement,
    SealedPart,
    SealedReferenceEntry,
    SealedTestEntry,
    Source,
    TaskError,
    TaskSpec,
    Tolerance,
    argument_names,
    required_expression_keys,
)
from .table import Table, TableError, read_table, trajectory_blocks

TASK_FILE = "task.yaml"
"""Name of the specification file in a task folder."""

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TASK_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")

_TOP_KEYS = {
    "schema_version",
    "id",
    "title",
    "formulation",
    "description",
    "intended_use",
    "columns",
    "dynamics",
    "evaluation",
    "data",
    "constants",
    "functions",
    "added_functions",
    "requirements",
    "requirements_nl",
    "literature",
    "context",
    "discussion_questions",
    "pool_cap",
    "budget",
    "test",
    "reference",
}


class _Errors(list):
    """Collector of validation messages."""

    def add(self, msg: str) -> None:
        self.append(msg)


# --------------------------------------------------------------------------------------
# paths


def check_relative_path(rel: Any) -> str | None:
    """Return an error message if ``rel`` is not a safe relative path, else ``None``.

    Every path resolves inside the task folder: the path must be a
    non-empty string, relative on POSIX and Windows, and free of ``..`` components.
    """
    if not isinstance(rel, str) or not rel.strip():
        return "path is empty or not a string"
    if PurePosixPath(rel).is_absolute() or PureWindowsPath(rel).is_absolute() or PureWindowsPath(rel).drive:
        return f"path {rel!r} is absolute"
    parts = re.split(r"[\\/]", rel)
    if ".." in parts:
        return f"path {rel!r} contains '..'"
    return None


def resolve_inside(
    task_dir: Path, rel: Any, forbidden_dirs: tuple[Path, ...] = ()
) -> tuple[Path | None, str | None]:
    """Resolve ``rel`` inside ``task_dir``; return ``(path, None)`` or ``(None, error)``.

    Every path resolves inside the task folder, and sealed
    data never reach the agent: the path must be relative, without ``..``, must resolve
    (symbolic links followed) inside the task folder and outside every folder of
    ``forbidden_dirs`` (absolute, resolved), and must name an existing regular file. The file is
    not opened.
    """
    err = check_relative_path(rel)
    if err:
        return None, err
    root = task_dir.resolve()
    target = (task_dir / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None, f"path {rel!r} resolves outside the task folder"
    for d in forbidden_dirs:
        if target == d or d in target.parents:
            return None, f"path {rel!r} points into the sealed folder {d.relative_to(root).as_posix()}/"
    if not target.is_file():
        return None, f"path {rel!r} does not name an existing file"
    return target, None


def sealed_dirs(task_dir: Path, raw: dict) -> tuple[Path, ...]:
    """Resolved sealed folders of a task: :data:`SEALED_FOLDERS` and the folders of the declared
    test and reference files. Nothing is opened."""
    root = task_dir.resolve()
    out = {(root / name).resolve() for name in SEALED_FOLDERS}
    entries = list(raw.get("test") or []) if isinstance(raw.get("test"), list) else []
    if isinstance(raw.get("reference"), dict):
        entries.append(raw["reference"])
    for e in entries:
        rel = e.get("file") if isinstance(e, dict) else None
        if check_relative_path(rel) is None:
            first = re.split(r"[\\/]", rel)[0]
            out.add((root / first).resolve() if first != rel else (root / rel).resolve().parent)
            out.add((root / rel).resolve().parent)
    return tuple(sorted(d for d in out if d != root))


# --------------------------------------------------------------------------------------
# small field readers


def _str(d: dict, key: str, errs: _Errors, where: str, required: bool = True) -> str | None:
    v = d.get(key)
    if v is None:
        if required:
            errs.add(f"{where}: field '{key}' is required")
        return None
    if not isinstance(v, str) or not v.strip():
        errs.add(f"{where}: field '{key}' must be a non-empty string")
        return None
    return v.strip()


def _num(v: Any, errs: _Errors, where: str) -> float | None:
    if isinstance(v, bool):
        errs.add(f"{where}: expected a number, got {v!r}")
        return None
    if isinstance(v, (int, float)):
        x = float(v)
    elif isinstance(v, str):
        try:
            x = float(sp.sympify(v, locals={"pi": sp.pi, "E": sp.E, "oo": sp.oo}).evalf())
        except Exception:
            errs.add(f"{where}: cannot read {v!r} as a number")
            return None
    else:
        errs.add(f"{where}: expected a number, got {v!r}")
        return None
    if not math.isfinite(x):
        errs.add(f"{where}: {v!r} is not finite")
        return None
    return x


def _int(v: Any, errs: _Errors, where: str, minimum: int) -> int | None:
    if isinstance(v, bool) or not isinstance(v, int):
        errs.add(f"{where}: expected an integer, got {v!r}")
        return None
    if v < minimum:
        errs.add(f"{where}: must be at least {minimum}, got {v}")
        return None
    return v


def _interval(v: Any, errs: _Errors, where: str) -> tuple[float, float] | None:
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        errs.add(f"{where}: expected an interval [lower, upper], got {v!r}")
        return None
    lo, hi = _num(v[0], errs, where), _num(v[1], errs, where)
    if lo is None or hi is None:
        return None
    if lo > hi:
        errs.add(f"{where}: lower bound {lo} exceeds upper bound {hi}")
        return None
    return (lo, hi)


def _source(v: Any, errs: _Errors, where: str) -> Source | None:
    if not isinstance(v, dict):
        errs.add(f"{where}: 'source' must be a mapping with 'stated_by' and 'date'")
        return None
    by = _str(v, "stated_by", errs, where)
    date = v.get("date")
    if date is None:
        errs.add(f"{where}: field 'date' is required")
    date = str(date) if date is not None else None
    note = v.get("note")
    if by is None or date is None:
        return None
    return Source(stated_by=by, date=date, note=str(note).strip() if note else None)


def _limits(v: Any, errs: _Errors, where: str, default: tuple | None) -> Limits | None:
    if v is None:
        if default is None:
            return None
        return Limits(turns=int(default[0]), seconds=float(default[1]), usd=float(default[2]))
    if not isinstance(v, dict):
        errs.add(f"{where}: expected a mapping with turns, seconds and usd")
        return None
    turns = _int(v.get("turns"), errs, f"{where}.turns", 1)
    secs = _num(v.get("seconds"), errs, f"{where}.seconds")
    usd = _num(v.get("usd"), errs, f"{where}.usd")
    if secs is not None and secs <= 0:
        errs.add(f"{where}.seconds: must be positive")
    if usd is not None and usd <= 0:
        errs.add(f"{where}.usd: must be positive")
    if None in (turns, secs, usd):
        return None
    return Limits(turns=turns, seconds=secs, usd=usd)


def _as_list(v: Any, errs: _Errors, where: str) -> list:
    if v is None:
        return []
    if not isinstance(v, list):
        errs.add(f"{where}: expected a list")
        return []
    return v


def _names(v: Any) -> tuple[str, ...]:
    if v is None:
        return ()
    if isinstance(v, str):
        return (v,)
    return tuple(str(x) for x in v)


# --------------------------------------------------------------------------------------
# main entry point


def load_task(task_dir: str | Path) -> TaskSpec:
    """Load and validate ``task_dir/task.yaml`` without touching the sealed files.

    Raises :class:`TaskError` listing every violation. Validations: exactly one output column; roles
    consistent with ``dynamics.states`` and ``dynamics.inputs``; every ``state_derivative``
    names a declared state; every non-sealed path resolves inside the task folder; constants
    and functions do not collide with column names; the default column order of a static
    table without roles (inputs in columns 1 to N − 1, output in column N).
    """
    task_dir = Path(task_dir).resolve()
    errs = _Errors()
    spec_path = task_dir / TASK_FILE
    if not spec_path.is_file():
        raise TaskError([f"{TASK_FILE} not found"], task_dir)
    try:
        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaskError([f"{TASK_FILE} is not valid YAML: {exc}"], task_dir) from exc
    if not isinstance(raw, dict):
        raise TaskError([f"{TASK_FILE} must contain a mapping"], task_dir)

    for key in sorted(set(raw) - _TOP_KEYS):
        errs.add(f"unknown top-level field '{key}'")

    if raw.get("schema_version") != SCHEMA_VERSION:
        errs.add(f"schema_version must be {SCHEMA_VERSION}, got {raw.get('schema_version')!r}")
    task_id = _str(raw, "id", errs, "task")
    if task_id is not None and not _TASK_ID.match(task_id):
        errs.add(f"id {task_id!r} must consist of lower-case letters, digits and hyphens")
    title = _str(raw, "title", errs, "task")
    description = _str(raw, "description", errs, "task", required=False)
    intended_use = _str(raw, "intended_use", errs, "task", required=False)
    formulation = raw.get("formulation")
    if formulation not in FORMULATIONS:
        errs.add(f"formulation must be one of {', '.join(FORMULATIONS)}, got {formulation!r}")
        raise TaskError(errs, task_dir)

    # -- data ------------------------------------------------------------------------
    data_raw = raw.get("data")
    if not isinstance(data_raw, dict):
        errs.add("data: a mapping with at least 'train' is required")
        raise TaskError(errs, task_dir)
    for key in sorted(set(data_raw) - {"train", "val", "trajectory_column", "noise", "preprocessing", "source_name"}):
        errs.add(f"data: unknown field '{key}'")
    forbidden = sealed_dirs(task_dir, raw)
    train_path, err = resolve_inside(task_dir, data_raw.get("train"), forbidden)
    if err:
        errs.add(f"data.train: {err}")
    val_path = None
    if data_raw.get("val") is not None:
        val_path, err = resolve_inside(task_dir, data_raw.get("val"), forbidden)
        if err:
            errs.add(f"data.val: {err}")
    traj_col = data_raw.get("trajectory_column")
    if traj_col is not None and (not isinstance(traj_col, str) or not _IDENT.match(traj_col)):
        errs.add(f"data.trajectory_column: {traj_col!r} is not a valid column name")
        traj_col = None
    source_names: dict[str, tuple[str, ...]] = {}
    sn = data_raw.get("source_name")
    if sn is not None:
        if not isinstance(sn, dict) or set(sn) - {"train", "val"}:
            errs.add("data.source_name: expected a mapping with the keys 'train' and/or 'val'")
        else:
            source_names = {k: _names(v) for k, v in sn.items()}
    tables: dict[str, Table] = {}
    for split, path in (("train", train_path), ("val", val_path)):
        if path is None:
            continue
        try:
            tables[split] = read_table(path)
        except TableError as exc:
            errs.add(f"data.{split}: {exc}")
    if "train" not in tables:
        raise TaskError(errs, task_dir)
    train = tables["train"]

    # -- columns and roles -----------------------------------------------------------
    header_vars = [h for h in train.header if h != traj_col]
    if traj_col is not None and traj_col not in train.header:
        errs.add(f"data.trajectory_column: column {traj_col!r} is not in the training table")
    cols_raw = raw.get("columns")
    columns_given = cols_raw is not None
    roles_defaulted = False
    columns: list[Column] = []
    if cols_raw is None:
        if formulation != "static":
            errs.add("columns: required for a dynamic task")
            raise TaskError(errs, task_dir)
        cols_raw = [{"name": h} for h in header_vars]
    if not isinstance(cols_raw, list) or not cols_raw:
        errs.add("columns: expected a non-empty list")
        raise TaskError(errs, task_dir)
    with_roles = [isinstance(c, dict) and c.get("roles") is not None for c in cols_raw]
    if formulation == "static" and not any(with_roles):
        roles_defaulted = True
    elif not all(with_roles):
        errs.add("columns: roles must be given for every column (only a static table without any roles uses the default column order)")
    n_cols = len(cols_raw)
    for i, c in enumerate(cols_raw):
        where = f"columns[{i}]"
        if not isinstance(c, dict):
            errs.add(f"{where}: expected a mapping")
            continue
        for key in sorted(set(c) - {"name", "symbol", "roles", "unit", "description", "range", "derivative_of"}):
            errs.add(f"{where}: unknown field '{key}'")
        name = _str(c, "name", errs, where)
        if name is None:
            continue
        if not _IDENT.match(name):
            errs.add(f"{where}: column name {name!r} is not an identifier")
        if roles_defaulted:
            # Default roles: inputs in columns 1 to N - 1, output in column N.
            roles: tuple[str, ...] = ("output",) if i == n_cols - 1 else ("input",)
        else:
            roles = _names(c.get("roles"))
            bad = [r for r in roles if r not in ROLES]
            if bad or not roles:
                errs.add(f"{where}: roles {list(roles)} must be a non-empty subset of {', '.join(ROLES)}")
        rng = None
        if c.get("range") is not None:
            rng = _interval(c.get("range"), errs, f"{where}.range")
        deriv_of = c.get("derivative_of")
        columns.append(
            Column(
                name=name,
                roles=roles,
                unit=str(c.get("unit")) if c.get("unit") is not None else "not stated",
                description=str(c.get("description", "")).strip(),
                symbol=str(c["symbol"]) if c.get("symbol") is not None else None,
                range=rng,
                derivative_of=str(deriv_of) if deriv_of is not None else None,
            )
        )
        if c.get("unit") is None and columns_given:
            errs.add(f"{where}: field 'unit' is required")
    names = [c.name for c in columns]
    if len(set(names)) != len(names):
        errs.add("columns: duplicate column names")
    if traj_col is not None and traj_col in names:
        errs.add(f"data.trajectory_column {traj_col!r} must not also be a model variable")
    if header_vars != names:
        errs.add(f"data.train: header {list(train.header)} does not match the declared columns {names} (plus the trajectory column)")
    if "val" in tables and list(tables["val"].header) != list(train.header):
        errs.add(f"data.val: header {list(tables['val'].header)} differs from the training header {list(train.header)}")

    outputs = [c.name for c in columns if "output" in c.roles]
    if len(outputs) != 1:
        errs.add(f"columns: exactly one column must have the role 'output', found {len(outputs)} ({', '.join(outputs) or 'none'})")
    for c in columns:
        if "input" in c.roles and ("state" in c.roles or "output" in c.roles):
            errs.add(f"column {c.name!r}: an input cannot also be a state or the output")
        if "state_derivative" in c.roles and set(c.roles) != {"state_derivative"}:
            errs.add(f"column {c.name!r}: a state derivative cannot carry another role")
        if c.derivative_of is not None and "state_derivative" not in c.roles:
            errs.add(f"column {c.name!r}: 'derivative_of' is only allowed for the role state_derivative")

    # -- functions and constants -----------------------------------------------------
    functions_raw = raw.get("functions")
    if functions_raw is None:
        functions = DEFAULT_FUNCTIONS
    else:
        functions = _names(functions_raw)
        unknown = [f for f in functions if f not in known_function_names()]
        if unknown:
            errs.add(f"functions: unknown function(s) {', '.join(unknown)}; permitted are {', '.join(known_function_names())} or an added function")
    added: list[AddedFunction] = []
    added_lams: dict[str, sp.Lambda] = {}
    for i, a in enumerate(_as_list(raw.get("added_functions"), errs, "added_functions")):
        where = f"added_functions[{i}]"
        if not isinstance(a, dict):
            errs.add(f"{where}: expected a mapping")
            continue
        name = _str(a, "name", errs, where)
        args = _names(a.get("arguments"))
        definition = _str(a, "definition", errs, where)
        domain = _str(a, "domain", errs, where)
        if name is None or definition is None or domain is None:
            continue
        if not _IDENT.match(name) or not args or not all(_IDENT.match(x) for x in args):
            errs.add(f"{where}: name and arguments must be identifiers")
            continue
        try:
            body = parse_task_expression(definition, args, functions)
            added_lams[name] = sp.Lambda(tuple(sp.Symbol(x, real=True) for x in args), body)
        except ExpressionError as exc:
            errs.add(f"{where}.definition: {exc}")
        added.append(AddedFunction(name=name, arguments=args, definition=definition, domain=domain))
    all_functions = set(functions) | {a.name for a in added}
    for n in names:
        if n in all_functions or n in known_function_names():
            errs.add(f"column {n!r} collides with the name of a function")
        if n in RESERVED_NAMES:
            errs.add(f"column {n!r} collides with the constant {n}")

    constants: list[Constant] = []
    for i, c in enumerate(_as_list(raw.get("constants"), errs, "constants")):
        where = f"constants[{i}]"
        if not isinstance(c, dict):
            errs.add(f"{where}: expected a mapping")
            continue
        name = _str(c, "name", errs, where)
        value = _num(c.get("value"), errs, f"{where}.value")
        unit = _str(c, "unit", errs, where)
        src = _str(c, "source", errs, where)
        if name is None or value is None or unit is None or src is None:
            continue
        if not _IDENT.match(name):
            errs.add(f"{where}: constant name {name!r} is not an identifier")
        if name in names:
            errs.add(f"constant {name!r} collides with a column name")
        if name in all_functions or name in known_function_names() or name in RESERVED_NAMES:
            errs.add(f"constant {name!r} collides with a function or reserved name")
        constants.append(Constant(name=name, value=value, unit=unit, source=src))
    const_names = [c.name for c in constants]
    if len(set(const_names)) != len(const_names):
        errs.add("constants: duplicate names")

    # -- dynamics --------------------------------------------------------------------
    output = outputs[0] if len(outputs) == 1 else None
    dyn_raw = raw.get("dynamics")
    dynamics: Dynamics | None = None
    if formulation == "static":
        if dyn_raw is not None:
            errs.add("dynamics: must be absent for a static task")
        for c in columns:
            if set(c.roles) - {"input", "output"}:
                errs.add(f"column {c.name!r}: a static task has only input and output columns")
        if not any("input" in c.roles for c in columns):
            errs.add("columns: a static task needs at least one input column")
    else:
        dynamics = _load_dynamics(dyn_raw, formulation, columns, output, const_names, functions, added_lams, errs)

    delays = dynamics.delays if dynamics is not None else ()
    inputs = dynamics.inputs if dynamics is not None else tuple(c.name for c in columns if "input" in c.roles)
    states = dynamics.states if dynamics is not None else ()
    args = argument_names(formulation, inputs, states, delays)
    keys = required_expression_keys(formulation, output or "y", states) if output else ()
    deriv_cols = {f"d{c.derivative_of}": c.name for c in columns if c.derivative_of}
    for k in keys:
        if formulation == "static" and k == output:
            continue
        if k in names and deriv_cols.get(k) == k:
            continue  # the state-derivative column of the same state carries the key's name
        if k in names or k in const_names:
            errs.add(f"expression key {k!r} collides with a column or constant name")

    # -- evaluation ------------------------------------------------------------------
    evaluation = _load_evaluation(raw.get("evaluation"), formulation, dynamics, columns, output, errs)

    # -- training data content -------------------------------------------------------
    if header_vars == names:
        _check_tables(tables, columns, traj_col, evaluation, errs)

    # -- requirements ----------------------------------------------------------------
    ranges = {c.name: c.range for c in columns if c.range is not None}
    for d in delays:
        if d.variable in ranges:
            ranges[d.name] = ranges[d.variable]
    requirements = _load_requirements(
        raw.get("requirements"), keys, output, args, ranges, const_names, functions, added_lams, formulation, errs
    )
    requirements_nl: list[NLRequirement] = []
    for i, r in enumerate(_as_list(raw.get("requirements_nl"), errs, "requirements_nl")):
        where = f"requirements_nl[{i}]"
        if not isinstance(r, dict):
            errs.add(f"{where}: expected a mapping with 'text' and 'source'")
            continue
        text = _str(r, "text", errs, where)
        src = _source(r.get("source"), errs, where)
        rid = str(r.get("id", f"NL{i + 1}"))
        if text is not None and src is not None:
            requirements_nl.append(NLRequirement(id=rid, text=text, source=src))
    all_ids = [r.id for r in requirements] + [r.id for r in requirements_nl]
    if len(set(all_ids)) != len(all_ids):
        errs.add("requirements: identifiers must be unique across formal and natural-language requirements")

    # -- literature, context, questions ----------------------------------------------
    literature = []
    for i, ref in enumerate(_as_list(raw.get("literature"), errs, "literature")):
        if not isinstance(ref, str) or not ref.strip():
            errs.add(f"literature[{i}]: expected a non-empty string")
        else:
            literature.append(" ".join(ref.split()))
    context: list[ContextFile] = []
    for i, c in enumerate(_as_list(raw.get("context"), errs, "context")):
        where = f"context[{i}]"
        if not isinstance(c, dict):
            errs.add(f"{where}: expected a mapping with 'file' and 'note'")
            continue
        path, err = resolve_inside(task_dir, c.get("file"), forbidden)
        note = _str(c, "note", errs, where)
        if err:
            errs.add(f"{where}.file: {err}")
        elif note is not None:
            context.append(ContextFile(path=path, note=note))
    ctx_names = [c.path.name for c in context]
    if len(set(ctx_names)) != len(ctx_names):
        errs.add("context: file names must be unique (they are copied to context/<name>)")
    questions: list[DiscussionQuestion] = []
    for i, q in enumerate(_as_list(raw.get("discussion_questions"), errs, "discussion_questions")):
        if isinstance(q, str):
            questions.append(DiscussionQuestion(id=f"Q{i + 1}", text=" ".join(q.split())))
        elif isinstance(q, dict) and isinstance(q.get("text"), str):
            questions.append(DiscussionQuestion(id=str(q.get("id", f"Q{i + 1}")), text=" ".join(q["text"].split())))
        else:
            errs.add(f"discussion_questions[{i}]: expected a string or a mapping with 'id' and 'text'")
    if len({q.id for q in questions}) != len(questions):
        errs.add("discussion_questions: identifiers must be unique")

    pool_cap = _int(raw.get("pool_cap"), errs, "pool_cap", 1)

    # -- budget ----------------------------------------------------------------------
    b = raw.get("budget") or {}
    if not isinstance(b, dict):
        errs.add("budget: expected a mapping")
        b = {}
    for key in sorted(set(b) - {"round", "session", "analysis_exchange"}):
        errs.add(f"budget: unknown field '{key}'")
    rnd = _limits(b.get("round"), errs, "budget.round", DEFAULT_ROUND_BUDGET)
    ses = _limits(b.get("session"), errs, "budget.session", (rnd.turns, rnd.seconds, rnd.usd) if rnd else DEFAULT_ROUND_BUDGET)
    ana = _limits(b.get("analysis_exchange"), errs, "budget.analysis_exchange", None)
    if rnd and ses and (ses.turns < rnd.turns or ses.seconds < rnd.seconds or ses.usd < rnd.usd):
        errs.add("budget.session: every session limit must be at least the round limit")

    # -- sealed part (lexical checks only) -------------------------------------------
    sealed = _load_sealed(raw.get("test"), raw.get("reference"), args, ranges, errs)

    if errs:
        raise TaskError(errs, task_dir)

    assert train_path is not None and output is not None and evaluation is not None
    assert pool_cap is not None and rnd is not None and ses is not None
    return TaskSpec(
        task_dir=task_dir,
        schema_version=SCHEMA_VERSION,
        id=task_id,
        title=" ".join(title.split()),
        formulation=formulation,
        description=" ".join(description.split()) if description else None,
        intended_use=" ".join(intended_use.split()) if intended_use else None,
        columns=tuple(columns),
        dynamics=dynamics,
        evaluation=evaluation,
        data=DataSpec(
            train_path=train_path,
            val_path=val_path,
            trajectory_column=traj_col,
            noise=" ".join(str(data_raw["noise"]).split()) if data_raw.get("noise") else None,
            preprocessing=" ".join(str(data_raw["preprocessing"]).split()) if data_raw.get("preprocessing") else None,
            source_names=source_names,
        ),
        constants=tuple(constants),
        functions=tuple(functions),
        added_functions=tuple(added),
        requirements=tuple(requirements),
        requirements_nl=tuple(requirements_nl),
        literature=tuple(literature),
        context=tuple(context),
        discussion_questions=tuple(questions),
        pool_cap=pool_cap,
        budget=Budget(round=rnd, session=ses, analysis_exchange=ana),
        sealed=sealed,
        roles_defaulted=roles_defaulted,
    )


# --------------------------------------------------------------------------------------
# sections


def _load_dynamics(
    d: Any,
    formulation: str,
    columns: list[Column],
    output: str | None,
    const_names: list[str],
    functions: tuple[str, ...],
    added_lams: dict,
    errs: _Errors,
) -> Dynamics | None:
    """Dynamic settings and their consistency with the roles."""
    if not isinstance(d, dict):
        errs.add("dynamics: required for a dynamic task")
        return None
    allowed = {"sampling_period", "states", "inputs", "measurement", "input_hold", "integrator", "substeps", "delays", "shift_equations"}
    for key in sorted(set(d) - allowed):
        errs.add(f"dynamics: unknown field '{key}'")
    ts = _num(d.get("sampling_period"), errs, "dynamics.sampling_period")
    if ts is not None and ts <= 0:
        errs.add("dynamics.sampling_period: must be positive")
    states = _names(d.get("states"))
    inputs = _names(d.get("inputs"))
    names = [c.name for c in columns]
    by_name = {c.name: c for c in columns}
    if not states:
        errs.add("dynamics.states: at least one state is required")
    for s in states:
        if s not in by_name:
            errs.add(f"dynamics.states: {s!r} is not a column")
        elif "state" not in by_name[s].roles:
            errs.add(f"dynamics.states: column {s!r} does not have the role 'state'")
    for u in inputs:
        if u not in by_name:
            errs.add(f"dynamics.inputs: {u!r} is not a column")
        elif "input" not in by_name[u].roles:
            errs.add(f"dynamics.inputs: column {u!r} does not have the role 'input'")
    for c in columns:
        if "state" in c.roles and c.name not in states:
            errs.add(f"column {c.name!r} has the role 'state' but is not declared in dynamics.states")
        if "input" in c.roles and c.name not in inputs:
            errs.add(f"column {c.name!r} has the role 'input' but is not declared in dynamics.inputs")
        if "state_derivative" in c.roles:
            if formulation != "continuous":
                errs.add(f"column {c.name!r}: a state derivative requires the continuous formulation")
            if c.derivative_of is None:
                errs.add(f"column {c.name!r}: a state derivative must name its state in 'derivative_of'")
            elif c.derivative_of not in states:
                errs.add(f"column {c.name!r}: 'derivative_of' names {c.derivative_of!r}, which is not a declared state")
    derivs = [c.derivative_of for c in columns if c.derivative_of]
    if len(set(derivs)) != len(derivs):
        errs.add("columns: at most one state-derivative column per state")
    if len(set(states)) != len(states) or len(set(inputs)) != len(inputs):
        errs.add("dynamics: duplicate names in states or inputs")

    input_hold = d.get("input_hold", "zero_order")
    if input_hold not in INPUT_HOLDS:
        errs.add(f"dynamics.input_hold: must be one of {', '.join(INPUT_HOLDS)}")
    integrator = d.get("integrator", "rk4")
    if integrator not in INTEGRATORS:
        errs.add(f"dynamics.integrator: must be one of {', '.join(INTEGRATORS)}")
    substeps = _int(d.get("substeps", 1), errs, "dynamics.substeps", 1) or 1
    if formulation != "continuous" and ("integrator" in d or "substeps" in d):
        errs.add("dynamics: integrator and substeps apply only to the continuous formulation")

    delays: list[Delay] = []
    shift: dict[str, str] = {}
    if formulation == "narx":
        if output is not None and tuple(states) != (output,):
            errs.add(f"dynamics.states: a NARX task has the output as its only declared state, expected [{output}]")
        for i, dl in enumerate(_as_list(d.get("delays"), errs, "dynamics.delays")):
            where = f"dynamics.delays[{i}]"
            if not isinstance(dl, dict):
                errs.add(f"{where}: expected a mapping with name, variable and lag")
                continue
            name, var = dl.get("name"), dl.get("variable")
            lag = _int(dl.get("lag"), errs, f"{where}.lag", 1)
            if not isinstance(name, str) or not _IDENT.match(name):
                errs.add(f"{where}: name {name!r} is not an identifier")
                continue
            if name in names or name in const_names or name in functions:
                errs.add(f"{where}: name {name!r} collides with a column, constant or function")
            if var not in states and var not in inputs:
                errs.add(f"{where}: variable {var!r} is neither the output state nor an input")
                continue
            if lag is not None:
                delays.append(Delay(name=name, variable=str(var), lag=lag))
        if not delays:
            errs.add("dynamics.delays: a NARX task declares at least one delayed variable")
        by_var: dict[str, dict[int, str]] = {}
        for dl in delays:
            by_var.setdefault(dl.variable, {})[dl.lag] = dl.name
        for var, lags in by_var.items():
            if sorted(lags) != list(range(1, max(lags) + 1)):
                errs.add(f"dynamics.delays: the delays of {var!r} must be consecutive from lag 1, got {sorted(lags)}")
                continue
            for lag, name in lags.items():
                shift[name] = var if lag == 1 else lags[lag - 1]
        if len({dl.name for dl in delays}) != len(delays):
            errs.add("dynamics.delays: duplicate names")
        given = d.get("shift_equations")
        if given is not None:
            if not isinstance(given, dict) or {str(k): str(v).strip() for k, v in given.items()} != shift:
                errs.add(f"dynamics.shift_equations: must equal the shifts implied by the delays, {shift}")
    elif d.get("delays") or d.get("shift_equations"):
        errs.add("dynamics: delays and shift_equations apply only to the NARX formulation")

    measurement = d.get("measurement")
    if measurement is None:
        if output is not None and output not in states:
            errs.add(f"dynamics.measurement: required, because the output {output!r} is not a state")
        measurement = output or ""
    else:
        measurement = str(measurement).strip()
        try:
            parse_task_expression(measurement, list(states) + list(inputs) + const_names, functions, added=added_lams)
        except ExpressionError as exc:
            errs.add(f"dynamics.measurement: {exc}")
    if ts is None or not states:
        return None
    return Dynamics(
        sampling_period=ts,
        states=states,
        inputs=inputs,
        measurement=measurement,
        input_hold=input_hold,
        integrator=integrator if formulation == "continuous" else "rk4",
        substeps=substeps,
        delays=tuple(delays),
        shift_equations=shift,
    )


def _load_evaluation(
    e: Any, formulation: str, dynamics: Dynamics | None, columns: list[Column], output: str | None, errs: _Errors
) -> Evaluation | None:
    """Evaluation mode, initialization, scoring, failure limits, time limit."""
    if not isinstance(e, dict):
        errs.add("evaluation: a mapping is required")
        return None
    for key in sorted(set(e) - {"mode", "initialization", "scoring", "failure_limits", "time_limit_s", "symbolic_time_limit_s", "horizon"}):
        errs.add(f"evaluation: unknown field '{key}'")
    static = formulation == "static"
    mode = e.get("mode", "algebraic" if static else None)
    if mode not in EVALUATION_MODES:
        errs.add(f"evaluation.mode: must be one of {', '.join(EVALUATION_MODES)}")
    elif static and mode != "algebraic":
        errs.add("evaluation.mode: a static task is evaluated algebraically")
    elif not static and mode == "algebraic":
        errs.add("evaluation.mode: a dynamic task is evaluated by one_step or simulation")
    init = _int(e.get("initialization", 0 if static else None), errs, "evaluation.initialization", 0)
    if init is not None:
        if static and init != 0:
            errs.add("evaluation.initialization: must be 0 for a static task")
        if not static and init < 1:
            errs.add("evaluation.initialization: a dynamic task needs at least 1 initial sample per trajectory")
        if dynamics is not None and dynamics.delays:
            need = max(d.lag for d in dynamics.delays) + 1
            if init < need:
                errs.add(f"evaluation.initialization: the declared delays need at least {need} initial samples")
    scoring = e.get("scoring", "all_samples" if static else "after_initialization")
    if scoring not in SCORING_RULES:
        errs.add(f"evaluation.scoring: must be one of {', '.join(SCORING_RULES)}")
    elif static and scoring != "all_samples":
        errs.add("evaluation.scoring: a static task scores all samples")
    elif not static and scoring != "after_initialization":
        errs.add("evaluation.scoring: a dynamic task scores the samples after the initialization samples")
    limits: list[FailureLimit] = []
    allowed = set(dynamics.states if dynamics else ()) | ({output} if output else set())
    for i, fl in enumerate(_as_list(e.get("failure_limits"), errs, "evaluation.failure_limits")):
        where = f"evaluation.failure_limits[{i}]"
        if not isinstance(fl, dict):
            errs.add(f"{where}: expected a mapping")
            continue
        var = fl.get("variable")
        if var not in allowed:
            errs.add(f"{where}: variable {var!r} is not a simulated state or the output")
            continue
        iv = _interval([fl.get("lower"), fl.get("upper")], errs, where)
        unit = _str(fl, "unit", errs, where)
        just = _str(fl, "justification", errs, where)
        if iv and unit and just:
            limits.append(FailureLimit(variable=str(var), lower=iv[0], upper=iv[1], unit=unit, justification=just))
    if len({fl.variable for fl in limits}) != len(limits):
        errs.add("evaluation.failure_limits: one entry per variable")
    tl = _num(e.get("time_limit_s"), errs, "evaluation.time_limit_s")
    if tl is not None and tl <= 0:
        errs.add("evaluation.time_limit_s: must be positive")
    stl = None
    if e.get("symbolic_time_limit_s") is not None:
        stl = _num(e.get("symbolic_time_limit_s"), errs, "evaluation.symbolic_time_limit_s")
        if stl is not None and stl <= 0:
            errs.add("evaluation.symbolic_time_limit_s: must be positive")
    horizon = None
    if e.get("horizon") is not None:
        horizon = _int(e.get("horizon"), errs, "evaluation.horizon", 1)
        if mode != "simulation":
            errs.add("evaluation.horizon: only for the evaluation mode simulation (the horizon of the simulations of the "
                     "training and validation data)")
    if None in (init, tl) or mode not in EVALUATION_MODES or scoring not in SCORING_RULES:
        return None
    return Evaluation(
        mode=mode,
        initialization=init,
        scoring=scoring,
        failure_limits=tuple(limits),
        time_limit_s=tl,
        symbolic_time_limit_s=stl,
        horizon=horizon,
    )


def _check_tables(
    tables: dict[str, Table], columns: list[Column], traj_col: str | None, evaluation: Evaluation | None, errs: _Errors
) -> None:
    """Finite training values inside the declared ranges; contiguous trajectories."""
    for split, t in tables.items():
        if not np.all(np.isfinite(t.values)):
            errs.add(f"data.{split}: contains non-finite values")
            continue
        blocks = [(0.0, slice(0, t.n_rows))]
        if traj_col is not None and traj_col in t.header:
            ids = t.column(traj_col)
            if not np.all(ids == np.round(ids)):
                errs.add(f"data.{split}: trajectory identifiers must be integers")
            try:
                blocks = trajectory_blocks(ids)
            except TableError as exc:
                errs.add(f"data.{split}: {exc}")
        if evaluation is not None:
            short = [int(b[0]) for b in blocks if (b[1].stop - b[1].start) <= evaluation.initialization]
            if short:
                errs.add(f"data.{split}: trajectories {short} have no sample after the initialization samples")
    train = tables["train"]
    for c in columns:
        if c.range is None or c.name not in train.header:
            continue
        v = train.column(c.name)
        lo, hi = float(np.min(v)), float(np.max(v))
        if lo < c.range[0] or hi > c.range[1]:
            errs.add(f"column {c.name!r}: training values [{lo:.6g}, {hi:.6g}] exceed the declared range {list(c.range)}")


def _load_domain(
    dom: Any, rtype: str, variables: tuple[str, ...], ranges: dict, errs: _Errors, where: str, limit_var: str | None = None
) -> dict[str, Any] | None:
    point_types = ("exact_value", "relation_at_points")
    if rtype in point_types:
        if not isinstance(dom, dict) or not isinstance(dom.get("points"), list) or not dom["points"]:
            errs.add(f"{where}.domain: a requirement of type {rtype} needs 'points', a non-empty list")
            return None
        pts = []
        for j, p in enumerate(dom["points"]):
            if not isinstance(p, dict) or set(p) != set(variables):
                errs.add(f"{where}.domain.points[{j}]: must assign a value to every variable {list(variables)}")
                return None
            vals = {k: _num(v, errs, f"{where}.domain.points[{j}].{k}") for k, v in p.items()}
            if None in vals.values():
                return None
            pts.append({k: vals[k] for k in variables})
        return {"points": pts}
    need = [v for v in variables if v != limit_var]
    if dom is None:
        missing = [v for v in need if v not in ranges]
        if missing:
            errs.add(f"{where}.domain: no box given and no declared range for {missing}")
            return None
        return {"box": {v: tuple(ranges[v]) for v in need}}
    if not isinstance(dom, dict) or not isinstance(dom.get("box"), dict):
        errs.add(f"{where}.domain: expected {{box: {{variable: [lower, upper]}}}}")
        return None
    box = {}
    for k, v in dom["box"].items():
        iv = _interval(v, errs, f"{where}.domain.box.{k}")
        if iv is None:
            return None
        box[str(k)] = iv
    extra = set(box) - set(variables)
    missing = set(need) - set(box)
    if extra or missing:
        errs.add(f"{where}.domain.box: must cover exactly the variables {need} (missing {sorted(missing)}, extra {sorted(extra)})")
        return None
    return {"box": {v: box[v] for v in variables if v in box}}


def _load_requirements(
    reqs: Any,
    keys: tuple[str, ...],
    output: str | None,
    args: tuple[str, ...],
    ranges: dict,
    const_names: list[str],
    functions: tuple[str, ...],
    added_lams: dict,
    formulation: str,
    errs: _Errors,
) -> list[Requirement]:
    """Formal requirements of the nine types, with target, variables, domain,
    tolerance, verification, exclusion rule and source."""
    out: list[Requirement] = []
    common = {"id", "type", "target", "variables", "domain", "tolerance", "verification", "exclude_on_violation", "exception", "source", "statement", "sampling"}
    specific = {
        "symmetry": {"transform", "factor"},
        "monotonicity": {"variable", "direction"},
        "parity": {"parity", "flip"},
        "exact_value": {"value"},
        "inequality": {"relation"},
        "curvature": {"variable", "sign"},
        "limit": {"variable", "approach", "value"},
        "equation": {"equals"},
        "relation_at_points": {"relation"},
    }
    targets = set(keys) | ({output} if output else set())
    for i, r in enumerate(_as_list(reqs, errs, "requirements")):
        where = f"requirements[{i}]"
        if not isinstance(r, dict):
            errs.add(f"{where}: expected a mapping")
            continue
        rid = _str(r, "id", errs, where)
        rtype = r.get("type")
        if rtype not in REQUIREMENT_TYPES:
            errs.add(f"{where}: type must be one of {', '.join(REQUIREMENT_TYPES)}, got {rtype!r}")
            continue
        where = f"requirement {rid or i} ({rtype})"
        for key in sorted(set(r) - common - specific[rtype]):
            errs.add(f"{where}: unknown field '{key}'")
        target = r.get("target", keys[0] if len(keys) == 1 else None)
        if target not in targets:
            errs.add(f"{where}: target {target!r} must be one of the expression keys {list(keys)} or the output")
            continue
        variables = _names(r.get("variables")) or args
        bad = [v for v in variables if v not in args]
        if bad:
            errs.add(f"{where}: variables {bad} are not arguments of the model expressions {list(args)}")
            continue
        names = list(args) + const_names
        params: dict[str, Any] = {}
        try:
            if rtype == "symmetry":
                tr = r.get("transform")
                if not isinstance(tr, dict) or not tr or set(tr) - set(variables):
                    raise ExpressionError("'transform' must map variables of the requirement to expressions")
                params["transform"] = {str(k): str(v) for k, v in tr.items()}
                for v in params["transform"].values():
                    parse_task_expression(v, names, functions, added=added_lams)
                factor = r.get("factor", 1)
                if factor not in (1, -1):
                    raise ExpressionError("'factor' must be 1 or -1")
                params["factor"] = factor
            elif rtype in ("monotonicity", "curvature", "limit"):
                var = r.get("variable")
                if var not in variables:
                    raise ExpressionError(f"'variable' {var!r} must be one of the requirement's variables")
                params["variable"] = var
                if rtype == "monotonicity":
                    if r.get("direction") not in ("increasing", "decreasing"):
                        raise ExpressionError("'direction' must be increasing or decreasing")
                    params["direction"] = r["direction"]
                elif rtype == "curvature":
                    if r.get("sign") not in ("convex", "concave"):
                        raise ExpressionError("'sign' must be convex or concave")
                    params["sign"] = r["sign"]
                else:
                    appr = r.get("approach")
                    if appr in ("oo", "-oo"):
                        params["approach"] = appr
                    else:
                        a = _num(appr, errs, f"{where}.approach")
                        if a is None:
                            continue
                        params["approach"] = a
                    val = _num(r.get("value"), errs, f"{where}.value")
                    if val is None:
                        continue
                    params["value"] = val
            elif rtype == "parity":
                if r.get("parity") not in ("even", "odd"):
                    raise ExpressionError("'parity' must be even or odd")
                params["parity"] = r["parity"]
                flip = _names(r.get("flip")) or variables
                if set(flip) - set(variables):
                    raise ExpressionError("'flip' must be a subset of the requirement's variables")
                params["flip"] = list(flip)
            elif rtype == "exact_value":
                val = _num(r.get("value"), errs, f"{where}.value")
                if val is None:
                    continue
                params["value"] = val
            elif rtype == "inequality":
                rel = r.get("relation")
                parse_task_expression(str(rel), names + [target], functions, added=added_lams, allow_relational=True)
                params["relation"] = str(rel).strip()
            elif rtype == "equation":
                eq = r.get("equals")
                parse_task_expression(str(eq), names, functions, added=added_lams)
                params["equals"] = str(eq).strip()
            elif rtype == "relation_at_points":
                rel = str(r.get("relation"))
                n_pts = len((r.get("domain") or {}).get("points") or [])
                placeholders = [f"at{j + 1}" for j in range(n_pts)]
                clash = [p for p in placeholders if p in names]
                if clash:
                    raise ExpressionError(f"placeholders {clash} collide with declared names")
                parse_task_expression(rel, placeholders + const_names, functions, added=added_lams, allow_relational=True)
                params["relation"] = rel.strip()
        except ExpressionError as exc:
            errs.add(f"{where}: {exc}")
            continue
        domain = _load_domain(r.get("domain"), rtype, variables, ranges, errs, where, params.get("variable") if rtype == "limit" else None)
        tol_raw = r.get("tolerance")
        tol = None
        if not isinstance(tol_raw, dict):
            errs.add(f"{where}: 'tolerance' must be a mapping with 'value' and 'unit'")
        else:
            tv = _num(tol_raw.get("value"), errs, f"{where}.tolerance.value")
            tu = _str(tol_raw, "unit", errs, f"{where}.tolerance")
            if tv is not None and tv < 0:
                errs.add(f"{where}.tolerance.value: must not be negative")
            elif tv is not None and tu is not None:
                tol = Tolerance(value=tv, unit=tu)
        verification = r.get("verification", "symbolic_then_sampling")
        if verification not in VERIFICATIONS:
            errs.add(f"{where}: verification must be one of {', '.join(VERIFICATIONS)}")
        excl = r.get("exclude_on_violation", True)
        if not isinstance(excl, bool):
            errs.add(f"{where}: exclude_on_violation must be true or false")
            excl = True
        exception = None
        if excl is False:
            if r.get("exception") is None:
                errs.add(f"{where}: exclude_on_violation false requires 'exception', the source of the explicit user instruction")
            else:
                exception = _source(r.get("exception"), errs, f"{where}.exception")
        elif r.get("exception") is not None:
            errs.add(f"{where}: 'exception' is only allowed with exclude_on_violation false")
        src = _source(r.get("source"), errs, where)
        sampling = r.get("sampling")
        if sampling is not None:
            if not isinstance(sampling, dict) or set(sampling) - {"samples", "seed"}:
                errs.add(f"{where}: 'sampling' may contain only 'samples' and 'seed'")
            else:
                params["sampling"] = {
                    k: _int(v, errs, f"{where}.sampling.{k}", 1 if k == "samples" else 0) for k, v in sampling.items()
                }
        if verification in ("sampling", "symbolic_then_sampling") and "sampling" not in params:
            errs.add(f"{where}: verification by sampling needs 'sampling: {{samples, seed}}' (the sample count and seed are recorded)")
        elif "sampling" in params and set(params["sampling"]) != {"samples", "seed"}:
            errs.add(f"{where}: 'sampling' needs both 'samples' and 'seed'")
        statement = r.get("statement")
        if None in (rid, domain, tol, src) or verification not in VERIFICATIONS:
            continue
        out.append(
            Requirement(
                id=rid,
                type=rtype,
                target=str(target),
                variables=tuple(variables),
                domain=domain,
                tolerance=tol,
                verification=verification,
                exclude_on_violation=excl,
                source=src,
                params=params,
                statement=" ".join(str(statement).split()) if statement else None,
                exception=exception,
            )
        )
    return out


def _load_sealed(test: Any, reference: Any, args: tuple[str, ...], ranges: dict, errs: _Errors) -> SealedPart:
    """Declared sealed test trajectories and reference (lexical checks only)."""
    entries: list[SealedTestEntry] = []
    files: list[str] = []
    for i, t in enumerate(_as_list(test, errs, "test")):
        where = f"test[{i}]"
        if not isinstance(t, dict):
            errs.add(f"{where}: expected a mapping with 'file', 'trajectory' and 'source_name'")
            continue
        for key in sorted(set(t) - {"file", "trajectory", "source_name"}):
            errs.add(f"{where}: unknown field '{key}'")
        err = check_relative_path(t.get("file"))
        if err:
            errs.add(f"{where}.file: {err}")
            continue
        traj = t.get("trajectory")
        if not isinstance(traj, (str, int)) or isinstance(traj, bool):
            errs.add(f"{where}: 'trajectory' identifier is required")
            continue
        sn = t.get("source_name")
        files.append(t["file"])
        entries.append(SealedTestEntry(trajectory=str(traj), source_name=str(sn) if sn is not None else None, _file=t["file"]))
    if len({e.trajectory for e in entries}) != len(entries):
        errs.add("test: trajectory identifiers must be unique")
    if len(set(files)) != len(files):
        errs.add("test: each test file is listed once")
    ref = None
    if reference is not None:
        if not isinstance(reference, dict):
            errs.add("reference: expected a mapping with 'file' and 'domain'")
        else:
            for key in sorted(set(reference) - {"file", "domain"}):
                errs.add(f"reference: unknown field '{key}'")
            err = check_relative_path(reference.get("file"))
            if err:
                errs.add(f"reference.file: {err}")
            else:
                dom = _load_domain(reference.get("domain"), "box", args, ranges, errs, "reference")
                if dom is not None:
                    ref = SealedReferenceEntry(domain=dom, _file=reference["file"])
    return SealedPart(test=tuple(entries), reference=ref)
