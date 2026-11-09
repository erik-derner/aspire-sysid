"""One autonomous run of an experiment: from the empty run folder to the record and the exports.

A run produces every artifact (round, record, exports), and the transcripts are searched
automatically for test values and recording names.

:func:`execute_run` performs, for one :class:`~aspire_sysid.experiment.config.RunSpec`:

1. creates the run folder ``experiments/<id>/runs/<run-id>/`` and writes ``run_start.json`` (the
   attempt number, a random token, the working directory and the identity of the process: number,
   host, start time); a run folder without a run record is an interrupted or running run
   (:mod:`aspire_sysid.experiment.grid`). Before each later write into the run folder (pool
   snapshot, workspace copy, run record, exports) the runner checks that ``run_start.json`` still
   carries its token, and stops with :class:`OwnershipError` otherwise, so that an execution
   never writes into the folder of another attempt;
2. creates the working directory under the workspace root, outside every repository
   (:mod:`aspire_sysid.experiment.workspace`), inspects and probes the agent's interpreter, renders
   the brief and the prompts and provisions the working directory;
3. runs the round with the transcript writer as event sink, the round budget of the
   task or of the experiment, and the evaluation of the checked candidates as callback;
   at the end of the round it takes the snapshot of ``models/`` (``pools/v1/``);
4. copies the final working directory into ``workspace/`` of the run folder;
5. runs the **leak scan** (:func:`aspire_sysid.evaluate.leaks.scan_for_sealed_leaks`) on the
   transcript and on every file of the working directory that the agent wrote or changed:
   recording names, sealed paths and file names, test rows, test values and the reference
   expression; the findings go into the run record and into the summary of the grid;
6. writes the run record with the fields of the experiment in ``extra.experiment_run``:
   experiment, dry run, run index, attempt, agent interpreter, shell environment adjustments, web
   backends, budget override and workspace copy, and with the leak scan in ``extra.leak_scan``.
   The run record with its final outcome marks the run as finished;
7. writes the exports (Python, and Matlab unless deferred) into ``export/`` with
   ``export/status.json``; a run whose pool has no evaluated candidate has no export, and the
   status file says why.

**Shell environment of the agent.** The environment of the agent's commands is derived from the
harness's environment without ``PYTHONPATH``, ``PYTHONHOME``, ``PYTHONSTARTUP``, ``PYTHONUSERBASE``,
``VIRTUAL_ENV`` and the installation targets of ``pip`` (``PIP_TARGET``, ``PIP_PREFIX``, ``PIP_ROOT``,
``PIP_USER``), so that no setting of the harness's own Python reaches the agent;
credentials are removed by the shell policy (:mod:`aspire_sysid.agent.policy`). Packages installed by the
agent go into a folder of the run's own attempt (``PIP_TARGET`` and ``PYTHONPATH`` point to
``<attempt>/packages``), so that one run's installations never change the environment of a later
or concurrent run, and the runs stay comparable.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import shutil
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from ..portable import portable_data
from ..agent import RoundLabels, load_tool_config, probe_environment, run_round
from ..agent.prices import PriceTable, default_price_table
from ..agent.providers import Provider, make_provider
from ..agent.tools import WebBackends
from ..brief import provision_workspace, render_run_texts
from ..evaluate import evaluate_pool
from ..evaluate.leaks import scan_for_sealed_leaks, sealed_fingerprint
from ..record import RUN_RECORD_FILE, TRANSCRIPT_FILE, RoundEntry, TranscriptWriter, snapshot_pool, write_run_record
from ..task import load_task
from ..task.schema import TaskSpec
from .agentenv import inspect_agent_interpreter
from .dryrun import dry_run_provider
from .config import Experiment, RunSpec
from .procs import process_identity
from .web import real_web_backends, web_backends_record
from .workspace import check_workspace_root, claim_attempt_folder, copy_workspace, experiment_instance, opaque_attempt_folder

__all__ = [
    "RUN_START_FILE",
    "EXPORT_STATUS_FILE",
    "ProviderFactory",
    "RunOptions",
    "RunSummary",
    "agent_base_environment",
    "execute_run",
    "OwnershipError",
    "run_exports",
    "leak_scan",
    "summary_of_record",
]

RUN_START_FILE = "run_start.json"
EXPORT_STATUS_FILE = "status.json"

ProviderFactory = Callable[[RunSpec, TaskSpec], Provider]
"""``factory(spec, task)`` returns the provider of one run (tests inject scripted providers)."""

_STRIPPED_VARIABLES = (
    "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE", "VIRTUAL_ENV",
    "PIP_TARGET", "PIP_PREFIX", "PIP_ROOT", "PIP_USER",
)


@dataclass
class RunOptions:
    """Settings of the runs of one grid execution.

    ``dry_run`` replaces the language model by the scripted agent of
    :mod:`aspire_sysid.experiment.dryrun`; ``provider_factory`` replaces it by any provider (tests);
    ``price_table`` replaces ``aspire/configs/prices.yaml`` (tests); ``octave`` and ``plots``
    override the experiment's settings; ``web`` replaces the web backends
    (default: fetch only in real runs, none in dry runs); ``fsync`` synchronizes
    every transcript line to the disk; ``api_key`` is handed to the provider object of a real run
    (never to an environment); ``dry_run_pause_s`` makes the scripted agent of a dry run wait in a
    shell command (interruption tests). 
    """

    dry_run: bool = False
    provider_factory: ProviderFactory | None = None
    price_table: PriceTable | None = None
    octave: bool | None | str = "experiment"
    plots: bool | None = None
    web: WebBackends | None = None
    fsync: bool = True
    api_key: str | None = field(default=None, repr=False)
    dry_run_pause_s: float = 0.0


@dataclass
class RunSummary:
    """The result of one run for the summary of the grid. """

    run_id: str
    run_dir: str
    outcome: str
    turns: int = 0
    cost_usd: float = 0.0
    leak_findings: list[dict[str, str]] = field(default_factory=list)
    exports: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form."""
        return {
            "run_id": self.run_id, "run_dir": self.run_dir, "outcome": self.outcome, "turns": self.turns,
            "cost_usd": self.cost_usd, "leak_findings": list(self.leak_findings), "exports": dict(self.exports), "error": self.error,
        }


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _dump(data: Any) -> str:
    from ..evaluate.pool import clean_json

    return json.dumps(portable_data(clean_json(data)), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False, default=str) + "\n"


