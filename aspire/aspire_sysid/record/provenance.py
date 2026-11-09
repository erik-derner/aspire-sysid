"""Dataset provenance record of a run.

For every dataset, the run record preserves its source and version, trajectory identifiers,
sampling period, sample counts, operating conditions, noise information, preprocessing and
assignment to training, validation or test use. It records how that assignment prevents
evaluation data from influencing fitting or selection, including filtering and delayed-variable
construction across dataset boundaries. The agent receives only the authorized part of this
information.

:func:`dataset_provenance` returns the record **for the user only**: one entry per dataset (the
training file, the validation file and every sealed test trajectory) with the fields of
:data:`DATASET_FIELDS`, and the statement of separation (:data:`SEPARATION_FIELDS`). It contains
the recording names (``source_name``) and the digests of the sealed files,
and is therefore never written into a working directory or sent to the agent.

:func:`authorized_provenance` returns the **authorized part**: exactly the dataset facts of the
public view of the task (:func:`aspire_sysid.task.public_view`), which the brief states:
neutral file names, sample and trajectory counts, trajectory lengths, the trajectory column, the
sampling period, noise and preprocessing.

Sources of the fields: the task specification (``task.yaml``) and the files of the task folder;
the sealed facts come from :func:`aspire_sysid.evaluate.sealed.sealed_dataset_records`, the only
module that opens the sealed files. Information that the task does not state is
recorded as :data:`NOT_STATED`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..evaluate.sealed import sealed_dataset_records
from ..task.provision import WORKSPACE_TRAIN, WORKSPACE_VAL
from ..task.public import public_view
from ..task.schema import TaskSpec
from ..task.table import read_table, trajectory_blocks

__all__ = [
    "PROVENANCE_FORMAT_VERSION",
    "NOT_STATED",
    "DATASET_FIELDS",
    "SEPARATION_FIELDS",
    "dataset_provenance",
    "authorized_provenance",
    "file_sha256",
]

PROVENANCE_FORMAT_VERSION = 1
"""Version of the dataset provenance record."""

NOT_STATED = "not stated"
"""Entry of a field that the task specification does not state."""

DATASET_FIELDS: tuple[str, ...] = (
    "dataset",
    "assignment",
    "agent_visible",
    "source",
    "version",
    "trajectories",
    "sampling_period_s",
    "samples",
    "operating_conditions",
    "noise",
    "preprocessing",
)
"""Fields of every dataset entry."""

SEPARATION_FIELDS: tuple[str, ...] = (
    "sealing",
    "per_trajectory_evaluation",
    "delayed_variables",
    "filtering",
    "selection",
    "use_of_test_data",
)
"""Fields of the statement of how the assignment prevents evaluation data from influencing
fitting or selection."""


def file_sha256(path: str | Path) -> str:
    """SHA-256 digest of the bytes of a file (data version)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _names(task: TaskSpec, group: str) -> list[str]:
    return list(task.data.source_names.get(group, ()))


def _rel(task: TaskSpec, path: Path) -> str:
    try:
        return path.resolve().relative_to(task.task_dir.resolve()).as_posix()
    except ValueError:
        return str(path)


def _operating_conditions(task: TaskSpec) -> dict[str, Any]:
    return {
        "statement": NOT_STATED + " per dataset; the task description states the conditions of the recordings as a whole",
        "task_description": " ".join(task.description.split()) if task.description else None,
        "source": "task.yaml, field description",
    }


def _visible_entry(task: TaskSpec, group: str, path: Path, workspace_name: str, assignment: str) -> dict[str, Any]:
    table = read_table(path)
    tc = task.data.trajectory_column
    if task.formulation != "static" and tc and tc in table.header:
        blocks = trajectory_blocks(table.column(tc))
        trajs = [{"id": str(int(i)) if float(i).is_integer() else repr(float(i)), "samples": sl.stop - sl.start} for i, sl in blocks]
    elif tc and tc in table.header:
        blocks = trajectory_blocks(table.column(tc))
        trajs = [{"id": group, "samples": table.n_rows, "note": f"a static task evaluates the whole file as one dataset; the file marks {len(blocks)} blocks in {tc}"}]
    else:
        trajs = [{"id": group, "samples": table.n_rows}]
    return {
        "dataset": group,
        "assignment": assignment,
        "agent_visible": True,
        "source": {
            "recording_names": _names(task, group) or NOT_STATED,
            "task_file": _rel(task, path),
            "working_directory_file": workspace_name,
            "provenance_document": "provenance.md of the task folder",
        },
        "version": {"sha256": file_sha256(path), "bytes": path.stat().st_size},
        "trajectories": trajs,
        "trajectory_column": tc,
        "sampling_period_s": task.dynamics.sampling_period if task.dynamics is not None else None,
        "samples": table.n_rows,
        "operating_conditions": _operating_conditions(task),
        "noise": task.data.noise or NOT_STATED,
        "preprocessing": task.data.preprocessing or NOT_STATED,
    }


