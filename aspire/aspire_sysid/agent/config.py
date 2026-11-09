"""The tool configuration of the agent.

There is one tool configuration. It offers every tool of
the harness: reading, writing and listing permitted files, executing commands, web access
(fetch, search), package installation and one level of helper agents. The file
``aspire/configs/tools.yaml`` holds its settings (limits, output caps, request settings);
:func:`load_tool_config` validates it. The list of tools is not a setting: the file must name
every tool, so that no tool can be switched off there. A user who wants to restrict the use of a
tool says so in the task description.

The records give the one configuration the name ``open`` (``configuration.name``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..paths import config_path

__all__ = [
    "ALL_TOOLS",
    "CONFIG_FILE",
    "CONFIG_NAME",
    "ToolConfigError",
    "ShellSettings",
    "OutputSettings",
    "RequestSettings",
    "HelperSettings",
    "WebSettings",
    "ToolConfig",
    "load_tool_config",
    "tool_config_from_mapping",
]

CONFIG_NAME = "open"
"""Name of the one tool configuration in the records (module docstring)."""

CONFIG_FILE = "tools.yaml"
"""File of the tool configuration in ``aspire/configs/``."""

ALL_TOOLS: tuple[str, ...] = (
    "read_file", "write_file", "list_files", "run_shell", "web_fetch", "web_search", "install_package", "start_helper",
)
"""The tools of the agent, in the order of their descriptions in every request."""


class ToolConfigError(ValueError):
    """A tool configuration file is malformed or contradicts the rules of the tools (every tool
    present, shell limit of at most 600 s)."""


@dataclass(frozen=True)
class ShellSettings:
    """Settings of ``run_shell`` (limit of 600 s or the remaining round time)."""

    limit_s: float = 600.0
    allowed_path_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class OutputSettings:
    """Caps of tool results: sent to the agent, and kept in the record."""

    agent_cap_chars: int = 20000
    record_cap_chars: int = 10_000_000


REASONING_EFFORTS = ("none", "low", "medium", "high", "xhigh", "max")
"""Reasoning efforts accepted in a configuration (OpenAI: ``none`` to ``xhigh``; Anthropic:
``low`` to ``max``, ``none`` disables thinking); the vendor rejects a value it does not support."""

REASONING_SUMMARIES = ("auto", "concise", "detailed")
"""Reasoning-summary settings accepted in a configuration (OpenAI ``reasoning.summary``; any of
them selects ``display: summarized`` for Anthropic)."""


@dataclass(frozen=True)
class RequestSettings:
    """Settings of every language-model request.

    ``reasoning_effort`` and ``reasoning_summary`` are passed to the provider as
    :class:`~aspire_sysid.agent.providers.ReasoningSettings`; ``None`` leaves the model's default
    (effort) or requests no summary.
    """

    max_output_tokens: int = 16384
    unreported_usage_chars_per_token: float = 2.0
    reasoning_effort: str | None = None
    reasoning_summary: str | None = None

    def reasoning(self) -> Any:
        """The :class:`~aspire_sysid.agent.providers.ReasoningSettings` of every request."""
        from .providers import ReasoningSettings  # noqa: PLC0415 - avoids an import cycle

        return ReasoningSettings(effort=self.reasoning_effort, summary=self.reasoning_summary)


@dataclass(frozen=True)
class HelperSettings:
    """Settings of the helper agents."""

    max_helpers: int = 5
    default_turns: int = 20


@dataclass(frozen=True)
class WebSettings:
    """Settings of the web tools."""

    max_fetch_chars: int = 200000
    denied_url_substrings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolConfig:
    """The tool configuration. ``origin`` is the file it was read from; ``name`` is
    always :data:`CONFIG_NAME`."""

    tools: tuple[str, ...] = ALL_TOOLS
    shell: ShellSettings = field(default_factory=ShellSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    requests: RequestSettings = field(default_factory=RequestSettings)
    helpers: HelperSettings | None = None
    web: WebSettings | None = None
    origin: str = "<mapping>"

    @property
    def name(self) -> str:
        """The name of the configuration in the records: always :data:`CONFIG_NAME`."""
        return CONFIG_NAME

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the record (the tool configuration)."""
        return {
            "name": self.name,
            "tools": list(self.tools),
            "shell": {
                "limit_s": self.shell.limit_s,
                "allowed_path_prefixes": list(self.shell.allowed_path_prefixes),
            },
            "output": {
                "agent_cap_chars": self.output.agent_cap_chars,
                "record_cap_chars": self.output.record_cap_chars,
            },
            "requests": {
                "max_output_tokens": self.requests.max_output_tokens,
                "unreported_usage_chars_per_token": self.requests.unreported_usage_chars_per_token,
                "reasoning_effort": self.requests.reasoning_effort,
                "reasoning_summary": self.requests.reasoning_summary,
            },
            "helpers": None
            if self.helpers is None
            else {"max_helpers": self.helpers.max_helpers, "default_turns": self.helpers.default_turns},
            "web": None
            if self.web is None
            else {
                "max_fetch_chars": self.web.max_fetch_chars,
                "denied_url_substrings": list(self.web.denied_url_substrings),
            },
            "origin": self.origin,
        }


