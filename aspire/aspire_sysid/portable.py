"""Machine-independent paths in the files that the harness writes.

Run folders, exports, logs and aggregations are meant to be shared with the repository. They must
not name the folders of the computer that produced them: the absolute location of the repository
checkout, the home folder of the user, or the system temporary folder. Every path that the harness
writes into such a file passes through this module:

- a path inside the **repository** (the folder that holds ``aspire/``) is written relative to the
  repository root, with ``/`` as separator, for example ``tasks/turtlebot`` or
  ``aspire/configs/prices.yaml``; the repository root itself is written ``.``;
- a path inside the **system temporary folder** (:func:`tempfile.gettempdir`) is written with the
  placeholder ``<tmp>``, for example ``<tmp>/aspire-runs/3f2a.../workspace``;
- a path inside the **home folder** is written with ``~`` on POSIX systems and ``%USERPROFILE%``
  on Windows;
- every other path (for example ``/usr/bin/python3``) is written unchanged.

When prefixes are nested (a temporary folder inside the home folder on Windows, a repository inside
the home folder), the longest matching prefix applies. :func:`portable_text` applies the same
replacement to every occurrence inside a text (a Markdown line, an error message);
:func:`portable_data` applies it to every string of a JSON-like structure. :func:`local_path` is
the inverse: it turns a recorded path back into a path of this computer (a relative path is
resolved against the repository root, the placeholders against this computer's folders), so that
``aspire record verify``, the exports and ``--resume`` work on records written in either form.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .paths import HARNESS_DIR

__all__ = ["TMP_PLACEHOLDER", "PathContext", "default_context", "portable_path", "portable_text", "portable_data", "local_path"]

TMP_PLACEHOLDER = "<tmp>"
"""Placeholder of the system temporary folder in recorded paths."""


@dataclass(frozen=True)
class PathContext:
    """The folders that are replaced, and the system convention.

    ``windows`` selects backslash separators, case-insensitive matching and ``%USERPROFILE%``.
    Tests construct contexts for other systems; the harness uses :func:`default_context`.
    """

    repo: str
    home: str | None
    temp: str | None
    windows: bool = False

    @property
    def home_placeholder(self) -> str:
        """``%USERPROFILE%`` on Windows, ``~`` elsewhere."""
        return "%USERPROFILE%" if self.windows else "~"

    def _variants(self, folder: str | None) -> list[str]:
        if not folder:
            return []
        out = {folder}
        if not self.windows:
            try:
                out.add(os.path.realpath(folder))
            except OSError:
                pass
            out.add(os.path.abspath(folder))
        else:
            out.add(folder.replace("/", "\\"))
            out.add(folder.replace("\\", "/"))
        return [v.rstrip("/\\") for v in out if v and v.rstrip("/\\")]

    def prefixes(self) -> list[tuple[str, str]]:
        """(prefix, replacement) pairs, longest prefix first; replacement ``""`` means relative."""
        pairs: list[tuple[str, str]] = []
        for v in self._variants(self.repo):
            pairs.append((v, ""))
        for v in self._variants(self.temp):
            pairs.append((v, TMP_PLACEHOLDER))
        for v in self._variants(self.home):
            pairs.append((v, self.home_placeholder))
        # among equal prefixes the first category (repository, then temporary folder) wins
        unique: dict[str, tuple[str, str]] = {}
        for p, r in pairs:
            unique.setdefault(p.lower() if self.windows else p, (p, r))
        # the longest prefix wins where folders are nested
        return sorted(unique.values(), key=lambda pr: -len(pr[0]))


def default_context() -> PathContext:
    """The context of this computer: the repository that holds this harness, ``Path.home`` and
    :func:`tempfile.gettempdir`. """
    try:
        home: str | None = str(Path.home())
    except (RuntimeError, KeyError, OSError):
        home = None
    return PathContext(repo=str(HARNESS_DIR.parent), home=home, temp=tempfile.gettempdir(), windows=os.name == "nt")


_SEPS = "/\\"


def _pattern(ctx: PathContext) -> tuple[re.Pattern[str], dict[str, str]]:
    pairs = ctx.prefixes()
    table = {(p.lower() if ctx.windows else p): r for p, r in pairs}
    alts = "|".join(re.escape(p) for p, _ in pairs)
    # a prefix counts only as a whole folder: followed by a separator, or by no path character
    pat = re.compile(rf"(?:{alts})(?=[{re.escape(_SEPS)}]|$|[^\w.\-])", re.IGNORECASE if ctx.windows else 0)
    return pat, table


def portable_text(text: str, ctx: PathContext | None = None) -> str:
    """Replace every occurrence of the repository, temporary and home folders in ``text`` (module
    docstring). A repository path becomes relative with ``/`` separators. """
    ctx = ctx or default_context()
    if not text or not ctx.prefixes():
        return text
    pat, table = _pattern(ctx)
    out: list[str] = []
    pos = 0
    for m in pat.finditer(text):
        repl = table[m.group(0).lower() if ctx.windows else m.group(0)]
        out.append(text[pos:m.start()])
        end = m.end()
        if repl == "":
            # repository-relative: drop the separator and write the rest of the path with "/"
            if end < len(text) and text[end] in _SEPS:
                end += 1
                tail = re.match(r"[^\s'\"`;,)\]}<>|]*", text[end:])
                rest = tail.group(0) if tail else ""
                out.append(rest.replace("\\", "/") if ctx.windows else rest)
                end += len(rest)
            else:
                out.append(".")
        else:
            out.append(repl)
        pos = end
    out.append(text[pos:])
    return "".join(out)


def portable_path(path: str | os.PathLike[str] | None, ctx: PathContext | None = None) -> str | None:
    """The recorded form of one path (module docstring); ``None`` stays ``None``. """
    if path is None:
        return None
    return portable_text(os.fspath(path), ctx)


def portable_data(obj: Any, ctx: PathContext | None = None) -> Any:
    """``obj`` with :func:`portable_text` applied to every string (keys included) of dictionaries,
    lists and tuples; other values unchanged. """
    ctx = ctx or default_context()
    if isinstance(obj, str):
        return portable_text(obj, ctx)
    if isinstance(obj, os.PathLike):
        return portable_text(os.fspath(obj), ctx)
    if isinstance(obj, dict):
        return {(portable_text(k, ctx) if isinstance(k, str) else k): portable_data(v, ctx) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [portable_data(v, ctx) for v in obj]
    return obj


def local_path(recorded: str | os.PathLike[str], ctx: PathContext | None = None) -> Path:
    """The path of this computer for a recorded path (the inverse of :func:`portable_path`): a
    relative path is resolved against the repository root, ``<tmp>`` against the temporary folder,
    ``~`` and ``%USERPROFILE%`` against the home folder; an absolute path is returned as it is.
"""
    ctx = ctx or default_context()
    s = os.fspath(recorded)
    for ph, base in ((TMP_PLACEHOLDER, ctx.temp), ("%USERPROFILE%", ctx.home), ("~", ctx.home)):
        if base and (s == ph or (s.startswith(ph) and s[len(ph)] in _SEPS)):
            return Path(base + s[len(ph):])
    pure = PureWindowsPath(s) if ctx.windows else PurePosixPath(s)
    if pure.is_absolute() or (ctx.windows and pure.drive):
        return Path(s)
    return Path(ctx.repo) / s
