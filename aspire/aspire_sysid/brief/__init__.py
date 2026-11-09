"""Task brief, system prompts and execution messages.

Implements the system prompts, the task brief (contents and order), the execution messages, the
contents of the working directory, and the hashes of the brief and the system prompt in the
record.

* :mod:`aspire_sysid.brief.messages`: the execution messages.
* :mod:`aspire_sysid.brief.render`: :func:`render_brief`, the text of ``TASK.md``.
* :mod:`aspire_sysid.brief.reference`: :func:`format_reference`, the fixed text of ``FORMAT.md``.
* :mod:`aspire_sysid.brief.prompts`: :func:`render_system_prompt` and the verbatim prompt
  paragraphs; the helper prompt and the first user message.
* :mod:`aspire_sysid.brief.workspace`: :func:`provision_workspace`, the single entry point
  that writes a working directory, and :func:`text_hashes` / :func:`render_run_texts` for the
  record.

This package does not import :mod:`aspire_sysid.agent` at import time, because the agent's turn
loop imports it.
"""

from .prompts import (
    FIRST_USER_MESSAGE,
    HELPER_SYSTEM_PROMPT,
    INTERACTIVE_PARAGRAPH,
    SYSTEM_PARAGRAPHS,
    environment_description,
    packages_text,
    render_system_prompt,
    sha256_text,
    system_prompt_core,
)
from .reference import format_reference
from .render import BRIEF_FILE, CHECK_COMMAND, FORMAT_FILE, POOL_STATEMENT, SECTION_TITLES, pool_statement, render_brief
from .workspace import RunTexts, WorkspaceManifest, provision_workspace, render_run_texts, text_hashes

__all__ = [
    "BRIEF_FILE",
    "CHECK_COMMAND",
    "FIRST_USER_MESSAGE",
    "HELPER_SYSTEM_PROMPT",
    "INTERACTIVE_PARAGRAPH",
    "FORMAT_FILE",
    "POOL_STATEMENT",
    "RunTexts",
    "SECTION_TITLES",
    "SYSTEM_PARAGRAPHS",
    "WorkspaceManifest",
    "environment_description",
    "format_reference",
    "packages_text",
    "pool_statement",
    "provision_workspace",
    "render_brief",
    "render_run_texts",
    "render_system_prompt",
    "sha256_text",
    "system_prompt_core",
    "text_hashes",
]
