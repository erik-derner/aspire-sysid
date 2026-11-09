"""The subcommand ``aspire experiment``: run, status, aggregate, report, export and agent-env.

An experiment is one task, run one or more times with identical settings
(:mod:`aspire_sysid.experiment.config`).

    aspire experiment run <experiment-dir> [--resume] [--dry-run] [--yes] [--concurrency N]
                        [--workspace-root DIR] [--agent-python EXE] [--allow-dirty]
                        [--allow-harness-interpreter] [--no-octave]
    aspire experiment status <experiment-dir> [--dry-run]
    aspire experiment aggregate <experiment-dir> [--dry-run] [--out DIR]
    aspire experiment report <experiment-dir> [--dry-run] [--out DIR]
    aspire experiment export <experiment-dir> [--dry-run] [--no-octave]
    aspire experiment agent-env <folder> [--package P ...] [--no-default-packages] [--python EXE]

A real run (without ``--dry-run``) needs the API key of the model's vendor in the environment or
in a ``.env`` file (:mod:`aspire_sysid.experiment.credentials`), prints the number of runs and the
largest cost they can incur (the sum of their round cost limits) and starts only after ``--yes``
or a confirmation typed at the terminal. The key is removed from the grid's environment and
passed to the workers through their standard input. Real runs are
refused when ``aspire/`` or ``tasks/`` has uncommitted changes (the harness identity, the git tree
hashes of these folders, would not identify the code and the tasks; ``--allow-dirty`` overrides) or when the harness package can be imported from the agent's
interpreter (``--allow-harness-interpreter`` overrides). Exit status of ``run``: 0 when every
executed run finished without a leak-scan finding; 3 when the leak scan found sealed information;
1 when a run failed or is still running in another process; 2 for a refused start.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

__all__ = ["register"]


def _load(args: argparse.Namespace):
    from .config import load_experiment

    return load_experiment(
        args.experiment_dir,
        workspace_root=getattr(args, "workspace_root", None),
        agent_python=getattr(args, "agent_python", None),
        tasks_root=getattr(args, "tasks_root", None),
    )


def _confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _cmd_run(args: argparse.Namespace) -> int:
    """Execute the runs of an experiment."""
    from ..record import code_revision
    from .agentenv import inspect_agent_interpreter
    from .credentials import MissingKeyError, take_api_key
    from .config import ExperimentError
    from .grid import GridError, maximum_cost_usd, pending_runs, run_grid
    from .host import maybe_relaunch_under_host, receive_relaunch_keys
    from .runner import RunOptions
    from .workspace import WorkspaceRootError, check_workspace_root

    relaunched = maybe_relaunch_under_host(getattr(args, "_argv", sys.argv[1:]))
    if relaunched is not None:
        return relaunched
    receive_relaunch_keys()  # in the re-launched host process only
    try:
        exp = _load(args)
        check_workspace_root(exp.workspace_root)
    except (ExperimentError, WorkspaceRootError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    strict = not args.dry_run
    pending = pending_runs(exp, args.dry_run)
    api_key = source = None
    if not args.dry_run and pending:
        # the key is taken before any subprocess starts, so that none inherits it
        try:
            api_key, source = take_api_key(exp.vendor, experiment_dir=exp.dir)
        except MissingKeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    rev = code_revision()
    ident = rev.get("identity") or {}
    interp = inspect_agent_interpreter(exp.agent_python)
    print(f"experiment {exp.id}{' (DRY RUN with the scripted agent)' if args.dry_run else ''}: task {exp.task}, {exp.runs} run(s); model {exp.model}")
    trees = ", ".join(f"{k} {str(v)[:12]}" for k, v in (ident.get("trees") or {}).items())
    print(f"harness identity: git trees {trees or 'not available'}{'; aspire/ or tasks/ HAS CHANGES' if ident.get('dirty') else ''} "
          f"(repository commit {rev.get('commit')}, for information)")
    print(f"agent interpreter {interp.executable}: Python {interp.python_version}; harness importable: {interp.harness_importable}")
    print(f"working directories under {exp.workspace_root}")
    if not interp.runs:
        print(f"error: the agent's interpreter does not run: {interp.error}", file=sys.stderr)
        return 2
    if strict and (not ident or ident.get("dirty") or None in (ident.get("trees") or {None: None}).values()) and not args.allow_dirty:
        print("error: aspire/ or tasks/ has uncommitted changes (or the git trees are not available); the harness identity "
              "(git tree hashes of aspire/ and tasks/) would not identify the code and the tasks. Commit first, or pass --allow-dirty.",
              file=sys.stderr)
        return 2
    if strict and interp.harness_importable and not args.allow_harness_interpreter:
        print("error: the harness package can be imported from the agent's interpreter; create a separate environment with "
              "`aspire experiment agent-env <folder>` and set agent_python (or --agent-python), or pass --allow-harness-interpreter.",
              file=sys.stderr)
        return 2
    finished = len(exp.grid()) - len(pending)
    print(f"runs: {len(exp.grid())} planned, {finished} finished, {len(pending)} to execute; concurrency {args.concurrency or exp.concurrency}")
    if not pending:
        print("nothing to execute")
    if api_key is not None:
        where = {
            "environment": "the environment (removed from this process's environment; it stays readable in the start-time "
                           "environment of this process, /proc/<pid>/environ on Linux; a .env file avoids this)",
            "launcher": "the launching process, through standard input",
        }.get(str(source), f"{source} (never put into an environment)")
        print(f"API key: from {where}; passed to the workers through standard input")
        cap = maximum_cost_usd(exp, [p.spec for p in pending])
        print(f"largest cost of these runs: {cap:.2f} USD (the sum of their round cost limits; a round can exceed its limit by the "
              "cost of the request during which the limit was reached)")
        if not args.yes and not _confirm("start the runs? [y/N] "):
            print("not started (pass --yes to start without the question)", file=sys.stderr)
            return 2
    opts = RunOptions(dry_run=args.dry_run, octave=False if args.no_octave else "experiment", api_key=api_key)
    try:
        result = run_grid(exp, opts=opts, resume=args.resume, concurrency=args.concurrency, echo=print)
    except GridError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    status = 0
    print("")
    print("summary:")
    for s in result.executed:
        print(f"  {s.run_id}: {s.outcome}, {s.turns} turns, {s.cost_usd:.4f} USD, exports {s.exports}, leak-scan findings {len(s.leak_findings)}")
    for f in result.failed:
        print(f"  {f['run_id']} (attempt {f['attempt']}): FAILED, the run stays interrupted: {f['error']}")
    for a in result.archived:
        print(f"  interrupted attempt kept as interrupted/{a}")
    for r in result.still_running:
        print(f"  {r['run_id']}: STILL RUNNING in process {r['pid']} on {r['host']}; not archived, not repeated; resume again after it has ended")
        status = 1
    ee = result.experiment_export
    if ee:
        print(f"  experiment-level Matlab export: {ee.get('status')}{' ' + str(ee.get('folder')) if ee.get('folder') else ''}"
              f"{'; ' + ee['error'] if ee.get('error') else ''}")
        if ee.get("status") == "failed":
            status = 1
    if result.failed:
        status = 1
    if result.leak_findings:
        print("", file=sys.stderr)
        print("!!! LEAK SCAN: SEALED INFORMATION FOUND IN A TRANSCRIPT OR AN AGENT-WRITTEN FILE !!!", file=sys.stderr)
        for f in result.leak_findings:
            print(f"!!! {f['run_id']}: {f['kind']} in {f['where']}: {f['detail']}", file=sys.stderr)
        status = 3
    return status


def _cmd_status(args: argparse.Namespace) -> int:
    """Print the state of every run of an experiment."""
    import json

    from .config import ExperimentError
    from .grid import grid_paths, grid_states, pid_alive

    try:
        exp = _load(args)
    except ExperimentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    paths = grid_paths(exp, args.dry_run)
    running = False
    if paths.lock.is_file():
        try:
            lock = json.loads(paths.lock.read_text(encoding="utf-8"))
            running = pid_alive(int(lock.get("pid", -1)))
            print(f"lock: process {lock.get('pid')} on {lock.get('host')}, started {lock.get('started_at')} ({'running' if running else 'not running: stale'})")
        except (OSError, ValueError):
            print(f"lock: {paths.lock} exists and cannot be read")
    counts: dict[str, int] = {}
    for st in grid_states(exp, args.dry_run):
        state = st.state
        if state == "interrupted" and running:
            state = "running or interrupted"
        counts[state] = counts.get(state, 0) + 1
        extra = ""
        if st.state == "finished":
            extra = f" ({st.outcome}{'' if st.export_complete else '; export missing'})"
        if st.interrupted_attempts:
            extra += f" [{st.interrupted_attempts} interrupted attempt(s)]"
        print(f"  {st.spec.run_id}: {state}{extra}")
    print("totals: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return 0


def _cmd_aggregate(args: argparse.Namespace) -> int:
    """Aggregate the finished runs of an experiment."""
    from .aggregate import AggregationRefused, aggregate_experiment, write_aggregate
    from .config import ExperimentError
    from .grid import grid_paths

    try:
        exp = _load(args)
        agg = aggregate_experiment(exp, dry_run=args.dry_run)
    except (ExperimentError, AggregationRefused) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else grid_paths(exp, args.dry_run).base
    j, m = write_aggregate(agg, out)
    print(f"wrote {j} and {m}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    """Write the HTML report of an experiment (:mod:`aspire_sysid.report`)."""
    from ..report import build_report
    from .grid import DRY_RUN_DIR

    base = Path(args.experiment_dir) / DRY_RUN_DIR if args.dry_run else None
    try:
        index = build_report(args.experiment_dir, args.out, runs_base=base)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {index}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    """Add the finished runs to the experiment-level Matlab export."""
    from .config import ExperimentError
    from .grid import GridError, acquire_lock, export_experiment_matlab, grid_paths, release_lock
    from .runner import RunOptions

    try:
        exp = _load(args)
        paths = grid_paths(exp, args.dry_run)
        acquire_lock(paths.lock)
    except (ExperimentError, GridError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        res = export_experiment_matlab(exp, paths, RunOptions(dry_run=args.dry_run, octave=False if args.no_octave else "experiment"))
    except Exception as exc:  # noqa: BLE001 - reported
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        release_lock(paths.lock)
    print(f"experiment-level Matlab export: {res.get('status')} {res.get('folder', '')}")
    for rid in res.get("added", []):
        print(f"  added {rid}")
    return 0 if res.get("verified", True) else 1


def _cmd_agent_env(args: argparse.Namespace) -> int:
    """Create a virtual environment for the agent's shell without the harness package."""
    from .agentenv import DEFAULT_AGENT_PACKAGES, AgentEnvironmentError, create_agent_environment, default_agent_env_dir, venv_python

    if args.folder is None:
        args.folder = str(default_agent_env_dir())
    packages = ([] if args.no_default_packages else list(DEFAULT_AGENT_PACKAGES)) + list(args.package or [])
    try:
        info = create_agent_environment(args.folder, packages, python=args.python)
    except AgentEnvironmentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"created {args.folder}: Python {info.python_version}; harness importable: {info.harness_importable}")
    print(f"pass to aspire experiment run:  --agent-python {venv_python(Path(args.folder).resolve())}")
    print("(do not commit this path in experiment.yaml: it names a folder of this computer)")
    return 0


