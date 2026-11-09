"""Command-line interface of the harness: the console script ``aspire``.

 Subcommands are registered by the functions in
:data:`COMMANDS`; each function adds one subparser and sets its handler with
``set_defaults(handler=...)``. A handler receives the parsed arguments and returns the exit
status. A subcommand (for example ``run``, ``evaluate``,
``experiment``) is added by writing one registration function and appending it to :data:`COMMANDS`.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Sequence

from . import __version__

Registrar = Callable[["argparse._SubParsersAction[argparse.ArgumentParser]"], None]


def _cmd_prices(args: argparse.Namespace) -> int:
    """Print the dated price schedule."""
    from .agent.prices import PriceTableError, load_price_table

    try:
        table = load_price_table(args.file)
    except PriceTableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Price schedule: {table.origin}")
    print(f"Table verified: {table.verified.isoformat()}")
    print("Prices in USD per 1,000,000 tokens; cached input tokens are charged at the input price.")
    header = ("model", "vendor", "input", "output", "verified", "source")
    rows = [
        (
            p.model,
            p.vendor or "-",
            f"{p.input_usd_per_mtok:.2f}",
            f"{p.output_usd_per_mtok:.2f}",
            p.verified.isoformat(),
            p.source,
        )
        for p in sorted(table.prices.values(), key=lambda p: p.model)
    ]
    widths = [max(len(r[i]) for r in [header, *rows]) for i in range(len(header))]
    for r in [header, *rows]:
        print("  ".join(cell.ljust(w) for cell, w in zip(r, widths)).rstrip())
    return 0


def _register_prices(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser(
        "prices",
        help="print the dated price schedule of the language models",
        description="Print the price schedule used to compute the cost of language-model requests.",
    )
    p.add_argument("--file", default=None, help="price schedule to read (default: aspire/configs/prices.yaml)")
    p.set_defaults(handler=_cmd_prices)


def _cmd_task_validate(args: argparse.Namespace) -> int:
    """Validate a task folder, including its sealed part."""
    from .task import TaskError, validate_task

    try:
        task = validate_task(args.task_dir)
    except TaskError as exc:
        print(f"invalid task: {exc}", file=sys.stderr)
        return 1
    e = task.evaluation
    print(f"valid task: {task.id} (schema version {task.schema_version}, {task.formulation})")
    print(f"expression keys: {', '.join(task.expression_keys)}")
    print(f"evaluation: {e.mode}, initialization {e.initialization}, scoring {e.scoring}")
    print(
        f"requirements: {len(task.requirements)} formal, {len(task.requirements_nl)} in natural language; "
        f"sealed test trajectories: {task.sealed.n_test_trajectories}; "
        f"reference: {'yes' if task.sealed.reference is not None else 'no'}"
    )
    return 0


def _cmd_task_show(args: argparse.Namespace) -> int:
    """Print the public view of a task, the part that may be shown to the agent."""
    import json

    import yaml

    from .task import TaskError, load_task, public_view

    try:
        view = public_view(load_task(args.task_dir))
    except TaskError as exc:
        print(f"invalid task: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(view, indent=2, ensure_ascii=False))
    else:
        print(yaml.safe_dump(view, sort_keys=False, allow_unicode=True, width=100), end="")
    return 0


def _register_task(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser(
        "task",
        help="validate a task folder or print its public view",
        description="Task specifications, schema version 1.",
    )
    tsub = p.add_subparsers(dest="task_command", metavar="subcommand")
    v = tsub.add_parser("validate", help="validate a task folder, including its sealed part")
    v.add_argument("task_dir", help="task folder containing task.yaml")
    v.set_defaults(handler=_cmd_task_validate)
    s = tsub.add_parser("show", help="print the public view of a task (the part shown to the agent)")
    s.add_argument("task_dir", help="task folder containing task.yaml")
    s.add_argument("--json", action="store_true", help="print JSON instead of YAML")
    s.set_defaults(handler=_cmd_task_show)
    p.set_defaults(handler=lambda args: (p.print_help(sys.stderr), 2)[1])


def _cmd_check(args: argparse.Namespace) -> int:
    """Run the file and expression checks on a working directory."""
    from .model import check_workspace
    from .task import TaskError, load_task

    task = None
    if args.task is not None:
        try:
            task = load_task(args.task)
        except TaskError as exc:
            print(f"invalid task: {exc}", file=sys.stderr)
            return 2
    try:
        report = check_workspace(args.workspace_dir, task)
    except (OSError, ValueError) as exc:
        print(f"error: cannot run the checks: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(report.text())
    return 0 if report.passed else 1


def _register_check(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser(
        "check",
        help="run the file and expression checks (rules F1 to P1) on a working directory",
        description=(
            "Check models/pool.json and models/<label>.json of a working directory against the rules "
            "F1 to P1. Without --task, the directory's check_config.json and "
            "data/train.csv are used, as by check_submission.py; with --task, the configuration and "
            "the training data come from the task folder. Exit status: 0 pass, 1 fail, 2 error."
        ),
    )
    p.add_argument("workspace_dir", help="working directory containing models/")
    p.add_argument("--task", default=None, help="task folder whose specification and training data are used")
    p.set_defaults(handler=_cmd_check)


def _cmd_evaluate(args: argparse.Namespace) -> int:
    """Evaluate a candidate pool on a task and write the reports."""
    from .evaluate import evaluate_pool, summary_text, write_reports
    from .task import TaskError, load_task

    try:
        task = load_task(args.task_dir)
    except TaskError as exc:
        print(f"invalid task: {exc}", file=sys.stderr)
        return 2
    try:
        ev = evaluate_pool(task, args.models_dir)
    except (OSError, ValueError) as exc:
        print(f"error: cannot evaluate: {exc}", file=sys.stderr)
        return 2
    print(summary_text(ev))
    if args.out is not None:
        files = write_reports(ev, task, args.out, plots=not args.no_plots)
        print(f"reports written to {args.out} ({len(files)} files)")
    return 0


def _register_evaluate(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser(
        "evaluate",
        help="evaluate a candidate pool on a task and write the reports",
        description=(
            "Check and evaluate the candidate files of a working directory (or its models/ folder) on a task"
            ": requirements, output errors, numerical failures, score, eligibility, ranking, "
            "complexity, structures, sensitivity and reference comparison. With --out, the JSON and Markdown "
            "reports, the permitted view for the agent and the plots are written to that folder."
        ),
    )
    p.add_argument("task_dir", help="task folder containing task.yaml")
    p.add_argument("models_dir", help="working directory containing models/, or the models/ folder itself")
    p.add_argument("--out", default=None, help="folder for evaluation.json, evaluation.md, permitted.json, permitted.md and plots/")
    p.add_argument("--no-plots", action="store_true", help="do not draw the plots")
    p.set_defaults(handler=_cmd_evaluate)



def _write_stdout(text: str) -> None:
    """Write ``text`` to standard output; as UTF-8 bytes when the console encoding cannot encode it
    (a Windows console with a legacy code page and a text with symbols such as ∈ or π)."""
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        sys.stdout.flush()
        sys.stdout.buffer.write(text.encode("utf-8"))


PREVIEW_MARKER = "<!-- end of preview header -->"
"""Line that ends the header of a brief preview; the brief follows after one empty line."""


def preview_header(task_dir: str, interactive: bool, out: str | None = None) -> str:
    """Header of a brief preview written for review.

    The header states the command that regenerates the preview and no date or revision, so that a
    rebase does not change it; the version of the text is the git history of the file."""
    flag = " --interactive" if interactive else ""
    target = f" --out {out}" if out else ""
    return (
        f"> **Preview for review, generated; do not edit.** This is the task brief `TASK.md` that the harness "
        f"writes into the working directory of a run of the task in `{task_dir}`"
        f"{' in interactive operation' if interactive else ' in autonomous operation'}. "
        f"Regenerate it from the repository root with "
        f"`aspire brief {task_dir}{flag} --preview{target}`."
        " The brief starts after the horizontal rule.\n\n---\n\n" + PREVIEW_MARKER + "\n\n"
    )


def _cmd_brief(args: argparse.Namespace) -> int:
    """Render the task brief TASK.md of a task."""
    from .brief import render_brief
    from .task import TaskError, load_task

    try:
        task = load_task(args.task_dir)
    except TaskError as exc:
        print(f"invalid task: {exc}", file=sys.stderr)
        return 1
    text = render_brief(task, interactive=args.interactive)
    if args.preview:
        text = preview_header(args.task_dir, args.interactive, args.out) + text
    if args.out:
        from pathlib import Path

        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(text.encode("utf-8"))
    else:
        _write_stdout(text)
    return 0


def _register_brief(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser(
        "brief",
        help="render the task brief TASK.md of a task",
        description=(
            "Render the task brief TASK.md from the public view of a task."
        ),
    )
    p.add_argument("task_dir", help="task folder containing task.yaml")
    p.add_argument("--interactive", action="store_true", help="render the brief of interactive operation (session limits, ask_user)")
    p.add_argument("--preview", action="store_true", help="prepend a header that marks the file as a generated preview")
    p.add_argument("--out", default=None, help="write the brief to this file (UTF-8) instead of standard output")
    p.set_defaults(handler=_cmd_brief)


def format_preview_header() -> str:
    """Header of the preview of ``FORMAT.md`` written for review."""
    return (
        "> **Preview for review, generated; do not edit.** This is the format reference `FORMAT.md` that the "
        "harness writes into the working directory of every run; it is the same for every task. "
        "Regenerate it from the repository root with "
        "`aspire format --preview --out FORMAT.md`."
        " The reference starts after the horizontal rule.\n\n---\n\n" + PREVIEW_MARKER + "\n\n"
    )


def _cmd_format(args: argparse.Namespace) -> int:
    """Print the format reference FORMAT.md."""
    from .brief import format_reference

    text = format_reference()
    if args.preview:
        text = format_preview_header() + text
    if args.out:
        from pathlib import Path

        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(text.encode("utf-8"))
    else:
        _write_stdout(text)
    return 0


def _register_format(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser(
        "format",
        help="print the format reference FORMAT.md",
        description=(
            "Print FORMAT.md: the model file format, the expression syntax, one general example and the writing "
            "rules. The text is the same for every task."
        ),
    )
    p.add_argument("--preview", action="store_true", help="prepend a header that marks the file as a generated preview")
    p.add_argument("--out", default=None, help="write the text to this file (UTF-8) instead of standard output")
    p.set_defaults(handler=_cmd_format)


def prompts_preview_body() -> str:
    """The body of the review document of the system prompts (``aspire prompt --preview``)."""
    from .brief.prompts import (
        ENVIRONMENT_HEADING,
        FIRST_USER_MESSAGE,
        HELPER_SYSTEM_PROMPT,
        INTERACTIVE_PARAGRAPH,
        system_prompt_core,
    )

    def block(text: str) -> str:
        return "\n".join(("> " + ln) if ln else ">" for ln in text.split("\n"))

    parts = [
        "# System prompts and fixed messages",
        "",
        "The system prompt of the main agent is the text printed in the appendix of the paper, with `{packages}` filled, followed by the "
        "environment description. Below, `{packages}` is left unfilled; the harness fills it with the installed "
        "symbolic-regression packages among PySR, gplearn and PySINDy and their versions (for example "
        "`gplearn 0.4.2`), with `none` when the probe of the agent's interpreter found none of them, and with "
        "`none that the harness could verify` when the probe failed (`aspire_sysid.brief.prompts`).",
        "",
        "## System prompt",
        "",
        block(system_prompt_core("{packages}")),
        "",
        "## Interactive operation",
        "",
        "Appended after the paragraphs above:",
        "",
        block(INTERACTIVE_PARAGRAPH),
        "",
        "## Environment description",
        "",
        f"Appended after one empty line, from the environment probe of the run: the line \"{ENVIRONMENT_HEADING}\", "
        "then the tools, the shell that interprets run_shell commands (cmd.exe on "
        "Windows, with the note that POSIX here-documents do not work there; /bin/sh elsewhere), the Python "
        "version of the agent's interpreter and every installed distribution with its version, sorted by name "
        "(`aspire prompt` prints the prompt of the current environment).",
        "",
        "## Helper agents",
        "",
        block(HELPER_SYSTEM_PROMPT),
        "",
        "## First user message of a round",
        "",
        block(FIRST_USER_MESSAGE),
        "",
    ]
    return "\n".join(parts)


def _cmd_prompt(args: argparse.Namespace) -> int:
    """Print the system prompt of the main agent."""
    from .agent.probe import probe_environment
    from .brief import render_system_prompt
    from .brief.prompts import HELPER_SYSTEM_PROMPT

    if args.preview:
        header = (
            "> **Preview for review, generated; do not edit.** The prompt texts that the harness sends to the agent. "
            "Regenerate it from the repository root with "
            "`aspire prompt --preview > system-prompts.md`."
            "\n\n---\n\n" + PREVIEW_MARKER + "\n\n"
        )
        sys.stdout.write(header + prompts_preview_body())
        return 0
    if args.helper:
        sys.stdout.write(HELPER_SYSTEM_PROMPT + "\n")
        return 0
    probe = probe_environment(args.python)
    _write_stdout(render_system_prompt(None, probe, interactive=args.interactive) + "\n")
    return 0


def _register_prompt(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser(
        "prompt",
        help="print the system prompt of the agent",
        description=(
            "Print the system prompt of the main agent with {packages} and the environment "
            "description filled from a probe of the given interpreter."
        ),
    )
    p.add_argument("--interactive", action="store_true", help="append the paragraph of interactive operation")
    p.add_argument("--python", default=None, help="interpreter of the agent's shell to probe (default: this interpreter)")
    p.add_argument("--helper", action="store_true", help="print the system prompt of a helper agent instead")
    p.add_argument("--preview", action="store_true", help="print all prompt texts as one Markdown document for review")
    p.set_defaults(handler=_cmd_prompt)


def _cmd_export(args: argparse.Namespace) -> int:
    """Export the evaluated pools of run records as Python and Matlab files."""
    from pathlib import Path

    from .export import export_matlab, export_python
    from .record import RecordError

    both = not args.python and not args.matlab
    status = 0
    try:
        if args.python or both:
            for run in args.run_dirs:
                out = Path(args.out) / "python" / Path(run).name if args.out else None
                res = export_python(run, out, pool_version=args.pool_version, task_dir=args.task_dir)
                print(f"python: {res.path} ({len(res.labels)} candidates, re-verification {'passed' if res.verified else 'FAILED'})")
                status |= 0 if res.verified else 1
        if args.matlab or both:
            out = Path(args.out) / "matlab" if args.out else Path(args.run_dirs[0]) / "export" / "matlab"
            rep = export_matlab(args.run_dirs, out, pool_version=args.pool_version, task_dir=args.task_dir,
                                octave=False if args.no_octave else None)
            for tid, folder in rep.folders.items():
                print(f"matlab: {folder}")
            for m in rep.models:
                oct_state = "not run" if m.octave is None else ("passed" if m.octave.get("passed") else "FAILED")
                print(f"  {m.file}  {m.label} (run {m.run_id}): translator {'passed' if m.verification.get('passed') else 'FAILED'}, "
                      f"Octave {oct_state}{'' if m.in_framework else ' [outside HP/: ' + (m.note or '') + ']'}")
            for tid, o in (rep.octave or {}).items():
                fc = o.get("framework_check") or {}
                if fc.get("ran"):
                    print(f"  the Matlab framework under Octave ({tid}): errors reproduced: {'yes' if fc.get('passed') else 'NO'}; "
                          + "; ".join(f"{k} {v.split(' ', 1)[0]}" for k, v in fc.get("steps", {}).items()))
            for s in rep.skipped:
                print(f"  note: {s}")
            status |= 0 if rep.verified else 1
    except (RecordError, FileExistsError, OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return status


def _register_export(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser(
        "export",
        help="export the evaluated pools of run records as Python and Matlab files",
        description=(
            "Export the evaluated pool of each run folder: a standalone Python module (NumPy only) per run, "
            "and a working folder for the Matlab framework per task (data sets, splitData.m, evaluationSets.m, "
            "startup.m, README.md, HP/<setting>/<train name>/modelNN.m in the [y, info] form of srProvenance). Every "
            "export is re-verified numerically; with GNU Octave installed, the M-files and the Matlab framework are also run "
            "in Octave. Without --python or --matlab, both are written."
        ),
    )
    p.add_argument("run_dirs", nargs="+", help="run folders containing run_record.json")
    p.add_argument("--python", action="store_true", help="write the Python module(s)")
    p.add_argument("--matlab", action="store_true", help="write the Matlab working folder(s)")
    p.add_argument("--out", default=None, help="output folder (default: <run-dir>/export/python and <first run-dir>/export/matlab)")
    p.add_argument("--pool-version", type=int, default=None, help="pool version to export (default: the last evaluated one)")
    p.add_argument("--task-dir", default=None, help="task folder, when it moved since the run (its digests are checked)")
    p.add_argument("--no-octave", action="store_true", help="do not run GNU Octave even when it is installed")
    p.set_defaults(handler=_cmd_export)


def _recommendation_text(block: dict) -> str:
    """One line on the agent's recommendation of an evaluation report."""
    if not block.get("present"):
        return block.get("note") or "none recorded"
    agent = block.get("agent") or {}
    label = agent.get("label")
    notes = list(block.get("notes") or [])
    if label is None:
        text = "none; the agent states: " + str(agent.get("reason") or "no reason")
        notes = [n for n in notes if "recommends no candidate" not in n]  # the reason says it already
    else:
        sealed = block.get("sealed") or {}
        s = sealed.get("test_score_S")
        elig = {True: "yes", False: "no"}.get(sealed.get("eligible"), "not available")
        text = (f"{label}; eligible: {elig}"
                + (f"; test score S = {s:.6g}" if isinstance(s, (int, float)) else "")
                + (f"; oracle rank {sealed['rank']}" if sealed.get("rank") is not None else ""))
    return text + (f" (harness notes: {'; '.join(notes)})" if notes else "")


