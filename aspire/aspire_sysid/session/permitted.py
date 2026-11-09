"""The permitted-results filter of interactive operation.

After each round, the user receives the complete evaluation report. The agent receives only the
outcomes of the file and expression checks, the training and validation results, and diagnostics
computed from information it is allowed to use. Test errors, test trajectories, test-derived
plots, reference comparisons and the locations of failures on withheld data are omitted.
Constraint results are returned only when they do not disclose sealed information. The harness
never reveals sealed test results to the agent.

The filter is a **whitelist** over the evaluation structure
(:class:`aspire_sysid.evaluate.PoolEvaluation`): :func:`permitted_results` builds a new structure
by copying named fields only; a field that is not named here never reaches the agent, whatever
the evaluation adds later. It never reads the sealed parts (``CandidateEvaluation.sealed``,
``PoolEvaluation.test_trajectories``, ``ranking``, the ``sealed`` entry of the recommendation).
What is copied:

* the pool file: validity, issues, pool version, order, whether the order came from the pool
  file, the pool limit;
* the counts of candidates proposed, accepted by the checks, outside the limit, evaluated,
  excluded by requirements, and failed numerically on training or validation data, recomputed
  from the whitelisted candidate fields below (never copied from the evaluation's own counts);
* the distinct structures (computed from the candidates only);
* the agent's own recommendation with the harness's notes (the notes are derived from the
  requirement assessments);
* per candidate: label, position, status, the file and expression checks, the expressions, the
  complexity, the structure and its group, the requirement assessments that pass the rule
  below, the errors and failures on the **training and validation** data only (groups ``train``
  and ``val``; any other group is dropped), the sensitivity rank diagnostic (computed from the
  agent-visible data) and the failed computations of the permitted stages.

**Requirement assessments.** A formal requirement is assessed from the task specification and the
candidate only, on the domain declared in the task (a box or a list of points, both shown in the
brief). Its result is passed when the requirement is a formal requirement of the effective task
whose declared domain is a box or points and equals the domain of the result; a result on any
other domain (which could only come from data) is withheld. Natural-language requirements are
passed with their status "unresolved, assessed by the human".

**Leak screen (second barrier).** :func:`screen_blocks` scans the rendered text of every
candidate block with the value-based leak scanner
(:func:`aspire_sysid.evaluate.leaks.scan_for_sealed_leaks`); a block with a finding is replaced
by the neutral statement "Results of <block>: withheld by the harness."; the reason (the findings)
is returned for the record only, never sent to the agent. The screen never applies to the user's own texts
(the user's feedback is preserved verbatim).
"""

from __future__ import annotations

import json
import math
from typing import Any, Iterable, Mapping

from ..evaluate.leaks import SealedFingerprint, scan_for_sealed_leaks
from ..task.schema import TaskSpec

__all__ = [
    "VISIBLE_GROUPS",
    "permitted_results",
    "render_permitted_blocks",
    "render_permitted_text",
    "permitted_summary",
    "screen_blocks",
]

VISIBLE_GROUPS: tuple[str, ...] = ("train", "val")
"""The data groups whose errors the agent may receive: training and validation results."""

_POOL_FILE_FIELDS = ("valid", "issues", "pool_version", "order", "order_from_pool_file", "pool_cap")
_STRUCTURE_FIELDS = ("distinct", "groups", "exhaustive", "convention")
_RECOMMENDATION_FIELDS = ("present", "agent", "notes", "issues", "note")
_CHECK_FIELDS = ("passed", "issues", "notes")
_REQUIREMENT_FIELDS = (
    "id", "kind", "type", "target", "statement", "outcome", "status", "excludes", "detail", "verification",
    "quantity", "domain", "tolerance", "assumptions", "symbolic", "sampling", "counterexample",
    "exclude_on_violation", "exception", "source",
)
_GROUP_FIELDS = ("group", "finished", "pooled_rmse", "scored_samples")
_TRAJECTORY_FIELDS = (
    "group", "trajectory", "n_samples", "scoring_interval", "required_samples", "completed_samples", "finished",
    "measures", "prefix_diagnostic", "failure", "note",
)
_MEASURE_FIELDS = ("n", "mean", "std", "sse", "rmse", "nrmse", "r2")
_FAILURE_FIELDS = ("group", "trajectory", "index", "time_s", "reason", "variable", "value", "detail")
_COMPLEXITY_FIELDS = ("fitted_parameters", "fixed_parameters", "tied_parameters", "noninteger_literals", "node_count", "node_count_per_key")
_SENSITIVITY_FIELDS = (
    "available", "reason", "targets", "data", "assumptions", "method", "scaling", "rank_threshold", "parameters",
    "rows", "rows_dropped", "singular_values", "rank", "deficient", "zero_columns", "dependent_groups",
)


