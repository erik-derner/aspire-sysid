"""The state of the web app, its channel to the user and its live progress.

The web app is a third way to conduct an interactive session, next to the terminal: the session
(:mod:`aspire_sysid.session.session`), the task interview (:mod:`aspire_sysid.session.interview`),
the checks, the evaluation, the records and the HTML report are unchanged. This module holds what
connects them to a browser:

* :class:`App`: the state shared by the session thread and the HTTP server. It is a list of
  **blocks** (pieces of HTML shown in order: the course of a round, a question and its answer, the
  result of a round, a text) and at most one **prompt** (what the user is asked to do next). Every
  change increases :attr:`App.version`; the browser asks for the changes since the version it has.
* :class:`WebChannel`: the :class:`~aspire_sysid.session.channel.UserChannel` of the browser. Each of
  its calls publishes a prompt and waits for the user's reply; the session pauses its execution
  clock around the call, as for the terminal, so the waiting time is user waiting time.
* :class:`WebProgress`: the event sink that shows the course of the running round, analysis exchange
  or task interview, rendered by the functions of the HTML report (one line per response of the
  agent, which unfolds to the reasoning summary, the commands and the outputs).

Everything shown is rendered on the server by plain code; the page's script only places blocks and
sends the user's inputs. The pending prompt lives here, so that reloading or closing the page loses
nothing: the session waits.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import threading
from pathlib import Path
from typing import Any, Callable

from ..agent.events import EventSink
from ..report import html_report as H
from ..session.channel import ChoiceContext, UserAction, UserChannel
from ..task.changes import TaskChange, TaskChangeError

__all__ = ["App", "AppLog", "WebChannel", "WebProgress", "check_definition_text"]

E = html.escape


class App:
    """State shared by the session thread and the HTTP server (module docstring)."""

    def __init__(self) -> None:
        self.cond = threading.Condition()
        self.version = 0
        self.blocks: list[dict[str, Any]] = []
        self.prompt: dict[str, Any] | None = None
        self._prompt_seq = 0
        self._replies: dict[int, Any] = {}
        self.status = ""
        self.phase = "start"                 # start, running, ended
        self.record_dir: Path | None = None  # the session record: the only folder whose files the server serves
        self.definition: dict[str, Any] | None = None  # the task definition the user may edit now (see server)
        self.closed = False

    # -- blocks ------------------------------------------------------------------------------

    def _changed(self) -> None:
        self.version += 1
        self.cond.notify_all()

    def add_block(self, html_text: str, cls: str = "") -> int:
        with self.cond:
            block = {"id": len(self.blocks) + 1, "html": html_text, "cls": cls, "version": self.version + 1}
            self.blocks.append(block)
            self._changed()
            return block["id"]

    def update_block(self, block_id: int, html_text: str, cls: str | None = None) -> None:
        with self.cond:
            block = self.blocks[block_id - 1]
            if block["html"] == html_text and (cls is None or cls == block["cls"]):
                return
            block["html"] = html_text
            if cls is not None:
                block["cls"] = cls
            block["version"] = self.version + 1
            self._changed()

    def set_status(self, text: str) -> None:
        with self.cond:
            if text != self.status:
                self.status = text
                self._changed()

    def set_phase(self, phase: str) -> None:
        with self.cond:
            self.phase = phase
            self._changed()

    def reset(self) -> None:
        """Forget the finished session, so that another one can be started."""
        with self.cond:
            self.blocks = []
            self.prompt = None
            self._replies = {}
            self.status = ""
            self.phase = "start"
            self.record_dir = None
            self.definition = None
            self._changed()

    # -- prompts ----------------------------------------------------------------------------

    def show_prompt(self, kind: str, **data: Any) -> int:
        """Publish a prompt without waiting for its reply (the start page, the end)."""
        with self.cond:
            self._prompt_seq += 1
            self.prompt = {"id": self._prompt_seq, "kind": kind, **data}
            self._changed()
            return self._prompt_seq

    def ask(self, kind: str, **data: Any) -> Any:
        """Publish a prompt and wait for the user's reply (called from the session thread)."""
        pid = self.show_prompt(kind, **data)
        with self.cond:
            while pid not in self._replies:
                if self.closed:
                    raise SystemExit("the web app was shut down while it waited for the user")
                self.cond.wait(timeout=1.0)
            reply = self._replies.pop(pid)
            if self.prompt is not None and self.prompt["id"] == pid:
                self.prompt = None
            self._changed()
            return reply

    def reply(self, prompt_id: int, value: Any) -> bool:
        """Deliver the user's reply to the pending prompt ``prompt_id``; false when it is not pending."""
        with self.cond:
            if self.prompt is None or self.prompt["id"] != prompt_id or prompt_id in self._replies:
                return False
            self._replies[prompt_id] = value
            self.cond.notify_all()
            return True

    def close(self) -> None:
        with self.cond:
            self.closed = True
            self.cond.notify_all()

    # -- what the browser receives ------------------------------------------------------------

    def state(self, since: int = -1) -> dict[str, Any]:
        with self.cond:
            return {
                "version": self.version,
                "phase": self.phase,
                "status": self.status,
                "order": [b["id"] for b in self.blocks],
                "blocks": [dict(b) for b in self.blocks if b["version"] > since],
                "prompt": None if self.prompt is None else dict(self.prompt),
            }

    def wait_for_change(self, since: int, timeout: float) -> None:
        with self.cond:
            if self.version <= since and not self.closed:
                self.cond.wait(timeout=timeout)


