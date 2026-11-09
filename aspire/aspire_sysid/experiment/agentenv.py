"""The interpreter of the agent's shell: a separate virtual environment without the harness package.

The run environment provides Python with numerical estimation and symbolic-regression tools, and
the harness records their versions; the environment description in the system prompt lists the
installed packages from the actual environment. The harness package can open the
sealed task store; an interpreter in which ``import aspire_sysid`` succeeds gives
the agent's programs that route. Real runs should therefore give the agent an interpreter of a
separate virtual environment in which the harness is not installed, placed outside the repository.

:func:`create_agent_environment` creates such an environment (``python -m venv``) and installs the
requested distributions with ``pip``; :func:`inspect_agent_interpreter` states whether an interpreter
exists, runs, and can import the harness package. The command line is ``aspire experiment agent-env
<folder>``; ``aspire/README.md`` ("Experiments") gives the steps for a local set-up.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ..paths import HARNESS_DIR

__all__ = [
    "DEFAULT_AGENT_PACKAGES",
    "STAMP_FILE",
    "AgentInterpreter",
    "AgentEnvironmentError",
    "venv_python",
    "inspect_agent_interpreter",
    "create_agent_environment",
]

DEFAULT_AGENT_PACKAGES: tuple[str, ...] = (
    "numpy", "scipy", "sympy", "pandas", "matplotlib", "scikit-learn", "gplearn", "pysindy",
)
"""Distributions installed by default into the agent's environment: numerical estimation (NumPy,
SciPy, pandas, scikit-learn), symbolic mathematics (SymPy, also needed by ``check_submission.py``),
plots (Matplotlib) and two symbolic-regression packages named in the system prompt (gplearn,
PySINDy). PySR is not in the default list because it needs a Julia installation; add it with
``--package pysr`` where Julia is available."""

STAMP_FILE = "aspire-agent-env.json"
"""File in the environment folder that records how the environment was created."""

_CHECK = (
    "import importlib.util, json, sys; "
    "print(json.dumps({'python': sys.version.split()[0], 'executable': sys.executable, "
    "'harness_importable': importlib.util.find_spec('aspire_sysid') is not None}))"
)


class AgentEnvironmentError(RuntimeError):
    """The agent's environment could not be created or its interpreter does not run. """


@dataclass(frozen=True)
class AgentInterpreter:
    """The interpreter of the agent's shell as the harness found it."""

    executable: str
    is_harness_interpreter: bool
    runs: bool
    python_version: str | None
    harness_importable: bool | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the run record."""
        return {
            "executable": self.executable,
            "is_harness_interpreter": self.is_harness_interpreter,
            "runs": self.runs,
            "python_version": self.python_version,
            "harness_importable": self.harness_importable,
            "error": self.error,
            "note": (
                "the harness package can be imported from the agent's interpreter; a program of the agent could use it to open the task store"
                if self.harness_importable
                else "the harness package cannot be imported from the agent's interpreter"
                if self.harness_importable is False
                else "not determined"
            ),
        }


AGENT_ENV_VARIABLE = "ASPIRE_AGENT_ENV"
"""Environment variable that names the folder of the agent's environment in place of the default one."""


def default_agent_env_dir() -> Path:
    """The default folder of the agent's environment on this computer, outside every repository:
    ``%LOCALAPPDATA%/aspire/agent-env`` on Windows, ``~/.local/share/aspire/agent-env`` elsewhere.
    ``aspire experiment agent-env`` creates it there when no folder is named, and ``aspire session``
    uses its interpreter when ``--python`` is not given and the environment exists. The environment
    variable ``ASPIRE_AGENT_ENV`` names another folder. """
    import os

    if os.environ.get(AGENT_ENV_VARIABLE):
        return Path(os.environ[AGENT_ENV_VARIABLE])
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "aspire" / "agent-env"


def venv_python(env_dir: str | Path) -> Path:
    """The interpreter of the virtual environment ``env_dir`` (``Scripts/python.exe`` on Windows, ``bin/python`` otherwise). """
    d = Path(env_dir)
    return d / "Scripts" / "python.exe" if sys.platform == "win32" else d / "bin" / "python"