def _cmd_record_show(args: argparse.Namespace) -> int:
    """Print the summary of a run record and of its transcript."""
    from pathlib import Path

    from .record import RecordError, load_run_record, read_transcript, reconstruct_rounds

    try:
        rec = load_run_record(args.run_dir)
    except RecordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    c = rec["consumption"]
    rev = rec["harness"]["code_revision"]
    print(f"run {rec['run_id']}: task {rec['task']['id']} ({rec['task']['formulation']}), "
          f"model {rec['model']['id']}")
    print(f"harness {rec['harness']['version']}, commit {rev.get('commit')}{' (uncommitted changes)' if rev.get('dirty') else ''}; "
          f"task specification sha256 {rec['task']['spec_sha256'][:16]}...")
    print(f"outcome: {rec['outcome']} ({rec['termination_reason']})")
    print(f"consumption: {c['turns']} turns, {c['input_tokens']} input and {c['output_tokens']} output tokens, "
          f"{c['cost_usd']:.4f} USD (price verified {rec['price'].get('verified')}), elapsed execution time {c['elapsed_s']:.1f} s, "
          f"user waiting time {c['waiting_s']:.1f} s, excess {c['excess_by_round_sum']}")
    for r in rec["rounds"]:
        ev = (r.get("evaluation") or {}).get("report") or {}
        counts = ev.get("counts") or {}
        print(f"  session {r['session']} round {r['round']} ({r['mode']}), pool version {r['pool_version']}: {r['outcome']}; "
              f"{r['consumption']['turns']} turns, {r['consumption']['cost_usd']:.4f} USD; evaluated {r['evaluated_labels']}"
              + (f"; eligible {counts.get('eligible')} of {counts.get('evaluated')}" if counts else ""))
        rec_block = ev.get("recommendation")
        if rec_block:
            print(f"    agent's recommendation (practical selection): {_recommendation_text(rec_block)}")
        rk = (ev.get("sealed") or {}).get("ranking")
        if rk:
            top = ", ".join(f"{e['rank']}. {e['label']} (S = {e['score_S']:.6g})" for e in rk["entries"]) or "no eligible candidate"
            n = rk["candidates_considered"]
            print(f"    {rk['label']} ({n} candidate{'' if n == 1 else 's'} considered, pool size {rk['pool_size']}): {top}")
    tpath = Path(args.run_dir) / rec["transcript"]["file"]
    if tpath.is_file():
        tr = read_transcript(tpath)
        for s in reconstruct_rounds(tr):
            seg = f"round {s.round}" + (f", analysis exchange {s.exchange}" if s.exchange is not None else "")
            print(f"  transcript: {seg}: {s.turns} turns, {s.cost_usd:.4f} USD, outcome {s.outcome}; "
                  f"agrees with the recorded totals: {s.consistent}" + ("; last line truncated" if tr.truncated_end else ""))
    return 0