def _pick(d: Mapping[str, Any] | None, fields: Iterable[str]) -> dict[str, Any] | None:
    if d is None:
        return None
    return {k: d[k] for k in fields if k in d}


def _clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return "nan" if obj != obj else ("inf" if obj > 0 else "-inf")
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes)):
        try:
            return _clean(obj.item())
        except (TypeError, ValueError):
            return str(obj)
    return obj


def _plain(obj: Any) -> Any:
    return json.loads(json.dumps(_clean(obj), default=str))


def _declared_domain(task: TaskSpec, rid: str) -> dict[str, Any] | None:
    for r in task.requirements:
        if r.id == rid:
            return _plain(r.domain)
    return None


def _requirement_permitted(res: Any, task: TaskSpec) -> tuple[bool, str | None]:
    if res.kind == "natural_language":
        return True, None
    if res.kind != "formal":
        return False, f"requirement {res.id}: not a formal or natural-language requirement"
    declared = _declared_domain(task, res.id)
    if declared is None:
        return False, f"requirement {res.id}: not a requirement of the effective task"
    if not set(declared) <= {"box", "points"}:
        return False, f"requirement {res.id}: its domain is not a declared box or list of points"
    if res.domain is not None and _plain(res.domain) != declared:
        return False, f"requirement {res.id}: assessed on a domain other than the declared one"
    return True, None


def _group(ge: Any) -> dict[str, Any]:
    d = ge.to_dict()
    out = _pick(d, _GROUP_FIELDS) or {}
    trs = []
    for t in d.get("trajectories", []):
        row = _pick(t, _TRAJECTORY_FIELDS) or {}
        for key in ("measures", "prefix_diagnostic"):
            if row.get(key) is not None:
                row[key] = _pick(row[key], _MEASURE_FIELDS)
        if row.get("failure") is not None:
            row["failure"] = _pick(row["failure"], _FAILURE_FIELDS)
        trs.append(row)
    out["trajectories"] = trs
    return out


def _counts(cands: list[dict[str, Any]]) -> dict[str, int]:
    """The pool counts recomputed from the whitelisted candidate fields."""
    evaluated = [c for c in cands if c["status"] == "evaluated"]
    return {
        "proposed": len(cands),
        "accepted_by_checks": sum(1 for c in cands if (c["checks"] or {}).get("passed")),
        "outside_limit": sum(1 for c in cands if c["status"] == "outside_limit"),
        "evaluated": len(evaluated),
        "excluded_by_requirements": sum(1 for c in evaluated if c["excluded_by_requirements"]),
        "failed_numerically_on_visible_data": sum(
            1 for c in evaluated if any(t.get("failure") for g in c["visible"].values() for t in g.get("trajectories", []))
        ),
    }


def permitted_results(evaluation: Any, task: TaskSpec, *, pool_version: int | None = None) -> dict[str, Any]:
    """The results of a pool evaluation that the agent may receive (module docstring).

    ``evaluation`` is a :class:`~aspire_sysid.evaluate.PoolEvaluation`; ``task`` is the effective
    task of the round (with the user's changes). Built by whitelist; the sealed parts are never
    read. The result is plain JSON data.
    """
    withheld: list[str] = []
    cands = []
    for c in evaluation.candidates:
        reqs = []
        for r in c.requirements:
            ok, why = _requirement_permitted(r, task)
            if ok:
                reqs.append(_pick(r.to_dict(), _REQUIREMENT_FIELDS))
            else:
                withheld.append(f"candidate {c.label}, {why}")
        visible = {g: _group(c.visible[g]) for g in VISIBLE_GROUPS if g in c.visible}
        cands.append({
            "label": c.label,
            "position": c.position,
            "within_limit": c.within_limit,
            "status": c.status,
            "checks": _pick(c.checks, _CHECK_FIELDS),
            "expressions": dict(c.expressions),
            "complexity": None if c.complexity is None else _pick(c.complexity.to_dict(), _COMPLEXITY_FIELDS),
            "structure": None if c.structure is None else dict(c.structure),
            "structure_group": c.structure_group,
            "requirements": reqs,
            "excluded_by_requirements": any(r.get("excludes") for r in reqs),
            "visible": visible,
            "sensitivity": None if c.sensitivity is None else _pick(c.sensitivity.to_dict(), _SENSITIVITY_FIELDS),
            "failed_computations": [dict(stage=f.get("stage"), error=f.get("error")) for f in c.failed_computations],
        })
    rec = _pick(evaluation.recommendation, _RECOMMENDATION_FIELDS) or {}
    out = {
        "pool_version": pool_version,
        "task_id": evaluation.task_id,
        "formulation": evaluation.formulation,
        "output": task.output,
        "output_unit": task.column(task.output).unit,
        "pool_file": _pick(evaluation.pool_file, _POOL_FILE_FIELDS),
        "counts": _counts(cands),
        "structures": _pick(evaluation.structures, _STRUCTURE_FIELDS),
        "recommendation": rec,
        "candidates": cands,
        "withheld": withheld,
    }
    return _plain(out)


