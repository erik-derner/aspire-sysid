"""Matlab export of evaluated pools for the Matlab model-evaluation framework (the folder of the framework).

The Matlab files follow the ``[y, info]`` form of the ``srProvenance`` convention of the Matlab
framework. The exports identify exclusions, numerical failures and unresolved requirements, and
they contain the evaluation settings or a reference to the saved run record. The export folders
are for the user only and keep the original recording names, which are never shown to the agent.

**Layout** (the working folder that ``srEvalHP`` of the Matlab framework expects)::

    <out>/<task-id>/
        <train name>.mat, <val name>.mat, <test name>.mat ...   data sets
        splitData.m          training set and its validation set(s) (agent-visible data only)
        evaluationSets.m     validation and test sets with their roles, for srEvaluate
        startup.m            puts this folder and the framework on the path
        README.md            contents, conventions, differences to the ASPIRE evaluation
        HP/<setting>/<train name>/model01.m ...   one folder per run and pool version
        other_models/<setting>/modelNN.m          candidates the framework cannot simulate as written
        aspire_export.json   task digests, data files with digests, one entry per export call

A later export into the same task folder adds its settings and keeps the earlier ones in the README;
it is refused (:class:`ExportConflictError`) when the task digests or a data file differ from the
manifest.

``<setting>`` is ``run=<n>-pool=<k>`` (``srScanModels`` turns ``run`` and ``pool`` into numeric columns); ``<train name>`` is the original recording name of the training data
(``data.source_name.train``): the name itself when there is one, and the first name followed by
``_plus<m>`` when the training file joins ``m + 1`` recordings; the task identifier with
``_train`` when the task names none. The validation set is named the same way; each test
trajectory by its own recording name.

**Data sets.** One ``.mat`` file per data set with ``D`` (regressors first, target last; a cell
array with one segment per trajectory, so that ``srSimulate`` restarts at every trajectory),
``Ts``, ``inputInd``, ``varNames``, ``varNamesLong``, ``varRanges`` (one row per column of ``D``:
the declared range, widened to the values of that data set). Static task: the regressors are the
inputs, the target is the output, ``inputInd`` names every regressor and ``Ts`` is NaN (the
framework then uses the sample index). Continuous-time task: the regressors are the states in
their declared order and then the inputs, the target is the state-derivative column of the last
state. **Test data are included**: the export is for the user only (never shown to the agent),
it is written outside every working directory, and the test data allow the evaluation to be
reproduced in the Matlab framework. The README states
this and lists them in ``evaluationSets.m`` only, never in ``splitData.m``.

**Model files.** One M-file per evaluated candidate, numbered in the agent's order:
``function [y, info] = modelNN(x)``. ``x(:,k)`` is regressor ``k``. Fitted parameters are flat
assignments ``name = <value>;`` (the lines that ``srProvenance`` rewrites to read the parameter
vector); fixed parameters and given constants are written as numbers into the expressions (a
literal that is not named as fitted is structural for ``srProvenance`` and ``extrapolationRisk``);
a **tied** parameter of ASPIRE, determined by an equation over other parameters, is an assignment
``name = <equation>;`` after the fitted ones, so that the evaluator of ``srProvenance`` computes it
from the parameter vector. ``info.FittedParameters`` lists the fitted parameters in table order,
``info.FixedConstants`` the fixed parameters and given constants, ``info.TiedParameters`` the
ties that are the identity with a fitted parameter (``Occurrence`` shares the entry of
``Parameter``; srProvenance's field has no other meaning), and the extension
``info.TiedEquations`` every tie with its equation and value. Further ``info`` fields state the
label, task, run, pool version, record, exclusions, numerical failures, unresolved requirements
and the test score.

**State-space convention of the framework** (``srSimulate``): the regressors that are not inputs
form a chain of integrators (the derivative of state ``i`` is state ``i + 1``) and the model gives
the derivative of the last state. A continuous-time candidate is written to ``HP/`` when its
expression of every state but the last is the next state (for ``friction-driven``: ``dtheta =
omega``, the requirement R1); ``y`` is then the expression of the last state (``domega``). A
one-state candidate (``fermenter-pressure``: ``dp``) always fits the convention. A candidate whose
other state equations differ is written to ``other_models/`` with the note, because ``srSimulate``
would simulate a different model. ``srEvaluate`` compares the simulation of the first regressor
with the data, which is the ASPIRE output when the measurement equation is the first state (true
for both dynamic benchmark tasks; otherwise the README says so). Discrete-time and NARX tasks are
not exported to Matlab (the framework integrates continuous-time chains only).

**Verification.** Every M-file is re-verified before it is placed in ``HP/``: its statements are
evaluated in Python by the restricted translator :func:`aspire_sysid.export.printing.matlab_evaluate`
and compared with the harness's numerical form of the SymPy expression at the training rows and at
random points of the declared ranges. When GNU Octave is installed (``octave-cli``), the M-files
are also run in Octave on the same points (:mod:`aspire_sysid.export.octave`). A file that fails
the Python verification is written to ``other_models/`` with the reason.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import sympy as sp

from ..portable import portable_data, portable_text
from .. import __version__
from ..evaluate.sealed import sealed_dataset_records
from ..model.checks import Candidate
from ..task.schema import TaskSpec
from ..record.provenance import file_sha256
from ..task.table import read_table, trajectory_blocks
from .common import SEALED_GROUP, ExportSource, check_export_location, candidate_status, load_export_source, sample_arguments
from .printing import MATLAB_RESERVED, PIECEWISE_PREFIX, ascii_text, matlab_evaluate, matlab_statements, number_text
from .python_export import VERIFY_RTOL, _compare, reference_values

__all__ = [
    "PROVENANCE_SCHEMA_VERSION",
    "MatlabModel",
    "MatlabExportReport",
    "export_matlab",
    "mfile_text",
    "framework_layout",
    "dataset_names",
    "chain_ok",
    "EXPORT_MANIFEST",
    "ExportConflictError",
]

PROVENANCE_SCHEMA_VERSION = 1
"""``info.SchemaVersion`` of the ``srProvenance`` convention (``srProvenance.m`` of the Matlab framework)."""

MODELS_ROOT = "HP"
OTHER_ROOT = "other_models"


@dataclass
class MatlabModel:
    """One exported M-file."""

    label: str
    run_id: str
    setting: str
    file: str
    in_framework: bool
    note: str | None
    statements: list[str]
    verification: dict[str, Any] = field(default_factory=dict)
    octave: dict[str, Any] | None = None
    reference: Any = field(default=None, repr=False)


@dataclass
class MatlabExportReport:
    """What :func:`export_matlab` wrote, per task folder."""

    root: Path
    folders: dict[str, Path] = field(default_factory=dict)
    files: list[str] = field(default_factory=list)
    models: list[MatlabModel] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    octave: dict[str, Any] | None = None

    @property
    def verified(self) -> bool:
        """True when every M-file passed the Python re-verification (and Octave, where it ran). """
        return all(m.verification.get("passed") and (m.octave is None or m.octave.get("passed")) for m in self.models)


# ---------------------------------------------------------------------------------------------
# Naming and layout
# ---------------------------------------------------------------------------------------------


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_=+.-]", "_", name).strip(".") or "data"


def _joined_name(names: Sequence[str], fallback: str) -> str:
    names = [n for n in names if n]
    if not names:
        return _safe(fallback)
    if len(names) == 1:
        return _safe(names[0])
    return _safe(f"{names[0]}_plus{len(names) - 1}")


def dataset_names(task: TaskSpec) -> dict[str, Any]:
    """Names of the data sets of the export: ``train``, ``val`` (or ``None``) and the test names by
    trajectory, from the original recording names (module docstring). """
    train = _joined_name(task.data.source_names.get("train", ()), f"{task.id}_train")
    val = None
    if task.data.val_path is not None:
        val = _joined_name(task.data.source_names.get("val", ()), f"{task.id}_val")
    tests = {}
    taken = {train, val}
    for rec in sealed_dataset_records(task):
        n = _safe(rec.source_name) if rec.source_name else _safe(f"{task.id}_{rec.trajectory}")
        while n in taken:
            n = n + "_"
        taken.add(n)
        tests[rec.trajectory] = n
    return {"train": train, "val": val, "tests": tests}


def _setting(src: ExportSource) -> str:
    rid = re.sub(r"[^A-Za-z0-9_-]", "_", src.run_id)
    m = re.search(r"(\d+)$", rid)
    run = f"run={int(m.group(1))}" if m else rid.replace("=", "_")
    return f"{run}-pool={src.pool_version}"


def framework_layout(task: TaskSpec) -> dict[str, Any]:
    """Regressors, target, input indices and the form of the data sets for the Matlab framework.

    Returns ``{"form": "static" | "state-space", "regressors": [...], "target": name or None,
    "input_ind": [...], "note": text}``; raises ``ValueError`` for discrete-time and NARX tasks
    (module docstring).

    """
    if task.formulation == "static":
        regs = list(task.inputs)
        return {"form": "static", "regressors": regs, "target": task.output, "input_ind": list(range(1, len(regs) + 1)), "note": None}
    if task.formulation != "continuous":
        raise ValueError(f"the {task.formulation} formulation has no representation in the Matlab framework, which integrates continuous-time chains only")
    states = list(task.states)
    regs = states + list(task.inputs)
    target = next((c.name for c in task.columns if "state_derivative" in c.roles and c.derivative_of == states[-1]), None)
    note = None
    if target is None:
        note = f"the task has no sampled derivative of {states[-1]}: the target column of D is NaN, and the one-step metrics of srEvaluate are NaN"
    h = task.dynamics.measurement.strip()
    if h != states[0]:
        note = ((note + "; ") if note else "") + (
            f"the measurement equation is {h}, not the first state {states[0]}: srEvaluate's simulation error compares x(:,1), "
            "which is not the ASPIRE output"
        )
    return {"form": "state-space", "regressors": regs, "target": target,
            "input_ind": [regs.index(u) + 1 for u in task.inputs], "note": note}


def chain_ok(task: TaskSpec, c: Candidate) -> tuple[bool, str | None]:
    """Whether a continuous-time candidate fits the chain of integrators of ``srSimulate``.

    True when, for every state but the last, the resolved expression of its derivative with all
    parameter values inserted equals the next state (``sympy.expand`` of the difference is zero).

    """
    if task.formulation != "continuous":
        return True, None
    states = list(task.states)
    num = c.numeric_expressions()
    for s, nxt in zip(states[:-1], states[1:]):
        diff = sp.expand(num[f"d{s}"] - sp.Symbol(nxt, real=True))
        if diff != 0:
            return False, (
                f"d{s} = {c.expressions[f'd{s}']} is not {nxt}: the Matlab framework integrates a chain of integrators "
                f"(d{s} = {nxt}) and would simulate a different model"
            )
    return True, None


# ---------------------------------------------------------------------------------------------
# M-files
# ---------------------------------------------------------------------------------------------


def _matlab_names(c: Candidate, regressors: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Symbol → Matlab text (``x(:,k)``, parameter names, fixed values) and parameter → Matlab name."""
    names: dict[str, str] = {r: f"x(:,{i + 1})" for i, r in enumerate(regressors)}
    pnames: dict[str, str] = {}
    taken = set(regressors) | set(MATLAB_RESERVED)
    for p in c.parameters:
        if p.type == "fixed":
            v = number_text(c.values[p.name])
            names[p.name] = f"({v})" if v.startswith("-") else v
            continue
        n = p.name
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,62}", n) or n in taken or n.startswith(PIECEWISE_PREFIX):
            base = "p_" + re.sub(r"[^A-Za-z0-9_]", "_", n)
            n = base[:63] if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", base) else f"p{len(pnames) + 1}"
            while n in taken:
                n = n + "_"
        taken.add(n)
        pnames[p.name] = n
        names[p.name] = n
    for k, v in c.constants.items():
        t = number_text(v)
        names[k] = f"({t})" if t.startswith("-") else t
    return names, pnames


