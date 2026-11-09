"""Probe of the installed software of the run environment, for the system prompt.

The run environment provides Python with numerical estimation and symbolic-regression tools,
and the harness records their versions. The harness fills ``{packages}`` of the system prompt
and adds the list of installed packages and their versions to the environment description from
the actual environment; it never states that a package is installed without checking. Where
available, the symbolic-regression tools are PySR, gplearn and PySINDy.

The probe runs a short script in the interpreter that the agent's shell uses (not necessarily
the harness's own interpreter) and reads the installed distributions and their versions with
``importlib.metadata``. A symbolic-regression package counts as installed only when its
distribution is present **and** its import module is found by ``importlib.util.find_spec``
(the module is not imported, because importing PySR starts its Julia backend). A failed probe
claims no package.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from .policy import shell_environment

__all__ = ["SR_PACKAGES", "EnvironmentProbe", "probe_environment", "PROBE_SCRIPT"]

SR_PACKAGES: tuple[tuple[str, str, str], ...] = (
    ("PySR", "pysr", "pysr"),
    ("gplearn", "gplearn", "gplearn"),
    ("PySINDy", "pysindy", "pysindy"),
)
"""Symbolic-regression packages named in the system prompt: display name, distribution name, module."""

PROBE_SCRIPT = r"""
import importlib.metadata as md, importlib.util as iu, json, sys
pk = {}
for d in md.distributions():
    try:
        name = d.metadata["Name"]
    except Exception:
        name = None
    if name:
        pk[name.lower().replace("_", "-")] = d.version
mods = {}
for m in sys.argv[1:]:
    try:
        mods[m] = iu.find_spec(m) is not None
    except Exception:
        mods[m] = False
print(json.dumps({"python": sys.version.split()[0], "executable": sys.executable, "packages": pk, "modules": mods}))
"""
"""The script run in the probed interpreter; its arguments are the module names to look for."""

Runner = Callable[[list[str], Mapping[str, str], float], "subprocess.CompletedProcess[str]"]


def _default_runner(argv: list[str], env: Mapping[str, str], timeout_s: float) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(argv, env=dict(env), capture_output=True, text=True, timeout=timeout_s, check=False)  # noqa: S603


@dataclass(frozen=True)
class EnvironmentProbe:
    """The result of the probe (Appendix A). ``error`` is set when the probe failed."""

    python_executable: str
    python_version: str | None
    packages: Mapping[str, str] = field(default_factory=dict)
    sr_packages: Mapping[str, str] = field(default_factory=dict)
    error: str | None = None

    def sr_packages_text(self) -> str:
        """The text that fills ``{packages}`` of the system prompt.

        The single fill rule of the harness (used by :func:`aspire_sysid.brief.prompts.packages_text`):
        the installed symbolic-regression packages in the order PySR, gplearn, PySINDy, each with its
        version, joined as ``"A 1.0"``, ``"A 1.0 and B 2.0"`` or ``"A 1.0, B 2.0 and C 3.0"``;
        ``"none"`` when the probe found none of them; ``"none that the harness could verify"`` when
        the probe failed. An uninstalled package is never named, not even as absent.
        """
        if self.error is not None:
            return "none that the harness could verify"
        order = [display for display, _, _ in SR_PACKAGES]
        items = [f"{n} {self.sr_packages[n]}" for n in order if n in self.sr_packages]
        items += [f"{n} {v}" for n, v in self.sr_packages.items() if n not in order]
        if not items:
            return "none"
        if len(items) == 1:
            return items[0]
        return ", ".join(items[:-1]) + " and " + items[-1]

    def package_lines(self) -> list[str]:
        """``"name version"`` for every installed distribution, sorted by name."""
        return [f"{n} {v}" for n, v in sorted(self.packages.items())]

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the record (versions recorded)."""
        return {
            "python_executable": self.python_executable,
            "python_version": self.python_version,
            "packages": dict(sorted(self.packages.items())),
            "sr_packages": dict(self.sr_packages),
            "error": self.error,
        }


def probe_environment(
    python_executable: str | Path | None = None,
    *,
    runner: Runner | None = None,
    timeout_s: float = 120.0,
) -> EnvironmentProbe:
    """Probe the installed packages of ``python_executable`` (default: the harness's interpreter).

    The run must pass the same interpreter to :func:`run_round`
    (``python_executable``), whose folder is first on the shell's ``PATH``; ``run_round``
    refuses a probe of another interpreter. ``runner(argv, env, timeout_s)`` runs the probe script and returns a
    completed process (injectable for tests). The probe runs with the shell environment of the
    network filter of the policy module (credentials removed, no network).
    """
    exe = str(python_executable or sys.executable)
    run = runner or _default_runner
    argv = [exe, "-c", PROBE_SCRIPT, *(m for _, _, m in SR_PACKAGES)]
    env = shell_environment(network_filter=True, python_executable=exe)
    try:
        proc = run(argv, env, timeout_s)
    except (OSError, subprocess.SubprocessError) as exc:
        return EnvironmentProbe(exe, None, error=f"the probe could not run: {type(exc).__name__}: {exc}")
    if proc.returncode != 0:
        return EnvironmentProbe(exe, None, error=f"the probe ended with exit status {proc.returncode}: {proc.stderr.strip()[:2000]}")
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
        packages = {str(k): str(v) for k, v in dict(data["packages"]).items()}
        modules = {str(k): bool(v) for k, v in dict(data["modules"]).items()}
        version = str(data["python"])
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        return EnvironmentProbe(exe, None, error=f"the probe output could not be read: {exc}")
    sr: dict[str, str] = {}
    for display, dist, module in SR_PACKAGES:
        if dist in packages and modules.get(module) is True:
            sr[display] = packages[dist]
    return EnvironmentProbe(exe, version, packages=packages, sr_packages=sr)
