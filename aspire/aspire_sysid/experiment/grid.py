"""The grid of an experiment: execution with concurrency, crash-resume and a lock file.

The report counts the runs attempted; the grid runner is protected against the agent's
process-ending commands; an interrupted grid resumes without repeating finished runs. The grid of an experiment is the list of its runs ``r01`` to ``r<NN>`` of one task.

**Folders.** A real grid writes into the experiment folder, a dry run into its subfolder
``dry-run/`` (so that dry-run records never mix with real ones):

=========================  ===================================================================
``runs/<run-id>/``         the run folders (:mod:`aspire_sysid.experiment.runner`)
``interrupted/``           interrupted attempts, ``<run-id>__attempt<k>/``, each labeled by
                           ``INTERRUPTED.json``
``logs/grid.jsonl``        one line per grid event (start, run start and end, interruption found)
``logs/<run>__attempt<k>.log``  the output of a run worker process
``export/matlab/``         the experiment-level Matlab export: the working folder of the task for
                           the Matlab framework with the models of every finished run
                           (:func:`export_experiment_matlab`; ``exported_runs.json`` lists the runs)
``experiment.lock``          the lock file of the grid process (experiment folder only)
=========================  ===================================================================

**States of a run.** *Finished*: the run folder has a run record with a final outcome; a finished
run is never repeated (a missing export is completed). *Interrupted*: the run folder exists
without such a record (the process ended during the run, for example by a crash, a power cut or
an ended process). With ``--resume`` the interrupted run folder is moved to
``interrupted/<run-id>__attempt<k>/``, labeled, completed by a copy of its working directory when
one exists, and the run is started again from the beginning in a fresh run folder with attempt
number ``k + 1``, a fresh working directory and a fresh conversation. Without ``--resume`` the
grid refuses to start when any run folder exists. An unfinished run whose process (number, host
and start time in ``run_start.json``) still runs on this host is never archived or repeated: the
resumed grid reports it as still running and leaves it alone (resume again after it has ended).
*Planned*: no run folder.

**Lock.** ``experiment.lock`` is created exclusively by the grid process and holds its process
number and host. A second grid process on the same experiment is refused while the first one is
alive; a lock of a process that no longer exists on the same host, or whose process number now
belongs to another process (a different start time), is replaced (the replacement is
logged).

**Concurrency.** Runs execute in separate worker processes (``concurrency`` at a time), so that a
crash of one run does not end the others and every run has a fresh interpreter. The workers end
when the grid process ends (:mod:`aspire_sysid.experiment.procs`), receive no API key in their
environment (the key goes through their standard input), and a run record counts for the grid
only when it belongs to the attempt that the grid started. A run with an
injected provider (tests) executes in the grid process itself, one run after the other.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import socket
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from ..portable import local_path, portable_data
from ..paths import HARNESS_DIR
from ..record import RUN_RECORD_FILE
from .config import Experiment, RunSpec
from ..agent.loop import OUTCOMES
from .credentials import worker_environment
from .host import worker_executable
from .procs import WorkerJob, is_running, pid_alive, process_alive, process_identity
from .runner import EXPORT_STATUS_FILE, RUN_START_FILE, RunOptions, RunSummary, execute_run, run_exports, summary_of_record
from .workspace import copy_workspace

__all__ = [
    "LOCK_FILE",
    "INTERRUPTED_LABEL",
    "DRY_RUN_DIR",
    "GridError",
    "LockHeldError",
    "GridPaths",
    "RunState",
    "GridResult",
    "grid_paths",
    "run_state",
    "grid_states",
    "pending_runs",
    "maximum_cost_usd",
    "acquire_lock",
    "release_lock",
    "pid_alive",
    "archive_interrupted",
    "running_process",
    "export_experiment_matlab",
    "run_grid",
]

LOCK_FILE = "experiment.lock"
INTERRUPTED_LABEL = "INTERRUPTED.json"
DRY_RUN_DIR = "dry-run"
_FINAL_OUTCOMES = frozenset(OUTCOMES)  # the round outcomes of the turn loop


class GridError(RuntimeError):
    """The grid cannot start or continue. """


class LockHeldError(GridError):
    """Another grid process holds the lock of the experiment. """


@dataclass(frozen=True)
class GridPaths:
    """The folders of one grid (module docstring). """

    base: Path
    lock: Path

    @property
    def runs(self) -> Path:
        return self.base / "runs"

    @property
    def interrupted(self) -> Path:
        return self.base / "interrupted"

    @property
    def logs(self) -> Path:
        return self.base / "logs"


def grid_paths(exp: Experiment, dry_run: bool) -> GridPaths:
    """The folders of the real grid (the experiment folder) or of the dry run (``dry-run/``).  """
    return GridPaths(exp.dir / DRY_RUN_DIR if dry_run else exp.dir, exp.dir / LOCK_FILE)


@dataclass(frozen=True)
class RunState:
    """The state of one run of the grid (module docstring).  """

    spec: RunSpec
    state: str  # planned | finished | interrupted
    outcome: str | None = None
    export_complete: bool | None = None
    interrupted_attempts: int = 0

    @property
    def next_attempt(self) -> int:
        """The attempt number of the next execution of the run."""
        return self.interrupted_attempts + 1


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _interrupted_attempts(paths: GridPaths, run_id: str) -> int:
    if not paths.interrupted.is_dir():
        return 0
    return sum(1 for p in paths.interrupted.iterdir() if p.is_dir() and p.name.startswith(run_id + "__attempt"))


def run_state(paths: GridPaths, spec: RunSpec) -> RunState:
    """The state of ``spec`` in the grid folders (module docstring).  """
    folder = paths.runs / spec.run_id
    n_int = _interrupted_attempts(paths, spec.run_id)
    if not folder.exists():
        return RunState(spec, "planned", interrupted_attempts=n_int)
    try:
        rec = json.loads((folder / RUN_RECORD_FILE).read_text(encoding="utf-8"))
        outcome = rec.get("outcome")
    except (OSError, ValueError):
        outcome = None
    if outcome in _FINAL_OUTCOMES:
        return RunState(spec, "finished", outcome, (folder / "export" / EXPORT_STATUS_FILE).is_file(), n_int)
    return RunState(spec, "interrupted", interrupted_attempts=n_int)


def grid_states(exp: Experiment, dry_run: bool = False) -> list[RunState]:
    """The state of every run of the experiment's grid, in grid order.  """
    paths = grid_paths(exp, dry_run)
    return [run_state(paths, s) for s in exp.grid()]


