"""The agent's tools, their registry and the confinement of paths to the working directory.

A tool is an operation the agent can request, such as reading a file or running a calculation;
the agent reaches the working directory only through the tools that the harness executes. The
tools read, write and list permitted files, execute commands, fetch web resources, search the
web, install packages and start helper agents. The tools cannot access sealed data, reference
expressions or withheld results.

Registry. A :class:`Tool` couples a description (:class:`~aspire_sysid.agent.providers.ToolSpec`)
with a handler ``handler(ctx, arguments) -> ToolOutcome``. :class:`ToolRegistry` holds the tools
offered in a round; :func:`build_registry` creates the built-in tools of a configuration. The
session layer adds ``ask_user`` with ``registry.register(Tool(...))``; its handler receives the
:class:`ToolContext` and excludes the user's answering time from the execution time with
``with ctx.clock.paused: ...``. A tool with ``helper_allowed=False`` is not
offered to helper agents (``start_helper`` always; ``ask_user`` by the choice of the session layer).

Path rules (:func:`resolve_in_workspace`): a path is relative to the working directory; an
absolute path, a drive letter, a path whose resolution (following symbolic links) leaves the
working directory, an existing file with more than one hard link (it may be the same file as
one outside the working directory), and a path with a NUL character are refused.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Callable, Iterable, Mapping

from .budget import BudgetTracker, ExecutionClock
from .config import ToolConfig
from .policy import ShellPolicy, shell_environment
from .providers import ToolSpec
from .shell import ShellResult, run_command

__all__ = [
    "ToolOutcome",
    "ToolContext",
    "Tool",
    "ToolRegistry",
    "PathError",
    "resolve_in_workspace",
    "WebBackends",
    "PipRunner",
    "HelperRunner",
    "BUILTIN_TOOLS",
    "build_registry",
    "REQUIREMENT_PATTERN",
    "default_pip_runner",
    "make_context",
]


@dataclass
class ToolOutcome:
    """The result of one tool execution (included in the next request).

    ``content`` is the complete result; the loop sends it to the agent shortened by the output
    cap and records it in full. ``denied`` marks a request refused by a policy;
    ``details`` holds structured data for the record (exit status, duration, ...).
    """

    content: str
    is_error: bool = False
    denied: bool = False
    details: dict[str, Any] = field(default_factory=dict)


WebFetch = Callable[[str, float], str]
WebSearch = Callable[[str, float], str]
PipRunner = Callable[[str, float], ShellResult]
"""``pip_runner(requirement, timeout_s)`` installs one requirement into the run environment."""
HelperRunner = Callable[[str, "int | None"], ToolOutcome]
"""``helper_runner(task_text, max_turns)`` runs one helper agent and returns its result."""


@dataclass(frozen=True)
class WebBackends:
    """Injectable backends of the web tools.

    ``fetch(url, timeout_s)`` returns the text of a web resource; ``search(query, timeout_s)``
    returns a text list of results. ``timeout_s`` is min(shell limit, remaining round time); the
    backend must return or raise within it. ``None`` means the tool is unavailable in this run and says so to the agent. No
    backend is configured in the tests; the harness makes no network request by itself.
    """

    fetch: WebFetch | None = None
    search: WebSearch | None = None


@dataclass
class ToolContext:
    """What a tool handler may use.

    ``emit(kind, **fields)`` records an event with the round's labels; ``clock`` is the
    execution clock (``ctx.clock.paused`` excludes user waiting time); ``tracker`` is the
    budget tracker of the calling agent (the helper's own tracker inside a helper).
    """

    workspace: Path
    config: ToolConfig
    policy: ShellPolicy
    env: Mapping[str, str]
    clock: ExecutionClock
    tracker: BudgetTracker
    emit: Callable[..., None]
    agent: str = "main"
    python_executable: str | None = None
    web: WebBackends = field(default_factory=WebBackends)
    pip_runner: PipRunner | None = None
    helper_runner: HelperRunner | None = None
    extra: dict[str, Any] = field(default_factory=dict)


Handler = Callable[[ToolContext, Mapping[str, Any]], ToolOutcome]


@dataclass(frozen=True)
class Tool:
    """A tool offered to the agent: description and handler."""

    name: str
    description: str
    parameters: Mapping[str, Any]
    handler: Handler
    helper_allowed: bool = True
    vendor_tool: str | None = None

    @property
    def spec(self) -> ToolSpec:
        """The description sent with every request."""
        return ToolSpec(name=self.name, description=self.description, parameters=dict(self.parameters), vendor_tool=self.vendor_tool)


class ToolRegistry:
    """The tools of a round, in the order of their descriptions.

    The session layer adds ``ask_user`` with :meth:`register`.
    """

    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        for t in tools:
            self.register(t)

    def register(self, tool: Tool, *, replace: bool = False) -> None:
        """Add ``tool``; a second tool of the same name requires ``replace``. """
        if tool.name in self._tools and not replace:
            raise ValueError(f"tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove the tool ``name`` (no error when absent). """
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """The tool ``name``, or ``None``. """
        return self._tools.get(name)

    def names(self) -> list[str]:
        """The tool names in order (descriptions sent with every request)."""
        return list(self._tools)

    def specs(self) -> list[ToolSpec]:
        """The descriptions sent with every request."""
        return [t.spec for t in self._tools.values()]

    def for_helpers(self) -> "ToolRegistry":
        """The tools of a helper agent: those with ``helper_allowed`` (no delegation)."""
        return ToolRegistry(t for t in self._tools.values() if t.helper_allowed)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# -- paths ------------------------------------------------------------------------------------


class PathError(ValueError):
    """A path leaves the working directory or is malformed."""


def resolve_in_workspace(workspace: Path, rel: Any) -> Path:
    """Resolve ``rel`` inside ``workspace``; refuse any path that leaves it.

    Refused: a non-string or empty path, a NUL character, an absolute POSIX or Windows path, a
    home-folder path (``~``), and any path whose resolution, following symbolic links, lies
    outside the working directory (``..`` escapes, links to outside folders), and an existing
    regular file with more than one hard link, because a hard link made by a program can give a
    file outside the working directory a name inside it.
    """
    if not isinstance(rel, str) or not rel.strip():
        raise PathError("the path must be a non-empty text relative to the working directory")
    if "\x00" in rel:
        raise PathError("the path contains a NUL character")
    if PurePosixPath(rel).is_absolute() or PureWindowsPath(rel).is_absolute() or PureWindowsPath(rel).drive:
        raise PathError(f"absolute paths are not permitted ({rel!r}); give a path relative to the working directory")
    if rel.startswith("~"):
        raise PathError(f"home-folder paths are not permitted ({rel!r})")
    root = workspace.resolve()
    target = (root / rel).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError:
        raise PathError(f"the path {rel!r} leads outside the working directory") from None
    try:
        st = target.stat()
    except OSError:
        return target
    if target.is_file() and st.st_nlink > 1:
        raise PathError(f"the file {rel!r} has {st.st_nlink} hard links; files with several names are not permitted")
    return target


def _rel(ctx: ToolContext, p: Path) -> str:
    rel = p.relative_to(ctx.workspace.resolve()).as_posix()
    return rel or "."


def _str_arg(args: Mapping[str, Any], key: str, *, required: bool = True, default: str | None = None) -> str | None:
    v = args.get(key, default)
    if v is None:
        if required:
            raise ValueError(f"the argument '{key}' is required")
        return None
    if not isinstance(v, str):
        raise ValueError(f"the argument '{key}' must be a text")
    return v


def _int_arg(args: Mapping[str, Any], key: str, default: int | None) -> int | None:
    v = args.get(key, default)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValueError(f"the argument '{key}' must be a non-negative integer")
    return v


# -- built-in tools ---------------------------------------------------------------------------


def _read_file(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
    """read_file: the text of a file in the working directory."""
    p = resolve_in_workspace(ctx.workspace, _str_arg(args, "path"))
    offset = _int_arg(args, "offset", 0) or 0
    if not p.is_file():
        return ToolOutcome(f"{_rel(ctx, p)} is not a file", is_error=True)
    text = p.read_bytes().decode("utf-8", errors="replace")
    part = text[offset:]
    note = f"[{_rel(ctx, p)}: {len(text)} characters" + (f"; from character {offset}]" if offset else "]")
    return ToolOutcome(f"{note}\n{part}", details={"path": _rel(ctx, p), "chars": len(text), "offset": offset})


def _write_file(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
    """write_file: create or replace a text file in the working directory."""
    p = resolve_in_workspace(ctx.workspace, _str_arg(args, "path"))
    content = _str_arg(args, "content")
    assert content is not None
    if p.is_dir():
        return ToolOutcome(f"{_rel(ctx, p)} is a folder", is_error=True)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Resolve again after creating the folders: a folder link created meanwhile cannot redirect the write.
    p = resolve_in_workspace(ctx.workspace, _rel(ctx, p))
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)
    return ToolOutcome(f"Wrote {len(content)} characters to {_rel(ctx, p)}.", details={"path": _rel(ctx, p), "chars": len(content)})


_LIST_MAX_ENTRIES = 2000


def _list_files(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
    """list_files: the files and folders under a folder of the working directory.

    Symbolic links are listed and not followed.
    """
    p = resolve_in_workspace(ctx.workspace, _str_arg(args, "path", required=False, default=".") or ".")
    if not p.is_dir():
        return ToolOutcome(f"{_rel(ctx, p)} is not a folder", is_error=True)
    lines: list[str] = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(p, followlinks=False):
        dirnames.sort()
        base = Path(dirpath)
        for name in dirnames:
            entry = base / name
            total += 1
            if len(lines) < _LIST_MAX_ENTRIES:
                suffix = " (symbolic link, not followed)" if entry.is_symlink() else "/"
                lines.append(_rel(ctx, entry.parent.resolve() / entry.name) + suffix)
        for name in sorted(filenames):
            entry = base / name
            total += 1
            if len(lines) < _LIST_MAX_ENTRIES:
                rel = _rel(ctx, entry.parent.resolve() / entry.name)
                if entry.is_symlink():
                    lines.append(f"{rel} (symbolic link)")
                else:
                    try:
                        lines.append(f"{rel}  {entry.stat().st_size} bytes")
                    except OSError:
                        lines.append(rel)
    head = f"[{_rel(ctx, p)}: {total} entries" + (f"; the first {_LIST_MAX_ENTRIES} are shown]" if total > len(lines) else "]")
    return ToolOutcome("\n".join([head, *lines]), details={"path": _rel(ctx, p), "entries": total})


def _run_shell(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
    """run_shell: one command in the working directory, limit min(shell.limit_s, remaining time)."""
    command = _str_arg(args, "command")
    assert command is not None
    reason = ctx.policy.check(command)
    if reason is not None:
        return ToolOutcome(f"Command refused by the {reason}.", is_error=True, denied=True, details={"reason": reason})
    remaining = ctx.tracker.remaining().seconds
    timeout = min(ctx.config.shell.limit_s, remaining)
    if not timeout > 0:
        return ToolOutcome("Command not executed: no execution time remains in the round.", is_error=True)
    result = run_command(
        command,
        cwd=ctx.workspace,
        env=ctx.env,
        timeout_s=timeout,
        record_cap_chars=ctx.config.output.record_cap_chars,
    )
    details = {k: v for k, v in result.to_dict().items() if k not in ("stdout", "stderr")}
    return ToolOutcome(result.text(), is_error=result.timed_out or result.exit_code != 0, details=details)


def _web_fetch(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
    """web_fetch: the text of a web resource."""
    url = _str_arg(args, "url")
    assert url is not None
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return ToolOutcome("Only http and https addresses can be fetched.", is_error=True)
    web = ctx.config.web
    for s in (web.denied_url_substrings if web else ()):
        if s.lower() in url.lower():
            return ToolOutcome(
                "Request refused: this address may hold withheld evaluation data.",
                is_error=True,
                denied=True,
                details={"reason": f"denied URL substring {s!r}"},
            )
    if ctx.web.fetch is None:
        return ToolOutcome("web_fetch is unavailable: no web backend is configured for this run.", is_error=True, details={"unavailable": True})
    timeout = min(ctx.config.shell.limit_s, ctx.tracker.remaining().seconds)
    if not timeout > 0:
        return ToolOutcome("Not executed: no execution time remains in the round.", is_error=True)
    text = ctx.web.fetch(url, timeout)
    cap = web.max_fetch_chars if web else len(text)
    return ToolOutcome(text[:cap] + (f"\n[... truncated at {cap} characters]" if len(text) > cap else ""), details={"url": url, "chars": len(text)})


def _web_search(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
    """web_search as a function tool: a list of search results from an injected backend.

    With a vendor whose adapter offers its built-in web search tool, the vendor executes the
    searches and this handler is never called. With any other provider (the scripted agent, a
    vendor without such a tool in its adapter) the tool is an ordinary function tool; without an
    injected backend it reports that it is unavailable.
    """
    query = _str_arg(args, "query")
    assert query is not None
    if ctx.web.search is None:
        return ToolOutcome("web_search is unavailable: this run has no web search.", is_error=True, details={"unavailable": True})
    timeout = min(ctx.config.shell.limit_s, ctx.tracker.remaining().seconds)
    if not timeout > 0:
        return ToolOutcome("Not executed: no execution time remains in the round.", is_error=True)
    return ToolOutcome(ctx.web.search(query, timeout), details={"query": query, "timeout_s": timeout})


REQUIREMENT_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(\[[A-Za-z0-9._,-]+\])?"
    r"(\s*(==|>=|<=|~=|!=|<|>)\s*[A-Za-z0-9.*+!_-]+(\s*,\s*(==|>=|<=|~=|!=|<|>)\s*[A-Za-z0-9.*+!_-]+)*)?$"
)
"""An accepted requirement for ``install_package``: a distribution name with optional extras and
version specifiers (PEP 508 subset); options, URLs and paths are refused."""


def default_pip_runner(ctx: ToolContext) -> PipRunner:
    """``pip install`` into the run environment's interpreter."""

    def run(requirement: str, timeout_s: float) -> ShellResult:
        exe = ctx.python_executable or sys.executable
        return run_command(
            [exe, "-m", "pip", "install", "--disable-pip-version-check", requirement],
            cwd=ctx.workspace,
            env=ctx.env,
            timeout_s=timeout_s,
            record_cap_chars=ctx.config.output.record_cap_chars,
        )

    return run


def _install_package(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
    """install_package: install one package into the run environment (open)."""
    req = (_str_arg(args, "requirement") or "").strip()
    if not REQUIREMENT_PATTERN.match(req):
        return ToolOutcome(
            f"Refused: {req!r} is not a package name with optional version specifiers (for example 'pysindy==1.7.5').",
            is_error=True,
            denied=True,
            details={"reason": "malformed requirement"},
        )
    timeout = min(ctx.config.shell.limit_s, ctx.tracker.remaining().seconds)
    if not timeout > 0:
        return ToolOutcome("Not executed: no execution time remains in the round.", is_error=True)
    runner = ctx.pip_runner or default_pip_runner(ctx)
    result = runner(req, timeout)
    details = {"requirement": req, **{k: v for k, v in result.to_dict().items() if k not in ("stdout", "stderr")}}
    return ToolOutcome(result.text(), is_error=result.timed_out or result.exit_code != 0, details=details)


def _start_helper(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
    """start_helper: run a helper agent on a subtask."""
    task = _str_arg(args, "task")
    assert task is not None
    max_turns = _int_arg(args, "max_turns", None)
    if ctx.helper_runner is None:
        return ToolOutcome("start_helper is unavailable here: helper agents cannot start further helpers.", is_error=True, denied=True)
    return ctx.helper_runner(task, max_turns)


def _schema(props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


RUN_SHELL_DESCRIPTION = (
    "Run one shell command in the working directory, for example 'python fit.py'. {shell} The command is "
    "ended, with every process it started, after {limit} s or when the round's remaining execution time "
    "is used, whichever comes first; processes started in the background end when the command "
    "finishes. Paths must stay inside the working directory."
)
"""Description of ``run_shell``; ``{limit}`` is the ``shell.limit_s`` of the tool configuration
(the limit is min(limit_s, remaining round time)); ``{shell}`` is
:func:`shell_sentence`, the shell that interprets the command on this computer."""


def shell_sentence(platform: str | None = None) -> str:
    """The sentence of the ``run_shell`` description that names the shell.

    Commands are started with ``subprocess`` and ``shell=True`` (:func:`aspire_sysid.agent.shell.run_command`):
    ``cmd.exe`` on Windows, ``/bin/sh`` elsewhere. Without the sentence, the agent learned the
    shell from its first failed POSIX command on Windows.
    """
    if (platform or sys.platform) == "win32":
        return "Commands run in the Windows command interpreter cmd.exe, not in a POSIX shell."
    return "Commands run in the POSIX shell /bin/sh."


def _seconds_text(x: float) -> str:
    return str(int(x)) if float(x) == int(x) else f"{x:g}"


BUILTIN_TOOLS: dict[str, Tool] = {
    "read_file": Tool(
        "read_file",
        "Read a text file in the working directory. The path is relative to the working directory. "
        "A long file is shortened in the reply; use 'offset' (a character position) to read further.",
        _schema({"path": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}}, ["path"]),
        _read_file,
    ),
    "write_file": Tool(
        "write_file",
        "Create or replace a text file in the working directory. The path is relative to the working "
        "directory; missing folders are created.",
        _schema({"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
        _write_file,
    ),
    "list_files": Tool(
        "list_files",
        "List the files and folders under a folder of the working directory (default: the working directory).",
        _schema({"path": {"type": "string"}}, []),
        _list_files,
    ),
    "run_shell": Tool(
        "run_shell",
        RUN_SHELL_DESCRIPTION.format(limit="600", shell=shell_sentence()),
        _schema({"command": {"type": "string"}}, ["command"]),
        _run_shell,
    ),
    "web_fetch": Tool(
        "web_fetch",
        "Fetch the text of a web resource (http or https address).",
        _schema({"url": {"type": "string"}}, ["url"]),
        _web_fetch,
    ),
    "web_search": Tool(
        "web_search",
        "Search the web and return a list of results.",
        _schema({"query": {"type": "string"}}, ["query"]),
        _web_search,
        vendor_tool="web_search",
    ),
    "install_package": Tool(
        "install_package",
        "Install one Python package into the run environment with pip, for example 'pysindy' or "
        "'pysindy==1.7.5'.",
        _schema({"requirement": {"type": "string"}}, ["requirement"]),
        _install_package,
    ),
    "start_helper": Tool(
        "start_helper",
        "Start a helper agent on a subtask. The helper has the same tools except start_helper, works in "
        "the same working directory, and returns its final reply. Its turns and cost count toward your "
        "budget. 'max_turns' limits its turns (optional).",
        _schema({"task": {"type": "string"}, "max_turns": {"type": "integer", "minimum": 1}}, ["task"]),
        _start_helper,
        helper_allowed=False,
    ),
}
"""The built-in tools of the harness, by name."""


def build_registry(config: ToolConfig) -> ToolRegistry:
    """The registry of the tools of ``config``, in its order. The session layer adds ``ask_user``."""
    tools = []
    for name in config.tools:
        tool = BUILTIN_TOOLS[name]
        if name == "run_shell":
            tool = replace(tool, description=RUN_SHELL_DESCRIPTION.format(limit=_seconds_text(config.shell.limit_s),
                                                                          shell=shell_sentence()))
        tools.append(tool)
    return ToolRegistry(tools)


def make_context(
    *,
    workspace: Path,
    config: ToolConfig,
    clock: ExecutionClock,
    tracker: BudgetTracker,
    emit: Callable[..., None],
    task_dir: Path | None,
    python_executable: str | None = None,
    web: WebBackends | None = None,
    pip_runner: PipRunner | None = None,
    base_env: Mapping[str, str] | None = None,
) -> ToolContext:
    """The tool context of the main agent of a round: policy and shell environment."""
    python_executable = python_executable or sys.executable
    policy = ShellPolicy.for_run(
        workspace,
        task_dir=task_dir,
        network_filter=False,
        allowed_path_prefixes=config.shell.allowed_path_prefixes,
        python_executable=python_executable,
    )
    env = shell_environment(
        network_filter=False,
        python_executable=python_executable,
        base=base_env,
        workspace=workspace,
    )
    return ToolContext(
        workspace=Path(workspace).resolve(),
        config=config,
        policy=policy,
        env=env,
        clock=clock,
        tracker=tracker,
        emit=emit,
        python_executable=python_executable,
        web=web or WebBackends(),
        pip_runner=pip_runner,
    )
