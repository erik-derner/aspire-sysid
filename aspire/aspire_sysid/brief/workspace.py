"""Provisioning of the working directory and the hashes of the texts sent to the agent.

The harness supplies in the working directory the brief, the permitted data and supporting
files, the required model file format, an empty model folder and ``check_submission.py``. The
harness records the version of the writing rules supplied to the agent; they are part of
``FORMAT.md``. The record contains the system prompt and the brief with a cryptographic hash of
each. Nothing else is written into the working directory.

:func:`provision_workspace` is the single entry point that writes a working directory. It writes
exactly

* ``TASK.md``, the brief (:func:`aspire_sysid.brief.render.render_brief`);
* ``FORMAT.md``, the model file format, one general example and the writing rules: one fixed
  text for every task (:func:`aspire_sysid.brief.reference.format_reference`; its digest is
  recorded);
* ``data/train.csv``, ``data/val.csv`` (when the task has validation data) and
  ``context/<file>`` for every supporting file (:func:`aspire_sysid.task.provision_data`);
* ``check_submission.py`` and ``check_config.json`` (:func:`aspire_sysid.model.write_check_files`);
* the empty folder ``models/``;

and returns a :class:`WorkspaceManifest` with every file and its SHA-256 digest. The function receives the task specification and uses only its agent-visible part; it never
receives a sealed path.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..model import write_check_files
from ..model.checks import MODELS_DIR
from ..task.provision import ProvisionedFile, provision_data
from ..task.schema import TaskSpec
from .prompts import FIRST_USER_MESSAGE, HELPER_SYSTEM_PROMPT, render_system_prompt, sha256_text
from .reference import format_reference
from .render import BRIEF_FILE, FORMAT_FILE, render_brief

__all__ = [
    "WorkspaceManifest",
    "RunTexts",
    "provision_workspace",
    "text_hashes",
    "render_run_texts",
]

@dataclass(frozen=True)
class WorkspaceManifest:
    """What :func:`provision_workspace` wrote.

    ``files`` lists every written file with its SHA-256 digest, sorted by name; ``folders`` are
    the folders created (``models`` is empty). ``brief_sha256`` is the digest of the bytes of
    ``TASK.md``; ``format_sha256`` is that of ``FORMAT.md``, the version of the model file format and
    of the writing rules supplied to the agent.
    """

    workspace: str
    task_id: str
    interactive: bool
    files: tuple[ProvisionedFile, ...]
    folders: tuple[str, ...]
    brief_sha256: str
    format_sha256: str

    @property
    def names(self) -> tuple[str, ...]:
        """The relative names of the written files, sorted."""
        return tuple(f.name for f in self.files)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the record."""
        return {
            "workspace": self.workspace,
            "task_id": self.task_id,
            "interactive": self.interactive,
            "files": [{"name": f.name, "sha256": f.sha256, "bytes": f.bytes} for f in self.files],
            "folders": list(self.folders),
            "brief_sha256": self.brief_sha256,
            "format_sha256": self.format_sha256,
        }


def _write_bytes(ws: Path, name: str, blob: bytes) -> ProvisionedFile:
    dst = ws / name
    if dst.exists():
        raise FileExistsError(f"{name} already exists in the working directory")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(blob)
    return ProvisionedFile(name=name, sha256=hashlib.sha256(blob).hexdigest(), bytes=len(blob))


def provision_workspace(
    task: TaskSpec,
    workspace_dir: str | Path,
    *,
    interactive: bool = False,
) -> WorkspaceManifest:
    """Write the working directory of a run and return its manifest.

    ``interactive`` selects the brief of interactive operation (its last section states the
    session limits). The folder must be absent or empty. Returns the :class:`WorkspaceManifest`;
    see the module docstring for the exact list of files.
    """
    ws = Path(workspace_dir)
    if ws.exists() and (not ws.is_dir() or any(ws.iterdir())):
        raise FileExistsError(f"the working directory {ws} exists and is not empty")
    ws.mkdir(parents=True, exist_ok=True)
    format_blob = format_reference().encode("utf-8")
    brief_blob = render_brief(task, interactive=interactive).encode("utf-8")
    written: list[ProvisionedFile] = [
        _write_bytes(ws, BRIEF_FILE, brief_blob),
        _write_bytes(ws, FORMAT_FILE, format_blob),
    ]
    written += provision_data(task, ws)
    written += write_check_files(task, ws)
    (ws / MODELS_DIR).mkdir(exist_ok=False)
    folders = sorted({str(Path(f.name).parent.as_posix()) for f in written if "/" in f.name} | {MODELS_DIR})
    return WorkspaceManifest(
        workspace=str(ws),
        task_id=task.id,
        interactive=interactive,
        files=tuple(sorted(written, key=lambda f: f.name)),
        folders=tuple(folders),
        brief_sha256=hashlib.sha256(brief_blob).hexdigest(),
        format_sha256=hashlib.sha256(format_blob).hexdigest(),
    )


def text_hashes(brief: str, system_prompt: str) -> dict[str, str]:
    """SHA-256 digests of the brief and the system prompt for the record.

    Both texts are written and sent as UTF-8; the digest of ``brief`` equals the digest of the
    file ``TASK.md`` that :func:`provision_workspace` writes, and the digest of ``system_prompt``
    equals the ``system_prompt_sha256`` of the ``round_start`` event of the turn loop.
    """
    return {"brief_sha256": sha256_text(brief), "system_prompt_sha256": sha256_text(system_prompt)}


@dataclass(frozen=True)
class RunTexts:
    """The texts that the harness sends to the agent in one run, with their hashes.

    ``brief`` is the text of ``TASK.md``; ``system_prompt`` the main agent's prompt (the
    system prompt of the harness with the environment description); ``first_user_message`` the message that starts
    the first round; ``helper_system_prompt`` the prompt of a helper agent.
    """

    brief: str
    system_prompt: str
    first_user_message: str
    helper_system_prompt: str
    hashes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the record."""
        return {
            "brief": self.brief,
            "system_prompt": self.system_prompt,
            "first_user_message": self.first_user_message,
            "helper_system_prompt": self.helper_system_prompt,
            "hashes": dict(self.hashes),
        }


def render_run_texts(task: TaskSpec, configuration: Any, probe: Any, *, interactive: bool = False) -> RunTexts:
    """Render the brief and the prompts of one run and their SHA-256 digests (App. A, B).

    ``configuration`` is the ``ToolConfig`` (``None``: the one of ``aspire/configs/tools.yaml``);
    ``probe`` is the ``EnvironmentProbe`` of the agent's interpreter (``None``: no package is
    claimed). The hashes are those of :func:`text_hashes`, plus ``first_user_message_sha256`` and
    ``helper_system_prompt_sha256``.
    """
    brief = render_brief(task, interactive=interactive)
    prompt = render_system_prompt(configuration, probe, interactive=interactive)
    hashes = text_hashes(brief, prompt)
    hashes["first_user_message_sha256"] = sha256_text(FIRST_USER_MESSAGE)
    hashes["helper_system_prompt_sha256"] = sha256_text(HELPER_SYSTEM_PROMPT)
    return RunTexts(brief, prompt, FIRST_USER_MESSAGE, HELPER_SYSTEM_PROMPT, hashes)
