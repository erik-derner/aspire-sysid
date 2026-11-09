"""Provisioning of the agent-visible data into a working directory.

The working directory receives the training and validation data
and the supporting files under neutral names, and nothing of the sealed store. This module
copies ``data/train.csv``, ``data/val.csv`` and ``context/<file>`` byte for byte; the brief
, the checking script and the empty ``models/`` folder are written by their own
modules. It never receives a sealed path.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from .schema import TaskSpec

WORKSPACE_TRAIN = "data/train.csv"
"""Neutral name of the training data in the working directory."""

WORKSPACE_VAL = "data/val.csv"
"""Neutral name of the validation data in the working directory."""

WORKSPACE_CONTEXT_DIR = "context"
"""Folder of the supporting files in the working directory."""


def workspace_context_name(path: Path) -> str:
    """Working-directory name ``context/<file name>`` of a supporting file."""
    return f"{WORKSPACE_CONTEXT_DIR}/{path.name}"


@dataclass(frozen=True)
class ProvisionedFile:
    """One file written to a working directory: its relative name and SHA-256 digest."""

    name: str
    sha256: str
    bytes: int


def provision_data(task: TaskSpec, workspace_dir: str | Path) -> list[ProvisionedFile]:
    """Copy the agent-visible data and supporting files into ``workspace_dir``.

    Writes ``data/train.csv``, ``data/val.csv`` (when the task has validation data) and
    ``context/<file>`` for every supporting file; creates the folders as needed. Refuses to
    overwrite an existing file. Returns the written files with their SHA-256 digests for the
    record.
    """
    ws = Path(workspace_dir)
    ws.mkdir(parents=True, exist_ok=True)
    plan: list[tuple[Path, str]] = [(task.data.train_path, WORKSPACE_TRAIN)]
    if task.data.val_path is not None:
        plan.append((task.data.val_path, WORKSPACE_VAL))
    plan += [(c.path, workspace_context_name(c.path)) for c in task.context]
    written: list[ProvisionedFile] = []
    for src, name in plan:
        dst = ws / name
        if dst.exists():
            raise FileExistsError(f"{name} already exists in the working directory")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        blob = dst.read_bytes()
        written.append(ProvisionedFile(name=name, sha256=hashlib.sha256(blob).hexdigest(), bytes=len(blob)))
    return written
