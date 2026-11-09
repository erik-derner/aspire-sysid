"""Generate the blind variants of the tasks turtlebot, fermenter-pressure and friction-driven.

A **blind variant** is a separate task folder, generated from a described task, whose data
values, split into training, validation and test data, sampling period T_s, column roles,
evaluation settings, failure limits, budget, pool limit and permitted functions are those of the
described task, and which omits everything that tells the agent what the system is: column
names, units, symbols, description, intended use, formal and natural-language requirements,
literature, supporting files, discussion questions, given constants other than T_s, recording
names. The noise and preprocessing statements are data-quality
information, which is not among the omitted fields: they are rewritten in the blind
names from the table ``DATA_QUALITY``, naming no physical quantity, unit or system and stating no
relation between columns that the formulation roles do not already state. The Kept / Replaced / Omitted decisions of
each field are listed in ``tasks/BLIND_MAPPING.md``, which this script writes together with the
machine-readable mapping ``tasks/blind_mapping.yaml``. Both files document for the reader how the
blind folders were generated; the harness neither provisions nor reads them (a
blind variant is an ordinary task with its own experiment).

Deterministic; PyYAML and the standard library only. Run from any folder:

    python tasks/make_blind.py            # (re)write the blind folders and both mapping files
    python tasks/make_blind.py --check    # regenerate in a temporary folder, compare byte for byte

A re-run writes byte-identical files: no clock, random number or file-system order enters the
output (the generation date of a blind task is a fixed constant: ``GENERATED_ON``, or the date in
its entry of ``BLIND``).

**Names**. The output column is ``y``; the other input and state columns are
``x1, x2, ...`` in the column order of the described task; a state-derivative column is
``d<state>`` in the blind names (for example ``dx1``, ``dy``), which is also the expression key of
that state. The expression key of a state of a discrete-time task is ``<state>_next`` in the blind
names (for example ``y_next``, ``x1_next``). The trajectory column keeps the name ``trajectory``, a word of the harness's own
vocabulary that the brief uses for every dynamic task, so it carries no information about the
system. The test files are ``test/held_out_<i>.csv``; the training and validation files keep the
neutral names ``data/train.csv`` and ``data/val.csv``.

**Identifiers.** The blind identifiers were drawn once as ``task-`` followed
by four characters chosen independently and uniformly from ``a``-``z`` and ``0``-``9`` with
Python's ``secrets.choice``; a second draw with ``random.SystemRandom.sample`` fixed the order in
which they were assigned to the described tasks. They are constants here and are never derived
from the described identifier.

**Ranges.** The declared range of a described column is chosen by the task author and may carry
physics (``[-3.1416, 3.1416]`` for an angle, ``[0, 100]`` for a valve position in percent). A
blind column declares no range; the agent can compute the range of a column from
the data. The failure-limit justification is regenerated from the smallest and the largest
training value of the variable.
"""

from __future__ import annotations

import argparse
import filecmp
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

TASKS_DIR = Path(__file__).resolve().parent

GENERATED_ON = "2026-10-08"
"""Fixed generation date written into provenance.md (so that a re-run is byte-identical)."""

SCRIPT = "tasks/make_blind.py"

UNIT_NOT_SUPPLIED = "not supplied"
"""The unit of every blind column: the task does not state the unit (tasks/README.md, Section 3)."""

TRAJECTORY_COLUMN = "trajectory"

BLIND: tuple[dict[str, Any], ...] = (
    # Identifiers drawn once (module docstring).
    {"id": "task-jdhj", "described": "friction-driven"},
    {"id": "task-qtqm", "described": "fermenter-pressure"},
    {"id": "task-kt5o", "described": "turtlebot"},
)

DATA_QUALITY: dict[str, dict[str, tuple[str, str]]] = {
    # described task -> field -> (blind statement, rationale). The source statement is the field of
    # the described task.yaml; both are listed in BLIND_MAPPING.md. No described task states its
    # noise or preprocessing at present, so the table is empty.
}
"""Neutral noise and preprocessing statements of the blind variants, with their rationale."""