# ---------------------------------------------------------------------------------------------
# Text for the agent
# ---------------------------------------------------------------------------------------------


def _n(x: Any) -> str:
    if x is None:
        return "not available"
    if isinstance(x, str):
        return x
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return str(x)
    return f"{x:.6g}"


def _u(unit: str) -> str:
    """The unit after a value: `` N``, or `` (dimensionless)`` for the unit ``-``."""
    return " (dimensionless)" if unit.strip() in ("", "-") else f" {unit}"


def _measures_text(m: Mapping[str, Any] | None, unit: str) -> str:
    if not m:
        return "no error measures"
    return (
        f"RMSE {_n(m.get('rmse'))}{_u(unit)}, NRMSE {_n(m.get('nrmse'))}, R² {_n(m.get('r2'))} "
        f"over {_n(m.get('n'))} samples"
    )


def _group_text(g: Mapping[str, Any], unit: str) -> list[str]:
    name = {"train": "training", "val": "validation"}.get(g.get("group"), g.get("group"))
    lines = [
        f"  - {name} data: pooled RMSE over the {name} trajectories, "
        f"{_n(g.get('pooled_rmse'))}{_u(unit)} over {_n(g.get('scored_samples'))} scored samples; "
        f"finished on every trajectory: {_n(g.get('finished'))}"
    ]
    for t in g.get("trajectories", []):
        part = f"    - trajectory {t.get('trajectory')}: {_n(t.get('completed_samples'))} of {_n(t.get('required_samples'))} required samples"
        if t.get("measures"):
            part += "; " + _measures_text(t["measures"], unit)
        if t.get("failure"):
            f = t["failure"]
            part += (
                f"; numerical failure at index {_n(f.get('index'))} (time {_n(f.get('time_s'))} s), variable "
                f"{f.get('variable')}: {f.get('reason')}"
            )
        if t.get("prefix_diagnostic"):
            part += "; error before the failure (diagnostic only): " + _measures_text(t["prefix_diagnostic"], unit)
        if t.get("note"):
            part += f"; {t['note']}"
        lines.append(part)
    return lines


def _requirement_text(r: Mapping[str, Any]) -> str:
    if r.get("kind") == "natural_language":
        return f"  - {r.get('id')} (natural language): unresolved; assessed by the human"
    txt = f"  - {r.get('id')} ({r.get('type')}): {r.get('outcome')}, {r.get('status')}"
    if r.get("excludes"):
        txt += ", excludes the candidate"
    elif r.get("status") == "violated" and not r.get("exclude_on_violation"):
        txt += ", reported without exclusion by the user's instruction"
    if r.get("detail"):
        txt += f"; {r['detail']}"
    ce = r.get("counterexample")
    if ce:
        txt += f"; counterexample on the declared domain: {json.dumps(ce, sort_keys=True)}"
    return txt


