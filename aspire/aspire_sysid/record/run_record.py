"""The run record: one JSON file per run, from which the evaluation can be recomputed offline.

The record contains the task, the model identifier and the tool configuration, the system prompt
and the brief with a cryptographic hash of each, software and code revisions, random seeds, turns
and tokens, elapsed execution time, the cost from a dated price schedule, user waiting time and
execution excess separately, and the dataset provenance. The exports contain the evaluation
settings or a reference to the saved record, which is retained without overwriting earlier
results. The evaluation is a pure function of the task specification and the candidate files,
so every diagnostic can be recomputed from the record.


**Run folder.** :func:`write_run_record` writes, into the run folder ``<run-dir>``:

====================================  ===========================================================
``run_record.json``                   the run record (fields below)
``provenance.json``                   the dataset provenance record (:mod:`.provenance`)
``pools/v<k>/models/``                verbatim copies of every file of ``models/`` at the end of
                                      the round that produced pool version ``k``
``evaluation/v<k>/``                  the evaluation reports of pool version ``k`` (``evaluation.json``, ``evaluation.md``, ``permitted.json``,
                                      ``permitted.md``, ``plots/``)
``transcript.jsonl``                  the transcript (:mod:`.transcript`), written during the run
``workspace/``                        the working directory (the experiment runner may keep it
                                      elsewhere; the record states where it was)
====================================  ===========================================================

Nothing is overwritten: a pool version or run record that exists already is an error
(:class:`RecordExistsError`). The run folder is for the user only: it contains the results on sealed
data and the recording names; it is never inside the working directory.

**Fields of** ``run_record.json`` (format version :data:`RUN_RECORD_FORMAT_VERSION`):
``run_id``; ``created_at`` (UTC); ``task`` (identifier, title, formulation, folder, the SHA-256
digest of the task specification and the digests of its files: ``task.yaml`` and the
agent-visible files in ``spec_sha256``, the sealed files in ``sealed_sha256``); ``configuration``
(tool configuration with its settings); ``model`` (identifier and vendor); ``harness`` (version,
code revision: git commit and whether the working tree had uncommitted changes of tracked
files); ``software`` (Python, NumPy, SciPy, SymPy, PyYAML, Matplotlib, platform); ``environment``
(the probe of the agent's interpreter); ``texts`` (the system prompt and the brief, each with its
SHA-256 digest, the first user message and the helper prompt); ``workspace_manifest``;
``seeds``; ``price``; ``budget`` and ``consumption`` (turns, tokens, cost, elapsed execution
time, user waiting time, excess, time of the final checks and of the evaluation); ``outcome``
and ``termination_reason``; ``rounds`` (per round: labels, outcome, limit, consumption, candidate
files, check report, the folder and SHA-256 digests of the copied candidate files, the evaluation
report and its digest); ``provenance`` (the dataset provenance record); ``transcript`` (file and
digest).

:func:`recompute_evaluation` re-runs the evaluation offline from the copied candidate files
and the task, and compares the result with the stored report.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..portable import local_path, portable_data
from .. import __version__
from ..evaluate import PoolEvaluation, evaluate_pool, to_json, write_reports
from ..evaluate.sealed import sealed_dataset_records, sealed_reference_record
from ..model import check_workspace
from ..model.checks import MODELS_DIR, CheckReport
from ..task import load_task
from ..task.schema import Limits, TaskSpec
from ..task.changes import TaskChange, apply_changes
from .provenance import dataset_provenance, file_sha256

__all__ = [
    "RUN_RECORD_FORMAT_VERSION",
    "RUN_RECORD_FILE",
    "PROVENANCE_FILE",
    "TRANSCRIPT_FILE",
    "POOLS_DIR",
    "EVALUATION_DIR",
    "TERMINATION_REASONS",
    "RecordError",
    "RecordExistsError",
    "RecordMismatchError",
    "RoundEntry",
    "code_revision",
    "harness_identity",
    "HARNESS_PATHS",
    "software_versions",
    "task_digests",
    "write_run_record",
    "load_run_record",
    "pool_dir",
    "evaluation_dir",
    "round_of_pool",
    "record_task",
    "recompute_evaluation",
    "stored_evaluation",
    "snapshot_pool",
    "SNAPSHOT_FILE",
    "applied_task_changes",
    "is_interactive",
]

RUN_RECORD_FORMAT_VERSION = 1
"""Version of the run record format (module docstring)."""

RUN_RECORD_FILE = "run_record.json"
PROVENANCE_FILE = "provenance.json"
TRANSCRIPT_FILE = "transcript.jsonl"
POOLS_DIR = "pools"
EVALUATION_DIR = "evaluation"

TERMINATION_REASONS: dict[str, str] = {
    "completed": "the agent sent the completion message DONE and at least one candidate within the pool limit passed the file and expression checks",
    "checks_failed_twice": "the agent sent DONE twice, and after the one permitted correction no candidate passed the file and expression checks",
    "budget_turns": "the turn limit was reached",
    "budget_time": "the limit on elapsed execution time was reached",
    "budget_cost": "the cost limit was reached",
    "error": "a language-model request failed",
    "answered": "the agent's answer ended the analysis exchange",
}
"""Termination reason of each round outcome."""


class RecordError(ValueError):
    """A run record is missing, malformed or does not match the task. """


class RecordExistsError(RecordError):
    """A record file or pool version exists already; records are never overwritten."""


class RecordMismatchError(RecordError):
    """The evaluation recomputed from the record differs from the stored report."""

    def __init__(self, message: str, differences: list[str]):
        super().__init__(message + ("\n" + "\n".join(f"  - {d}" for d in differences[:20]) if differences else ""))
        self.differences = differences


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _dump(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


# ---------------------------------------------------------------------------------------------
# Versions and digests
# ---------------------------------------------------------------------------------------------

_REVISION_CACHE: dict[str, dict[str, Any]] = {}


HARNESS_PATHS: tuple[str, ...] = ("aspire", "tasks")
"""Folders of the repository that make up the harness identity: the harness itself and the task
store. Changes elsewhere (for example in ``experiments/``) do not change what a run computes."""


def harness_identity(repo_root: str | Path, paths: tuple[str, ...] = HARNESS_PATHS) -> dict[str, Any]:
    """The identity of the harness in the repository ``repo_root``.

    ``trees`` maps each folder of ``paths`` to the git tree hash of that folder in the commit
    ``HEAD`` (``git rev-parse HEAD:<folder>``; ``None`` for a folder that the commit lacks);
    ``dirty`` is true when ``git status --porcelain -- <paths>`` lists any change in these folders,
    tracked or untracked (ignored files such as ``__pycache__`` are not listed); ``changed`` lists
    those entries (at most 50); ``changes_sha256`` is the SHA-256 digest of the changes
    (``git diff HEAD --binary`` of these folders and the names and contents of the untracked
    files), ``None`` when there are none. Two runs have the same harness identity when the trees,
    the dirty flags and the change digests are equal.
    """
    root = Path(repo_root)

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=30, check=False)

    trees: dict[str, str | None] = {}
    for folder in paths:
        r = git("rev-parse", f"HEAD:{folder}")
        trees[folder] = r.stdout.strip() if r.returncode == 0 else None
    st = git("status", "--porcelain", "--", *paths)
    if st.returncode != 0:
        raise subprocess.SubprocessError(st.stderr.strip())
    changed = [line for line in st.stdout.splitlines() if line.strip()]
    changes_sha256 = None
    if changed:
        h = hashlib.sha256()
        diff = subprocess.run(["git", "diff", "HEAD", "--binary", "--", *paths], cwd=root, capture_output=True, timeout=60, check=False)
        h.update(diff.stdout)
        for line in sorted(changed):
            if line.startswith("??"):
                rel = line[3:].strip().strip('"')
                target = root / rel
                files = sorted(q for q in target.rglob("*") if q.is_file()) if target.is_dir() else [target]
                for f in files:
                    h.update(f.relative_to(root).as_posix().encode("utf-8") + b"\0")
                    try:
                        h.update(f.read_bytes())
                    except OSError:
                        h.update(b"<unreadable>")
        changes_sha256 = h.hexdigest()
    return {"paths": list(paths), "trees": trees, "dirty": bool(changed), "changes_sha256": changes_sha256, "changed": changed[:50]}


def code_revision(path: str | Path | None = None) -> dict[str, Any]:
    """The code revision of the harness: harness identity, git commit and dirty flags.

    ``path`` is a folder inside the repository (default: the package folder). ``identity`` is
    :func:`harness_identity` of the repository (git tree hashes of ``aspire/`` and ``tasks/`` and
    whether these folders have changes), which identifies the code and the tasks of a run and is
    what the aggregation compares. ``commit`` (the commit ``HEAD``) and ``dirty`` (tracked files
    anywhere in the repository differ from it; ``git status --porcelain --untracked-files=no``) are
    recorded for information. Without git, or outside a repository, the values are ``None`` and
    ``note`` states why.
    """
    where = Path(path) if path is not None else Path(__file__).resolve().parents[1]
    key = str(where)
    if key in _REVISION_CACHE:
        return dict(_REVISION_CACHE[key])

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=where, capture_output=True, text=True, timeout=30, check=True).stdout.strip()

    try:
        commit = git("rev-parse", "HEAD")
        status = git("status", "--porcelain", "--untracked-files=no")
        top = git("rev-parse", "--show-toplevel")
        out = {"commit": commit, "dirty": bool(status), "identity": harness_identity(top), "source": "git", "note": None}
    except (OSError, subprocess.SubprocessError) as exc:
        out = {"commit": None, "dirty": None, "identity": None, "source": "git", "note": f"not available: {type(exc).__name__}"}
    _REVISION_CACHE[key] = out
    return dict(out)


def software_versions() -> dict[str, Any]:
    """Versions of the software that affects estimation or evaluation."""
    import matplotlib
    import numpy
    import scipy
    import sympy
    import yaml

    return {
        "aspire_sysid": __version__,
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "sympy": sympy.__version__,
        "pyyaml": yaml.__version__,
        "matplotlib": matplotlib.__version__,
        "platform": platform.platform(),
    }


def task_digests(task: TaskSpec) -> dict[str, Any]:
    """SHA-256 digests of the task specification.

    ``spec_sha256`` is the digest of the sorted list ``name:digest`` of ``task.yaml`` and the
    agent-visible files (training and validation data, supporting files); ``sealed_sha256`` that
    of the sealed test files and the reference file, whose digests come from the evaluation module
