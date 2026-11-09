"""Command policy of ``run_shell``: sealing filter, network filter and shell environment.

No tool permits access to sealed data, reference expressions or withheld results. The one tool
configuration includes web access and package installation, so the network filter
below is not applied to the agent's shell; the harness uses it for its own environment probe
(:mod:`aspire_sysid.agent.probe`). The limit of this policy is stated in the documentation.

This module provides

* :class:`ShellPolicy.check`, which returns the reason for refusing a command, or ``None``:

  - **sealing filter** (always): a command is refused when it names the task
    store, the repository that holds the harness, a path outside the working directory, the
    root folder, a previous or parent folder, a ``git`` option that selects another repository,
    or the harness package ``aspire_sysid`` (details: :meth:`ShellPolicy.sealing_violation`);
  - **network filter** (only when requested; not for the agent's shell): a command is refused when a command position names
    a network program (``curl``, ``wget``, ``ssh``, ...), a package installer (``pip install``,
    ``conda install``, ...) or a remote ``git`` operation, when it contains ``python -m pip``, a
    PowerShell web command or a URL, or when its inline code imports or calls a network module
    (:data:`COMMAND_RULES`, :data:`CODE_RULES`). The scripts in the working directory that the
    command names are checked as well: shell scripts (``.sh``, ``.bash``, ``.ps1``, ``.bat``,
    ``.cmd``) with all rules, other scripts (``fit.py``, ...) with the code rules only
    (:func:`script_network_violation`);
  - **host-process filter** (always): a command
    is refused when it ends processes by the name of the Python interpreter or of the harness, or
    all processes of the user (:data:`HOST_PROCESS_RULES`), because the grid runner and the run
    workers run as the same operating-system user;

* :func:`shell_environment`, the environment of every shell command: variables that may hold
  credentials are removed (API keys, tokens, secrets, passwords, the ``GIT_*`` group), ``git``
  is confined to the working directory by ``GIT_CEILING_DIRECTORIES``, the interpreter's folder
  is first on ``PATH``, and with the network filter the proxy variables point to an unreachable address
  and ``pip`` is configured without a package index.

Limit of the policy (stated in ``aspire/README.md``, "Tool policy and its limits"): the filters
read the command text, and scripts named in a command are checked for network use only, never
for paths. A program can still open network connections or any path the operating-system user
can read by means the text does not reveal (a module imported by a script, a path assembled at
run time, a symbolic link created by a program, direct access to a repository's object store).
The post-run leak scan (:mod:`aspire_sysid.evaluate.leaks`) finds sealed values written to the
transcript or the files, but not test data used silently. Full isolation requires an
operating-system sandbox or a separate operating-system user without read access to ``tasks/``.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable, Mapping

from ..paths import HARNESS_DIR

__all__ = [
    "UNREACHABLE_PROXY",
    "NETWORK_RULES",
    "SEALING_WORDS",
    "ShellPolicy",
    "network_violation",
    "script_network_violation",
    "HOST_PROCESS_RULES",
    "host_process_violation",
    "host_code_violation",
    "HOST_CODE_RULES",
    "COMMAND_RULES",
    "CODE_RULES",
    "is_credential_variable",
    "shell_environment",
    "interpreter_prefixes",
]

UNREACHABLE_PROXY = "http://127.0.0.1:9"
"""Proxy address of a shell environment with the network filter: the discard port of the local host, where no
proxy listens, so that a program that honours the proxy variables cannot reach the network."""

_I = re.IGNORECASE

# A command position in shell text: the start, or after ; & | ( ` $( or a newline, optionally
# preceded by wrappers (sudo, env VAR=x, nohup, exec, time, xargs, command) and a folder path.
_CMD = (
    r"(?:^|[;&|(`\n]|\$\()\s*"
    r"(?:(?:sudo|env|nohup|exec|time|xargs|command|builtin|stdbuf|timeout\s+\S+)\s+(?:-\S+\s+|\w+=\S*\s+)*)*"
    r"(?:\S*[/\\])?"
)


def _at_command(names: str, rest: str = r"(?=$|[\s;&|)`])") -> re.Pattern[str]:
    return re.compile(_CMD + r"(?:" + names + r")(?:\.exe)?" + rest, re.IGNORECASE)


COMMAND_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (_at_command(r"curl|wget|aria2c|lynx|w3m|links|elinks|httpie|http|https"), "a program that downloads from the network"),
    (_at_command(r"ssh|scp|sftp|ftp|telnet|rsync|nc|ncat|netcat|socat|nslookup|dig|host|ping|traceroute"), "a network program"),
    (_at_command(r"pip3?(?:\.\d+)?", r"\s+(?:install|download|wheel|index|search)\b"), "package installation"),
    (_at_command(r"pipx|easy_install|poetry|pdm|hatch|npm|npx|yarn|pnpm"), "a package manager"),
    (_at_command(r"uv", r"\s+(?:pip|add|sync|tool|venv|run\s+--with)\b"), "package installation (uv)"),
    (_at_command(r"conda|mamba|micromamba", r"\s+(?:install|create|update|env)\b"), "package installation (conda)"),
    (_at_command(r"apt|apt-get|yum|dnf|brew|choco|winget|scoop", r"\s+install\b"), "package installation"),
    (_at_command(r"git", r"\s+(?:\S+\s+)*?(?:clone|fetch|pull|push|remote|submodule|ls-remote)\b"), "a remote git operation"),
    (_at_command(r"iwr|irm|bitsadmin|start-bitstransfer|invoke-webrequest|invoke-restmethod"), "a PowerShell web command"),
    (
        re.compile(r"\b(?:invoke-webrequest|invoke-restmethod|start-bitstransfer)\b|net\.webclient|system\.net\.http|certutil\b.*-urlcache", re.IGNORECASE),
        "a PowerShell or Windows web client",
    ),
    (re.compile(r"-m\s+pip\b"), "package installation (python -m pip)"),
    (re.compile(r"\b(?:https?|ftp|wss?)://", re.IGNORECASE), "a URL"),
)
"""Rules of the network filter for shell command text.
Program names count only in a command position, so that an argument or a word inside quoted
code (``grep links notes.txt``) is not taken for a program."""

_NET_MODULES = r"(?:urllib3?|urllib\.request|requests|httpx|aiohttp|http\.client|http\.server|socket|socketserver|ftplib|smtplib|telnetlib|paramiko|websockets?|pycurl|xmlrpc)"

_NET_PROGRAMS = r"curl|wget|aria2c|ssh|scp|sftp|ftp|telnet|rsync|nc|ncat|netcat|socat|pip|pip3|conda|npm|pipx"

CODE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?:^|[;\"'])\s*(?:import|from)\s+" + _NET_MODULES + r"\b", re.MULTILINE), "a Python network module"),
    (
        re.compile(r"\burllib\.request\b|\bhttp\.client\b|\bsocket\.(?:socket|create_connection)\b|__import__\(\s*[\"'](?:socket|urllib|requests|http)"),
        "a Python network module",
    ),
    (
        re.compile(r"[\[(]\s*[rbfu]?[\"'](?:\S*/)?(?:" + _NET_PROGRAMS + r")[\"']"),
        "a network program or installer as the first element of an argument list",
    ),
    (
        re.compile(
            r"\b(?:system|popen|run|call|check_output|check_call|Popen|getoutput|getstatusoutput|spawn\w*|exec\w*)"
            r"\(\s*\[?\s*[rbfu]?[\"'](?:\S*/)?(?:" + _NET_PROGRAMS + r")\b"
        ),
        "a network program or installer called from code",
    ),
    (
        re.compile(r"[\"']-m[\"']\s*,\s*[\"']pip[\"']|\bpip3?\s+install\b|\bgit\s+(?:clone|fetch|pull|push|ls-remote)\b"),
        "package installation or a remote git operation called from code",
    ),
    (re.compile(r"/dev/(?:tcp|udp)/"), "a network device"),
    (re.compile(r"\bPkg\.add\b|\binstall\.packages\b|\bdownload\.file\b"), "package installation or download (Julia, R)"),
)
"""Rules of the network filter for program code: case-sensitive imports and calls of
network modules, and network programs or installers as the first element of an argument list
(``subprocess.run(["curl", ...])``) or at the start of a string passed to a process call
(``os.system("curl ...")``). They apply to the scripts a command names and to the command
text itself (inline ``python -c`` code); ordinary words in comments and strings (``links``,
``curl of the surface``) do not match."""

NETWORK_RULES: tuple[tuple[re.Pattern[str], str], ...] = COMMAND_RULES + CODE_RULES
"""All rules of the network filter applied to a shell command text."""

SEALING_WORDS: tuple[str, ...] = ("aspire_sysid",)
"""Words that a command may not contain: the harness package, which can open the sealed
store."""

_SCRIPT_TOKEN = re.compile(r"[\w./\\-]+\.(py|sh|bash|ps1|r|jl|bat|cmd|ipynb)\b", _I)
_POSIX_ABS = re.compile(r"(?<![\w.~/\\$-])(/[^\s'\"`;|&<>(),=:]*)")
_WIN_ABS = re.compile(r"(?<![\w])([A-Za-z]:[\\/][^\s'\"`;|&<>(),=]*)")
_UNC = re.compile(r"(^|[\s'\"=(])\\\\[\w.$-]+")
_PARENT = re.compile(r"(?<![.\w])\.\.(?=[/\\]|$|[\s'\"`;|&<>(){},:])")
_HOME = re.compile(r"\$\{?HOME\b|%USERPROFILE%|%HOMEPATH%|%HOMEDRIVE%|\$env:", _I)
_TILDE = re.compile(r"(?<![\w~])~[\w.-]*(?=[/\\]|$|[\s;|&<>)])")
_LONE_ROOT = re.compile(r"(?:^|(?<=[\s=]))/(?=$|[\s;|&)])")
# Windows (cmd.exe): a path rooted at the current drive without a drive letter (\Users\...), the
# lone root "\", and %NAME% variable references
_WIN_ROOTED = re.compile(r"(?<![\w.~/\\$:-])(\\(?!\\)[^\s'\"`;|&<>(),=:]*)")
_WIN_LONE_ROOT = re.compile(r"(?:^|(?<=[\s=]))\\(?=$|[\s;|&)])")
_WIN_VARIABLE = re.compile(r"%([A-Za-z_][\w()]*)%")
_GLOB_OR_VARIABLE = re.compile(r"[*?\[\]{}$`~]")
_DIRECTORY_TRICKS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bcd\s+-(?=$|[\s;|&)])"), "'cd -' (the previous folder)"),
    (re.compile(r"\b(OLDPWD|pushd|popd)\b", _I), "a previous-folder variable or folder stack"),
    (re.compile(r"\$\{[^}]*[%#/:^,][^}]*\}"), "a parameter expansion that edits a value"),
    (re.compile(r"(dirname|\.parent\b|os\.path\.split|parents\[).*?(pwd|getcwd|cwd\(\))|(pwd|getcwd|cwd\(\)).*?(dirname|\.parent\b|os\.path\.split|parents\[)", _I),
     "the parent of the current folder"),
)
_GIT = re.compile(r"\bgit\b", _I)
_GIT_ESCAPES = re.compile(r"(^|\s)(-C\b|--git-dir\b|--work-tree\b|--namespace\b|--exec-path\b|--super-prefix\b)|\bGIT_[A-Z_]+=", _I)
_QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")


def _unquoted(command: str) -> str:
    """The command with its quoted parts replaced by a space (the shell expands only unquoted text)."""
    return _QUOTED.sub(" ", command)


_SCRIPT_MAX_BYTES = 2_000_000


def network_violation(text: str) -> str | None:
    """The reason why the shell command ``text`` indicates network use or installation, or ``None``.

    The network filter of the module docstring (no web access, no package installation). Applies
    :data:`COMMAND_RULES` (program names in command positions, URLs) and :data:`CODE_RULES`
    (inline code).
    """
    for pattern, reason in NETWORK_RULES:
        m = pattern.search(text)
        if m:
            return f"{reason} ({m.group(0).strip()!r})"
    return None


_PROCESS_NAMES = r"(?<![\w.-])(?:python[\d.]*w?|py|pypy[\d.]*|aspire[\w-]*|worker|experiment)(?:\.exe)?(?![\w-])"
_KILL_WORDS = r"\b(?:kill|pkill|killall|taskkill|stop-process|spps)\b"
_LISTING_WORDS = r"\b(?:pgrep|pidof|ps|tasklist|get-process|gps)\b"
_PARENT_WORDS = r"(?:\$\{?PPID\b|\bgetppid\s*\()"

HOST_PROCESS_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (_at_command(r"killall5"), "a command that ends all processes"),
    (_at_command(r"kill", r"\s+(?:(?:-\S+|[A-Z]+)\s+)*-1(?=$|[\s;&|)`])"), "a command that ends all processes of the user (kill -1)"),
    (re.compile(r"\bos\.kill\s*\(\s*-1\b"), "code that ends all processes of the user (os.kill(-1, ...))"),
    (re.compile(r"(?s)\b(?:killpg|getpgid)\b.*\bgetppid\b|\bgetppid\b.*\b(?:killpg|getpgid)\b"),
     "code that ends the process group of its parent process (os.killpg(os.getpgid(os.getppid()), ...))"),
    (re.compile(r"(?is)" + _LISTING_WORDS + r".*" + _KILL_WORDS + r"|" + _KILL_WORDS + r".*" + _LISTING_WORDS),
     "a command that finds processes and ends them in one step (for example pgrep ... | xargs kill, kill $(pgrep ...))"),
    (re.compile(r"(?is)" + _PARENT_WORDS + r".*(?:" + _KILL_WORDS + r"|\bsignal\b)|" + _KILL_WORDS + r".*" + _PARENT_WORDS),
     "a command that ends its parent process ($PPID, os.getppid()), which is the harness"),
    (_at_command(r"taskkill", r"[^;&|\n]*[/-]im\s+\S*" + _PROCESS_NAMES), "a command that ends processes by the image name of the interpreter or the harness"),
    (re.compile(r"\b(?:stop-process|spps)\b[^;&|\n]*-(?:name|processname)\s+\S*" + _PROCESS_NAMES, re.IGNORECASE),
     "a command that ends processes by the name of the interpreter or the harness"),
    (re.compile(r"\bwmic\b[^;&|\n]*\bprocess\b[^;&|\n]*" + _PROCESS_NAMES + r"[^;&|\n]*\b(?:delete|terminate)\b", re.IGNORECASE),
     "a command that ends processes by the name of the interpreter or the harness"),
)
"""Rules of the host-process filter (always applied): commands that end
processes by the name of the Python interpreter or of the harness (``pkill python``, ``killall
python3``, ``taskkill /IM python.exe``), by a pattern of their command line, their user or a
regular expression (``pkill -f ...``, ``pkill -u $USER``, ``killall -r ...``), all processes of the
user (``kill -1``, ``os.kill(-1, ...)``, ``killall5``), the processes that a listing finds in the
same command (``pgrep python | xargs kill``, ``kill $(pgrep ...)``), or the parent process
(``kill $PPID``, ``os.kill(os.getppid(), ...)``). Such commands could end the grid runner or a run
worker, which run as the same operating-system user. Gaps are listed in
:mod:`aspire_sysid.experiment.host`."""


HOST_CODE_RULES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    r for r in HOST_PROCESS_RULES if "code" in r[1] or "parent" in r[1]
)
"""The rules of the host-process filter that also apply to the scripts a command names (both
configurations): ending all processes of the user, the parent process, or the parent's group."""

