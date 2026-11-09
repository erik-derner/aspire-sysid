"""Time-bounded symbolic computation in a separate worker process.

The harness first attempts a symbolic verification where the requirement permits
it, and distinguishes a proof, a counterexample and an inconclusive calculation; the
symbolic part of the reference comparison is also computed here. SymPy's simplification, extremum and limit routines
can run for an unbounded time on some expressions, and a Python thread cannot be stopped from
outside. Every symbolic job therefore runs in a worker process that the harness terminates when
the job exceeds its time limit; the job then counts as inconclusive, with the reason "time
limit".

Mechanism (works on Linux and Windows): one worker process, started with the ``spawn`` method of
:mod:`multiprocessing` (the only start method available on Windows), receives jobs over a pipe.
The harness waits for the answer with ``Connection.poll(time_limit)``; on expiry it calls
``Process.terminate`` (SIGTERM on Linux, ``TerminateProcess`` on Windows), discards the worker
and starts a new one for the next job. Starting the worker costs one interpreter start with the
SymPy import (of the order of one second); the worker is reused across jobs and candidates, and
it is stopped when the harness exits. A new worker first reports that it is ready; only then is
the job sent and its time limit started, so that the start-up does not count against the job.
Because of the ``spawn`` method, a script that calls the evaluation must protect its entry point
with ``if __name__ == "__main__":``; otherwise the worker cannot start, and every symbolic stage is
reported as unavailable with that explanation (:data:`MAIN_GUARD_HINT`). The jobs are pure functions of their arguments (SymPy
objects, numbers and strings), so the result does not depend on the process that computes it.

For tests, :func:`set_isolation` may select ``"inline"``: the jobs then run in the calling
process without a time limit. The harness itself always uses ``"process"``.
"""

from __future__ import annotations

import atexit
import multiprocessing as mp
import threading
import traceback
from dataclasses import dataclass
from typing import Any

DEFAULT_TIME_LIMIT_S = 10.0
"""Time limit of one symbolic job when the task declares none (``evaluation.symbolic_time_limit_s``)."""


@dataclass(frozen=True)
class JobResult:
    """The outcome of one bounded symbolic job.

    ``status`` is ``ok`` (``value`` holds the result), ``timeout`` (the time limit was reached and
    the worker was terminated), ``error`` (the job raised; ``detail`` holds the exception) or
    ``unavailable`` (the worker process could not be started; ``detail`` says why).
    """

    status: str
    value: Any = None
    detail: str = ""


def _jobs() -> dict[str, Any]:
    from . import symbolic_jobs

    return symbolic_jobs.JOBS