def _cmd_record_verify(args: argparse.Namespace) -> int:
    """Recompute the evaluation of a run record offline and compare it with the stored report."""
    from .record import RecordError, RecordMismatchError, recompute_evaluation

    try:
        recompute_evaluation(args.run_dir, args.pool_version, task_dir=args.task_dir)
    except RecordMismatchError as exc:
        print(f"MISMATCH: {exc}", file=sys.stderr)
        return 1
    except RecordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("the recomputed evaluation equals the stored report")
    from .record import load_run_record
    from .record.run_record import applied_task_changes, is_interactive, round_of_pool

    rec = load_run_record(args.run_dir)
    if is_interactive(rec):
        rnd = round_of_pool(rec, args.pool_version)
        print(f"interactive session: pool version {rnd['pool_version']} (round {rnd['round']}), "
              f"{'test-informed' if rnd.get('test_informed') else 'not test-informed'}")
        changes = applied_task_changes(args.run_dir, rec, rnd)
        if changes:
            print("task changes applied before the evaluation (checked against the transcript):")
            for c in changes:
                print(f"  - {c['kind']} {c.get('requirement') or ''} {'' if c.get('value') is None else c['value']}: "
                      f"\"{c['instruction']}\" ({c['stated_by']}, {c['date']})".replace("  ", " "))
        else:
            print("task changes applied before the evaluation: none")
    return 0