def agent_base_environment(packages_dir: Path | None, environ: Mapping[str, str] | None = None) -> tuple[dict[str, str], dict[str, Any]]:
    """The environment from which the agent's shell environment is derived (module docstring).

 Returns the environment and the record of the adjustments.
    """
    src = os.environ if environ is None else environ
    removed = sorted(k for k in src if k.upper() in _STRIPPED_VARIABLES)
    env = {k: v for k, v in src.items() if k not in removed}
    note: dict[str, Any] = {"removed_variables": removed, "package_target": None}
    if packages_dir is not None:
        env["PIP_TARGET"] = str(packages_dir)
        env["PYTHONPATH"] = str(packages_dir)
        note["package_target"] = str(packages_dir)
        note["package_target_note"] = "packages installed by the agent go into this folder of the run's attempt (PIP_TARGET, PYTHONPATH)"
    return env, note


class OwnershipError(RuntimeError):
    """The run folder no longer belongs to this execution (another attempt took it). """


def _assert_owner(run_dir: Path, token: str) -> None:
    try:
        start = json.loads((run_dir / RUN_START_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        start = {}
    if start.get("token") != token:
        raise OwnershipError(
            f"{run_dir} now belongs to attempt {start.get('attempt')} (token differs); this execution writes nothing more there"
        )


def leak_scan(task: TaskSpec, run_dir: Path, workspace: Path, manifest: Any) -> dict[str, Any]:
    """Search the transcript and the files the agent wrote or changed for sealed information.

 Returns
    ``{"clean", "findings", "scanned", "not_scanned", "method"}``; ``not_scanned`` lists the files
    above 20 MB and the unreadable ones with the reason.
    """
    provisioned = {f.name: f.sha256 for f in getattr(manifest, "files", ())}
    items: list[Any] = []
    scanned: list[str] = []
    not_scanned: list[dict[str, Any]] = []
    transcript = run_dir / TRANSCRIPT_FILE
    if transcript.is_file():
        items.append(transcript)
        scanned.append(TRANSCRIPT_FILE)
    if workspace.is_dir():
        for p in sorted(workspace.rglob("*")):
            if not p.is_file() or p.is_symlink():
                continue
            rel = p.relative_to(workspace).as_posix()
            if "__pycache__" in rel.split("/"):
                continue
            try:
                size = p.stat().st_size
                if size > 20_000_000:
                    not_scanned.append({"path": f"workspace/{rel}", "bytes": size, "reason": "larger than 20000000 bytes"})
                    continue
                digest = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError as exc:
                not_scanned.append({"path": f"workspace/{rel}", "reason": f"cannot be read: {exc}"})
                continue
            if provisioned.get(rel) == digest:
                continue  # provisioned by the harness and unchanged
            items.append((f"workspace/{rel}", p.read_bytes().decode("utf-8", errors="replace")))
            scanned.append(f"workspace/{rel}")
    findings = scan_for_sealed_leaks(task, items, fingerprint=sealed_fingerprint(task))
    return {
        "clean": not findings,
        "findings": [{"kind": f.kind, "where": f.where.replace(str(run_dir), "<run>"), "detail": f.detail} for f in findings],
        "scanned": scanned,
        "not_scanned": not_scanned,
        "method": (
            "aspire_sysid.evaluate.leaks.scan_for_sealed_leaks: sealed paths and file names, recording names and their stems, "
            "digests of sealed files, test rows, test values with at least 6 significant digits, the reference expression"
        ),
    }


def _octave_setting(exp: Experiment, opts: RunOptions) -> bool | None:
    return exp.exports.octave if opts.octave == "experiment" else opts.octave  # type: ignore[return-value]


def run_exports(run_dir: Path, exp: Experiment, opts: RunOptions) -> dict[str, Any]:
    """Write the Python and Matlab exports of a finished run and ``export/status.json``.


    An existing ``export/`` folder without a status file (an interrupted export) is removed first.
    Returns the status.
    """
    from ..export import export_matlab, export_python
    from ..record import RecordError

    out = run_dir / "export"
    status_path = out / EXPORT_STATUS_FILE
    if status_path.is_file():
        return json.loads(status_path.read_text(encoding="utf-8"))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    status: dict[str, Any] = {"written_at": _utc_now()}
    if exp.exports.python:
        try:
            res = export_python(run_dir, out / "python")
            status["python"] = {"status": "written", "file": res.path.relative_to(run_dir).as_posix(),
                                "labels": list(res.labels), "verified": res.verified}
        except RecordError as exc:
            status["python"] = {"status": "not produced", "reason": str(exc)}
    else:
        status["python"] = {"status": "not requested"}
    if exp.exports.matlab:
        try:
            rep = export_matlab([run_dir], out / "matlab", octave=_octave_setting(exp, opts))
            status["matlab"] = {
                "status": "written",
                "files": list(rep.files),
                "models_in_framework": sum(1 for m in rep.models if m.in_framework),
                "models": len(rep.models),
                "verified": rep.verified,
                "skipped": list(rep.skipped),
                "octave": rep.octave,
            }
        except RecordError as exc:
            status["matlab"] = {"status": "not produced", "reason": str(exc)}
    else:
        status["matlab"] = {"status": "deferred", "reason": "exports.matlab is false; run `aspire export --matlab` later"}
    status_path.write_text(_dump(status), encoding="utf-8", newline="\n")
    return status


def summary_of_record(run_dir: Path) -> RunSummary:
    """The :class:`RunSummary` of a finished run, read from its record and export status.  """
    rec = json.loads((run_dir / RUN_RECORD_FILE).read_text(encoding="utf-8"))
    camp = (rec.get("extra") or {}).get("experiment_run") or {}
    leak = (rec.get("extra") or {}).get("leak_scan") or {}
    status_path = run_dir / "export" / EXPORT_STATUS_FILE
    exports = json.loads(status_path.read_text(encoding="utf-8")) if status_path.is_file() else {"status": "missing"}
    return RunSummary(
        run_id=str(camp.get("run_id") or rec.get("run_id")),
        run_dir=str(run_dir),
        outcome=str(rec.get("outcome")),
        turns=int(rec["consumption"]["turns"]),
        cost_usd=float(rec["consumption"]["cost_usd"]),
        leak_findings=list(leak.get("findings") or []),
        exports={k: (v.get("status") if isinstance(v, dict) else v) for k, v in exports.items() if k in ("python", "matlab", "status")},
    )


def _key_status(opts: RunOptions) -> str:
    unused = opts.dry_run or opts.provider_factory is not None
    if opts.api_key:
        return "received as an argument (unused: dry run or injected provider)" if unused else "received as an argument and given to the provider object"
    return "not needed (dry run or injected provider)" if unused else "not received; the provider reads its environment variable"


def execute_run(exp: Experiment, spec: RunSpec, *, attempt: int, runs_dir: Path, opts: RunOptions) -> RunSummary:
    """Execute one run and return its summary (module docstring). 

    ``runs_dir`` is the folder of the run folders; the run folder ``<runs_dir>/<run-id>`` must not
    exist. Exceptions of the harness propagate: the run folder then has no run record and the grid
    treats the run as interrupted.
    """
    rid = spec.run_id
    run_dir = runs_dir / rid
    root = check_workspace_root(exp.workspace_root)
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} exists; a run folder is never overwritten")
    attempt_dir = opaque_attempt_folder(root, dry_run=opts.dry_run)
    token = uuid.uuid4().hex
    ident = process_identity()
    # the attempt folder first: when it cannot be claimed, no run folder exists that would look interrupted
    claim_attempt_folder(attempt_dir, {"token": token})
    try:
        run_dir.mkdir(parents=True)
    except FileExistsError:
        raise FileExistsError(f"{run_dir} exists; a run folder is never overwritten") from None
    workspace = attempt_dir / "workspace"
    packages = attempt_dir / "packages"
    start = {
        "run_id": rid, "experiment": exp.id, "experiment_folder": str(exp.dir), "attempt": attempt, "token": token,
        "started_at": _utc_now(), **ident, "workspace": str(workspace), "attempt_folder": str(attempt_dir),
        "experiment_instance": experiment_instance(exp.dir), "dry_run": opts.dry_run,
        "api_key": _key_status(opts),
    }
    (run_dir / RUN_START_FILE).write_text(_dump(start), encoding="utf-8", newline="\n")

    task = load_task(exp.task_dir)
    cfg = load_tool_config()
    exe = exp.agent_python or sys.executable
    interpreter = inspect_agent_interpreter(exe)
    probe = probe_environment(exe)
    texts = render_run_texts(task, cfg, probe)
    manifest = provision_workspace(task, workspace)
    packages.mkdir(parents=True, exist_ok=True)
    base_env, env_note = agent_base_environment(packages)
    if opts.provider_factory is not None:
        provider = opts.provider_factory(spec, task)
    elif opts.dry_run:
        provider = dry_run_provider(task, exp.model, pause_s=opts.dry_run_pause_s)
    else:
        provider = make_provider(exp.model, **({"api_key": opts.api_key} if opts.api_key else {}))
    if opts.web is not None:
        web = opts.web
    elif not opts.dry_run and opts.provider_factory is None:
        web = real_web_backends()
    else:
        web = WebBackends()
    prices = opts.price_table or default_price_table()
    limits = exp.budget or task.budget.round
    seeds = {"run_index": spec.index, "attempt": attempt}
    writer = TranscriptWriter(
        run_dir / TRANSCRIPT_FILE,
        header={
            "run_id": rid, "experiment": exp.id, "dry_run": opts.dry_run, "task": task.id,
            "configuration": cfg.name, "model": provider.model_id, "vendor": provider.vendor, "attempt": attempt, "seeds": seeds,
        },
        fsync=opts.fsync,
    )
    try:
        result = run_round(
            provider, texts.system_prompt, texts.first_user_message, workspace, task, cfg, limits, writer,
            evaluate_callback=lambda report, labels: evaluate_pool(task, report),
            labels=RoundLabels(task=task.id),
            price_table=prices,
            web=web,
            probe=probe,
            python_executable=exe,
            helper_system_prompt=texts.helper_system_prompt,
            base_env=base_env,
        )
    finally:
        writer.close()
    _assert_owner(run_dir, token)
    snapshot = snapshot_pool(run_dir, workspace, 1)
    copy = copy_workspace(workspace, run_dir / "workspace")
    leaks = leak_scan(task, run_dir, workspace, manifest)
    output = task.column(task.output)
    _assert_owner(run_dir, token)
    fields = {
        "experiment": exp.to_dict(),
        "experiment_id": exp.id,
        "dry_run": opts.dry_run,
        "run_id": rid,
        "task_id": spec.task,
        "run_index": spec.index,
        "runs": exp.runs,
        "attempt": attempt,
        "token": token,
        "output": {"name": output.name, "unit": output.unit},
        "pool_cap": task.pool_cap,
        "round_budget": {"turns": limits.turns, "seconds": limits.seconds, "usd": limits.usd,
                         "source": "experiment override" if exp.budget is not None else "task"},
        "workspace": {"path": str(workspace), "root": str(root), "outside_repository": True, "copy": copy.to_dict(),
                      "kept": exp.keep_workspaces},
        "agent_interpreter": interpreter.to_dict(),
        "shell_environment": env_note,
        "web_backends": web_backends_record(web, provider.vendor),
        "provider": {"vendor": provider.vendor, "model": provider.model_id},
    }
    write_run_record(
        run_dir, task, configuration=cfg, model_id=provider.model_id, vendor=provider.vendor,
        rounds=[RoundEntry(result, workspace, pool_snapshot=snapshot)], run_texts=texts, manifest=manifest, run_id=rid, seeds=seeds,
        probe=probe, price_table=prices, plots=exp.plots if opts.plots is None else opts.plots,
        extra={"experiment_run": fields, "leak_scan": leaks},
    )
    _assert_owner(run_dir, token)
    exports = run_exports(run_dir, exp, opts)
    if not exp.keep_workspaces:
        shutil.rmtree(attempt_dir, ignore_errors=True)
    summary = summary_of_record(run_dir)
    summary.exports = {k: (v.get("status") if isinstance(v, dict) else v) for k, v in exports.items() if k in ("python", "matlab")}
    return summary
