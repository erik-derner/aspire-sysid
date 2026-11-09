"""Working directories of autonomous runs outside the repository, and their copies for the record.

The working directory holds only the files the agent may see; test data and reference
expressions are sealed; the record of a run keeps a copy of the working directory. A working
directory inside the repository would expose the committed test files through the git history (``git log -p`` in the working directory finds
the enclosing repository). The experiment runner therefore places every working directory under a
**workspace root** outside every git repository, by default ``<system temp>/aspire-runs``:

    <workspace root>/[dry-run/]<random>/workspace

where ``<random>`` is a new random name for every attempt (:func:`opaque_attempt_folder`). The
path names no experiment, task, task context, tool configuration or run, so that the agent of a
blind run cannot learn from its working directory that it is blind, nor which
task it is; the mapping from the random name to the run is kept only in the run folder
(``run_start.json``), and the owner file of the attempt folder holds only a random token. Dry
runs have their own subtree. A leftover attempt folder is never deleted:
:func:`claim_attempt_folder` refuses a non-empty folder. The layout ensures neither a relative path (``..``) from the working directory nor git's search for an
enclosing repository reaches ``tasks/``. At the end of the run the harness copies the final
working directory into the run folder as ``workspace/`` (:func:`copy_workspace`), without caches
and within size bounds, and records what it left out.

**Residual risk.** The working directory outside the repository removes the relative routes to
the task store; it does not isolate the agent. The agent's commands run as the same
operating-system user as the harness, so a program that opens the absolute path of the task
store can read it (the command filter refuses such paths in command text, but not in a program
that assembles them at run time; ``aspire/README.md``, "Tool policy and its limits"). Full
isolation requires an operating-system sandbox or a separate user without read access to
``tasks/``. For blind tasks in particular: the working directories of all runs lie under the same
workspace root, so a program of a blind run that lists the root and reads the ``TASK.md`` of a
sibling folder (a described run of the same task) learns the task; only a separate
operating-system user per run, or running blind tasks with their own workspace root, prevents
that.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import secrets
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..paths import HARNESS_DIR

__all__ = [
    "WorkspaceRootError",
    "EXCLUDED_NAMES",
    "MAX_FILE_BYTES",
    "MAX_TOTAL_BYTES",
    "check_workspace_root",
    "enclosing_repository",
    "opaque_attempt_folder",
    "experiment_instance",
    "claim_attempt_folder",
    "LeftoverAttemptError",
    "ENVIRONMENT_MARKERS",
    "OWNER_FILE",
    "WorkspaceCopy",
    "copy_workspace",
]

EXCLUDED_NAMES: tuple[str, ...] = (
    "__pycache__", "*.pyc", "*.pyo", ".ipynb_checkpoints", ".git", ".cache", ".mypy_cache", ".pytest_cache",
    "node_modules", ".julia", "*.egg-info",
)
"""Folder and file name patterns that the copy for the record leaves out (caches)."""

ENVIRONMENT_MARKERS: tuple[str, ...] = ("pyvenv.cfg", "conda-meta")
"""A folder that contains one of these entries is a Python or conda environment created by the
agent; the copy leaves it out (whatever its name) and lists it. A folder merely named ``env`` or
``venv`` without a marker is copied."""

OWNER_FILE = "aspire-attempt.json"
"""File in each attempt folder that names the run, the attempt and the token of its owner."""

MAX_FILE_BYTES = 20_000_000
"""A file larger than this is not copied into the run folder; the record lists it with its size."""

MAX_TOTAL_BYTES = 200_000_000
"""The copy stops adding files when the copied bytes would exceed this bound; the rest is listed."""


class WorkspaceRootError(ValueError):
    """The workspace root lies inside a git repository or the repository of the harness. """


def enclosing_repository(path: str | Path) -> Path | None:
    """The first folder at or above ``path`` that holds a ``.git`` entry, or ``None``.

    This is the folder in which ``git`` started below ``path`` would find a repository (git's
    discovery walks the parent folders; the shell environment of the agent's commands additionally sets
    ``GIT_CEILING_DIRECTORIES``). 
    """
    p = Path(path).resolve()
    for folder in (p, *p.parents):
        if (folder / ".git").exists():
            return folder
    return None


def check_workspace_root(root: str | Path) -> Path:
    """Resolve the workspace root and refuse one inside a git repository.

    Refused: a root inside the repository that holds the harness (the folder above ``aspire/``)
    and a root at or below any folder that contains ``.git``. Returns the resolved root.
    """
    r = Path(root).resolve()
    repo = HARNESS_DIR.parent.resolve()
    try:
        r.relative_to(repo)
        inside = True
    except ValueError:
        inside = False
    if inside:
        raise WorkspaceRootError(
            f"the workspace root {r} lies inside the repository {repo}; working directories must lie outside it, "
            "so that relative paths and git's search for a repository cannot reach tasks/"
        )
    enclosing = enclosing_repository(r)
    if enclosing is not None:
        raise WorkspaceRootError(
            f"the workspace root {r} lies inside the git repository {enclosing}; choose a folder outside every repository "
            "(default: <system temp>/aspire-runs)"
        )
    return r


def experiment_instance(experiment_dir: str | Path) -> str:
    """The first 10 hexadecimal digits of the SHA-256 digest of the absolute experiment folder.

    Identifies the checkout of an experiment in its records (it is
    not part of any working-directory path).
    """
    return hashlib.sha256(str(Path(experiment_dir).resolve()).encode("utf-8")).hexdigest()[:10]


def opaque_attempt_folder(root: str | Path, *, dry_run: bool = False) -> Path:
    """A new attempt folder ``<root>/[dry-run/]<random>`` (not yet created) whose name reveals
    nothing about the run (module docstring); the working directory is its subfolder
    ``workspace``. """
    base = Path(root) / "dry-run" if dry_run else Path(root)
    return base / secrets.token_hex(8)


class LeftoverAttemptError(RuntimeError):
    """An attempt folder exists already and belongs to another execution; it is never deleted. """


def claim_attempt_folder(folder: str | Path, owner: dict[str, Any]) -> Path:
    """Create the attempt folder and write its owner file; refuse an existing non-empty folder.

 An existing empty folder (left by
    an interruption before anything was written) is taken; any other existing folder raises
    :class:`LeftoverAttemptError` naming its owner, and nothing is deleted.
    """
    d = Path(folder)
    if d.exists() and any(d.iterdir()):
        try:
            other = json.loads((d / OWNER_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            other = {"owner": "unknown (no readable owner file)"}
        raise LeftoverAttemptError(
            f"the attempt folder {d} exists and is not empty (owner: {other}); it is never deleted by the harness. "
            "Move or delete it by hand if it is not needed, then resume."
        )
    d.mkdir(parents=True, exist_ok=True)
    (d / OWNER_FILE).write_text(json.dumps(owner, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return d


@dataclass
class WorkspaceCopy:
    """What :func:`copy_workspace` copied and what it left out."""

    source: str
    destination: str
    files: int = 0
    bytes: int = 0
    excluded: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the run record."""
        return {
            "source": self.source,
            "destination": self.destination,
            "files_copied": self.files,
            "bytes_copied": self.bytes,
            "excluded": list(self.excluded),
            "rules": {
                "excluded_names": list(EXCLUDED_NAMES),
                "environment_markers": list(ENVIRONMENT_MARKERS),
                "max_file_bytes": MAX_FILE_BYTES,
                "max_total_bytes": MAX_TOTAL_BYTES,
                "links": "symbolic links are listed, never followed",
            },
        }


