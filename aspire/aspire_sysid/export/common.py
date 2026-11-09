"""Shared part of the Python and Matlab exports: the evaluated pool read back from a run record.

The harness exports each evaluated pool as Python and Matlab files with the equations, the
parameter values, the origin and estimation history of those values, the variable definitions
and any known shift or measurement equations. The exports identify exclusions, numerical
failures and unresolved requirements, and they contain the evaluation settings or a reference to
the saved run record. The exports are generated from the run records, because the evaluation is
a pure function of the record.

:func:`load_export_source` reads a run folder written by
:func:`aspire_sysid.record.write_run_record`: the record, the task (digests checked), the copied
candidate files of one pool version (checked again with the pool version of the round, so that the
exported expressions are exactly the checked canonical ones) and the stored evaluation report.
:func:`candidate_status` extracts, per candidate, the exclusions, numerical failures, unresolved
requirements and the sealed results that the exports state (for the user only).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..portable import local_path, portable_path
from ..evaluate.data import SEALED_GROUPS
from ..model import check_workspace
from ..model.checks import Candidate, CheckReport
from ..record.run_record import RecordError, round_of_pool, load_run_record, record_task
from ..task.schema import TaskSpec
from ..task.table import read_table

__all__ = [
    "ExportSource", "load_export_source", "candidate_status", "sample_arguments", "SEALED_GROUP", "ExportLocationError",
    "check_export_location", "recorded_workspaces", "WORKSPACE_MARKERS",
]

SEALED_GROUP = next(iter(SEALED_GROUPS))
"""Name of the sealed data group in the evaluation report (from the evaluation module)."""


@dataclass
class ExportSource:
    """One evaluated pool of a run, read back from its record."""

    run_dir: Path
    record: dict[str, Any]
    round: dict[str, Any]
    task: TaskSpec
    pool_version: int
    report: CheckReport
    evaluation: dict[str, Any] | None

    @property
    def run_id(self) -> str:
        """The run identifier of the record. """
        return str(self.record.get("run_id"))

    @property
    def configuration(self) -> str:
        """The tool configuration of the run. """
        return str(self.record.get("configuration", {}).get("name"))

    @property
    def evaluated_labels(self) -> list[str]:
        """The evaluated candidates, in the agent's order (or the harness's, see the record). """
        return list(self.report.evaluated)

    def candidate(self, label: str) -> Candidate:
        """The checked candidate ``label`` (canonical expressions, parameter table, values). """
        res = self.report.candidates[label]
        if res.candidate is None:
            raise KeyError(f"{label} did not pass the checks")
        return res.candidate

    def evaluation_of(self, label: str) -> dict[str, Any] | None:
        """The candidate's entry of the stored evaluation report, or ``None``. """
        if self.evaluation is None:
            return None
        return next((c for c in self.evaluation.get("candidates", []) if c.get("label") == label), None)

    def interaction(self) -> dict[str, Any] | None:
        """For a pool of an interactive session: its label
        test-informed or not and the user's task changes in force; ``None`` for an autonomous run."""
        from ..record.run_record import is_interactive

        if not is_interactive(self.record):
            return None
        return {
            "operation": "interactive",
            "round": self.round.get("round"),
            "test_informed": bool(self.round.get("test_informed")),
            "task_changes_in_force": [dict(c) for c in (self.round.get("task_changes_in_force") or [])],
        }

    def interaction_text(self) -> str | None:
        """One paragraph stating :meth:`interaction` for the headers of the exports."""
        it = self.interaction()
        if it is None:
            return None
        label = (
            "test-informed: the user had seen results on sealed data before the feedback that seeded this round, so its "
            "results are not an independent final test of the identification procedure"
            if it["test_informed"] else "not test-informed"
        )
        changes = "; ".join(
            f"{c['kind']}{' ' + c['requirement'] if c.get('requirement') else ''}{'' if c.get('value') is None else ' ' + format(c['value'], 'g')}: "
            f"\"{c['instruction']}\" ({c['stated_by']}, {c['date']})"
            for c in it["task_changes_in_force"]
        ) or "none"
        return (f"Interactive session: pool version {self.pool_version} (round {it['round']}) is {label}. "
                f"Task changes by the user in force for this pool version: {changes}.")

    def record_reference(self) -> dict[str, Any]:
        """Reference to the saved experiment record; for an interactive session it also
        holds :meth:`interaction`."""
        ev = self.round.get("evaluation") or {}
        extra = {} if self.interaction() is None else {"interaction": self.interaction()}
        return {
            **extra,
            "run_id": self.run_id,
            "run_record": portable_path((self.run_dir / "run_record.json").resolve()),
            "pool_version": self.pool_version,
            "evaluation_report": ev.get("report_file"),
            "evaluation_report_sha256": ev.get("report_sha256"),
            "task_spec_sha256": self.record["task"].get("spec_sha256"),
            "code_revision": self.record.get("harness", {}).get("code_revision"),
            "harness_version": self.record.get("harness", {}).get("version"),
        }


