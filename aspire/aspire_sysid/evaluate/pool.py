"""Evaluation of a candidate pool: the top-level pure function of the evaluation.

The evaluation procedure and the candidate and pool reports. The
evaluation is a pure function of the task specification and the candidate files.

:func:`evaluate_pool` takes a task and the candidate files and returns a :class:`PoolEvaluation`.
The sequence per candidate is: file and expression checks; assessment of
the requirements; output errors and numerical failure checks on the test, training and
validation data; then complexity, parameter sensitivity and the reference comparison. One
candidate's failure never stops the evaluation of the others.

**Pool limit.** The first ``pool_cap`` labels of the pool file's order
are evaluated; later labels are retained, checked, marked "outside the limit" and not evaluated.

**Eligibility.** A candidate is eligible for numerical ranking when it passed the
file and expression checks, has no demonstrated violation of a mandatory requirement (a
counterexample of a requirement with ``exclude_on_violation`` true), and its evaluation finished
on every test trajectory. A violation of a requirement that the user allowed without exclusion
is reported with the instruction and does not affect eligibility.

**Ranking.** The eligible candidates are ranked by increasing pooled score ``S``,
equation (9) of :mod:`aspire_sysid.evaluate.metrics`. Tie rule: two consecutive candidates in that order are tied when
``|S_a − S_b| ≤ TIE_RELATIVE_TOLERANCE · max(S_a, S_b)`` (relative 1e-12, about 4500 units in the
last place of a binary64 number, the scale of rounding differences in the summation); tied
candidates share a rank (competition ranking: 1, 1, 3), and the report lists them without
claiming a difference. Candidates with equal ``S`` keep the agent's order in the listing. The
report shows every candidate with rank at most :data:`TOP_K` (five), which includes all
candidates tied at rank five, labeled "oracle-based selection on test data" with the number of
candidates considered (the eligible candidates) and the pool size. Without test data, no
ranking is made; the agent's order and recommendation are preserved.

**Sealed and permitted results.** Everything derived from the sealed test data or the reference
expression is held in the ``sealed`` parts of the result: test errors and failures, the score
``S``, eligibility, the ranking and the reference comparison. :func:`permitted_view` returns the
result without them, for the messages to the agent: the checks, the
requirement assessments (computed from the task specification and the candidate only), the
training and validation errors and failures, complexity, structures and sensitivity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp

from .. import __version__
from ..model import check_config_from_task
from ..model import checks as checks_mod
from ..model.checks import CheckReport
from ..task.schema import TaskSpec
from .compiled import CompiledModel
from .complexity import Complexity, complexity, distinct_structures, structure
from .constraints import RequirementResult, assess_requirements, unavailable_requirements
from .data import sealed_trajectories, visible_trajectories
from .errors import GroupEvaluation, evaluate_group
from .reference import ReferenceComparison, compare_with_reference
from .sealed import load_reference
from .sensitivity import SensitivityResult, sensitivity

TOP_K = 5
"""Number of ranks reported by the oracle-based selection."""

TIE_RELATIVE_TOLERANCE = 1e-12
"""Relative tolerance under which two scores are reported as a numerical tie."""

RANKING_LABEL = "oracle-based selection on test data"
"""The label of every test-based ranking."""


@dataclass
class SealedCandidateResults:
    """Results of one candidate derived from sealed data."""

    test: GroupEvaluation | None = None
    score: float | None = None
    eligible: bool | None = None
    ineligibility: list[str] = field(default_factory=list)
    failed_numerically: bool = False
    rank: int | None = None
    reference: ReferenceComparison | None = None
    failed_computations: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Plain data for the JSON report (sealed)."""
        return {
            "failed_computations": list(self.failed_computations),
            "test": None if self.test is None else self.test.to_dict(),
            "score_S": self.score,
            "eligible": self.eligible,
            "ineligibility": list(self.ineligibility),
            "failed_numerically": self.failed_numerically,
            "rank": self.rank,
            "reference_comparison": None if self.reference is None else self.reference.to_dict(),
        }


