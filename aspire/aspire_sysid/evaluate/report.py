"""Candidate and pool reports: machine-readable JSON and Markdown.

A candidate report gives the file and expression checks, RMSE, NRMSE and R² per
dataset and trajectory, the numbers of samples evaluated and required, the requirement outcomes,
complexity, sensitivity, reference comparisons and plots, and distinguishes missing information,
inapplicable checks and failed computations; a pool report lists the counts of candidates
proposed, accepted, evaluated, excluded, failed numerically and eligible, the number of distinct
structures, the agent's recommendation with its evidence, and any separate oracle-based ranking,
with overlapping categories identified; plots carry captions.

:func:`write_reports` writes, into an output folder:

- ``evaluation.json`` and ``evaluation.md``: the complete evaluation for the user, including the
  sealed results;
- ``permitted.json`` and ``permitted.md``: the permitted view, without any result
  derived from sealed data;
- ``plots/<label>_<group>.png``: the plots, when requested; their captions are in
  ``evaluation.md`` (the plots of the training and validation data also in ``permitted.md``).

The JSON files are written with sorted keys, so that the same evaluation gives byte-identical
files. In the Markdown reports, "not applicable" marks an inapplicable item, "not available"
missing information, and "failed" a computation that did not finish.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..task.schema import TaskSpec
from .plots import GROUP_NAMES, mode_text, plot_caption, plot_group
from .pool import PoolEvaluation, permitted_view

NA = "not applicable"
MISSING = "not available"


def to_json(data: Any) -> str:
    """Deterministic JSON text (sorted keys, two-space indentation, final newline)."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def _num(x: Any, digits: int = 6) -> str:
    if x is None:
        return NA
    if isinstance(x, str):
        return x
    return f"{x:.{digits}g}"


def _groups(include_sealed: bool) -> tuple[str, ...]:
    return ("test", "train", "val") if include_sealed else ("train", "val")


def test_informed_text(test_informed: bool) -> str:
    """The label of a round of interactive operation in a report."""
    if test_informed:
        return (
            "Label: test-informed. The user had been shown results on sealed data (test results or a reference "
            "comparison) before the feedback that seeded this round; its results and its recommendation are not an "
            "independent final test of the identification procedure."
        )
    return "Label: not test-informed. No result on sealed data had been shown to the user before this round."


