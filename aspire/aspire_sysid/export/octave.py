"""Running exported M-files and the Matlab framework in GNU Octave (numerical
re-verification of every M-file; the export of an experiment runs in the Matlab framework).

When ``octave-cli`` (or ``octave``) is installed:

* :func:`run_models_in_octave` runs every exported model file in Octave on the verification points
  and compares ``y`` with the harness's values of the SymPy expression (relative tolerance
  :data:`aspire_sysid.export.python_export.VERIFY_RTOL`), and runs ``srProvenance`` on each
  file and checks that its evaluator reproduces the model. Each model is called through a copy in
  a temporary folder under a unique function name, because every run folder has its own
  ``model01``; only the function name of the copy differs.
* :func:`run_framework_in_octave` runs the Matlab framework on the export folder: ``startup``,
  ``srScanModels`` and ``srEvalHP`` (recorded with their errors), ``srSplitDataVal``,
  ``srLoadData`` on every data set, and ``srSimulate`` (static data: the model output) for every
  model in ``HP/`` and data set; the errors on the scored samples are compared with the errors of
  the ASPIRE evaluation (relative tolerance :data:`FRAMEWORK_RTOL`).

Octave is not Matlab. the Matlab framework uses Matlab features that Octave 8.4 lacks: the ``string``
class (``string``, ``strlength``; ``==`` between double-quoted texts of different lengths is an
error in Octave), the ``table`` class (``srScanModels``, ``srEvaluate``, ``srSummary`` and
therefore ``srEvalHP``) and Java (the MD5 hash of ``srFileHash``, which then falls back to the file
size and date). This module therefore puts two compatibility functions on the Octave path, in a
temporary folder outside the framework: ``string(x)``, which returns ``char(x)``, and
``strlength(s)``, which returns ``numel(char(s))``; and it removes the field ``form`` from a data
set before ``srSimulate``, whose test ``data.form == "static"`` Octave cannot evaluate. The
framework files are never modified. The results state which functions ran and which failed, with
Octave's error messages.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .python_export import _compare

__all__ = [
    "octave_executable", "octave_available", "octave_version", "run_octave", "run_models_in_octave", "run_framework_in_octave",
    "COMPAT_FUNCTIONS", "FRAMEWORK_RTOL", "framework_folder",
]

COMPAT_FUNCTIONS: dict[str, str] = {
    "string.m": "function s = string(x)\n% Octave compatibility for the Matlab framework (ASPIRE harness): Matlab strings as char.\ns = char(x);\nend\n",
    "strlength.m": "function n = strlength(s)\n% Octave compatibility for the Matlab framework (ASPIRE harness).\nn = numel(char(s));\nend\n",
}
"""Compatibility functions put on the Octave path for ``srProvenance`` (module docstring)."""


def octave_executable() -> str | None:
    """Path of ``octave-cli`` or ``octave``, or ``None``. """
    return shutil.which("octave-cli") or shutil.which("octave")


def octave_available() -> bool:
    """True when GNU Octave is installed. """
    return octave_executable() is not None


def run_octave(script: str, cwd: str | Path, timeout: float = 600.0) -> subprocess.CompletedProcess:
    """Run an Octave script text in ``cwd`` without a user interface; returns the completed process.

    ``TMPDIR`` points to ``cwd``, so that the copies that ``srBindModel`` and ``srProvenance``
    write under Octave's ``tempdir`` are private to this call (their names are derived from the
    file size and date when Java is unavailable, and could otherwise collide with stale copies).

    """
    exe = octave_executable()
    if exe is None:
        raise RuntimeError("GNU Octave is not installed")
    path = Path(cwd) / "aspire_octave_script.m"
    path.write_text(script, encoding="utf-8", newline="\n")
    env = dict(os.environ, TMPDIR=str(Path(cwd).resolve()))
    try:
        return subprocess.run([exe, "--no-gui", "--quiet", "--norc", str(path.name)], cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, env=env)
    finally:
        path.unlink(missing_ok=True)


def octave_version() -> str | None:
    """The Octave version string, or ``None``. """
    exe = octave_executable()
    if exe is None:
        return None
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60)
    first = out.stdout.splitlines()[0] if out.stdout else ""
    return first.strip() or None


def framework_folder(start: str | Path | None = None) -> Path | None:
    """the folder of the framework of the repository that contains ``start`` or, failing that,
    of the repository that contains the harness; ``None`` when neither has it. """
    starts = ([Path(start).resolve()] if start is not None else []) + [Path(__file__).resolve()]
    for p in starts:
        for parent in [p, *p.parents]:
            cand = parent / "resources" / "matlab-framework"
            if (cand / "srProvenance.m").is_file():
                return cand
    return None


def _q(text: str) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def run_models_in_octave(folder: str | Path, models: Sequence[Any], points: np.ndarray, *, provenance: bool = True) -> dict[str, Any]:
    """Run the exported models of one task folder in Octave and compare them (module docstring).

    ``models`` are :class:`aspire_sysid.export.matlab_export.MatlabModel` objects (their ``file``
    relative to ``folder`` and their ``reference`` values at ``points``). Returns ``{"version",
    "models": {file: {"passed", ...}}, "provenance_summary", "framework"}``.

    """
    folder = Path(folder)
    fw = framework_folder(folder)
    with tempfile.TemporaryDirectory(prefix="aspire_octave_") as tmp:
        tmpd = Path(tmp)
        np.savetxt(tmpd / "X.csv", points, delimiter=",", fmt="%.17g")
        compat = tmpd / "compat"
        compat.mkdir()
        for name, text in COMPAT_FUNCTIONS.items():
            (compat / name).write_text(text, encoding="ascii", newline="\n")
        lines = ["X = dlmread('X.csv', ',');", "fid = fopen('out.txt', 'w');", f"addpath({_q(str(tmpd / 'models'))});"]
        (tmpd / "models").mkdir()
        if provenance and fw is not None:
            lines.append(f"addpath({_q(str(fw))}, '-end');")
            lines.append(f"addpath({_q(str(compat))}, '-end');")
        for i, m in enumerate(models):
            src = (folder / m.file).read_text(encoding="ascii")
            name = f"aspire_m{i + 1:03d}"
            first, rest = src.split("\n", 1)
            (tmpd / "models" / f"{name}.m").write_text(first.replace(Path(m.file).stem + "(x)", name + "(x)") + "\n" + rest, encoding="ascii", newline="\n")
            lines += [
                "try",
                f"  [y, info] = {name}(X);",
                f"  fprintf(fid, 'MODEL %d %d %d\\n', {i + 1}, isreal(y), numel(y));",
                "  fprintf(fid, '%.17g\\n', real(y));",
                f"  fprintf(fid, 'INFO %d %d %d\\n', {i + 1}, isfield(info, 'FittedParameters'), numel(info.FittedParameters));",
                "catch err",
                f"  fprintf(fid, 'ERROR %d %s\\n', {i + 1}, strrep(err.message, char(10), ' '));",
                "end",
            ]
            if provenance and fw is not None:
                lines += [
                    "try",
                    f"  prov = srProvenance({_q(str((folder / m.file).resolve()))}, X);",
                    "  if isempty(prov)",
                    f"    fprintf(fid, 'PROV %d 0 0 NaN\\n', {i + 1});",
                    "  else",
                    f"    y0 = {name}(X); y1 = prov.Evaluator(X, prov.Values);",
                    f"    fprintf(fid, 'PROV %d 1 %d %.17g\\n', {i + 1}, numel(prov.Values), max(abs(y1(:) - y0(:))));",
                    "  end",
                    "catch err",
                    f"  fprintf(fid, 'PROVERROR %d %s\\n', {i + 1}, strrep(err.message, char(10), ' '));",
                    "end",
                ]
        lines.append("fclose(fid);")
        proc = run_octave("\n".join(lines) + "\n", tmpd)
        out_file = tmpd / "out.txt"
        text = out_file.read_text(encoding="utf-8", errors="replace") if out_file.exists() else ""
    results: dict[str, Any] = {}
    prov_ok = prov_empty = prov_err = 0
    lines_out = text.splitlines()
    i = 0
    by_index = {k + 1: m for k, m in enumerate(models)}
    while i < len(lines_out):
        parts = lines_out[i].split(" ", 3)
        tag = parts[0]
        if tag == "MODEL":
            k, is_real, n = int(parts[1]), parts[2] == "1", int(parts[3])
            vals = np.array([float(v) for v in lines_out[i + 1 : i + 1 + n]])
            i += 1 + n
            m = by_index[k]
            res = _compare(np.broadcast_to(vals, (len(points),)) if n in (1, len(points)) else vals, m.reference)
            res["real"] = is_real
            res["passed"] = bool(res["passed"] and is_real and n in (1, len(points)))
            res["method"] = f"M-file run in GNU Octave on {len(points)} points and compared with the harness's values"
            results[m.file] = res
            continue
        if tag == "INFO":
            m = by_index[int(parts[1])]
            results.setdefault(m.file, {})["info_fitted_parameters"] = int(parts[3])
        elif tag == "ERROR":
            m = by_index[int(parts[1])]
            results[m.file] = {"passed": False, "error": parts[2] + (" " + parts[3] if len(parts) > 3 else "")}
        elif tag == "PROV":
            m = by_index[int(parts[1])]
            p = lines_out[i].split(" ")
            ok = p[2] == "1"
            results.setdefault(m.file, {})["srProvenance"] = (
                {"returned": True, "fitted_parameters": int(p[3]), "evaluator_max_abs_difference": float(p[4])} if ok else {"returned": False}
            )
            prov_ok += ok
            prov_empty += not ok
        elif tag == "PROVERROR":
            m = by_index[int(parts[1])]
            results.setdefault(m.file, {})["srProvenance"] = {"error": " ".join(parts[2:])}
            prov_err += 1
        i += 1
    for m in models:
        results.setdefault(m.file, {"passed": False, "error": "no output from Octave: " + (proc.stderr.strip()[-500:] or "unknown")})
        results[m.file].setdefault("passed", False)
    summary = None
    if provenance and fw is not None:
        summary = (f"{prov_ok} of {len(models)} files returned a provenance struct whose evaluator reproduces the model, {prov_empty} returned [] "
                   f"(no fitted parameter, or a declaration srProvenance did not accept), {prov_err} failed with an error; run with the "
                   "compatibility functions string and strlength on the path")
    return {"version": octave_version(), "models": results, "provenance_summary": summary, "framework": str(fw) if fw else None,
            "stderr": proc.stderr[-2000:], "returncode": proc.returncode}


FRAMEWORK_RTOL = 1e-6
"""Relative tolerance of the comparison of the errors that the Matlab framework computes in Octave with
the errors of the ASPIRE evaluation (the same model, integrator and data; the arithmetic of the two
implementations differs in the order of operations)."""


def run_framework_in_octave(folder: str | Path, models: Sequence[Any], datasets: Sequence[dict[str, Any]], *, form: str,
                            initialization: int) -> dict[str, Any]:
    """Run the Matlab framework on an export folder under Octave and compare its errors with ASPIRE's.

    ``models`` are the exported :class:`~aspire_sysid.export.matlab_export.MatlabModel` objects in
    ``HP/``; ``datasets`` lists ``{"name", "expected": {file: {"rmse", "samples"}}}`` per data set
    (the ASPIRE errors of each model on that data set: the pooled RMSE over the
    scored samples). The script runs ``startup``, ``srSplitDataVal``, ``srScanModels`` and
    ``srEvalHP`` (whose results are recorded, including their errors), and for every data set and
    model: ``srLoadData``; for a state-space data set ``srSimulate(model, 0, data)`` (offset 0, as in
    ASPIRE) and the error of the first regressor, for a static data set the model output against
    the target; the squared errors are summed over the samples after the first ``initialization``
    samples of each segment, which is the scoring interval of ASPIRE. ``srSimulate`` receives the
    data set without its ``form`` field, because its test ``data.form == "static"`` compares Matlab
    strings, which Octave cannot do for texts of different lengths; this changes nothing else.

    """
    folder = Path(folder).resolve()
    fw = framework_folder(folder)
    if fw is None:
        return {"ran": False, "reason": "the Matlab framework (matlab-framework) was not found"}
    with tempfile.TemporaryDirectory(prefix="aspire_octave_fw_") as tmp:
        tmpd = Path(tmp)
        compat = tmpd / "compat"
        compat.mkdir()
        for name, text in COMPAT_FUNCTIONS.items():
            (compat / name).write_text(text, encoding="ascii", newline="\n")
        L = [
            "fid = fopen('out.txt', 'w');",
            f"cd({_q(str(folder))});",
            "try, startup; fprintf(fid, 'STEP startup ok\\n'); catch err, fprintf(fid, 'STEP startup error %s\\n', strrep(err.message, char(10), ' ')); end",
            f"addpath({_q(str(fw))});",
            "try, srScanModels('HP'); fprintf(fid, 'STEP srScanModels ok\\n'); catch err, fprintf(fid, 'STEP srScanModels error %s\\n', strrep(err.message, char(10), ' ')); end",
            "try, srEvalHP('HP', 'IgnoreOffset', false, 'Print', false, 'Cache', false); fprintf(fid, 'STEP srEvalHP ok\\n'); catch err, fprintf(fid, 'STEP srEvalHP error %s\\n', strrep(err.message, char(10), ' ')); end",
            f"addpath({_q(str(compat))}, '-end');",
            "try, srScanModels('HP'); fprintf(fid, 'STEP srScanModels+compat ok\\n'); catch err, fprintf(fid, 'STEP srScanModels+compat error %s\\n', strrep(err.message, char(10), ' ')); end",
            "try, srEvalHP('HP', 'IgnoreOffset', false, 'Print', false, 'Cache', false); fprintf(fid, 'STEP srEvalHP+compat ok\\n'); catch err, fprintf(fid, 'STEP srEvalHP+compat error %s\\n', strrep(err.message, char(10), ' ')); end",
            "try, [tr, va] = splitData({}); v = srSplitDataVal(tr{1}); fprintf(fid, 'STEP srSplitDataVal ok %d\\n', numel(v)); catch err, fprintf(fid, 'STEP srSplitDataVal error %s\\n', strrep(err.message, char(10), ' ')); end",
        ]
        for i, d in enumerate(datasets):
            L += [
                "try",
                f"  S = srLoadData({_q(d['name'])});",
                f"  fprintf(fid, 'DATA %d ok %d %s\\n', {i + 1}, S.N, S.form);",
                "catch err",
                f"  fprintf(fid, 'DATA %d error %s\\n', {i + 1}, strrep(err.message, char(10), ' '));",
                "  S = [];",
                "end",
                "if ~isempty(S)",
                "  n = S.Dsamples(2:end); if sum(n) ~= S.N, n = S.N; end",
                "  mask = true(S.N, 1); st = cumsum([1; n(:)]);",
                f"  for q = 1:numel(n), mask(st(q):min(st(q) + {int(initialization)} - 1, S.N)) = false; end",
            ]
            for j, m in enumerate(models):
                L += [
                    "  try",
                    f"    h = srBindModel({_q(str((folder / m.file).resolve()))});",
                ]
                if form == "static":
                    L += ["    y = h(S.D(:, 1:end-1)); e = S.D(:, end) - y(:, 1); dv = 0;"]
                else:
                    L += ["    S2 = rmfield(S, 'form'); [xm, dv] = srSimulate(h, 0, S2); e = S.D(:, 1) - xm(:, 1);"]
                L += [
                    f"    fprintf(fid, 'ERR %d %d %.17g %d %d\\n', {i + 1}, {j + 1}, sum(e(mask).^2), nnz(mask), dv);",
                    "  catch err",
                    f"    fprintf(fid, 'ERRFAIL %d %d %s\\n', {i + 1}, {j + 1}, strrep(err.message, char(10), ' '));",
                    "  end",
                ]
            L.append("end")
        L.append("fclose(fid);")
        proc = run_octave("\n".join(L) + "\n", tmpd)
        text = (tmpd / "out.txt").read_text(encoding="utf-8", errors="replace") if (tmpd / "out.txt").exists() else ""
    steps: dict[str, str] = {}
    data_status: dict[str, str] = {}
    comparisons: list[dict[str, Any]] = []
    for line in text.splitlines():
        parts = line.split(" ")
        if parts[0] == "STEP":
            steps[parts[1]] = " ".join(parts[2:])
        elif parts[0] == "DATA":
            data_status[datasets[int(parts[1]) - 1]["name"]] = " ".join(parts[2:])
        elif parts[0] in ("ERR", "ERRFAIL"):
            d = datasets[int(parts[1]) - 1]
            m = models[int(parts[2]) - 1]
            exp = d["expected"].get(m.file) or {}
            row: dict[str, Any] = {"dataset": d["name"], "model": m.file, "label": m.label}
            if parts[0] == "ERRFAIL":
                row.update({"passed": False, "error": " ".join(parts[3:])})
            else:
                sse, cnt, dv = float(parts[3]), int(parts[4]), parts[5] == "1"
                rmse = math.sqrt(sse / cnt) if cnt > 0 else math.nan
                row.update({"framework_rmse": rmse, "framework_samples": cnt, "diverged": dv,
                            "aspire_rmse": exp.get("rmse"), "aspire_samples": exp.get("samples")})
                a = exp.get("rmse")
                if isinstance(a, (int, float)) and math.isfinite(rmse) and not dv:
                    row["relative_difference"] = abs(rmse - a) / max(abs(a), 1e-300)
                    row["passed"] = bool(row["relative_difference"] <= FRAMEWORK_RTOL and cnt == exp.get("samples"))
                else:
                    row["passed"] = None
                    row["note"] = "no finite ASPIRE error to compare (numerical failure or divergence)"
            comparisons.append(row)
    compared = [c for c in comparisons if c.get("passed") is not None]
    return {
        "ran": True,
        "framework": str(fw),
        "steps": steps,
        "datasets": data_status,
        "comparisons": comparisons,
        "passed": bool(compared) and all(c["passed"] for c in compared),
        "tolerance": FRAMEWORK_RTOL,
        "returncode": proc.returncode,
        "stderr_tail": proc.stderr[-1500:],
    }