_KILL_BY_NAME = re.compile(_CMD + r"(pkill|killall)(?:\.exe)?(?=$|[\s;&|)`])([^;&|\n`)]*)", re.IGNORECASE)
_EXACT_NAME = re.compile(r"^[A-Za-z0-9_+-][A-Za-z0-9_.+-]*$")
_SIGNAL_NAMES = (
    "HUP|INT|QUIT|ILL|TRAP|ABRT|IOT|BUS|FPE|KILL|USR1|SEGV|USR2|PIPE|ALRM|TERM|STKFLT|CHLD|CONT|STOP|TSTP|TTIN|TTOU|URG|"
    "XCPU|XFSZ|VTALRM|PROF|WINCH|IO|POLL|PWR|SYS"
)
_SIGNAL_OPTION = re.compile(r"^-(?:\d+|(?:SIG)?(?:" + _SIGNAL_NAMES + r"))$", re.IGNORECASE)


def _kill_by_name_violation(text: str) -> str | None:
    """``pkill`` and ``killall`` are permitted only with exact matching (``pkill -x``, ``killall -e``),
    a signal and exact process names that are not protected; any other option (``-f``, ``-v``,
    ``-u``, ``-P``, ``-g``, ``-s`` of ``pkill``, ``-r``, ...) and any pattern are refused, because a
    pattern such as ``thon``, ``.`` or ``^p`` can match the harness's processes."""
    import shlex

    for m in _KILL_BY_NAME.finditer(text):
        prog, rest = m.group(1).lower(), m.group(2)
        try:
            args = shlex.split(rest)
        except ValueError:
            args = rest.split()
        exact = False
        names: list[str] = []
        i = 0
        while i < len(args):
            a = args[i]
            if prog == "pkill" and a in ("-x", "--exact"):
                exact = True
            elif prog == "killall" and a in ("-e", "--exact"):
                exact = True
            elif a in ("-e", "--echo") and prog == "pkill":
                pass
            elif prog == "killall" and a in ("-q", "--quiet", "-w", "--wait"):
                pass
            elif _SIGNAL_OPTION.match(a) or a.startswith("--signal="):
                pass
            elif a == "--signal" or (prog == "killall" and a == "-s"):
                i += 1
            elif a.startswith("-"):
                return f"{prog} with the option {a!r}; only exact names with {'-x' if prog == 'pkill' else '-e'} and a signal are permitted"
            else:
                names.append(a)
            i += 1
        if not exact:
            return f"{prog} without exact matching ({'-x' if prog == 'pkill' else '-e'}); a pattern can match the harness's processes"
        if not names:
            return f"{prog} without a process name"
        for n in names:
            if not _EXACT_NAME.match(n):
                return f"{prog} with the pattern {n!r}; only an exact process name is permitted"
            if re.fullmatch(_PROCESS_NAMES, n, re.IGNORECASE):
                return f"{prog} with the name {n!r} of the interpreter or the harness"
    return None


