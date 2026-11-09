"""Aggregation of the repeated runs of an experiment (one task).

For repeated runs, the report states what varies, how many runs were attempted, how many
produced a pool, and how many produced an eligible model. It defines the per-run quantity
summarized, such as the test error of the agent's recommended model or the smallest test score in
the pool; the latter remains labeled oracle-based. For repeated runs, the report gives the mean,
the sample standard deviation, and the number of finite results. The sample standard
deviation is undefined for fewer than two results. A single-run result is labeled as such. Runs
without a finite result are counted and explained separately; they are neither assigned zero nor
silently dropped. If a mean uses only successful runs, the report states this beside the result.
Results from different models are never aggregated.

**Scope.** An experiment is one task, run one or more times with identical settings
(:mod:`aspire_sysid.experiment.config`); the aggregation is over these runs. Runs of different
tasks are never aggregated.

**Counts.** *Attempted*: runs with a run record (a finished run, whatever its outcome).
*Delivered*: runs whose final check report passed, that is, a valid pool file with at least one
candidate within the pool limit that passed the file and expression checks.
*Eligible*: runs with at least one candidate eligible for ranking. A run that ended
at a budget limit without a valid pool file can have evaluated and eligible candidates in the
harness's file-name order; such runs are counted separately, so that the three counts overlap and
need not form a chain. Planned runs without a record and interrupted attempts are reported, never
counted as attempted.

**Per-run quantities.**

1. ``recommended_test_S``: the pooled test RMSE ``S`` of the candidate that the
   agent recommended from training and validation evidence (practical selection). No finite
   result, with the reason, when no candidate was evaluated, when the recommendation is absent or
   invalid, when the agent stated that no recommendation is supported, when the recommended
   candidate was not evaluated, or when it is not eligible (excluded by a requirement or failed
   numerically on test data). ``recommended_train_rmse``: the pooled RMSE of the same candidate
   on the training data, computed by the harness in the evaluation mode of the task.
2. ``oracle_best_S``: the smallest ``S`` among the eligible candidates of the run: "oracle-based
   selection on test data", reported with the pool size; no finite result when no candidate is
   eligible.
3. ``turns``, ``input_tokens``, ``output_tokens``, ``cost_usd``, ``elapsed_s``: consumption of the
   run; always finite.
4. ``pool_size`` (candidates proposed), ``evaluated_candidates``, ``distinct_structures`` (over the evaluated candidates), ``sensitivity_deficient`` (evaluated candidates whose
   sensitivity rank test found a rank deficiency), and the complexity of the recommended
   candidate (fitted parameters, expression-tree nodes).
5. Per test trajectory: the RMSE of the recommended and of the oracle-best
   candidate. Requirement outcomes: per requirement, the outcomes over the recommended candidates
   and over all evaluated candidates.

**Statistics.** For each quantity with ``k`` finite results ``x_1 .. x_k`` among ``N`` attempted
runs: the mean ``x̄ = (1/k) Σ x_i`` and the sample standard deviation
``s = sqrt(Σ (x_i − x̄)² / (k − 1))`` (divisor ``k − 1``), which is undefined (``None``, never 0)
for ``k < 2``; the number of finite results and the runs without one, with their reasons. When
``k < N``, the report states beside the result that the mean uses only the runs with a finite
result.

**Missing runs and spend.** Planned runs without a run record are listed with their state
(planned, or unfinished: interrupted or still running) and reason. The tokens and the cost of
interrupted attempts and of unfinished run folders are totalled from their transcripts and
reported as spend; they never enter the statistics.

**Refusal.** :func:`aggregate_records` raises :class:`AggregationRefused` when the records differ
in the task, in the model identifier, in the harness identity (version, git tree hashes of
``aspire/`` and ``tasks/`` and whether these folders had changes; the repository commit is not
compared) or in being dry runs.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..portable import portable_data
from ..evaluate import RANKING_LABEL
from ..evaluate.data import SEALED_GROUPS
from ..record import RUN_RECORD_FILE

__all__ = [
    "AggregationRefused",
    "QUANTITIES",
    "SD_FORMULA",
    "describe",
    "run_quantities",
    "check_homogeneous",
    "aggregate_records",
    "load_records",
    "aggregate_experiment",
    "attempt_spend",
    "unfinished_spend",
    "render_markdown",
    "write_aggregate",
]

SD_FORMULA = "s = sqrt( sum_i (x_i - xbar)^2 / (k - 1) ), xbar = (1/k) sum_i x_i, over the k runs with a finite result (divisor k - 1); undefined for k < 2"
"""The sample standard deviation of the report (divisor k − 1 for k finite results), stated once in every report."""

QUANTITIES: dict[str, dict[str, str]] = {
    "recommended_test_S": {
        "label": "test score S of the recommended candidate (practical selection)",
        "unit": "output",
        "definition": "pooled test RMSE S of the candidate the agent recommended from training and validation evidence",
    },
    "recommended_train_rmse": {
        "label": "training error of the recommended candidate",
        "unit": "output",
        "definition": "pooled RMSE of the recommended candidate on the training data, computed by the harness in the evaluation mode of the task",
    },
    "oracle_best_S": {
        "label": "best eligible test score S in the pool (" + RANKING_LABEL + ")",
        "unit": "output",
        "definition": "smallest S among the eligible candidates of the run; selects on the test data and measures whether the pool contains an accurate model",
    },
    "turns": {"label": "turns", "unit": "-", "definition": "language-model responses of the round"},
    "input_tokens": {"label": "input tokens", "unit": "tokens", "definition": "input tokens of all requests of the run"},
    "output_tokens": {"label": "output tokens", "unit": "tokens", "definition": "output tokens (including reasoning tokens) of all responses"},
    "cost_usd": {"label": "cost", "unit": "USD", "definition": "cost from the dated price schedule (aspire/configs/prices.yaml)"},
    "elapsed_s": {"label": "elapsed execution time", "unit": "s", "definition": "elapsed execution time of the round, without the final checks and the evaluation"},
    "pool_size": {"label": "pool size", "unit": "-", "definition": "candidates proposed in the final pool"},
    "evaluated_candidates": {"label": "evaluated candidates", "unit": "-", "definition": "candidates within the pool limit that passed the checks and were evaluated"},
    "distinct_structures": {"label": "distinct structures", "unit": "-", "definition": "distinct expression structures among the evaluated candidates"},
    "sensitivity_deficient": {"label": "candidates with a sensitivity rank deficiency", "unit": "-", "definition": "evaluated candidates whose sensitivity rank test found dependent fitted parameters"},
    "recommended_fitted_parameters": {"label": "fitted parameters of the recommended candidate", "unit": "-", "definition": "count of fitted parameters"},
    "recommended_node_count": {"label": "expression-tree nodes of the recommended candidate", "unit": "-", "definition": "node count under the convention of aspire_sysid/evaluate/complexity.py"},
}
"""The per-run quantities of the aggregation (module docstring)."""


class AggregationRefused(ValueError):
    """The runs differ in task, model, harness revision or dry-run status. """


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def describe(values: Sequence[tuple[str, Any, str | None]]) -> dict[str, Any]:
    """Statistics of one quantity over the runs of an experiment (module docstring).

    ``values`` holds ``(run_id, value or None, reason when there is no finite value)``. Returns the
    number of runs, the number of finite results, the mean, the sample standard deviation (divisor
    k − 1 for k finite results; ``None`` with the note "undefined" for fewer than two), minimum,
    maximum, the per-run values, the runs without a finite result with their reasons, and the note
    on the runs the mean uses.
    """
    finite = [(r, float(v)) for r, v, _ in values if _finite(v)]
    missing = [{"run_id": r, "reason": why or "no finite value"} for r, v, why in values if not _finite(v)]
    n = len(finite)
    xs = [v for _, v in finite]
    mean = sum(xs) / n if n else None
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1)) if n >= 2 else None  # type: ignore[operator]
    out: dict[str, Any] = {
        "n_runs": len(values),
        "n_finite": n,
        "mean": mean,
        "sd": sd,
        "sd_note": None if n >= 2 else "undefined: fewer than two finite results",
        "min": min(xs) if xs else None,
        "max": max(xs) if xs else None,
        "single_result": n == 1,
        "values": [{"run_id": r, "value": v if _finite(v) else None} for r, v, _ in values],
        "no_finite_result": missing,
    }
    if n == 0:
        out["mean_note"] = "no run has a finite result"
    elif n < len(values):
        out["mean_note"] = f"the mean uses only the {n} of {len(values)} runs with a finite result"
    else:
        out["mean_note"] = f"all {n} runs"
    return out


# ---------------------------------------------------------------------------------------------
# Per-run quantities
# ---------------------------------------------------------------------------------------------


def _last_round(record: Mapping[str, Any]) -> Mapping[str, Any]:
    rounds = [r for r in record.get("rounds", []) if r.get("mode", "round") == "round"]
    return rounds[-1] if rounds else {}


def _candidate(ev: Mapping[str, Any], label: str | None) -> Mapping[str, Any] | None:
    if label is None:
        return None
    return next((c for c in ev.get("candidates", []) if c.get("label") == label), None)


def _trajectory_rmse(cand: Mapping[str, Any] | None) -> dict[str, float | None]:
    if not cand:
        return {}
    group = next(iter(SEALED_GROUPS))  # the sealed data group of the evaluation report
    test = ((cand.get("sealed") or {}).get(group) or {})
    out: dict[str, float | None] = {}
    for t in test.get("trajectories") or []:
        m = t.get("measures") or {}
        out[str(t.get("trajectory"))] = m.get("rmse") if t.get("finished") and _finite(m.get("rmse")) else None
    return out


def run_quantities(record: Mapping[str, Any]) -> dict[str, Any]:
    """The per-run quantities of one run record (module docstring). """
    camp = (record.get("extra") or {}).get("experiment_run") or {}
    cons = record.get("consumption") or {}
    rr = _last_round(record)
    check = rr.get("check_report") or {}
    ev = ((rr.get("evaluation") or {}).get("report")) or None
    outcome = record.get("outcome")
    task_id = (record.get("task") or {}).get("id")
    q: dict[str, Any] = {
        "run_id": camp.get("run_id") or record.get("run_id"),
        "task": task_id,
        "outcome": outcome,
        "termination_reason": record.get("termination_reason"),
        "delivered": bool(check.get("passed")),
        "order_assigned_by_harness": bool(rr.get("order_assigned_by_harness")),
        "turns": cons.get("turns"),
        "input_tokens": cons.get("input_tokens"),
        "output_tokens": cons.get("output_tokens"),
        "cost_usd": cons.get("cost_usd"),
        "elapsed_s": cons.get("elapsed_s"),
        "leak_findings": len(((record.get("extra") or {}).get("leak_scan") or {}).get("findings") or []),
        "output": camp.get("output") or {},
        "pool_cap": camp.get("pool_cap"),
    }
    reasons: dict[str, str] = {}
    if ev is None:
        why = f"no candidate was evaluated (outcome {outcome}: {record.get('termination_reason')})"
        q.update(pool_size=len(check.get("order") or []), evaluated_candidates=0, eligible_candidates=0, eligible=False,
                 recommended_test_S=None, recommended_train_rmse=None, oracle_best_S=None, distinct_structures=None, sensitivity_deficient=None,
                 recommended_label=None, oracle_best_label=None, recommended_fitted_parameters=None, recommended_node_count=None,
                 recommended_trajectory_rmse={}, oracle_best_trajectory_rmse={}, requirements_recommended={}, requirements_all={})
        for k in ("recommended_test_S", "recommended_train_rmse", "oracle_best_S", "distinct_structures", "sensitivity_deficient",
                  "recommended_fitted_parameters", "recommended_node_count"):
            reasons[k] = why
        q["reasons"] = reasons
        return q
    counts = ev.get("counts") or {}
    evaluated = [c for c in ev.get("candidates", []) if c.get("status") == "evaluated"]
    n_elig = counts.get("eligible")
    q["pool_size"] = counts.get("proposed")
    q["evaluated_candidates"] = counts.get("evaluated")
    q["eligible_candidates"] = n_elig
    q["eligible"] = bool(n_elig)
    structs = (ev.get("structures") or {}).get("distinct")
    q["distinct_structures"] = structs
    if structs is None:
        reasons["distinct_structures"] = "the structure comparison is not available"
    sens_avail = [c for c in evaluated if (c.get("sensitivity") or {}).get("available")]
    q["sensitivity_deficient"] = sum(1 for c in sens_avail if (c.get("sensitivity") or {}).get("deficient"))
    q["sensitivity_unavailable"] = len(evaluated) - len(sens_avail)

    # practical selection: the recommended candidate
    rec = ev.get("recommendation") or {}
    label = (rec.get("agent") or {}).get("label") if rec.get("present") else None
    q["recommended_label"] = label
    cand = _candidate(ev, label)
    value = None
    if not rec.get("present"):
        why = "no valid recommendation: " + str(rec.get("note") or "the recommendation is absent or invalid")
    elif label is None:
        why = "the agent stated that no recommendation is supported"
    elif cand is None or cand.get("status") != "evaluated":
        why = f"the recommended candidate {label} was not evaluated ({'absent' if cand is None else cand.get('status')})"
    else:
        sealed = cand.get("sealed") or {}
        if sealed.get("eligible") and _finite(sealed.get("score_S")):
            value, why = float(sealed["score_S"]), None
        else:
            why = f"the recommended candidate {label} is not eligible: " + ("; ".join(sealed.get("ineligibility") or []) or "no finite test score")
    q["recommended_test_S"] = value
    if why:
        reasons["recommended_test_S"] = why
    train = (((cand or {}).get("visible") or {}).get("train") or {}) if cand and cand.get("status") == "evaluated" else {}
    q["recommended_train_rmse"] = float(train["pooled_rmse"]) if train.get("finished") and _finite(train.get("pooled_rmse")) else None
    if q["recommended_train_rmse"] is None:
        reasons["recommended_train_rmse"] = why or f"the recommended candidate {label} has no finite training error"
    ok = value is not None
    comp = (cand or {}).get("complexity") or {}
    q["recommended_fitted_parameters"] = comp.get("fitted_parameters") if cand and cand.get("status") == "evaluated" else None
    q["recommended_node_count"] = comp.get("node_count") if cand and cand.get("status") == "evaluated" else None
    if q["recommended_fitted_parameters"] is None:
        reasons["recommended_fitted_parameters"] = reasons["recommended_node_count"] = reasons.get("recommended_test_S", "no evaluated recommended candidate")
    q["recommended_trajectory_rmse"] = _trajectory_rmse(cand) if ok else {}

    # oracle-based selection: the best eligible candidate
    ranking = (ev.get("sealed") or {}).get("ranking") or None
    entries = (ranking or {}).get("entries") or []
    if entries and _finite(entries[0].get("score_S")):
        best = entries[0]
        q["oracle_best_S"] = float(best["score_S"])
        q["oracle_best_label"] = best.get("label")
        q["oracle_pool_size"] = ranking.get("pool_size")
        q["oracle_candidates_considered"] = ranking.get("candidates_considered")
        q["oracle_best_trajectory_rmse"] = _trajectory_rmse(_candidate(ev, best.get("label")))
    else:
        q["oracle_best_S"] = None
        q["oracle_best_label"] = None
        q["oracle_pool_size"] = (ranking or {}).get("pool_size", q["pool_size"])
        q["oracle_candidates_considered"] = (ranking or {}).get("candidates_considered", 0)
        q["oracle_best_trajectory_rmse"] = {}
        why_not = [f"{c.get('label')}: " + ("; ".join((c.get("sealed") or {}).get("ineligibility") or []) or "not eligible") for c in evaluated]
        reasons["oracle_best_S"] = "no eligible candidate (" + (
            str((ev.get("sealed") or {}).get("no_ranking_reason") or "") or ("; ".join(why_not) if why_not else "no candidate was evaluated")) + ")"

    # requirement outcomes
    def outcomes(c: Mapping[str, Any]) -> dict[str, str]:
        return {str(r.get("id")): str(r.get("outcome") if r.get("kind") == "formal" else "assessed by the human") for r in c.get("requirements") or []}

    q["requirements_recommended"] = outcomes(cand) if cand and cand.get("status") == "evaluated" else {}
    allc: dict[str, Counter] = {}
    for c in evaluated:
        for rid, out in outcomes(c).items():
            allc.setdefault(rid, Counter())[out] += 1
    q["requirements_all"] = {k: dict(v) for k, v in allc.items()}
    q["reasons"] = reasons
    return q


# ---------------------------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------------------------


def _identity(record: Mapping[str, Any]) -> dict[str, Any]:
    camp = (record.get("extra") or {}).get("experiment_run") or {}
    rev = ((record.get("harness") or {}).get("code_revision")) or {}
    hid = rev.get("identity") or {}
    return {
        "model": (record.get("model") or {}).get("id"),
        "harness": (
            (record.get("harness") or {}).get("version"),
            json.dumps(hid.get("trees"), sort_keys=True) if hid else None,
            hid.get("dirty") if hid else None,
            hid.get("changes_sha256") if hid else None,
        ),
        "commit": rev.get("commit"),
        "task": (record.get("task") or {}).get("id"),
        "written_by_runner": bool(camp),
        "dry_run": camp.get("dry_run"),
    }


def check_homogeneous(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Refuse to aggregate records of different tasks, models, harness revisions or dry-run status.

    Results from different models are never aggregated; an experiment is one task; the records state the software and code revisions.
    Returns the common identity. Raises :class:`AggregationRefused` naming the differing field and
    the runs of each value.
    """
    if not records:
        raise AggregationRefused("no finished run to aggregate")
    ids = [(_identity(r), r.get("run_id")) for r in records]
    names = {"task": "tasks", "model": "model identifiers",
             "harness": "harness identities (version, git tree hashes of aspire/ and tasks/, changes in these folders and their digest)",
             "dry_run": "dry-run status"}
    for key, what in names.items():
        groups: dict[str, list[str]] = {}
        for ident, rid in ids:
            groups.setdefault(json.dumps(ident[key], default=str), []).append(str(rid))
        if len(groups) > 1:
            listing = "; ".join(f"{k}: {', '.join(v[:5])}{' ...' if len(v) > 5 else ''}" for k, v in groups.items())
            raise AggregationRefused(f"the runs differ in their {what} and are never aggregated together ({listing})")
    first = ids[0][0]
    if first["harness"][1] is None:
        raise AggregationRefused("the records carry no harness identity (code_revision.identity: git tree hashes of aspire/ and tasks/)")
    if not all(i["written_by_runner"] for i, _ in ids):
        raise AggregationRefused("the records carry no fields of an experiment (extra.experiment_run); they were not written by the experiment runner")
    return {"task": first["task"], "model": first["model"], "harness_version": first["harness"][0], "trees": json.loads(first["harness"][1]),
            "dirty": first["harness"][2], "changes_sha256": first["harness"][3], "commits": sorted({str(i["commit"]) for i, _ in ids if i["commit"]}),
            "dry_run": first["dry_run"]}