def render_markdown(
    ev: PoolEvaluation,
    task: TaskSpec,
    *,
    include_sealed: bool = True,
    plot_files: dict | None = None,
    test_informed: bool | None = None,
) -> str:
    """The Markdown report of a pool evaluation; the permitted view without sealed data.

    ``test_informed`` (interactive operation) adds the round's label below the title
    and to the recommendation; ``None`` (autonomous operation) adds nothing.
    """
    d = ev.to_dict(include_sealed)
    y = task.output
    unit = task.column(y).unit
    L: list[str] = []
    title = "Evaluation report" if include_sealed else "Evaluation results permitted to the agent"
    L.append(f"# {title}: task {ev.task_id}")
    L.append("")
    if test_informed is not None:
        L.append(test_informed_text(test_informed))
        L.append("")
    L.append(
        "Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is "
        "one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference "
        "expression) are inaccessible to the agent."
        + (" This report contains results on sealed data and is not shown to the agent." if include_sealed else " This view contains no result derived from sealed data.")
    )
    L.append("")
    s = d["settings"]
    L.append(f"Evaluation mode: {mode_text(task)}.")
    L.append(
        f"Error measures: for one trajectory with scoring interval I of N samples, measured output "
        f"y[k] ({y}, {unit}) and model output ŷ[k], SSE = Σ_(k∈I) (ŷ[k] − y[k])²; RMSE = sqrt(SSE/N), in {unit}; NRMSE = RMSE/σ, with μ and σ "
        f"the mean and the population standard deviation of y on I; R² = 1 − SSE / Σ_(k∈I) (y[k] − μ)²; NRMSE and R² are not applicable "
        f"when σ = 0. The pooled RMSE over several trajectories is S = sqrt(ΣSSE / ΣN); on the test data it is the ranking score."
    )
    if s["failure_limits"]:
        L.append("Numerical failure limits: " + "; ".join(f"{f['variable']} in [{f['lower']:g}, {f['upper']:g}] {f['unit']}" for f in s["failure_limits"]) + f"; evaluation time limit {s['time_limit_s']:g} s per candidate and data group; symbolic time limit {s['symbolic_time_limit_s']:g} s per verification.")
    if s.get("discontinuities"):
        L.append(f"Discontinuous expressions: {s['discontinuities']}.")
    L.append(f"Harness version {s['harness_version']}; NumPy {s['software']['numpy']}; SymPy {s['software']['sympy']}.")
    L.append("")
    # pool
    L.append("## Pool")
    L.append("")
    c = d["counts"]
    L.append("| category | count |")
    L.append("|---|---|")
    for key, text in [
        ("proposed", "candidates proposed"),
        ("accepted_by_checks", "accepted by the file and expression checks"),
        ("outside_limit", f"outside the pool limit of {task.pool_cap} (not evaluated)"),
        ("evaluated", "evaluated"),
        ("excluded_by_requirements", "excluded by physical requirements"),
        ("failed_numerically_on_visible_data", "failed numerically on training or validation data"),
        ("failed_numerically", "failed numerically on test data"),
        ("eligible", "eligible for ranking"),
    ]:
        if key in c:
            L.append(f"| {text} | {NA if c[key] is None else c[key]} |")
    L.append("")
    L.append(f"Note: {c['overlap']['note']}." + (f" Excluded and failed numerically: {', '.join(c['overlap']['excluded_and_failed_numerically'])}." if include_sealed and c['overlap'].get('excluded_and_failed_numerically') else ""))
    st = d["structures"]
    L.append("")
    L.append(f"Distinct structures: {st['distinct']} among {c['evaluated']} evaluated candidates" + ("" if st["exhaustive"] else " (an upper bound: a renaming search was cut)") + f"; groups: {'; '.join(', '.join(g) for g in st['groups']) or NA}. Convention: {st['convention']}.")
    pf = d["pool_file"]
    if not pf["valid"]:
        L.append("")
        L.append("Pool file: invalid or missing: " + "; ".join(f"[{i['rule']}] {i['where']}: {i['message']}" for i in pf["issues"]))
    L.append("")
    L.append("### Recommendation of the agent")
    L.append("")
    rec = d["recommendation"]
    if not rec.get("present"):
        L.append(rec.get("note", MISSING))
        for i in rec.get("issues", []):
            L.append(f"- {i}")
    else:
        a = rec["agent"]
        if a.get("label") is None:
            L.append(f"The agent recommends no candidate. Its reason: {a.get('reason', MISSING)}")
        else:
            L.append(f"Recommended candidate: {a['label']}. The agent's reason: {a.get('reason', MISSING)}")
        for n in rec.get("notes", []):
            L.append(f"- Harness note: {n}.")
        if test_informed is not None:
            L.append(f"- Label of this recommendation: {'test-informed' if test_informed else 'not test-informed'}.")
        if include_sealed and "sealed" in rec:
            r = rec["sealed"]
            L.append(f"- Test score S of the recommended candidate (practical selection): {_num(r['test_score_S'])} {unit}; eligible: {r['eligible']}; rank in the oracle-based selection: {r['rank'] if r['rank'] is not None else NA}.")
    L.append("")
    if include_sealed:
        sealed = d["sealed"]
        L.append("## Oracle-based selection on test data")
        L.append("")
        if sealed["ranking"] is None:
            L.append(sealed["no_ranking_reason"])
        else:
            rk = sealed["ranking"]
            L.append(
                f"Label: {rk['label']}. Candidates considered: {rk['candidates_considered']} eligible of {rk['pool_size']} evaluated. "
                f"Criterion: {rk['criterion']}, the pooled RMSE over the test trajectories "
                + ", ".join(f"{t['trajectory']} ({t['scored_samples']} scored samples)" for t in sealed["test_trajectories"])
                + f". Tie rule: {rk['tie_rule']}. {rk['note']}"
            )
            L.append("")
            if rk["entries"]:
                L.append(f"| rank | candidate | S ({unit}) | unresolved requirements | violations allowed by the user |")
                L.append("|---|---|---|---|---|")
                for e in rk["entries"]:
                    L.append(
                        f"| {e['rank']}{' (tie)' if e['tied_with_previous'] else ''} | {e['label']} | {e['score_S']:.6g} | "
                        f"{', '.join(e['unresolved_requirements']) or 'none'} | {', '.join(e['allowed_violations']) or 'none'} |"
                    )
            else:
                L.append("No candidate is eligible for ranking.")
            if rk["ties"]:
                L.append("")
                L.append("Numerical ties (no difference in performance is claimed): " + "; ".join(", ".join(t) for t in rk["ties"]) + ".")
        L.append("")
    # candidates
    L.append("## Candidates")
    for cd, ce in zip(d["candidates"], ev.candidates):
        L.append("")
        L.append(f"### Candidate {cd['label']}")
        L.append("")
        pos = cd["position"]
        L.append(f"Position in the agent's order: {pos if pos is not None else 'not listed'}. Status: {cd['status'].replace('_', ' ')}.")
        ch = cd["checks"]
        if ch["passed"]:
            L.append("File and expression checks: passed.")
        else:
            L.append("File and expression checks: rejected.")
            for i in ch["issues"]:
                L.append(f"- [{i['rule']}] {i['where']}: {i['message']}")
        for k, v in cd["expressions"].items():
            L.append(f"- `{k} = {v}`")
        if cd["complexity"]:
            cx = cd["complexity"]
            L.append(
                f"Complexity: {cx['fitted_parameters']} fitted, {cx['fixed_parameters']} fixed and {cx['tied_parameters']} tied parameters; "
                f"{cx['noninteger_literals']} non-integer numeric literals; {cx['node_count']} expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once)."
            )
        if cd["status"] != "evaluated":
            L.append("Not evaluated" + (" (outside the pool limit)." if cd["status"] == "outside_limit" else " (rejected by the file and expression checks)."))
            continue
        L.append(f"Structure group {cd['structure_group']}: " + "; ".join(f"`{k} = {v}`" for k, v in cd["structure"].items()))
        L.append("")
        L.append("Requirements:")
        L.append("")
        L.append("| id | type | outcome | status | method | detail |")
        L.append("|---|---|---|---|---|---|")
        for r in cd["requirements"]:
            method = (r.get("symbolic") or {}).get("procedure") if r.get("symbolic") else None
            if r.get("sampling"):
                method = (method + " then " if method else "") + f"sampling ({r['sampling']['samples']} points, seed {r['sampling']['seed']})"
            extra = ""
            if r["outcome"] == "counterexample":
                extra = " Excludes the candidate." if r["excludes"] else (" Allowed without exclusion by the user's instruction" + (f" ({r['exception']['stated_by']}, {r['exception']['date']})" if r.get("exception") else "") + ".")
            L.append(f"| {r['id']} | {r['type']} | {r['outcome']} | {r['status']} | {method or NA} | {r['detail'].replace('|', chr(92) + '|')}{extra} |")
        L.append("")
        for g in _groups(include_sealed):
            gd = cd["sealed"]["test"] if g == "test" else cd["visible"].get(g)
            if gd is None:
                if g == "val" and task.data.val_path is None:
                    continue
                L.append(f"{GROUP_NAMES[g].capitalize()}: {MISSING}.")
                continue
            pooled = "failed (a trajectory did not finish)" if not gd["finished"] else (f"{_num(gd['pooled_rmse'])} {unit}" if gd["pooled_rmse"] is not None else NA)
            L.append(f"Output errors on the {GROUP_NAMES[g]} (pooled RMSE: {pooled}):")
            L.append("")
            L.append(f"| trajectory | scored samples | completed | RMSE ({unit}) | NRMSE | R² | failure |")
            L.append("|---|---|---|---|---|---|---|")
            for t in gd["trajectories"]:
                m = t["measures"] or t["prefix_diagnostic"]
                tag = "" if t["measures"] else (" (prefix diagnostic)" if t["prefix_diagnostic"] else "")
                fail = t["failure"]["detail"] if t["failure"] else "none"
                if t["required_samples"] == 0:
                    L.append(f"| {t['trajectory']} | 0 | 0 | {NA} | {NA} | {NA} | {t['note']} |")
                elif m is None:
                    L.append(f"| {t['trajectory']} | {t['required_samples']} | {t['completed_samples']} | failed | failed | failed | {fail} |")
                else:
                    L.append(f"| {t['trajectory']} | {t['required_samples']} | {t['completed_samples']} | {_num(m['rmse'])}{tag} | {_num(m['nrmse'])} | {_num(m['r2'])} | {fail} |")
            L.append("")
        sn = cd["sensitivity"]
        if sn is not None:
            if not sn["available"]:
                L.append(f"Sensitivity rank test: {MISSING} ({sn['reason']}).")
            else:
                L.append(
                    f"Sensitivity rank test (diagnostic; never excludes): targets {', '.join(sn['targets'])} on the {', '.join(sn['data'])} data "
                    f"({sn['rows']} rows, {sn['rows_dropped']} dropped); {sn['method']}; scaling: {sn['scaling']}; rank threshold {sn['rank_threshold']}; "
                    f"singular values {', '.join(f'{v:.3g}' for v in sn['singular_values'])}; rank {sn['rank']} of {len(sn['parameters'])}."
                )
                for grp in sn["dependent_groups"]:
                    L.append(f"- Locally indistinguishable combination: {', '.join(f'{p} ({v:+.3f})' for p, v in grp['components'].items())}; relative singular value {_num(grp['relative'], 3)}.")
                for p in sn["zero_columns"]:
                    L.append(f"- Parameter {p} has no influence on the targets.")
        failed = list(cd["failed_computations"]) + (list(cd["sealed"]["failed_computations"]) if include_sealed else [])
        for fc in failed:
            L.append(f"- Failed computation ({fc['stage']}): {fc['error']}")
        if include_sealed:
            rc = cd["sealed"]["reference_comparison"]
            if rc is not None:
                L.append(f"Reference comparison: {rc['outcome'].replace('_', ' ')}.")
                for k, r in rc["per_key"].items():
                    na = r.get("numerical_agreement") or {}
                    L.append(f"- {k}: {r['outcome'].replace('_', ' ')}; {r.get('detail', '')}. Numerical agreement (not a proof): max |difference| {_num(na.get('max_abs_difference'))}, RMS difference {_num(na.get('rms_difference'))} at {na.get('points', 0)} points (seed {na.get('seed')}).")
            elif task.sealed.reference is None:
                L.append("Reference comparison: not applicable (the task has no reference expression).")
            L.append(f"Eligible for ranking: {cd['sealed']['eligible'] if cd['sealed']['eligible'] is not None else NA}" + (f" ({'; '.join(cd['sealed']['ineligibility'])})" if cd["sealed"]["ineligibility"] else "") + ".")
        if plot_files:
            for g in _groups(include_sealed):
                key = (cd["label"], g)
                if key in plot_files:
                    path, caption = plot_files[key]
                    L.append("")
                    L.append(f"![{cd['label']} {g}]({path})")
                    L.append("")
                    L.append(f"*{caption}*")
    L.append("")
    return "\n".join(L)