def host_process_violation(text: str) -> str | None:
    """The reason why ``text`` would end the harness's own processes, or ``None``.

    Applies :data:`HOST_PROCESS_RULES` to the command text, always.
    """
    for pattern, reason in HOST_PROCESS_RULES:
        m = pattern.search(text)
        if m:
            return f"{reason} ({m.group(0).strip()!r})"
    reason = _kill_by_name_violation(text)
    return None if reason is None else f"a command that ends processes by name: {reason}"


def host_code_violation(text: str) -> str | None:
    """The reason why program code ``text`` would end the harness's processes, or ``None``: :data:`HOST_CODE_RULES`, applied to the scripts a command names."""
    for pattern, reason in HOST_CODE_RULES:
        m = pattern.search(text)
        if m:
            return f"{reason} ({m.group(0).strip()[:80]!r})"
    return None


def script_network_violation(text: str) -> str | None:
    """The reason why the program code ``text`` indicates network use or installation, or ``None``.

 Applies only :data:`CODE_RULES`, so that words in comments and strings of a
    script (``links``, ``curl``) are not taken for programs.
    """
    for pattern, reason in CODE_RULES:
        m = pattern.search(text)
        if m:
            return f"{reason} ({m.group(0).strip()!r})"
    return None


def interpreter_prefixes(python_executable: str | Path | None = None) -> list[Path]:
    """Installation folders of the harness's interpreter and of ``python_executable``.

    Commands may name these folders, for example ``/usr/lib/python3.11/...``; they hold the
    numerical and symbolic-regression software.
    """
    out = {Path(sys.prefix), Path(sys.base_prefix), Path(sys.exec_prefix)}
    if python_executable is not None:
        out.add(Path(python_executable).parent)
    return sorted(out)