def load_export_source(run_dir: str | Path, pool_version: int | None = None, *, task_dir: str | Path | None = None) -> ExportSource:
    """Read the evaluated pool ``pool_version`` (default: the last) of a run folder (module docstring).

    Raises :class:`aspire_sysid.record.RecordError` when the record, the task or the pool is
    missing or the task's digests differ from the record.

    """
    run = Path(run_dir)
    record = load_run_record(run)
    rnd = dict(round_of_pool(record, pool_version))
    task = record_task(run, task_dir)
    folder = run / rnd["pool"]["folder"]
    report = check_workspace(folder, task, pool_version=int(rnd["pool_version"]), previous_labels=list(rnd.get("previous_labels") or []))
    evaluation = None
    if rnd.get("evaluation"):
        evaluation = json.loads((run / rnd["evaluation"]["report_file"]).read_text(encoding="utf-8"))
    if not report.evaluated:
        raise RecordError(f"pool version {rnd['pool_version']} of {run} has no evaluated candidate")
    return ExportSource(run, record, rnd, task, int(rnd["pool_version"]), report, evaluation)


def candidate_status(src: ExportSource, label: str) -> dict[str, Any]:
    """Exclusions, numerical failures, unresolved requirements and sealed results of a candidate.

    The exports identify exclusions, numerical failures and unresolved requirements; the test-based
    rank is labeled oracle-based selection on test data, with the number of candidates
    considered. All fields are plain data taken from the stored evaluation report;
    ``None`` where the report has no entry.
    """
    ce = src.evaluation_of(label)
    if ce is None:
        return {"available": False}
    failures = []
    for g, ge in (ce.get("visible") or {}).items():
        for tr in ge.get("trajectories", []):
            if tr.get("failure"):
                failures.append(tr["failure"])
    sealed = ce.get("sealed") or {}
    test = sealed.get(SEALED_GROUP) or {}
    for tr in test.get("trajectories", []) if isinstance(test, dict) else []:
        if tr.get("failure"):
            failures.append(tr["failure"])
    ranking = (src.evaluation or {}).get("sealed", {}).get("ranking") or {}
    violations = [
        {"id": r["id"], "outcome": r.get("outcome"), "excludes": r.get("excludes"), "detail": r.get("detail")}
        for r in ce.get("requirements", [])
        if r.get("outcome") == "counterexample"
    ]
    return {
        "available": True,
        "status": ce.get("status"),
        "exclusions": list(ce.get("exclusions") or []),
        "allowed_violations": list(ce.get("allowed_violations") or []),
        "violations": violations,
        "unresolved_requirements": list(ce.get("unresolved_requirements") or []),
        "numerical_failures": failures,
        "failed_computations": list(ce.get("failed_computations") or []) + list(sealed.get("failed_computations") or []),
        "score_S": sealed.get("score_S"),
        "eligible": sealed.get("eligible"),
        "ineligibility": list(sealed.get("ineligibility") or []),
        "rank": sealed.get("rank"),
        "ranking_label": ranking.get("label"),
        "candidates_considered": ranking.get("candidates_considered"),
        "pool_size": ranking.get("pool_size"),
        "visible_rmse": {g: ge.get("pooled_rmse") for g, ge in (ce.get("visible") or {}).items()},
    }