def _quote(text: Any) -> str:
    return "'" + ascii_text(text).replace("'", "''").replace("\n", " ") + "'"


def _cellstr(items: Sequence[Any]) -> str:
    return "{" + ", ".join(_quote(i) for i in items) + "}"


def _struct(fields: dict[str, list[str]]) -> str:
    """``struct('A', {...}, 'B', {...})`` with the given element texts (Matlab literals or names)."""
    return "struct(" + ", ".join(f"'{k}', {{{', '.join(v)}}}" for k, v in fields.items()) + ")"


def _comment(label: str, text: Any, width: int = 96) -> list[str]:
    body = " ".join(ascii_text(text).split())
    if not body:
        return []
    return textwrap.wrap(f"{label}: {body}" if label else body, width=width, initial_indent="% ", subsequent_indent="%     ",
                         break_long_words=True, break_on_hyphens=False)


def _unit(task: TaskSpec, name: str) -> str:
    try:
        return task.column(name).unit
    except KeyError:
        return "-"


def _yes_no(v: Any) -> str:
    return "not applicable" if v is None else ("yes" if v else "no")


def _failure_text(f: dict[str, Any]) -> str:
    t = f" (t = {f['time_s']:.6g} s)" if isinstance(f.get("time_s"), (int, float)) else ""
    var = f", {f['variable']}" if f.get("variable") else ""
    return f"{f.get('group')} trajectory {f.get('trajectory')}, sample {f.get('index')}{t}: {f.get('reason')}{var}"