def _resolved(p: Path) -> Path:
    try:
        return p.resolve(strict=False)
    except (OSError, RuntimeError):
        return p


def _within(p: Path, root: Path) -> bool:
    try:
        p.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass
class ShellPolicy:
    """The sealing filter and, optionally, the network filter of ``run_shell``.

    ``workspace`` is the working directory; ``protected_roots`` are folders a command may never
    name (the task store and the repository of the harness); ``allowed_prefixes`` are absolute
    folders a command may name besides the working directory.
    """

    workspace: Path
    network_filter: bool
    protected_roots: tuple[Path, ...] = ()
    allowed_prefixes: tuple[Path, ...] = ()
    extra_words: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.workspace = _resolved(Path(self.workspace))
        self.protected_roots = tuple(_resolved(Path(p)) for p in self.protected_roots)
        self.allowed_prefixes = tuple(_resolved(Path(p)) for p in self.allowed_prefixes)

    @classmethod
    def for_run(
        cls,
        workspace: str | Path,
        *,
        task_dir: str | Path | None,
        network_filter: bool,
        allowed_path_prefixes: Iterable[str] = (),
        python_executable: str | Path | None = None,
    ) -> "ShellPolicy":
        """The policy of one run: the task folder and the repository of the harness
        (the folder that contains ``aspire/``) are protected; the configured prefixes and the
        interpreter's folders are allowed."""
        protected = [HARNESS_DIR.parent]
        if task_dir is not None:
            protected.append(Path(task_dir))
        allowed = [Path(p) for p in allowed_path_prefixes] + interpreter_prefixes(python_executable)
        return cls(
            workspace=Path(workspace),
            network_filter=network_filter,
            protected_roots=tuple(protected),
            allowed_prefixes=tuple(allowed),
        )

    # -- checks --------------------------------------------------------------------------

    def _path_allowed(self, p: Path) -> bool:
        r = _resolved(p)
        if _within(r, self.workspace):
            return True
        if any(_within(r, root) for root in self.protected_roots):
            return False
        return any(_within(r, pre) for pre in self.allowed_prefixes)

    def sealing_violation(self, command: str) -> str | None:
        """The reason why ``command`` may reach outside the working directory, or ``None``.

 Refused:

        * the harness package name; a ``..`` component, also when split by quotes or backslashes
          (``.""./``); ``$HOME`` and its Windows forms; outside quotes, ``~`` and ``~name``;
          a drive letter or network share;
        * outside quotes, a lone ``/`` argument (``find / ...``, ``cd / && ...``);
        * ``cd -``, ``$OLDPWD``, ``pushd``/``popd``, a parameter expansion that edits a value
          (``${PWD%/*}``), and the parent of the current folder (``dirname "$PWD"``,
          ``Path.cwd.parent``);
        * an absolute path whose first component contains a glob, brace, variable or tilde
          character (``/h*/user``), or that lies outside the working directory and the allowed
          prefixes, or inside the task store or the repository;
        * a ``git`` command with ``-C``, ``--git-dir``, ``--work-tree`` or a ``GIT_*``
          assignment (the shell environment also confines ``git`` to the working directory).

        A POSIX absolute path counts only when its first component exists on this computer or
        contains a glob or variable character, so that a division such as ``x /y`` in inline
        Python code is not taken for a path.
        """
        low = command.lower()
        for w in SEALING_WORDS + tuple(self.extra_words):
            if w.lower() in low:
                return f"the command names {w!r}, which is not available to the agent"
        bare = _unquoted(command)
        if _PARENT.search(command) or _PARENT.search(re.sub(r"['\"\\]", "", command)):
            return "the command names a parent folder ('..'); paths must stay inside the working directory"
        if _HOME.search(command) or _TILDE.search(bare):
            return "the command names a home folder; paths must stay inside the working directory"
        if _UNC.search(command):
            return "the command names a network share; paths must stay inside the working directory"
        if _LONE_ROOT.search(bare):
            return "the command names the root folder '/'; paths must stay inside the working directory"
        for pattern, what in _DIRECTORY_TRICKS:
            if pattern.search(command):
                return f"the command uses {what}; paths must stay inside the working directory"
        if _GIT.search(bare) and _GIT_ESCAPES.search(command):
            return "the git command names another repository or work tree (-C, --git-dir, --work-tree, GIT_*)"
        for m in _WIN_ABS.finditer(command):
            p = m.group(1)
            if sys.platform != "win32" or _GLOB_OR_VARIABLE.search(p) or not self._path_allowed(Path(p)):
                return f"the command names the absolute path {p!r} outside the working directory"
        for m in _POSIX_ABS.finditer(command):
            p = m.group(1)
            parts = PurePosixPath(p).parts
            if len(parts) < 2:
                continue  # a lone "/" inside quoted code is more often an operator; unquoted, see above
            if _GLOB_OR_VARIABLE.search(parts[1]):
                return f"the command names the absolute path {p!r} with a pattern in its first folder"
            if not Path("/" + parts[1]).exists():
                continue
            if _GLOB_OR_VARIABLE.search(p):
                prefix = Path(p.split("*")[0].split("?")[0].split("[")[0].split("{")[0].split("$")[0])
                if not self._path_allowed(prefix) or any(_within(root, _resolved(prefix)) for root in self.protected_roots):
                    return f"the command names the absolute path pattern {p!r} outside the working directory"
                continue
            if not self._path_allowed(Path(p)):
                return f"the command names the absolute path {p!r} outside the working directory"
        if sys.platform == "win32":
            return self._windows_sealing_violation(command, bare)
        return None

    def _windows_sealing_violation(self, command: str, bare: str) -> str | None:
        """The Windows forms of :meth:`sealing_violation` (``cmd.exe`` runs the commands).

 Refused: the lone root ``\\`` outside quotes; a path rooted at the
        current drive without a drive letter (``\\Users\\...``), under the same rules as a POSIX
        absolute path (it counts when its first component exists on this computer or contains a
        pattern or variable character); and a ``%NAME%`` reference whose value is an absolute
        folder outside the working directory and the allowed prefixes (``%TEMP%``,
        ``%SystemDrive%``). A variable that holds a list, such as ``%PATH%``, is not a folder and
        stays permitted.
        """
        if _WIN_LONE_ROOT.search(bare):
            return "the command names the root folder '\\'; paths must stay inside the working directory"
        for m in _WIN_ROOTED.finditer(command):
            p = m.group(1)
            parts = PureWindowsPath(p).parts
            if len(parts) < 2:
                continue
            if _GLOB_OR_VARIABLE.search(parts[1]) or "%" in parts[1]:
                return f"the command names the absolute path {p!r} with a pattern in its first folder"
            if not Path("\\" + parts[1]).exists():
                continue  # more often an escape sequence in inline code, such as '\n'
            prefix = Path(re.split(r"[*?\[\]{}$`~%]", p)[0])
            if not self._path_allowed(prefix) or any(_within(root, _resolved(prefix)) for root in self.protected_roots):
                return f"the command names the absolute path {p!r} outside the working directory"
        for m in _WIN_VARIABLE.finditer(command):
            value = os.environ.get(m.group(1), "")
            if not value or ";" in value:
                continue
            folder = PureWindowsPath(value)
            if (folder.drive or folder.root) and not self._path_allowed(Path(value)):
                return f"the command names %{m.group(1)}%, a folder outside the working directory"
        return None

    def _named_scripts(self, command: str) -> list[Path]:
        out: list[Path] = []
        for m in _SCRIPT_TOKEN.finditer(command):
            tok = m.group(0)
            if PureWindowsPath(tok).is_absolute() or tok.startswith("/"):
                continue
            p = _resolved(self.workspace / tok)
            if _within(p, self.workspace) and p.is_file():
                out.append(p)
        return out

    def check(self, command: str) -> str | None:
        """The reason for refusing ``command``, or ``None`` when it may run.

        The sealing filter always applies, to the command text; the network
        filter applies when :attr:`network_filter` is set, to the command text and to the text
        of the scripts in the working directory that it names. (Scripts are not searched for
        paths: the checking script ``check_submission.py`` itself names the harness package in
        its documentation.)
        """
        if "\x00" in command:
            return "the command contains a NUL character"
        reason = self.sealing_violation(command)
        if reason:
            return f"sealing filter: {reason}"
        reason = host_process_violation(command)
        if reason:
            return f"host-process filter: the command contains {reason}; end your own processes by their process number"
        for script in self._named_scripts(command):
            try:
                if script.stat().st_size > _SCRIPT_MAX_BYTES:
                    continue
                code = script.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            reason = host_code_violation(code)
            if reason:
                rel = script.relative_to(self.workspace).as_posix()
                return f"host-process filter: the script {rel} contains {reason}"
        if self.network_filter:
            reason = network_violation(command)
            if reason:
                return f"network filter: the command contains {reason}"
            for script in self._named_scripts(command):
                try:
                    if script.stat().st_size > _SCRIPT_MAX_BYTES:
                        continue
                    text = script.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                shell_script = script.suffix.lower() in (".sh", ".bash", ".ps1", ".bat", ".cmd")
                reason = network_violation(text) if shell_script else script_network_violation(text)
                if reason:
                    rel = script.relative_to(self.workspace).as_posix()
                    return f"network filter: the script {rel} contains {reason}"
        return None


