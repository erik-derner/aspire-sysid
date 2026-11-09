"""The API key of a real run: from the environment or a local ``.env`` file.

For a real run the experiment runner takes the key from the harness's environment or, when it is
not set there, from a file ``.env`` (lines ``NAME=value``; ``#`` starts a comment; optional quotes)
searched in the experiment folder, the current folder and the repository root, in that order
(:func:`take_api_key`). The key never stays in a process environment: a key found in the
environment is removed from the grid process's environment, a key from ``.env`` is never put into
it, the run workers are started without it (:func:`worker_environment`) and receive it through
their standard input, and the provider object receives it as an argument
(``make_provider(model, api_key=...)``). The Windows re-launch under the renamed interpreter
(:mod:`aspire_sysid.experiment.host`) removes the key variables from the environment of the
re-launched process and passes the keys through its standard input (:func:`accept_passed_keys`).
So the start-time environment (``/proc/<pid>/environ`` on Linux) of no worker, no agent command
and no inspection subprocess contains the key. **Exception:** a key that was already in the
environment of the grid process when it started stays in that process's start-time environment
(``/proc/<grid pid>/environ``), which removing it from ``os.environ`` does not change; the key in
a ``.env`` file avoids this. The file ``.env`` is never committed (``.gitignore`` lists it) and
the key is never written to a record.

**Remaining risk.** The key is in the memory of the grid process and of each worker. A program
of the agent runs as the same operating-system user; where the system permits a process to read
the memory of another process of the same user (for example Linux with
``kernel.yama.ptrace_scope = 0``, or a debugger interface on Windows), such a program could read
it. Only a separate operating-system user for the agent's commands removes this risk.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Mapping

from ..paths import HARNESS_DIR

__all__ = [
    "KEY_VARIABLES", "MissingKeyError", "read_dotenv", "dotenv_candidates", "take_api_key", "worker_environment",
    "accept_passed_keys", "passed_keys_of",
]

_PASSED: dict[str, str] = {}
"""Keys received from the launching process through standard input (Windows re-launch)."""

KEY_VARIABLES: Mapping[str, str] = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
"""Environment variable of the API key of each vendor (plain model APIs)."""


class MissingKeyError(RuntimeError):
    """A real run was requested without an API key. """


def _dotenv_text(path: str | Path) -> str:
    """The text of a ``.env`` file: UTF-8 with or without a byte-order mark, or UTF-16 with one.

    Editors and shells on Windows write these forms (the output redirection ``>`` of Windows
    PowerShell 5.1 writes UTF-16 or UTF-8, depending on its settings, each with a byte-order mark).
    Raises :class:`UnicodeDecodeError` for any other encoding."""
    data = Path(path).read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


def read_dotenv(path: str | Path) -> dict[str, str]:
    """The ``NAME=value`` lines of a ``.env`` file. Blank lines and ``#`` comments
    are skipped; ``export NAME=value`` is accepted; surrounding single or double quotes are removed.
    The file is UTF-8, with or without a byte-order mark, or UTF-16 with one. """
    out: dict[str, str] = {}
    for raw in _dotenv_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if name:
            out[name] = value
    return out


def dotenv_candidates(experiment_dir: str | Path | None = None) -> list[Path]:
    """The ``.env`` files searched, in order: experiment folder, current folder, repository root. """
    folders: list[Path] = []
    if experiment_dir is not None:
        folders.append(Path(experiment_dir))
    folders += [Path.cwd(), HARNESS_DIR.parent]
    seen: list[Path] = []
    for f in folders:
        p = (f / ".env").resolve()
        if p not in seen:
            seen.append(p)
    return seen


def take_api_key(vendor: str, *, experiment_dir: str | Path | None = None, candidates: Iterable[Path] | None = None,
                 environ: dict[str, str] | None = None) -> tuple[str, str]:
    """Take the vendor's API key for a real run; return ``(key, source)``.

 The key is read from the environment variable of the vendor
    and then **removed from that environment**, or, when the variable is not set, read from the
    first ``.env`` file that holds it, without being put into the environment. ``source`` is
    ``"environment"`` or the path of the file. Raises :class:`MissingKeyError` when neither holds
    a non-empty key, or when a ``.env`` file is not text in an accepted encoding
    (:func:`read_dotenv`), so that a real run never starts without one. The caller hands the key to the
    provider object (``make_provider(..., api_key=key)``) or to a worker through its standard
    input; it is never printed or recorded.
    """
    env = os.environ if environ is None else environ
    var = KEY_VARIABLES.get(vendor)
    if var is None:
        raise MissingKeyError(f"no API key variable is known for the vendor {vendor!r}")
    if environ is None and _PASSED.get(var):
        return _PASSED[var], "launcher"
    value = env.get(var, "").strip()
    if value:
        env.pop(var, None)
        return value, "environment"
    files = list(candidates) if candidates is not None else dotenv_candidates(experiment_dir)
    for p in files:
        if p.is_file():
            try:
                value = read_dotenv(p).get(var, "").strip()
            except UnicodeDecodeError as exc:
                raise MissingKeyError(
                    f"the file {p} cannot be read as text in UTF-8 (or in UTF-16 with a byte-order mark); "
                    "save it in UTF-8 with a text editor"
                ) from exc
            if value:
                return value, str(p)
    searched = ", ".join(str(p) for p in files)
    raise MissingKeyError(
        f"{var} is not set in the environment and no .env file holds it (searched: {searched}); "
        "a real run needs the key; a dry run (--dry-run) does not"
    )


def worker_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """The environment of a run worker: the grid's environment without any API key variable.


    """
    src = os.environ if environ is None else environ
    return {k: v for k, v in src.items() if k not in KEY_VARIABLES.values()}


def passed_keys_of(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """The API key variables present in ``environ`` (default: this process), to be passed to a
    re-launched process through its standard input. """
    src = os.environ if environ is None else environ
    return {k: src[k] for k in KEY_VARIABLES.values() if src.get(k, "").strip()}


def accept_passed_keys(keys: Mapping[str, str]) -> None:
    """Keep the keys received from the launching process for :func:`take_api_key` (never in the
    environment). """
    _PASSED.update({k: v for k, v in keys.items() if k in KEY_VARIABLES.values() and v})