class AppLog:
    """A text stream whose lines become one block of harness messages (the lines that ``aspire
    session`` prints at its start and end, and its error messages)."""

    def __init__(self, app: App, title: str = "Messages of the harness") -> None:
        self.app = app
        self.title = title
        self.lines: list[tuple[str, bool]] = []
        self._buffer = ""
        self._block: int | None = None
        self.errors: list[str] = []

    def write(self, text: str) -> int:
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._add(line.rstrip())
        return len(text)

    def flush(self) -> None:
        return None

    def _add(self, line: str) -> None:
        is_error = line.lower().startswith(("error:", "invalid task:", "invalid tool configuration:"))
        if is_error:
            self.errors.append(line)
        self.lines.append((line, is_error))
        body = "".join(f"<div class='{'logerr' if err else 'logline'}'>{E(text)}</div>" for text, err in self.lines)
        block = (f"<details class=fold{' open' if self.errors else ''}><summary>{E(self.title)}</summary>"
                 f"<div class=in>{body}</div></details>")
        if self._block is None:
            self._block = self.app.add_block(block, "log")
        else:
            self.app.update_block(self._block, block)


def _card(title: str, body: str, cls: str = "card") -> str:
    return f"<div class='{cls}'><div class=cardtitle>{E(title)}</div>{body}</div>"


def _say(text: str) -> str:
    return f"<div class=say>{E(text)}</div>"


# ---------------------------------------------------------------------------------------------
# the live course of a round, an analysis exchange or the task interview


