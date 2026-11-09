"""Applies the formal requirements of the described task friction-driven to the recommended models
of the blind task task-jdhj, after renaming the neutral names of the blind task to the names of
the described task (``tasks/blind_mapping.yaml``: y = theta, x1 = omega, x2 = u, dy = dtheta,
dx1 = domega).

Plain code, no language model. The blind task states no requirement, and the agent did not know
the conditions; no blind candidate is excluded by them. The result shows whether the models that
the agent delivered without the description and without the requirements would satisfy the
requirements that the described task states (R1, R2 and R3). The harness's own verification is used
(``aspire_sysid.evaluate.constraints.assess_requirements``); parameter values are those of the
delivered model files. No test data are read.

    .venv/Scripts/python.exe experiments/paper/blind_requirements.py

Writes ``experiments/paper/blind_requirements.json``.
"""
from __future__ import annotations

import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
NAMES = {"y": "theta", "x1": "omega", "x2": "u"}
KEYS = {"dy": "dtheta", "dx1": "domega"}


def rename(expression: str, parameter_names: set[str]) -> str:
    def repl(match: re.Match) -> str:
        word = match.group(0)
        return word if word in parameter_names else NAMES.get(word, word)

    return re.sub(r"[A-Za-z_][A-Za-z0-9_]*", repl, expression)


def main() -> None:
    import sympy as sp
    from aspire_sysid.evaluate.compiled import CompiledModel, parse_task_text
    from aspire_sysid.evaluate.constraints import assess_requirements
    from aspire_sysid.task import load_task

    task = load_task(REPO / "tasks" / "friction-driven")
    exp_dir = REPO / "experiments" / "paper-friction-driven-blind"
    agg = json.loads((exp_dir / "aggregate.json").read_text(encoding="utf-8"))
    out = {}
    for run in agg["runs"]:
        label = run["recommended_label"]
        model = json.loads((exp_dir / "runs" / run["run_id"] / "pools" / "v1" / "models" / f"{label}.json").read_text(encoding="utf-8"))
        values = {p["name"]: p["value"] for p in model["parameters"] if p.get("value") is not None}
        tied = {p["name"]: p["equation"] for p in model["parameters"] if p.get("type") == "tied" and p.get("equation")}
        names = set(values) | set(tied)
        clash = names & (set(NAMES.values()) | set(NAMES))
        if clash:
            raise SystemExit(f"{run['run_id']}: parameter names {sorted(clash)} clash with variable names")
        exprs = {}
        args = ["theta", "omega", "u"]
        subs = {}
        for name, value in values.items():
            subs[sp.Symbol(name, real=True)] = sp.Float(value)
        for key, text in model["expressions"].items():
            parsed = parse_task_text(task, rename(text, names), args + sorted(names))
            for name, equation in tied.items():  # tied parameters through their equations
                parsed = parsed.subs(sp.Symbol(name, real=True), parse_task_text(task, equation, sorted(names)))
            exprs[KEYS[key]] = parsed.subs(subs)
        compiled = CompiledModel.from_expressions(task, label, exprs)
        res = {r.id: r.outcome for r in assess_requirements(task, compiled)}
        out[run["run_id"]] = {"label": label, "outcomes": res,
                              "violated": [k for k, v in res.items() if v == "counterexample"]}
        print(run["run_id"], label, "violated:", ", ".join(out[run["run_id"]]["violated"]) or "none")
    path = HERE / "blind_requirements.json"
    path.write_text(json.dumps({"written_by": "experiments/paper/blind_requirements.py",
                                "conditions_of": "tasks/friction-driven", "models_of": "experiments/paper-friction-driven-blind",
                                "runs": out}, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("written:", path.name)


if __name__ == "__main__":
    main()