FORBIDDEN_WORDS = (
    "theta", "omega", "kappa", "valve", "flow", "pressure", "angle", "angular", "velocity", "acceleration",
    "force", "slip", "peak", "friction", "pendulum", "encoder", "motor", "voltage", "fermenter", "tank",
    "tire", "magic", "sensor", "air", "rad", "rig",
)
"""Words that no statement of a blind task may contain (checked case-insensitively as words)."""

MAPPING_YAML = "blind_mapping.yaml"
MAPPING_MD = "BLIND_MAPPING.md"
PROVENANCE = "provenance.md"

_OMITTED_TOP = (
    ("description", "system description"),
    ("intended_use", "intended use"),
    ("requirements", "formal requirements"),
    ("requirements_nl", "natural-language requirements"),
    ("literature", "literature"),
    ("context", "supporting files"),
    ("discussion_questions", "discussion questions"),
    ("constants", "given constants (T_s is kept in dynamics.sampling_period)"),
)


class BlindError(RuntimeError):
    """The described task has a feature that this generator does not handle."""


# ---------------------------------------------------------------------------------------------


def title_of(blind_id: str) -> str:
    """The neutral title of a blind task: ``Identification task <suffix>``."""
    return f"Identification task {blind_id.split('-', 1)[1]}"


def column_map(described: dict[str, Any]) -> dict[str, str]:
    """Described column name -> blind column name (module docstring, "Names")."""
    cols = described["columns"]
    out: dict[str, str] = {}
    k = 0
    for c in cols:
        roles = set(c["roles"])
        if "output" in roles:
            out[c["name"]] = "y"
        elif roles & {"input", "state"}:
            k += 1
            out[c["name"]] = f"x{k}"
    for c in cols:
        if "state_derivative" in c["roles"]:
            out[c["name"]] = "d" + out[c["derivative_of"]]
    if len(set(out.values())) != len(out) or set(out) != {c["name"] for c in cols}:
        raise BlindError(f"column mapping is not one-to-one: {out}")
    return out


def rename_identifiers(text: str, names: dict[str, str]) -> str:
    """Replace every whole identifier of ``names`` in an expression text in one pass."""
    if not names:
        return text
    pat = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")(?![A-Za-z0-9_])")
    return pat.sub(lambda m: names[m.group(1)], text)


def _expression_keys(described: dict[str, Any], cmap: dict[str, str]) -> dict[str, str]:
    form = described["formulation"]
    if form == "static":
        out = next(c["name"] for c in described["columns"] if "output" in c["roles"])
        return {cmap[out]: out}
    if form == "continuous":
        return {"d" + cmap[s]: "d" + s for s in described["dynamics"]["states"]}
    if form == "discrete":
        return {cmap[s] + "_next": s + "_next" for s in described["dynamics"]["states"]}
    raise BlindError(f"formulation {form!r} is not handled by the generator")


def _read_csv(path: Path) -> tuple[list[str], bytes]:
    """Header names and the bytes after the header line (kept verbatim)."""
    raw = path.read_bytes()
    nl = raw.index(b"\n")
    return raw[:nl].decode("ascii").split(","), raw[nl + 1:]


def _training_range(body: bytes, header: list[str], name: str) -> list[float]:
    j = header.index(name)
    vals = [float(line.split(b",")[j]) for line in body.splitlines() if line.strip()]
    return [min(vals), max(vals)]


def _rewrite_csv(src: Path, dst: Path, cmap: dict[str, str]) -> None:
    header, body = _read_csv(src)
    new = [cmap.get(h, h) if h != TRAJECTORY_COLUMN else TRAJECTORY_COLUMN for h in header]
    unknown = [h for h in header if h not in cmap and h != TRAJECTORY_COLUMN]
    if unknown:
        raise BlindError(f"{src}: header names {unknown} are not columns of the task")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes((",".join(new) + "\n").encode("ascii") + body)


def justification(variable: str, bound: float, rng: list[float]) -> str:
    """The neutral justification of a failure limit, from the training range of ``variable``;
    a training range of zero width at zero (all values 0) has no ratio and says so."""
    largest = max(abs(rng[0]), abs(rng[1]))
    if largest == 0:
        return f"numerical divergence bound; every training value of {variable} is 0"
    return f"numerical divergence bound, about {round(bound / largest)} times the largest training magnitude of {variable}"


