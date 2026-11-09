"""Collects the results of the six experiments of the manuscript and of the reference models.

Plain code, no language model. The script reads

- ``experiments/paper-*/aggregate.json`` (written by ``aspire experiment aggregate``),
- the run records, transcripts and delivered model files of the runs,
- ``experiments/references/<task>/{models,pysr-default,pysr-matched}/evaluation/evaluation.json``
  (written by ``aspire evaluate``),

and writes into ``experiments/paper/``

- ``results.json``: every number that the manuscript reports, with its source;
- ``results.md``: the same as tables for reading;
- ``tables.tex``: the bodies of the tables of the manuscript;

and into the output folder ``paper/figures/`` (created by the script) the figures
``test-<system>.pdf``: measured and simulated output on
the test data for the recommended candidate of the median run of each described task. The median
run of an experiment is the run whose recommended candidate has the median test score S among
the runs with a finite S (the lower of the two middle runs for an even number); it is fixed by
this rule, not chosen by inspection.

Requirements: for every run the outcomes of the formal requirements of the task are read from
the evaluation report of the run (``runs/<run>/evaluation/v1/evaluation.json``): per candidate the
requirements with a demonstrated violation (outcome ``counterexample``), and whether the candidate
is excluded by them. The same is read for the models of PySINDy and PySR, whose test scores do
not depend on the requirements and are reported whether or not a model violates one.

Statistics over the runs of an experiment are those of the aggregation: mean, sample standard
deviation (divisor k - 1) and the number k of runs with a finite value. For PySR the same
statistics are computed here over the five seeds.

Run with the interpreter of the harness, from the repository root::

    .venv/Scripts/python.exe experiments/paper/collect_results.py
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]

EXPERIMENTS = [
    {"id": "paper-turtlebot", "system": "turtlebot", "context": "described", "task": "turtlebot"},
    {"id": "paper-turtlebot-blind", "system": "turtlebot", "context": "blind", "task": "task-kt5o"},
    {"id": "paper-friction-driven", "system": "friction-driven", "context": "described", "task": "friction-driven"},
    {"id": "paper-friction-driven-blind", "system": "friction-driven", "context": "blind", "task": "task-jdhj"},
    {"id": "paper-fermenter-pressure", "system": "fermenter-pressure", "context": "described", "task": "fermenter-pressure"},
    {"id": "paper-fermenter-pressure-blind", "system": "fermenter-pressure", "context": "blind", "task": "task-qtqm"},
]
SYSTEM_NAMES = {"turtlebot": "Mobile robot", "friction-driven": "Friction system", "fermenter-pressure": "Fermenter"}
UNITS = {"turtlebot": "m", "friction-driven": "rad", "fermenter-pressure": "bar"}
QUANTITIES = ["recommended_train_rmse", "recommended_test_S", "oracle_best_S", "pool_size",
              "evaluated_candidates", "distinct_structures", "sensitivity_deficient",
              "recommended_fitted_parameters", "recommended_node_count", "turns", "input_tokens",
              "output_tokens", "cost_usd", "elapsed_s"]
SR_IMPORT = re.compile(r"(?:^|[\s;])(?:import|from)\s+(gplearn|pysindy|pysr)\b")
REFERENCE_POOLS = {"models": "PySINDy", "pysr-default": "PySR, default setting",
                   "pysr-matched": "PySR, matched setting"}
# The pool ``models`` of experiments/references also holds a model written by hand from physical
# knowledge. The manuscript compares with PySINDy and PySR only, so these labels
# are not collected; their evaluation stays in experiments/references/<task>/evaluation/.
HAND_WRITTEN = ("ReferenceUnicycle", "ReferencePhysical")


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stats(values: list[float]) -> dict:
    finite = [v for v in values if v is not None and math.isfinite(v)]
    return {"values": values, "n_finite": len(finite), "n": len(values),
            "mean": statistics.fmean(finite) if finite else None,
            "sd": statistics.stdev(finite) if len(finite) > 1 else None,
            "min": min(finite) if finite else None, "max": max(finite) if finite else None}


def decimals_for(sd: float | None, mean: float | None) -> int:
    """Decimals such that the standard deviation (or the mean) has two significant digits."""
    ref = sd if sd else mean
    if not ref:
        return 0
    return max(0, 1 - math.floor(math.log10(abs(ref))))


def pm(q: dict, tex: bool = False, decimals: int | None = None) -> str:
    """``mean ± sd (k)`` of a quantity record of the aggregation or of :func:`stats`."""
    if q.get("mean") is None:
        return "no finite result"
    d = decimals_for(q.get("sd"), q["mean"]) if decimals is None else decimals
    sign = r" $\pm$ " if tex else " ± "
    if q.get("sd") is None:
        return f"{q['mean']:.{d}f} (single)"
    return f"{q['mean']:.{d}f}{sign}{q['sd']:.{d}f}"


def pmk(q: dict, decimals: int) -> str:
    """As :func:`pm` for a table of the manuscript, with the number of finite values when some are missing."""
    n, k = q.get("n_runs", q.get("n")), q.get("n_finite")
    return pm(q, True, decimals) + ("" if k == n else f" ({k} of {n})")


def requirement_outcomes(candidates: list[dict]) -> dict:
    """Per candidate label: the outcome of every formal requirement, the violated ones and the exclusion."""
    out = {}
    for cand in candidates:
        formal = [r for r in cand.get("requirements") or [] if r.get("kind") == "formal"]
        out[cand["label"]] = {"outcomes": {r["id"]: r["outcome"] for r in formal},
                              "violated": [r["id"] for r in formal if r["outcome"] == "counterexample"],
                              "excluded": bool(cand.get("excluded_by_requirements"))}
    return out


def tool_use(transcript: pathlib.Path) -> dict:
    """Counts of tool calls of a run (main agent and helper agents) and use of an SR package.

    ``sr_packages`` lists the packages of gplearn, PySINDy and PySR that a file written by the
    agent or a shell command imports; ``sr_executed`` is true when such an import is in a shell
    command or in a written file whose name appears in a later shell command.
    """
    calls: dict[str, int] = {}
    helpers = web_search = 0
    written: dict[str, set[str]] = {}
    packages: set[str] = set()
    executed: set[str] = set()
    with open(transcript, encoding="utf-8") as fh:
        for line in fh:
            ev = json.loads(line)
            kind = ev.get("kind")
            if kind == "helper_start":
                helpers += 1
            elif kind == "response":
                web_search += int((ev.get("usage") or {}).get("web_search_calls") or 0)
            elif kind == "tool_call":
                tool = ev.get("tool")
                calls[tool] = calls.get(tool, 0) + 1
                args = ev.get("arguments") or {}
                if tool == "write_file":
                    found = set(SR_IMPORT.findall(str(args.get("content", ""))))
                    if found:
                        written[pathlib.PurePosixPath(str(args.get("path", ""))).name] = found
                        packages |= found
                elif tool == "run_shell":
                    command = str(args.get("command", ""))
                    inline = set(SR_IMPORT.findall(command))
                    packages |= inline
                    executed |= inline
                    for name, found in written.items():
                        if name and name in command:
                            executed |= found
    return {"tool_calls": calls, "helpers_started": helpers, "web_search_calls": web_search,
            "sr_packages_imported": sorted(packages), "sr_packages_executed": sorted(executed)}


def run_details(exp_dir: pathlib.Path, run: dict) -> dict:
    run_dir = exp_dir / "runs" / run["run_id"]
    record = load_json(run_dir / "run_record.json")
    out = {k: run.get(k) for k in ("run_id", "outcome", "delivered", "eligible", "recommended_label",
                                   "recommended_train_rmse", "recommended_test_S", "oracle_best_label",
                                   "oracle_best_S", "oracle_candidates_considered", "pool_size",
                                   "evaluated_candidates", "eligible_candidates", "distinct_structures",
                                   "sensitivity_deficient", "turns", "input_tokens", "output_tokens",
                                   "cost_usd", "elapsed_s", "leak_findings", "termination_reason")}
    out["created_at"] = record.get("created_at")
    first = json.loads(open(run_dir / "transcript.jsonl", encoding="utf-8").readline())
    out["started_at"] = first.get("recorded_at")
    out["platform"] = record["software"].get("platform")
    out["agent_packages"] = {k: record["environment"]["packages"].get(k) for k in
                             ("numpy", "scipy", "sympy", "pandas", "scikit-learn", "gplearn", "pysindy")}
    out["agent_python"] = record["environment"].get("python_version")
    out.update(tool_use(run_dir / "transcript.jsonl"))
    label = run.get("recommended_label")
    evaluation = run_dir / "evaluation" / "v1" / "evaluation.json"
    reqs = requirement_outcomes(load_json(evaluation)["candidates"]) if evaluation.exists() else {}
    out["candidate_violations"] = {k: v["violated"] for k, v in reqs.items()}
    out["excluded_labels"] = [k for k, v in reqs.items() if v["excluded"]]
    out["excluded_by_requirements"] = len(out["excluded_labels"])
    out["recommended_excluded"] = bool(label and reqs.get(label, {}).get("excluded"))
    out["recommended_violations"] = reqs.get(label, {}).get("violated", []) if label else []
    out["recommended_family"] = None
    if label:
        model_file = run_dir / "pools" / "v1" / "models" / f"{label}.json"
        if model_file.exists():
            model = load_json(model_file)
            out["recommended_family"] = model.get("discussion", {}).get("family")
            out["recommended_expressions"] = model.get("expressions")
    return out


def median_run(runs: list[dict]) -> str | None:
    finite = sorted((r["recommended_test_S"], r["run_id"]) for r in runs
                    if r.get("recommended_test_S") is not None and math.isfinite(r["recommended_test_S"]))
    return finite[(len(finite) - 1) // 2][1] if finite else None


def collect_experiment(exp: dict) -> dict | None:
    exp_dir = REPO / "experiments" / exp["id"]
    if not (exp_dir / "aggregate.json").exists():
        return None
    agg = load_json(exp_dir / "aggregate.json")
    runs = [run_details(exp_dir, r) for r in agg["runs"]]
    return {
        **exp,
        "planned": agg["runs_planned"], "attempted": agg["runs_attempted"], "delivered": agg["delivered"],
        "eligible": agg["eligible"], "interrupted_attempts": agg["interrupted_attempts"],
        "outcomes": agg["outcomes"], "leak_findings": agg["leak_findings"],
        "identity": agg["identity"], "pool_cap": agg["pool_cap"], "output": agg["output"],
        "quantities": {q: {k: agg["quantities"][q][k] for k in ("mean", "sd", "n_finite", "n_runs", "min", "max", "values")}
                       for q in QUANTITIES if q in agg["quantities"]},
        "per_trajectory_rmse": agg.get("per_trajectory_rmse"),
        "requirements": agg.get("requirements"),
        "candidates": {"evaluated": sum(r["evaluated_candidates"] or 0 for r in runs),
                       "eligible": sum(r["eligible_candidates"] or 0 for r in runs),
                       "excluded_by_requirements": sum(r["excluded_by_requirements"] for r in runs),
                       "runs_with_excluded_recommendation": sum(1 for r in runs if r["recommended_excluded"]),
                       "runs_with_exclusion": sum(1 for r in runs if r["excluded_by_requirements"])},
        "runs": runs,
        "median_run": median_run(agg["runs"]),
        "dates": sorted({r["started_at"][:10] for r in runs if r.get("started_at")}),
        "tool_use_runs": {
            "sr_package_executed": sum(1 for r in runs if r["sr_packages_executed"]),
            "sr_package_imported": sum(1 for r in runs if r["sr_packages_imported"]),
            "web_search": sum(1 for r in runs if r["web_search_calls"] > 0),
            "web_fetch": sum(1 for r in runs if r["tool_calls"].get("web_fetch", 0) > 0),
            "install_package": sum(1 for r in runs if r["tool_calls"].get("install_package", 0) > 0),
            "helper": sum(1 for r in runs if r["helpers_started"] > 0),
        },
    }


def collect_references(task: str) -> dict:
    out = {}
    base = REPO / "experiments" / "references" / task
    for pool, what in REFERENCE_POOLS.items():
        path = base / pool / "evaluation" / "evaluation.json" if pool != "models" else base / "evaluation" / "evaluation.json"
        if not path.exists():
            continue
        report = load_json(path)
        reqs = requirement_outcomes(report["candidates"])
        rows = []
        for cand in report["candidates"]:
            if cand["label"] in HAND_WRITTEN:
                continue
            sealed = cand.get("sealed") or {}
            test = sealed.get("test") or {}
            train = (cand.get("visible") or {}).get("train") or {}
            val = (cand.get("visible") or {}).get("val") or {}
            rows.append({"label": cand["label"], "status": cand.get("status"), "eligible": sealed.get("eligible"),
                         "ineligibility": sealed.get("ineligibility"),
                         "train_rmse": train.get("pooled_rmse"), "val_rmse": val.get("pooled_rmse"),
                         "test_S": sealed.get("score_S"),
                         "test_trajectory_rmse": {t["trajectory"]: (t.get("measures") or {}).get("rmse")
                                                  for t in test.get("trajectories", [])} if test else {},
                         "fitted_parameters": (cand.get("complexity") or {}).get("fitted_parameters"),
                         "nodes": (cand.get("complexity") or {}).get("node_count"),
                         "violated": reqs[cand["label"]]["violated"],
                         "excluded_by_requirements": reqs[cand["label"]]["excluded"],
                         "expressions": cand.get("expressions")})
        entry = {"what": what, "candidates": rows,
                 "models_with_violation": sum(1 for r in rows if r["violated"]),
                 "violated_requirements": sorted({i for r in rows for i in r["violated"]})}
        if pool.startswith("pysr"):
            entry["test_S"] = stats([r["test_S"] for r in rows])
            entry["train_rmse"] = stats([r["train_rmse"] for r in rows])
            entry["eligible"] = sum(1 for r in rows if r["eligible"])
            entry["test_trajectory_rmse"] = {t: stats([r["test_trajectory_rmse"].get(t) for r in rows])
                                             for t in rows[0]["test_trajectory_rmse"]}
        out[pool] = entry
    return out


def derived(experiments: list[dict]) -> dict:
    """Numbers that the text of the manuscript states over all runs or per system; each is computed
    here from the per-run entries, so that no number of the text is counted by hand."""
    runs = [(e, r) for e in experiments for r in e["runs"]]
    finite = lambda v: v is not None and math.isfinite(v)
    out = {
        "runs": len(runs),
        "runs_ended_by_agent": sum(1 for _, r in runs if r.get("termination_reason") == "agent_done"),
        "termination_reasons": sorted({str(r.get("termination_reason")) for _, r in runs}),
        "max_turns": max(r["turns"] for _, r in runs), "max_elapsed_s": max(r["elapsed_s"] for _, r in runs),
        "max_cost_usd": max(r["cost_usd"] for _, r in runs),
        "candidates_evaluated": sum(e["candidates"]["evaluated"] for e in experiments),
        "candidates_eligible": sum(e["candidates"]["eligible"] for e in experiments),
        "candidates_excluded_by_requirements": sum(e["candidates"]["excluded_by_requirements"] for e in experiments),
        "pool_size_min": min(r["pool_size"] for _, r in runs), "pool_size_max": max(r["pool_size"] for _, r in runs),
        "rank_deficient_candidates": sum(r.get("sensitivity_deficient") or 0 for _, r in runs),
        "leak_findings": sum(r.get("leak_findings") or 0 for _, r in runs),
        "runs_with_leak_findings": sum(1 for _, r in runs if r.get("leak_findings")),
        "runs_with_recommendation": sum(1 for _, r in runs if r.get("recommended_label")),
        "runs_with_finite_recommended_S": sum(1 for _, r in runs if finite(r.get("recommended_test_S"))),
        "runs_recommended_is_lowest": sum(1 for _, r in runs if r.get("recommended_label") and r["recommended_label"] == r.get("oracle_best_label")),
        "tool_use_runs": {k: sum(e["tool_use_runs"][k] for e in experiments) for k in experiments[0]["tool_use_runs"]},
        "turns_mean_range": [min(e["quantities"]["turns"]["mean"] for e in experiments), max(e["quantities"]["turns"]["mean"] for e in experiments)],
        "elapsed_min_mean_range": [min(e["quantities"]["elapsed_s"]["mean"] for e in experiments) / 60, max(e["quantities"]["elapsed_s"]["mean"] for e in experiments) / 60],
        "dates": sorted({d for e in experiments for d in e["dates"]}),
    }
    total = sum(r["cost_usd"] for _, r in runs)
    out["total_cost_usd"] = total
    out["cost_per_eligible_candidate_usd"] = total / out["candidates_eligible"] if out["candidates_eligible"] else None
    per_system = {}
    for system in dict.fromkeys(e["system"] for e in experiments):
        exps = [e for e in experiments if e["system"] == system]
        sys_runs = [r for e in exps for r in e["runs"]]
        rec = [r["recommended_test_S"] for r in sys_runs if finite(r.get("recommended_test_S"))]
        losses = []
        for e in exps:
            q = e["quantities"]
            # runs with both a finite recommended score and a finite lowest score of the pool
            pairs = [(r["recommended_test_S"], r["oracle_best_S"]) for r in e["runs"]
                     if finite(r.get("recommended_test_S")) and finite(r.get("oracle_best_S"))]
            if pairs:
                loss = statistics.fmean(a - b for a, b in pairs)
                losses.append({"experiment": e["id"], "runs": len(pairs), "mean_loss": loss,
                               "relative_to_recommended": loss / statistics.fmean(a for a, _ in pairs)})
        per_system[system] = {
            "recommended_S_min": min(rec) if rec else None, "recommended_S_max": max(rec) if rec else None,
            "recommended_S_by_context": {e["context"]: sorted(r["recommended_test_S"] for r in e["runs"] if finite(r.get("recommended_test_S"))) for e in exps},
            "runs_recommended_is_lowest": sum(1 for r in sys_runs if r.get("recommended_label") and r["recommended_label"] == r.get("oracle_best_label")),
            "runs": len(sys_runs), "selection_loss": losses,
        }
    out["per_system"] = per_system
    return out


def figure(exp: dict, result: dict) -> str | None:
    """Measured and simulated output on the test data, recommended candidate of the median run."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from aspire_sysid.evaluate.compiled import CompiledModel
    from aspire_sysid.evaluate.data import sealed_trajectories
    from aspire_sysid.evaluate.pool import check_report
    from aspire_sysid.evaluate.predict import predict_trajectory
    from aspire_sysid.task import load_task

    run_id = result["median_run"]
    if run_id is None:
        return None
    run = next(r for r in result["runs"] if r["run_id"] == run_id)
    task = load_task(REPO / "tasks" / exp["task"])
    report = check_report(task, REPO / "experiments" / exp["id"] / "runs" / run_id / "pools" / "v1" / "models")
    model = CompiledModel(task, report.candidates[run["recommended_label"]].candidate)
    trajectories = sealed_trajectories(task)
    t_s = task.dynamics.sampling_period
    n = len(trajectories)
    columns = 4 if n > 4 else n
    rows = math.ceil(n / columns)
    fig, axes = plt.subplots(rows, columns, figsize=(6.5, 1.6 * rows + 0.5), squeeze=False)
    sse = count = 0.0
    for i, traj in enumerate(trajectories):
        ax = axes[i // columns][i % columns]
        pred = predict_trajectory(model, traj)
        measured = pred.measured
        time = [k * t_s for k in range(len(measured))]
        ax.plot(time, measured, color="black", linewidth=0.9, label="measured")
        ax.plot(time, pred.predicted, color="tab:red", linewidth=0.9, linestyle="--", label="simulated")
        idx = list(pred.completed)
        sse += float(sum((pred.predicted[k] - measured[k]) ** 2 for k in idx))
        count += len(idx)
        ax.set_title(f"test trajectory {i + 1}", fontsize=7)
        ax.tick_params(labelsize=6)
        if i // columns == rows - 1:
            ax.set_xlabel("time (s)", fontsize=7)
        if i % columns == 0:
            ax.set_ylabel(f"{task.output} ({UNITS[exp['system']]})", fontsize=7)
    for j in range(n, rows * columns):
        axes[j // columns][j % columns].axis("off")
    axes[0][0].legend(fontsize=6, frameon=False)
    fig.tight_layout()
    path = REPO / "paper" / "figures" / f"test-{exp['system']}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)  # the folder of the manuscript is not in this repository
    fig.savefig(path, metadata={"CreationDate": None})  # no time stamp: the file is reproducible
    plt.close(fig)
    recomputed = math.sqrt(sse / count) if count else float("nan")
    result["figure"] = {"file": f"paper/figures/{path.name}", "run": run_id, "label": run["recommended_label"],
                        "S_recomputed": recomputed, "S_recorded": run["recommended_test_S"]}
    return path.name


def write_markdown(results: dict) -> str:
    lines = ["# Results of the experiments of the manuscript", "",
             "Written by `experiments/paper/collect_results.py`; do not edit. Entries are mean ± sample "
             "standard deviation over the runs with a finite value (k of N); S is the pooled RMSE of the "
             "simulated output on the test data.", ""]
    lines += ["## Runs", "", "| Experiment | Task | Attempted | Delivered | Eligible | Outcomes | Leak-scan findings | Dates (UTC) |", "|---|---|---|---|---|---|---|---|"]
    for e in results["experiments"]:
        lines.append(f"| {e['id']} | {e['task']} | {e['attempted']} of {e['planned']} | {e['delivered']} | {e['eligible']} | "
                     f"{', '.join(f'{k} {v}' for k, v in e['outcomes'].items())} | {e['leak_findings']} | {', '.join(e['dates'])} |")
    lines += ["", "## Errors", "", "| Experiment | Unit | Training error (recommended) | S (recommended, practical selection) | Lowest S in the pool (oracle-based selection on test data) | Pool sizes | Median run |", "|---|---|---|---|---|---|---|"]
    for e in results["experiments"]:
        q = e["quantities"]
        k = lambda name: f" ({q[name]['n_finite']} of {q[name]['n_runs']})"
        lines.append(f"| {e['id']} | {UNITS[e['system']]} | {pm(q['recommended_train_rmse'])}{k('recommended_train_rmse')} | "
                     f"{pm(q['recommended_test_S'])}{k('recommended_test_S')} | {pm(q['oracle_best_S'])}{k('oracle_best_S')} | "
                     f"{', '.join(str(r['pool_size']) for r in e['runs'])} | {e['median_run']} |")
    lines += ["", "## Compared methods (PySINDy and PySR)", "", "| Task | Model | Eligible | Fitted parameters | Training error | Test score S |", "|---|---|---|---|---|---|"]
    for task, pools in results["references"].items():
        for pool, entry in pools.items():
            if pool == "models":
                for c in entry["candidates"]:
                    lines.append(f"| {task} | {c['label']} | {c['eligible']} | {c['fitted_parameters']} | "
                                 f"{c['train_rmse']:.4g} | {c['test_S'] if c['test_S'] is None else format(c['test_S'], '.4g')} |")
            else:
                lines.append(f"| {task} | {entry['what']} (5 seeds) | {entry['eligible']} of {len(entry['candidates'])} | "
                             f"{', '.join(str(c['fitted_parameters']) for c in entry['candidates'])} | "
                             f"{pm(entry['train_rmse'])} ({entry['train_rmse']['n_finite']} of 5) | "
                             f"{pm(entry['test_S'])} ({entry['test_S']['n_finite']} of 5) |")
    lines += ["", "## Formal requirements", "",
              "Outcomes of the harness's verification: proof (satisfied), counterexample (demonstrated violation, "
              "excludes the candidate), inconclusive or unavailable (unresolved). Requirements stated in natural "
              "language are not listed; a human assesses them.", "",
              "| Experiment | Candidates evaluated | Excluded by requirements | Eligible | Runs with an excluded candidate | Runs with an excluded recommended model |", "|---|---|---|---|---|---|"]
    for e in results["experiments"]:
        c = e["candidates"]
        lines.append(f"| {e['id']} | {c['evaluated']} | {c['excluded_by_requirements']} | {c['eligible']} | {c['runs_with_exclusion']} | {c['runs_with_excluded_recommendation']} |")
    lines += ["", "| Experiment | Requirement | All evaluated candidates | Recommended candidates |", "|---|---|---|---|"]
    fmt = lambda d: ", ".join(f"{k} {v}" for k, v in sorted((d or {}).items())) or "-"
    for e in results["experiments"]:
        req = e.get("requirements") or {}
        for rid in (req.get("all_evaluated") or {}):
            lines.append(f"| {e['id']} | {rid} | {fmt(req['all_evaluated'].get(rid))} | {fmt((req.get('recommended') or {}).get(rid))} |")
    lines += ["", "| Experiment | Run | Excluded candidates (violated requirements) | Recommended model excluded |", "|---|---|---|---|"]
    for e in results["experiments"]:
        for r in e["runs"]:
            if r["excluded_by_requirements"]:
                detail = "; ".join(f"{k}: {', '.join(r['candidate_violations'][k])}" for k in r["excluded_labels"])
                lines.append(f"| {e['id']} | {r['run_id']} | {detail} | {'yes' if r['recommended_excluded'] else 'no'} |")
    lines += ["", "| Task | Models of the tool | Models with a demonstrated violation | Violated requirements |", "|---|---|---|---|"]
    for task, pools in results["references"].items():
        for pool, entry in pools.items():
            lines.append(f"| {task} | {entry['what']} ({len(entry['candidates'])}) | {entry['models_with_violation']} | {', '.join(entry['violated_requirements']) or '-'} |")
    lines += ["", "## Pools", "", "| Experiment | Pool size | Evaluated | Distinct structures | Rank-deficient | Fitted parameters (recommended) |", "|---|---|---|---|---|---|"]
    for e in results["experiments"]:
        q = e["quantities"]
        lines.append(f"| {e['id']} | {pm(q['pool_size'])} | {pm(q['evaluated_candidates'])} | {pm(q['distinct_structures'])} | "
                     f"{pm(q['sensitivity_deficient'])} | {pm(q['recommended_fitted_parameters'])} |")
    lines += ["", "## Tools (runs of the experiment in which the event occurred)", "", "| Experiment | SR package executed | Web search | Web fetch | Package installed | Helper started |", "|---|---|---|---|---|---|"]
    for e in results["experiments"]:
        t = e["tool_use_runs"]
        lines.append(f"| {e['id']} | {t['sr_package_executed']} | {t['web_search']} | {t['web_fetch']} | {t['install_package']} | {t['helper']} |")
    lines += ["", "## Cost", "", "| Experiment | Turns | Input tokens | Output tokens | Elapsed time (s) | Cost (USD) | Total cost (USD) |", "|---|---|---|---|---|---|---|"]
    for e in results["experiments"]:
        q = e["quantities"]
        lines.append(f"| {e['id']} | {pm(q['turns'])} | {pm(q['input_tokens'], decimals=0)} | {pm(q['output_tokens'], decimals=0)} | "
                     f"{pm(q['elapsed_s'], decimals=0)} | {pm(q['cost_usd'], decimals=2)} | {sum(r['cost_usd'] for r in e['runs']):.2f} |")
    lines += ["", f"Total cost of all runs: {results['total_cost_usd']:.2f} USD.", "", "## Runs in detail", "",
              "| Experiment | Run | Outcome | Recommended | Training error | S | Lowest S (oracle) | Pool | Turns | Cost | SR executed | Web searches | Helpers |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    f = lambda v: "-" if v is None else format(v, ".4g")
    for e in results["experiments"]:
        for r in e["runs"]:
            lines.append(f"| {e['id']} | {r['run_id']} | {r['outcome']} | {r['recommended_label']} | {f(r['recommended_train_rmse'])} | "
                         f"{f(r['recommended_test_S'])} | {f(r['oracle_best_S'])} ({r['oracle_best_label']}) | {r['pool_size']} | {r['turns']} | "
                         f"{r['cost_usd']:.2f} | {', '.join(r['sr_packages_executed']) or '-'} | {r['web_search_calls']} | {r['helpers_started']} |")
    d = results["derived"]
    lines += ["", "## Numbers of the text", "",
              f"- Runs: {d['runs']}; with a recommendation {d['runs_with_recommendation']}; with a finite test score of the recommended model {d['runs_with_finite_recommended_S']}; termination reasons: {', '.join(d['termination_reasons'])}.",
              f"- Largest consumption of a run: {d['max_turns']} turns, {d['max_elapsed_s']:.0f} s, {d['max_cost_usd']:.2f} USD.",
              f"- Candidates: {d['candidates_evaluated']} evaluated, {d['candidates_excluded_by_requirements']} excluded by requirements, {d['candidates_eligible']} eligible; pool sizes {d['pool_size_min']} to {d['pool_size_max']}; rank-deficient candidates {d['rank_deficient_candidates']}.",
              f"- Leak-scan findings: {d['leak_findings']} in {d['runs_with_leak_findings']} runs.",
              f"- Recommended model has the lowest test score of its pool: {d['runs_recommended_is_lowest']} of {d['runs']} runs ("
              + "; ".join(f"{k}: {v['runs_recommended_is_lowest']} of {v['runs']}" for k, v in d["per_system"].items()) + ").",
              "- Mean loss of the recommendation against the lowest test score of the pool: "
              + "; ".join(f"{x['experiment']}: {x['mean_loss']:.4f} ({100 * x['relative_to_recommended']:.0f} %, {x['runs']} runs)" for v in d["per_system"].values() for x in v["selection_loss"]) + ".",
              "- Range of the test score of the recommended models: "
              + "; ".join(f"{k}: {v['recommended_S_min']:.4f} to {v['recommended_S_max']:.4f}" for k, v in d["per_system"].items() if v["recommended_S_min"] is not None) + ".",
              f"- Tool use (runs): " + ", ".join(f"{k} {v}" for k, v in d["tool_use_runs"].items()) + ".",
              f"- Mean turns per run by experiment: {d['turns_mean_range'][0]:.1f} to {d['turns_mean_range'][1]:.1f}; mean elapsed time: {d['elapsed_min_mean_range'][0]:.1f} to {d['elapsed_min_mean_range'][1]:.1f} min.",
              f"- Total cost {d['total_cost_usd']:.2f} USD; per eligible candidate {d['cost_per_eligible_candidate_usd']:.2f} USD. Dates of the runs (UTC): {', '.join(d['dates'])}."]
    lines += ["", "## Model families of the recommended candidates", ""]
    for e in results["experiments"]:
        for r in e["runs"]:
            lines.append(f"- **{e['id']} {r['run_id']} ({r['recommended_label']})**: {r['recommended_family']}")
    return "\n".join(lines) + "\n"


def write_tex(results: dict) -> str:
    out = ["% Bodies of the tables of the manuscript; written by experiments/paper/collect_results.py."]
    exps = results["experiments"]
    name = lambda e: f"{SYSTEM_NAMES[e['system']]} & {e['context']}"
    out.append("% tab:aspire (training error, S recommended, lowest S in the pool, pool sizes, fitted parameters of the recommended model, cost per run)")
    for e in exps:
        q = e["quantities"]
        out.append(f"{name(e)} & {pmk(q['recommended_train_rmse'], 4)} & {pmk(q['recommended_test_S'], 4)} & "
                   f"{pmk(q['oracle_best_S'], 4)} & {', '.join(str(r['pool_size']) for r in e['runs'])} & "
                   f"{pmk(q['recommended_fitted_parameters'], 1)} & {pmk(q['cost_usd'], 2)} \\\\")
    out.append("% tab:methods (per system: fitted parameters, test score S), systems in the order mobile robot, friction system, fermenter")
    systems = ("turtlebot", "friction-driven", "fermenter-pressure")
    for context in ("described", "blind"):
        cells = []
        for system in systems:
            q = next(e for e in exps if e["system"] == system and e["context"] == context)["quantities"]
            cells.append(f"{pmk(q['recommended_fitted_parameters'], 1)} & {pmk(q['recommended_test_S'], 4)}")
        out.append(f"ASPIRE, {context} task & " + " & ".join(cells) + " \\\\")
    for setting, label in (("default", "ReferenceSindy"), ("matched", "ReferenceSindyThreshold")):
        cells = []
        for system in systems:
            c = next(c for c in results["references"][system]["models"]["candidates"] if c["label"] == label)
            cells.append(f"{c['fitted_parameters']} & {c['test_S']:.4f}")
        out.append(f"PySINDy, {setting} & " + " & ".join(cells) + " \\\\")
    for setting in ("default", "matched"):
        cells = []
        for system in systems:
            e = results["references"][system][f"pysr-{setting}"]
            counts = [c["fitted_parameters"] for c in e["candidates"]]
            span = str(counts[0]) if min(counts) == max(counts) else f"{min(counts)}--{max(counts)}"
            cells.append(f"{span} & {pm(e['test_S'], True, 4)}")
        out.append(f"PySR, {setting} & " + " & ".join(cells) + " \\\\")
    out.append("% text: turns and elapsed time per run; training error of PySINDy and PySR")
    for e in exps:
        q = e["quantities"]
        out.append(f"% {name(e)}: turns {pm(q['turns'], False, 1)}, time {pm(q['elapsed_s'], False, 0)} s, "
                   f"pool size {pm(q['pool_size'], False, 1)}, rank-deficient candidates {sum(r.get('sensitivity_deficient') or 0 for r in e['runs'])}")
    out.append("% text: formal requirements (candidates evaluated, excluded, eligible; tool models with a demonstrated violation)")
    for e in exps:
        c = e["candidates"]
        out.append(f"% {name(e)}: evaluated {c['evaluated']}, excluded by requirements {c['excluded_by_requirements']}, eligible {c['eligible']}, "
                   f"runs with an excluded recommended model {c['runs_with_excluded_recommendation']}")
    for system in systems:
        for pool, entry in results["references"][system].items():
            out.append(f"% {SYSTEM_NAMES[system]}, {entry['what']}: {entry['models_with_violation']} of {len(entry['candidates'])} models "
                       f"violate a requirement ({', '.join(entry['violated_requirements']) or 'none'})")
    for system in systems:
        pools = results["references"][system]
        sindy = ", ".join(f"{c['label']} {c['train_rmse']:.4f}" for c in pools["models"]["candidates"])
        pysr = ", ".join(f"{p} {pm(pools[p]['train_rmse'], False, 4)}" for p in ("pysr-default", "pysr-matched"))
        out.append(f"% {SYSTEM_NAMES[system]}: training error {sindy}, {pysr}")
    return "\n".join(out) + "\n"

def main() -> None:
    experiments = []
    for exp in EXPERIMENTS:
        result = collect_experiment(exp)
        if result is None:
            print("not aggregated yet:", exp["id"])
            continue
        if exp["context"] == "described" and "--no-figures" not in sys.argv:
            print("figure:", figure(exp, result), result.get("figure"))
        experiments.append(result)
    references = {task: collect_references(task) for task in ("turtlebot", "friction-driven", "fermenter-pressure")}
    results = {"written_by": "experiments/paper/collect_results.py", "experiments": experiments,
               "references": references,
               "derived": derived(experiments),
               "total_cost_usd": sum(r["cost_usd"] for e in experiments for r in e["runs"]),
               "runs_total": {k: sum(e[k] for e in experiments) for k in ("planned", "attempted", "delivered", "eligible")}}
    (HERE / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8", newline="\n")
    (HERE / "results.md").write_text(write_markdown(results), encoding="utf-8", newline="\n")
    (HERE / "tables.tex").write_text(write_tex(results), encoding="utf-8", newline="\n")
    print("written: results.json, results.md, tables.tex;", len(experiments), "experiments")


if __name__ == "__main__":
    main()
