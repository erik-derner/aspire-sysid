"""The stub of a new task: a task folder made from the user's data files.

``aspire session --train <file> [--val <file>] [--test <file> ...]`` starts from data files. The
harness creates a new task folder and *copies* the files into it under neutral names
(``data/train.csv``, ``data/val.csv``, and one file per test trajectory in the sealed folder); the
originals are not touched, and their names, which may be recording names, are kept only in
``interview/stub.json`` and are never shown to an agent. The task interview
(:mod:`aspire_sysid.session.interview`) then prepares ``task.yaml`` with the user.

**Sealing.** This module *writes* into the sealed folder of the new task and writes the test
entries of the definition; it never opens a file of the sealed folder for reading (the digest of a
test file is computed from the user's original). It is the only module outside
``aspire_sysid/evaluate`` and the task schema and loader that names the sealed folders, and it sets
the fields that decide what is sealed (:func:`merge_definition`): the identifier, the paths of the
data files and the test entries. A definition written by an agent cannot change them, declare a
visible file as test data, or add a sealed reference.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .schema import SEALED_FOLDERS

__all__ = ["InterviewError", "STUB_FILE", "TaskStub", "create_task_stub", "default_task_dir", "draft_text", "load_task_stub",
           "merge_definition"]

TEST = "test"
REFERENCE = "reference"
assert (TEST, REFERENCE) == SEALED_FOLDERS  # the sealed folders and the fields of task.yaml of the same names

_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
STUB_FILE = "interview/stub.json"


class InterviewError(Exception):
    """The task stub cannot be created, or the interview cannot run."""


# ---------------------------------------------------------------------------------------------
# the task stub


@dataclass(frozen=True)
class TaskStub:
    """A new task folder that holds the user's data files and no definition yet.

    ``train``, ``val`` and ``tests`` are paths relative to the task folder; ``sources`` maps each of
    them to the original path and the SHA-256 digest of the copied file (for the user only; never shown to the agent).
    """

    task_dir: Path
    task_id: str
    train: str
    val: str | None
    tests: tuple[str, ...]
    sources: Mapping[str, Mapping[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "train": self.train, "val": self.val, "tests": list(self.tests),
                "sources": {k: dict(v) for k, v in self.sources.items()}}

    @property
    def supplied_text(self) -> str:
        """The kinds of data the user supplied, for the first message of the interview."""
        parts = ["training data (data/train.csv)"]
        if self.val:
            parts.append("validation data (data/val.csv)")
        text = " and ".join(parts)
        return text + ("; the user also supplied test data, which the harness keeps" if self.tests else "")


def default_task_dir(base: str | Path | None = None, today: str | None = None) -> Path:
    """The folder of a new task when none is named: ``tasks/task-<YYYYMMDD>-<n>`` under the current
    directory, with the first number ``n`` from 01 for which no folder exists."""
    root = Path(base) if base is not None else Path.cwd() / "tasks"
    day = today or _dt.date.today().strftime("%Y%m%d")
    n = 1
    while (root / f"task-{day}-{n:02d}").exists():
        n += 1
    return root / f"task-{day}-{n:02d}"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def create_task_stub(task_dir: str | Path, train: str | Path, val: str | Path | None = None,
                     tests: Sequence[str | Path] = ()) -> TaskStub:
    """Create the task folder ``task_dir`` and copy the user's data files into it (module docstring,
    step 1). The name of the folder is the task identifier: lower-case letters, digits and hyphens.

    The files are copied, never moved. Raises :class:`InterviewError` when a file does not exist,
    the identifier is not permitted, or the folder exists and is not empty.
    """
    folder = Path(task_dir).resolve()
    if not _ID.match(folder.name):
        raise InterviewError(f"the name of the task folder, {folder.name!r}, is the task identifier and must consist of "
                             "lower-case letters, digits and hyphens")
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise InterviewError(f"the task folder {folder} exists and is not empty; an existing task is never overwritten")
    plan: list[tuple[Path, str]] = [(Path(train), "data/train.csv")]
    if val is not None:
        plan.append((Path(val), "data/val.csv"))
    plan += [(Path(t), f"{TEST}/{TEST}_{i}.csv") for i, t in enumerate(tests, 1)]
    for src, _ in plan:
        if not src.is_file():
            raise InterviewError(f"the data file {src} does not exist")
    sources: dict[str, dict[str, str]] = {}
    for src, rel in plan:
        dst = folder / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        sources[rel] = {"original": str(src.resolve()), "sha256": _sha256(src)}  # of the original: the sealed copy is never read
    stub = TaskStub(folder, folder.name, "data/train.csv", "data/val.csv" if val is not None else None,
                    tuple(rel for _, rel in plan if rel.startswith(TEST + "/")), sources)
    (folder / "interview").mkdir(exist_ok=True)
    (folder / STUB_FILE).write_text(json.dumps(stub.to_dict(), indent=2) + "\n", encoding="utf-8", newline="\n")
    return stub


def load_task_stub(task_dir: str | Path) -> TaskStub:
    """Read the stub of a task folder created by :func:`create_task_stub`."""
    folder = Path(task_dir).resolve()
    try:
        d = json.loads((folder / STUB_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InterviewError(f"{folder} is not a task folder prepared for an interview ({exc})") from exc
    return TaskStub(folder, str(d["task_id"]), str(d["train"]), d.get("val"), tuple(d.get("tests") or ()), d.get("sources") or {})


def draft_text(stub: TaskStub) -> str:
    """The draft ``task.yaml`` written into the interview agent's working directory."""
    lines = [
        "# Draft of the task definition. Complete it as TASK_GUIDE.md and TASK_REFERENCE.md describe.",
        "# The fields marked \"set by the harness\" must stay as they are; the harness restores them at every check.",
        f"# The harness also adds the test data itself: do not write a field `{TEST}`.",
        "",
        "schema_version: 1            # set by the harness",
        f"id: {stub.task_id}            # set by the harness",
        "",
        "data:",
        f"  train: {stub.train}       # set by the harness",
    ]
    if stub.val:
        lines.append(f"  val: {stub.val}           # set by the harness")
    return "\n".join(lines) + "\n"


def merge_definition(text: str, stub: TaskStub) -> dict[str, Any]:
    """The task definition of the agent's ``task.yaml`` with the harness's fields set (module
    docstring, step 3): identifier, schema version, data paths and test entries. A sealed reference
    cannot be declared through an interview. Raises :class:`InterviewError` when the text is not a
    YAML mapping."""
    try:
        spec = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise InterviewError(f"task.yaml is not valid YAML: {exc}") from exc
    if not isinstance(spec, dict):
        raise InterviewError("task.yaml must be a YAML mapping of fields, as in the examples")
    spec = dict(spec)
    spec["schema_version"] = 1
    spec["id"] = stub.task_id
    data = dict(spec.get("data") or {}) if isinstance(spec.get("data"), dict) else {}
    data["train"] = stub.train
    data.pop("val", None)
    data.pop("source_name", None)
    if stub.val:
        data["val"] = stub.val
    spec["data"] = data
    spec.pop(TEST, None)
    spec.pop(REFERENCE, None)
    if stub.tests:
        spec[TEST] = [{"file": rel, "trajectory": f"{TEST}-{i}"} for i, rel in enumerate(stub.tests, 1)]
    return spec