def render_permitted_blocks(permitted: Mapping[str, Any]) -> list[tuple[str, str]]:
    """The permitted results as text blocks ``(label, text)``: a header and one block per candidate.

    Contents of the round completion: file and expression checks, training and validation errors,
    authorized constraint assessments, diagnostics.
    """
    unit = permitted.get("output_unit") or ""
    pf = permitted.get("pool_file") or {}
    counts = permitted.get("counts") or {}
    head = [
        f"Pool version {_n(permitted.get('pool_version'))}. Pool file: {'valid' if pf.get('valid') else 'missing or invalid'}; "
        f"order {', '.join(pf.get('order') or []) or 'none'}"
        + ("" if pf.get("order_from_pool_file", True) else " (assigned by the harness in file-name order)")
        + f"; pool limit {_n(pf.get('pool_cap'))}.",
    ]
    for i in pf.get("issues") or []:
        head.append(f"  - pool file issue [{i.get('rule')}] {i.get('where')}: {i.get('message')}")
    head.append(
        "Counts (the categories overlap): "
        + ", ".join(f"{k.replace('_', ' ')} {_n(v)}" for k, v in counts.items())
        + "."
    )
    st = permitted.get("structures") or {}
    head.append(f"Distinct expression structures: {_n(st.get('distinct'))} (groups: {json.dumps(st.get('groups'))}).")
    rec = permitted.get("recommendation") or {}
    if rec.get("present"):
        agent = rec.get("agent") or {}
        head.append(f"Your recommendation as recorded: {agent.get('label') or 'no candidate recommended'}.")
    else:
        head.append(f"Recommendation: none recorded ({rec.get('note') or 'absent'}).")
    for note in rec.get("notes") or []:
        head.append(f"  - harness note: {note}")
    blocks = [("pool", "\n".join(head))]
    for c in permitted.get("candidates", []):
        lines = [f"Candidate {c['label']} (position {_n(c.get('position'))}, status {c.get('status')}):"]
        chk = c.get("checks") or {}
        lines.append(f"  - file and expression checks: {'passed' if chk.get('passed') else 'failed'}")
        for i in chk.get("issues") or []:
            lines.append(f"    - [{i.get('rule')}] {i.get('where')}: {i.get('message')}")
        for g in c.get("visible", {}).values():
            lines += _group_text(g, unit)
        if c.get("requirements"):
            lines.append("  - requirements:")
            lines += ["  " + _requirement_text(r) for r in c["requirements"]]
        cx = c.get("complexity")
        if cx:
            lines.append(
                f"  - complexity: {cx.get('fitted_parameters')} fitted, {cx.get('fixed_parameters')} fixed, "
                f"{cx.get('tied_parameters')} tied parameters; {cx.get('noninteger_literals')} non-integer literals; "
                f"{cx.get('node_count')} expression-tree nodes"
            )
        if c.get("structure_group") is not None:
            lines.append(f"  - structure group {c['structure_group']}")
        sv = c.get("sensitivity")
        if sv:
            if sv.get("available"):
                lines.append(
                    f"  - sensitivity rank test on {', '.join(sv.get('data') or [])}: rank {_n(sv.get('rank'))} of "
                    f"{len(sv.get('parameters') or [])} fitted parameters; deficient: {_n(sv.get('deficient'))}"
                    + (f"; dependent groups {json.dumps(sv.get('dependent_groups'))}" if sv.get("dependent_groups") else "")
                )
            else:
                lines.append(f"  - sensitivity rank test not available: {sv.get('reason')}")
        for f in c.get("failed_computations") or []:
            lines.append(f"  - failed computation ({f.get('stage')}): {f.get('error')}")
        blocks.append((c["label"], "\n".join(lines)))
    return blocks


def screen_blocks(
    blocks: list[tuple[str, str]], task: TaskSpec, *, fingerprint: SealedFingerprint | None = None
) -> tuple[list[tuple[str, str]], list[dict[str, str]]]:
    """Replace every block that the leak scanner flags by a withholding statement (module docstring).

    Returns the screened blocks and the findings (kind, block label, matched text) for the record.

    """
    out: list[tuple[str, str]] = []
    findings: list[dict[str, str]] = []
    for label, text in blocks:
        hits = scan_for_sealed_leaks(task, [(label, text)], fingerprint=fingerprint)
        if hits:
            findings += [{"kind": h.kind, "block": label, "detail": h.detail} for h in hits]
            out.append((label, f"Results of {label}: withheld by the harness."))
        else:
            out.append((label, text))
    return out, findings


PERMITTED_OPENING = "the following:"
PERMITTED_CLOSING = "This ends the permitted results"


def render_permitted_text(blocks: list[tuple[str, str]]) -> str:
    """The screened blocks as the text that fills the placeholder of the round-completion message:
    an opening, the blocks, and a closing sentence that the template's
    following full stop ends."""
    return PERMITTED_OPENING + "\n\n" + "\n\n".join(text for _, text in blocks) + "\n\n" + PERMITTED_CLOSING


def permitted_summary(permitted: Mapping[str, Any]) -> str:
    """A short form of the permitted results for the new-round message:
    per candidate the check outcome, the pooled training and validation RMSE and the violated
    requirements."""
    unit = permitted.get("output_unit") or ""
    parts = []
    for c in permitted.get("candidates", []):
        bits = [f"checks {'passed' if (c.get('checks') or {}).get('passed') else 'failed'}"]
        for g in VISIBLE_GROUPS:
            ge = (c.get("visible") or {}).get(g)
            if ge is not None:
                name = "training" if g == "train" else "validation"
                bits.append(f"{name} RMSE {_n(ge.get('pooled_rmse'))}{_u(unit)}")
        viol = [r["id"] for r in c.get("requirements", []) if r.get("status") == "violated"]
        if viol:
            bits.append("violated " + ", ".join(viol))
        parts.append(f"{c['label']}: " + ", ".join(bits))
    return "; ".join(parts) if parts else "no candidate was evaluated"