@dataclass
class CandidateEvaluation:
    """The evaluation of one candidate.

    ``status`` is ``evaluated``, ``failed_checks`` (the file and expression checks rejected it)
    or ``outside_limit`` (beyond the pool cap: checked, retained, not evaluated).
    ``failed_computations`` lists the evaluation stages that raised an error (failed
    computations are distinguished from missing information and inapplicable checks); the
    sealed stages record theirs in ``sealed.failed_computations``.
    """

    label: str
    position: int | None
    within_limit: bool
    status: str
    checks: dict[str, Any]
    expressions: dict[str, str] = field(default_factory=dict)
    complexity: Complexity | None = None
    structure: dict[str, str] | None = None
    structure_group: int | None = None
    requirements: list[RequirementResult] = field(default_factory=list)
    visible: dict[str, GroupEvaluation] = field(default_factory=dict)
    sensitivity: SensitivityResult | None = None
    failed_computations: list[dict[str, str]] = field(default_factory=list)
    sealed: SealedCandidateResults = field(default_factory=SealedCandidateResults)

    @property
    def excluded_by_requirements(self) -> bool:
        """True when a mandatory requirement is demonstrably violated."""
        return any(r.excludes for r in self.requirements)

    @property
    def exclusions(self) -> list[str]:
        """Identifiers of the requirements whose violation excludes the candidate."""
        return [r.id for r in self.requirements if r.excludes]

    @property
    def allowed_violations(self) -> list[str]:
        """Violated requirements that the user allowed without exclusion."""
        return [r.id for r in self.requirements if r.kind == "formal" and r.outcome == "counterexample" and not r.exclude_on_violation]

    @property
    def unresolved(self) -> list[str]:
        """Requirements whose assessment is unresolved."""
        return [r.id for r in self.requirements if r.status == "unresolved"]

    def to_dict(self, include_sealed: bool = True) -> dict[str, Any]:
        """Plain data for the JSON report; without ``include_sealed`` the sealed part is omitted."""
        d: dict[str, Any] = {
            "label": self.label,
            "position": self.position,
            "within_limit": self.within_limit,
            "status": self.status,
            "checks": self.checks,
            "expressions": dict(self.expressions),
            "complexity": None if self.complexity is None else self.complexity.to_dict(),
            "structure": self.structure,
            "structure_group": self.structure_group,
            "requirements": [r.to_dict() for r in self.requirements],
            "excluded_by_requirements": self.excluded_by_requirements,
            "exclusions": self.exclusions,
            "allowed_violations": self.allowed_violations,
            "unresolved_requirements": self.unresolved,
            "visible": {g: ev.to_dict() for g, ev in self.visible.items()},
            "sensitivity": None if self.sensitivity is None else self.sensitivity.to_dict(),
            "failed_computations": list(self.failed_computations),
        }
        if include_sealed:
            d["sealed"] = self.sealed.to_dict()
        return d