def _dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100, default_flow_style=None)


# ---------------------------------------------------------------------------------------------


def build_one(entry: dict[str, Any], out_root: Path) -> dict[str, Any]:
    """Write the blind folder ``out_root/<id>/`` and return its mapping entry."""
    bid, did = entry["id"], entry["described"]
    ddir = TASKS_DIR / did
    d = yaml.safe_load((ddir / "task.yaml").read_text(encoding="utf-8"))
    if d.get("added_functions") or (d.get("dynamics") or {}).get("delays"):
        raise BlindError(f"{did}: added functions and NARX delays are not handled by the generator")
    cmap = column_map(d)
    keys = _expression_keys(d, cmap)
    folder = out_root / bid
    folder.mkdir(parents=True)

    # -- data files (header renamed, every other byte kept) ------------------------------------
    data = d["data"]
    traj = data.get("trajectory_column")
    if traj not in (None, TRAJECTORY_COLUMN):
        raise BlindError(f"{did}: trajectory column {traj!r} is not {TRAJECTORY_COLUMN!r}")
    files: dict[str, str] = {}
    for split in ("train", "val"):
        if data.get(split) is None:
            continue
        rel = f"data/{split}.csv"
        _rewrite_csv(ddir / data[split], folder / rel, cmap)
        files[rel] = data[split]
    tests = []
    for i, t in enumerate(d.get("test") or [], 1):
        rel = f"test/held_out_{i}.csv"
        _rewrite_csv(ddir / t["file"], folder / rel, cmap)
        files[rel] = t["file"]
        tests.append({"file": rel, "trajectory": t["trajectory"]})

    # -- columns: blind names, roles, unit not supplied, no declared range ----------------------
    header, body = _read_csv(folder / "data/train.csv")
    columns = []
    for c in d["columns"]:
        col: dict[str, Any] = {"name": cmap[c["name"]], "roles": list(c["roles"])}
        if c.get("derivative_of"):
            col["derivative_of"] = cmap[c["derivative_of"]]
        col["unit"] = UNIT_NOT_SUPPLIED
        columns.append(col)
    ranges = {c["name"]: _training_range(body, header, c["name"]) for c in columns}

    spec: dict[str, Any] = {
        "schema_version": 1,
        "id": bid,
        "title": title_of(bid),
        "formulation": d["formulation"],
        "columns": columns,
    }
    if d.get("dynamics"):
        dyn = d["dynamics"]
        spec["dynamics"] = {
            "sampling_period": dyn["sampling_period"],
            "states": [cmap[s] for s in dyn["states"]],
            "inputs": [cmap[u] for u in dyn["inputs"]],
            "measurement": rename_identifiers(str(dyn.get("measurement", "")), cmap) or None,
            **{k: dyn[k] for k in ("input_hold", "integrator", "substeps") if k in dyn},
        }
        if spec["dynamics"]["measurement"] is None:
            del spec["dynamics"]["measurement"]
    ev = d["evaluation"]
    limits = []
    for fl in ev.get("failure_limits") or []:
        v = cmap[fl["variable"]]
        limits.append({
            "variable": v, "lower": fl["lower"], "upper": fl["upper"], "unit": UNIT_NOT_SUPPLIED,
            "justification": justification(v, max(abs(fl["lower"]), abs(fl["upper"])), ranges[v]),
        })
    spec["evaluation"] = {
        **{k: ev[k] for k in ("mode", "initialization", "scoring") if k in ev},
        "failure_limits": limits,
        **{k: ev[k] for k in ("time_limit_s", "symbolic_time_limit_s", "horizon") if k in ev},
    }
    sdata: dict[str, Any] = {"train": "data/train.csv"}
    if "data/val.csv" in files:
        sdata["val"] = "data/val.csv"
    if traj:
        sdata["trajectory_column"] = TRAJECTORY_COLUMN
    quality = DATA_QUALITY.get(did, {})
    for field in ("noise", "preprocessing"):
        if field in quality:
            text = quality[field][0]
            _assert_neutral(text, d, f"{did}: data.{field}")
            sdata[field] = text
    spec["data"] = sdata
    if d.get("functions") is not None:
        spec["functions"] = list(d["functions"])
    spec["pool_cap"] = d["pool_cap"]
    if d.get("budget") is not None:
        spec["budget"] = d["budget"]
    spec["test"] = tests

    reference = None
    if d.get("reference"):
        ref = yaml.safe_load((ddir / d["reference"]["file"]).read_text(encoding="utf-8"))
        exprs = {_blind_key(k, keys): rename_identifiers(v, cmap) for k, v in ref["expressions"].items()}
        (folder / "reference").mkdir()
        (folder / "reference/reference.yaml").write_text(
            "# Sealed reference expression (tasks/make_blind.py).\n" + _dump({"format_version": 1, "expressions": exprs}), encoding="utf-8", newline="\n")
        files["reference/reference.yaml"] = d["reference"]["file"]
        box = {cmap[k]: v for k, v in d["reference"]["domain"]["box"].items()}
        spec["reference"] = {"file": "reference/reference.yaml", "domain": {"box": box}}
        reference = {"expression_keys": {_blind_key(k, keys): k for k in ref["expressions"]}}

    (folder / "task.yaml").write_text(_dump(spec), encoding="utf-8", newline="\n")

    omitted = [label for key, label in _OMITTED_TOP if d.get(key)]
    omitted += ["column symbols", "column descriptions", "units (every unit is 'not supplied')",
                "declared column ranges"]
    for field in ("noise", "preprocessing"):
        if data.get(field) and field not in quality:
            omitted.append(f"{field} statement (no neutral wording in DATA_QUALITY)")
    if data.get("source_name") or any(t.get("source_name") for t in d.get("test") or []):
        omitted.append("recording names (data.source_name, test[].source_name; listed in this mapping only)")
    omitted.append("failure-limit justifications (regenerated from the training values)")
    kept = ["data values, row order and trajectory boundaries of every file", "split into training, validation and test data",
            "column roles", "evaluation mode, initialization, scoring interval, time limits, horizon of the training evaluation",
            "failure limits (numbers)",
            "budget", "pool limit", "permitted functions"]
    if d.get("dynamics"):
        kept.insert(3, "sampling period T_s, states, inputs, measurement equation, input hold, integrator, substeps")
    for field in ("noise", "preprocessing"):
        if field in quality:
            kept.append(f"{field} statement, rewritten neutrally (see the table below)")
    if reference is not None:
        kept.append("sealed reference expression (rewritten in the blind names) and its domain")

    (folder / PROVENANCE).write_text(_provenance(bid, did, cmap, keys, files, sorted(files), entry.get("generated_on", GENERATED_ON)),
                                     encoding="utf-8", newline="\n")
    return {
        "described_task": did,
        "title": spec["title"],
        "formulation": d["formulation"],
        "columns": {b: dname for dname, b in cmap.items()},
        "expression_keys": dict(sorted(keys.items())),
        "trajectory_column": {TRAJECTORY_COLUMN: traj} if traj else {},
        "files": {k: files[k] for k in sorted(files)},
        "recording_names": {
            "train": _names(data.get("source_name", {}).get("train")),
            "val": _names(data.get("source_name", {}).get("val")),
            "test": {t["file"]: t.get("source_name") for t in (d.get("test") or [])},
        },
        "kept": kept,
        "omitted": omitted,
        "data_quality": {
            field: {"blind": quality[field][0], "described": " ".join(str(data.get(field) or "").split()), "rationale": quality[field][1]}
            for field in ("noise", "preprocessing") if field in quality
        },
    }


