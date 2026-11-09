"""The local server of the web app: ``aspire web`` and ``aspire session ... --web``.

One process, one user, one session at a time. The server listens on ``127.0.0.1`` only and is built
on the Python standard library (``http.server``); the page is :mod:`aspire_sysid.web.page`. The
session runs in a worker thread through :func:`aspire_sysid.session.cli.run_session_command`, the
function behind ``aspire session``, with a :class:`~aspire_sysid.web.app.WebChannel` in place of the
terminal. Everything a session does (key handling, the agent's interpreter, the task interview, the
rounds, the records, the report) is therefore the same as on the terminal.

**Addresses.** Every address starts with ``/t/<token>/``; the token is a random text generated at
start and printed with the address of the page. Below it:

* ``GET  ./`` the page; ``GET api/state?since=N`` the changes of the state (the request waits up to
  25 s for a change, unless ``wait=0``);
* ``POST api/start`` ``{"task": id}`` or ``{"train": {"name", "text"}, "val": ..., "tests": [...],
  "new_task": name}``; ``POST api/reply`` ``{"prompt": id, "reply": {...}}``;
* ``GET api/task[?id=...]``, ``POST api/task/check``, ``POST api/task/save``: the text of a
  ``task.yaml``, its check and its saving (a task of the start page, or the task of the running
  interview while its brief awaits the user's verdict);
* ``POST api/reset`` (after a session: back to the start page), ``POST api/shutdown``;
* ``GET files/<path>``: a file of the session record, for the pages of the HTML report.

**Sealing**. The pages of the report show results on the test data, and the
agent's commands run on the same computer. The token keeps the server from being a way to them: it
is never in an environment variable, a command line or a file, so a command of the agent that
requests an address of this server without it receives "not found"; the ``Host`` header must name
this computer; and the agent's ``web_fetch`` refuses local addresses (``aspire/configs/tools.yaml``).
The server serves files of the session record only, never of a task folder. The limit stated in
``aspire/README.md`` remains: a program of the agent can read what the operating-system user of the
harness can read.

**Re-execution.** On POSIX, ``aspire session`` replaces its process image so that the API key is not
in the environment of the process that parents the agent's commands. The web app cannot do this,
because the server and the session share one process; it runs the session with ``--no-reexec``.
Keep the key in a ``.env`` file, which is never put into the environment.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import json
import re
import secrets
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import yaml

from ..report import html_report as H
from .app import App, AppLog, WebChannel, WebProgress, check_definition_text
from .page import render_page

__all__ = ["WebServer", "cmd_web", "register", "serve_session"]

MAX_BODY = 512 * 1024 * 1024
WAIT_S = 25.0
_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_TYPES = {".html": "text/html; charset=utf-8", ".png": "image/png", ".json": "application/json; charset=utf-8",
          ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".py": "text/plain; charset=utf-8",
          ".csv": "text/plain; charset=utf-8", ".jsonl": "text/plain; charset=utf-8", ".yaml": "text/plain; charset=utf-8",
          ".m": "text/plain; charset=utf-8", ".svg": "image/svg+xml"}


class WebServer:
    """The web app: its state, its HTTP server and the worker thread of the session (module docstring).

    ``tasks_root`` is the folder of the task folders (default ``tasks`` under the current directory);
    ``sessions_root`` the folder of the session records (default ``sessions`` there). ``session_args``
    are options of ``aspire session`` applied to every session started from the page (``--model``,
    ``--python``, ``--no-plots``, ...). ``session_options`` are keyword arguments passed to
    :func:`~aspire_sysid.session.cli.run_session_command` (tests inject a scripted provider).
    """

    def __init__(self, *, host: str = "127.0.0.1", port: int = 0, tasks_root: str | Path | None = None,
                 sessions_root: str | Path | None = None, session_args: list[str] | None = None,
                 session_options: dict[str, Any] | None = None, user: str | None = None) -> None:
        self.app = App()
        self.token = secrets.token_urlsafe(24)
        self.prefix = f"/t/{self.token}/"
        self.tasks_root = Path(tasks_root).resolve() if tasks_root is not None else Path.cwd() / "tasks"
        self.sessions_root = Path(sessions_root).resolve() if sessions_root is not None else Path.cwd() / "sessions"
        self.session_args = list(session_args or [])
        self.session_options = dict(session_options or {})
        self.user = user
        self.worker: threading.Thread | None = None
        self.exit_code: int | None = None
        self._lock = threading.Lock()
        server = self

        class Handler(_Handler):
            web = server

        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.httpd.daemon_threads = True
        self.host, self.port = host, self.httpd.server_address[1]
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{self.prefix}"

    # -- running the server -----------------------------------------------------------------------

    def start_background(self) -> None:
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="aspire-web", daemon=True)
        self._thread.start()

    def serve_forever(self) -> None:
        try:
            self.httpd.serve_forever()
        finally:
            self.close()

    def close(self) -> None:
        self.app.close()
        with contextlib.suppress(Exception):
            self.httpd.server_close()

    def shutdown(self) -> None:
        self.app.close()
        threading.Thread(target=self.httpd.shutdown, daemon=True).start()

    # -- the start page -------------------------------------------------------------------------------

    def tasks(self) -> list[dict[str, str]]:
        out = []
        if self.tasks_root.is_dir():
            for d in sorted(self.tasks_root.iterdir()):
                f = d / "task.yaml"
                if d.is_dir() and f.is_file():
                    try:
                        spec = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
                    except (OSError, yaml.YAMLError):
                        spec = {}
                    out.append({"id": d.name, "title": str(spec.get("title") or "(no title)")})
        return out

    def model(self) -> str:
        from ..agent.providers import default_model_id

        if "--model" in self.session_args:
            return self.session_args[self.session_args.index("--model") + 1]
        try:
            return default_model_id()
        except Exception:  # noqa: BLE001 - shown on the start page only
            return "not configured"

    def show_start(self) -> None:
        self.app.show_prompt("start", tasks=self.tasks(), tasks_root=str(self.tasks_root), model=self.model(),
                             today=_dt.date.today().strftime("%Y%m%d"),
                             note="A session can take an hour and costs what the limits of the task allow.")

    # -- starting a session ---------------------------------------------------------------------------

    def _args(self, task_dir: Path) -> argparse.Namespace:
        from ..cli import build_parser

        args = build_parser().parse_args(["session", str(task_dir), *self.session_args])
        args.web = False
        args.no_reexec = True  # the server and the session share this process (module docstring)
        if self.user and not getattr(args, "user", None):
            args.user = self.user
        return args

    def task_folder(self, task_id: Any) -> Path:
        if not isinstance(task_id, str) or not _ID.match(task_id) or not (self.tasks_root / task_id / "task.yaml").is_file():
            raise ValueError(f"there is no task {task_id!r} in {self.tasks_root}")
        return self.tasks_root / task_id

    def start(self, payload: dict[str, Any]) -> None:
        """Start a session from the start page: on a task folder, or from uploaded data files (the
        task interview runs first). Raises :class:`ValueError` with the reason when it cannot start."""
        from ..session.cli import default_session_dir
        from ..task.stub import InterviewError, create_task_stub, default_task_dir

        with self._lock:
            if self.app.phase == "running":
                raise ValueError("a session is running; one session runs at a time")
            if payload.get("task"):
                args = self._args(self.task_folder(payload["task"]))
                task_id = str(payload["task"])
            elif isinstance(payload.get("train"), dict):
                name = str(payload.get("new_task") or "").strip()
                folder = (self.tasks_root / name) if name else default_task_dir(self.tasks_root)
                upload = Path(tempfile.mkdtemp(prefix="aspire-upload-"))
                try:
                    def save(item: dict[str, Any], sub: str) -> Path:
                        # the file keeps its name, which the stub records as the original; the name is never shown to an agent
                        target = upload / sub / (Path(str(item.get("name") or "data.csv")).name or "data.csv")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(str(item.get("text") or ""), encoding="utf-8", newline="")
                        return target

                    train = save(payload["train"], "train")
                    val = save(payload["val"], "val") if isinstance(payload.get("val"), dict) else None
                    held = [save(t, f"held-{i}") for i, t in enumerate(payload.get("tests") or [], 1) if isinstance(t, dict)]
                    try:
                        stub = create_task_stub(folder, train, val, held)
                    except InterviewError as exc:
                        raise ValueError(str(exc)) from exc
                finally:
                    shutil.rmtree(upload, ignore_errors=True)
                args = self._args(stub.task_dir)
                args.interview = True
                task_id = stub.task_id
            else:
                raise ValueError("choose a task, or give the training data")
            if not getattr(args, "out", None):
                args.out = str(default_session_dir(task_id, base=self.sessions_root))
            self.launch(args)

    def launch(self, args: argparse.Namespace) -> None:
        """Run the session of ``args`` in the worker thread."""
        args.web = False
        args.no_reexec = True
        self.app.record_dir = Path(args.out).resolve() if getattr(args, "out", None) else None
        self.app.prompt = None
        self.app.set_phase("running")
        self.worker = threading.Thread(target=self._run, args=(args,), name="aspire-session", daemon=True)
        self.worker.start()

    def _run(self, args: argparse.Namespace) -> None:
        from ..session.cli import run_session_command

        app = self.app
        log = AppLog(app)
        progress = WebProgress(app)
        channel = WebChannel(app, user=getattr(args, "user", None) or self.user or "the user", progress=progress)
        code: int | None = None
        app.set_status("The session starts.")
        try:
            with contextlib.redirect_stderr(log):  # type: ignore[type-var]
                code = run_session_command(args, channel=channel, stdout=log, sink=progress, **self.session_options)  # type: ignore[arg-type]
        except SystemExit as exc:
            log.write(f"error: the session was interrupted ({exc})\n")
        except Exception as exc:  # noqa: BLE001 - shown to the user; the record keeps what was written
            log.write(f"error: {type(exc).__name__}: {exc}\n")
        finally:
            self.exit_code = code
            progress.close_scope()
            folder = app.record_dir
            report = folder is not None and (folder / "report" / "index.html").is_file()
            done = code == 0 and folder is not None and (folder / "session.json").is_file()
            body = ""
            if report:
                body += "<p><a href='files/report/index.html' target=_blank rel=noopener>Open the report of the session</a> (all rounds, the course of the session, the files).</p>"
            if folder is not None and folder.exists():
                body += f"<p class='muted small'>Record of the session: <code>{H.E(str(folder))}</code></p>"
            if log.errors:
                body += f"<p class=note>{H.E(log.errors[-1])}</p>"
            title = "The session has ended." if done else ("The identification was not started." if code == 0 else "The session could not be completed.")
            app.set_phase("ended")
            app.set_status(title)
            app.show_prompt("ended", title=title, html=body)

    # -- the text of a task definition -----------------------------------------------------------------

    def definition(self, task_id: str | None) -> tuple[Path, bool]:
        """The task folder whose ``task.yaml`` the user may edit now, and whether it is the task of the
        running interview. Raises :class:`ValueError` when there is none."""
        if task_id:
            if self.app.phase == "running":
                raise ValueError("the definition of a task cannot be edited while a session runs")
            return self.task_folder(task_id), False
        d = self.app.definition
        if d is None:
            raise ValueError("no task definition can be edited now")
        return Path(d["task_dir"]), True

    def definition_text(self, task_id: str | None) -> dict[str, Any]:
        folder, _ = self.definition(task_id)
        f = folder / "task.yaml"
        return {"ok": True, "path": str(f), "text": f.read_text(encoding="utf-8") if f.is_file() else ""}

    def definition_check(self, task_id: str | None, text: str, save: bool) -> dict[str, Any]:
        folder, in_interview = self.definition(task_id)
        if save and in_interview:
            ok, result = self.app.definition["save"](text)  # type: ignore[index]
        else:
            ok, result = check_definition_text(folder, text, keep=save)
        if ok:
            return {"ok": True, "valid": True, "brief_html": H.markdown(result), "saved": bool(save)}
        return {"ok": True, "valid": False, "errors": result, "saved": False}


class _Handler(BaseHTTPRequestHandler):
    web: WebServer
    protocol_version = "HTTP/1.1"
    server_version = "aspire-web"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - the signature of the base class
        return None

    # -- helpers ------------------------------------------------------------------------------------

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: Any, status: int = 200) -> None:
        self._send(status, json.dumps(data, default=str).encode("utf-8"), "application/json; charset=utf-8")

    def _not_found(self) -> None:
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def _route(self) -> tuple[str, dict[str, list[str]]] | None:
        """The path below the token prefix and the query, or ``None`` after a "not found" reply: the
        request names another host, or does not carry the token."""
        host = (self.headers.get("Host") or "").lower()
        if host not in (f"127.0.0.1:{self.web.port}", f"localhost:{self.web.port}"):
            self._not_found()
            return None
        parts = urlsplit(self.path)
        if not parts.path.startswith(self.web.prefix):
            self._not_found()
            return None
        return unquote(parts.path[len(self.web.prefix):]), parse_qs(parts.query)

    def _body(self) -> dict[str, Any]:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return {}
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    # -- GET ---------------------------------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 - the name the base class calls
        route = self._route()
        if route is None:
            return
        path, query = route
        web = self.web
        if path == "":
            self._send(200, render_page().encode("utf-8"), "text/html; charset=utf-8")
        elif path == "api/state":
            try:
                since = int((query.get("since") or ["-1"])[0])
            except ValueError:
                since = -1
            if (query.get("wait") or ["1"])[0] != "0":
                web.app.wait_for_change(since, WAIT_S)
            self._json(web.app.state(since))
        elif path == "api/task":
            try:
                self._json(web.definition_text((query.get("id") or [None])[0]))
            except (ValueError, OSError) as exc:
                self._json({"ok": False, "error": str(exc)})
        elif path.startswith("files/"):
            self._serve_record_file(path[len("files/"):])
        else:
            self._not_found()

    def _serve_record_file(self, rel: str) -> None:
        root = self.web.app.record_dir
        if root is None:
            self._not_found()
            return
        try:
            target = (root / rel).resolve()
            target.relative_to(root.resolve())
        except (ValueError, OSError):
            self._not_found()
            return
        if not target.is_file():
            self._not_found()
            return
        self._send(200, target.read_bytes(), _TYPES.get(target.suffix.lower(), "application/octet-stream"))

    # -- POST --------------------------------------------------------------------------------------

    def do_POST(self) -> None:  # noqa: N802 - the name the base class calls
        route = self._route()
        if route is None:
            return
        path, _ = route
        web = self.web
        body = self._body()
        try:
            if path == "api/start":
                web.start(body)
                self._json({"ok": True})
            elif path == "api/reply":
                ok = web.app.reply(int(body.get("prompt") or 0), body.get("reply"))
                self._json({"ok": ok, **({} if ok else {"error": "This input is no longer awaited; the page shows the current state."})})
            elif path in ("api/task/check", "api/task/save"):
                self._json(web.definition_check(body.get("id") or None, str(body.get("text") or ""), save=path.endswith("save")))
            elif path == "api/reset":
                if web.app.phase == "running":
                    raise ValueError("a session is running")
                web.app.reset()
                web.show_start()
                self._json({"ok": True})
            elif path == "api/shutdown":
                if web.app.phase == "running":
                    raise ValueError("a session is running; end it first")
                self._json({"ok": True})
                web.shutdown()
            else:
                self._not_found()
        except (ValueError, OSError, TypeError) as exc:
            self._json({"ok": False, "error": str(exc)})


# ---------------------------------------------------------------------------------------------
# commands


def _serve(web: WebServer, *, open_browser: bool, out: Any = None) -> int:
    out = out or sys.stdout
    out.write(f"ASPIRE web app: {web.url}\n"
              "Open this address in a browser on this computer (it works on this computer only). Stop with Ctrl+C.\n")
    out.flush()
    if open_browser:
        import webbrowser

        with contextlib.suppress(Exception):
            webbrowser.open(web.url)
    try:
        web.serve_forever()
    except KeyboardInterrupt:
        out.write("\nThe web app was stopped.\n")
    return 0


def _session_args(args: argparse.Namespace) -> list[str]:
    """The options of ``aspire web`` that apply to every session it starts."""
    out: list[str] = []
    for flag, name in (("--model", "model"), ("--python", "python"), ("--workspace-root", "workspace_root"), ("--user", "user")):
        if getattr(args, name, None):
            out += [flag, str(getattr(args, name))]
    for flag, name in (("--no-plots", "no_plots"), ("--allow-harness-interpreter", "allow_harness_interpreter")):
        if getattr(args, name, False):
            out.append(flag)
    return out


def cmd_web(args: argparse.Namespace) -> int:
    """``aspire web``: the web app with its start page (module docstring)."""
    web = WebServer(port=int(getattr(args, "port", 0) or 0), tasks_root=getattr(args, "tasks", None),
                    sessions_root=getattr(args, "sessions", None), session_args=_session_args(args), user=getattr(args, "user", None))
    web.show_start()
    return _serve(web, open_browser=not getattr(args, "no_browser", False))


def serve_session(args: argparse.Namespace, **session_options: Any) -> int:
    """``aspire session ... --web``: the session of ``args`` in the browser instead of on the terminal.
    The start page is skipped; after the session the page offers another one."""
    web = WebServer(port=int(getattr(args, "port", 0) or 0), session_args=_session_args(args), session_options=session_options,
                    user=getattr(args, "user", None))
    web.launch(args)
    return _serve(web, open_browser=not getattr(args, "no_browser", False))


def register(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register ``aspire web``."""
    p = sub.add_parser(
        "web",
        help="interactive operation in the browser: start page, task interview, session",
        description=(
            "Start the web app of interactive operation on this computer and open it in the browser. The start page "
            "offers a session on a task folder or from data files (an agent then prepares the task with you), and the "
            "editing of a task.yaml. It is an alternative to `aspire session` on the terminal and runs the same session."
        ),
    )
    p.add_argument("--port", type=int, default=0, help="port on 127.0.0.1 (default: a free port)")
    p.add_argument("--no-browser", action="store_true", help="do not open the browser; the address is printed")
    p.add_argument("--tasks", default=None, help="folder of the task folders (default: tasks under the current directory)")
    p.add_argument("--sessions", default=None, help="folder of the session records (default: sessions under the current directory)")
    p.add_argument("--model", default=None, help="model identifier (default: the model of the project)")
    p.add_argument("--python", default=None, help="interpreter of the agent's shell (default: as for aspire session)")
    p.add_argument("--allow-harness-interpreter", action="store_true", help="as for aspire session")
    p.add_argument("--no-plots", action="store_true", help="do not draw the plots of the evaluation reports")
    p.add_argument("--user", default=None, help="name of the user in the record of task changes")
    p.add_argument("--workspace-root", default=None, help="as for aspire session")
    p.set_defaults(handler=cmd_web)
