"""Execution of shell commands with a time limit and termination of the whole process tree.

A shell command instructs the operating system to run, for example, a Python script; its limit
is 600 s or the remaining round time, whichever is shorter. At a budget limit the harness
terminates the remaining tool work where supported. Shell commands run so that a timeout
terminates the whole process tree.

Every command is bounded by the shell limit: at the time limit, and also when the command has
finished, the harness ends every process the command started, including processes started in
the background.

* **POSIX.** The command starts in a new session and therefore in a new process group
  (``start_new_session``); the harness sends ``SIGKILL`` to the group. A program can leave the
  group (``setsid -f``, a double fork with ``os.setsid``); therefore every command also
  receives a random marker in its environment, ``ASPIRE_SHELL_TOKEN=<random>``, which its
  descendants inherit, and on Linux the harness then searches ``/proc/<pid>/environ`` of every
  process of the same user and ends each process that carries the marker
  (:func:`sweep_marked_processes`). Limit: a process that replaces its whole environment
  (``env -i``, ``execve`` with a new environment) after leaving the process group escapes both
  mechanisms; so does, on a POSIX system without ``/proc``, any process that leaves the group.
* **Windows.** The command starts suspended, is assigned to a job object with the limit
  ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`` and is then resumed, so that every process it starts
  belongs to the job regardless of re-parenting; the job is terminated at the time limit and
  its handle is closed when the command has finished, which ends every remaining process.

The output is written to temporary files outside the working directory, so that a process
holding the output open cannot block the harness.

**Termination requests.** A process that ends the harness on a signal (the experiment worker raises
``SystemExit`` on ``SIGTERM``, :mod:`aspire_sysid.experiment.procs`) must not interrupt the start of a
command before the harness holds its process, nor the cleanup that ends it. The signal handler
therefore calls :func:`request_termination`, which raises at once outside and records the request
inside a :func:`termination_deferred` section; the request is raised when the outermost section
ends. :func:`run_command` starts the command, and ends its process tree, inside such sections, so
that the process group and the marked processes are ended on every exit path.
"""

from __future__ import annotations

import os
import secrets
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping, Sequence

__all__ = [
    "ShellResult", "run_command", "cap_text", "WindowsJob", "TOKEN_VARIABLE", "sweep_marked_processes",
    "termination_deferred", "request_termination",
]

TOKEN_VARIABLE = "ASPIRE_SHELL_TOKEN"
"""Environment variable that marks every process started by one shell command (module docstring)."""


@dataclass(frozen=True)
class ShellResult:
    """The outcome of one command (full output kept for the record).

    ``exit_code`` is ``None`` when the command was terminated at its time limit.
    ``stdout_chars`` and ``stderr_chars`` are the lengths of the complete outputs; ``stdout``
    and ``stderr`` are shortened by :func:`cap_text` only when they exceed the record cap.
    """

    command: str
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    timeout_s: float
    duration_s: float
    stdout_chars: int
    stderr_chars: int

    def text(self) -> str:
        """The combined text of the result as sent to the agent before the output cap."""
        head = (
            f"[terminated: time limit of {self.timeout_s:.0f} s reached; the process tree was ended]"
            if self.timed_out
            else f"[exit status {self.exit_code}]"
        )
        parts = [head]
        if self.stdout:
            parts.append(self.stdout.rstrip("\n"))
        if self.stderr:
            parts.append("[stderr]")
            parts.append(self.stderr.rstrip("\n"))
        return "\n".join(parts)

    def to_dict(self) -> dict[str, object]:
        """JSON-serializable form for the record."""
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "timeout_s": self.timeout_s,
            "duration_s": self.duration_s,
            "stdout_chars": self.stdout_chars,
            "stderr_chars": self.stderr_chars,
        }