@dataclass
class PoolEvaluation:
    """The evaluation of one candidate pool. See the module docstring."""

    task_id: str
    formulation: str
    settings: dict[str, Any]
    pool_file: dict[str, Any]
    candidates: list[CandidateEvaluation]
    structures: dict[str, Any]
    recommendation: dict[str, Any]
    test_trajectories: list[dict[str, Any]]
    ranking: dict[str, Any] | None
    no_ranking_reason: str | None

    def candidate(self, label: str) -> CandidateEvaluation:
        """The evaluation of the candidate ``label`` (KeyError if absent)."""
        for c in self.candidates:
            if c.label == label:
                return c
        raise KeyError(label)

    @property
    def evaluated(self) -> list[CandidateEvaluation]:
        """The candidates that were evaluated, in the agent's order."""
        return [c for c in self.candidates if c.status == "evaluated"]

    def counts(self, include_sealed: bool = True) -> dict[str, Any]:
        """The counts of the pool report; categories may overlap."""
        ev = self.evaluated
        d: dict[str, Any] = {
            "proposed": len(self.candidates),
            "accepted_by_checks": sum(1 for c in self.candidates if c.checks["passed"]),
            "outside_limit": sum(1 for c in self.candidates if c.status == "outside_limit"),
            "evaluated": len(ev),
            "excluded_by_requirements": sum(1 for c in ev if c.excluded_by_requirements),
            "failed_numerically_on_visible_data": sum(1 for c in ev if any(g.failures for g in c.visible.values())),
        }
        if include_sealed:
            d["failed_numerically"] = sum(1 for c in ev if c.sealed.failed_numerically)
            d["eligible"] = None if not self.test_trajectories else sum(1 for c in ev if c.sealed.eligible)
            both = [c.label for c in ev if c.excluded_by_requirements and c.sealed.failed_numerically]
            d["overlap"] = {
                "excluded_and_failed_numerically": both,
                "note": (
                    "the categories overlap: the candidates accepted by the checks include those outside the pool limit, and a "
                    "candidate can be both excluded by requirements and failed numerically; the counts need not sum to the pool size"
                ),
            }
        else:
            d["overlap"] = {"note": "the categories overlap; the counts need not sum to the pool size"}
        return d

    def to_dict(self, include_sealed: bool = True) -> dict[str, Any]:
        """Plain data of the whole evaluation; without ``include_sealed``, the permitted view."""
        d: dict[str, Any] = {
            "format_version": 1,
            "task_id": self.task_id,
            "formulation": self.formulation,
            "settings": self.settings,
            "pool_file": self.pool_file,
            "counts": self.counts(include_sealed),
            "structures": self.structures,
            "recommendation": self.recommendation if include_sealed else _strip_sealed_recommendation(self.recommendation),
            "candidates": [c.to_dict(include_sealed) for c in self.candidates],
        }
        if include_sealed:
            d["sealed"] = {
                "test_trajectories": self.test_trajectories,
                "ranking": self.ranking,
                "no_ranking_reason": self.no_ranking_reason,
            }
        return clean_json(d)


def _strip_sealed_recommendation(rec: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in rec.items() if k != "sealed"}


def permitted_view(ev: PoolEvaluation) -> dict[str, Any]:
    """The part of the evaluation that the agent may receive.

    It contains the file and expression checks, the requirement assessments, the training and
    validation errors and failures, complexity, structures, the sensitivity diagnostic and the
    agent's own recommendation; it contains no test error, test trajectory, failure location on
    test data, score, eligibility, ranking or reference comparison.
    """
    return ev.to_dict(include_sealed=False)


def clean_json(obj: Any) -> Any:
    """``obj`` with every non-finite float written as a string (``"inf"``, ``"-inf"``, ``"nan"``)."""
    if isinstance(obj, dict):
        return {str(k): clean_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean_json(v) for v in obj]
    if isinstance(obj, (np.floating,)):
        obj = float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, float) and not math.isfinite(obj):
        return "nan" if obj != obj else ("inf" if obj > 0 else "-inf")
    return obj


# ---------------------------------------------------------------------------------------------


