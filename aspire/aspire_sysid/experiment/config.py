"""Experiment configuration ``experiments/<id>/experiment.yaml``: loader and validation.

A **run** is one session for a specified task and tool configuration. For repeated runs, the
report states what varies, how many runs were attempted, how many produced a pool, and how many
produced an eligible model.

An **experiment** is one task, run one or more times with identical settings: one pinned model
identifier, one harness revision, one round budget. The runs differ only in the
run index, that is, in the stochastic responses of the language model (the requests set no seed).
Two tasks are two experiments; a variant of a task without names and description is a task of its
own with its own experiment. The file ``experiment.yaml`` (schema version 2) has the fields

====================  ==========================================================================
``schema_version``    ``2``
``id``                the experiment identifier; equal to the name of the experiment folder
``model``             the pinned model identifier (validated with
                      :func:`aspire_sysid.agent.providers.check_pinned_model_id` and required to
                      have a dated price in ``aspire/configs/prices.yaml``)
``task``              the task identifier (folder ``<tasks_root>/<task>/``)
``runs``              number of runs, at least 1
``concurrency``       number of runs executed at the same time (separate processes), at least 1
``budget``            ``null`` (default): the task's round budget (60 turns,
                      3600 s, 10 USD by default); or ``{turns, seconds, usd}``, an override that
                      replaces the round budget of the task and is recorded in every run record
``seeds``             optional text: the seed policy; the default states that the language
                      model receives no seed and that requirement sampling and the reference
                      comparison use the seeds of the task
``exports``           ``{python: true, matlab: true, octave: auto}``: the exports of every run
; ``matlab: false`` defers the Matlab export; ``octave``:
                      ``true``, ``false`` or ``auto`` (run the M-files in GNU Octave when
                      ``octave-cli`` is installed)
``plots``             ``true`` (default): the evaluation reports include plots
``workspace_root``    optional: the folder under which the working directories are created;
                      default ``<system temp>/aspire-runs``; it must lie outside every git
                      repository (see :mod:`aspire_sysid.experiment.workspace`)
``agent_python``      optional: the interpreter of the agent's shell, normally a separate
                      virtual environment without the harness package (``aspire experiment
                      agent-env``); default: the harness's own interpreter; a relative
                      path is relative to the experiment folder; symbolic links are not
                      resolved (the interpreter of a virtual environment is often a link)
``keep_workspaces``   ``true`` (default): keep the working directory under the workspace root
                      after it has been copied into the run folder
``tasks_root``        optional: the task store, relative to the experiment folder; default
                      ``../../tasks``
``notes``             optional free text
====================  ==========================================================================

A run is identified by ``r<NN>``, where ``NN`` is the run index from 01, and recorded in
``experiments/<id>/runs/r<NN>/``.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..task.schema import Limits

__all__ = [
    "EXPERIMENT_FILE",
    "EXPERIMENT_SCHEMA_VERSION",
    "DEFAULT_SEED_POLICY",
    "ExperimentError",
    "ExportSettings",
    "Experiment",
    "RunSpec",
    "load_experiment",
    "experiment_from_mapping",
    "run_id",
    "parse_run_id",
    "default_workspace_root",
]

EXPERIMENT_FILE = "experiment.yaml"
EXPERIMENT_SCHEMA_VERSION = 2

DEFAULT_SEED_POLICY = (
    "The language-model requests set no seed, so the responses are not reproducible; the runs of an "
    "experiment differ only in these responses. Requirement sampling and the reference comparison use the "
    "seeds declared by the task and the harness, recorded in every run record."
)
"""Seed policy of an experiment without a ``seeds`` field (random seeds are recorded)."""

_FIELDS = {
    "schema_version", "id", "model", "task", "runs", "concurrency", "budget", "seeds", "exports", "plots",
    "workspace_root", "agent_python", "keep_workspaces", "tasks_root", "notes",
}

_REMOVED_FIELDS = {
    "tasks": "an experiment has one task; name it in the field task (two tasks are two experiments)",
    "runs_per_cell": "the number of runs is the field runs",
    "kind": "experiments have no kind",
    "pool_cap": "the pool limit is declared by the task",
    "exclude_cells": "an experiment has one task and no cells",
    "configurations": "there is one tool configuration",
}
"""Fields that the file does not accept, with what replaces them (named in the error message)."""


class ExperimentError(ValueError):
    """The experiment configuration is missing or invalid. """


@dataclass(frozen=True)
class ExportSettings:
    """Exports of every run."""

    python: bool = True
    matlab: bool = True
    octave: bool | None = None  # None: automatic (run in Octave when octave-cli is installed)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the record."""
        return {"python": self.python, "matlab": self.matlab, "octave": "auto" if self.octave is None else self.octave}


@dataclass(frozen=True)
class RunSpec:
    """One run of an experiment: the task and the run index."""

    task: str
    index: int

    @property
    def run_id(self) -> str:
        """``r<NN>``."""
        return run_id(self.index)