def cap_text(text: str, cap: int) -> tuple[str, bool]:
    """Shorten ``text`` to at most about ``cap`` characters: its first and last parts with a note.

 Returns the text
    and whether it was shortened. The note states the number of omitted characters.
    """
    if cap <= 0 or len(text) <= cap:
        return text, False
    head = cap // 2
    tail = cap - head
    omitted = len(text) - head - tail
    return f"{text[:head]}\n[... {omitted} characters omitted ...]\n{text[-tail:]}", True


def _read_capped(path: Path, cap: int) -> tuple[str, int]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    capped, _ = cap_text(text, cap)
    return capped, len(text)


# -- Windows job object ---------------------------------------------------------------------


def _win32():
    """The kernel32 and ntdll functions used by :class:`WindowsJob`, with declared signatures."""
    import ctypes  # noqa: PLC0415 - Windows only
    from ctypes import wintypes  # noqa: PLC0415

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    ntdll = ctypes.WinDLL("ntdll")  # type: ignore[attr-defined]
    handle = wintypes.HANDLE
    signatures = [  # a list: ctypes function pointers are not hashable
        (kernel32.CreateJobObjectW, [ctypes.c_void_p, wintypes.LPCWSTR], handle),
        (kernel32.SetInformationJobObject, [handle, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        (kernel32.AssignProcessToJobObject, [handle, handle], wintypes.BOOL),
        (kernel32.TerminateJobObject, [handle, wintypes.UINT], wintypes.BOOL),
        (kernel32.CloseHandle, [handle], wintypes.BOOL),
        (kernel32.OpenProcess, [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], handle),
        (kernel32.QueryInformationJobObject, [handle, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
        (ntdll.NtResumeProcess, [handle], ctypes.c_long),
    ]
    for fn, args, res in signatures:
        fn.argtypes = args
        fn.restype = res
    return ctypes, wintypes, kernel32, ntdll


class WindowsJob:
    """A Windows job object whose processes end when it is closed.

    The job carries the limit ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE``: :meth:`kill_all` ends
    every process of the job at once, and :meth:`release` closes the last handle, which ends
    any process still running. :meth:`attach` places a suspended process into the job before it
    runs; :meth:`start` resumes it and raises :class:`OSError` when resuming fails.
    """

    KILL_ON_JOB_CLOSE = 0x00002000
    EXTENDED_LIMIT_INFORMATION = 9
    CREATE_SUSPENDED = 0x00000004
    CREATE_NEW_PROCESS_GROUP = 0x00000200

    def __init__(self) -> None:
        ctypes, wintypes, self._k32, self._nt = _win32()

        class Basic(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class Io(ctypes.Structure):
            _fields_ = [(f"Counter{i}", ctypes.c_uint64) for i in range(6)]

        class Extended(ctypes.Structure):
            _fields_ = [
                ("Basic", Basic),
                ("Io", Io),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        self._ctypes = ctypes
        job = self._k32.CreateJobObjectW(None, None)
        if not job:
            raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
        self._job = job
        limits = Extended()
        limits.Basic.LimitFlags = self.KILL_ON_JOB_CLOSE
        if not self._k32.SetInformationJobObject(job, self.EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits), ctypes.sizeof(limits)):
            code = ctypes.get_last_error()
            self.release()
            raise OSError(code, "SetInformationJobObject failed")

    @property
    def is_open(self) -> bool:
        """True until :meth:`release`."""
        return self._job is not None

    def attach(self, process_handle: int) -> None:
        """Place the (suspended) process into the job; raises :class:`OSError` on failure."""
        if self._job is None or not self._k32.AssignProcessToJobObject(self._job, process_handle):
            raise OSError(self._ctypes.get_last_error(), "AssignProcessToJobObject failed")

    def start(self, process_handle: int) -> None:
        """Resume a process created suspended; raises :class:`OSError` with the NTSTATUS on failure."""
        status = self._nt.NtResumeProcess(process_handle)
        if status != 0:
            raise OSError(status, f"NtResumeProcess failed with status 0x{status & 0xFFFFFFFF:08X}")

    def kill_all(self) -> None:
        """End every process of the job now."""
        if self._job is not None:
            self._k32.TerminateJobObject(self._job, 1)

    def active_processes(self) -> int | None:
        """The number of processes of the job that are still running, or ``None`` when it cannot be read."""
        if self._job is None:
            return 0
        ctypes = self._ctypes

        class Accounting(ctypes.Structure):  # JOBOBJECT_BASIC_ACCOUNTING_INFORMATION
            _fields_ = [(f"Time{i}", ctypes.c_int64) for i in range(4)] + [
                ("TotalPageFaultCount", ctypes.c_uint32),
                ("TotalProcesses", ctypes.c_uint32),
                ("ActiveProcesses", ctypes.c_uint32),
                ("TotalTerminatedProcesses", ctypes.c_uint32),
            ]

        info = Accounting()
        if not self._k32.QueryInformationJobObject(self._job, 1, ctypes.byref(info), ctypes.sizeof(info), None):
            return None
        return int(info.ActiveProcesses)

    def wait_empty(self, timeout_s: float = 10.0) -> bool:
        """Wait until no process of the job runs (``TerminateJobObject`` returns before the processes
        have ended and released their files); True when the job is empty."""
        deadline = time.monotonic() + timeout_s
        while True:
            n = self.active_processes()
            if n == 0:
                return True
            if n is None or time.monotonic() >= deadline:
                return False
            time.sleep(0.02)

    def release(self) -> None:
        """Close the job; with ``KILL_ON_JOB_CLOSE`` every remaining process ends."""
        job, self._job = self._job, None
        if job is not None:
            self._k32.CloseHandle(job)


# -- marker sweep (Linux) -----------------------------------------------------------------------


def sweep_marked_processes(token: str, *, rounds: int = 5, proc_root: str | Path = "/proc") -> list[int]:
    """End every process whose environment carries ``ASPIRE_SHELL_TOKEN=<token>``.

 Reads ``/proc/<pid>/environ`` of
    every readable process; repeats up to ``rounds`` times while processes are found, so that a
    process started during a sweep is also ended. Returns the ended process identifiers; on a
    system without ``/proc`` it returns an empty list.
    """
    root = Path(proc_root)
    if not root.is_dir():
        return []
    needle = f"{TOKEN_VARIABLE}={token}".encode()
    me = os.getpid()
    ended: list[int] = []
    for _ in range(max(1, rounds)):
        found = False
        for entry in root.iterdir():
            if not entry.name.isdigit() or int(entry.name) == me:
                continue
            try:
                environ = (entry / "environ").read_bytes()
            except OSError:
                continue
            if needle in environ.split(b"\0"):
                try:
                    os.kill(int(entry.name), signal.SIGKILL)
                except OSError:
                    continue
                ended.append(int(entry.name))
                found = True
        if not found:
            break
        time.sleep(0.02)
    return ended


# -- deferred termination --------------------------------------------------------------------------

_DEFERRAL: dict[str, int | None] = {"depth": 0, "pending": None}


@contextmanager
def termination_deferred() -> Iterator[None]:
    """A section in which a termination request is recorded instead of raised (module docstring).

 At the end of the outermost section a recorded request raises
    ``SystemExit(128 + signal number)``. Sections nest.
    """
    _DEFERRAL["depth"] = int(_DEFERRAL["depth"] or 0) + 1
    try:
        yield
    finally:
        _DEFERRAL["depth"] = int(_DEFERRAL["depth"] or 1) - 1
        pending = _DEFERRAL["pending"]
        if _DEFERRAL["depth"] == 0 and pending is not None:
            _DEFERRAL["pending"] = None
            raise SystemExit(128 + int(pending))


def request_termination(signum: int) -> None:
    """Raise ``SystemExit(128 + signum)``, or record the request inside a deferred section (module docstring). """
    if int(_DEFERRAL["depth"] or 0) > 0:
        _DEFERRAL["pending"] = signum
        return
    raise SystemExit(128 + signum)


# -- running a command -------------------------------------------------------------------------


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)  # type: ignore[attr-defined]
    except (ProcessLookupError, PermissionError, OSError):
        pass


def run_command(
    command: str | Sequence[str],
    *,
    cwd: str | Path,
    env: Mapping[str, str],
    timeout_s: float,
    record_cap_chars: int = 10_000_000,
) -> ShellResult:
    """Run ``command`` in ``cwd`` with ``env``; end its whole process tree at ``timeout_s``.

 A string is
    run by the system shell; a sequence is run directly. Standard input is empty. The process
    tree is ended at the time limit and also when the command has finished, including processes
    that left the process group but kept the command's marker (module docstring).
    """
    if not timeout_s > 0:
        raise ValueError(f"timeout_s must be positive, got {timeout_s!r}")
    shell = isinstance(command, str)
    shown = command if shell else subprocess.list2cmdline(list(command))
    win = sys.platform == "win32"
    token = secrets.token_hex(16)
    run_env = dict(env)
    run_env[TOKEN_VARIABLE] = token
    # ignore_cleanup_errors: on Windows a file that a process still holds cannot be removed; a
    # leftover folder in the temporary folder must not turn a finished command into an error
    with tempfile.TemporaryDirectory(prefix="aspire-shell-", ignore_cleanup_errors=True) as tmp:
        out_path = Path(tmp) / "stdout"
        err_path = Path(tmp) / "stderr"
        with open(out_path, "wb") as out_f, open(err_path, "wb") as err_f:
            kwargs: dict[str, object] = {
                "cwd": str(cwd),
                "env": run_env,
                "stdin": subprocess.DEVNULL,
                "stdout": out_f,
                "stderr": err_f,
                "shell": shell,
            }
            job: WindowsJob | None = None
            proc: subprocess.Popen | None = None
            timed_out = False
            exit_code: int | None = None
            start = time.monotonic()
            try:
                with termination_deferred():  # the harness holds the process before a request can end it
                    if win:
                        job = WindowsJob()
                        kwargs["creationflags"] = WindowsJob.CREATE_SUSPENDED | WindowsJob.CREATE_NEW_PROCESS_GROUP
                    else:
                        kwargs["start_new_session"] = True
                    start = time.monotonic()
                    proc = subprocess.Popen(command, **kwargs)  # noqa: S603 - the agent's command, filtered by the policy
                    if job is not None:
                        handle = int(proc._handle)  # type: ignore[attr-defined]
                        try:
                            job.attach(handle)
                            job.start(handle)
                        except OSError:
                            job.kill_all()
                            raise
                try:
                    exit_code = proc.wait(timeout=timeout_s)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    exit_code = None
                    with termination_deferred():
                        if job is not None:
                            job.kill_all()
                        else:
                            _kill_group(proc.pid)
            finally:
                with termination_deferred():  # the cleanup is never interrupted by a request
                    if job is not None:
                        job.kill_all()  # also the background processes of a finished command
                        job.wait_empty()  # until they have released the output files
                        job.release()  # KILL_ON_JOB_CLOSE ends every remaining process of the job
                    elif proc is not None:
                        _kill_group(proc.pid)
                    if not win:
                        sweep_marked_processes(token)
                    if proc is not None and proc.poll() is None:
                        proc.kill()
                    if proc is not None:
                        try:
                            proc.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            pass
            duration = time.monotonic() - start
        stdout, n_out = _read_capped(out_path, record_cap_chars)
        stderr, n_err = _read_capped(err_path, record_cap_chars)
    return ShellResult(
        command=shown,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        timeout_s=float(timeout_s),
        duration_s=duration,
        stdout_chars=n_out,
        stderr_chars=n_err,
    )
