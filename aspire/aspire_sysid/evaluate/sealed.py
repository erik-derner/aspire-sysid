"""Access to the sealed part of a task: test trajectories and reference expression.

The sealed test data and reference expression are withheld from the agent by construction. This
module is the only place in the harness that resolves and opens the files of ``test/`` and
``reference/`` of a task folder; the task loader records their declared locations without
opening them. Evaluation proper reads the sealed data through
:func:`load_test_trajectories` and :func:`load_reference`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp
import yaml

from ..task.expr import ExpressionError, parse_task_expression
from ..task.loader import resolve_inside
from ..task.schema import SEALED_FOLDERS, TaskSpec
from ..task.table import Table, TableError, read_table, trajectory_blocks

TEST_DIR, REFERENCE_DIR = SEALED_FOLDERS
"""Folders of the sealed test files and of the sealed reference expression."""

REFERENCE_FORMAT_VERSION = 1
"""Version of the reference file format: ``{format_version: 1, expressions: {key: text}}``."""


class SealedDataError(ValueError):
    """A sealed file is missing, lies outside its folder or is malformed."""


@dataclass(frozen=True)
class SealedTrajectory:
    """One sealed test trajectory: identifier, recording name, table, digest."""

    trajectory: str
    source_name: str | None
    table: Table
    sha256: str
    path: Path


@dataclass(frozen=True)
class Reference:
    """The sealed reference expression, keyed by the task's expression keys."""

    expressions: dict[str, str]
    parsed: dict[str, sp.Expr]
    domain: dict[str, Any]
    sha256: str
    path: Path


def _in_folder(task: TaskSpec, rel: str, folder: str) -> Path:
    path, err = resolve_inside(task.task_dir, rel)
    if err:
        raise SealedDataError(err)
    try:
        path.relative_to((task.task_dir / folder).resolve())
    except ValueError:
        raise SealedDataError(f"path {rel!r} is not inside the folder {folder}/") from None
    return path


def sealed_test_paths(task: TaskSpec) -> list[Path]:
    """Resolved paths of the sealed test files, in declared order.

    Raises :class:`SealedDataError` if a file is missing, outside ``test/`` or outside the task
    folder (symbolic links followed).
    """
    return [_in_folder(task, e._file, TEST_DIR) for e in task.sealed.test]


def reference_file_path(task: TaskSpec) -> Path | None:
    """Resolved path of the sealed reference file, or ``None`` without a reference."""
    if task.sealed.reference is None:
        return None
    return _in_folder(task, task.sealed.reference._file, REFERENCE_DIR)


def load_test_trajectories(task: TaskSpec) -> list[SealedTrajectory]:
    """Read every sealed test trajectory; one file is one trajectory.

    The header must equal the task's column names (no trajectory column); values must be
    finite. Raises :class:`SealedDataError`.
    """
    out = []
    for entry, path in zip(task.sealed.test, sealed_test_paths(task)):
        try:
            table = read_table(path)
        except TableError as exc:
            raise SealedDataError(f"test trajectory {entry.trajectory}: {exc}") from exc
        if table.header != task.column_names:
            raise SealedDataError(
                f"test trajectory {entry.trajectory}: header {list(table.header)} differs from the columns {list(task.column_names)}"
            )
        if not np.all(np.isfinite(table.values)):
            raise SealedDataError(f"test trajectory {entry.trajectory}: non-finite values")
        out.append(
            SealedTrajectory(
                trajectory=entry.trajectory,
                source_name=entry.source_name,
                table=table,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                path=path,
            )
        )
    return out