# -- shell environment -------------------------------------------------------------------------

_CREDENTIAL_WORDS = (
    "KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "PASS", "CREDENTIAL", "AUTH", "COOKIE", "PRIVATE", "WEBHOOK",
)
_CREDENTIAL_SUFFIXES = ("_PWD", "_DSN")
_CREDENTIAL_NAMES = ("DATABASE_URL",)
_CREDENTIAL_PREFIXES = (
    "OPENAI",
    "ANTHROPIC",
    "CLAUDE",
    "AWS_",
    "AZURE_",
    "GOOGLE_",
    "GCP_",
    "GCLOUD",
    "GH_",
    "GITHUB_",
    "GITLAB_",
    "GIT_",
    "HF_",
    "HUGGING",
    "OVERLEAF",
    "NETRC",
    "SSH_",
    "DOCKER_",
    "KUBE",
    "ASPIRE_",
)
_URL_WITH_CREDENTIALS = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^/\s:@]+:[^/\s@]*@")
_PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "FTP_PROXY", "NO_PROXY")


def is_credential_variable(name: str, value: str = "") -> bool:
    """Whether an environment variable may hold a credential and is removed.

    A variable is removed when its name contains ``KEY``, ``TOKEN``, ``SECRET``, ``PASS``
    (``PASSWORD``, ``PASSWD``, ...), ``CREDENTIAL``, ``AUTH``, ``COOKIE``, ``PRIVATE`` or
    ``WEBHOOK``; ends with ``_PWD`` or ``_DSN``; is ``DATABASE_URL``; starts with the prefix
    of a vendor or service (``OPENAI``, ``ANTHROPIC``, ``AWS_``, ``GITHUB_``, ...) or with
    ``GIT_`` (the whole ``GIT_*`` group, including ``GIT_DIR``, ``GIT_WORK_TREE`` and
    ``GIT_CONFIG_*``); or when its value contains an address with user and password
    (``scheme://user:pass@host``). Names are compared in upper case.
    """
    up = name.upper()
    return (
        any(w in up for w in _CREDENTIAL_WORDS)
        or up.endswith(_CREDENTIAL_SUFFIXES)
        or up in _CREDENTIAL_NAMES
        or up.startswith(_CREDENTIAL_PREFIXES)
        or bool(_URL_WITH_CREDENTIALS.search(value or ""))
    )