class WebProgress(EventSink):
    """Shows the events of the running scope as the course of the HTML report (module docstring).

    A scope starts with the ``round_start`` event of the main agent: an identification round, an
    analysis exchange, or an exchange of the task interview (all exchanges of one interview form one
    scope). The block of a scope is rewritten at every event and folded when the scope ends.
    """

    def __init__(self, app: App) -> None:
        self.app = app
        self.events: list[dict[str, Any]] = []
        self.block: int | None = None
        self.title = ""
        self.scope = ""
        self.unit = "the round"
        self.turns = 0

    def _render(self, final: bool = False) -> None:
        run = H.Run("live", Path("."), {}, None, None, [], self.events)
        turns = f" ({self.turns} turn{'s' if self.turns != 1 else ''})" if self.turns else ""
        note = "" if final else " <span class='pill warn'>running</span>"
        course = H._course(run).replace("since the start of the run", f"since the start of {self.unit}")
        body = (f"<details class='fold course'{'' if final else ' open'}><summary>{E(self.title)}{turns}{note}</summary>"
                f"<div class=in>{course}</div></details>")
        cls = "course final" if final else "course"
        if self.block is None:
            self.block = self.app.add_block(body, cls)
        else:
            self.app.update_block(self.block, body, cls)

    def _start_scope(self, scope: str, title: str) -> None:
        if self.block is not None and scope != self.scope:
            self._render(final=True)
        if scope != self.scope:
            self.events, self.block, self.turns = [], None, 0
        self.scope, self.title = scope, title

    def close_scope(self) -> None:
        """Fold the block of the running scope (called when the interview or the session ends)."""
        if self.block is not None:
            self._render(final=True)
        self.events, self.block, self.scope, self.turns = [], None, "", 0

    def emit(self, kind: str, **fields: Any) -> None:
        """Add one event to the course of the running scope and update the status line."""
        agent = str(fields.get("agent") or "main")
        helper = agent not in ("main", "harness", "None")
        if kind == "round_start" and not helper:
            if fields.get("session") == "interview":
                self._start_scope("interview", "Preparation of the task: what the agent did")
                self.unit = "each part of the preparation"
            elif fields.get("mode") == "exchange":
                n = fields.get("exchange")
                self._start_scope(f"exchange-{n}", f"Analysis request {n}: what the agent did")
                self.unit = "the analysis"
            else:
                n = fields.get("round")
                self._start_scope(f"round-{n}", f"Round {n}: what the agent did")
                self.unit = "the round"
            self.app.set_status(f"{self.title.split(':')[0]}: the agent is working.")
        if not self.scope:
            return
        self.events.append({"kind": kind, **json.loads(json.dumps(fields, default=str))})
        if kind == "response":
            if not helper:
                self.turns += 1
            who = f"helper agent {agent}" if helper else f"turn {self.turns}"
            self.app.set_status(f"{self.title.split(':')[0]}: the agent is working ({who}, "
                                f"execution time {H.clock(fields.get('elapsed_s'))}).")
        elif kind == "evaluation" and fields.get("status") == "started":
            self.app.set_status(f"{self.title.split(':')[0]}: the harness evaluates the models on the training and the test data.")
        if kind in ("request", "tool_call"):
            return  # nothing new to show
        final = kind == "round_end" and not helper and self.scope != "interview"
        self._render(final=final)
        if final:
            self.events, self.block, self.scope = [], None, ""


# ---------------------------------------------------------------------------------------------
# the channel