. ``files`` lists every digest.
    """
    files: dict[str, str] = {"task.yaml": file_sha256(task.task_dir / "task.yaml")}
    visible = [task.data.train_path] + ([task.data.val_path] if task.data.val_path is not None else []) + [c.path for c in task.context]
    for p in visible:
        try:
            rel = p.resolve().relative_to(task.task_dir.resolve()).as_posix()
        except ValueError:
            rel = str(p)
        files[rel] = file_sha256(p)
    sealed: dict[str, str] = {}
    for rec in sealed_dataset_records(task):
        sealed[rec.declared_file] = rec.sha256
    ref = sealed_reference_record(task)
    if ref is not None:
        sealed[ref["declared_file"]] = ref["sha256"]

    def digest(d: Mapping[str, str]) -> str:
        return hashlib.sha256("\n".join(f"{k}:{v}" for k, v in sorted(d.items())).encode("utf-8")).hexdigest()

    return {"spec_sha256": digest(files), "files": files, "sealed_sha256": digest(sealed), "sealed_files": sealed}


def _limits(lim: Limits | None) -> dict[str, Any] | None:
    return None if lim is None else {"turns": lim.turns, "seconds": lim.seconds, "usd": lim.usd}


def _seeds(task: TaskSpec, extra: Mapping[str, Any] | None) -> dict[str, Any]:
    from ..evaluate import reference as _ref

    reqs = {}
    for r in task.requirements:
        s = r.params.get("sampling") if isinstance(r.params, Mapping) else None
        if isinstance(s, Mapping) and "seed" in s:
            reqs[r.id] = s["seed"]
    return {
        "requirement_sampling": reqs,
        "reference_comparison": _ref.REFERENCE_SEED if task.sealed.reference is not None else None,
        "language_model": "none: the requests set no seed, and the responses of the language model are not reproducible",
        "harness": "none: the harness draws no other random numbers",
        "run": dict(extra or {}),
    }


# ---------------------------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------------------------


@dataclass
class RoundEntry:
    """One round (or analysis exchange) of a run, for the record.

    ``result`` is the :class:`~aspire_sysid.agent.loop.RoundResult`; ``pool_snapshot`` the folder
    written by :func:`snapshot_pool` at the end of the round (``pools/v<k>`` of the run folder; the
    normal case); ``workspace`` the working directory, whose ``models/`` folder is copied when the
    record is written only if no snapshot was taken (the record then states that the copy is
    later than the end of the round); ``evaluation`` the pool evaluation (default: the
    result's evaluation when it is a :class:`PoolEvaluation`); ``previous_labels`` the labels of
    the previous pool version (interactive operation); ``test_informed`` marks a round after the
    user has seen test results.

    Interactive operation also uses ``reports_dir``: the folder
    ``evaluation/v<k>`` of the run folder into which the session wrote the complete reports at the
    end of the round (labelled test-informed or not); the record then refers to them instead of
    writing them again. ``task_changes`` lists the user's task changes in force for the round
    (:meth:`aspire_sysid.task.changes.TaskChange.to_dict`); the record stores them as
    ``task_changes_in_force`` and :func:`recompute_evaluation` applies them to the task before it
    re-evaluates the pool ("It evaluates the current pool under the recorded task
    settings").
    """

    result: Any
    workspace: str | Path | None = None
    session: str = "session-1"
    round: int = 1
    pool_version: int = 1
    previous_labels: Sequence[str] = ()
    evaluation: PoolEvaluation | None = None
    test_informed: bool = False
    mode: str = "round"
    pool_snapshot: str | Path | None = None
    reports_dir: str | Path | None = None
    task_changes: Sequence[Mapping[str, Any]] = ()


def pool_dir(run_dir: str | Path, pool_version: int) -> Path:
    """Folder of the copied candidate files of pool version ``pool_version`` (contains ``models/``). """
    return Path(run_dir) / POOLS_DIR / f"v{int(pool_version)}"


def evaluation_dir(run_dir: str | Path, pool_version: int) -> Path:
    """Folder of the evaluation reports of pool version ``pool_version``. """
    return Path(run_dir) / EVALUATION_DIR / f"v{int(pool_version)}"


SNAPSHOT_FILE = "snapshot.json"
"""Manifest of a pool snapshot: the files with their SHA-256 digests, the source and the time."""


def snapshot_pool(run_dir: str | Path, workspace: str | Path, pool_version: int, *, session: str = "session-1",
                  round: int = 1) -> Path:
    """Copy ``models/`` of the working directory into ``pools/v<k>/models`` of the run folder.

    The harness preserves the earlier pools and never overwrites an earlier result. Called at the end of each round, before the agent can change the files again (the
    next round of interactive operation works in the same working directory). Every regular file is
    copied verbatim; links are listed, not followed. ``pools/v<k>/snapshot.json`` records the files
    with their digests, the source folder, the session, the round and the UTC time. Returns the
    snapshot folder, which :class:`RoundEntry` takes as ``pool_snapshot``. Raises
    :class:`RecordExistsError` when the pool version exists already.
    """
    dest = pool_dir(run_dir, pool_version)
    copy = _copy_models(Path(workspace), dest)
    manifest = {"pool_version": int(pool_version), "session": session, "round": round, "taken_at": _utc_now(),
                "taken": "at the end of the round", **copy}
    (dest / SNAPSHOT_FILE).write_text(_dump(portable_data(manifest)), encoding="utf-8", newline="\n")
    return dest


def _copy_models(workspace: Path, dest: Path) -> dict[str, Any]:
    """Copy every regular file of ``workspace/models`` verbatim; links are listed, not followed."""
    src = workspace / MODELS_DIR
    target = dest / MODELS_DIR
    if dest.exists():
        raise RecordExistsError(f"{dest} exists; a pool version is never overwritten")
    target.mkdir(parents=True)
    copied: dict[str, str] = {}
    skipped: list[str] = []
    if src.is_dir():
        for p in sorted(src.iterdir()):
            if p.is_symlink() or not p.is_file():
                skipped.append(p.name)
                continue
            shutil.copyfile(p, target / p.name)
            copied[p.name] = file_sha256(target / p.name)
    return {"files": copied, "not_copied": skipped, "source": str(src)}


def _check_record(report: CheckReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "passed": bool(report.passed),
        "order": list(report.order),
        "order_from_pool_file": report.order_from_pool,
        "evaluated": list(report.evaluated),
        "outside_limit": list(report.outside_limit),
        "issues": [{"rule": i.rule, "where": i.where, "message": i.message} for i in report.issues],
        "text": report.text(),
    }


def _round_record(entry: RoundEntry, run_dir: Path, task: TaskSpec, plots: bool) -> dict[str, Any]:
    res = entry.result
    rec: dict[str, Any] = {
        "session": entry.session,
        "round": entry.round,
        "mode": entry.mode,
        "pool_version": entry.pool_version,
        "previous_labels": list(entry.previous_labels),
        "test_informed": bool(entry.test_informed),
        "outcome": res.outcome,
        "termination_reason": TERMINATION_REASONS.get(res.outcome, res.outcome),
        "limit": None if res.limit is None else {"kind": res.limit.kind, "scope": res.limit.scope},
        "error": res.error,
        "consumption": {
            "turns": res.turns,
            "input_tokens": res.usage.input_tokens,
            "output_tokens": res.usage.output_tokens,
            "cached_input_tokens": res.usage.cached_input_tokens,
            "reasoning_tokens": res.usage.reasoning_tokens,
            "web_search_calls": res.usage.web_search_calls,
            "estimated_usage_turns": res.estimated_usage_turns,
            "cost_usd": res.cost_usd,
            "elapsed_s": res.elapsed_s,
            "waiting_s": res.waiting_s,
            "excess": dict(res.excess),
            "checks_s": res.checks_s,
            "evaluation_s": res.evaluation_s,
        },
        "correction_used": res.correction_used,
        "done_count": res.done_count,
        "reminder_sent": res.reminder_sent,
        "termination_message": res.termination_message,
        "helpers": [{"name": h.name, "turns": h.turns, "cost_usd": h.cost_usd, "ended": h.ended, "allowance": dict(h.allowance)} for h in res.helpers],
        "candidate_files": res.candidate_files.to_dict(),
        "check_report": _check_record(res.check_report),
        "evaluated_labels": list(res.evaluated_labels),
        "order_assigned_by_harness": res.order_assigned_by_harness,
        "final_text": res.final_text,
    }
    if entry.task_changes:
        rec["task_changes_in_force"] = [dict(c) for c in entry.task_changes]
    if entry.mode != "round":
        return rec
    ws = Path(entry.workspace) if entry.workspace is not None else None
    if entry.pool_snapshot is not None:
        snap = Path(entry.pool_snapshot)
        if snap.resolve() != pool_dir(run_dir, entry.pool_version).resolve():
            raise RecordError(f"the snapshot {snap} is not pools/v{entry.pool_version} of the run folder {run_dir}")
        manifest = json.loads((snap / SNAPSHOT_FILE).read_text(encoding="utf-8"))
        rec["pool"] = {"folder": snap.resolve().relative_to(Path(run_dir).resolve()).as_posix(), **manifest}
    elif ws is not None:
        dest = pool_dir(run_dir, entry.pool_version)
        copy = _copy_models(ws, dest)
        rec["pool"] = {"folder": dest.relative_to(run_dir).as_posix(), "taken": "when the run record was written (no end-of-round snapshot)",
                       **copy}
    else:
        rec["pool"] = None
    ev = entry.evaluation if entry.evaluation is not None else (res.evaluation if isinstance(res.evaluation, PoolEvaluation) else None)
    if ev is not None:
        out = evaluation_dir(run_dir, entry.pool_version)
        if entry.reports_dir is not None:
            # written by the session at the end of the round (interactive operation)
            if Path(entry.reports_dir).resolve() != out.resolve() or not (out / "evaluation.json").is_file():
                raise RecordError(f"the reports {entry.reports_dir} are not evaluation/v{entry.pool_version} of the run folder {run_dir}")
        else:
            if out.exists():
                raise RecordExistsError(f"{out} exists; an evaluation is never overwritten")
            write_reports(ev, task, out, plots=plots)
        data = ev.to_dict()
        rec["evaluation"] = {
            "folder": out.relative_to(run_dir).as_posix(),
            "report_file": (out / "evaluation.json").relative_to(run_dir).as_posix(),
            "report_sha256": file_sha256(out / "evaluation.json"),
            "permitted_file": (out / "permitted.json").relative_to(run_dir).as_posix(),
            "report": data,
        }
    else:
        rec["evaluation"] = None
    return rec


def write_run_record(
    run_dir: str | Path,
    task: TaskSpec,
    *,
    configuration: Any,
    model_id: str,
    rounds: Sequence[RoundEntry],
    run_texts: Any = None,
    manifest: Any = None,
    run_id: str | None = None,
    vendor: str | None = None,
    seeds: Mapping[str, Any] | None = None,
    probe: Any = None,
    price_table: Any = None,
    session_outcome: str | None = None,
    session_termination: str | None = None,
    plots: bool = True,
    extra: Mapping[str, Any] | None = None,
    session_totals: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the run record and its companion files into ``run_dir`` (module docstring).

    ``configuration`` is a :class:`~aspire_sysid.agent.config.ToolConfig` or its name; ``rounds``
    lists the rounds of the run in order; ``run_texts`` is the
    :class:`~aspire_sysid.brief.RunTexts` of the run and ``manifest`` the
    :class:`~aspire_sysid.brief.WorkspaceManifest` of the working directory (either may be
    ``None``; the record then says visibly that it was not supplied, ``"supplied": false``); ``probe`` the
    environment probe of the agent's interpreter; ``price_table`` the price schedule used
    (default: ``aspire/configs/prices.yaml``); ``seeds`` further seeds of the caller (the experiment
    runner). ``session_outcome`` and ``session_termination`` describe how a session of several
    rounds ended (interactive operation); for one round they are the round's.
    ``session_totals`` (interactive operation) are the totals of the whole session: the record then
    holds them as ``consumption.session`` (user waiting time inside and between rounds, harness
    time) next to the sums over the round entries, and ``consumption.summed_over`` says what the
    sums cover. Returns the record as written. Raises :class:`RecordExistsError` when ``run_record.json`` exists.
    """
    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)
    path = run / RUN_RECORD_FILE
    if path.exists():
        raise RecordExistsError(f"{path} exists; a run record is never overwritten")
    if not rounds:
        raise RecordError("a run record needs at least one round")
    cfg_name = configuration if isinstance(configuration, str) else getattr(configuration, "name", str(configuration))
    cfg_settings = None if isinstance(configuration, str) else (configuration.to_dict() if hasattr(configuration, "to_dict") else None)
    if price_table is None:
        from ..agent.prices import default_price_table

        price_table = default_price_table()
    try:
        p = price_table.price(model_id)
        price = {
            "model": p.model,
            "input_usd_per_mtok": p.input_usd_per_mtok,
            "output_usd_per_mtok": p.output_usd_per_mtok,
            "verified": p.verified.isoformat(),
            "source": p.source,
            "table_verified": price_table.verified.isoformat(),
            "table": price_table.origin,
        }
    except Exception as exc:  # noqa: BLE001 - recorded; the round itself refused an unpriced model
        price = {"model": model_id, "error": f"{type(exc).__name__}: {exc}"}

    round_records = [_round_record(e, run, task, plots) for e in rounds]
    totals = {"turns": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "elapsed_s": 0.0, "waiting_s": 0.0,
              "checks_s": 0.0, "evaluation_s": 0.0, "estimated_usage_turns": 0, "web_search_calls": 0}
    excess = {"turns": 0.0, "seconds": 0.0, "usd": 0.0}
    for rr in round_records:
        c = rr["consumption"]
        for k in totals:
            totals[k] += c[k]
        for k in excess:
            excess[k] += float(c["excess"].get(k, 0.0))
    totals["excess_by_round_sum"] = excess
    if session_totals is not None:
        totals["summed_over"] = (
            "the round and analysis-exchange entries: user waiting time and harness time inside them only; "
            "consumption.session holds the totals of the whole session"
        )
        totals["session"] = dict(session_totals)
    last = round_records[-1]
    provenance = dataset_provenance(task)
    (run / PROVENANCE_FILE).write_text(_dump(portable_data(provenance)), encoding="utf-8", newline="\n")
    texts: dict[str, Any] = {
        "supplied": False,
        "note": "not supplied by the caller: the system prompt, the brief and their SHA-256 digests are missing from this record"
        "; the digest of the system prompt is in the round_start events of the transcript",
    }
    if run_texts is not None:
        d = run_texts.to_dict()
        texts = {
            "supplied": True,
            "system_prompt": d["system_prompt"],
            "system_prompt_sha256": d["hashes"].get("system_prompt_sha256"),
            "brief": d["brief"],
            "brief_sha256": d["hashes"].get("brief_sha256"),
            "first_user_message": d["first_user_message"],
            "first_user_message_sha256": d["hashes"].get("first_user_message_sha256"),
            "helper_system_prompt": d["helper_system_prompt"],
            "helper_system_prompt_sha256": d["hashes"].get("helper_system_prompt_sha256"),
        }
    transcript = run / TRANSCRIPT_FILE
    record: dict[str, Any] = {
        "format_version": RUN_RECORD_FORMAT_VERSION,
        "kind": "aspire_run_record",
        "user_facing": "contains results on sealed test data and recording names; never shown to the agent",
        "run_id": run_id or run.name,
        "created_at": _utc_now(),
        "task": {
            "id": task.id,
            "title": task.title,
            "formulation": task.formulation,
            "folder": str(task.task_dir),
            **task_digests(task),
        },
        "configuration": {"name": cfg_name, "settings": cfg_settings},
        "model": {"id": model_id, "vendor": vendor},
        "harness": {"version": __version__, "code_revision": code_revision()},
        "software": software_versions(),
        "environment": probe.to_dict() if probe is not None and hasattr(probe, "to_dict") else probe,
        "texts": texts,
        "workspace_manifest": (manifest.to_dict() if hasattr(manifest, "to_dict") else manifest) if manifest is not None
        else {"supplied": False, "note": "not supplied by the caller: the files written into the working directory are not listed"},
        "seeds": _seeds(task, seeds),
        "price": price,
        "budget": {
            "round": _limits(task.budget.round),
            "session": _limits(task.budget.session),
            "analysis_exchange": _limits(task.budget.analysis_exchange),
        },
        "consumption": totals,
        "outcome": session_outcome or last["outcome"],
        "termination_reason": session_termination or last["termination_reason"],
        "rounds": round_records,
        "provenance": provenance,
        "provenance_file": PROVENANCE_FILE,
        "transcript": {
            "file": TRANSCRIPT_FILE,
            "present": transcript.is_file(),
            "sha256": file_sha256(transcript) if transcript.is_file() else None,
        },
        "extra": dict(extra or {}),
    }
    # machine-independent paths (repository-relative, <tmp>, ~): the record is committed (aspire_sysid.portable)
    record = portable_data(record)
    path.write_text(_dump(record), encoding="utf-8", newline="\n")
    return record


# ---------------------------------------------------------------------------------------------
# Reading and recomputing
# ---------------------------------------------------------------------------------------------


def load_run_record(run_dir: str | Path) -> dict[str, Any]:
    """Read ``run_record.json`` of a run folder. Raises :class:`RecordError`."""
    path = Path(run_dir) / RUN_RECORD_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecordError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("format_version") != RUN_RECORD_FORMAT_VERSION:
        raise RecordError(f"{path}: not a run record of format version {RUN_RECORD_FORMAT_VERSION}")
    return data


def round_of_pool(record: Mapping[str, Any], pool_version: int | None) -> Mapping[str, Any]:
    """The round entry of a record that produced pool version ``pool_version`` (the last one with
    candidate files when ``None``)."""
    rounds = [r for r in record["rounds"] if r.get("mode", "round") == "round" and r.get("pool")]
    if pool_version is not None:
        rounds = [r for r in rounds if int(r["pool_version"]) == int(pool_version)]
    if not rounds:
        raise RecordError(f"the record has no round with candidate files{'' if pool_version is None else f' for pool version {pool_version}'}")
    return rounds[-1]


def record_task(run_dir: str | Path, task_dir: str | Path | None = None, *, check: bool = True) -> TaskSpec:
    """Load the task of a run record and check its digests against the record."""
    record = load_run_record(run_dir)
    folder = Path(task_dir) if task_dir is not None else local_path(record["task"]["folder"])
    task = load_task(folder)
    if check:
        dig = task_digests(task)
        diffs = [k for k in ("spec_sha256", "sealed_sha256") if dig[k] != record["task"].get(k)]
        if task.id != record["task"]["id"] or diffs:
            raise RecordError(
                f"the task in {folder} differs from the task of the record ({task.id} vs {record['task']['id']}; differing digests: {diffs or 'none'})"
            )
    return task


def stored_evaluation(run_dir: str | Path, pool_version: int | None = None) -> dict[str, Any]:
    """The evaluation report stored for a pool version (the last one by default), as plain data. """
    rnd = round_of_pool(load_run_record(run_dir), pool_version)
    if not rnd.get("evaluation"):
        raise RecordError(f"pool version {rnd['pool_version']} has no stored evaluation")
    return json.loads((Path(run_dir) / rnd["evaluation"]["report_file"]).read_text(encoding="utf-8"))


def _differences(a: Any, b: Any, where: str = "") -> list[str]:
    if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return [f"{where or '/'}: {a!r} != {b!r}"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{where}/{k}: present in only one report")
            else:
                out += _differences(a[k], b[k], f"{where}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{where}: lengths {len(a)} and {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += _differences(x, y, f"{where}[{i}]")
        return out
    return [] if a == b else [f"{where}: {a!r} != {b!r}"]


def is_interactive(record: Mapping[str, Any]) -> bool:
    """True for the record of an interactive session."""
    return ((record.get("extra") or {}).get("session") or {}).get("operation") == "interactive"


def applied_task_changes(run_dir: str | Path, record: Mapping[str, Any], rnd: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The user's task changes in force for a round entry, cross-checked against the transcript.

    The harness records each instruction and the round in which it takes effect.
    ``task_changes_in_force`` is accepted only in the record of an interactive session, and
    only when it equals the ``task_change`` events of the transcript with ``effective_round`` at most
    the round's number, in their order; otherwise :class:`RecordError` states the difference. An
    autonomous record without the field gives ``[]``.
    """
    changes = [dict(c) for c in (rnd.get("task_changes_in_force") or [])]
    if not is_interactive(record):
        if changes:
            raise RecordError("the round entry has task_changes_in_force, but the record is not of an interactive session")
        return []
    path = Path(run_dir) / (record.get("transcript") or {}).get("file", TRANSCRIPT_FILE)
    from .transcript import read_transcript

    try:
        events = read_transcript(path).lines
    except Exception as exc:  # noqa: BLE001 - reported as a record error
        raise RecordError(f"cannot read the transcript {path} to check the task changes: {exc}") from exc
    expected = [dict(ev["change"]) for ev in events
                if ev.get("kind") == "task_change" and int(ev.get("effective_round") or 0) <= int(rnd.get("round") or 0)]
    if json.loads(json.dumps(expected)) != json.loads(json.dumps(changes)):
        raise RecordError(
            f"the task changes in force for round {rnd.get('round')} in the run record ({changes}) differ from the task_change "
            f"events of the transcript with effective_round <= {rnd.get('round')} ({expected})"
        )
    return changes


def recompute_evaluation(
    run_record_dir: str | Path,
    pool_version: int | None = None,
    *,
    task_dir: str | Path | None = None,
    compare: bool = True,
) -> PoolEvaluation:
    """Recompute the evaluation of a recorded pool offline and compare it with the stored report.

    A run record reproduces its evaluation report offline.
    The task is loaded from the folder named in the record (or ``task_dir``) and its
    digests are checked; the copied candidate files of ``pools/v<k>/models`` are checked with the
    pool version and previous labels of the round and evaluated by
    :func:`aspire_sysid.evaluate.evaluate_pool`. With ``compare``, the JSON form of the result
    must equal the stored ``evaluation.json`` field by field; otherwise
    :class:`RecordMismatchError` lists the differences. Returns the recomputed
    :class:`PoolEvaluation`.
    """
    run = Path(run_record_dir)
    record = load_run_record(run)
    rnd = round_of_pool(record, pool_version)
    task = record_task(run, task_dir)
    changes = applied_task_changes(run, record, rnd)
    if changes:
        task = apply_changes(task, [TaskChange(**c) for c in changes])
    folder = run / rnd["pool"]["folder"]
    report = check_workspace(folder, task, pool_version=int(rnd["pool_version"]), previous_labels=list(rnd.get("previous_labels") or []))
    ev = evaluate_pool(task, report)
    if compare:
        if not rnd.get("evaluation"):
            raise RecordError(f"pool version {rnd['pool_version']} has no stored evaluation to compare with")
        stored = json.loads((run / rnd["evaluation"]["report_file"]).read_text(encoding="utf-8"))
        # the label of a round of interactive operation is not a result of the evaluation; it must
        # agree with the round entry's flag
        labels = [stored.pop("test_informed", None)]
        if isinstance(stored.get("recommendation"), dict):
            labels.append(stored["recommendation"].pop("test_informed", None))
        for lab in labels:
            if lab is not None and bool(lab) != bool(rnd.get("test_informed")):
                raise RecordMismatchError(
                    f"the stored report of pool version {rnd['pool_version']} is labelled test_informed={lab}, "
                    f"the round entry test_informed={rnd.get('test_informed')}", [])
        fresh = json.loads(to_json(ev.to_dict()))
        diffs = _differences(fresh, stored)
        if diffs:
            raise RecordMismatchError(f"the recomputed evaluation of pool version {rnd['pool_version']} differs from the stored report", diffs)
    return ev