def _separation(task: TaskSpec, n_sealed: int) -> dict[str, str]:
    delays = task.dynamics.delays if task.dynamics is not None else ()
    if delays:
        delayed = (
            "the delayed variables "
            + ", ".join(f"{d.name}[k] = {d.variable}[k - {d.lag}]" for d in delays)
            + " are built inside each trajectory only; the first samples of a trajectory without the required history are not "
            "evaluated, and no value is taken across a trajectory or dataset boundary"
        )
    else:
        delayed = "not applicable: the task declares no delayed variables"
    return {
        "sealing": (
            f"the {n_sealed} sealed test trajectory file(s) are held in the task store and opened only by the evaluation module "
            "of the harness; they are never copied into the working directory, and the brief, the execution messages and the "
            "results permitted to the agent contain no test value, test trajectory, test-derived plot or failure location on "
            "test data; the leak scanner searches the working directory and the transcript for them"
        ),
        "per_trajectory_evaluation": (
            "every trajectory and static dataset is evaluated on its own; a simulation starts once per trajectory and the end of "
            "one trajectory is never joined to the beginning of another"
        ),
        "delayed_variables": delayed,
        "filtering": (
            "the harness applies no filtering or other preprocessing; the preprocessing of the task authors is stated per "
            "dataset, and any filtering by the agent is applied by its own scripts to the data in its working directory, which "
            "contain no test data"
        ),
        "selection": (
            "the agent fits and recommends from the training and validation data only; its recommendation is recorded in the "
            "pool file before any test result exists; the ranking on test data is computed afterwards by the harness and is "
            "labeled oracle-based selection on test data"
        ),
        "use_of_test_data": (
            "the authors used the test data during the development of the framework and of the tasks; a result of a round "
            "after the user has seen test results is labeled test-informed"
        ),
    }


def dataset_provenance(task: TaskSpec) -> dict[str, Any]:
    """The dataset provenance record of ``task``, for the user only (module docstring).

    Returns plain data: ``format_version``, ``task_id``, ``datasets`` (training, validation and
    every test trajectory, each with :data:`DATASET_FIELDS`), ``separation``
    (:data:`SEPARATION_FIELDS`), ``build_script`` (the digest of the task's ``build.py`` when it
    exists) and ``authorized_part`` (:func:`authorized_provenance`). For the user only: it holds the
    recording names and the digests of the sealed files.
    """
    datasets = [_visible_entry(task, "train", task.data.train_path, WORKSPACE_TRAIN, "training")]
    if task.data.val_path is not None:
        datasets.append(_visible_entry(task, "val", task.data.val_path, WORKSPACE_VAL, "validation"))
    sealed = sealed_dataset_records(task)
    for rec in sealed:
        datasets.append({
            "dataset": rec.trajectory,
            "assignment": rec.assignment,
            "agent_visible": False,
            "source": {
                "recording_names": [rec.source_name] if rec.source_name else NOT_STATED,
                "task_file": rec.declared_file,
                "working_directory_file": None,
                "provenance_document": "provenance.md of the task folder",
            },
            "version": {"sha256": rec.sha256},
            "trajectories": [{"id": rec.trajectory, "samples": rec.samples}],
            "trajectory_column": None,
            "sampling_period_s": task.dynamics.sampling_period if task.dynamics is not None else None,
            "samples": rec.samples,
            "operating_conditions": _operating_conditions(task),
            "noise": task.data.noise or NOT_STATED,
            "preprocessing": task.data.preprocessing or NOT_STATED,
        })
    build = task.task_dir / "build.py"
    prov_doc = task.task_dir / "provenance.md"
    return {
        "format_version": PROVENANCE_FORMAT_VERSION,
        "task_id": task.id,
        "user_facing": "contains recording names and digests of sealed files; never shown to the agent",
        "sampling_period_s": task.dynamics.sampling_period if task.dynamics is not None else None,
        "sampling_period_note": None if task.dynamics is not None else "static task: the samples are not ordered in time",
        "datasets": datasets,
        "separation": _separation(task, len(sealed)),
        "build_script": {"file": "build.py", "sha256": file_sha256(build)} if build.is_file() else NOT_STATED,
        "provenance_document": {"file": "provenance.md", "sha256": file_sha256(prov_doc)} if prov_doc.is_file() else NOT_STATED,
        "authorized_part": authorized_provenance(task),
    }


def authorized_provenance(task: TaskSpec) -> dict[str, Any]:
    """The part of the dataset provenance that the agent receives.

    Exactly the dataset facts of the public view (from which the brief is rendered): the neutral
    working-directory names, sample and trajectory counts and lengths, the trajectory column,
    the sampling period, noise and preprocessing. It never contains a recording name, a digest of
    a sealed file or any fact about the test data.
    """
    view = public_view(task)
    data = view["data"]
    out: dict[str, Any] = {
        "sampling_period_s": view.get("dynamics", {}).get("sampling_period"),
        "noise": data.get("noise"),
        "preprocessing": data.get("preprocessing"),
        "trajectory_column": data.get("trajectory_column"),
        "train": data.get("train"),
    }
    if "val" in data:
        out["val"] = data["val"]
    return out