def _blind_key(key: str, keys: dict[str, str]) -> str:
    inv = {v: k for k, v in keys.items()}
    if key not in inv:
        raise BlindError(f"reference expression key {key!r} is not an expression key")
    return inv[key]


def _names(v: Any) -> list[str]:
    if v is None:
        return []
    return [v] if isinstance(v, str) else [str(x) for x in v]


def _assert_neutral(text: str, d: dict[str, Any], where: str) -> None:
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
    bad = sorted({c["name"] for c in d["columns"]} & words)
    units = {str(c.get("unit")) for c in d["columns"]} - {"-"}
    bad += sorted(u for u in units if re.search(r"(?<![A-Za-z])" + re.escape(u) + r"(?![A-Za-z])", text))
    bad += [w for w in FORBIDDEN_WORDS if re.search(rf"(?<![A-Za-z0-9_]){re.escape(w)}(?![A-Za-z0-9_])", text, re.I)]
    if bad:
        raise BlindError(f"{where} is to be kept, but it names {bad}")


def _provenance(bid: str, did: str, cmap: dict[str, str], keys: dict[str, str], files: dict[str, str], order: list[str],
                generated_on: str = GENERATED_ON) -> str:
    lines = [
        f"# Provenance of the task `{bid}`",
        "",
        "For the user only; never provisioned into a working directory (tasks/README.md, Section 5).",
        "",
        f"Blind variant of the described task `{did}`, generated by `{SCRIPT}`. "
        "The data values are identical to those of the described task: every data and test file is the described file with "
        "only its header row renamed; row order and trajectory boundaries are unchanged. Origin and construction "
        f"of the data: `tasks/{did}/provenance.md`. The complete mapping and the list of kept, replaced and "
        "omitted fields: `tasks/BLIND_MAPPING.md`.",
        "",
        "| Blind column | Described column |",
        "|---|---|",
    ]
    lines += [f"| `{b}` | `{dn}` |" for dn, b in cmap.items()]
    lines += ["", "| Blind expression key | Described expression key |", "|---|---|"]
    lines += [f"| `{b}` | `{dk}` |" for b, dk in sorted(keys.items())]
    lines += ["", "| Blind file | Described file |", "|---|---|"]
    lines += [f"| `{f}` | `{files[f]}` |" for f in order]
    return "\n".join(lines) + "\n"