def _cmd_record_report(args: argparse.Namespace) -> int:
    """Write the HTML report of the record folder of an interactive session. The
    session writes this report itself after every round; the command writes it again, for example
    after a change of the report's form."""
    from .report.session_report import build_session_report

    try:
        index = build_session_report(args.run_dir, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {index}")
    return 0


def _register_record(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser("record", help="inspect and verify run records", description="Run records of experiments and interactive sessions.")
    rsub = p.add_subparsers(dest="record_command", metavar="subcommand")
    s = rsub.add_parser("show", help="print the summary of a run record and its transcript")
    s.add_argument("run_dir", help="run folder containing run_record.json")
    s.set_defaults(handler=_cmd_record_show)
    v = rsub.add_parser("verify", help="recompute the evaluation offline and compare it with the stored report")
    v.add_argument("run_dir", help="run folder containing run_record.json")
    v.add_argument("--pool-version", type=int, default=None, help="pool version (default: the last evaluated one)")
    v.add_argument("--task-dir", default=None, help="task folder, when it moved since the run")
    v.set_defaults(handler=_cmd_record_verify)
    r = rsub.add_parser("report", help="write the HTML report of the record folder of an interactive session")
    r.add_argument("run_dir", help="session folder containing session.json")
    r.add_argument("--out", default=None, help="folder of the report (default: <run_dir>/report)")
    r.set_defaults(handler=_cmd_record_report)


def _register_experiment(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    from .experiment.commands import register

    register(sub)


def _register_session(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    from .session.cli import register

    register(sub)


def _register_web(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    from .web.server import register

    register(sub)


COMMANDS: list[Registrar] = [
    _register_prices,
    _register_task,
    _register_check,
    _register_evaluate,
    _register_brief,
    _register_format,
    _register_prompt,
    _register_export,
    _register_record,
    _register_experiment,
    _register_session,
    _register_web,
]
"""Registration functions of the subcommands, in the order shown in the help text."""


def build_parser() -> argparse.ArgumentParser:
    """The argument parser with every registered subcommand."""
    parser = argparse.ArgumentParser(
        prog="aspire",
        description=(
            "Harness of ASPIRE (Agentic System-identification Platform for Iterative Reasoning "
            "and Exploration)."
        ),
    )
    parser.add_argument("--version", action="version", version=f"aspire-sysid {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="command")
    for register in COMMANDS:
        register(sub)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the console script ``aspire``; returns the exit status.

    Without a subcommand, the help text is printed and the exit status is 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    args._argv = list(argv) if argv is not None else sys.argv[1:]
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help(sys.stderr)
        return 2
    return int(handler(args))


if __name__ == "__main__":
    sys.exit(main())