def _worker_main(conn) -> None:  # pragma: no cover - runs in the worker process
    jobs = _jobs()
    conn.send(("ready", None, ""))
    while True:
        try:
            msg = conn.recv()
        except (EOFError, OSError):
            return
        if msg is None:
            return
        name, args = msg
        try:
            conn.send(("ok", jobs[name](*args), ""))
        except Exception as exc:  # noqa: BLE001 - reported to the harness as an error
            conn.send(("error", None, f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}"))


STARTUP_LIMIT_S = 120.0
"""Longest wait for a new worker process to import SymPy and report that it is ready; the start-up
time is not counted against the time limit of a job."""

MAIN_GUARD_HINT = (
    "the symbolic worker process could not be started; a script that calls the evaluation must "
    "protect its entry point with `if __name__ == \"__main__\":` (the worker is started with the "
    "spawn method, which imports the calling script's main module), and code typed on standard input "
    "cannot start it"
)
"""Explanation recorded when the worker process cannot be started."""


class WorkerStartError(RuntimeError):
    """The worker process did not start or did not report that it is ready."""


def _repair_windows_base_executable() -> None:
    """Point ``sys._base_executable`` at this interpreter when the file it names does not exist.

 The renamed host interpreter ``Scripts/aspire-host.exe`` is a copy of the base
    interpreter inside a virtual environment (:func:`aspire_sysid.experiment.host.host_interpreter`);
    Python derives its ``sys._base_executable`` as ``<home>/aspire-host.exe``, which does not exist.
    In a virtual environment on Windows, the spawn start method launches ``sys._base_executable``, so
    the worker could not start. The host copy is itself a complete interpreter that finds
    ``pyvenv.cfg``, so it can start the worker directly (with the image name ``aspire-host.exe``).
    """
    import os
    import sys

    if sys.platform == "win32" and not os.path.isfile(getattr(sys, "_base_executable", "") or ""):
        sys._base_executable = sys.executable  # type: ignore[attr-defined]


class _Worker:
    def __init__(self) -> None:
        _repair_windows_base_executable()
        ctx = mp.get_context("spawn")
        self.conn, child = ctx.Pipe()
        self.proc = ctx.Process(target=_worker_main, args=(child,), daemon=True, name="aspire-symbolic")
        try:
            self.proc.start()
        except Exception as exc:  # noqa: BLE001
            raise WorkerStartError(f"{MAIN_GUARD_HINT} ({type(exc).__name__}: {exc})") from exc
        child.close()
        try:
            ready = self.conn.poll(STARTUP_LIMIT_S) and self.conn.recv()[0] == "ready"
        except (EOFError, OSError):
            ready = False
        if not ready:
            self.stop(kill=True)
            raise WorkerStartError(MAIN_GUARD_HINT)

    def stop(self, kill: bool = False) -> None:
        try:
            if not kill:
                self.conn.send(None)
                self.proc.join(2.0)
        except (OSError, EOFError, BrokenPipeError):
            pass
        if self.proc.is_alive():
            self.proc.terminate()
            self.proc.join(5.0)
            if self.proc.is_alive():  # pragma: no cover
                self.proc.kill()
                self.proc.join(5.0)
        self.conn.close()


class SymbolicRunner:
    """Runs symbolic jobs in a worker process with a time limit per job."""

    def __init__(self, isolation: str = "process"):
        if isolation not in ("process", "inline"):
            raise ValueError("isolation must be 'process' or 'inline'")
        self.isolation = isolation
        self._worker: _Worker | None = None
        self._lock = threading.Lock()

    def run(self, name: str, args: tuple, time_limit_s: float) -> JobResult:
        """Run the job ``name`` with ``args``; stop it after ``time_limit_s`` seconds."""
        if self.isolation == "inline":
            try:
                return JobResult("ok", _jobs()[name](*args))
            except Exception as exc:  # noqa: BLE001
                return JobResult("error", None, f"{type(exc).__name__}: {exc}")
        with self._lock:
            if self._worker is None or not self._worker.proc.is_alive():
                try:
                    self._worker = _Worker()  # waits for "ready": start-up is not timed
                except WorkerStartError as exc:
                    self._worker = None
                    return JobResult("unavailable", None, str(exc))
            w = self._worker
            try:
                w.conn.send((name, args))
                if not w.conn.poll(time_limit_s):
                    w.stop(kill=True)
                    self._worker = None
                    return JobResult("timeout", None, f"the symbolic computation exceeded the time limit of {time_limit_s:g} s")
                status, value, detail = w.conn.recv()
            except (EOFError, OSError, BrokenPipeError) as exc:
                w.stop(kill=True)
                self._worker = None
                return JobResult("error", None, f"the symbolic worker failed: {type(exc).__name__}: {exc}")
            return JobResult(status, value, detail)

    def close(self) -> None:
        """Stop the worker process."""
        with self._lock:
            if self._worker is not None:
                self._worker.stop()
                self._worker = None


_RUNNER: SymbolicRunner | None = None
_ISOLATION = "process"


def set_isolation(isolation: str) -> None:
    """Select ``process`` (default, time-limited) or ``inline`` (tests only, no time limit)."""
    global _ISOLATION, _RUNNER
    if _RUNNER is not None:
        _RUNNER.close()
        _RUNNER = None
    _ISOLATION = isolation


def runner() -> SymbolicRunner:
    """The shared runner of this harness process (started lazily, stopped at exit)."""
    global _RUNNER
    if _RUNNER is None:
        _RUNNER = SymbolicRunner(_ISOLATION)
    return _RUNNER


def run_job(name: str, args: tuple, time_limit_s: float | None) -> JobResult:
    """Run one symbolic job with the shared runner; ``None`` uses the default limit."""
    return runner().run(name, args, DEFAULT_TIME_LIMIT_S if time_limit_s is None else float(time_limit_s))


@atexit.register
def _shutdown() -> None:  # pragma: no cover
    if _RUNNER is not None:
        _RUNNER.close()