def sample_arguments(task: TaskSpec, n_random: int = 64, seed: int = 20260925, max_rows: int = 400) -> np.ndarray:
    """Points at which an export is re-verified numerically.

    The rows of the training data (at most ``max_rows``, evenly spaced; the columns in the order
    of the task's argument names; for NARX tasks the delayed variables are built inside each
    trajectory and rows without history are left out), followed by ``n_random`` points drawn
    uniformly from the declared column ranges with NumPy's ``default_rng(seed)``. Returns an array
    with one row per point and one column per argument.
    """
    from ..evaluate.sealed import argument_columns

    table = read_table(task.data.train_path)
    cols, mask = argument_columns(task, table)
    names = list(task.argument_names)
    rows = np.column_stack([np.asarray(cols[n], dtype=float) for n in names])[mask]
    if len(rows) > max_rows:
        rows = rows[np.linspace(0, len(rows) - 1, max_rows).round().astype(int)]
    rng = np.random.default_rng(seed)
    extra = []
    for n in names:
        try:
            c = task.column(n)
            lo, hi = c.range if c.range is not None else (float(np.min(cols[n][mask])), float(np.max(cols[n][mask])))
        except KeyError:
            v = np.asarray(cols[n], dtype=float)[mask]
            lo, hi = float(np.min(v)), float(np.max(v))
        extra.append(rng.uniform(lo, hi, n_random))
    return np.vstack([rows, np.column_stack(extra)]) if n_random > 0 else rows


WORKSPACE_MARKERS = ("TASK.md", "check_submission.py")
"""Files that mark a working directory of an agent (written by the harness)."""


class ExportLocationError(ValueError):
    """An export folder lies inside, overlaps or contains a working directory."""


def _within(a: Path, b: Path) -> bool:
    return a == b or b in a.parents


def recorded_workspaces(run_dir: str | Path, record: dict[str, Any] | None = None) -> list[Path]:
    """Working directories named by a run record: the manifest's folder, the sources of the pool
    copies, and ``<run-dir>/workspace`` (the archived copy that the experiment runner keeps).
"""
    run = Path(run_dir)
    record = record if record is not None else load_run_record(run)
    out = [run / "workspace"]
    man = record.get("workspace_manifest") or {}
    if isinstance(man, dict) and man.get("workspace"):
        out.append(local_path(man["workspace"]))
    for r in record.get("rounds", []):
        src = (r.get("pool") or {}).get("source")
        if src:
            out.append(local_path(src).parent)
    seen, res = set(), []
    for p in out:
        q = p.resolve()
        if q not in seen:
            seen.add(q)
            res.append(q)
    return res


def check_export_location(out_dir: str | Path, run_dirs: list[str | Path]) -> Path:
    """Refuse an export folder from which sealed data could reach an agent.

    The exports are for the user only and hold results on sealed data (the Matlab export also the test
    data). ``out_dir`` is refused when it lies inside or equals a working directory named by a run
    record, or contains one; when it or one of its ancestors contains ``TASK.md`` or
    ``check_submission.py`` (it is inside a working directory); and when a folder below it contains
    one of these files (it contains a working directory). Returns the resolved folder; raises
    :class:`ExportLocationError`.
    """
    out = Path(out_dir).resolve()
    for run in run_dirs:
        for ws in recorded_workspaces(run):
            if _within(out, ws) or _within(ws, out):
                raise ExportLocationError(f"the export folder {out} overlaps the working directory {ws} of the run {run}; "
                                          "sealed data must never be written where an agent works")
    for anc in [out, *out.parents]:
        for marker in WORKSPACE_MARKERS:
            if (anc / marker).is_file():
                raise ExportLocationError(f"the export folder {out} is inside a working directory ({anc / marker} exists)")
    if out.is_dir():
        for root, _dirs, files in os.walk(out):
            hit = [m for m in WORKSPACE_MARKERS if m in files]
            if hit:
                raise ExportLocationError(f"the export folder {out} contains a working directory ({Path(root) / hit[0]} exists)")
    return out
