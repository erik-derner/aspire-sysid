"""The public view of a task: the part of the specification that may be shown to the agent.

 The view contains every agent-visible field of the schema. Of the
``data`` field it contains the noise and preprocessing statements, and in addition the facts the
brief must state about the provisioned files: their neutral names in the
working directory, the trajectory column, and the sample and trajectory counts. It never
contains a recording name (``source_name``), a path of the task store, the sealed test entries
or the reference. The brief is rendered from this view only.
"""

from __future__ import annotations

from typing import Any

from .provision import WORKSPACE_TRAIN, WORKSPACE_VAL, workspace_context_name
from .schema import TaskSpec
from .table import read_table, trajectory_blocks


def _source(s) -> dict[str, Any]:
    d = {"stated_by": s.stated_by, "date": s.date}
    if s.note:
        d["note"] = s.note
    return d


def _file_facts(task: TaskSpec, path, name: str) -> dict[str, Any]:
    t = read_table(path)
    n_traj = 1
    lengths = [t.n_rows]
    if task.data.trajectory_column is not None:
        blocks = trajectory_blocks(t.column(task.data.trajectory_column))
        n_traj = len(blocks)
        lengths = [b[1].stop - b[1].start for b in blocks]
    return {"file": name, "samples": t.n_rows, "trajectories": n_traj, "trajectory_lengths": lengths}


def public_view(task: TaskSpec) -> dict[str, Any]:
    """Return the agent-visible part of ``task`` as plain data (lists, dicts, numbers, strings).

    The result is JSON- and YAML-serializable and
    contains no sealed information and no recording name.
    """
    view: dict[str, Any] = {
        "schema_version": task.schema_version,
        "id": task.id,
        "title": task.title,
        "formulation": task.formulation,
        "description": task.description,
        "intended_use": task.intended_use,
        "columns": [
            {
                "name": c.name,
                "symbol": c.symbol,
                "roles": list(c.roles),
                "unit": c.unit,
                "description": c.description,
                "range": list(c.range) if c.range is not None else None,
                **({"derivative_of": c.derivative_of} if c.derivative_of else {}),
            }
            for c in task.columns
        ],
        "roles_defaulted": task.roles_defaulted,
        "expression_keys": list(task.expression_keys),
        "arguments": list(task.argument_names),
    }
    if task.dynamics is not None:
        d = task.dynamics
        dyn: dict[str, Any] = {
            "sampling_period": d.sampling_period,
            "states": list(d.states),
            "inputs": list(d.inputs),
            "measurement": d.measurement,
            "input_hold": d.input_hold,
        }
        if task.formulation == "continuous":
            dyn["integrator"] = d.integrator
            dyn["substeps"] = d.substeps
        if d.delays:
            dyn["delays"] = [{"name": x.name, "variable": x.variable, "lag": x.lag} for x in d.delays]
            dyn["shift_equations"] = dict(d.shift_equations)
        view["dynamics"] = dyn
    e = task.evaluation
    view["evaluation"] = {
        "mode": e.mode,
        "initialization": e.initialization,
        "scoring": e.scoring,
        "failure_limits": [
            {"variable": f.variable, "lower": f.lower, "upper": f.upper, "unit": f.unit, "justification": f.justification}
            for f in e.failure_limits
        ],
        "time_limit_s": e.time_limit_s,
        "symbolic_time_limit_s": e.symbolic_time_limit_s,
    }
    data: dict[str, Any] = {
        "noise": task.data.noise,
        "preprocessing": task.data.preprocessing,
        "trajectory_column": task.data.trajectory_column,
        "train": _file_facts(task, task.data.train_path, WORKSPACE_TRAIN),
    }
    if task.data.val_path is not None:
        data["val"] = _file_facts(task, task.data.val_path, WORKSPACE_VAL)
    view["data"] = data
    view["constants"] = [
        {"name": c.name, "value": c.value, "unit": c.unit, "source": c.source} for c in task.constants
    ]
    view["functions"] = list(task.functions)
    view["added_functions"] = [
        {"name": a.name, "arguments": list(a.arguments), "definition": a.definition, "domain": a.domain}
        for a in task.added_functions
    ]
    reqs = []
    for r in task.requirements:
        item: dict[str, Any] = {
            "id": r.id,
            "type": r.type,
            "target": r.target,
            "variables": list(r.variables),
            "domain": _plain(r.domain),
            "tolerance": {"value": r.tolerance.value, "unit": r.tolerance.unit},
            "verification": r.verification,
            "exclude_on_violation": r.exclude_on_violation,
            "source": _source(r.source),
        }
        item.update(_plain(r.params))
        if r.statement:
            item["statement"] = r.statement
        if r.exception is not None:
            item["exception"] = _source(r.exception)
        reqs.append(item)
    view["requirements"] = reqs
    view["requirements_nl"] = [{"id": r.id, "text": r.text, "source": _source(r.source)} for r in task.requirements_nl]
    view["literature"] = list(task.literature)
    view["context"] = [{"file": workspace_context_name(c.path), "note": c.note} for c in task.context]
    view["discussion_questions"] = [{"id": q.id, "text": q.text} for q in task.discussion_questions]
    view["pool_cap"] = task.pool_cap
    b = task.budget
    view["budget"] = {
        "round": _limits(b.round),
        "session": _limits(b.session),
        "analysis_exchange": _limits(b.analysis_exchange) if b.analysis_exchange else None,
    }
    return view


def _limits(lim) -> dict[str, Any]:
    return {"turns": lim.turns, "seconds": lim.seconds, "usd": lim.usd}


def _plain(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    return x