def _clean_env() -> dict[str, str]:
    from .credentials import KEY_VARIABLES

    drop = {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "VIRTUAL_ENV", *KEY_VARIABLES.values()}
    env = {k: v for k, v in os.environ.items() if k not in drop}
    return env


def inspect_agent_interpreter(executable: str | Path | None) -> AgentInterpreter:
    """Run ``executable`` and report its version and whether ``aspire_sysid`` is importable.

 ``None`` means the harness's own interpreter. The check runs with
    ``PYTHONPATH`` removed and in a neutral folder (the parent of the harness repository is never the
    current folder), as the agent's shell would; an editable installation of the harness is still
    found, which is the case this check exists for.
    """
    exe = str(executable or sys.executable)
    # compared without resolving links: the interpreter of a virtual environment is often a link
    # to the base interpreter, but it runs with the environment's own packages
    same = os.path.normcase(os.path.abspath(exe)) == os.path.normcase(os.path.abspath(sys.executable))
    try:
        proc = subprocess.run([exe, "-c", _CHECK], capture_output=True, text=True, timeout=120, env=_clean_env(),
                              cwd=str(Path(exe).resolve().parent), check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return AgentInterpreter(exe, same, False, None, None, f"{type(exc).__name__}: {exc}")
    if proc.returncode != 0:
        return AgentInterpreter(exe, same, False, None, None, f"exit status {proc.returncode}: {proc.stderr.strip()[:500]}")
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        return AgentInterpreter(exe, same, False, None, None, f"unreadable output: {exc}")
    return AgentInterpreter(exe, same, True, str(data["python"]), bool(data["harness_importable"]))


def create_agent_environment(
    env_dir: str | Path,
    packages: Sequence[str] = DEFAULT_AGENT_PACKAGES,
    *,
    python: str | Path | None = None,
    with_pip: bool = True,
    runner: Any = None,
) -> AgentInterpreter:
    """Create a virtual environment for the agent's shell and install ``packages``.

    ``env_dir`` must not exist or be empty and must lie outside the
    repository of the harness (an interpreter inside the repository would make the command filter's
    protection of the repository and the interpreter's allowed folders overlap). ``python`` is the
    base interpreter (default: the harness's). The environment receives no harness package. Writes
    :data:`STAMP_FILE` with the base interpreter, the requested packages and the installed versions.
    Returns the inspection of the new interpreter; raises :class:`AgentEnvironmentError` when a step
    fails or the harness package is importable from it. ``runner(argv)`` replaces
    :func:`subprocess.run` (tests).
    """
    d = Path(env_dir).resolve()
    repo = HARNESS_DIR.parent.resolve()
    try:
        d.relative_to(repo)
        raise AgentEnvironmentError(f"{d} lies inside the repository {repo}; create the agent's environment outside it")
    except ValueError:
        pass
    if d.exists() and any(d.iterdir()):
        raise AgentEnvironmentError(f"{d} exists and is not empty")
    run = runner or (lambda argv: subprocess.run(argv, capture_output=True, text=True, env=_clean_env(), check=False))
    base = str(python or sys.executable)
    argv = [base, "-m", "venv", str(d)] + ([] if with_pip else ["--without-pip"])
    proc = run(argv)
    if proc.returncode != 0:
        raise AgentEnvironmentError(f"{' '.join(argv)} failed: {proc.stderr.strip()[:2000]}")
    exe = venv_python(d)
    if packages:
        if not with_pip:
            raise AgentEnvironmentError("packages cannot be installed into an environment created without pip")
        argv = [str(exe), "-m", "pip", "install", *packages]
        proc = run(argv)
        if proc.returncode != 0:
            raise AgentEnvironmentError(f"{' '.join(argv)} failed: {proc.stderr.strip()[-2000:]}")
    info = inspect_agent_interpreter(exe)
    if not info.runs:
        raise AgentEnvironmentError(f"the new interpreter {exe} does not run: {info.error}")
    if info.harness_importable:
        raise AgentEnvironmentError(f"the harness package is importable from {exe}; the agent's environment must not contain it")
    stamp = {
        "created_by": "aspire experiment agent-env",
        "base_python": base,
        "python": info.python_version,
        "requested_packages": list(packages),
        "harness_importable": info.harness_importable,
    }
    (d / STAMP_FILE).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8", newline="\n")
    return info