def run_id(index: int) -> str:
    """The identifier of run ``index`` of an experiment: ``r<NN>``. """
    return f"r{int(index):02d}"


def parse_run_id(text: str) -> int | None:
    """The run index of a run identifier ``r<NN>``, or ``None``. """
    if len(text) < 3 or not text.startswith("r") or not text[1:].isdigit() or int(text[1:]) < 1:
        return None
    return int(text[1:])


def default_workspace_root() -> Path:
    """``<system temp>/aspire-runs``: the default root of the working directories of autonomous
    runs (interactive sessions use ``<system temp>/aspire-sessions``). """
    return Path(tempfile.gettempdir()) / "aspire-runs"


@dataclass(frozen=True)
class Experiment:
    """A loaded experiment configuration (module docstring). """

    dir: Path
    id: str
    model: str
    vendor: str
    task: str
    runs: int
    concurrency: int
    budget: Limits | None
    seeds: str
    exports: ExportSettings
    plots: bool
    workspace_root: Path
    agent_python: str | None
    keep_workspaces: bool
    tasks_root: Path
    notes: str
    config_sha256: str
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @property
    def runs_dir(self) -> Path:
        """``experiments/<id>/runs``: the run folders."""
        return self.dir / "runs"

    def grid(self) -> list[RunSpec]:
        """Every run of the experiment, ordered by run index."""
        return [RunSpec(self.task, i) for i in range(1, self.runs + 1)]

    @property
    def task_dir(self) -> Path:
        """The folder of the experiment's task in the task store."""
        return self.tasks_root / self.task

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the run records and the aggregation."""
        return {
            "id": self.id,
            "folder": str(self.dir),
            "model": self.model,
            "vendor": self.vendor,
            "task": self.task,
            "runs": self.runs,
            "concurrency": self.concurrency,
            "budget_override": None if self.budget is None else {"turns": self.budget.turns, "seconds": self.budget.seconds, "usd": self.budget.usd},
            "seeds": self.seeds,
            "exports": self.exports.to_dict(),
            "plots": self.plots,
            "workspace_root": str(self.workspace_root),
            "agent_python": self.agent_python,
            "keep_workspaces": self.keep_workspaces,
            "tasks_root": str(self.tasks_root),
            "notes": self.notes,
            "config_sha256": self.config_sha256,
        }


def _bool(v: Any, name: str, default: bool) -> bool:
    if v is None:
        return default
    if not isinstance(v, bool):
        raise ExperimentError(f"{name} must be true or false, not {v!r}")
    return v


def _int(v: Any, name: str, minimum: int) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
        raise ExperimentError(f"{name} must be an integer of at least {minimum}, not {v!r}")
    return v


def _path(value: str, base: Path) -> Path:
    p = Path(os.path.expandvars(os.path.expanduser(value)))
    return (p if p.is_absolute() else base / p).resolve()


def _interpreter_path(value: str, base: Path) -> Path:
    """The absolute path of an interpreter, without resolving symbolic links: the interpreter of a
    virtual environment is often a link to the base interpreter, and only the unresolved path runs
    with the environment's own packages."""
    p = Path(os.path.expandvars(os.path.expanduser(value)))
    return Path(os.path.abspath(p if p.is_absolute() else base / p))