def _stage(errors: list[dict[str, str]], name: str, fn, default):
    """Run one evaluation stage; record an exception as a failed computation."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - reported, never propagated
        errors.append({"stage": name, "error": f"{type(exc).__name__}: {exc}"})
        return default


def _check_record(res) -> dict[str, Any]:
    return {
        "passed": bool(res.passed),
        "issues": [{"rule": i.rule, "where": i.where, "message": i.message} for i in res.issues],
        "notes": list(res.notes),
    }


def _settings(task: TaskSpec) -> dict[str, Any]:
    from . import constraints, reference, sensitivity as sens_mod
    from .symbolic import DEFAULT_TIME_LIMIT_S

    e = task.evaluation
    dyn = task.dynamics
    return {
        "harness_version": __version__,
        "software": {"numpy": np.__version__, "sympy": sp.__version__},
        "mode": e.mode,
        "initialization": e.initialization,
        "scoring": e.scoring,
        "horizon": e.horizon,
        "horizon_note": (
            None if e.horizon is None else
            f"the training and validation data are evaluated in consecutive segments of at most {e.horizon} simulated "
            "samples, each started from the measured state; the test files are evaluated as they are"
        ),
        "sampling_period_s": None if dyn is None else dyn.sampling_period,
        "integrator": None if dyn is None or task.formulation != "continuous" else dyn.integrator,
        "substeps": None if dyn is None or task.formulation != "continuous" else dyn.substeps,
        "input_hold": None if dyn is None else dyn.input_hold,
        "measurement": None if dyn is None else dyn.measurement,
        "discontinuities": (
            None
            if dyn is None
            else "expressions with jumps (Piecewise, sign) are evaluated pointwise at the sample instants and Runge-Kutta "
            "stages; no event detection or step refinement is applied at a jump"
        ),
        "failure_limits": [
            {"variable": f.variable, "lower": f.lower, "upper": f.upper, "unit": f.unit, "justification": f.justification}
            for f in e.failure_limits
        ],
        "time_limit_s": e.time_limit_s,
        "symbolic_time_limit_s": DEFAULT_TIME_LIMIT_S if e.symbolic_time_limit_s is None else e.symbolic_time_limit_s,
        "requirement_confirmation_points": constraints.CONFIRMED_POINTS,
        "reference_samples": reference.REFERENCE_SAMPLES,
        "reference_seed": reference.REFERENCE_SEED,
        "sensitivity_rank_threshold": sens_mod.RANK_THRESHOLD,
        "tie_relative_tolerance": TIE_RELATIVE_TOLERANCE,
        "top_k": TOP_K,
        "pool_cap": task.pool_cap,
    }


def check_report(task: TaskSpec, models: str | Path | CheckReport) -> CheckReport:
    """The file and expression checks of the candidate files.

    ``models`` is a working directory (with ``models/``), a ``models`` folder, or a report that
    the caller already computed. The configuration and the training data come from the task.
    """
    if isinstance(models, CheckReport):
        return models
    p = Path(models)
    models_dir = p / checks_mod.MODELS_DIR if (p / checks_mod.MODELS_DIR).is_dir() else p
    cfg = check_config_from_task(task)
    train = checks_mod.read_training_data(task.data.train_path, cfg.trajectory_column, cfg.train_file)
    return checks_mod.check_models(models_dir, cfg, train)


def _rank(evals: list[CandidateEvaluation], n_evaluated: int) -> dict[str, Any]:
    elig = [c for c in evals if c.sealed.eligible]
    elig.sort(key=lambda c: (c.sealed.score, c.position))
    groups: list[list[CandidateEvaluation]] = []
    for c in elig:
        s = c.sealed.score
        if groups:
            prev = groups[-1][-1].sealed.score
            if abs(s - prev) <= TIE_RELATIVE_TOLERANCE * max(abs(s), abs(prev)):
                groups[-1].append(c)
                continue
        groups.append([c])
    entries = []
    rank = 1
    for g in groups:
        for j, c in enumerate(sorted(g, key=lambda c: c.position)):
            c.sealed.rank = rank
            entries.append({
                "rank": rank,
                "label": c.label,
                "score_S": c.sealed.score,
                "tied_with_previous": j > 0,
                "unresolved_requirements": c.unresolved,
                "allowed_violations": c.allowed_violations,
            })
        rank += len(g)
    ties = [[c.label for c in sorted(g, key=lambda c: c.position)] for g in groups if len(g) > 1]
    top = [e for e in entries if e["rank"] <= TOP_K]
    return {
        "label": RANKING_LABEL,
        "candidates_considered": len(elig),
        "pool_size": n_evaluated,
        "criterion": "pooled test RMSE S, increasing",
        "tie_rule": f"|S_a - S_b| <= {TIE_RELATIVE_TOLERANCE:g} * max(S_a, S_b) for consecutive candidates; tied candidates share a rank",
        "entries": top,
        "ties": ties,
        "note": (
            "This ranking selects on the test data. It measures whether the pool contains an accurate model, "
            "not whether the agent can recognize that model without test data. A rank is not evidence of physical "
            "admissibility: each entry carries its unresolved requirements and any violation allowed by the user."
        ),
    }


def evaluate_pool(task: TaskSpec, models: str | Path | CheckReport) -> PoolEvaluation:
    """Evaluate the candidate pool of ``models`` for ``task`` (module docstring).

    A pure function of the task specification and the candidate files: given
    the same inputs it returns the same result, apart from a time limit reached on a slower
    computer. ``models`` is a working directory, its ``models`` folder, or a :class:`CheckReport`.
    """
    report = check_report(task, models)
    visible = visible_trajectories(task)
    visible_whole = visible_trajectories(task, whole=True)
    test = sealed_trajectories(task)
    ref = load_reference(task)
    keys = task.expression_keys
    cands: list[CandidateEvaluation] = []
    labels = list(report.order) + sorted(lab for lab in report.candidates if lab not in report.order)
    structures = []
    for lab in labels:
        res = report.candidates[lab]
        within = res.position is not None and res.within_limit
        if res.position is not None and not res.within_limit:
            status = "outside_limit"
        elif within and res.passed:
            status = "evaluated"
        else:
            status = "failed_checks"
        ce = CandidateEvaluation(label=lab, position=res.position, within_limit=within, status=status, checks=_check_record(res))
        cands.append(ce)
        if res.candidate is not None:
            ce.expressions = dict(res.candidate.expression_texts)
            ce.complexity = complexity(res.candidate, keys)
        if status != "evaluated":
            continue
        cand = res.candidate
        try:
            model = CompiledModel(task, cand)
        except Exception as exc:  # noqa: BLE001 - one candidate never stops the others
            ce.failed_computations.append({"stage": "numerical form of the expressions", "error": f"{type(exc).__name__}: {exc}"})
            ce.sealed.eligible = False if test else None
            ce.sealed.ineligibility = ["the expressions could not be put into numerical form"] if test else []
            continue
        # order: requirements, output errors and failures, then diagnostics
        ce.requirements = _stage(ce.failed_computations, "requirements", lambda: assess_requirements(task, model), None)
        if ce.requirements is None:  # every requirement unresolved, with the error
            ce.requirements = unavailable_requirements(task, ce.failed_computations[-1]["error"])
        if test:
            ce.sealed.test = _stage(ce.sealed.failed_computations, "errors on the test data", lambda: evaluate_group(model, test, "test"), None)
        for g, trs in visible.items():
            ge = _stage(ce.failed_computations, f"errors on the {g} data", lambda trs=trs, g=g: evaluate_group(model, trs, g), None)
            if ge is not None:
                ce.visible[g] = ge
        st = _stage(ce.failed_computations, "structure", lambda: structure(cand, keys), None)
        if st is not None:
            structures.append(st)
            ce.structure = st.display
        ce.sensitivity = _stage(ce.failed_computations, "sensitivity rank test", lambda: sensitivity(task, cand, visible_whole), None)
        if ref is not None:
            ce.sealed.reference = _stage(ce.sealed.failed_computations, "reference comparison", lambda: compare_with_reference(task, model, ref, cand), None)
        # eligibility
        sealed = ce.sealed
        if test:
            reasons = []
            if ce.excluded_by_requirements:
                reasons.append("demonstrated violation of mandatory requirement(s) " + ", ".join(ce.exclusions))
            if sealed.test is None:
                reasons.append("the evaluation on the test data failed")
            else:
                sealed.failed_numerically = bool(sealed.test.failures)
                sealed.score = sealed.test.pooled_rmse
                if not sealed.test.finished:
                    reasons.append("the evaluation did not finish on every test trajectory")
                elif sealed.score is None:
                    reasons.append("no test trajectory has a sample in its scoring interval")
            sealed.ineligibility = reasons
            sealed.eligible = not reasons
    groups, exhaustive = distinct_structures(structures)
    for i, g in enumerate(groups):
        for lab in g:
            next(c for c in cands if c.label == lab).structure_group = i + 1
    evaluated = [c for c in cands if c.status == "evaluated"]
    pool = report.pool
    pool_file = {
        "valid": report.pool_ok,
        "issues": [{"rule": i.rule, "where": i.where, "message": i.message} for i in report.pool_issues],
        "pool_version": None if pool is None else pool.pool_version,
        "order": list(report.order),
        "order_from_pool_file": report.order_from_pool,
        "pool_cap": task.pool_cap,
    }
    ranking = None
    reason = None
    if test:
        ranking = _rank(evaluated, len(evaluated))
    else:
        reason = "the task has no test data: no ranking is made; the agent's order and recommendation are preserved"
    recommendation = _recommendation(pool, cands, bool(test))
    return PoolEvaluation(
        task_id=task.id,
        formulation=task.formulation,
        settings=_settings(task),
        pool_file=pool_file,
        candidates=cands,
        structures={
            "distinct": len(groups),
            "groups": groups,
            "exhaustive": exhaustive,
            "convention": (
                "ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first "
                "occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical "
                "in SymPy's canonical form"
            ),
        },
        recommendation=recommendation,
        test_trajectories=[{"trajectory": t.trajectory, "n_samples": t.n, "scored_samples": len(task.evaluation.scoring_indices(t.n))} for t in test],
        ranking=ranking,
        no_ranking_reason=reason,
    )


def _recommendation(pool, cands: list[CandidateEvaluation], has_test: bool) -> dict[str, Any]:
    """The agent's recommendation with the harness's notes."""
    if pool is None:
        return {"present": False, "note": "the pool file is missing or invalid; no recommendation is recorded"}
    if pool.recommendation is None:
        issues = [f"[{i.rule}] {i.where}: {i.message}" for i in getattr(pool, "recommendation_issues", ())]
        return {
            "present": False,
            "issues": issues,
            "note": "the recommendation is absent or invalid and is treated as absent; this does not affect the candidates",
        }
    rec = dict(pool.recommendation)
    out: dict[str, Any] = {"present": True, "agent": rec, "notes": []}
    label = rec.get("label")
    if label is None:
        out["notes"].append("the agent recommends no candidate")
        return out
    c = next((x for x in cands if x.label == label), None)
    if c is None or c.status != "evaluated":
        out["notes"].append(f"the recommended candidate {label} was not evaluated ({'absent' if c is None else c.status})")
        return out
    if c.excluded_by_requirements:
        out["notes"].append(f"the recommended candidate {label} is excluded by the demonstrated violation of {', '.join(c.exclusions)}")
    if c.allowed_violations:
        out["notes"].append(f"the recommended candidate {label} violates {', '.join(c.allowed_violations)}, which the user allowed without exclusion")
    formal_unresolved = [r.id for r in c.requirements if r.kind == "formal" and r.status == "unresolved"]
    if formal_unresolved:
        out["notes"].append(f"the recommendation involves unresolved formal requirement(s) {', '.join(formal_unresolved)}, for human assessment")
    nl = [r.id for r in c.requirements if r.kind == "natural_language"]
    if nl:
        out["notes"].append(f"requirement(s) stated in natural language ({', '.join(nl)}) are assessed by the human")
    if has_test:
        out["sealed"] = {
            "test_score_S": c.sealed.score,
            "eligible": c.sealed.eligible,
            "rank": c.sealed.rank,
            "note": "the test error of the recommended candidate (practical selection); sealed",
        }
    return out