def _num(data: Mapping[str, Any], key: str, default: float, where: str, *, integer: bool = False, minimum: float = 0) -> Any:
    v = data.get(key, default)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        raise ToolConfigError(f"{where}: '{key}' must be a finite number, got {v!r}")
    if integer and int(v) != v:
        raise ToolConfigError(f"{where}: '{key}' must be an integer, got {v!r}")
    if v < minimum or (minimum == 0 and v <= 0):
        raise ToolConfigError(f"{where}: '{key}' must be positive, got {v!r}")
    return int(v) if integer else float(v)


def _choice(data: Mapping[str, Any], key: str, allowed: tuple[str, ...], where: str) -> str | None:
    v = data.get(key)
    if v is None:
        return None
    if v not in allowed:
        raise ToolConfigError(f"{where}: '{key}' must be one of {list(allowed)} or null, got {v!r}")
    return str(v)


def _section(data: Mapping[str, Any], key: str, where: str) -> Mapping[str, Any] | None:
    v = data.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ToolConfigError(f"{where}: '{key}' must be a mapping or null")
    return v


def _strings(v: Any, where: str) -> tuple[str, ...]:
    if v is None:
        return ()
    if not isinstance(v, list) or not all(isinstance(x, str) and x for x in v):
        raise ToolConfigError(f"{where}: expected a list of non-empty strings, got {v!r}")
    return tuple(v)


def tool_config_from_mapping(data: Any, *, origin: str = "<mapping>") -> ToolConfig:
    """Validate a parsed configuration and build the :class:`ToolConfig`.

    Rules: the file names every tool of :data:`ALL_TOOLS` exactly once (no tool can be switched
    off); ``helpers`` and ``web`` sections are required.
    """
    where = f"tool configuration {origin}"
    if not isinstance(data, Mapping):
        raise ToolConfigError(f"{where}: expected a mapping at the top level")
    if data.get("schema_version") != 2:
        raise ToolConfigError(f"{where}: schema_version must be 2")
    unknown_keys = sorted(set(data) - {"schema_version", "tools", "shell", "output", "requests", "helpers", "web"})
    if unknown_keys:
        raise ToolConfigError(f"{where}: unknown field(s) {unknown_keys}")
    tools = _strings(data.get("tools"), f"{where}, 'tools'")
    unknown = [t for t in tools if t not in ALL_TOOLS]
    if unknown:
        raise ToolConfigError(f"{where}: unknown tools {unknown}; known: {sorted(ALL_TOOLS)}")
    if len(set(tools)) != len(tools):
        raise ToolConfigError(f"{where}: a tool is listed twice")
    missing = [t for t in ALL_TOOLS if t not in tools]
    if missing:
        raise ToolConfigError(
            f"{where}: the agent always has every tool; missing {missing}. A restriction of the "
            "use of a tool belongs in the task description, not in this file."
        )
    sh = _section(data, "shell", where) or {}
    shell = ShellSettings(
        limit_s=_num(sh, "limit_s", 600.0, f"{where}, shell"),
        allowed_path_prefixes=_strings(sh.get("allowed_path_prefixes"), f"{where}, shell.allowed_path_prefixes"),
    )
    if shell.limit_s > 600:
        raise ToolConfigError(f"{where}: shell.limit_s must not exceed 600 s, got {shell.limit_s}")
    out = _section(data, "output", where) or {}
    output = OutputSettings(
        agent_cap_chars=_num(out, "agent_cap_chars", 20000, f"{where}, output", integer=True),
        record_cap_chars=_num(out, "record_cap_chars", 10_000_000, f"{where}, output", integer=True),
    )
    rq = _section(data, "requests", where) or {}
    requests = RequestSettings(
        max_output_tokens=_num(rq, "max_output_tokens", 16384, f"{where}, requests", integer=True),
        unreported_usage_chars_per_token=_num(rq, "unreported_usage_chars_per_token", 2.0, f"{where}, requests"),
        reasoning_effort=_choice(rq, "reasoning_effort", REASONING_EFFORTS, f"{where}, requests"),
        reasoning_summary=_choice(rq, "reasoning_summary", REASONING_SUMMARIES, f"{where}, requests"),
    )
    hp = _section(data, "helpers", where)
    helpers = None
    if hp is not None:
        helpers = HelperSettings(
            max_helpers=_num(hp, "max_helpers", 5, f"{where}, helpers", integer=True),
            default_turns=_num(hp, "default_turns", 20, f"{where}, helpers", integer=True),
        )
    if helpers is None:
        raise ToolConfigError(f"{where}: start_helper requires a 'helpers' section")
    wb = _section(data, "web", where)
    web = None
    if wb is not None:
        web = WebSettings(
            max_fetch_chars=_num(wb, "max_fetch_chars", 200000, f"{where}, web", integer=True),
            denied_url_substrings=_strings(wb.get("denied_url_substrings"), f"{where}, web.denied_url_substrings"),
        )
    if web is None:
        raise ToolConfigError(f"{where}: the web tools require a 'web' section")
    return ToolConfig(
        tools=tools,
        shell=shell,
        output=output,
        requests=requests,
        helpers=helpers,
        web=web,
        origin=origin,
    )


def load_tool_config(path: str | Path | None = None) -> ToolConfig:
    """Load the tool configuration from ``aspire/configs/tools.yaml``, or from ``path``.

 Raises :class:`ToolConfigError`.
    """
    p = config_path(CONFIG_FILE) if path is None else Path(path)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ToolConfigError(f"tool configuration {p}: cannot be read ({exc})") from exc
    return tool_config_from_mapping(data, origin=str(p))