def _mapping_markdown(mapping: dict[str, Any]) -> str:
    L = [
        "# Blind task variants: mapping to the described tasks",
        "",
        "A **blind variant** is a task folder generated from a described task by `tasks/make_blind.py`; it keeps the data "
        "values and the evaluation settings and omits everything that tells the agent (the language model) what the system is."
        " A blind variant is an ordinary task with its own experiment: the "
        "harness neither provisions nor reads this file or `tasks/blind_mapping.yaml`; both document how the "
        "blind folders were generated. Regenerate "
        "both files and the blind folders with `python tasks/make_blind.py`; `python tasks/make_blind.py --check` verifies that "
        "they are up to date.",
        "",
        "**Identifiers.** Drawn once: `task-` followed by four characters chosen independently and uniformly from "
        "`a`-`z` and `0`-`9` (`secrets.choice`); a second draw (`random.SystemRandom().sample`) fixed the assignment to the "
        "described tasks. They are "
        "fixed constants of the generator and are not derived from the described identifiers.",
        "",
        "**Names.** Output column `y`; other input and state columns `x1, x2, ...` in the described column order; a state-derivative "
        "column `d<state>` in the blind names, which is also the expression key of that state; the expression key of a state "
        "of a discrete-time task is `<state>_next` in the blind names. The trajectory column keeps its "
        "name `trajectory` (a harness word, used in every dynamic brief). Test files `test/held_out_<i>.csv`. Unit of every "
        "column and failure limit: `not supplied`. A blind column declares no range.",
        "",
        "| Blind task | Described task | Title of the blind task |",
        "|---|---|---|",
    ]
    for bid, e in mapping["blind_tasks"].items():
        L.append(f"| `{bid}` | `{e['described_task']}` | {e['title']} |")
    for bid, e in mapping["blind_tasks"].items():
        L += ["", f"## `{bid}` (blind variant of `{e['described_task']}`)", "", "| Blind column | Described column |", "|---|---|"]
        L += [f"| `{b}` | `{dn}` |" for b, dn in e["columns"].items()]
        if e["trajectory_column"]:
            L += [f"| `{b}` (trajectory column) | `{dn}` |" for b, dn in e["trajectory_column"].items()]
        L += ["", "| Blind expression key | Described expression key |", "|---|---|"]
        L += [f"| `{b}` | `{dk}` |" for b, dk in e["expression_keys"].items()]
        L += ["", "| Blind file | Described file | Recording name |", "|---|---|---|"]
        rec = e["recording_names"]
        for bf, dfile in e["files"].items():
            if bf == "data/train.csv":
                names = ", ".join(rec["train"]) or "not stated"
            elif bf == "data/val.csv":
                names = ", ".join(rec["val"]) or "not stated"
            elif bf.startswith("test/"):
                names = rec["test"].get(dfile) or "not stated"
            else:
                names = "not applicable"
            L.append(f"| `{bf}` | `{dfile}` | {names} |")
        if e["data_quality"]:
            L += ["", "| Statement | Blind task | Described task | Rationale |", "|---|---|---|---|"]
            L += [f"| {f} | {q['blind']} | {q['described']} | {q['rationale']} |" for f, q in e["data_quality"].items()]
        L += ["", "Kept: " + "; ".join(e["kept"]) + ".", "", "Omitted: " + "; ".join(e["omitted"]) + "."]
    return "\n".join(L) + "\n"