def pending_runs(exp: Experiment, dry_run: bool = False) -> list[RunState]:
    """The runs that a (resumed) grid would execute: planned and interrupted ones.  """
    return [s for s in grid_states(exp, dry_run) if s.state != "finished"]


def maximum_cost_usd(exp: Experiment, specs: Iterable[RunSpec]) -> float:
    """The largest cost that the runs ``specs`` can incur: the sum of their round cost limits.

 A round may exceed its cost
    limit by the cost of the request during which the limit was reached; the bound does not
    include that excess.
    """
    from ..task import load_task

    per_run = exp.budget.usd if exp.budget is not None else load_task(exp.task_dir).budget.round.usd
    return per_run * len(list(specs))


# ---------------------------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------------------------


def acquire_lock(path: Path, *, log: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Create the lock file of the grid, or raise :class:`LockHeldError` (module docstring).  """
    me = {**process_identity(), "started_at": _utc_now(), "argv": sys.argv}
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                other = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raise LockHeldError(f"{path} exists and cannot be read; if no grid process is running, delete it") from None
            if other.get("host") == me["host"] and not process_alive(other):
                if log:
                    log(f"replacing the stale lock of process {other.get('pid')} (started {other.get('started_at')}), which no longer exists "
                        "(or whose number now belongs to another process)")
                path.unlink(missing_ok=True)
                continue
            raise LockHeldError(
                f"another grid process holds {path} (process {other.get('pid')} on {other.get('host')}, started {other.get('started_at')}); "
                "two grid processes never run on one experiment"
            ) from None
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(me, fh, indent=2)
        return me
    raise LockHeldError(f"cannot create {path}")


def release_lock(path: Path) -> None:
    """Remove the lock file when it belongs to this process.  """
    try:
        other = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if other.get("pid") == os.getpid() and other.get("host") == socket.gethostname():
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------------------------
# Interrupted runs
# ---------------------------------------------------------------------------------------------


def running_process(paths: GridPaths, spec: RunSpec) -> dict[str, Any] | None:
    """The process identity of ``run_start.json`` of an unfinished run when that process still runs
    on this host (so that the run must not be archived), else ``None``. """
    try:
        start = json.loads((paths.runs / spec.run_id / RUN_START_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ident = {k: start.get(k) for k in ("pid", "host", "start_time")}
    return ident if ident["pid"] is not None and is_running(ident) else None


def archive_interrupted(exp: Experiment, paths: GridPaths, state: RunState) -> Path:
    """Move an interrupted run folder to ``interrupted/<run-id>__attempt<k>/`` and label it.

 The label ``INTERRUPTED.json``
    states when the interruption was found, the attempt, the files present and where the working
    directory was; the working directory is copied into the archived folder when it still exists
    and was not copied before. Returns the archived folder. A run whose process still runs on this
    host (:func:`running_process`) is never archived: :class:`GridError` is raised. 
    """
    src = paths.runs / state.spec.run_id
    alive = running_process(paths, state.spec)
    if alive is not None:
        raise GridError(f"the run {state.spec.run_id} is still executed by process {alive['pid']} on {alive['host']}; it is not archived")
    start: dict[str, Any] = {}
    try:
        start = json.loads((src / RUN_START_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    attempt = int(start.get("attempt") or state.next_attempt)
    dest = paths.interrupted / f"{state.spec.run_id}__attempt{attempt}"
    while dest.exists():
        attempt += 1
        dest = paths.interrupted / f"{state.spec.run_id}__attempt{attempt}"
    paths.interrupted.mkdir(parents=True, exist_ok=True)
    files = sorted(p.relative_to(src).as_posix() for p in src.rglob("*") if p.is_file())
    os.replace(src, dest)
    ws = local_path(start["workspace"]) if start.get("workspace") else None  # the random path is known only from run_start.json
    copied = None
    if not (dest / "workspace").exists() and ws is not None and ws.is_dir():
        copied = copy_workspace(ws, dest / "workspace").to_dict()
    label = {
        "label": "interrupted attempt; not a finished run; never aggregated",
        "run_id": state.spec.run_id,
        "attempt": attempt,
        "detected_at": _utc_now(),
        "reason": "the run folder had no run record with a final outcome when the grid was resumed (the process ended during the run)",
        "run_start": start,
        "files_present": files,
        "workspace": None if ws is None else str(ws),
        "workspace_copy": copied,
        "repeated_as_attempt": attempt + 1,
    }
    (dest / INTERRUPTED_LABEL).write_text(json.dumps(portable_data(label), indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return dest


# ---------------------------------------------------------------------------------------------
# Experiment-level Matlab export
# ---------------------------------------------------------------------------------------------

EXPORTED_RUNS_FILE = "exported_runs.json"


def export_experiment_matlab(exp: Experiment, paths: GridPaths, opts: RunOptions) -> dict[str, Any]:
    """Add the finished runs not yet exported to the experiment-level Matlab export.


    The folder ``<grid>/export/matlab/`` holds the working folder of the task for the Matlab framework with
    the models of every finished run whose own Matlab export was written (runs without an
    evaluated candidate have none); ``exported_runs.json`` lists the runs already added, so that a
    resumed grid adds only new runs (model folders are never overwritten). Returns what was done.
    """
    from ..export import export_matlab

    out = paths.base / "export" / "matlab"
    registry = out / EXPORTED_RUNS_FILE
    done: dict[str, Any] = json.loads(registry.read_text(encoding="utf-8")) if registry.is_file() else {"runs": {}}
    if not exp.exports.matlab:
        return {"status": "deferred", "reason": "exports.matlab is false"}
    new: list[Path] = []
    for st in grid_states(exp, opts.dry_run):
        rid = st.spec.run_id
        if st.state != "finished" or rid in done["runs"]:
            continue
        status_path = paths.runs / rid / "export" / EXPORT_STATUS_FILE
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (status.get("matlab") or {}).get("status") == "written":
            new.append(paths.runs / rid)
    if not new:
        return {"status": "up to date", "folder": str(out), "runs": sorted(done["runs"])}
    octave = exp.exports.octave if opts.octave == "experiment" else opts.octave
    rep = export_matlab(new, out, octave=octave)  # type: ignore[arg-type]
    for d in new:
        done["runs"][d.name] = {"exported_at": _utc_now(), "models": sum(1 for m in rep.models if m.run_id == d.name)}
    # export_matlab creates no folder when it skips every task (for example a task of the discrete
    # formulation, which the Matlab framework does not represent); the registry is written regardless.
    out.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps(portable_data(done), indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return {"status": "written", "folder": str(out), "added": [d.name for d in new], "verified": rep.verified, "skipped": list(rep.skipped)}


# ---------------------------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------------------------


@dataclass
class GridResult:
    """What one execution of the grid did. """

    executed: list[RunSummary] = field(default_factory=list)
    skipped_finished: list[str] = field(default_factory=list)
    archived: list[str] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)
    exports_completed: list[str] = field(default_factory=list)
    still_running: list[dict[str, Any]] = field(default_factory=list)
    experiment_export: dict[str, Any] = field(default_factory=dict)

    @property
    def leak_findings(self) -> list[dict[str, Any]]:
        """Every leak-scan finding of the executed runs, with the run identifier."""
        return [{"run_id": s.run_id, **f} for s in self.executed for f in s.leak_findings]

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form."""
        return {
            "executed": [s.to_dict() for s in self.executed],
            "skipped_finished": list(self.skipped_finished),
            "archived": list(self.archived),
            "failed": list(self.failed),
            "exports_completed": list(self.exports_completed),
            "still_running": list(self.still_running),
            "experiment_export": dict(self.experiment_export),
            "leak_findings": self.leak_findings,
        }


class _Log:
    def __init__(self, path: Path, echo: Callable[[str], None] | None) -> None:
        self.path = path
        self.echo = echo
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: str, **fields: Any) -> None:
        line = {"at": _utc_now(), "event": event, **fields}
        with self._lock:
            with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(portable_data(json.loads(json.dumps(line, default=str))), sort_keys=True) + "\n")
            if self.echo:
                detail = ", ".join(f"{k}={v}" for k, v in fields.items())
                self.echo(f"[grid] {event}: {detail}")


