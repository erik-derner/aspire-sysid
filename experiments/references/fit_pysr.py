"""Reference models found by symbolic regression with PySR.

One call fits one reference model: one task, one setting, one seed. PySR searches a closed-form
expression for every fitting target that the task offers, on the training data only:

``turtlebot``
    the next states ``x``, ``y`` and ``phi`` as functions of the present states and commands, on
    the one-step transitions in which the logged heading does not wrap (three searches);
``fermenter-pressure``
    the supplied derivative column ``dp`` as a function of ``p``, ``valve`` and ``flow``;
``friction-driven``
    the supplied derivative column ``domega`` as a function of ``theta``, ``omega`` and ``u``;
    ``dtheta`` is written as ``omega``, which the task prescribes (requirement R1).

Settings:

``default``
    ``PySRRegressor`` with the default settings of the package; the equation of each target is
    the one that the package selects (``model_selection="best"``).
``matched``
    Two changes that bring the tool closer to what the agent is given: the unary operators
    ``sin cos tanh exp log sqrt abs sign`` are added (functions that the task permits), and the
    equation of each target is the member of the Pareto front of the search with the smallest
    root mean squared error of the simulated output on the training data, computed as the
    harness computes it. For a task with several targets the choice is made target by target,
    starting from the equations that the package selects, until no choice changes.

In both settings the seed is passed as ``random_state`` with ``deterministic=True`` and
``parallelism="serial"``, so that a call can be repeated exactly. With ``--threads`` the search
uses multithreading instead and the seed no longer determines the result.

Run with the Python environment that holds PySR (PySR 1.5.10 with Julia)::

    <pysr-python> experiments/references/fit_pysr.py <task> <default|matched> <seed>
    <pysr-python> experiments/references/fit_pysr.py <task> <default|matched> --pool
    aspire evaluate tasks/<task> experiments/references/<task>/pysr-<setting>/models \
        --out experiments/references/<task>/pysr-<setting>/evaluation

The script reads only the training data of the task. It never reads the test data.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
import time

import numpy as np
import sympy as sp

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

SCRIPT = "experiments/references/fit_pysr.py"
MATCHED_UNARY = ["sin", "cos", "tanh", "exp", "log", "sqrt", "abs", "sign"]
RECORDED = ["niterations", "populations", "population_size", "ncycles_per_iteration", "maxsize",
            "maxdepth", "binary_operators", "unary_operators", "model_selection", "elementwise_loss",
            "parsimony", "random_state", "deterministic", "parallelism", "batching", "precision"]


def label_of(setting: str, seed: int) -> str:
    return f"ReferencePysr{setting.capitalize()}S{seed}"


def folder_of(task: str, setting: str) -> pathlib.Path:
    return common.HERE / task / f"pysr-{setting}"


def targets(task: str):
    """Variable names, regressor matrix, and per expression key the target vector (or None for a
    key that the task prescribes), with the number of rows left out."""
    spec = common.TASKS[task]
    names = spec["states"] + spec["inputs"]
    trajectories = common.load(task)
    if task == "turtlebot":
        rows, nexts, omitted = [], [], 0
        for t in trajectories:
            table = np.column_stack([t[n] for n in names])
            keep = np.abs(np.diff(t["phi"])) < np.pi  # the logged heading does not wrap
            omitted += int((~keep).sum())
            rows.append(table[:-1][keep])
            nexts.append(table[1:, :3][keep])
        x, y = np.vstack(rows), np.vstack(nexts)
        return names, x, {f"{s}_next": y[:, i] for i, s in enumerate(spec["states"])}, omitted
    x = np.vstack([np.column_stack([t[n] for n in names]) for t in trajectories])
    out = {}
    for s in spec["states"]:
        column = spec["derivative"].get(s)
        out[f"d{s}"] = np.concatenate([t[column] for t in trajectories]) if column else None
    return names, x, out, 0


def to_expression(expr: sp.Expr, names: list[str], prefix: str):
    """The expression text over the column names and the parameter rows of its constants.

    Every non-integer number of the equation becomes a named parameter of type ``fitted``.
    """
    variables = {sp.Symbol(f"x{i}"): sp.Symbol(n) for i, n in enumerate(names)}
    expr = sp.sympify(expr).xreplace(variables)
    floats = sorted(expr.atoms(sp.Float), key=lambda f: str(f))
    mapping, rows = {}, []
    for i, f in enumerate(floats, 1):
        name = f"{prefix}{i}"
        mapping[f] = sp.Symbol(name)
        rows.append({"name": name, "value": float(f), "unit": "not assigned", "type": "fitted",
                     "description": "Constant of the equation found by the search, optimized by "
                                    "the package together with the structure; its unit follows "
                                    "from its position in the expression and was not derived."})
    text = sp.sstr(expr.xreplace(mapping))
    return text, rows


def fit_target(key: str, x: np.ndarray, y: np.ndarray, setting: str, seed: int, raw: pathlib.Path, threads: bool):
    from pysr import PySRRegressor

    options = dict(random_state=seed, deterministic=True, parallelism="serial")
    if threads:
        options = dict(random_state=seed, deterministic=False, parallelism="multithreading")
    if setting == "matched":
        options["unary_operators"] = list(MATCHED_UNARY)
    # the files of the package (hall of fame, checkpoint) go to a temporary folder; the front is
    # saved as a table in ``raw``
    model = PySRRegressor(progress=False, verbosity=0, output_directory=tempfile.mkdtemp(prefix="pysr-"),
                          run_id=key, **options)
    start = time.time()
    model.fit(x, y)
    elapsed = time.time() - start
    front = model.equations_
    best = int(model.get_best().name)
    params = {k: v for k, v in model.get_params().items() if k in RECORDED}
    print(f"  {key}: {len(front)} equations on the front, {elapsed:.0f} s; selected by the package: "
          f"complexity {int(front.loc[best, 'complexity'])}, loss {float(front.loc[best, 'loss']):.6g}", flush=True)
    return front, best, params, elapsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=list(common.TASKS))
    parser.add_argument("setting", choices=["default", "matched"])
    parser.add_argument("seed", nargs="?", type=int)
    parser.add_argument("--pool", action="store_true", help="write pool.json for the model files present")
    parser.add_argument("--threads", action="store_true", help="multithreaded search (not reproducible)")
    args = parser.parse_args()
    task, setting = args.task, args.setting
    models = folder_of(task, setting) / "models"
    if args.pool:
        order = sorted(p.stem for p in models.glob("ReferencePysr*.json"))
        common.write_pool(models, order, "Reference models found by PySR without the agent, one per seed; none is recommended.")
        print("pool:", order)
        return
    seed = args.seed
    spec = common.TASKS[task]
    out, unit = spec["output"], spec["units"][spec["output"]]
    names, x, wanted, omitted = targets(task)
    raw = folder_of(task, setting) / "raw" / f"s{seed}"
    raw.mkdir(parents=True, exist_ok=True)
    print(f"{task} {setting} seed {seed}: {len(x)} rows, targets {[k for k, v in wanted.items() if v is not None]}", flush=True)

    import pysr

    fronts, chosen, params, seconds = {}, {}, {}, {}
    for key, y in wanted.items():
        if y is None:
            continue
        fronts[key], chosen[key], params, seconds[key] = fit_target(key, x, y, setting, seed, raw, args.threads)
        fronts[key].drop(columns=["lambda_format", "sympy_format"], errors="ignore").to_csv(raw / f"{key}_front.csv", index=True)

    prefixes = {key: f"c{chr(ord('a') + i)}" for i, key in enumerate(spec["keys"])}

    def assemble(choice: dict[str, int]):
        expressions, rows = {}, []
        for key in spec["keys"]:
            if wanted[key] is None:
                expressions[key] = {"dtheta": "omega"}[key]
                continue
            text, r = to_expression(fronts[key].loc[choice[key], "sympy_format"], names, prefixes[key])
            expressions[key] = text
            rows.extend(r)
        return expressions, rows

    def error(choice: dict[str, int]) -> float:
        expressions, rows = assemble(choice)
        try:
            return common.training_error(task, expressions, {r["name"]: r["value"] for r in rows})
        except Exception as exc:  # an equation that cannot be simulated counts as a failure
            print("   simulation raised", type(exc).__name__, exc, flush=True)
            return float("inf")

    package_choice = dict(chosen)
    package_error = error(package_choice)
    sweeps = 0
    if setting == "matched":
        changed = True
        while changed and sweeps < 5:
            changed, sweeps = False, sweeps + 1
            for key in fronts:
                scores = {int(i): error({**chosen, key: int(i)}) for i in fronts[key].index}
                best = min(scores, key=lambda i: (scores[i], i))
                if scores[best] < error(chosen):
                    chosen[key], changed = best, True
    expressions, rows = assemble(chosen)
    train = error(chosen)
    print(f"  training RMSE of the simulated {out}: {train:.6g} {unit} (equations selected by the "
          f"package: {package_error:.6g} {unit})", flush=True)
    for key, text in expressions.items():
        print("   ", key, "=", text if len(text) < 300 else text[:300] + " ...", flush=True)

    # agreement of the written expression with the prediction of the package on the fitted rows
    for key in fronts:
        text, r = to_expression(fronts[key].loc[chosen[key], "sympy_format"], names, prefixes[key])
        table = {n: sp.Symbol(n) for n in names + [q["name"] for q in r]}
        table.update({"Abs": sp.Abs, "sign": sp.sign})
        f = sp.lambdify([table[n] for n in names], sp.sympify(text, locals=table).subs({table[q["name"]]: q["value"] for q in r}), "numpy")
        mine = np.broadcast_to(f(*x.T), (len(x),))
        theirs = np.asarray(fronts[key].loc[chosen[key], "lambda_format"](x), float)
        print(f"   {key}: largest difference to the prediction of the package {float(np.max(np.abs(mine - theirs))):.3g}", flush=True)

    fitted_keys = list(fronts)
    operators = (f"binary operators `{'`, `'.join(params['binary_operators'] or ['+', '-', '*', '/'])}`"
                 + (f" and unary operators `{'`, `'.join(params['unary_operators'])}`" if params.get("unary_operators") else " and no unary operator"))
    if setting == "matched":
        selection = (f"Of the equations on the Pareto front of accuracy and complexity that the search "
                     f"returns for a target, the one with the smallest root mean squared error of the "
                     f"simulated `{out}` on the training data was selected, with the simulation of the "
                     f"evaluation of the task"
                     + (f"; with several targets the choice was made target by target, starting from the "
                        f"equations that the package selects, until no choice changed ({sweeps} sweeps)" if len(fronts) > 1 else "")
                     + f". With the equations that the package selects the training error is "
                       f"`{package_error:.4g}` {unit}. The unary operators were added because the task "
                       f"permits these functions; `Piecewise`, `Min`, `Max` and the remaining permitted "
                       f"functions were not offered to the search.")
    else:
        selection = ("The equation of each target is the one that the package selects with "
                     "`model_selection=\"best\"`: the equation with the highest score (the decrease of "
                     "the logarithm of the loss per unit of complexity) among those whose loss is at "
                     "most 1.5 times the smallest loss of the front. The defaults were used because "
                     "the model is a reference for what the tool gives without tuning.")
    mode = ("`deterministic=True`, `parallelism=\"serial\"`, so that the seed determines the result"
            if not args.threads else "multithreading, so that the seed does not determine the result")
    prescribed = "".join(f" The expression `{k}` is `{expressions[k]}`, as the task prescribes." for k in spec["keys"] if wanted[k] is None)
    what = "next state" if spec["formulation"] == "discrete" else "supplied derivative column"
    if spec["formulation"] == "discrete":
        data_text = f"data/train.csv, `{len(x)}` one-step transitions of all trajectories."
        if omitted:
            data_text += (f" `{omitted}` transitions in which the logged heading `phi` wraps at pi were "
                          f"left out, because the wrapped next heading is not a continuous function of "
                          f"the present state.")
    else:
        data_text = f"data/train.csv, all `{len(x)}` rows of all trajectories."
    if "val" in spec["files"]:
        data_text += " The validation data were not used."
    content = {
        "expressions": expressions,
        "parameters": rows,
        "estimation": {
            "criterion": f"Mean squared error between the equation and its target, the default loss "
                         f"of the package, for each target separately ({', '.join('`' + k + '`' for k in fitted_keys)}); "
                         f"the target is the {what}. This is not the simulation error that the task scores."
                         + (" The simulation error on the training data was used only to select among "
                            "the equations that the search returned." if setting == "matched" else ""),
            "data": data_text,
            "method": f"Symbolic regression by regularized evolution with PySR {pysr.__version__} "
                      f"(Cranmer, 2023, arXiv:2305.01582), pysr.PySRRegressor, one search per target, "
                      f"with {operators}, `niterations={params['niterations']}`, "
                      f"`populations={params['populations']}`, `population_size={params['population_size']}`, "
                      f"`maxsize={params['maxsize']}` and the other settings of the package at their "
                      f"defaults. {selection}{prescribed} The search needs no starting values from the "
                      f"user: it starts from random expressions and optimizes the constants of an "
                      f"equation inside the search. Seed `random_state={seed}`, {mode}. "
                      f"Search time: {', '.join(f'{k} {v:.0f} s' for k, v in seconds.items())}.",
            "script": SCRIPT,
        },
        "discussion": {
            "family": "Closed-form expression found by symbolic regression (genetic search over "
                      "expression trees). Reference model; it is not a candidate of the agent.",
            "interpretation": "The terms have no assigned physical meaning; each expression is the "
                              "equation that the search returned for its target, written with its "
                              "constants as named parameters.",
            "origin": "The structure was found by the search of the package from the operators "
                      "listed in the estimation record; no physical reasoning entered"
                      + ("; the selection among the returned equations used the simulation error "
                         "on the training data." if setting == "matched" else "."),
            "limitations": "The search minimizes the error of one step or of the derivative, not the "
                           "simulation error, so that a small loss does not bound the error of a "
                           "long simulation. The result depends on the seed. Outside the range of "
                           "the training data the expression is not expected to hold.",
        },
    }
    common.write_model(models, label_of(setting, seed), content)
    record = {"task": task, "setting": setting, "seed": seed, "threads": args.threads, "pysr": pysr.__version__,
              "parameters_of_the_search": {k: (v if isinstance(v, (int, float, str, bool, list, type(None))) else str(v)) for k, v in params.items()},
              "seconds": seconds, "selected_by_package": package_choice, "selected": chosen,
              "training_error": train, "training_error_package_selection": package_error,
              "front_sizes": {k: int(len(v)) for k, v in fronts.items()}}
    (raw / "record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("written:", models / f"{label_of(setting, seed)}.json", flush=True)


if __name__ == "__main__":
    main()