def mfile_text(src: ExportSource, label: str, name: str, layout: dict[str, Any], note: str | None) -> tuple[str, list[str]]:
    """The M-file of candidate ``label`` as function ``name`` and its assignment statements.

    Module docstring (form of the file and of ``info``).
    """
    task = src.task
    c = src.candidate(label)
    regs = layout["regressors"]
    names, pnames = _matlab_names(c, regs)
    key = task.output if task.formulation == "static" else f"d{task.states[-1]}"
    fitted = [p for p in c.parameters if p.type == "fitted"]
    fixed = [p for p in c.parameters if p.type == "fixed"]
    tied = [p for p in c.parameters if p.type == "tied"]
    statements = [f"{pnames[p.name]} = {number_text(c.values[p.name])};" for p in fitted]
    counter = [0]
    for p in tied:
        statements += matlab_statements(c.tie_expressions[p.name], names, pnames[p.name], counter)
    y_stmts = matlab_statements(c.expressions[key], names, "y", counter)
    body = y_stmts[-1][len("y = "):-1]
    if not any(f"x(:,{i + 1})" in body for i in range(len(regs))) and not body.startswith(PIECEWISE_PREFIX):
        y_stmts[-1] = f"y = ({body}).*ones(size(x,1),1);"
    statements += y_stmts
    st = candidate_status(src, label)
    ref = src.record_reference()
    ev_settings = (src.evaluation or {}).get("settings") or {}

    L = [f"function [y, info] = {name}(x)"]
    L += _comment("", f"{name.upper()} ASPIRE candidate {label} of task {task.id}, pool version {src.pool_version}, run {src.run_id}.")
    L.append("%")
    L += _comment("", f"Generated by the harness of ASPIRE (aspire-sysid {__version__}) from the run record {ref['run_record']} "
                  f"(code revision {(ref.get('code_revision') or {}).get('commit')}); regenerate with: aspire export <run-dir> --matlab. "
                  "ASPIRE = the harness (software) and the agent (language model) that proposed this model. For the user only: the header "
                  "states results on sealed test data.")
    if src.interaction_text():
        L.append("%")
        L += _comment("", src.interaction_text())
    L.append("%")
    L.append("% Regressors (columns of x) and output y:")
    for i, r in enumerate(regs):
        col = task.column(r)
        role = "input" if r in task.inputs else f"state {task.states.index(r) + 1}" if r in task.states else "input"
        L += _comment("", f"  x(:,{i + 1}) = {r} [{col.unit}], {role}: {col.description}")
    if task.formulation == "static":
        L += _comment("", f"  y = {task.output} [{_unit(task, task.output)}], the model output: y = f(x; p)")
    else:
        L += _comment("", f"  y = d{task.states[-1]}/dt [{_unit(task, layout['target']) if layout['target'] else '-'}], the derivative of the last state "
                      "(the Matlab framework integrates it)")
    L.append("% Model equations (canonical form checked by the harness; parameter names as in the table):")
    for k in task.expression_keys:
        L += _comment("", f"  {k} = {c.expressions[k]}")
    if task.dynamics is not None:
        L += _comment("", f"  measurement (given by the task): y_meas = {task.dynamics.measurement}")
        if len(task.states) > 1:
            L += _comment("", "  the derivatives of the states before the last are supplied by srSimulate's chain of integrators")
    if note:
        L += _comment("NOTE", note)
    L.append("% Parameter table (name | value | unit | type | description):")
    for p in c.parameters:
        shown = pnames.get(p.name, p.name)
        extra = f" = {p.equation}" if p.type == "tied" else ""
        ren = f" (Matlab name {shown})" if shown != p.name and p.type != "fixed" else ""
        L += _comment("", f"  {p.name}{ren} | {number_text(c.values[p.name])} | {p.unit} | {p.type}{extra} | {p.description}")
    for k, v in c.constants.items():
        const = next((x for x in task.constants if x.name == k), None)
        L += _comment("", f"  {k} | {number_text(v)} | {const.unit if const else '-'} | given constant of the task | {const.source if const else '-'}")
    if fixed or c.constants:
        L.append("% Fixed parameters and given constants are written as numbers in the expressions (structural constants).")
    L.append("% Estimation record (as written by the agent):")
    for k, v in c.estimation.items():
        L += _comment(f"  {k}", v if not isinstance(v, list) else "; ".join(map(str, v)))
    L.append("% The agent's discussion:")
    for k in ("family", "interpretation", "origin", "limitations"):
        L += _comment(f"  {k}", c.discussion.get(k, ""))
    L.append("% Evaluation by the harness:")
    L += _comment("  settings", ", ".join(f"{k} {ev_settings.get(k)}" for k in ("mode", "initialization", "scoring", "integrator", "substeps", "input_hold")
                                           if ev_settings.get(k) is not None))
    for fl in ev_settings.get("failure_limits") or []:
        L += _comment("  failure limit", f"{fl['lower']} <= {fl['variable']} <= {fl['upper']} {fl['unit']}")
    L += _comment("  exclusions", ", ".join(st.get("exclusions") or []) or "none")
    if st.get("allowed_violations"):
        L += _comment("  violations allowed by the user", ", ".join(st["allowed_violations"]))
    L += _comment("  numerical failures", "; ".join(_failure_text(f) for f in st.get("numerical_failures") or []) or "none")
    L += _comment("  unresolved requirements", ", ".join(st.get("unresolved_requirements") or []) or "none")
    if st.get("score_S") is not None or st.get("eligible") is not None:
        L += _comment("  test score S (pooled test RMSE)", f"{st.get('score_S')} [{_unit(task, task.output)}], eligible: {_yes_no(st.get('eligible'))}, "
                      f"rank {st.get('rank')} in the {st.get('ranking_label') or 'oracle-based selection on test data'} "
                      f"({st.get('candidates_considered')} candidates considered, pool size {st.get('pool_size')})")
    for s in statements:
        L.append(s)
    L.append("if nargout > 1")
    L.append(f"    info.SchemaVersion = {PROVENANCE_SCHEMA_VERSION};")
    L.append("    info.FittedParameters = " + (_struct({"Name": [_quote(pnames[p.name]) for p in fitted], "Value": [pnames[p.name] for p in fitted]})
                                               if fitted else "struct('Name', {}, 'Value', {})") + ";")
    fixed_items = [(p.name, c.values[p.name]) for p in fixed] + list(c.constants.items())
    L.append("    info.FixedConstants = " + (_struct({"Name": [_quote(n) for n, _ in fixed_items], "Value": [number_text(v) for _, v in fixed_items]})
                                             if fixed_items else "struct('Name', {}, 'Value', {})") + ";")
    identity = [(p, str(c.tie_expressions[p.name])) for p in tied if str(c.tie_expressions[p.name]) in {q.name for q in fitted}]
    L.append("    info.TiedParameters = " + (_struct({"Occurrence": [_quote(pnames[p.name]) for p, _ in identity], "Parameter": [_quote(pnames[q]) for _, q in identity]})
                                             if identity else "struct('Occurrence', {}, 'Parameter', {})") + ";")
    L.append("    info.TiedEquations = " + (_struct({"Name": [_quote(pnames[p.name]) for p in tied], "Equation": [_quote(p.equation) for p in tied],
                                                     "Value": [pnames[p.name] for p in tied]})
                                            if tied else "struct('Name', {}, 'Equation', {}, 'Value', {})") + ";")
    L.append(f"    info.Label = {_quote(label)};")
    L.append(f"    info.TaskId = {_quote(task.id)};")
    L.append(f"    info.RunId = {_quote(src.run_id)};")
    L.append(f"    info.PoolVersion = {src.pool_version};")
    L.append(f"    info.Record = {_quote(ref['run_record'])};")
    L.append(f"    info.Regressors = {_cellstr(regs)};")
    L.append(f"    info.Output = {_quote(key)};")
    L.append(f"    info.Expressions = {_struct({'Key': [_quote(k) for k in task.expression_keys], 'Expression': [_quote(str(c.expressions[k])) for k in task.expression_keys]})};")
    L.append(f"    info.InFramework = {'false' if note else 'true'};")
    L.append(f"    info.Exclusions = {_cellstr(st.get('exclusions') or [])};")
    L.append(f"    info.UnresolvedRequirements = {_cellstr(st.get('unresolved_requirements') or [])};")
    L.append(f"    info.NumericalFailures = {_cellstr([_failure_text(f) for f in st.get('numerical_failures') or []])};")
    s_val = st.get("score_S")
    L.append(f"    info.TestScore = {number_text(s_val) if isinstance(s_val, (int, float)) else 'NaN'};")
    L.append(f"    info.OracleRank = {st.get('rank') if isinstance(st.get('rank'), int) else 'NaN'};")
    L.append("end")
    L.append("end")
    return "\n".join(L) + "\n", statements


