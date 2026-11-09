"""Harness side of the model files: checking files, configuration, example and in-process checks.

The working directory receives the model file format with a complete example and
the checking script ``check_submission.py``; the harness repeats the file and expression checks
afterwards. A complete example of the model file
format is provided before work starts, and one check module serves both sides.

The checks themselves are in :mod:`aspire_sysid.model.checks`, which the working directory
receives byte for byte as ``check_submission.py``. This module builds the check configuration
from the public view of a task, writes the two checking files, runs the checks in-process with
a configuration derived from the task (never from the copy in the working directory, which the
agent can edit) and the training data of the task store, and builds the example model files that
the brief shows.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ..task.provision import WORKSPACE_TRAIN, ProvisionedFile
from ..task.public import public_view
from ..task.schema import TaskSpec
from . import checks
from .checks import (
    CONFIG_FILE,
    MODELS_DIR,
    POOL_FILE,
    RULES,
    Candidate,
    CheckConfig,
    CheckReport,
    Delay,
    Issue,
    Pool,
)

CHECK_SCRIPT = "check_submission.py"
"""Name of the checking script in the working directory."""

CHECKS_MODULE_PATH: Path = Path(checks.__file__).resolve()
"""The source file of the check module; the working directory receives it byte for byte."""


class CandidateCheckError(ValueError):
    """A model file did not pass the file and expression checks."""

    def __init__(self, label: str, issues: list[Issue]):
        self.label = label
        self.issues = list(issues)
        super().__init__(f"candidate {label} failed the checks:\n" + "\n".join(f"  {i.text()}" for i in issues))


def rule_table() -> list[tuple[str, str]]:
    """The file and expression checks as ``(rule identifier, text)`` rows.

    The checking script prints these identifiers and texts with every violation.
    """
    return list(RULES.items())


def check_config_from_task(
    task: TaskSpec, *, pool_version: int = 1, previous_labels: Iterable[str] = ()
) -> CheckConfig:
    """The check configuration of ``task``, built from its public view only.

    Every value comes from :func:`aspire_sysid.task.public_view`, so the configuration file
    contains nothing that the brief does not also show. ``pool_version`` and ``previous_labels``
    describe the pool version expected in this round and the labels of the previous version
    (interactive operation); in autonomous operation they are 1 and empty.
    """
    view = public_view(task)
    dyn = view.get("dynamics") or {}
    return CheckConfig(
        task_id=view["id"],
        formulation=view["formulation"],
        columns={c["name"]: tuple(c["roles"]) for c in view["columns"]},
        arguments=tuple(view["arguments"]),
        expression_keys=tuple(view["expression_keys"]),
        delays=tuple(Delay(d["name"], d["variable"], int(d["lag"])) for d in dyn.get("delays", [])),
        constants={c["name"]: float(c["value"]) for c in view["constants"]},
        functions=tuple(view["functions"]),
        added_functions=tuple((a["name"], tuple(a["arguments"]), a["definition"]) for a in view["added_functions"]),
        question_ids=tuple(q["id"] for q in view["discussion_questions"]),
        pool_cap=int(view["pool_cap"]),
        trajectory_column=view["data"]["trajectory_column"],
        train_file=view["data"]["train"]["file"],
        pool_version=int(pool_version),
        previous_labels=tuple(previous_labels),
    )


def _write(ws: Path, name: str, blob: bytes, overwrite: bool) -> ProvisionedFile:
    dst = ws / name
    if dst.exists() and not overwrite:
        raise FileExistsError(f"{name} already exists in the working directory")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(blob)
    return ProvisionedFile(name=name, sha256=hashlib.sha256(blob).hexdigest(), bytes=len(blob))


def config_json(config: CheckConfig) -> str:
    """The text of ``check_config.json``: indented JSON with a final newline."""
    return json.dumps(config.to_dict(), indent=2, ensure_ascii=False) + "\n"


def write_check_files(
    task: TaskSpec,
    workspace_dir: str | Path,
    *,
    pool_version: int = 1,
    previous_labels: Iterable[str] = (),
    overwrite: bool = False,
) -> list[ProvisionedFile]:
    """Write ``check_submission.py`` and ``check_config.json`` into the working directory.

 The script is a byte copy of :mod:`aspire_sysid.model.checks`;
    the configuration is :func:`check_config_from_task`. Returns the written files with their
    SHA-256 digests for the record. An existing file is replaced only with
    ``overwrite`` (a new round with a new pool version).
    """
    ws = Path(workspace_dir)
    ws.mkdir(parents=True, exist_ok=True)
    cfg = check_config_from_task(task, pool_version=pool_version, previous_labels=previous_labels)
    return [
        _write(ws, CHECK_SCRIPT, CHECKS_MODULE_PATH.read_bytes(), overwrite),
        _write(ws, CONFIG_FILE, config_json(cfg).encode("utf-8"), overwrite),
    ]


def check_workspace(
    workspace_dir: str | Path,
    task: TaskSpec | None = None,
    *,
    pool_version: int = 1,
    previous_labels: Iterable[str] = (),
) -> CheckReport:
    """Run the file and expression checks on a working directory.

    With ``task`` (the harness's use), the configuration is built from the task and the training
    data are read from the task store, so that edits of ``check_config.json`` or
    ``data/train.csv`` in the working directory cannot change the harness's checks. Without
    ``task``, the directory's own ``check_config.json`` and training data are used, exactly as by
    ``check_submission.py``.
    """
    ws = Path(workspace_dir)
    if task is None:
        return checks.check_directory(ws)
    cfg = check_config_from_task(task, pool_version=pool_version, previous_labels=previous_labels)
    return checks.check_directory(ws, cfg, train_path=task.data.train_path)


def load_candidate(path: str | Path, task: TaskSpec, *, pool_version: int = 1, previous_labels: Iterable[str] = ()) -> Candidate:
    """Read one model file and return the checked :class:`Candidate`.

    Raises :class:`CandidateCheckError` with the issues when the file fails a check.
    """
    cfg = check_config_from_task(task, pool_version=pool_version, previous_labels=previous_labels)
    train = checks.read_training_data(task.data.train_path, cfg.trajectory_column, cfg.train_file)
    res = checks.check_candidate_file(Path(path), cfg, train)
    if not res.passed:
        raise CandidateCheckError(res.label, res.issues)
    return res.candidate


def load_pool(path: str | Path, task: TaskSpec, *, pool_version: int = 1) -> Pool:
    """Read the pool file and return the checked :class:`Pool`.

    Raises :class:`CandidateCheckError` (label ``pool``) with the issues when the file is invalid.
    """
    cfg = check_config_from_task(task, pool_version=pool_version)
    p = Path(path)
    try:
        data = checks.read_json(p)
    except (ValueError, UnicodeDecodeError) as exc:
        raise CandidateCheckError("pool", [Issue("F1", p.name, f"not valid JSON: {exc}")]) from exc
    pool, issues, _ = checks.check_pool_data(data, cfg, f"{MODELS_DIR}/{p.name}")
    if pool is None:
        raise CandidateCheckError("pool", issues)
    return pool


# ---------------------------------------------------------------------------------------------
# Example model files
# ---------------------------------------------------------------------------------------------

EXAMPLE_LABEL = "M01"
"""Label of the candidate of the example pool."""


def _free_name(base: str, taken: set[str]) -> str:
    name = base
    while name in taken:
        name += "x"
    taken.add(name)
    return name


def example_model_data(task: TaskSpec) -> tuple[dict[str, Any], dict[str, Any]]:
    """A complete candidate and pool file for ``task`` as plain data.

    Used by the dry run's scripted agent and by tests; it is not shown to the agent, whose
    ``FORMAT.md`` carries one general example (:mod:`aspire_sysid.brief.reference`). The
    candidate has one expression per required key, one fitted, one fixed and one tied parameter,
    the estimation record, the four discussion sections and an answer to every discussion
    question. Its structure and values illustrate the format only. It passes the checks of
    ``task``.

    Where the task states a formal requirement of type ``equation`` on an expression key (for
    example the kinematic identity ``dtheta = omega``), the candidate uses the required expression
    for that key, so that it does not violate a stated requirement. Because the candidate is not a
    proposed model, its pool file recommends no candidate (``"recommended": null``).
    """
    cfg = check_config_from_task(task)
    args = list(cfg.arguments)
    taken = set(cfg.columns) | set(cfg.arguments) | set(cfg.constants) | set(cfg.expression_keys)
    taken |= {d.name for d in cfg.delays} | {a[0] for a in cfg.added_functions}
    if cfg.trajectory_column:
        taken.add(cfg.trajectory_column)
    a, b, n = _free_name("a1", taken), _free_name("b1", taken), _free_name("n0", taken)
    first, last = args[0], args[-1]
    generic = f"{a}*{first} + {b}*{last}/{n}"
    fixed_by_task: dict[str, str] = {}
    for r in task.requirements:
        if r.type == "equation" and r.target in cfg.expression_keys and r.target not in fixed_by_task:
            fixed_by_task[r.target] = str(r.params["equals"])
    if len(fixed_by_task) == len(cfg.expression_keys):
        fixed_by_task = {}  # the parameters must appear in some expression (rule E3)
    expressions = {k: fixed_by_task.get(k, generic) for k in cfg.expression_keys}
    note = ""
    if fixed_by_task:
        note = " " + "; ".join(f"{k} = {v} is the expression required by the task, without parameters" for k, v in fixed_by_task.items()) + "."
    candidate: dict[str, Any] = {
        "expressions": expressions,
        "parameters": [
            {"name": a, "value": 0.5, "unit": "-", "type": "fitted", "description": f"coefficient of {first}; the value 0.5 is illustrative"},
            {"name": n, "value": 2.0, "unit": "-", "type": "fixed", "description": f"normalisation of the {last} term, chosen by the modeller; illustrative"},
            {"name": b, "value": 1.0, "unit": "-", "type": "tied", "equation": f"2*{a}", "description": f"coefficient of {last}/{n}, tied to {a} by assumption; illustrative"},
        ],
        "estimation": {
            "criterion": "sum of squared one-step errors of every expression, over all training samples",
            "data": f"{cfg.train_file}, all rows",
            "method": "ordinary least squares; no starting values, no seed",
            "script": f"fit_{EXAMPLE_LABEL}.py",
        },
        "discussion": {
            "family": "Linear regression in the arguments; this candidate illustrates the file format and is not a proposed model.",
            "interpretation": f"The term {a}*{first} is proportional to {first}; the term {b}*{last}/{n} is proportional to {last}.",
            "origin": "Chosen to show one fitted, one fixed and one tied parameter." + note,
            "limitations": "The candidate is not a model of the system.",
        },
    }
    if cfg.question_ids:
        candidate["answers"] = {q: f"Answer to question {q}." for q in cfg.question_ids}
    pool: dict[str, Any] = {
        "order": [EXAMPLE_LABEL],
        "recommended": None,
        "reason": f"No candidate is recommended: {EXAMPLE_LABEL} illustrates the file format and is not a proposed model.",
    }
    return candidate, pool


def example_model_files(task: TaskSpec) -> dict[str, str]:
    """The files of :func:`example_model_data` as ``{relative path: JSON text}``.

    Keys are ``models/M01.json`` and ``models/pool.json``.
    """
    candidate, pool = example_model_data(task)
    return {
        f"{MODELS_DIR}/{EXAMPLE_LABEL}.json": json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
        f"{MODELS_DIR}/{POOL_FILE}": json.dumps(pool, indent=2, ensure_ascii=False) + "\n",
    }


__all__ = [
    "CHECK_SCRIPT",
    "CHECKS_MODULE_PATH",
    "CandidateCheckError",
    "EXAMPLE_LABEL",
    "WORKSPACE_TRAIN",
    "check_config_from_task",
    "check_workspace",
    "config_json",
    "example_model_data",
    "example_model_files",
    "load_candidate",
    "load_pool",
    "rule_table",
    "write_check_files",
]