def shell_environment(
    *,
    network_filter: bool,
    python_executable: str | Path | None = None,
    base: Mapping[str, str] | None = None,
    workspace: str | Path | None = None,
) -> dict[str, str]:
    """The environment of every shell command of the agent.

    Starts from ``base`` (default: the harness's environment) and removes every variable for
    which :func:`is_credential_variable` holds, including the whole ``GIT_*`` group. The folder
    of ``python_executable`` (default: the harness's interpreter) is put first on ``PATH`` so
    that ``python`` is the run's interpreter. With ``workspace``, ``GIT_CEILING_DIRECTORIES`` is
    set to the working directory's parent folder and the working directory, so that ``git``
    started inside the working directory never finds a repository that contains it (the
    repository of the task store and its history). With ``network_filter``, the
    proxy variables in both cases point to :data:`UNREACHABLE_PROXY`, ``NO_PROXY`` is empty,
    and ``pip`` is configured with no package index.
    """
    src = base if base is not None else os.environ
    env = {k: v for k, v in src.items() if not is_credential_variable(k, v)}
    exe = Path(python_executable) if python_executable is not None else Path(sys.executable)
    env["PATH"] = str(exe.parent) + os.pathsep + env.get("PATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    if workspace is not None:
        ws = _resolved(Path(workspace))
        env["GIT_CEILING_DIRECTORIES"] = os.pathsep.join([str(ws.parent), str(ws)])
        env["GIT_CONFIG_NOSYSTEM"] = "1"
    if network_filter:
        for k in list(env):
            if k.upper() in _PROXY_VARS:
                del env[k]
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "FTP_PROXY"):
            env[k] = UNREACHABLE_PROXY
            env[k.lower()] = UNREACHABLE_PROXY
        env["NO_PROXY"] = ""
        env["no_proxy"] = ""
        env["PIP_NO_INDEX"] = "1"
        env["PIP_INDEX_URL"] = UNREACHABLE_PROXY + "/simple"
    return env