def experiment_from_mapping(
    data: Any,
    experiment_dir: str | Path,
    *,
    tasks_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
    agent_python: str | None = None,
    config_sha256: str = "",
    check_task: bool = True,
) -> Experiment:
    """Validate an experiment mapping (module docstring). 

    ``tasks_root``, ``workspace_root`` and ``agent_python`` override the fields of the file (command
    line, tests). With ``check_task`` the task folder must exist and load. Raises
    :class:`ExperimentError` listing the problem.
    """
    from ..agent.prices import UnknownModelPriceError, default_price_table
    from ..agent.providers import ModelIdError, check_pinned_model_id

    d = Path(experiment_dir).resolve()
    if not isinstance(data, Mapping):
        raise ExperimentError(f"{d / EXPERIMENT_FILE}: the file must contain a mapping")
    removed = [f"{k}: {why}" for k, why in _REMOVED_FIELDS.items() if k in data]
    if removed:
        raise ExperimentError("field(s) of an earlier form of experiment.yaml: " + "; ".join(removed)
                              + ". An experiment is one task with one or more runs (fields task and runs).")
    unknown = sorted(set(data) - _FIELDS)
    if unknown:
        raise ExperimentError(f"unknown field(s) {unknown}; permitted: {sorted(_FIELDS)}")
    if data.get("schema_version") != EXPERIMENT_SCHEMA_VERSION:
        raise ExperimentError(f"schema_version must be {EXPERIMENT_SCHEMA_VERSION}")
    eid = data.get("id")
    if not isinstance(eid, str) or eid != d.name:
        raise ExperimentError(f"id must equal the name of the experiment folder ({d.name!r}), not {eid!r}")
    model = data.get("model")
    if not isinstance(model, str):
        raise ExperimentError("model must be a pinned model identifier")
    try:
        vendor = check_pinned_model_id(model)
        default_price_table().price(model)
    except ModelIdError as exc:
        raise ExperimentError(f"model: {exc}") from exc
    except UnknownModelPriceError as exc:
        raise ExperimentError(f"model {model!r} has no verified price in aspire/configs/prices.yaml ({exc})") from exc
    task = data.get("task")
    if not isinstance(task, str) or not task.strip() or "/" in task or chr(92) in task:
        raise ExperimentError(f"task must be one task identifier (the name of a folder of the task store), not {task!r}")
    runs = _int(data.get("runs"), "runs", 1)
    conc = _int(data.get("concurrency", 1), "concurrency", 1)
    budget = data.get("budget")
    limits: Limits | None = None
    if budget is not None:
        if not isinstance(budget, Mapping) or set(budget) != {"turns", "seconds", "usd"}:
            raise ExperimentError("budget must be null or a mapping with exactly turns, seconds and usd")
        try:
            limits = Limits(turns=_int(budget["turns"], "budget.turns", 1), seconds=float(budget["seconds"]), usd=float(budget["usd"]))
        except (TypeError, ValueError) as exc:
            raise ExperimentError(f"budget: {exc}") from exc
        if not (limits.seconds > 0 and limits.usd > 0):
            raise ExperimentError("budget.seconds and budget.usd must be positive")
    seeds = data.get("seeds") or DEFAULT_SEED_POLICY
    if not isinstance(seeds, str):
        raise ExperimentError("seeds must be a text stating the seed policy")
    ex = data.get("exports") or {}
    if not isinstance(ex, Mapping) or set(ex) - {"python", "matlab", "octave"}:
        raise ExperimentError("exports must be a mapping with the fields python, matlab and octave")
    oct_v = ex.get("octave", "auto")
    if oct_v not in (True, False, "auto"):
        raise ExperimentError("exports.octave must be true, false or auto")
    exports = ExportSettings(
        python=_bool(ex.get("python"), "exports.python", True),
        matlab=_bool(ex.get("matlab"), "exports.matlab", True),
        octave=None if oct_v == "auto" else bool(oct_v),
    )
    plots = _bool(data.get("plots"), "plots", True)
    keep = _bool(data.get("keep_workspaces"), "keep_workspaces", True)
    troot = Path(tasks_root).resolve() if tasks_root is not None else _path(str(data.get("tasks_root") or "../../tasks"), d)
    if workspace_root is not None:
        wroot = Path(workspace_root).resolve()
    elif data.get("workspace_root"):
        wroot = _path(str(data["workspace_root"]), d)
    else:
        wroot = default_workspace_root().resolve()
    apy = agent_python if agent_python is not None else data.get("agent_python")
    if apy is not None and (not isinstance(apy, str) or not apy.strip()):
        raise ExperimentError("agent_python must be the path of an interpreter")
    if apy is not None:
        # a relative path given as an argument is relative to the current folder, one in the file to the experiment folder
        apy = str(_interpreter_path(apy, Path.cwd() if agent_python is not None else d))
    notes = data.get("notes") or ""
    if not isinstance(notes, str):
        raise ExperimentError("notes must be a text")
    exp = Experiment(
        dir=d, id=eid, model=model, vendor=vendor, task=task, runs=runs, concurrency=conc, budget=limits, seeds=seeds,
        exports=exports, plots=plots, workspace_root=wroot, agent_python=apy, keep_workspaces=keep, tasks_root=troot,
        notes=notes, config_sha256=config_sha256, raw=dict(data),
    )
    if check_task:
        _check_task(exp)
    return exp


def _check_task(exp: Experiment) -> None:
    from ..task import TaskError, load_task

    try:
        task = load_task(exp.task_dir)
    except TaskError as exc:
        raise ExperimentError(f"task {exp.task} ({exp.task_dir}): {exc}") from exc
    if task.id != exp.task:
        raise ExperimentError(f"task folder {exp.task_dir} declares the identifier {task.id!r}")


def load_experiment(
    experiment_dir: str | Path,
    *,
    tasks_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
    agent_python: str | None = None,
    check_task: bool = True,
) -> Experiment:
    """Read and validate ``<experiment_dir>/experiment.yaml`` (module docstring). """
    d = Path(experiment_dir)
    p = d / EXPERIMENT_FILE
    try:
        blob = p.read_bytes()
        data = yaml.safe_load(blob.decode("utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ExperimentError(f"{p}: cannot be read ({exc})") from exc
    return experiment_from_mapping(
        data, d, tasks_root=tasks_root, workspace_root=workspace_root, agent_python=agent_python,
        config_sha256=hashlib.sha256(blob).hexdigest(), check_task=check_task,
    )
