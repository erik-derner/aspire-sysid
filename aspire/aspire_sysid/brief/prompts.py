"""System prompts of the harness, the environment description and the first user message.

The harness has one system prompt, printed in the appendix of the paper, and one paragraph
appended for interactive operation. There is one tool configuration, so there is one system
prompt. This module holds these texts verbatim and assembles the prompt that the harness sends with every
language-model request of the main agent.

Assembly rule (documented here and in ``aspire/README.md``):

1. The three paragraphs of the prompt, in their order, with ``{packages}`` filled (rule
   below). Each paragraph is one line, without line breaks inside a paragraph; paragraphs are separated by one empty line.
2. Interactive operation: the interactive paragraph is appended after the paragraphs of step 1.
3. The **environment description** follows, separated by one empty line and introduced by the
   line :data:`ENVIRONMENT_HEADING`: the tools, the shell that
   interprets ``run_shell`` commands (:func:`shell_line`), the Python version of
   the agent's interpreter, and the installed packages with their versions from the environment
   probe. It is the only part of the prompt that depends on the run environment.

Fill rule for ``{packages}`` (the prompt never states that a package is installed without
checking): the symbolic-regression packages PySR, gplearn and PySINDy that the probe
found installed, each with its version, in that order, joined as "A 1.0", "A 1.0 and B 2.0" or
"A 1.0, B 2.0 and C 3.0"; when the probe found none of them, the word ``none``; when the probe
failed, ``none that the harness could verify``. An uninstalled package is never named, not even
as absent. The sentence then reads, for example, "The installed symbolic-regression packages are
none; symbolic-regression search is suited to tasks of this kind, and whether you use it is your
decision." The rule is implemented once, in
``aspire_sysid.agent.probe.EnvironmentProbe.sr_packages_text``, and used here.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Protocol

__all__ = [
    "SYSTEM_PARAGRAPHS",
    "INTERACTIVE_PARAGRAPH",
    "ENVIRONMENT_HEADING",
    "HARNESS_DISTRIBUTIONS",
    "HELPER_SYSTEM_PROMPT",
    "FIRST_USER_MESSAGE",
    "packages_text",
    "shell_line",
    "environment_description",
    "system_prompt_core",
    "render_system_prompt",
    "sha256_text",
]

SYSTEM_PARAGRAPHS: tuple[str, ...] = (
    "You are an agent for system identification. Your task is in TASK.md in the working directory; "
    "read it first. FORMAT.md describes the files you deliver and how to write your texts. A human "
    "will assess your models and your explanations.",
    "How you identify the models is your decision. You may read and write files in the working "
    "directory, write and run code, fetch web resources, search the web, install Python packages and "
    "start helper agents. The installed symbolic-regression packages are {packages}; "
    "symbolic-regression search is suited to tasks of this kind, and whether you use it is your "
    "decision. Models of any kind, including black-box models, may serve as intermediate tools; the "
    "models you deliver have the form that TASK.md requires.",
    "Report what you actually did: the methods, the data and the settings you used. Helper agents "
    "cannot start further helpers, and their turns and cost count toward your limits. Everything you "
    "do is recorded. The test data and the evaluation results are not available to you; do not try to "
    "reach them or any file outside the working directory.",
)
"""The system prompt, verbatim, one paragraph per entry;
``{packages}`` is its placeholder. The first paragraph names the two files of the brief,
the second states what the agent may do, the third what it reports and what it cannot reach. The
prompt repeats nothing that ``TASK.md`` or ``FORMAT.md`` states: the pool, the recommendation, the
check of the files and the message that ends a round are in ``TASK.md``."""

INTERACTIVE_PARAGRAPH = (
    "This is an interactive session; TASK.md states how it proceeds. When you ask the user, ask one "
    "specific question at a time and say which decision it affects. If the user cannot answer, state "
    "the assumption you make instead and its limitation."
)
"""The paragraph appended in interactive operation, verbatim."""

HARNESS_DISTRIBUTIONS: tuple[str, ...] = ("aspire-sysid",)
"""Distributions of the harness itself, never listed in the environment description: the agent's
interpreter of a real run should not have the harness installed (aspire/README.md), and the
description makes no statement about it."""

ENVIRONMENT_HEADING = "Environment description (supplied by the harness from the run environment):"
"""First line of the environment description."""

HELPER_SYSTEM_PROMPT = (
    "You are a helper agent for system identification. The main agent has assigned you the "
    "subtask stated in the first message. You work in the same working directory as the main "
    "agent, with the tools described in this request; you cannot start further helper agents. "
    "Your turns and costs count toward the main agent's budget. Do not access information outside "
    "the permissions stated in TASK.md. When the subtask is finished, reply with text only, "
    "without a tool request. State what you did, the files you wrote, the methods, data and "
    "settings you used, and the results; give every number with its unit, the data set it was "
    "computed on and, for an error, its definition. Follow the writing rules in FORMAT.md. That reply ends your "
    "work and is returned to the main agent."
)
"""System prompt of a helper agent; harness text, written under the writing rules of the
harness's texts."""

