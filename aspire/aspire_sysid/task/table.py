"""Reading of the comma-separated data tables of a task.

A table is a comma-separated file with one header row of column names and one numeric row per
sample. The reader uses the standard library and NumPy only; it is shared by the task loader
(training and validation data) and by ``aspire_sysid.evaluate.sealed`` (test data).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


class TableError(ValueError):
    """A data table is malformed (header, row length or a non-numeric value)."""


@dataclass(frozen=True)
class Table:
    """A numeric data table: ``header`` names the columns of ``values`` (rows × columns)."""

    header: tuple[str, ...]
    values: np.ndarray

    @property
    def n_rows(self) -> int:
        """Number of samples."""
        return int(self.values.shape[0])

    def column(self, name: str) -> np.ndarray:
        """The values of column ``name`` (KeyError if absent)."""
        return self.values[:, self.header.index(name)]


def read_table(path: Path) -> Table:
    """Read a comma-separated table with a header row.

    Every value must parse as a finite or non-finite float; an empty table is an error.
    """
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise TableError(f"{path.name}: empty file")
    header = tuple(h.strip() for h in rows[0])
    if len(set(header)) != len(header):
        raise TableError(f"{path.name}: duplicate column names in the header {header}")
    body = [r for r in rows[1:] if r and any(cell.strip() for cell in r)]
    if not body:
        raise TableError(f"{path.name}: no data rows")
    values = np.empty((len(body), len(header)), dtype=float)
    for i, r in enumerate(body):
        if len(r) != len(header):
            raise TableError(f"{path.name}: row {i + 2} has {len(r)} values, header has {len(header)}")
        try:
            values[i] = [float(cell) for cell in r]
        except ValueError as exc:
            raise TableError(f"{path.name}: row {i + 2}: {exc}") from exc
    return Table(header=header, values=values)


def trajectory_blocks(ids: np.ndarray) -> list[tuple[float, slice]]:
    """Split a trajectory-identifier column into contiguous blocks.

    Returns ``(identifier, slice)`` per block in file order. Raises :class:`TableError` if an
    identifier occurs in two separate blocks, because trajectories are never joined.
    """
    blocks: list[tuple[float, slice]] = []
    start = 0
    for k in range(1, len(ids) + 1):
        if k == len(ids) or ids[k] != ids[start]:
            blocks.append((float(ids[start]), slice(start, k)))
            start = k
    seen = [b[0] for b in blocks]
    if len(set(seen)) != len(seen):
        raise TableError("a trajectory identifier occurs in two separate blocks of rows")
    return blocks