def _excluded(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDED_NAMES)


def copy_workspace(source: str | Path, destination: str | Path, *, max_file_bytes: int = MAX_FILE_BYTES,
                   max_total_bytes: int = MAX_TOTAL_BYTES) -> WorkspaceCopy:
    """Copy the final working directory into the run folder for the record.

    Files are copied in sorted order; names matching :data:`EXCLUDED_NAMES`, symbolic links,
    files above ``max_file_bytes`` and files beyond the total bound ``max_total_bytes`` are left
    out and listed with the reason. ``destination`` must not exist (records are never
    overwritten).
    """
    src = Path(source)
    dst = Path(destination)
    if dst.exists():
        raise FileExistsError(f"{dst} exists; a copy of a working directory is never overwritten")
    out = WorkspaceCopy(str(src), str(dst))
    dst.mkdir(parents=True)
    if not src.is_dir():
        out.excluded.append({"path": ".", "reason": "the working directory does not exist"})
        return out
    for dirpath, dirnames, filenames in os.walk(src, followlinks=False):
        here = Path(dirpath)
        rel_dir = here.relative_to(src)
        keep_dirs = []
        for d in sorted(dirnames):
            rel = (rel_dir / d).as_posix()
            if (here / d).is_symlink():
                out.excluded.append({"path": rel, "reason": "symbolic link (not followed)"})
            elif any((here / d / m).exists() for m in ENVIRONMENT_MARKERS):
                out.excluded.append({"path": rel + "/", "reason": "Python or conda environment (contains " +
                                     next(m for m in ENVIRONMENT_MARKERS if (here / d / m).exists()) + ")"})
            elif _excluded(d):
                out.excluded.append({"path": rel + "/", "reason": "cache folder"})
            else:
                keep_dirs.append(d)
        dirnames[:] = keep_dirs
        for f in sorted(filenames):
            p = here / f
            rel = (rel_dir / f).as_posix()
            if p.is_symlink():
                out.excluded.append({"path": rel, "reason": "symbolic link (not followed)"})
                continue
            if _excluded(f):
                out.excluded.append({"path": rel, "reason": "cache file"})
                continue
            try:
                size = p.stat().st_size
            except OSError as exc:
                out.excluded.append({"path": rel, "reason": f"cannot be read: {exc}"})
                continue
            if size > max_file_bytes:
                out.excluded.append({"path": rel, "reason": f"larger than {max_file_bytes} bytes", "bytes": size})
                continue
            if out.bytes + size > max_total_bytes:
                out.excluded.append({"path": rel, "reason": f"the copy reached its total bound of {max_total_bytes} bytes", "bytes": size})
                continue
            target = dst / rel_dir / f
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(p, target)
            except OSError as exc:
                out.excluded.append({"path": rel, "reason": f"copy failed: {exc}"})
                continue
            out.files += 1
            out.bytes += size
    return out