def generate(out_root: Path) -> None:
    """Write the blind folders and both mapping files into ``out_root``."""
    mapping: dict[str, Any] = {"format_version": 1, "generated_by": SCRIPT, "generated_on": GENERATED_ON, "blind_tasks": {}}
    for entry in BLIND:
        mapping["blind_tasks"][entry["id"]] = build_one(entry, out_root)
    (out_root / MAPPING_YAML).write_text(
        "# Blind-to-described mapping (tasks/BLIND_MAPPING.md). Harness-side only; never provisioned.\n"
        "# Generated by tasks/make_blind.py; do not edit.\n" + _dump(mapping), encoding="utf-8", newline="\n")
    (out_root / MAPPING_MD).write_text(_mapping_markdown(mapping), encoding="utf-8", newline="\n")


def outputs() -> list[str]:
    """The names this script owns in ``tasks/``."""
    return [e["id"] for e in BLIND] + [MAPPING_YAML, MAPPING_MD]


def _same_tree(a: Path, b: Path) -> list[str]:
    diffs = []
    fa = sorted(p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    fb = sorted(p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    diffs += [f"only in the generated output: {x}" for x in sorted(set(fa) - set(fb))]
    diffs += [f"not generated: {x}" for x in sorted(set(fb) - set(fa))]
    diffs += [f"differs: {x}" for x in sorted(set(fa) & set(fb)) if not filecmp.cmp(a / x, b / x, shallow=False)]
    return diffs


def check(tasks_dir: Path = TASKS_DIR) -> list[str]:
    """Differences between a fresh generation and the files in ``tasks_dir`` (empty: up to date)."""
    with tempfile.TemporaryDirectory() as tmp:
        generate(Path(tmp))
        diffs = []
        for name in outputs():
            a, b = Path(tmp) / name, tasks_dir / name
            if a.is_dir():
                diffs += [f"{name}/{x}" for x in _same_tree(a, b)] if b.is_dir() else [f"missing folder {name}/"]
            elif not b.is_file() or not filecmp.cmp(a, b, shallow=False):
                diffs.append(f"differs or missing: {name}")
        return diffs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="compare a fresh generation with tasks/ and report differences")
    args = ap.parse_args(argv)
    if args.check:
        diffs = check()
        for x in diffs:
            print(x)
        print("blind variants are up to date" if not diffs else f"{len(diffs)} difference(s)")
        return 1 if diffs else 0
    with tempfile.TemporaryDirectory() as tmp:
        generate(Path(tmp))
        for name in outputs():
            target = TASKS_DIR / name
            if target.is_dir():
                if not (target / PROVENANCE).read_text(encoding="utf-8").startswith(f"# Provenance of the task `{name}`"):
                    raise BlindError(f"{target} exists and was not written by this script; refusing to replace it")
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            src = Path(tmp) / name
            if src.is_dir():
                shutil.copytree(src, target)
            else:
                shutil.copyfile(src, target)
    print("wrote " + ", ".join(outputs()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
