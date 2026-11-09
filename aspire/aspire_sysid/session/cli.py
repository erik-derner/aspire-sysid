"""The subcommand ``aspire session``: an interactive session on the terminal.

    aspire session <task-dir> --model <id> --out <dir>
                   [--python EXE] [--allow-harness-interpreter] [--workspace-root DIR]
                   [--no-plots] [--no-reexec] [--user NAME]

The harness runs round 1, shows the complete evaluation report after each round on the terminal
and offers the choices of interactive operation: an analysis request, a new identification round with
feedback (and task changes), or the end of the session. The agent's questions (``ask_user``) are
asked on the terminal.

**Record**. ``<dir>`` is a run folder (:mod:`aspire_sysid.record`): ``transcript.jsonl``
(the transcript of every event, session events included), ``pools/v<k>/`` per pool version (the
snapshot of ``models/`` with ``snapshot.json``, and the session's ``recommendation.json`` and
``agent_results.json``/``.txt``), ``evaluation/v<k>/`` (the complete reports), ``run_record.json``
and ``provenance.json`` (written at the end of the session), ``session.json`` (the session record)
and ``workspace/`` (a copy of the final working directory). ``aspire record verify <dir>
--pool-version k`` and ``aspire export <dir>`` work on it.

**Isolation** (the measures of the experiment runner). The agent's working
directory is created under ``--workspace-root`` (default ``<system temporary folder>/aspire-sessions``),
which must lie outside every git repository (:func:`aspire_sysid.experiment.workspace.check_workspace_root`)
and outside the record. The interpreter of the agent's shell is ``--python`` (default: the harness's
own); with a real model the session is refused when the harness package can be imported from it,
unless ``--allow-harness-interpreter`` is given (create an environment with ``aspire experiment
agent-env <folder>``). The shell environment is derived as for the runs of an experiment
(:func:`aspire_sysid.experiment.runner.agent_base_environment`); the
agent's package installations go to a package folder of the session, next to the working
directory. The API key is handled as in the experiment runner
(:func:`aspire_sysid.experiment.credentials.take_api_key`): a key found in the environment is removed
from the harness process's environment before any agent command runs, a key from a ``.env`` file is
never put into it, and the key reaches only the provider object (``make_provider(model,
api_key=...)``); it is never printed or recorded, and the agent's shell environment never contains it.
The remaining risk stated in aspire/README.md (a key in the environment of the starting shell stays
readable in ``/proc/<pid>/environ``; the harness's memory) applies to sessions as well.

**Re-execution** (real models, POSIX). The harness process is the parent of every command of the
agent, and a command can read ``/proc/$PPID/environ``, ``/proc/$PPID/cmdline`` and
``/proc/$PPID/cwd``. The first two show the environment and the command line with which the process
*started*; removing the key from ``os.environ`` later does not change them. Therefore, after the key
has been taken (and before any subprocess starts), ``aspire session`` replaces its own process
image with ``os.execve``: the new image starts with an environment without any API key variable
(``PWD`` set to the workspace root, ``OLDPWD`` removed), with the workspace root as its working
directory, and with a bootstrap command line ``python -c <code>`` that contains no path; the key,
the arguments (with the task and record paths) and ``sys.path`` reach it through an inherited
pipe in the form of the experiment command's relaunch (``{variable: key}``, received with
:func:`~aspire_sysid.experiment.credentials.accept_passed_keys` and taken with ``take_api_key``). The
run record states the key's original source (``environment`` or ``dotenv``) and the re-execution
(``extra.api_key``). ``SIGTERM`` and ``SIGHUP`` end the session through ``SystemExit`` (see
:func:`_install_termination_handlers`), so that a running agent command is ended with its tree. ``--no-reexec`` disables it with a warning; on Windows it is not available.
Remaining channels: ``/proc/$PPID/fd`` lists the files the process holds open, among them the
transcript in the record folder, and the agent can read the memory of the process where the system
permits it; the parent of the harness process (the user's shell) keeps its own command line and
working directory. Only a separate operating-system user for the agent's commands closes these.

The model identifier must be one that the harness accepts (a dated snapshot, or an identifier listed
in ``aspire/configs/models.yaml`` for a model without one) and must have a verified price.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

__all__ = ["register", "run_session_command"]


_SOURCE_TEXT = {"environment": "the environment", "launcher": "the launching process"}

REEXEC_MAX_PAYLOAD = 60_000
"""Largest payload (bytes) handed to the re-executed process through the pipe; the pipe buffer of
Linux holds 64 KiB, and the payload is written before the new process image reads it."""


def _import_factory(spec: Any) -> Callable[..., Any]:
    if callable(spec):
        return spec
    module, _, name = str(spec).partition(":")
    import importlib

    return getattr(importlib.import_module(module), name)


def _reexec(args: argparse.Namespace, *, api_key: str, key_source: str, cwd: Path, provider_factory: Any) -> None:
    """Replace this process by a new Python image that runs the session (module docstring,
    "Re-execution"). Does not return. The key, the arguments (paths included) and ``sys.path`` go
    through an inherited pipe; the new image's environment has no API key variable and ``PWD`` is
    the neutral folder ``cwd``; its command line is a bootstrap without paths. """
    import json
    import os

    from ..agent.providers import vendor_of
    from ..experiment.credentials import KEY_VARIABLES

    payload = {
        "sys_path": [p for p in sys.path if p],
        "args": {k: v for k, v in vars(args).items() if k not in ("handler",) and not k.startswith("_")},
        # the same form as the experiment command's relaunch (variable name -> key), accepted in the new image
        # by aspire_sysid.experiment.credentials.accept_passed_keys
        "passed_keys": {KEY_VARIABLES[vendor_of(args.model)]: api_key},
        "key_source": key_source,
        "cwd": str(cwd),
        "provider_factory": provider_factory if isinstance(provider_factory, str) else None,
    }
    data = json.dumps(payload).encode("utf-8")
    if len(data) > REEXEC_MAX_PAYLOAD:
        raise RuntimeError(f"the re-execution payload has {len(data)} bytes, more than {REEXEC_MAX_PAYLOAD}")
    r, w = os.pipe()
    os.set_inheritable(r, True)
    view = memoryview(data)
    while view:
        n = os.write(w, view)
        view = view[n:]
    os.close(w)
    env = {k: v for k, v in os.environ.items() if k not in KEY_VARIABLES.values() and k != "OLDPWD"}
    env["PWD"] = str(cwd)
    boot = (f"import json,os,sys;d=json.loads(os.fdopen({r},'rb').read());sys.path[:0]=d['sys_path'];"
            "from aspire_sysid.session.cli import child_entry;sys.exit(child_entry(d))")
    os.chdir(cwd)
    sys.stdout.flush()
    sys.stderr.flush()
    os.execve(sys.executable, [sys.executable, "-c", boot], env)


def _on_termination_signal(signum: int, frame: Any) -> None:
    from ..agent.shell import request_termination

    request_termination(signum)  # SystemExit now, or after the command's start or cleanup section


def _restore_handlers(previous: dict[Any, Any]) -> None:
    import signal

    for sig, handler in previous.items():
        try:
            signal.signal(sig, handler)
        except (ValueError, TypeError):
            pass


def _install_termination_handlers() -> dict[Any, Any]:
    """End the session on ``SIGTERM`` and ``SIGHUP`` with ``SystemExit`` instead of the default
    immediate death, so that the running agent command and its process tree are ended by
    :func:`aspire_sysid.agent.shell.run_command` (its termination-deferred sections) and the
    transcript keeps every event written so far.  Not on Windows, where the job object of each command ends it."""
    import signal

    previous: dict[Any, Any] = {}
    if sys.platform == "win32":
        return previous
    for name in ("SIGTERM", "SIGHUP"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                previous[sig] = signal.signal(sig, _on_termination_signal)
            except ValueError:  # not the main thread (tests calling the command from a thread)
                pass
    return previous


def child_entry(payload: dict[str, Any]) -> int:
    """Entry point of the re-executed session process (module docstring, "Re-execution"). """
    args = argparse.Namespace(**payload["args"])
    return run_session_command(args, provider_factory=payload.get("provider_factory"), _child=payload)


def run_session_command(
    args: argparse.Namespace,
    *,
    provider: Any = None,
    provider_factory: Any = None,
    channel: Any = None,
    probe: Any = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    interview_clock: Any = None,
    session_factory: Callable[..., Any] | None = None,
    _child: dict[str, Any] | None = None,
    **session_kwargs: Any,
) -> int:
    """Run ``aspire session`` (module docstring).

    ``provider`` injects a provider object (tests; not a real model: no API key, the interpreter
    check is informative only). ``provider_factory`` (a callable or ``"module:function"``, called as
    ``factory(model_id, api_key=key)``) replaces :func:`~aspire_sysid.agent.providers.make_provider`
    on the real-model path, including the re-execution (tests). ``_child`` is the payload of the
    re-executed process.

    Returns 0 after a session that ended normally, 2 for an invalid task, configuration, model,
    interpreter, workspace root, missing API key or session folder.
    """
    import tempfile

    from ..agent.config import ToolConfigError, load_tool_config
    from ..agent.probe import probe_environment
    from ..agent.providers import ModelIdError, check_pinned_model_id, default_model_id, make_provider, vendor_of
    from ..agent.tools import WebBackends
    from ..experiment.agentenv import default_agent_env_dir, inspect_agent_interpreter, venv_python
    from ..experiment.credentials import MissingKeyError, accept_passed_keys, take_api_key
    from ..experiment.workspace import WorkspaceRootError, check_workspace_root
    from ..task import TaskError, load_task
    from .channel import TerminalChannel, TerminalProgress
    from .session import Session

    if getattr(args, "web", False) and channel is None:  # the same session in the browser (aspire_sysid.web)
        from ..web.server import serve_session

        options = {k: v for k, v in (("provider", provider), ("provider_factory", provider_factory), ("probe", probe),
                                     ("interview_clock", interview_clock), ("session_factory", session_factory)) if v is not None}
        return serve_session(args, **options, **session_kwargs)
    out = stdout or sys.stdout
    # a session starts from a task folder, or from data files, for which an interview agent first
    # prepares the task definition with the user (aspire_sysid.session.interview)
    from .interview import Interview, InterviewError, create_task_stub, default_task_dir, load_task_stub

    stub = None
    task = None
    try:
        if getattr(args, "train", None):
            if getattr(args, "task_dir", None):
                print("error: name a task folder, or give data files with --train (and --new-task for the folder of the "
                      "new task), not both", file=sys.stderr)
                return 2
            stub = create_task_stub(getattr(args, "new_task", None) or default_task_dir(), args.train,
                                    getattr(args, "val", None), expand_files(getattr(args, "held_out", None) or ()))
            # from here on the task folder exists; a re-executed process continues with it
            args.task_dir, args.interview = str(stub.task_dir), True
            args.train = args.val = args.held_out = args.new_task = None
            out.write(f"new task folder {stub.task_dir}: the data files were copied into it (the originals are unchanged)\n")
        elif getattr(args, "interview", False):
            stub = load_task_stub(args.task_dir)
        elif not getattr(args, "task_dir", None):
            print("error: name a task folder, or give the training data with --train <file>", file=sys.stderr)
            return 2
        elif getattr(args, "val", None) or getattr(args, "held_out", None) or getattr(args, "new_task", None):
            print("error: --val, --test and --new-task belong to --train; a task folder already names its data", file=sys.stderr)
            return 2
    except InterviewError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if stub is None:
        try:
            task = load_task(args.task_dir)
        except TaskError as exc:
            print(f"invalid task: {exc}", file=sys.stderr)
            return 2
    task_id = stub.task_id if stub is not None else task.id
    try:
        config = load_tool_config()
    except ToolConfigError as exc:
        print(f"invalid tool configuration: {exc}", file=sys.stderr)
        return 2
    if not getattr(args, "model", None):  # the model of the project (configs/models.yaml)
        try:
            args.model = default_model_id()
        except ModelIdError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if not getattr(args, "out", None):
        args.out = str(default_session_dir(task_id))
    out_dir = Path(args.out).resolve()
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        print(f"error: the session folder {out_dir} exists and is not empty; earlier results are never overwritten", file=sys.stderr)
        return 2
    root = Path(getattr(args, "workspace_root", None) or Path(tempfile.gettempdir()) / "aspire-sessions")
    try:
        root = check_workspace_root(root)
    except WorkspaceRootError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    python = getattr(args, "python", None)
    looked_for: Path | None = None
    if not python:  # the agent's environment at its default place, when it exists; otherwise the harness's interpreter
        candidate = venv_python(default_agent_env_dir())
        if candidate.is_file():
            python = str(candidate)
        else:
            python, looked_for = sys.executable, candidate
        args.python = python
    real = provider is None
    key: str | None = None
    source = "not needed (injected provider)"
    reexec_note: dict[str, Any] = {"reexecuted": False}
    if real:
        # a floating alias is refused before a key is looked up
        try:
            check_pinned_model_id(args.model)
        except ValueError as exc:
            print(f"error: cannot use the model {args.model!r}: {exc}", file=sys.stderr)
            return 2
        # the key is taken before any subprocess starts, so that none inherits it (key handling of the experiment runner)
        if _child is not None:
            # the key arrived through the pipe; the key helpers keep it out of the environment
            accept_passed_keys(_child.pop("passed_keys", {}) or {})
            try:
                key, _via = take_api_key(vendor_of(args.model))  # "launcher": from the pipe
            except (MissingKeyError, ValueError) as exc:
                print(f"error: cannot use the model {args.model!r}: {exc}", file=sys.stderr)
                return 2
            source = _child["key_source"]
            reexec_note = {"reexecuted": True, "working_directory": _child["cwd"],
                           "note": "the process that parents the agent's commands was started without an API key variable, "
                                   "with a neutral working directory and without paths on its command line"}
        else:
            try:
                key, source = take_api_key(vendor_of(args.model))  # removed from os.environ when found there
            except (MissingKeyError, ValueError) as exc:
                print(f"error: cannot use the model {args.model!r}: {exc}", file=sys.stderr)
                return 2
            if not getattr(args, "no_reexec", False) and sys.platform != "win32":
                root.mkdir(parents=True, exist_ok=True)
                for name in ("task_dir", "out", "workspace_root", "python"):  # data files are already in the task folder
                    if getattr(args, name, None):
                        setattr(args, name, str(Path(getattr(args, name)).resolve()) if name != "python" else getattr(args, name))
                args.workspace_root = str(root)
                args.out = str(out_dir)
                _reexec(args, api_key=key, key_source=source, cwd=root, provider_factory=provider_factory)
            why = "--no-reexec was given" if getattr(args, "no_reexec", False) else "re-execution is not supported on Windows"
            print(
                f"warning: {why}; this process parents the agent's commands, so its /proc/<pid>/cmdline and cwd (paths of the "
                "task and the record)"
                + (", and its /proc/<pid>/environ with the API key taken from the environment," if source == "environment" else "")
                + " are readable by them",
                file=sys.stderr,
            )
            reexec_note = {"reexecuted": False, "reason": why}
    interpreter = inspect_agent_interpreter(python)
    out.write(f"agent interpreter {interpreter.executable}: Python {interpreter.python_version}; "
              f"harness importable: {interpreter.harness_importable}\n")
    if not interpreter.runs:
        print(f"error: the agent's interpreter does not run: {interpreter.error}", file=sys.stderr)
        return 2
    if real and interpreter.harness_importable and not getattr(args, "allow_harness_interpreter", False):
        if looked_for is not None:
            print(f"error: no environment for the agent's commands was found ({looked_for} does not exist), and the harness's own "
                  "interpreter is not used for them, because the harness package can be imported from it. Create the "
                  "environment once with `aspire experiment agent-env` (no argument; it installs the numerical packages and "
                  "takes a few minutes), then start the session again.", file=sys.stderr)
            return 2
        print("error: the harness package can be imported from the agent's interpreter; create a separate environment with "
              "`aspire experiment agent-env <folder>` and pass it with --python, or pass --allow-harness-interpreter.", file=sys.stderr)
        return 2
    web = session_kwargs.pop("web", None)
    if real:
        try:
            factory_fn = _import_factory(provider_factory) if provider_factory is not None else make_provider
            provider = factory_fn(args.model, api_key=key)
        except (ValueError, ImportError, RuntimeError, AttributeError) as exc:
            print(f"error: cannot use the model {args.model!r}: {exc}", file=sys.stderr)
            return 2
        finally:
            key = None
        out.write(f"API key: from {_SOURCE_TEXT.get(source, 'a .env file')}\n")
        if web is None:
            from ..experiment.web import real_web_backends

            web = real_web_backends()
    if web is None:
        web = WebBackends()
    if probe is None:
        probe = probe_environment(python)
    if channel is None:
        channel = TerminalChannel(stdin or sys.stdin, out, user=getattr(args, "user", None) or "the user")
        session_kwargs.setdefault("sink", TerminalProgress(out))  # one line per response of the agent
    out.write(f"model {args.model}; session record {out_dir}\n")
    if stub is not None:
        progress = session_kwargs.get("sink")
        if isinstance(progress, TerminalProgress):
            progress.exchange_text = TerminalProgress.INTERVIEW_TEXT
        interview = Interview(
            stub, provider, config, channel, sink=progress, probe=probe, python_executable=python, web=web,
            workspace_root=root, isolate_environment=True, price_table=session_kwargs.get("price_table"),
            clock=interview_clock, fsync=session_kwargs.get("fsync", True),
        )
        previous = _install_termination_handlers()
        try:
            prepared = interview.run()
        finally:
            _restore_handlers(previous)
        if isinstance(progress, TerminalProgress):
            progress.exchange_text = TerminalProgress.ANALYSIS_TEXT
        out.write(f"\nPreparation of the task: {prepared.turns} turns, {prepared.elapsed_s:.0f} s of execution time, "
                  f"{prepared.cost_usd:.2f} USD. Task folder: {stub.task_dir} (record of the preparation in interview/)\n")
        if prepared.outcome != "accepted":
            out.write(f"The identification was not started: {prepared.detail or prepared.outcome}.\n")
            return 0 if prepared.outcome == "stopped" else 1
        try:
            task = load_task(stub.task_dir)
        except TaskError as exc:
            print(f"invalid task: {exc}", file=sys.stderr)
            return 2
    scored = task.column(task.output)
    if isinstance(channel, TerminalChannel) and channel.output is None:
        channel.output = (scored.name, scored.unit)
    factory = session_factory or Session
    key_record: Any = (
        {"status": "received by the provider object", "source": source if source in _SOURCE_TEXT else "dotenv", **reexec_note}
        if real else "not needed (injected provider)"
    )
    session = factory(
        task,
        provider,
        config,
        channel,
        out_dir,
        probe=probe,
        python_executable=python,
        plots=not getattr(args, "no_plots", False),
        workspace_root=root,
        isolate_environment=True,
        web=web,
        extra_record={"agent_interpreter": interpreter.to_dict(), "operation": "interactive", "command": "aspire session",
                      "api_key": key_record},
        **session_kwargs,
    )
    previous = _install_termination_handlers()
    try:
        result = session.run()
    finally:
        _restore_handlers(previous)
    out.write(
        f"\nSession ended ({result.reason}). Completed pool versions: "
        f"{', '.join(str(v) for v in result.completed_pool_versions) or 'none'}. Record: {out_dir} "
        "(run_record.json, session.json, transcript.jsonl)\n"
    )
    index = getattr(session, "report_index", None)
    if index is not None:
        out.write(f"Report of the session (open in a browser): {Path(index).as_uri()}\n")
    elif getattr(session, "report_error", None):
        out.write(f"The HTML report could not be written ({session.report_error}); the record is complete.\n")
    return 0


def expand_files(patterns: Any) -> list[str]:
    """The files named by ``patterns``: a pattern with ``*``, ``?`` or ``[`` is expanded by the harness
    (PowerShell and cmd.exe pass it unchanged) and its files are put in natural order, so that
    ``part_2.csv`` precedes ``part_10.csv``; any other entry is kept. Raises
    :class:`~aspire_sysid.task.stub.InterviewError` when a pattern names no file."""
    import glob
    import re

    from ..task.stub import InterviewError

    def natural(name: str) -> list[Any]:
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]

    out: list[str] = []
    for pattern in patterns:
        text = str(pattern)
        if any(ch in text for ch in "*?["):
            found = sorted(glob.glob(text), key=natural)
            if not found:
                raise InterviewError(f"the pattern {text} names no file")
            out += found
        else:
            out.append(text)
    return out


def default_session_dir(task_id: str, base: str | Path | None = None, today: str | None = None) -> Path:
    """The record folder of a session when ``--out`` is not given: ``sessions/<task>-<date>-<n>``
    under the current directory, with the date as YYYYMMDD and ``n`` the first number from 01 for
    which no folder exists (earlier results are never overwritten)."""
    import datetime as _dt

    root = Path(base) if base is not None else Path.cwd() / "sessions"
    day = today or _dt.date.today().strftime("%Y%m%d")
    n = 1
    while (root / f"{task_id}-{day}-{n:02d}").exists():
        n += 1
    return root / f"{task_id}-{day}-{n:02d}"


def register(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register ``aspire session``."""
    p = sub.add_parser(
        "session",
        help="run an interactive session (rounds, questions, analysis requests) on the terminal",
        description=(
            "Run an interactive session. Start it from a task folder, or from data files with --train "
            "(and optionally --val and --test): an agent then prepares the task definition with you first. "
            "In the session the agent identifies models in rounds and may ask "
            "questions. While the agent works, one line per response is printed; after each round the results "
            "are shown as a short table and as an HTML page, and you choose an analysis request, a new round with "
            "feedback, or the end of the session. The session folder is a run folder (aspire record verify, "
            "aspire export) with the HTML report in its folder report/."
        ),
    )
    p.add_argument("task_dir", nargs="?", default=None, help="task folder containing task.yaml; omit it and give --train to "
                   "start from data files")
    p.add_argument("--train", default=None, help="training data (a CSV file with a header row), for a new task: an agent "
                   "prepares the task definition with you before the identification starts; the file is copied, not moved")
    p.add_argument("--val", default=None, help="validation data of the new task (optional; with --train)")
    p.add_argument("--test", dest="held_out", nargs="+", action="extend", default=None, metavar="FILE",
                   help="test data of the new task, one file per test trajectory (optional; with --train): several files or "
                   "a pattern such as data/held_out_*.csv, which the harness expands itself, so that the command is the same "
                   "in every shell; no agent can access them")
    p.add_argument("--new-task", default=None, help="folder of the new task, whose name is the task identifier (with --train; "
                   "default: tasks/task-<date>-<n> under the current directory)")
    p.add_argument("--model", default=None, help="model identifier (default: the model of the project, default_model of "
                   "aspire/configs/models.yaml)")
    p.add_argument("--out", default=None, help="session record folder (absent or empty), outside the workspace root "
                   "(default: sessions/<task>-<date>-<n> under the current directory)")
    p.add_argument("--python", default=None, help="interpreter of the agent's shell (default: the environment created by "
                   "`aspire experiment agent-env` at its default place, when it exists; otherwise the harness's interpreter)")
    p.add_argument("--allow-harness-interpreter", action="store_true",
                   help="accept an agent interpreter from which the harness package can be imported (real models only)")
    p.add_argument("--no-plots", action="store_true", help="do not draw the plots of the evaluation reports")
    p.add_argument("--no-reexec", action="store_true",
                   help="do not re-execute the session in a new process image without the API key and paths (real models; "
                   "prints a warning)")
    p.add_argument("--user", default=None, help="name of the user in the record of task changes (default: 'the user')")
    p.add_argument("--web", action="store_true", help="conduct the session in the browser instead of on the terminal (see `aspire web`)")
    p.add_argument("--port", type=int, default=0, help="with --web: port on 127.0.0.1 (default: a free port)")
    p.add_argument("--no-browser", action="store_true", help="with --web: do not open the browser; the address is printed")
    p.add_argument(
        "--workspace-root",
        default=None,
        help="folder under which the agent's working directory is created, outside every git repository and outside "
        "the session record (default: <system temporary folder>/aspire-sessions)",
    )
    p.set_defaults(handler=run_session_command)
