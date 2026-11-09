"""Protection of the grid runner against the agent's process-ending commands.

The grid runner runs under a renamed interpreter so that an agent command such as
``taskkill /IM python.exe`` cannot end it; such a command, issued by an agent, would otherwise
end a whole grid.

**Windows.** ``taskkill /IM <name>`` ends every process whose image name is ``<name>``. The
command ``aspire experiment run`` therefore re-launches itself under a copy of the interpreter
named :data:`HOST_EXE_NAME` (``aspire-host.exe``) in the interpreter's folder
(:func:`maybe_relaunch_under_host`); the run workers are started with the same interpreter
(``sys.executable``), so that no process of the grid has the image name ``python.exe``. The
original ``python.exe`` process only waits for the copy; if it is ended, the grid continues and
only the exit status on the console is lost. When the copy cannot be made, the grid runs
unprotected and a warning says so. In a virtual environment, ``Scripts/python.exe`` is a launcher
that starts the base interpreter as a child process whose image name is ``python.exe``; the
renamed interpreter is therefore a copy of the base interpreter with its DLLs, which runs in the
virtual environment through its ``pyvenv.cfg`` (:func:`host_interpreter`).

If the renamed copy cannot be started (for example, a security product blocks the unknown
executable), the grid runs under ``python.exe`` without this protection, and a warning says so;
the exit status of a failed start is never taken for the result of the grid.

**POSIX (Linux, macOS).** A renamed interpreter is not needed for the Windows case: every shell
command of the agent runs in its own process group, which the harness ends with the command
(:mod:`aspire_sysid.agent.shell`), and ``kill 0`` reaches only that group. The equivalent risk is
a command that ends processes by name or all processes of the user: ``pkill python``,
``killall python3``, ``kill -9 -1``. The command filter of the harness
(:func:`aspire_sysid.agent.policy.host_process_violation`) refuses such commands in the command
text: ``pkill`` and ``killall`` except with exact matching (``pkill -x``, ``killall -e``), a signal
and exact names other than the interpreter's or the harness's (so no pattern such as ``thon`` or
``.``, and no ``-f``, ``-v``, ``-u``, ``-P``, ``-g`` or ``-s``); all processes of the user (``kill
-1``, ``os.kill(-1, ...)``); the parent process or its group (``kill $PPID``, ``os.getppid`` with a
kill, ``os.killpg(os.getpgid(os.getppid), ...)``, also in the scripts a command names); and
finding and ending processes in one command (``pgrep python | xargs kill``, ``kill $(pgrep ...)``).

**Remaining gaps of the filter** (it reads command text only):

1. a process ended by its number in a separate command (``ps`` first, then ``kill 12345``);
2. a signal sent by a program or script to a process number it found itself (``os.kill(pid, ...)``,
   ``subprocess.run(["kill", ...])``, ``psutil``); scripts are read only for the parent-process and
   all-processes rules, and modules they import are not read;
3. a command whose text hides the words (variables, ``eval``, encodings);
4. on Windows, ``taskkill /PID`` with a number, and ``Stop-Process -Id``.

A worker or grid process ended this way leaves an unfinished run, which ``aspire experiment run
--resume`` detects and repeats (the workers end with the grid, :mod:`aspire_sysid.experiment.procs`);
only an operating-system sandbox or a separate user for the agent removes the risk.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Sequence

__all__ = [
    "HOST_EXE_NAME",
    "RELAUNCH_GUARD",
    "RelaunchDecision",
    "decide_relaunch",
    "host_interpreter",
    "venv_base_interpreter",
    "needs_relaunch",
    "maybe_relaunch_under_host",
    "worker_executable",
    "receive_relaunch_keys",
    "KEYS_ON_STDIN",
]

HOST_EXE_NAME = "aspire-host.exe"
"""Image name of the renamed interpreter on Windows."""

RELAUNCH_GUARD = "ASPIRE_HOST_RELAUNCHED"
"""Environment variable set in the re-launched process, so that it does not re-launch again."""

KEYS_ON_STDIN = "ASPIRE_HOST_KEYS_ON_STDIN"
"""Set in the re-launched process: the first line of its standard input holds the API keys as JSON."""


def receive_relaunch_keys(stdin: Any = None, environ: dict[str, str] | None = None) -> None:
    """In the re-launched process: read the API keys from the first line of standard input and keep
    them for :func:`aspire_sysid.experiment.credentials.take_api_key`. """
    env = os.environ if environ is None else environ
    if not env.get(KEYS_ON_STDIN):
        return
    from .credentials import accept_passed_keys

    line = (stdin or sys.stdin).readline()
    try:
        keys = json.loads(line) if line.strip() else {}
    except ValueError:
        keys = {}
    accept_passed_keys(keys if isinstance(keys, dict) else {})


@dataclass(frozen=True)
class RelaunchDecision:
    """Whether the grid runner re-launches itself, and why. """

    relaunch: bool
    reason: str


def decide_relaunch(platform: str | None = None, executable: str | None = None,
                    environ: dict[str, str] | None = None) -> RelaunchDecision:
    """Decide about the re-launch under :data:`HOST_EXE_NAME` (module docstring). """
    plat = platform or sys.platform
    env = os.environ if environ is None else environ
    if plat != "win32":
        return RelaunchDecision(False, "not Windows: agent commands run in their own process groups")
    if env.get(RELAUNCH_GUARD):
        return RelaunchDecision(False, "this process is the re-launched host")
    image = PureWindowsPath(executable or sys.executable).name.lower()
    if image == HOST_EXE_NAME:
        return RelaunchDecision(False, f"already running as {HOST_EXE_NAME}")
    return RelaunchDecision(True, f"running as {image}, which taskkill /IM {image} would end")


def needs_relaunch(platform: str | None = None, executable: str | None = None, environ: dict[str, str] | None = None) -> bool:
    """Whether the grid runner must re-launch itself under :data:`HOST_EXE_NAME`. """
    return decide_relaunch(platform, executable, environ).relaunch


def _same_file_content(a: Path, b: Path) -> bool:
    try:
        sa, sb = a.stat(), b.stat()
    except OSError:
        return False
    return sa.st_size == sb.st_size and a.read_bytes() == b.read_bytes()


def venv_base_interpreter(python_exe: str | Path) -> Path | None:
    """The base interpreter of the virtual environment of ``python_exe`` (the ``home`` entry of
    ``pyvenv.cfg`` in the interpreter's folder or its parent), or ``None`` outside a virtual
    environment or when ``home`` names no ``python.exe``. """
    src = Path(python_exe)
    for cfg in (src.parent / "pyvenv.cfg", src.parent.parent / "pyvenv.cfg"):
        if not cfg.is_file():
            continue
        for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip().lower() == "home":
                base = Path(value.strip()) / "python.exe"
                return base if base.is_file() else None
        return None
    return None


def host_interpreter(python_exe: str | Path, *, copy: Callable[[Path, Path], object] | None = None) -> Path | None:
    """The renamed interpreter :data:`HOST_EXE_NAME` in the folder of ``python_exe``, created or
    brought up to date; ``None`` when it cannot be written. 

    Outside a virtual environment it is a copy of ``python_exe``. In a virtual environment on
    Windows, ``Scripts/python.exe`` is a launcher that starts the base interpreter as a child
    process named ``python.exe``; a renamed launcher would therefore not protect the grid. The
    renamed interpreter is then a copy of the base interpreter (:func:`venv_base_interpreter`),
    and the DLLs of the base folder (``python3.dll``, ``python3XY.dll``, the C runtime) are copied
    next to it. The copy finds ``pyvenv.cfg`` in the parent folder, so it runs in the same
    environment (same ``sys.prefix`` and site packages) as a single process named
    :data:`HOST_EXE_NAME` (verified on Windows 11 with Python 3.12.10).

    Each file is written to a temporary file in the folder and moved into place, so that a
    concurrent start never sees a half-written executable. ``copy(src, dst)`` replaces the byte
    copy (tests).
    """
    src = Path(python_exe)
    dst = src.with_name(HOST_EXE_NAME)
    base = venv_base_interpreter(src) if sys.platform == "win32" else None
    if base is None:
        pairs = [(src, dst)]
    else:
        pairs = [(base, dst)] + [(dll, dst.with_name(dll.name)) for dll in sorted(base.parent.glob("*.dll"))]
    try:
        for a, b in pairs:
            if b.exists() and _same_file_content(a, b):
                continue
            if copy is not None:
                copy(a, b)
                continue
            fd, tmp = tempfile.mkstemp(prefix=".aspire-host-", dir=str(b.parent))
            with os.fdopen(fd, "wb") as fh:
                fh.write(a.read_bytes())
            os.replace(tmp, b)
        return dst
    except OSError:
        return None


def maybe_relaunch_under_host(argv: Sequence[str], *, platform: str | None = None, executable: str | None = None,
                              runner: Callable[..., "subprocess.CompletedProcess"] = subprocess.run) -> int | None:
    """Run ``aspire <argv>`` again under the renamed interpreter and return that run's exit status.

  Returns ``None`` (the caller continues in this process, without
    the protection) when no re-launch is needed, when the copy cannot be written, or when the
    renamed interpreter cannot be started; the last two print a warning on standard error.
    """
    decision = decide_relaunch(platform, executable)
    if not decision.relaunch:
        return None
    host = host_interpreter(executable or sys.executable)
    if host is None:
        print(f"warning: {HOST_EXE_NAME} could not be written next to the interpreter; the grid runs unprotected against "
              "commands that end processes by image name", file=sys.stderr)
        return None
    from .credentials import passed_keys_of, worker_environment

    keys = passed_keys_of()
    env = {**worker_environment(), RELAUNCH_GUARD: "1", KEYS_ON_STDIN: "1"}  # no key in the new environment
    try:
        done = runner([str(host), "-m", "aspire_sysid", *argv], env=env, input=json.dumps(keys) + "\n", text=True)
    except OSError as exc:
        print(f"warning: {host} could not be started ({exc}); the grid runs unprotected under the original interpreter",
              file=sys.stderr)
        return None
    return int(done.returncode)


def worker_executable() -> str:
    """The interpreter that starts the run workers: the grid runner's own (on Windows, the renamed
    host after :func:`maybe_relaunch_under_host`).  """
    return sys.executable
