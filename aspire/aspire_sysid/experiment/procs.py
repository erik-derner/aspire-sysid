"""Processes of the grid: liveness, identity of a process, and the lifetime of the run workers.

 Three measures keep one run from
being executed twice at the same time and keep a worker from writing into the folder of another
attempt:

1. **Identity of a process** (:func:`process_identity`, :func:`is_running`). ``run_start.json``
   records the process number, the host and, where the system provides it, the start time of the
   worker process (Linux: field 22 of ``/proc/<pid>/stat``). A run is taken for running when a
   process with that number exists on this host and, where recorded, has the same start time, so
   that a reused process number is not mistaken for the worker.
2. **Workers end with the grid** (:func:`guard_parent`). A worker must not outlive the grid
   process that started it. On POSIX: on Linux the worker asks the kernel to send it ``SIGTERM``
   when its parent ends (``prctl(PR_SET_PDEATHSIG)``) and then checks that the parent is still the
   grid; a watchdog thread polls the parent process number and, when it changes and no
   ``SIGTERM`` has arrived yet, sends one (never a second), and ends the worker forcibly 15 s
   later if it has not ended. The ``SIGTERM`` handler raises ``SystemExit`` through
   :func:`aspire_sysid.agent.shell.request_termination`, which defers it while a command is being
   started or cleaned up, so that the agent's running command is always ended with its process
   group and marked processes, and no run record is written. On Windows the watchdog is not used
   (the parent process number does not change when the parent ends); the grid places every worker
   into a job object with ``KILL_ON_JOB_CLOSE`` (:class:`WorkerJob`), whose handle only the grid
   holds, so that the system ends the workers when the grid ends.
3. **Ownership of the run folder** (checked in :mod:`aspire_sysid.experiment.runner`): the worker
   writes into its run folder only while ``run_start.json`` there carries its own random token.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

__all__ = [
    "pid_alive",
    "process_start_time",
    "process_identity",
    "is_running",
    "process_alive",
    "guard_parent",
    "WorkerJob",
]


def pid_alive(pid: int) -> bool:
    """Whether a process with number ``pid`` exists on this computer. """
    if pid <= 0:
        return False
    if sys.platform == "win32":  # pragma: no cover - exercised on Windows only
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE  # the default restype int would truncate a 64-bit handle
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = wintypes.DWORD()
        ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _windows_creation_time(pid: int) -> str | None:  # pragma: no cover - Windows only
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel32.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
            return None
        created = times[0]
        return str((created.dwHighDateTime << 32) | created.dwLowDateTime)
    finally:
        kernel32.CloseHandle(handle)


def process_start_time(pid: int, proc_root: str | Path = "/proc") -> str | None:
    """The start time of process ``pid``, or ``None`` when it cannot be read. 

    Linux: clock ticks since boot (field 22 of ``/proc/<pid>/stat``); Windows: the creation time
    from ``GetProcessTimes`` (100-ns intervals since 1601); other systems: ``None``.
    """
    if sys.platform == "win32":  # pragma: no cover - Windows only
        return _windows_creation_time(pid)
    try:
        text = (Path(proc_root) / str(pid) / "stat").read_text()
    except OSError:
        return None
    rest = text.rsplit(")", 1)[-1].split()
    return rest[19] if len(rest) > 19 else None  # field 22 of the whole line


def process_identity(pid: int | None = None) -> dict[str, Any]:
    """Process number, host and start time of ``pid`` (default: this process). """
    import socket

    p = os.getpid() if pid is None else pid
    return {"pid": p, "host": socket.gethostname(), "start_time": process_start_time(p)}


def process_alive(identity: dict[str, Any]) -> bool:
    """Whether the process of ``identity`` (number and, where recorded, start time) exists on this
    computer; a live process with another start time is a reused number. """
    pid = int(identity.get("pid") or -1)
    if not pid_alive(pid):
        return False
    recorded = identity.get("start_time")
    return recorded is None or process_start_time(pid) in (None, recorded)


def is_running(identity: dict[str, Any]) -> bool:
    """Whether the process described by ``identity`` (:func:`process_identity`) still runs on this host.

 A process on another host cannot be checked and is taken for
    running. This process itself is never taken for a running worker.
    """
    import socket

    if identity.get("host") not in (None, socket.gethostname()):
        return True
    if int(identity.get("pid") or -1) == os.getpid():
        return False
    return process_alive(identity)


_TERMINATION = {"received": False}


def _on_sigterm(signum: int, frame: Any) -> None:
    from ..agent.shell import request_termination

    _TERMINATION["received"] = True
    request_termination(signum)  # raises SystemExit, or defers it while a command starts or is cleaned up


def guard_parent(grid_pid: int, *, poll_s: float = 1.0, grace_s: float = 15.0,
                 exit_now: Callable[[int], None] = os._exit) -> threading.Thread:
    """Make this worker end when the grid process ``grid_pid`` ends (module docstring, item 2).

 Installs a ``SIGTERM`` handler that raises ``SystemExit``,
    requests ``PR_SET_PDEATHSIG`` on Linux, ends the worker at once when the parent is already
    another process, and starts the watchdog thread, which it returns.
    """
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _on_sigterm)
    if sys.platform.startswith("linux"):
        try:
            import ctypes

            libc = ctypes.CDLL(None, use_errno=True)
            libc.prctl(1, int(signal.SIGTERM), 0, 0, 0)  # PR_SET_PDEATHSIG
        except (OSError, AttributeError):
            pass
    # On Windows the job object of the grid ends the worker (module docstring, item 2); the parent
    # check does not apply there, because a virtual environment's python.exe is a launcher whose
    # child, the actual worker, has the launcher and not the grid as its parent.
    if sys.platform != "win32" and os.getppid() != grid_pid:
        exit_now(3)

    def watch() -> None:
        while os.getppid() == grid_pid and not _TERMINATION["received"]:
            time.sleep(poll_s)
        if not _TERMINATION["received"]:  # never a second SIGTERM after the first
            os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(grace_s)
        exit_now(3)

    if sys.platform == "win32":  # pragma: no cover - the job object of the grid ends the worker on Windows
        return threading.current_thread()
    t = threading.Thread(target=watch, name="aspire-parent-watchdog", daemon=True)
    t.start()
    return t


class WorkerJob:
    """The Windows job object that ends the run workers when the grid process ends (module docstring).

 Uses :class:`aspire_sysid.agent.shell.WindowsJob`
    (``KILL_ON_JOB_CLOSE``); the grid holds the only handle and never closes it before its end, so
    that the system ends every worker when the grid ends for any reason. On other systems the
    object does nothing.
    """

    def __init__(self) -> None:
        self._job = None
        if sys.platform == "win32":  # pragma: no cover - Windows only
            from ..agent.shell import WindowsJob

            self._job = WindowsJob()

    @property
    def active(self) -> bool:
        """True on Windows, where the job exists."""
        return self._job is not None

    def adopt(self, proc: Any) -> None:
        """Place a started worker process into the job (Windows); no effect elsewhere."""
        if self._job is not None:  # pragma: no cover - Windows only
            self._job.attach(int(proc._handle))

    def close(self) -> None:
        """Close the job at the orderly end of the grid (all workers have ended by then)."""
        if self._job is not None:  # pragma: no cover - Windows only
            self._job.release()
            self._job = None
