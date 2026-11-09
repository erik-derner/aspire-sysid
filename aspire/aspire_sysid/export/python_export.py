"""Python export of an evaluated pool: one standalone module that needs NumPy only.

The harness exports each evaluated pool as Python files with the equations, the parameter
values, the origin and estimation history of those values, the variable definitions and any
known shift or measurement equations; the files identify exclusions, numerical failures and
unresolved requirements and contain the evaluation settings or a reference to the saved run
record.

The generated module ``<task>_pool_v<k>.py`` contains

* ``RECORD``: the reference to the run record (run identifier, file, pool version, digests of the
  evaluation report and of the task specification, code revision);
* ``TASK``, ``VARIABLES`` (name, symbol, roles, unit, description of every column),
  ``ARGUMENTS`` (the arguments of every function, in order), ``EXPRESSION_KEYS`` and
  ``KNOWN_EQUATIONS`` (the measurement equation ``h`` and the shift equations, given by the task,
  never searched);
* ``EVALUATION_SETTINGS``: the settings of the evaluation (mode, initialization, scoring,
  integrator, substeps, input hold, failure limits, tolerances), copied from the report;
* ``CANDIDATES``: per evaluated candidate, the canonical expressions and the agent's text, the
  parameter table (name, value, unit, type fitted / fixed / tied, description, tie
  equation), the resolved tie equations, the estimation record, the four discussion sections, the
  predecessor, and the status from the evaluation report: exclusions, violations allowed by the
  user, numerical failures, unresolved requirements, and the test score with the label of the
  oracle-based selection;
* ``RECOMMENDATION``: the agent's recommendation with the harness's notes;
* one function per candidate, for example ``M01(theta, omega, u)``, returning a dictionary with
  one NumPy array per expression key, and ``MODELS`` / :func:`evaluate` to call them by label;
* ``VERIFICATION``: the result of the numerical re-verification at export time.

The functions follow the numerical semantics of the harness (``numpy.errstate(all="ignore")``,
first-true ``Piecewise`` via ``numpy.select``, NaN-propagating ``minimum``/``maximum``); see
:mod:`aspire_sysid.export.printing`. The export is **re-verified numerically**: the written module
is imported, every function is evaluated at the training rows and at random points of the declared
ranges (:func:`aspire_sysid.export.common.sample_arguments`), and the values are compared with
the harness's own numerical form of the canonical SymPy expression
(:meth:`aspire_sysid.model.Candidate.numeric_function`), with relative tolerance
:data:`VERIFY_RTOL`; NaN must occur at the same points.
"""

from __future__ import annotations

import importlib.util
import json
import keyword
import pprint
import re
import sys
import textwrap
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .. import __version__
from ..model.checks import Candidate
from .common import ExportSource, candidate_status, check_export_location, load_export_source, sample_arguments
from .printing import numpy_code

__all__ = ["VERIFY_RTOL", "PythonExportResult", "python_module_text", "export_python", "verify_python_module", "module_file_name"]

VERIFY_RTOL = 1e-9
"""Relative tolerance of the numerical re-verification (absolute: ``VERIFY_RTOL`` times the largest
magnitude of the compared values, at least ``VERIFY_RTOL``)."""

_RESERVED = {"numpy", "_piecewise", "_shape", "_out", "MODELS", "evaluate"}
_MODULE_NAMES = {"RECORD", "TASK", "VARIABLES", "ARGUMENTS", "EXPRESSION_KEYS", "KNOWN_EQUATIONS", "EVALUATION_SETTINGS", "CANDIDATES",
                 "RECOMMENDATION", "VERIFICATION"}


@dataclass
class PythonExportResult:
    """The written module and its verification."""

    path: Path
    labels: list[str]
    verification: dict[str, Any] = field(default_factory=dict)

    @property
    def verified(self) -> bool:
        """True when every candidate passed the numerical re-verification. """
        return bool(self.verification) and all(v.get("passed") for v in self.verification.values())


