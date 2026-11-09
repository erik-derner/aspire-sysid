"""Experiments: one task with repeated runs, crash-resume, host-process protection and aggregation.

An experiment is one task, run one or more times with identical settings.
Implements runs and repeated-run statistics (attempted, delivered and eligible counts, mean and
sample standard deviation, runs without a finite result counted and explained), the oracle label
of the test-based ranking, and the protection of the host process.

- :mod:`.config`: ``experiments/<id>/experiment.yaml`` (:func:`load_experiment`,
  :class:`Experiment`, :class:`RunSpec`);
- :mod:`.workspace`: working directories outside every repository and their copies for the record;
- :mod:`.runner`: one run (:func:`execute_run`): provisioning, round, record, leak scan, exports;
- :mod:`.grid`: the runs with concurrency, crash-resume and the lock file (:func:`run_grid`);
- :mod:`.worker`: the worker process of one run;
- :mod:`.host`: the renamed host interpreter on Windows and the POSIX rationale;
- :mod:`.dryrun`: the scripted agent of ``--dry-run``;
- :mod:`.aggregate`: aggregation over the runs (:func:`aggregate_records`, :func:`aggregate_experiment`);
- :mod:`.agentenv`: the agent's virtual environment; :mod:`.credentials`: the API key and ``.env``;
- :mod:`.web`: the fetch backend of real runs;
- :mod:`.commands`: the subcommand ``aspire experiment``.
"""

from .aggregate import AggregationRefused, aggregate_experiment, aggregate_records, describe, render_markdown, run_quantities, write_aggregate
from .config import Experiment, ExperimentError, RunSpec, default_workspace_root, load_experiment, run_id
from .grid import GridError, GridResult, LockHeldError, grid_paths, grid_states, maximum_cost_usd, pending_runs, run_grid
from .runner import RunOptions, RunSummary, execute_run
from .workspace import WorkspaceRootError, check_workspace_root, copy_workspace

__all__ = [
    "AggregationRefused",
    "Experiment",
    "ExperimentError",
    "GridError",
    "GridResult",
    "LockHeldError",
    "RunOptions",
    "RunSpec",
    "RunSummary",
    "WorkspaceRootError",
    "aggregate_experiment",
    "aggregate_records",
    "check_workspace_root",
    "copy_workspace",
    "default_workspace_root",
    "describe",
    "execute_run",
    "grid_paths",
    "grid_states",
    "load_experiment",
    "maximum_cost_usd",
    "pending_runs",
    "render_markdown",
    "run_grid",
    "run_id",
    "run_quantities",
    "write_aggregate",
]