FIRST_USER_MESSAGE = (
    "The identification round begins. The task brief is TASK.md in the working directory; the "
    "candidate file format and the writing rules are in FORMAT.md."
)
"""The first user message of an autonomous round (a request needs a user message; the system
prompt instructs the agent to read TASK.md first). Harness text."""


class _ProbeLike(Protocol):
    python_version: str | None
    packages: Mapping[str, str]
    sr_packages: Mapping[str, str]
    error: str | None

    def sr_packages_text(self) -> str: ...


def packages_text(probe: _ProbeLike | None) -> str:
    """The text that fills ``{packages}`` (fill rule in the module docstring).

    The rule is implemented once, in
    :meth:`aspire_sysid.agent.probe.EnvironmentProbe.sr_packages_text`; ``probe=None`` (no probe
    was run) gives ``none that the harness could verify``, as a failed probe does.
    """
    if probe is None:
        return "none that the harness could verify"
    return probe.sr_packages_text()


def shell_line(platform: str | None = None) -> str:
    """The line of the environment description that names the shell of ``run_shell``.

    Commands are started with ``subprocess`` and ``shell=True``: ``cmd.exe`` on Windows,
    ``/bin/sh`` elsewhere. On Windows, the line also names the consequence, because language
    models often write POSIX here-documents, which ``cmd.exe`` rejects, and naming ``cmd.exe`` in
    the tool description alone does not prevent it.
    """
    import sys

    if (platform or sys.platform) == "win32":
        return ("- Shell: run_shell passes each command to the Windows command interpreter cmd.exe, not to a "
                "POSIX shell. POSIX shell syntax such as here-documents (<<) does not work there; run Python "
                "code from a script file or with python -c.")
    return "- Shell: run_shell passes each command to the POSIX shell /bin/sh."


def _tools(configuration: Any) -> tuple[str, ...]:
    if configuration is None:
        from ..agent.config import load_tool_config

        configuration = load_tool_config()
    return tuple(configuration.tools)


def environment_description(configuration: Any, probe: _ProbeLike | None, *, interactive: bool = False) -> str:
    """The environment description appended to the system prompt.

    ``configuration`` is the :class:`~aspire_sysid.agent.config.ToolConfig` (``None``: the one of
    ``aspire/configs/tools.yaml``). The text names the tools (``ask_user`` added in interactive
    operation), the shell that interprets ``run_shell`` commands (:func:`shell_line`), the Python
    version of the agent's interpreter and every installed distribution with its version, sorted
    by name, except the harness's own distribution (:data:`HARNESS_DISTRIBUTIONS`); a failed probe
    is stated as such and no package is claimed.
    """
    tools = _tools(configuration)
    tool_list = list(tools) + (["ask_user"] if interactive and "ask_user" not in tools else [])
    lines = [
        ENVIRONMENT_HEADING,
        f"- Tools: {', '.join(tool_list)}.",
    ]
    if "run_shell" in tool_list:
        lines.append(shell_line())
    if probe is None or probe.error is not None:
        reason = "no probe was run" if probe is None else probe.error
        lines.append(f"- Installed software: the harness could not list the installed packages ({reason}); no package is claimed.")
        return "\n".join(lines)
    lines.append(f"- Python {probe.python_version}.")
    pk = sorted(
        ((n, v) for n, v in probe.packages.items() if n.lower().replace("_", "-") not in HARNESS_DISTRIBUTIONS),
        key=lambda kv: kv[0].lower(),
    )
    lines.append(f"- Installed packages and versions ({len(pk)}): " + ", ".join(f"{n} {v}" for n, v in pk) + ".")
    return "\n".join(lines)


def system_prompt_core(packages: str, *, interactive: bool = False) -> str:
    """The fixed part of the system prompt, with ``{packages}`` filled (steps 1 and 2
    of the assembly rule in the module docstring)."""
    paras = [p.replace("{packages}", packages) for p in SYSTEM_PARAGRAPHS]
    if interactive:
        paras.append(INTERACTIVE_PARAGRAPH)
    return "\n\n".join(paras)


def render_system_prompt(configuration: Any, probe: _ProbeLike | None, *, interactive: bool = False) -> str:
    """The complete system prompt of the main agent.

    ``configuration`` is the :class:`~aspire_sysid.agent.config.ToolConfig` (``None``: the one of
    ``aspire/configs/tools.yaml``); ``probe`` is the
    :class:`~aspire_sysid.agent.probe.EnvironmentProbe` of the agent's interpreter. The result is
    the fixed text (:func:`system_prompt_core`), one empty line and the environment description
    (:func:`environment_description`).
    """
    core = system_prompt_core(packages_text(probe), interactive=interactive)
    return core + "\n\n" + environment_description(configuration, probe, interactive=interactive)


def sha256_text(text: str) -> str:
    """SHA-256 digest of the UTF-8 bytes of ``text`` (cryptographic hash of the
    system prompt and the brief). The harness sends and writes these texts as UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