def _verify_statements(statements: list[str], reference: np.ndarray, points: np.ndarray) -> dict[str, Any]:
    try:
        env = matlab_evaluate(statements, points)
    except Exception as exc:  # noqa: BLE001 - a translation failure is a verification failure
        return {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    got = np.broadcast_to(np.asarray(env["y"], dtype=float), (len(points),))
    res = _compare(got, reference)
    res["method"] = (f"generated statements evaluated by the restricted Matlab translator at {len(points)} points (training rows and random "
                     f"points in the declared ranges) and compared with the harness's numerical form of the SymPy expression, relative "
                     f"tolerance {VERIFY_RTOL:g}")
    return res


# ---------------------------------------------------------------------------------------------
# Data sets and support files
# ---------------------------------------------------------------------------------------------


def _var_names_long(task: TaskSpec, cols: list[str | None]) -> list[str]:
    out = []
    for n in cols:
        if n is None:
            out.append("target (not available)")
            continue
        col = task.column(n)
        out.append(ascii_text(f"{col.description} ({col.unit})"))
    return out


def _matrix(task: TaskSpec, columns: dict[str, np.ndarray], layout: dict[str, Any]) -> np.ndarray:
    n = len(next(iter(columns.values())))
    cols = [np.asarray(columns[r], dtype=float) for r in layout["regressors"]]
    t = layout["target"]
    cols.append(np.asarray(columns[t], dtype=float) if t is not None else np.full(n, np.nan))
    return np.column_stack(cols)


def _write_mat(path: Path, task: TaskSpec, layout: dict[str, Any], segments: list[np.ndarray]) -> None:
    from scipy.io import savemat

    names = layout["regressors"] + [layout["target"]]
    allrows = np.vstack(segments)
    ranges = np.zeros((len(names), 2))
    for i, n in enumerate(names):
        vals = allrows[:, i]
        vals = vals[np.isfinite(vals)]
        declared = None
        if n is not None:
            declared = task.column(n).range
        lo, hi = (declared if declared is not None else (float(vals.min()), float(vals.max())) if vals.size else (-1.0, 1.0))
        if vals.size:
            lo, hi = min(lo, float(vals.min())), max(hi, float(vals.max()))
        ranges[i] = (lo, hi)
    if layout["form"] == "static" or len(segments) == 1:
        D: Any = segments[0] if len(segments) == 1 else np.vstack(segments)
    else:
        D = np.empty((len(segments), 1), dtype=object)
        for i, s in enumerate(segments):
            D[i, 0] = s
    ts = task.dynamics.sampling_period if task.dynamics is not None else float("nan")
    savemat(
        path,
        {
            "D": D,
            "Ts": float(ts),
            "inputInd": np.asarray(layout["input_ind"], dtype=float).reshape(1, -1),
            "varNames": np.array([n if n is not None else "target" for n in names], dtype=object).reshape(1, -1),
            "varNamesLong": np.array(_var_names_long(task, names), dtype=object).reshape(1, -1),
            "varRanges": ranges,
        },
        do_compression=True,
    )


def _segments(task: TaskSpec, path: Path, layout: dict[str, Any]) -> list[np.ndarray]:
    table = read_table(path)
    cols = {n: table.column(n) for n in task.column_names}
    tc = task.data.trajectory_column
    if layout["form"] == "static" or not tc or tc not in table.header:
        return [_matrix(task, cols, layout)]
    return [_matrix(task, {k: v[sl] for k, v in cols.items()}, layout) for _, sl in trajectory_blocks(table.column(tc))]


def _framework_path(out_dir: Path) -> str | None:
    """Path of the Matlab framework for ``startup.m``: relative when the export lies in the repository;
    ``None`` when it lies elsewhere, so that ``startup.m`` reads the environment variable
    ``SR_FRAMEWORK`` and no path of this computer is written."""
    from .octave import framework_folder

    fw = framework_folder(out_dir)
    if fw is None:
        return None
    repo = fw.parent.parent
    out = out_dir.resolve()
    if out == repo or repo in out.parents:
        return os.path.relpath(fw, out).replace("\\", "/")
    return None


def _write_support(folder: Path, task: TaskSpec, names: dict[str, Any]) -> list[str]:
    val = [names["val"]] if names["val"] else []
    split = (
        "function [trainDataFiles, valDataFiles] = splitData(ind, pairedFlag) %#ok<INUSD>\n"
        "% Training data set and its validation data set(s) of this ASPIRE export (generated by the harness).\n"
        "% The validation set is the agent-visible validation file; the sealed test sets are listed in\n"
        "% evaluationSets.m, never here. The arguments are accepted for srSplitDataVal and ignored.\n"
        f"trainDataFiles = {{'{names['train']}'}};\n"
        f"valDataFiles = {{{', '.join(repr(v).replace(chr(34), chr(39)) for v in val)}}};\n"
        "end\n"
    )
    (folder / "splitData.m").write_text(split, encoding="ascii", newline="\n")
    tests = list(names["tests"].values())
    roles = ["'validation'"] * len(val) + [f"'{SEALED_GROUP}'"] * len(tests)
    sets = [f"'{v}'" for v in val + tests]
    evs = (
        "function sets = evaluationSets()\n"
        "% Data sets with their roles for srEvaluate (generated by the harness of ASPIRE):\n"
        "%   M = srModelProps(srScanModels('HP')); R = srEvaluate(M, evaluationSets(), 'IgnoreOffset', false);\n"
        "% The sets with role 'test' are the sealed test trajectories of the task (for the user only; never give them to an agent).\n"
        + (f"sets = struct('name', {{{', '.join(sets)}}}, 'role', {{{', '.join(roles)}}});\n" if sets else "sets = struct('name', {}, 'role', {});\n")
        + "end\n"
    )
    (folder / "evaluationSets.m").write_text(evs, encoding="ascii", newline="\n")
    fw = _framework_path(folder)
    fw_line = (f"srFramework = fullfile(srWorkDir, '{fw}');   % folder of the Matlab framework\n" if fw and not Path(fw).is_absolute() else
               "srFramework = getenv('SR_FRAMEWORK');   % set SR_FRAMEWORK to the folder of the Matlab framework\n")
    startup = (
        "% Put this ASPIRE export and the Matlab framework on the path (generated by the harness).\n"
        "%   cd <this folder>; startup\n"
        "srWorkDir = fileparts(mfilename('fullpath'));\n"
        "addpath(srWorkDir);\n"
        + fw_line
        + "if exist(fullfile(srFramework, 'srEvalHP.m'), 'file')\n"
        "    addpath(srFramework);\n"
        "else\n"
        "    warning('startup:framework', 'the Matlab framework not found at %s; add it to the path by hand.', srFramework);\n"
        "end\n"
        "clear srWorkDir srFramework\n"
    )
    (folder / "startup.m").write_text(startup, encoding="ascii", newline="\n")
    return ["splitData.m", "evaluationSets.m", "startup.m"]


EXPORT_MANIFEST = "aspire_export.json"
"""Manifest of a task folder of the Matlab export: the task digests, the data files with their
SHA-256 digests, and one entry per export call (runs, models per setting, verification)."""


class ExportConflictError(ValueError):
    """A task folder of the Matlab export holds data of another task specification, or files that
    its manifest does not describe (records are never overwritten or mixed)."""


def _verification_text(octave_state: str, octave: dict[str, Any] | None) -> str:
    if octave is None:
        return {"not installed": "GNU Octave was not installed; the M-files were verified with the Python translator only.",
                "switched off": "GNU Octave was switched off for this export (--no-octave); the M-files were verified with the "
                                "Python translator only."}.get(octave_state, "GNU Octave did not run.")
    text = (f"{octave.get('version') or 'GNU Octave'} ran every M-file on the verification points"
            + (f"; srProvenance: {octave.get('provenance_summary')}" if octave.get("provenance_summary") else "") + ".")
    fc = octave.get("framework_check")
    if fc and fc.get("ran"):
        steps = "; ".join(f"`{k}`: {v.split('  ')[0]}" for k, v in fc["steps"].items())
        comp = [c for c in fc["comparisons"] if c.get("passed") is not None]
        worst = max((c.get("relative_difference", 0.0) for c in comp), default=0.0)
        text += (
            f" the Matlab framework under Octave (with the compatibility functions `string` and `strlength` on the path; the "
            f"framework files unchanged). Steps: {steps}. For {len(comp)} pairs of model and data set, `srLoadData` and "
            f"`srSimulate(model, 0, data)` (static data: the model output) reproduce the ASPIRE errors on the scored samples "
            f"{'within' if fc.get('passed') else 'NOT within'} the relative tolerance {fc['tolerance']:g} (largest relative "
            f"difference {worst:.3g}); `srSimulate` received each data set without its `form` field, whose string comparison "
            "Octave cannot evaluate."
        )
    return text


def _model_entry(m: MatlabModel) -> dict[str, Any]:
    v = "passed" if m.verification.get("passed") else f"FAILED ({m.verification.get('error') or 'values differ'})"
    o = "not run" if m.octave is None else ("passed" if m.octave.get("passed") else f"FAILED ({m.octave.get('error') or 'values differ'})")
    return {"file": m.file, "label": m.label, "run_id": m.run_id, "setting": m.setting, "in_framework": m.in_framework,
            "note": m.note, "translator": v, "octave": o}


def _readme(folder: Path, task: TaskSpec, names: dict[str, Any], layout: dict[str, Any], manifest: dict[str, Any]) -> None:
    train_rec = list(task.data.source_names.get("train", ()))
    val_rec = list(task.data.source_names.get("val", ()))
    rows = [f"| `{names['train']}.mat` | training data (agent-visible) | {', '.join(train_rec) or 'not stated'} |"]
    if names["val"]:
        rows.append(f"| `{names['val']}.mat` | validation data (agent-visible, offered) | {', '.join(val_rec) or 'not stated'} |")
    for traj, n in names["tests"].items():
        rows.append(f"| `{n}.mat` | sealed test trajectory {traj} | {n} |")
    runs: list[str] = []
    sections: list[str] = []
    verif: list[str] = []
    skipped: list[str] = []
    for k, ex in enumerate(manifest["exports"], start=1):
        runs += ex["runs"]
        for setting in ex["settings"]:
            models = [m for m in ex["models"] if m["setting"] == setting]
            sections.append(f"### `{setting}` (export {k}, {ex['exported_at']})\n\n"
                            "| File | Label | Run | Python translator | Octave | Note |\n|---|---|---|---|---|---|\n"
                            + "\n".join(f"| `{m['file']}` | {m['label']} | {m['run_id']} | {m['translator']} | {m['octave']} | {m['note'] or ''} |"
                                        for m in models))
        verif.append(f"- Export {k} ({', '.join(f'`{x}`' for x in ex['settings'])}): {ex['verification']}")
        skipped += ex["skipped"]
    dyn = task.dynamics
    warnings = []
    if dyn is not None and task.formulation == "continuous" and dyn.substeps != 1:
        warnings.append(f"The task integrates with {dyn.substeps} Runge-Kutta substeps per sampling period: pass `'Nsub', {dyn.substeps}` to "
                        "`srEvalHP` and `srEvaluate`, whose default is 1.")
    if dyn is not None and dyn.input_hold != "zero_order":
        warnings.append(f"The task holds the inputs by `{dyn.input_hold}`; `srSimulate` holds them constant over each sample interval "
                        "(zero-order hold), so its simulation differs from the ASPIRE evaluation.")
    dynamic_text = "" if layout["form"] == "static" else (
        "Dynamic models: `srSimulate` treats the regressors that are not inputs as a chain of integrators\n"
        "(the derivative of state i is state i + 1) and integrates the model output as the derivative of the\n"
        "last state. A candidate is placed in `HP/` only when its other state equations are exactly this\n"
        f"chain; otherwise it is written to `{OTHER_ROOT}/` with the reason. `srEvaluate` computes the simulation\n"
        "error of the first regressor.\n"
    )
    nsub = f", 'Nsub', {dyn.substeps}" if dyn is not None and task.formulation == "continuous" and dyn.substeps != 1 else ""
    text = f"""# ASPIRE export of task `{task.id}` for the Matlab model-evaluation framework

Generated by the harness of ASPIRE (aspire-sysid {__version__}). ASPIRE consists of the harness
(the software that ran the agent, checked and evaluated its models) and the agent (the language
model that proposed them). This folder follows the layout that `srEvalHP` expects
(`matlab-framework/README.md`). It is for the user only: it contains the sealed test data of
the task and results on them. Never place it in, or copy it into, a working directory of an agent.
`{EXPORT_MANIFEST}` records the digests of the task specification and of the data files; a later
export into this folder is refused when they differ.

## Use

```matlab
cd <this folder>
startup                                          % this folder and the framework on the path
[M, R, T] = srEvalHP('HP', 'IgnoreOffset', false{nsub});   % training and validation sets (splitData)
R = srEvaluate(M, evaluationSets(), 'IgnoreOffset', false{nsub});   % validation and sealed test sets
```

`'IgnoreOffset', false` is needed to simulate the model as ASPIRE did: with the default `true`,
`srSimulate` subtracts the model output at x = 0 from the derivative.
{chr(10).join('**Warning.** ' + w for w in warnings)}

## Data sets

| File | Content | Original recording(s) |
|---|---|---|
{chr(10).join(rows)}

Each `.mat` file holds `D` (regressors {', '.join(f'`{r}`' for r in layout['regressors'])}, then the target
`{layout['target']}`), `Ts`, `inputInd` = {layout['input_ind']}, `varNames`, `varNamesLong` and `varRanges`
(the declared range of each column, widened to the values of that data set). `D` is a cell array with
one segment per trajectory where the file holds several, so that `srSimulate` restarts at every
trajectory, as the ASPIRE evaluation does. Form: {layout['form']}.{(' ' + layout['note']) if layout['note'] else ''}
The test sets are included because the authors used them as development data
and so that the ASPIRE test results can be reproduced here; they appear in `evaluationSets.m`
only, never in `splitData.m`.

## Runs

The folders `HP/run=<n>-pool=<k>` give `srScanModels` the numeric columns `run` and `pool` (the pool version).

{chr(10).join(runs)}

## Model files

{(chr(10) + chr(10)).join(sections)}

Each model is `function [y, info] = modelNN(x)`, numbered in the agent's order of the pool. The header
states the label, the regressor mapping `x(:,k)`, the equations, the parameter table (name, value,
unit, status fitted / fixed / tied, source, initial value), the estimation record, the origin, the
evaluation settings, the exclusions, numerical failures, unresolved requirements and the test score
`S` (pooled test RMSE; the rank is an oracle-based selection on test
data, stated with the number of candidates considered and the pool size).

Parameter provenance (`srProvenance`, schema {PROVENANCE_SCHEMA_VERSION}): fitted parameters are the flat
assignments `name = value;` and are listed in `info.FittedParameters`; fixed parameters and given
constants are numbers in the expressions and are listed in `info.FixedConstants`. A tied parameter
of ASPIRE is determined by an equation over other parameters; it is the assignment
`name = <equation>;` after the fitted ones, so that the evaluator that `srProvenance` builds
computes it from the parameter vector. `info.TiedParameters` lists only the ties that are the
identity with a fitted parameter (`Occurrence` shares the entry of `Parameter`, the meaning of that
field in `srProvenance`); `info.TiedEquations` lists every tie with its equation and value.
A `Piecewise` expression is computed in auxiliary variables `{PIECEWISE_PREFIX}<n>`: each starts as NaN (no
condition holds) and receives, from the last pair to the first, the value of each pair on the rows
where its condition holds, so that the first true pair wins, as in ASPIRE.

{dynamic_text}
## Differences between this framework and the ASPIRE evaluation

1. ASPIRE scores the samples after the initialization samples of each trajectory
   (scoring rule `{task.evaluation.scoring}`, {task.evaluation.initialization} initialization sample(s)); `srEvaluate` computes
   the error over all samples, including the initial sample, where the error is zero by construction.
2. ASPIRE stops a simulation at the failure limits of the task and at non-finite values and keeps the
   error before the failure as a diagnostic; `srSimulate` stops at ten times the range of each state
   in the data (`DivergeFactor`).
3. `srEvaluate` pools validation data sets as sqrt(sum SSE / sum N), which is the pooled RMSE of ASPIRE on its
   own sample sets.
4. Matlab's `min` and `max` ignore NaN arguments, where ASPIRE returns NaN; `log`, `sqrt`, `asin`,
   `acos` and powers of negative numbers return complex values where ASPIRE gives NaN. These cases
   concern only arguments outside the domain on which the model is real and finite.

## Verification

Every M-file was evaluated by the harness's restricted Matlab translator and compared with the
harness's numerical form of the SymPy expression at the training rows and at random points of the
declared ranges (relative tolerance {VERIFY_RTOL:g}).

{chr(10).join(verif)}

The check of this folder in Matlab is open.

## Candidates outside `HP/` or not evaluated

{chr(10).join('- ' + x for x in skipped) or '- none'}
"""
    (folder / "README.md").write_text(portable_text(text), encoding="utf-8", newline="\n")


def _load_manifest(folder: Path, src: ExportSource) -> dict[str, Any]:
    """The manifest of an existing task folder, checked against the task of ``src`` (or a new one)."""
    path = folder / EXPORT_MANIFEST
    digests = {"task_spec_sha256": src.record["task"]["spec_sha256"], "task_sealed_sha256": src.record["task"]["sealed_sha256"]}
    if not path.is_file():
        if folder.is_dir() and any(folder.iterdir()):
            raise ExportConflictError(f"{folder} is not empty and has no {EXPORT_MANIFEST}: it was not written by this exporter")
        return {"format_version": 1, "task_id": src.task.id, **digests, "data_files": {}, "exports": []}
    man = json.loads(path.read_text(encoding="utf-8"))
    diff = [k for k, v in digests.items() if man.get(k) != v]
    if man.get("task_id") != src.task.id or diff:
        raise ExportConflictError(
            f"{folder} holds the export of another task specification (differing: {diff or ['task_id']}); "
            "export into another folder"
        )
    for name, digest in man.get("data_files", {}).items():
        f = folder / name
        if not f.is_file() or file_sha256(f) != digest:
            raise ExportConflictError(f"the data file {f} differs from the one recorded in {EXPORT_MANIFEST}")
    return man


# ---------------------------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------------------------


def _expected_errors(srcs: Sequence[ExportSource], models: Sequence[MatlabModel], names: dict[str, Any]) -> list[dict[str, Any]]:
    """Per data set of the export, the ASPIRE errors of each exported model (pooled RMSE (9) over
    the scored samples), from the stored evaluation reports."""
    by_run = {s.run_id: s for s in srcs}
    sets: dict[str, dict[str, Any]] = {names["train"]: {}}
    if names["val"]:
        sets[names["val"]] = {}
    for n in names["tests"].values():
        sets[n] = {}
    for m in models:
        ce = by_run[m.run_id].evaluation_of(m.label) or {}
        vis = ce.get("visible") or {}
        for group, dname in (("train", names["train"]), ("val", names["val"])):
            ge = vis.get(group)
            if dname and ge and ge.get("finished"):
                sets[dname][m.file] = {"rmse": ge.get("pooled_rmse"), "samples": ge.get("scored_samples")}
        sealed = ((ce.get("sealed") or {}).get(SEALED_GROUP) or {})
        for tr in sealed.get("trajectories", []) if isinstance(sealed, dict) else []:
            dname = names["tests"].get(tr.get("trajectory"))
            if dname and tr.get("finished") and tr.get("measures"):
                sets[dname][m.file] = {"rmse": tr["measures"].get("rmse"), "samples": tr.get("required_samples")}
    return [{"name": k, "expected": v} for k, v in sets.items()]


def export_matlab(
    run_dirs: Sequence[str | Path],
    out_dir: str | Path,
    *,
    pool_version: int | None = None,
    task_dir: str | Path | None = None,
    octave: bool | None = None,
    framework: bool = True,
) -> MatlabExportReport:
    """Export the evaluated pools of one or more runs into working folders for the Matlab framework.

    See the module docstring. Runs of the same task share one folder ``<out>/<task-id>``
    (the data sets are written once; one ``HP/<setting>`` folder per run and pool version).
    ``octave`` runs the M-files in GNU Octave: ``None`` when ``octave-cli`` is installed, ``True``
    requires it, ``False`` skips it; with ``framework``, the Matlab framework is also run on the folder
    under Octave and its errors are compared with the ASPIRE evaluation
    (:func:`aspire_sysid.export.octave.run_framework_in_octave`). Existing model folders are never
    overwritten.
    """
    from .octave import octave_available, run_framework_in_octave, run_models_in_octave

    out = Path(out_dir)
    check_export_location(out, list(run_dirs))
    report = MatlabExportReport(out)
    sources = [load_export_source(r, pool_version, task_dir=task_dir) for r in run_dirs]
    by_task: dict[str, list[ExportSource]] = {}
    for s in sources:
        by_task.setdefault(s.task.id, []).append(s)
    use_octave = octave_available() if octave is None else octave
    if octave and not octave_available():
        raise RuntimeError("GNU Octave (octave-cli) is not installed")
    for task_id, srcs in sorted(by_task.items()):
        task = srcs[0].task
        folder = out / task_id
        try:
            layout = framework_layout(task)
        except ValueError as exc:
            report.skipped.append(f"{task_id}: {exc}")
            continue
        for other in srcs[1:]:
            if other.record["task"]["spec_sha256"] != srcs[0].record["task"]["spec_sha256"]:
                raise ExportConflictError(f"the runs {srcs[0].run_id} and {other.run_id} used different specifications of task {task_id}")
        manifest = _load_manifest(folder, srcs[0])
        folder.mkdir(parents=True, exist_ok=True)
        report.folders[task_id] = folder
        names = dataset_names(task)
        for key, path in (("train", task.data.train_path), ("val", task.data.val_path)):
            if path is None or names[key] is None:
                continue
            target = folder / f"{names[key]}.mat"
            if target.name not in manifest["data_files"]:
                _write_mat(target, task, layout, _segments(task, path, layout))
                manifest["data_files"][target.name] = file_sha256(target)
                report.files.append(f"{task_id}/{target.name}")
        for rec in sealed_dataset_records(task, with_values=True):
            target = folder / f"{names['tests'][rec.trajectory]}.mat"
            if target.name not in manifest["data_files"]:
                _write_mat(target, task, layout, [_matrix(task, rec.columns, layout)])
                manifest["data_files"][target.name] = file_sha256(target)
                report.files.append(f"{task_id}/{target.name}")
        report.files += [f"{task_id}/{f}" for f in _write_support(folder, task, names)]
        points = sample_arguments(task)
        task_models: list[MatlabModel] = []
        skipped: list[str] = []
        for s in srcs:
            setting = _setting(s)
            hp_dir = folder / MODELS_ROOT / setting / names["train"]
            other_dir = folder / OTHER_ROOT / setting
            if hp_dir.exists() or other_dir.exists():
                raise FileExistsError(f"{hp_dir} exists; an export is never overwritten")
            labels = s.evaluated_labels
            width = max(2, len(str(len(labels))))
            for i, label in enumerate(labels, start=1):
                name = f"model{i:0{width}d}"
                c = s.candidate(label)
                ok, note = chain_ok(task, c)
                text, statements = mfile_text(s, label, name, layout, None if ok else note)
                key = task.output if task.formulation == "static" else f"d{task.states[-1]}"
                ref = reference_values(c, key, points)
                ver = _verify_statements(statements, ref, points)
                if not ver["passed"]:
                    ok, note = False, f"the numerical re-verification failed: {ver.get('error') or 'values differ'}"
                    text, statements = mfile_text(s, label, name, layout, note)
                dest = (hp_dir if ok else other_dir) / f"{name}.m"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding="ascii", newline="\n")
                rel = dest.relative_to(folder).as_posix()
                report.files.append(f"{task_id}/{rel}")
                m = MatlabModel(label, s.run_id, setting, rel, ok, note, statements, ver, reference=ref)
                task_models.append(m)
                if not ok:
                    skipped.append(f"{rel} ({label}, run {s.run_id}) is outside `HP/`: {note}")
            for lab in s.report.order:
                if lab not in labels:
                    res = s.report.candidates.get(lab)
                    why = "outside the pool limit" if lab in s.report.outside_limit else "failed the file and expression checks"
                    if res is None or res.file is None:
                        why = "no candidate file"
                    skipped.append(f"{lab} (run {s.run_id}, pool version {s.pool_version}): {why}; not evaluated")
        oct_result = None
        if use_octave and task_models:
            oct_result = run_models_in_octave(folder, task_models, points)
            for m in task_models:
                m.octave = oct_result["models"].get(m.file)
            in_hp = [m for m in task_models if m.in_framework]
            if framework and in_hp:
                oct_result["framework_check"] = run_framework_in_octave(
                    folder, in_hp, _expected_errors(srcs, in_hp, names), form=layout["form"], initialization=task.evaluation.initialization
                )
            report.octave = {**(report.octave or {}), task_id: {k: v for k, v in oct_result.items() if k != "models"}}
        report.models += task_models
        octave_state = "ran" if oct_result is not None else ("switched off" if octave is False else "not installed")
        manifest["exports"].append({
            "exported_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "harness_version": __version__,
            "settings": [_setting(s) for s in srcs],
            "runs": [f"- `{_setting(s)}`: run `{s.run_id}`, pool version {s.pool_version}, model "
                     f"`{s.record.get('model', {}).get('id')}`, record `{s.record_reference()['run_record']}`"
                     + (f". {s.interaction_text()}" if s.interaction_text() else "") for s in srcs],
            "models": [_model_entry(m) for m in task_models],
            "skipped": skipped,
            "octave": octave_state,
            "verification": _verification_text(octave_state, oct_result),
        })
        manifest = portable_data(manifest)
        (folder / EXPORT_MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        _readme(folder, task, names, layout, manifest)
        report.files += [f"{task_id}/README.md", f"{task_id}/{EXPORT_MANIFEST}"]
        report.skipped += skipped
    return report