def write_plots(ev: PoolEvaluation, task: TaskSpec, out_dir: str | Path) -> dict[tuple[str, str], tuple[str, str]]:
    """Write the plots of every evaluated candidate and data group; return paths and captions.

 Keys are ``(label, group)``; values are the path relative to ``out_dir`` and the
    caption.
    """
    out = Path(out_dir)
    files = {}
    for ce in ev.evaluated:
        groups = dict(ce.visible)
        if ce.sealed.test is not None:
            groups["test"] = ce.sealed.test
        for g, ge in groups.items():
            rel = f"plots/{ce.label}_{g}.png"
            plot_group(task, ce, ge, out / rel)
            files[(ce.label, g)] = (rel, plot_caption(task, ce, ge))
    return files


def _labelled(d: dict, test_informed: bool | None) -> dict:
    if test_informed is None:
        return d
    d = dict(d)
    d["test_informed"] = test_informed
    if isinstance(d.get("recommendation"), dict):
        d["recommendation"] = dict(d["recommendation"], test_informed=test_informed)
    return d


def write_reports(ev: PoolEvaluation, task: TaskSpec, out_dir: str | Path, *, plots: bool = True, test_informed: bool | None = None) -> list[Path]:
    """Write the JSON and Markdown reports (and plots) of a pool evaluation.

    Returns the written files. The permitted view contains no sealed result and references only
    the plots of the training and validation data. ``test_informed`` (interactive operation) adds the field ``test_informed`` to both JSON files and to their recommendation,
    and the label to both Markdown files; ``None`` leaves the reports unchanged.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    plot_files = write_plots(ev, task, out) if plots else {}
    written = []
    ti = test_informed
    for name, text in [
        ("evaluation.json", to_json(_labelled(ev.to_dict(), ti))),
        ("permitted.json", to_json(_labelled(permitted_view(ev), ti))),
        ("evaluation.md", render_markdown(ev, task, include_sealed=True, plot_files=plot_files, test_informed=ti)),
        ("permitted.md", render_markdown(ev, task, include_sealed=False, plot_files={k: v for k, v in plot_files.items() if k[1] != "test"}, test_informed=ti)),
    ]:
        p = out / name
        p.write_text(text, encoding="utf-8", newline="\n")
        written.append(p)
    written += [out / rel for rel, _ in plot_files.values()]
    return written


def summary_text(ev: PoolEvaluation) -> str:
    """A short plain-text summary of a pool evaluation for the command line."""
    c = ev.counts()
    lines = [
        f"task {ev.task_id}: {c['proposed']} proposed, {c['accepted_by_checks']} accepted by the checks, "
        f"{c['evaluated']} evaluated, {c['outside_limit']} outside the limit, {c['excluded_by_requirements']} excluded by requirements, "
        f"{c['failed_numerically']} failed numerically, eligible: {'not applicable' if c['eligible'] is None else c['eligible']} "
        "(categories overlap)",
        f"distinct structures: {ev.structures['distinct']}",
    ]
    rec = ev.recommendation
    if rec.get("present"):
        lines.append(f"agent's recommendation: {rec['agent'].get('label') or 'none'}")
    if ev.ranking is None:
        lines.append(ev.no_ranking_reason or "no ranking")
    else:
        rk = ev.ranking
        lines.append(f"{rk['label']} ({rk['candidates_considered']} candidates considered, pool size {rk['pool_size']}):")
        for e in rk["entries"]:
            lines.append(f"  {e['rank']}{' (tie)' if e['tied_with_previous'] else ''}  {e['label']}  S = {e['score_S']:.6g}")
    return "\n".join(lines)