def _record_attempt(paths: GridPaths, spec: RunSpec) -> int | None:
    try:
        rec = json.loads((paths.runs / spec.run_id / RUN_RECORD_FILE).read_text(encoding="utf-8"))
        return int(rec["extra"]["experiment_run"]["attempt"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


_WORKER_BOOT = (
    "import sys; sys.path.insert(0, {harness!r}); "
    "from aspire_sysid.experiment.worker import main; sys.exit(main(sys.argv[1:]))"
)


def _worker_command(exp: Experiment, spec: RunSpec, attempt: int, opts: RunOptions) -> list[str]:
    options = {
        "dry_run": opts.dry_run,
        "octave": opts.octave,
        "plots": opts.plots,
        "fsync": opts.fsync,
        "tasks_root": str(exp.tasks_root),
        "workspace_root": str(exp.workspace_root),
        "agent_python": exp.agent_python,
        "dry_run_pause_s": opts.dry_run_pause_s,
    }
    boot = _WORKER_BOOT.format(harness=str(HARNESS_DIR))
    return [worker_executable(), "-c", boot, str(exp.dir), spec.run_id, str(attempt), json.dumps(options), str(os.getpid())]


def _run_in_worker(exp: Experiment, paths: GridPaths, spec: RunSpec, attempt: int, opts: RunOptions,
                   procs: list[subprocess.Popen], stop: threading.Event, job: WorkerJob) -> tuple[int, str]:
    """Start one worker without the API key in its environment; the key goes through its standard input."""
    log_path = paths.logs / f"{spec.run_id}__attempt{attempt}.log"
    if stop.is_set():
        return -1, str(log_path)
    with open(log_path, "w", encoding="utf-8", newline="\n") as fh:
        proc = subprocess.Popen(_worker_command(exp, spec, attempt, opts), stdin=subprocess.PIPE, stdout=fh,
                                stderr=subprocess.STDOUT, env=worker_environment(), text=True)
        procs.append(proc)
        job.adopt(proc)
        try:
            assert proc.stdin is not None
            proc.stdin.write(json.dumps({"api_key": opts.api_key}) + "\n")
            proc.stdin.close()
        except OSError:
            pass
        code = proc.wait()
    return code, str(log_path)


def run_grid(
    exp: Experiment,
    *,
    opts: RunOptions | None = None,
    resume: bool = False,
    concurrency: int | None = None,
    in_process: bool | None = None,
    echo: Callable[[str], None] | None = None,
) -> GridResult:
    """Execute the grid of ``exp`` (module docstring). 

    ``resume`` archives interrupted runs and continues; without it the grid refuses to start when
    any run folder exists. ``concurrency`` overrides the experiment's; ``in_process`` executes the
    runs in this process one after the other (default: when ``opts.provider_factory`` is set).
    Exceptions of a run executed in this process that are not ordinary errors (``KeyboardInterrupt``,
    ``SystemExit``, or a simulated crash in the tests) propagate after the lock is released; the run
    stays interrupted. Returns the :class:`GridResult`.
    """
    opts = opts or RunOptions()
    paths = grid_paths(exp, opts.dry_run)
    paths.base.mkdir(parents=True, exist_ok=True)
    log = _Log(paths.logs / "grid.jsonl", echo)
    acquire_lock(paths.lock, log=lambda text: log("lock_replaced", note=text))
    result = GridResult()
    try:
        states = [run_state(paths, s) for s in exp.grid()]
        existing = [s.spec.run_id for s in states if s.state != "planned"]
        if existing and not resume:
            raise GridError(
                f"{len(existing)} run folder(s) exist already in {paths.runs} (for example {existing[0]}); "
                "use --resume to continue the grid (finished runs are never repeated)"
            )
        log("grid_start", experiment=exp.id, task=exp.task, dry_run=opts.dry_run, runs=len(states), resume=resume, pid=os.getpid())
        todo: list[tuple[RunSpec, int]] = []
        for st in states:
            if st.state == "finished":
                result.skipped_finished.append(st.spec.run_id)
                if not st.export_complete:
                    alive = running_process(paths, st.spec)
                    if alive is not None:  # its worker may still be writing the exports
                        result.still_running.append({"run_id": st.spec.run_id, **alive})
                        log("export_not_repaired", run=st.spec.run_id, pid=alive["pid"], note="the run's process still runs")
                        continue
                    run_exports(paths.runs / st.spec.run_id, exp, opts)
                    result.exports_completed.append(st.spec.run_id)
                    log("export_completed", run=st.spec.run_id)
                continue
            if st.state == "interrupted":
                alive = running_process(paths, st.spec)
                if alive is not None:
                    result.still_running.append({"run_id": st.spec.run_id, **alive})
                    log("run_still_running", run=st.spec.run_id, pid=alive["pid"], host=alive["host"],
                        note="not archived and not repeated; resume again after that process has ended")
                    continue
                dest = archive_interrupted(exp, paths, st)
                result.archived.append(dest.name)
                log("interrupted_run_archived", run=st.spec.run_id, folder=str(dest))
                st = run_state(paths, st.spec)
            todo.append((st.spec, st.next_attempt))
        paths.runs.mkdir(parents=True, exist_ok=True)
        inproc = (opts.provider_factory is not None) if in_process is None else in_process
        if inproc:
            for spec, attempt in todo:
                log("run_start", run=spec.run_id, attempt=attempt, mode="in-process")
                try:
                    summary = execute_run(exp, spec, attempt=attempt, runs_dir=paths.runs, opts=opts)
                except Exception as exc:  # noqa: BLE001 - one failed run does not stop the grid; it stays interrupted
                    result.failed.append({"run_id": spec.run_id, "attempt": attempt, "error": f"{type(exc).__name__}: {exc}"})
                    log("run_failed", run=spec.run_id, attempt=attempt, error=f"{type(exc).__name__}: {exc}")
                    continue
                result.executed.append(summary)
                log("run_end", run=spec.run_id, attempt=attempt, outcome=summary.outcome, cost_usd=summary.cost_usd,
                    leak_findings=len(summary.leak_findings))
        else:
            procs: list[subprocess.Popen] = []
            stop = threading.Event()
            n = max(1, concurrency or exp.concurrency)

            worker_job = WorkerJob()

            def job(item: tuple[RunSpec, int]) -> None:
                spec, attempt = item
                log("run_start", run=spec.run_id, attempt=attempt, mode="worker process")
                code, log_path = _run_in_worker(exp, paths, spec, attempt, opts, procs, stop, worker_job)
                st = run_state(paths, spec)
                if st.state == "finished" and _record_attempt(paths, spec) != attempt:
                    result.failed.append({"run_id": spec.run_id, "attempt": attempt,
                                          "error": f"the run record belongs to attempt {_record_attempt(paths, spec)}, not to attempt {attempt}"})
                    log("run_failed", run=spec.run_id, attempt=attempt, exit_status=code, worker_log=log_path, note="record of another attempt")
                elif st.state == "finished":
                    summary = summary_of_record(paths.runs / spec.run_id)
                    result.executed.append(summary)
                    log("run_end", run=spec.run_id, attempt=attempt, outcome=summary.outcome, cost_usd=summary.cost_usd,
                        leak_findings=len(summary.leak_findings), exit_status=code)
                else:
                    result.failed.append({"run_id": spec.run_id, "attempt": attempt, "error": f"worker exit status {code}; see {log_path}"})
                    log("run_failed", run=spec.run_id, attempt=attempt, exit_status=code, worker_log=log_path)

            pool = ThreadPoolExecutor(max_workers=n)
            try:
                futures = [pool.submit(job, item) for item in todo]
                for f in futures:
                    f.result()
            except BaseException:
                stop.set()
                for p in procs:
                    if p.poll() is None:
                        p.terminate()
                raise
            finally:
                pool.shutdown(wait=True, cancel_futures=True)
                worker_job.close()
        try:
            result.experiment_export = export_experiment_matlab(exp, paths, opts)
            log("experiment_export", **{k: v for k, v in result.experiment_export.items() if k in ("status", "folder", "added", "verified")})
        except Exception as exc:  # noqa: BLE001 - the run records are complete; the export can be repeated
            result.experiment_export = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            log("experiment_export_failed", error=f"{type(exc).__name__}: {exc}")
        log("grid_end", executed=len(result.executed), failed=len(result.failed), skipped_finished=len(result.skipped_finished),
            leak_findings=len(result.leak_findings))
    finally:
        release_lock(paths.lock)
    return result