def register(sub: Any) -> None:
    """Register ``aspire experiment`` and its subcommands. """
    p = sub.add_parser("experiment", help="run, inspect and aggregate the runs of an experiment",
                       description="An experiment is one task, run one or more times with identical settings.")
    csub = p.add_subparsers(dest="experiment_command", metavar="subcommand")

    r = csub.add_parser("run", help="execute the runs of an experiment (crash-resume with --resume)")
    r.add_argument("experiment_dir")
    r.add_argument("--resume", action="store_true", help="continue an experiment: keep finished runs, archive and repeat interrupted ones")
    r.add_argument("--dry-run", action="store_true", help="replace the language model by the scripted agent (no cost; writes into <experiment>/dry-run/)")
    r.add_argument("--yes", action="store_true", help="start a real run without the confirmation question")
    r.add_argument("--concurrency", type=int, default=None, help="runs at the same time (default: the experiment's)")
    r.add_argument("--workspace-root", default=None, help="folder of the working directories (default: the experiment's, or <system temp>/aspire-runs)")
    r.add_argument("--agent-python", default=None, help="interpreter of the agent's shell (default: the experiment's, or the harness's)")
    r.add_argument("--tasks-root", default=None, help="task store (default: the experiment's, or ../../tasks)")
    r.add_argument("--allow-dirty", action="store_true", help="allow a real run with uncommitted changes in aspire/ or tasks/")
    r.add_argument("--allow-harness-interpreter", action="store_true", help="allow an agent interpreter that can import the harness package")
    r.add_argument("--no-octave", action="store_true", help="do not run the Matlab exports in GNU Octave")
    r.set_defaults(handler=_cmd_run)

    s = csub.add_parser("status", help="print the state of every run of the experiment")
    s.add_argument("experiment_dir")
    s.add_argument("--tasks-root", default=None, help="task store (default: the experiment's, or ../../tasks)")
    s.add_argument("--dry-run", action="store_true", help="the dry runs (<experiment>/dry-run/)")
    s.set_defaults(handler=_cmd_status)

    a = csub.add_parser("aggregate", help="aggregate the finished runs (JSON and Markdown)")
    a.add_argument("experiment_dir")
    a.add_argument("--tasks-root", default=None, help="task store (default: the experiment's, or ../../tasks)")
    a.add_argument("--dry-run", action="store_true", help="aggregate the dry runs")
    a.add_argument("--out", default=None, help="output folder (default: the experiment folder, or <experiment>/dry-run/)")
    a.set_defaults(handler=_cmd_aggregate)

    h = csub.add_parser("report", help="write the HTML report: one page for the experiment and one page per run")
    h.add_argument("experiment_dir")
    h.add_argument("--dry-run", action="store_true", help="the report of the dry runs (<experiment>/dry-run/)")
    h.add_argument("--out", default=None, help="output folder (default: <experiment>/report, or <experiment>/dry-run/report)")
    h.set_defaults(handler=_cmd_report)

    x = csub.add_parser("export", help="add the finished runs to the experiment-level Matlab export")
    x.add_argument("experiment_dir")
    x.add_argument("--tasks-root", default=None, help="task store (default: the experiment's, or ../../tasks)")
    x.add_argument("--dry-run", action="store_true", help="the dry runs")
    x.add_argument("--no-octave", action="store_true", help="do not run the M-files in GNU Octave")
    x.set_defaults(handler=_cmd_export)

    e = csub.add_parser("agent-env", help="create a virtual environment for the agent's shell without the harness package")
    e.add_argument("folder", nargs="?", default=None,
                   help="the new environment's folder, outside the repository (default: the folder that aspire session "
                   "looks for, %%LOCALAPPDATA%%/aspire/agent-env on Windows and ~/.local/share/aspire/agent-env elsewhere)")
    e.add_argument("--package", action="append", help="a further distribution to install (repeatable), for example pysr")
    e.add_argument("--no-default-packages", action="store_true", help="install only the --package distributions")
    e.add_argument("--python", default=None, help="base interpreter of the environment (default: the harness's)")
    e.set_defaults(handler=_cmd_agent_env)
    p.set_defaults(handler=lambda args: (p.print_help(sys.stderr), 2)[1])
