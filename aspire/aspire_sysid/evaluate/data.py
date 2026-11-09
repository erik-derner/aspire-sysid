"""Evaluation data: trajectories and static datasets of the training, validation and test files.

A trajectory is an ordered sequence of samples from one experiment and has an identifier; the
harness never joins the end of one trajectory to the beginning of another; the error
measures apply separately to each trajectory and dataset.

A **data group** is the set of trajectories of one use: ``train`` (the training file), ``val``
(the validation file) or ``test`` (the sealed test files). The training and validation files of a
dynamic task are split into trajectories by the task's trajectory column; each block of rows is
evaluated on its own. A sealed test file is always one trajectory (``tasks/README.md`` §1). A
file of a static task is one **static dataset**, whatever its trajectory column, because a static
model has no memory that could connect samples.

**Horizon.** A simulation error grows with the length of the simulated trajectory, so errors on
trajectories of different lengths are not comparable. A task in simulation mode may declare
``evaluation.horizon`` = H, the length of its test trajectories in simulated samples. The harness
then evaluates the training and validation data in **segments** (:func:`segments`): every
trajectory with n samples and I initialization samples is cut into the row ranges
``[jH, jH + I + H)`` for j = 0, 1, ..., clipped at n, as long as a range holds more than I rows. A
segment starts from the measured state of its first I rows and simulates at most H samples;
consecutive segments share I rows, so that every sample after the first I of the trajectory is
scored exactly once. The segment ``j`` of trajectory ``t`` has the identifier ``t-<j+1>``. The
sealed test files are never cut.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..task.schema import TaskSpec
from ..task.table import Table, read_table, trajectory_blocks
from .sealed import load_test_trajectories

GROUPS = ("train", "val", "test")
"""Data groups in report order. ``test`` is sealed."""

SEALED_GROUPS = frozenset({"test"})
"""Data groups whose results are derived from sealed data and never reach the agent."""


@dataclass(frozen=True)
class Trajectory:
    """One evaluation trajectory or static dataset.

    ``group`` is ``train``, ``val`` or ``test``; ``trajectory`` its identifier (the value of the
    trajectory column, the test entry's identifier, or the group name for a whole file);
    ``columns`` maps every task column to its samples.
    """

    group: str
    trajectory: str
    columns: dict[str, np.ndarray]

    @property
    def n(self) -> int:
        """Number of samples."""
        return len(next(iter(self.columns.values())))


def _id_text(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else repr(float(value))


def split_table(task: TaskSpec, table: Table, group: str) -> list[Trajectory]:
    """Split a training or validation table into its trajectories.

    Dynamic tasks: one :class:`Trajectory` per contiguous block of the trajectory column, or the
    whole table when the task declares none. Static tasks: the whole table as one dataset.
    """
    cols = {name: np.asarray(table.column(name), dtype=float) for name in task.column_names if name in table.header}
    tc = task.data.trajectory_column
    if task.formulation == "static" or not tc or tc not in table.header:
        return [Trajectory(group, group, cols)]
    out = []
    for ident, sl in trajectory_blocks(table.column(tc)):
        out.append(Trajectory(group, _id_text(ident), {k: v[sl].copy() for k, v in cols.items()}))
    return out


def segments(trajectory: Trajectory, horizon: int, initialization: int) -> list[Trajectory]:
    """Cut ``trajectory`` into consecutive segments of at most ``horizon`` simulated samples after
    ``initialization`` samples each (module docstring, "Horizon"). 

    A trajectory that fits into one segment is returned unchanged, with its identifier.
    """
    n = trajectory.n
    if n <= initialization + horizon:
        return [trajectory]
    out = []
    start = 0
    while start + initialization < n:
        stop = min(start + initialization + horizon, n)
        out.append(Trajectory(trajectory.group, f"{trajectory.trajectory}-{len(out) + 1}",
                              {k: v[start:stop].copy() for k, v in trajectory.columns.items()}))
        start += horizon
    return out


def visible_trajectories(task: TaskSpec, *, whole: bool = False) -> dict[str, list[Trajectory]]:
    """Trajectories of the agent-visible data: ``train`` and, when present, ``val``.

    When the task declares ``evaluation.horizon``, every trajectory is cut into segments of that
    horizon (:func:`segments`); ``whole`` returns the uncut trajectories (the parameter-sensitivity
    diagnostic uses them, because it does not simulate).
    """
    out = {"train": split_table(task, read_table(task.data.train_path), "train")}
    if task.data.val_path is not None:
        out["val"] = split_table(task, read_table(task.data.val_path), "val")
    e = task.evaluation
    if e.horizon is not None and e.mode == "simulation" and not whole:
        out = {g: [s for tr in trs for s in segments(tr, e.horizon, e.initialization)] for g, trs in out.items()}
    return out


def sealed_trajectories(task: TaskSpec) -> list[Trajectory]:
    """The sealed test trajectories, one per test file, in declared order.

    Reads the sealed files through :func:`aspire_sysid.evaluate.sealed.load_test_trajectories`;
    an empty list means that the task has no test data, and no ranking is made.
    """
    out = []
    for tr in load_test_trajectories(task):
        cols = {name: np.asarray(tr.table.column(name), dtype=float) for name in task.column_names}
        out.append(Trajectory("test", tr.trajectory, cols))
    return out