def _merge_counters(dicts: Iterable[Mapping[str, Mapping[str, int]]]) -> dict[str, dict[str, int]]:
    out: dict[str, Counter] = {}
    for d in dicts:
        for k, v in d.items():
            out.setdefault(k, Counter()).update(v)
    return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}


def aggregate_records(
    records: Sequence[Mapping[str, Any]],
    *,
    planned: int | None = None,
    interrupted: int = 0,
    experiment: Mapping[str, Any] | None = None,
    missing: Sequence[Mapping[str, Any]] | None = None,
    unfinished_spend: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate the finished run records of one experiment (module docstring). 

    ``planned`` gives the number of runs planned and ``interrupted`` the number of interrupted
    attempts; both are reported, never counted as attempted runs. ``missing`` lists the planned
    runs without a run record (``run_id``, ``state``, ``reason``) and ``unfinished_spend`` the
    tokens and cost of interrupted attempts and unfinished run folders (:func:`unfinished_spend`);
    both are reported as given. Raises :class:`AggregationRefused` for records that must not be
    aggregated together.
    """
    ident = check_homogeneous(records)
    runs = [run_quantities(r) for r in records]
    stats = {name: describe([(q["run_id"], q.get(name), q["reasons"].get(name)) for q in runs]) for name in QUANTITIES}
    trajs: dict[str, dict[str, Any]] = {}
    for which in ("recommended", "oracle_best"):
        ids = sorted({t for q in runs for t in q[f"{which}_trajectory_rmse"]})
        trajs[which] = {
            t: describe([(q["run_id"], q[f"{which}_trajectory_rmse"].get(t),
                          q["reasons"].get("recommended_test_S" if which == "recommended" else "oracle_best_S")
                          or f"not finished on trajectory {t}") for q in runs])
            for t in ids
        }
    rec_req: dict[str, Counter] = {}
    for q in runs:
        for rid, out in q["requirements_recommended"].items():
            rec_req.setdefault(rid, Counter())[out] += 1
    units = {json.dumps(q["output"], sort_keys=True) for q in runs if q["output"]}
    caps = sorted({q["pool_cap"] for q in runs if q["pool_cap"] is not None})
    pools = sorted({q.get("oracle_pool_size") for q in runs if q.get("oracle_pool_size") is not None})
    return {
        "format_version": 2,
        "kind": "aspire_aggregate",
        "identity": ident,
        "experiment": dict(experiment or {}),
        "task": ident["task"],
        "what_varies": "the runs differ only in the responses of the language model; the requests set no seed",
        "statistics": {
            "mean": "xbar = (1/k) sum_i x_i over the k runs with a finite result",
            "sample_standard_deviation": SD_FORMULA,
            "note": "the sample standard deviation divides by k - 1; the output errors use the population convention",
        },
        "ranking_label": RANKING_LABEL,
        "quantity_definitions": QUANTITIES,
        "missing_runs": [dict(m) for m in (missing or [])],
        "unfinished_spend": dict(unfinished_spend or {"attempts": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "items": []}),
        "counts_labels": {
            "attempted": "attempted", "delivered": "delivered", "eligible": "eligible",
            "evaluated_without_valid_pool_file": "evaluated without a valid pool file", "interrupted_attempts": "interrupted attempts",
        },
        "counts_definitions": {
            "attempted": "runs with a run record (finished, whatever the outcome)",
            "delivered": "runs whose final check report passed: a valid pool file with at least one candidate within the pool limit that passed the file and expression checks",
            "eligible": "runs with at least one candidate eligible for ranking",
            "evaluated_without_valid_pool_file": "runs that ended without a valid pool file whose checked candidates were evaluated in file-name order (harness order); they can be eligible without being delivered",
            "interrupted_attempts": "attempts ended by an interruption of the harness and repeated from the beginning; not attempted runs",
        },
        "output": json.loads(next(iter(units))) if len(units) == 1 else None,
        "pool_cap": caps[0] if len(caps) == 1 else caps,
        "pool_sizes": pools,
        "runs_planned": planned,
        "runs_attempted": len(runs),
        "runs_not_executed": None if planned is None else max(0, planned - len(runs)),
        "interrupted_attempts": interrupted,
        "delivered": sum(1 for q in runs if q["delivered"]),
        "eligible": sum(1 for q in runs if q.get("eligible")),
        "evaluated_without_valid_pool_file": sum(1 for q in runs if q["order_assigned_by_harness"] and q.get("evaluated_candidates")),
        "outcomes": dict(sorted(Counter(q["outcome"] for q in runs).items())),
        "single_run": len(runs) == 1,
        "quantities": stats,
        "per_trajectory_rmse": trajs,
        "requirements": {
            "recommended": {k: dict(sorted(v.items())) for k, v in sorted(rec_req.items())},
            "all_evaluated": _merge_counters(q["requirements_all"] for q in runs),
        },
        "leak_findings": sum(q["leak_findings"] for q in runs),
        "runs": [{k: v for k, v in q.items() if k not in ("requirements_all",)} for q in runs],
    }


def load_records(run_dirs: Iterable[str | Path]) -> list[dict[str, Any]]:
    """Read the run records of ``run_dirs`` (skipping folders without one).  """
    out = []
    for d in run_dirs:
        p = Path(d) / RUN_RECORD_FILE
        if p.is_file():
            out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def aggregate_experiment(exp: Any, *, dry_run: bool = False) -> dict[str, Any]:
    """Aggregate the finished runs of an experiment. """
    from .grid import grid_paths, grid_states

    paths = grid_paths(exp, dry_run)
    states = grid_states(exp, dry_run)
    records = load_records(paths.runs / s.spec.run_id for s in states if s.state == "finished")
    interrupted = sum(s.interrupted_attempts for s in states)
    missing = []
    for s in states:
        if s.state == "finished":
            continue
        reason = ("not executed yet" if s.state == "planned" else
                  "the run folder has no run record: the run was interrupted, or it is still running in another process")
        missing.append({"run_id": s.spec.run_id, "state": s.state,
                        "reason": reason, "interrupted_attempts": s.interrupted_attempts})
    folders = [p for p in sorted(paths.interrupted.glob("*")) if p.is_dir()] if paths.interrupted.is_dir() else []
    folders += [paths.runs / s.spec.run_id for s in states if s.state == "interrupted"]
    return aggregate_records(records, planned=len(states), interrupted=interrupted, experiment=exp.to_dict(),
                             missing=missing, unfinished_spend=unfinished_spend(folders))


def attempt_spend(transcript: str | Path) -> dict[str, Any]:
    """Tokens and cost of one transcript, summed over its ``response`` events.

 The charged usage (``usage_charged``, including estimates for unreported usage)
    and ``cost_usd`` of each response are summed; a transcript cut off by a crash is read up to its
    last complete line.
    """
    from ..record import read_transcript

    out = {"responses": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    for ev in read_transcript(transcript, tolerate_truncated_end=True).lines:
        if ev.get("kind") != "response":
            continue
        u = ev.get("usage_charged") or ev.get("usage") or {}
        out["responses"] += 1
        out["input_tokens"] += int(u.get("input_tokens") or 0)
        out["output_tokens"] += int(u.get("output_tokens") or 0)
        out["cost_usd"] += float(ev.get("cost_usd") or 0.0)
    return out


def unfinished_spend(folders: Iterable[str | Path]) -> dict[str, Any]:
    """The spend of interrupted attempts and unfinished run folders, from their transcripts.

    Reported as spend, never aggregated into the statistics.
    """
    items = []
    for f in folders:
        t = Path(f) / "transcript.jsonl"
        if not t.is_file():
            items.append({"folder": Path(f).name, "responses": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                          "note": "no transcript"})
            continue
        try:
            items.append({"folder": Path(f).name, **attempt_spend(t)})
        except Exception as exc:  # noqa: BLE001 - reported
            items.append({"folder": Path(f).name, "responses": None, "input_tokens": None, "output_tokens": None, "cost_usd": None,
                          "note": f"transcript unreadable: {exc}"})
    ok = [i for i in items if i["cost_usd"] is not None]
    return {
        "attempts": len(items),
        "input_tokens": sum(i["input_tokens"] for i in ok),
        "output_tokens": sum(i["output_tokens"] for i in ok),
        "cost_usd": sum(i["cost_usd"] for i in ok),
        "items": items,
    }


# ---------------------------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------------------------


def _num(x: Any, digits: int = 4) -> str:
    if x is None:
        return "–"
    v = float(x)
    if not math.isfinite(v):
        return str(x)
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    if abs(v) >= 10 ** digits:
        return f"{v:.0f}"
    return f"{v:.{digits}g}"


def _stat_cell(st: Mapping[str, Any], digits: int = 4) -> str:
    if st["n_finite"] == 0:
        return f"no finite result (0 of {st['n_runs']})"
    if st["n_finite"] == 1:
        return f"{_num(st['mean'], digits)} (single run)" if st["n_runs"] == 1 else f"{_num(st['mean'], digits)} (1 of {st['n_runs']}; s undefined)"
    return f"{_num(st['mean'], digits)} ± {_num(st['sd'], digits)} ({st['n_finite']} of {st['n_runs']})"


def render_markdown(agg: Mapping[str, Any]) -> str:
    """The aggregation as a Markdown report. """
    ident = agg["identity"]
    exp = agg.get("experiment") or {}
    q = agg["quantities"]
    lines: list[str] = []
    lines += [f"# Aggregation of experiment {exp.get('id', '(runs)')}", ""]
    lines += [
        "## 1 Scope",
        "",
        f"Task: `{agg['task']}`{' (dry run with the scripted agent; not a result)' if ident.get('dry_run') else ''}. "
        f"Model identifier: `{ident['model']}`. Harness version {ident['harness_version']}; harness identity: git tree "
        + ", ".join(f"`{k}` {str(v)[:12]}" for k, v in (ident.get("trees") or {}).items())
        + (" with uncommitted changes in these folders (the tree hashes do not identify the code)" if ident.get("dirty") else "")
        + (f"; repository commit(s), for information: {', '.join('`' + c[:12] + '`' for c in ident['commits'])}" if ident.get("commits") else "")
        + ".",
        "",
        "An **experiment** is one task, run one or more times with identical settings; a **run** is one session of the agent "
        "for the task. " + agg["what_varies"].capitalize() + ". Every run of an aggregation used the same task, "
        "model identifier and harness identity; the harness refuses to aggregate runs that differ in any of them.",
        "",
    ]
    if exp:
        budget = exp.get("budget_override")
        lines += [
            f"Runs planned: {exp.get('runs')}. Round budget: "
            + (f"{budget['turns']} turns, {budget['seconds']} s, {budget['usd']} USD (experiment override)." if budget else "the round budget of the task.")
            + f" Pool limit of the task: {agg.get('pool_cap')}.",
            "",
        ]
    lines += [
        "## 2 Definitions",
        "",
        "Counts: " + "; ".join(f"*{agg.get('counts_labels', {}).get(k, k)}*: {v}" for k, v in agg["counts_definitions"].items())
        + ". The counts overlap and need not sum to the number of runs.",
        "",
        "Per-run quantities: " + "; ".join(f"*{v['label']}*: {v['definition']}" for v in agg["quantity_definitions"].values()) + ".",
        "",
        f"The test score S is the pooled root mean squared error (RMSE) over all test trajectories, "
        f"in the unit of the output. Every best-of-pool value is labeled "
        f"\"{agg['ranking_label']}\": it selects on the test data and states whether the pool contains an accurate model, not "
        "whether the agent recognized it; it is reported with the pool size and the number of candidates considered (the eligible "
        "candidates of the run). The agent's recommendation is reported separately.",
        "",
        f"Statistics: a table entry `m ± s (k of N)` gives the mean m and the sample standard deviation s over the k runs with a "
        f"finite result among the N attempted runs (divisor k − 1); {agg['statistics']['sample_standard_deviation']}. "
        f"{agg['statistics']['note'].capitalize()}. An entry of an experiment with one run is labeled \"single run\" and has no s; "
        "an entry with one finite result among several runs states that s is undefined. Runs without a "
        "finite result are listed in Section 6 with their reasons, for every quantity; they are never assigned zero.",
        "",
    ]
    outs = ", ".join(f"{k} {v}" for k, v in agg["outcomes"].items()) or "–"
    lines += ["## 3 Runs", "",
              "| Planned | Attempted | Delivered | Eligible | Evaluated without valid pool file | Interrupted attempts | Outcomes | Leak-scan findings |",
              "|---|---|---|---|---|---|---|---|",
              f"| {_num(agg['runs_planned'])} | {agg['runs_attempted']} | {agg['delivered']} | {agg['eligible']} | "
              f"{agg['evaluated_without_valid_pool_file']} | {agg['interrupted_attempts']} | {outs} | {agg['leak_findings']} |"]
    total_leaks = agg["leak_findings"]
    lines += ["", ("**Leak scan: sealed information was found in " + str(total_leaks) + " place(s); see the run records (extra.leak_scan).**")
              if total_leaks else "Leak scan: no sealed information was found in any transcript or agent-written file.", ""]
    o = agg.get("output") or {}
    unit = f"{o.get('unit')} (output {o.get('name')})" if o else "unit not recorded"
    considered = ", ".join(str(r.get("oracle_candidates_considered")) for r in agg["runs"]) or "–"
    lines += ["## 4 Errors of the output", "",
              "| Unit | Training error of the recommended candidate | S of the recommended candidate (practical selection) | Best eligible S (" + agg["ranking_label"] + ") | Candidates considered per run | Pool sizes | Pool limit |",
              "|---|---|---|---|---|---|---|",
              f"| {unit} | {_stat_cell(q['recommended_train_rmse'])} | {_stat_cell(q['recommended_test_S'])} | {_stat_cell(q['oracle_best_S'])} | "
              f"{considered} | {', '.join(str(p) for p in agg['pool_sizes']) or '–'} | {agg['pool_cap']} |"]
    notes = [name for name in ("recommended_test_S", "oracle_best_S") if 0 < q[name]["n_finite"] < q[name]["n_runs"]]
    if notes:
        lines += [""] + [f"- {QUANTITIES[n]['label']}: {q[n]['mean_note']}." for n in notes]
    names = ("turns", "input_tokens", "output_tokens", "cost_usd", "elapsed_s", "pool_size", "evaluated_candidates", "distinct_structures",
             "sensitivity_deficient", "recommended_fitted_parameters", "recommended_node_count")
    lines += ["", "## 5 Consumption and pool properties", "", "| Quantity | Unit | Value |", "|---|---|---|"]
    lines += [f"| {QUANTITIES[k]['label']} | {QUANTITIES[k]['unit']} | {_stat_cell(q[k])} |" for k in names]
    lines += ["", "## 6 Runs without a finite result", "",
              "Every quantity of Sections 4 and 5 for which an attempted run has no finite value, with the reason.", ""]
    any_missing = False
    for name in QUANTITIES:
        for m in q[name]["no_finite_result"]:
            any_missing = True
            lines.append(f"- run {m['run_id']}, {QUANTITIES[name]['label']}: {m['reason']}.")
    if not any_missing:
        lines.append("Every attempted run has a finite value of every quantity.")
    missing = agg.get("missing_runs") or []
    lines += ["", "Planned runs without a run record (not attempted runs; not in the counts of Section 3):", ""]
    if missing:
        lines += [f"- {m['run_id']}: {m['state']}; {m['reason']}"
                  + (f"; {m['interrupted_attempts']} interrupted attempt(s)" if m.get("interrupted_attempts") else "") + "." for m in missing]
    else:
        lines.append("- none.")
    spend = agg.get("unfinished_spend") or {}
    lines += ["", f"Spend of interrupted attempts and unfinished run folders (from their transcripts; not in the statistics): "
              f"{spend.get('attempts', 0)} attempt(s), {_num(spend.get('input_tokens', 0))} input tokens, "
              f"{_num(spend.get('output_tokens', 0))} output tokens, {float(spend.get('cost_usd', 0.0)):.4f} USD."]
    for i in spend.get("items", []):
        lines.append(f"- {i['folder']}: {_num(i.get('responses'))} responses, {_num(i.get('input_tokens'))} input tokens, "
                     f"{_num(i.get('output_tokens'))} output tokens, {_num(i.get('cost_usd'), 3)} USD{'; ' + i['note'] if i.get('note') else ''}.")
    lines += ["", "## 7 Root mean squared error per test trajectory", "",
              "RMSE of the recommended candidate and of the best eligible candidate (" + agg["ranking_label"] + "), per test trajectory.", "",
              "| Trajectory | Recommended candidate | Best eligible candidate |", "|---|---|---|"]
    per = agg["per_trajectory_rmse"]
    for t in sorted(set(per["recommended"]) | set(per["oracle_best"])):
        r, b = per["recommended"].get(t), per["oracle_best"].get(t)
        lines.append(f"| {t} | {_stat_cell(r) if r else '–'} | {_stat_cell(b) if b else '–'} |")
    req = agg["requirements"]
    lines += ["", "## 8 Requirement outcomes", "",
              "Outcomes of the assessment of each requirement: proof, counterexample, inconclusive or unavailable for formal "
              "requirements; natural-language requirements are assessed by the human. Counts over the recommended candidates of the runs and over all evaluated candidates.", ""]
    rids = sorted(set(req["recommended"]) | set(req["all_evaluated"]))
    if rids:
        fmt = lambda d: ", ".join(f"{k} {v}" for k, v in d.items()) or "–"  # noqa: E731
        lines += ["| Requirement | Recommended candidates | All evaluated candidates |", "|---|---|---|"]
        lines += [f"| {rid} | {fmt(req['recommended'].get(rid, {}))} | {fmt(req['all_evaluated'].get(rid, {}))} |" for rid in rids]
    else:
        lines.append("The task states no requirement.")
    lines += ["", "## 9 Runs", "", "| Run | Outcome | Delivered | Eligible | Recommended | Training error (recommended) | S (recommended) | Best eligible | S (best eligible; " + agg["ranking_label"] + ") | Candidates considered | Pool size | Turns | Cost (USD) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in agg["runs"]:
        lines.append(f"| {r['run_id']} | {r['outcome']} | {'yes' if r['delivered'] else 'no'} | {'yes' if r.get('eligible') else 'no'} | {r.get('recommended_label') or '–'} | "
                     f"{_num(r.get('recommended_train_rmse'))} | {_num(r.get('recommended_test_S'))} | {r.get('oracle_best_label') or '–'} | {_num(r.get('oracle_best_S'))} | "
                     f"{_num(r.get('oracle_candidates_considered'))} | {_num(r.get('pool_size'))} | "
                     f"{_num(r.get('turns'))} | {_num(r.get('cost_usd'), 3)} |")
    lines.append("")
    return "\n".join(lines)


def write_aggregate(agg: Mapping[str, Any], out_dir: str | Path) -> tuple[Path, Path]:
    """Write ``aggregate.json`` and ``aggregate.md`` into ``out_dir`` (derived reports; rewritten on every call).  """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    j = out / "aggregate.json"
    m = out / "aggregate.md"
    agg = portable_data(agg)  # machine-independent paths (aspire_sysid.portable)
    j.write_text(json.dumps(agg, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    m.write_text(render_markdown(agg), encoding="utf-8", newline="\n")
    return j, m