def load_reference(task: TaskSpec) -> Reference | None:
    """Read and parse the sealed reference expression, or ``None``.

    The file is YAML with ``format_version: 1`` and ``expressions``, a mapping from every
    required expression key of the task to an expression over the task's argument names and
    constants. Raises :class:`SealedDataError`.
    """
    path = reference_file_path(task)
    if path is None:
        return None
    blob = path.read_bytes()
    try:
        raw = yaml.safe_load(blob.decode("utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise SealedDataError(f"reference: not valid YAML: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("format_version") != REFERENCE_FORMAT_VERSION:
        raise SealedDataError(f"reference: expected a mapping with format_version {REFERENCE_FORMAT_VERSION}")
    exprs = raw.get("expressions")
    if not isinstance(exprs, dict) or set(exprs) != set(task.expression_keys):
        raise SealedDataError(f"reference: 'expressions' must have exactly the keys {list(task.expression_keys)}")
    names = list(task.argument_names) + list(task.constant_names)
    parsed = {}
    for key, text in exprs.items():
        try:
            parsed[key] = parse_task_expression(str(text), names, task.functions)
        except ExpressionError as exc:
            raise SealedDataError(f"reference expression {key!r}: {exc}") from exc
    return Reference(
        expressions={k: str(v) for k, v in exprs.items()},
        parsed=parsed,
        domain=task.sealed.reference.domain,
        sha256=hashlib.sha256(blob).hexdigest(),
        path=path,
    )


@dataclass(frozen=True)
class SealedDatasetRecord:
    """User-facing facts of one sealed test trajectory for the records and exports.

    ``assignment`` is the data use (``"test"``); ``declared_file`` the location declared in
    ``task.yaml`` (relative to the task folder); ``columns`` maps every task column to its
    samples, and is filled only when the caller asks for the values (the Matlab export, which is
    user-facing and never reaches the agent). 
    """

    trajectory: str
    source_name: str | None
    declared_file: str
    sha256: str
    samples: int
    assignment: str = TEST_DIR
    columns: dict[str, np.ndarray] | None = None


def sealed_dataset_records(task: TaskSpec, *, with_values: bool = False) -> list[SealedDatasetRecord]:
    """The sealed test trajectories as user-facing records.

    For every dataset, the experiment record preserves its source and version,
    trajectory identifiers, sampling period, sample counts and assignment to training,
    validation or test use. This is the only way in which the record and export modules learn
    about the sealed files: they receive the digest, the sample count, the recording name and,
    with ``with_values``, the values, but never a resolved path. Their results
    are user-facing and are never written into a working directory.
    """
    out = []
    for entry, tr in zip(task.sealed.test, load_test_trajectories(task)):
        cols = None
        if with_values:
            cols = {name: np.asarray(tr.table.column(name), dtype=float) for name in task.column_names}
        out.append(
            SealedDatasetRecord(
                trajectory=tr.trajectory,
                source_name=tr.source_name,
                declared_file=entry._file,
                sha256=tr.sha256,
                samples=tr.table.n_rows,
                columns=cols,
            )
        )
    return out


def sealed_reference_record(task: TaskSpec) -> dict[str, Any] | None:
    """User-facing facts of the sealed reference expression, or ``None``.

    Returns the declared location, the SHA-256 digest and the domain, not the expression, so that a
    record that cites it does not repeat the reference text.
    """
    ref = load_reference(task)
    if ref is None:
        return None
    return {"declared_file": task.sealed.reference._file, "sha256": ref.sha256, "domain": ref.domain}


def argument_columns(task: TaskSpec, table: Table) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Values of every argument name on the rows of ``table`` and the mask of usable rows.

    Delayed variables of a NARX task are built within each trajectory
    only (never across a boundary); rows without the required history are masked out.
    """
    n = table.n_rows
    cols = {name: table.column(name) for name in task.column_names if name in table.header}
    mask = np.ones(n, dtype=bool)
    delays = task.dynamics.delays if task.dynamics is not None else ()
    if delays:
        tc = task.data.trajectory_column
        blocks = trajectory_blocks(table.column(tc)) if tc and tc in table.header else [(0.0, slice(0, n))]
        for d in delays:
            arr = np.full(n, np.nan)
            src = table.column(d.variable)
            for _, sl in blocks:
                seg = src[sl]
                shifted = np.full(len(seg), np.nan)
                shifted[d.lag :] = seg[: len(seg) - d.lag]
                arr[sl] = shifted
            cols[d.name] = arr
            mask &= np.isfinite(arr)
    for c in task.constants:
        cols[c.name] = np.full(n, c.value)
    return cols, mask


def evaluate_expression(expr: sp.Expr, values: dict[str, np.ndarray], n: int) -> np.ndarray:
    """Evaluate a parsed task expression element-wise on ``values`` in real floating point.

    Non-real or non-finite values: a non-real intermediate result, such as the
    square root or logarithm of a negative number, yields NaN.
    """
    syms = sorted(expr.free_symbols, key=str)
    f = sp.lambdify(syms, expr, modules="numpy")
    with np.errstate(all="ignore"):
        try:
            out = np.asarray(f(*[values[str(s)] for s in syms]), dtype=float)
        except TypeError:  # a complex result cannot be converted to float
            out = np.full(n, np.nan)
    return np.broadcast_to(out, (n,)).copy()


def validate_sealed(task: TaskSpec) -> list[str]:
    """Check the sealed part of ``task``; return the list of errors (empty when valid).

    Every test file lies in ``test/`` inside the task
    folder, has the task's columns, finite values and more samples than the initialization;
    the reference file lies in ``reference/``, provides every expression key, and evaluates to
    real, finite values on every usable training sample.
    """
    errors: list[str] = []
    try:
        trajectories = load_test_trajectories(task)
    except SealedDataError as exc:
        errors.append(f"test: {exc}")
        trajectories = []
    for tr in trajectories:
        if len(task.evaluation.scoring_indices(tr.table.n_rows)) == 0:
            errors.append(f"test trajectory {tr.trajectory}: no sample in the scoring interval")
    try:
        ref = load_reference(task)
    except SealedDataError as exc:
        errors.append(str(exc))
        ref = None
    if ref is not None:
        train = read_table(task.data.train_path)
        values, mask = argument_columns(task, train)
        for key, expr in ref.parsed.items():
            out = evaluate_expression(expr, values, train.n_rows)
            bad = ~np.isfinite(out) & mask
            if np.any(bad):
                first = int(np.argmax(bad))
                errors.append(
                    f"reference expression {key!r} is not real and finite on the training data "
                    f"({int(bad.sum())} sample(s), first at row {first + 1})"
                )
    return errors
