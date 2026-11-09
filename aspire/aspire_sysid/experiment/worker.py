"""The worker process of one run of the grid.

Started by :func:`aspire_sysid.experiment.grid.run_grid` with the grid runner's interpreter (on
Windows the renamed host interpreter) as

    <python> -c <boot> <experiment-dir> <run-id> <attempt> <options-json> <grid-pid>

with an environment that holds no API key (:func:`aspire_sysid.experiment.credentials.worker_environment`).
The first line of its standard input is a JSON object ``{"api_key": <key or null>}``; the key is
given to the provider object only. The worker first arranges to end when the grid process ends
(:func:`aspire_sysid.experiment.procs.guard_parent`), then loads the experiment with the grid's
overrides, executes the run (:func:`aspire_sysid.experiment.runner.execute_run`) and exits with
status 0 when the run record was written, 1 otherwise. The boot code puts the harness folder on
``sys.path`` of the worker only; the environment variable ``PYTHONPATH`` is not used, so that the
agent's shell does not inherit it.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Sequence

from ..portable import portable_data, portable_text
from .config import load_experiment, parse_run_id
from .procs import guard_parent
from .runner import RunOptions, execute_run

__all__ = ["main"]


def main(argv: Sequence[str]) -> int:
    """Execute one run; the exit status is 0 when its record was written (module docstring).  """
    from .grid import grid_paths

    exp_dir, rid, attempt, options, grid_pid = argv[0], argv[1], int(argv[2]), json.loads(argv[3]), int(argv[4])
    guard_parent(grid_pid)
    line = sys.stdin.readline()
    secret = json.loads(line) if line.strip() else {}
    exp = load_experiment(exp_dir, tasks_root=options.get("tasks_root"), workspace_root=options.get("workspace_root"),
                          agent_python=options.get("agent_python"), check_task=False)
    spec = next((s for s in exp.grid() if s.run_id == rid), None)
    if spec is None or parse_run_id(rid) is None:
        print(f"not a run of the experiment: {rid}", file=sys.stderr)
        return 2
    opts = RunOptions(dry_run=bool(options.get("dry_run")), octave=options.get("octave", "experiment"),
                      plots=options.get("plots"), fsync=bool(options.get("fsync", True)),
                      api_key=secret.get("api_key") or None, dry_run_pause_s=float(options.get("dry_run_pause_s") or 0.0))
    paths = grid_paths(exp, opts.dry_run)
    try:
        summary = execute_run(exp, spec, attempt=attempt, runs_dir=paths.runs, opts=opts)
    except Exception:  # noqa: BLE001 - reported in the worker log; the run stays interrupted
        print(portable_text(traceback.format_exc()), file=sys.stderr, end="")
        return 1
    print(json.dumps(portable_data(summary.to_dict()), indent=2))
    return 0