def module_file_name(task_id: str, pool_version: int) -> str:
    """File name of the module of one pool: ``<task id with _>_pool_v<k>.py``. """
    return re.sub(r"[^A-Za-z0-9_]", "_", task_id) + f"_pool_v{int(pool_version)}.py"


def _func_name(label: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", label)
    if not name.isidentifier() or keyword.iskeyword(name) or name in _RESERVED or name in _MODULE_NAMES:
        name = f"candidate_{name}"
    return name


def _local(name: str) -> str:
    return f"p_{name}" if name in _RESERVED or keyword.iskeyword(name) else name


def _param_rows(c: Candidate) -> list[dict[str, Any]]:
    rows = []
    for p in c.parameters:
        row = {"name": p.name, "value": float(c.values[p.name]), "recorded_value": float(p.value), "unit": p.unit,
               "type": p.type, "description": p.description}
        if p.equation is not None:
            row["equation"] = p.equation
        rows.append(row)
    return rows


def _function_text(src: ExportSource, label: str, c: Candidate) -> str:
    task = src.task
    args = list(c.arguments)
    names = {a: a for a in args}
    for p in c.parameters:
        names[p.name] = _local(p.name)
    for k in c.constants:
        names[k] = _local(k)
    fname = _func_name(label)
    lines = [f"def {fname}({', '.join(args)}):"]
    keys = list(task.expression_keys)
    doc = (
        f'    """Candidate {label}: returns {{{", ".join(repr(k) for k in keys)}}} as NumPy arrays of the broadcast shape of the '
        "arguments. Arguments in the units of VARIABLES."
        '"""'
    )
    lines.append(doc)
    for a in args:
        lines.append(f"    {a} = numpy.asarray({a}, dtype=float)")
    lines.append(f"    _shape = numpy.broadcast_shapes({', '.join(f'numpy.shape({a})' for a in args)}{',' if len(args) == 1 else ''})")
    for name, value in c.constants.items():
        lines.append(f"    {names[name]} = numpy.float64({float(value)!r})  # given constant of the task")
    for p in c.parameters:
        if p.type != "tied":
            lines.append(f"    {names[p.name]} = numpy.float64({float(c.values[p.name])!r})  # {p.type}, unit {p.unit}")
    lines.append("    with numpy.errstate(all=\"ignore\"):")
    for p in c.parameters:
        if p.type == "tied":
            eq = " ".join(str(p.equation).split())
            lines.append(f"        {names[p.name]} = {numpy_code(c.tie_expressions[p.name], names)}  # tied: {p.name} = {eq}")
    for k in keys:
        lines.append(f"        _{k} = {numpy_code(c.expressions[k], names)}")
    lines.append("    return {" + ", ".join(f"{k!r}: numpy.broadcast_to(numpy.asarray(_{k}, dtype=float), _shape).copy()" for k in keys) + "}")
    return "\n".join(lines)


def _plain(obj: Any) -> Any:
    return json.loads(json.dumps(obj, default=str))


def python_module_text(src: ExportSource, verification: dict[str, Any] | None = None) -> str:
    """The text of the Python module of the evaluated pool of ``src`` (module docstring). """
    task = src.task
    labels = src.evaluated_labels
    ev = src.evaluation or {}
    variables = [
        {"name": col.name, "symbol": col.symbol, "roles": list(col.roles), "unit": col.unit, "description": col.description,
         "range": list(col.range) if col.range is not None else None}
        for col in task.columns
    ]
    dyn = task.dynamics
    known = {
        "measurement": None if dyn is None else dyn.measurement,
        "measurement_note": None if dyn is None else "y[k] = h(x[k], u[k]), given by the task; never searched",
        "shift_equations": {} if dyn is None else dict(dyn.shift_equations),
        "delays": [] if dyn is None else [{"name": d.name, "variable": d.variable, "lag": d.lag} for d in dyn.delays],
    }
    cands: dict[str, Any] = {}
    for label in labels:
        c = src.candidate(label)
        pos = src.report.candidates[label].position
        cands[label] = {
            "function": _func_name(label),
            "position": pos,
            "expressions": {k: str(e) for k, e in c.expressions.items()},
            "expressions_as_written_by_the_agent": dict(c.expression_texts),
            "parameters": _param_rows(c),
            "tie_equations_resolved": {k: str(e) for k, e in c.tie_expressions.items()},
            "given_constants": {k: float(v) for k, v in c.constants.items()},
            "estimation": _plain(c.estimation),
            "discussion": {k: c.discussion.get(k) for k in ("family", "interpretation", "origin", "limitations")},
            "predecessor": c.predecessor,
            "status": _plain(candidate_status(src, label)),
        }
    head = {
        "RECORD": _plain(src.record_reference()),
        "TASK": {"id": task.id, "title": task.title, "formulation": task.formulation,
                 "sampling_period_s": None if dyn is None else dyn.sampling_period,
                 "states": list(task.states), "inputs": list(task.inputs), "output": task.output,
                 },
        "VARIABLES": variables,
        "ARGUMENTS": list(task.argument_names),
        "EXPRESSION_KEYS": list(task.expression_keys),
        "KNOWN_EQUATIONS": known,
        "EVALUATION_SETTINGS": _plain(ev.get("settings")),
        "CANDIDATES": cands,
        "RECOMMENDATION": _plain(ev.get("recommendation")),
        "VERIFICATION": _plain(verification) if verification is not None else None,
    }
    doc = [
        f'r"""Evaluated candidate pool {src.pool_version} of task {task.id}, run {src.run_id}.',
        "",
        f"Generated by the harness of ASPIRE (aspire-sysid {__version__}) from the run record",
        f"{src.record_reference()['run_record']}; regenerate with `aspire export <run-dir> --python`.",
        *([*textwrap.wrap(src.interaction_text(), 100), ""] if src.interaction_text() else []),
        "ASPIRE consists of the harness (the software that ran, checked and evaluated the models) and the agent",
        "(the language model that proposed them). User-facing: CANDIDATES[...]['status'] holds results on sealed test",
        "data; never give this file to an agent.",
        "",
        "Contents: RECORD (reference to the run record), TASK, VARIABLES (name, symbol, roles, unit, description),",
        "ARGUMENTS, EXPRESSION_KEYS, KNOWN_EQUATIONS (measurement and shift equations given by the task),",
        "EVALUATION_SETTINGS, CANDIDATES (expressions, parameter table with status fitted/fixed/tied, source and",
        "initial value, estimation record, origin, exclusions, numerical failures, unresolved requirements),",
        "RECOMMENDATION, VERIFICATION, and one function per candidate. Requires NumPy only.",
        "",
        "Expression keys: the output name for a static task (y = f(u; p, c)); d<state> for a",
        "continuous-time task (dx/dt = g_c(x, u; p, c)); <state>_next for a discrete-time task; <output>_next for a",
        "NARX task. Usage: `M = evaluate('M01', **{name: values for name in ARGUMENTS})` returns one array per key.",
        '"""',
    ]
    out = ["\n".join(doc), "", "import numpy", ""]
    for name, value in head.items():
        out.append(f"{name} = {pprint.pformat(value, width=110, sort_dicts=True)}")
        out.append("")
    out += [
        "",
        "def _piecewise(conditions, values):",
        '    """Value of the first pair whose condition holds, NaN where none holds (harness semantics)."""',
        "    conds = [numpy.asarray(c, dtype=bool) for c in conditions]",
        "    vals = [numpy.asarray(v, dtype=float) for v in values]",
        "    shape = numpy.broadcast_shapes(*[c.shape for c in conds], *[v.shape for v in vals])",
        "    return numpy.select([numpy.broadcast_to(c, shape) for c in conds], [numpy.broadcast_to(v, shape) for v in vals], default=numpy.nan)",
        "",
    ]
    for label in labels:
        out.append("")
        out.append(_function_text(src, label, src.candidate(label)))
        out.append("")
    out.append("")
    out.append("MODELS = {" + ", ".join(f"{lab!r}: {_func_name(lab)}" for lab in labels) + "}")
    out += [
        "",
        "",
        "def evaluate(label, **arguments):",
        '    """Evaluate candidate ``label`` at the given argument values (names of ARGUMENTS)."""',
        "    return MODELS[label](**{name: arguments[name] for name in ARGUMENTS})",
        "",
    ]
    return "\n".join(out)


def _import(path: Path) -> Any:
    name = f"aspire_export_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    before = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # no __pycache__ folder in the export
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = before
        sys.modules.pop(name, None)
    return mod


def _compare(got: np.ndarray, want: np.ndarray) -> dict[str, Any]:
    got = np.asarray(got, dtype=float)
    want = np.asarray(want, dtype=float)
    finite = np.isfinite(want) & np.isfinite(got)
    same_nonfinite = np.array_equal(np.isnan(got), np.isnan(want)) and np.array_equal(np.isposinf(got), np.isposinf(want)) and np.array_equal(np.isneginf(got), np.isneginf(want))
    scale = float(np.max(np.abs(want[finite]))) if finite.any() else 1.0
    atol = VERIFY_RTOL * max(1.0, scale)
    diff = np.abs(got[finite] - want[finite])
    ok = bool(same_nonfinite and np.all(diff <= atol + VERIFY_RTOL * np.abs(want[finite])))
    return {"passed": ok, "points": int(len(want)), "finite_points": int(finite.sum()),
            "max_abs_difference": float(diff.max()) if diff.size else 0.0, "nonfinite_pattern_equal": bool(same_nonfinite)}


def reference_values(c: Candidate, key: str, points: np.ndarray) -> np.ndarray:
    """Values of expression ``key`` of ``c`` at ``points`` with the harness's numerical semantics. """
    f = c.numeric_function(key)
    return np.array([float(f(*row)) for row in points], dtype=float)


def verify_python_module(path: str | Path, src: ExportSource) -> dict[str, Any]:
    """Import the written module and compare every function with the SymPy expressions (module docstring). """
    mod = _import(Path(path))
    pts = sample_arguments(src.task)
    names = list(src.task.argument_names)
    out: dict[str, Any] = {}
    for label in src.evaluated_labels:
        c = src.candidate(label)
        got = mod.evaluate(label, **{n: pts[:, i] for i, n in enumerate(names)})
        per_key = {k: _compare(got[k], reference_values(c, k, pts)) for k in src.task.expression_keys}
        out[label] = {"passed": all(v["passed"] for v in per_key.values()), "keys": per_key,
                      "method": f"module imported and evaluated at {len(pts)} points (training rows and random points in the declared ranges); "
                                f"compared with the harness's numerical form of the canonical SymPy expressions, relative tolerance {VERIFY_RTOL:g}"}
    return out


def export_python(run_dir: str | Path, out_dir: str | Path | None = None, *, pool_version: int | None = None,
                  task_dir: str | Path | None = None) -> PythonExportResult:
    """Write and verify the Python module of an evaluated pool (module docstring).

    ``out_dir`` defaults to ``<run-dir>/export/python``; a folder inside, overlapping or containing a
    working directory is refused (:func:`aspire_sysid.export.common.check_export_location`). An
    existing module is never overwritten
    (the record is retained without overwriting earlier results).
    """
    src = load_export_source(run_dir, pool_version, task_dir=task_dir)
    out = Path(out_dir) if out_dir is not None else Path(run_dir) / "export" / "python"
    check_export_location(out, [run_dir])
    out.mkdir(parents=True, exist_ok=True)
    path = out / module_file_name(src.task.id, src.pool_version)
    if path.exists():
        raise FileExistsError(f"{path} exists; exports are not overwritten")
    tmp = out / f".{path.name}.unverified.py"
    tmp.write_text(python_module_text(src), encoding="utf-8", newline="\n")
    try:
        verification = verify_python_module(tmp, src)
    finally:
        tmp.unlink(missing_ok=True)
    path.write_text(python_module_text(src, verification), encoding="utf-8", newline="\n")
    _import(path)  # the final text imports
    return PythonExportResult(path, src.evaluated_labels, verification)