class WebChannel(UserChannel):
    """The user's side of a session in the browser (module docstring).

    ``user`` names the user in the record of task changes. ``progress`` is the
    :class:`WebProgress` of the session, whose running block is folded when the user is asked for a
    verdict on the task brief.
    """

    def __init__(self, app: App, *, user: str = "the user", progress: WebProgress | None = None,
                 today: Callable[[], str] | None = None) -> None:
        self.app = app
        self.user = user
        self.progress = progress
        self._today = today or (lambda: _dt.date.today().isoformat())
        self.interview: Any = None

    def bind_interview(self, interview: Any) -> None:
        """Called by the task interview, so that the user's own edits of ``task.yaml`` reach it."""
        self.interview = interview

    # -- the agent's question ----------------------------------------------------------------

    def ask(self, question: str, decision: str | None) -> str | None:
        body = H.agent_markdown(question) + (f"<p class='muted small'>Decision affected, as stated by the agent: {H.agent_text(decision)}</p>" if decision else "")
        self.app.set_status("Waiting for your answer to the agent's question.")
        reply = self.app.ask("question", question=question, decision=decision or "", html=body)
        text = str((reply or {}).get("text") or "").strip()
        answer = _card("Your answer", _say(text), "card user") if text else _card("Your answer", "<p class=muted>No answer given.</p>", "card user")
        self.app.add_block(_card("The agent asked", body, "card question") + answer, "question")
        self.app.set_status("The agent continues.")
        return text or None

    # -- the result of a round ---------------------------------------------------------------

    def show_report(self, round_number: int, pool_version: int, report_markdown: str, report_dir: str | None) -> None:
        """Show the models of the round: the table of the report, the agent's recommendation and the
        page of the round from the session's HTML report."""
        self.app.add_block(self._round_html(round_number, pool_version, report_markdown, report_dir), "round")

    def _round_html(self, round_number: int, pool_version: int, report_markdown: str, report_dir: str | None) -> str:
        from ..report import session_report as SR

        head = f"<h2>Round {round_number} has ended</h2>"
        try:
            folder = Path(str(report_dir)).parent.parent
            self.app.record_dir = folder
            sess = json.loads((folder / "session.json").read_text(encoding="utf-8"))
            rounds = SR._load_rounds(folder, sess, SR._events(folder), folder / "report")
            rd, run = next((rd, r) for rd, r in rounds if r is not None and r.pool_version == pool_version)
        except Exception:  # noqa: BLE001 - the complete report is shown instead of the table
            return head + f"<pre>{E(report_markdown)}</pre>"
        # the page of the round from the session's HTML report holds the table of the models, the agent's
        # recommendation, the model cards and the course of the round; it is shown as it is
        page = f"files/report/{SR.round_page_name(pool_version)}"
        rec = run.candidate(run.recommended)
        what = f"The agent recommends <b>{E(rec.label)}</b>." if rec is not None else "The agent recommended no model."
        informed = (" <span class='pill bad'>test-informed</span> You had seen test errors before this round started, so its "
                    "test errors are not errors on unseen data.") if rd.get("test_informed") else ""
        n = len(run.candidates)
        return (f"<h2>Round {round_number} has ended: {n} model{'s' if n != 1 else ''}</h2>"
                f"<p class=sub>{what}{informed} The page below shows the models with their equations, errors, explanations and "
                f"plots, and what the agent did (<a href='{page}' target=_blank rel=noopener>open it in a new tab</a>).</p>"
                f"<iframe class=page src='{page}' title='Models of round {round_number}'></iframe>")

    def show_text(self, title: str, text: str) -> None:
        self.app.add_block(_card(title, H.agent_markdown(text)), "text")

    # -- the next action -------------------------------------------------------------------------

    def choose(self, context: ChoiceContext) -> UserAction:
        self.app.set_status("Waiting for your choice: an analysis request, a new round, or the end of the session.")
        note = ""
        while True:
            reply = self.app.ask("choice", last_round=context.last_round, remaining=context.remaining,
                                 analysis_limits=context.analysis_limits, requirements=list(context.requirement_ids), note=note) or {}
            action = str(reply.get("action") or "")
            text = str(reply.get("text") or "").strip()
            if action == "end":
                self.app.add_block(_card("You", "<p>Ended the session.</p>", "card user"), "user")
                self.app.set_status("The session ends: the harness writes the record and the report.")
                return UserAction("end")
            if action == "analysis":
                if not text:
                    note = "An analysis request needs a text."
                    continue
                self.app.add_block(_card("Your analysis request", _say(text), "card user"), "user")
                self.app.set_status("Your analysis request was passed to the agent.")
                return UserAction("analysis", text)
            if action == "new_round":
                try:
                    changes = [self._change(c) for c in reply.get("changes") or []]
                except (TaskChangeError, ValueError, TypeError) as exc:
                    note = f"A task change was not accepted: {exc}"
                    continue
                listed = "".join(f"<li>{E(c.text())}</li>" for c in changes)
                body = (_say(text) if text else "<p class=muted>No feedback text.</p>") + (f"<p>Task changes:</p><ul>{listed}</ul>" if listed else "")
                self.app.add_block(_card("Your feedback for a new round", body, "card user"), "user")
                self.app.set_status("A new round starts.")
                return UserAction("new_round", text, tuple(changes))
            note = "Choose an analysis request, a new round, or the end of the session."

    def _change(self, c: dict[str, Any]) -> TaskChange:
        kind = str(c.get("kind") or "")
        instruction = str(c.get("instruction") or "").strip()
        if kind == "add_nl_requirement":
            return TaskChange(kind, None, instruction, self.user, self._today())
        value = None
        if kind == "set_tolerance":
            value = float(c.get("value"))
        return TaskChange(kind, str(c.get("requirement") or "") or None, instruction, self.user, self._today(), value=value)

    # -- the task brief of an interview -------------------------------------------------------

    def confirm_task(self, brief: str, summary: str = "") -> "bool | str":
        """Show the task brief and wait for the verdict. While it is shown, the user may also edit
        ``task.yaml`` directly (:meth:`save_definition`); the brief is then shown again."""
        if self.progress is not None:
            self.progress.close_scope()
        if summary.strip():
            self.app.add_block(_card("The agent's summary of the task", H.agent_markdown(summary.strip())), "text")
        block = self.app.add_block(self._brief_html(brief), "brief")
        self.app.set_status("Waiting for your verdict on the task.")
        task_dir = getattr(getattr(self.interview, "stub", None), "task_dir", None)
        self.app.definition = None if task_dir is None else {
            "task_dir": Path(task_dir), "save": self._save_definition, "block": block}
        try:
            reply = self.app.ask("verdict", editable=task_dir is not None) or {}
        finally:
            self.app.definition = None
        verdict = str(reply.get("verdict") or "")
        text = str(reply.get("text") or "").strip()
        if verdict == "accept":
            self.app.add_block(_card("You", "<p>Accepted the task. The identification starts.</p>", "card user"), "user")
            return True
        if verdict == "change" and text:
            self.app.add_block(_card("Your change request", _say(text), "card user"), "user")
            self.app.set_status("Your change request was passed to the agent, which continues the preparation of the task.")
            return text
        self.app.add_block(_card("You", "<p>Stopped. The identification does not start; the task folder is kept.</p>", "card user"), "user")
        return False

    @staticmethod
    def _brief_html(brief: str) -> str:
        return ("<h2>The task as the identification agent will receive it</h2><p class=sub>The task brief <code>TASK.md</code>, "
                f"written by the harness from <code>task.yaml</code>.</p><div class='card doc'>{H.markdown(brief)}</div>")

    def _save_definition(self, text: str) -> tuple[bool, str]:
        """The user's own edit of ``task.yaml`` during the confirmation: checked and kept by the
        interview, and the brief on the page is replaced."""
        ok, result = self.interview.user_edit(text)
        if ok and self.app.definition is not None:
            self.app.update_block(self.app.definition["block"], self._brief_html(result))
            self.app.add_block(_card("You", "<p>Edited <code>task.yaml</code>. The task brief above shows the new definition.</p>", "card user"), "user")
        return ok, result


# ---------------------------------------------------------------------------------------------
# checking a definition the user typed


def check_definition_text(task_dir: str | Path, text: str, *, keep: bool) -> tuple[bool, str]:
    """Check the text of a ``task.yaml`` for the task folder ``task_dir`` with the task loader.

    Returns ``(True, brief)`` with the task brief of the definition, or ``(False, errors)``. With
    ``keep`` a valid text becomes the ``task.yaml`` of the folder; in every other case the file is
    left exactly as it was. The check reads the definition and the agent-visible data only: the
    loader never opens a sealed file.
    """
    from ..brief.render import render_brief
    from ..task import TaskError, load_task

    target = Path(task_dir) / "task.yaml"
    before = target.read_bytes() if target.is_file() else None
    ok, result = False, ""
    try:
        target.write_text(text, encoding="utf-8", newline="\n")
        task = load_task(task_dir)
        ok, result = True, render_brief(task, interactive=True)
    except TaskError as exc:
        result = str(exc)
    except Exception as exc:  # noqa: BLE001 - a text the loader cannot read at all
        result = f"the task definition cannot be read ({type(exc).__name__}: {exc})"
    if not (ok and keep):
        if before is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(before)
    return ok, result
