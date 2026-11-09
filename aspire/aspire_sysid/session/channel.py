"""The conversation channel between the harness and the user in interactive operation.

In interactive operation, the user answers or declines the agent's questions (``ask_user``), receives the
complete evaluation report after each round, and then asks for an explanation or an analysis
(analysis request), requests new or revised candidates (new identification round, with feedback
and possibly changed requirements), or ends the session. :class:`UserChannel` is the interface
through which the harness does all of this; the harness pauses the execution clock during every
call, so that the user's time is recorded as user waiting time and never as execution time.

Two implementations:

* :class:`TerminalChannel`: text on a terminal (standard input and output), used by
  ``aspire session``;
* :class:`ScriptedChannel`: prepared answers and actions, for tests; it can advance a fake time
  source to simulate the user's waiting time.

The texts that the user types are passed on verbatim: the harness records the question and the
answer verbatim, and it preserves the user's feedback rather than attempting to remove such
information.
"""

from __future__ import annotations

import abc
import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, TextIO

from ..agent.events import EventSink
from .changes import TaskChange

__all__ = [
    "TerminalProgress",
    "round_summary_text",
    "ACTION_KINDS",
    "UserAction",
    "ChoiceContext",
    "UserChannel",
    "ScriptedChannel",
    "TerminalChannel",
    "parse_change_line",
]

ACTION_KINDS: tuple[str, ...] = ("analysis", "new_round", "end")
"""The user's choices after a round or an analysis exchange: an analysis request,
a new identification round, or the end of the session."""


@dataclass(frozen=True)
class UserAction:
    """One choice of the user after a round or an analysis exchange.

    ``kind`` is one of :data:`ACTION_KINDS`; ``text`` is the verbatim analysis request or the
    verbatim feedback of a new round (empty for ``end``); ``changes`` are the task changes that
    take effect with the new round (only for ``new_round``).
    """

    kind: str
    text: str = ""
    changes: tuple[TaskChange, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in ACTION_KINDS:
            raise ValueError(f"unknown user action {self.kind!r}; the defined actions are {ACTION_KINDS}")
        if self.changes and self.kind != "new_round":
            raise ValueError("task changes take effect with a new identification round")


@dataclass(frozen=True)
class ChoiceContext:
    """What the harness tells the user before the user chooses the next action.

    ``completed_pool_versions`` are the pool versions with at least one evaluated candidate;
    ``last_round`` is the number of the last round; ``remaining`` is the remaining session
    allowance as text; ``analysis_limits`` the limits of one analysis exchange as text;
    ``requirement_ids`` the identifiers of the formal requirements (for task changes).
    """

    last_round: int
    completed_pool_versions: tuple[int, ...]
    remaining: str
    analysis_limits: str
    requirement_ids: tuple[str, ...] = ()


class UserChannel(abc.ABC):
    """Interface between the harness and the user in interactive operation.

    The harness pauses the execution clock around every call (user waiting time).
    """

    @abc.abstractmethod
    def ask(self, question: str, decision: str | None) -> str | None:
        """Show the agent's question and return the user's verbatim answer, or ``None`` when the
        user declines (``ask_user``). ``decision`` is the modeling choice that the
        agent says the answer affects."""

    @abc.abstractmethod
    def show_report(self, round_number: int, pool_version: int, report_markdown: str, report_dir: str | None) -> None:
        """Show the complete evaluation report of a round to the user, including the results on
        sealed test data ("After each round, the user receives the complete evaluation
        report")."""

    @abc.abstractmethod
    def show_text(self, title: str, text: str) -> None:
        """Show a text to the user: the agent's answer to an analysis request, or a harness notice
        such as the session-completion message."""

    @abc.abstractmethod
    def choose(self, context: ChoiceContext) -> UserAction:
        """Return the user's next action: analysis request, new round, or end."""

    def confirm_task(self, brief: str, summary: str = "") -> "bool | str":
        """Show the task brief that a task interview produced, with the interview agent's summary, and
        return the user's verdict: ``True`` (accepted; the identification starts), ``False`` (stop) or
        a text with the changes the user asks for (:mod:`aspire_sysid.session.interview`). The
        default accepts, for channels that are never used with an interview."""
        return True


# ---------------------------------------------------------------------------------------------
# Scripted channel (tests)
# ---------------------------------------------------------------------------------------------


class ScriptedChannel(UserChannel):
    """A channel with prepared answers and actions, for tests.

    ``answers`` are consumed by :meth:`ask` in order; ``None`` declines the question. ``actions``
    are consumed by :meth:`choose` in order; when they are exhausted, the user ends the session.
    ``wait`` is called with the kind of each interaction (``"ask"``, ``"report"``, ``"text"``,
    ``"choose"``) while the harness waits; tests use it to advance a fake time source, which then
    appears as user waiting time. Everything shown to the user is kept in :attr:`shown`.
    """

    def __init__(
        self,
        answers: Iterable[str | None] = (),
        actions: Iterable[UserAction] = (),
        *,
        wait: Callable[[str], None] | None = None,
    ) -> None:
        self._answers = list(answers)
        self._actions = list(actions)
        self._wait = wait
        self.questions: list[tuple[str, str | None]] = []
        self.reports: list[tuple[int, int, str]] = []
        self.briefs: list[str] = []
        self.verdicts: list[bool | str] = []  # consumed by confirm_task in order; exhausted: the brief is accepted
        self.shown: list[tuple[str, str]] = []
        self.contexts: list[ChoiceContext] = []

    def _waiting(self, kind: str) -> None:
        if self._wait is not None:
            self._wait(kind)

    def ask(self, question: str, decision: str | None) -> str | None:
        """Return the next prepared answer (``None``: declined). """
        self.questions.append((question, decision))
        self._waiting("ask")
        if not self._answers:
            return None
        return self._answers.pop(0)

    def confirm_task(self, brief: str, summary: str = "") -> "bool | str":
        """Keep the brief in :attr:`briefs` and return the next entry of :attr:`verdicts`, or accept."""
        self._waiting("text")
        self.briefs.append(brief)
        return self.verdicts.pop(0) if self.verdicts else True

    def show_report(self, round_number: int, pool_version: int, report_markdown: str, report_dir: str | None) -> None:
        """Keep the report."""
        self.reports.append((round_number, pool_version, report_markdown))
        self._waiting("report")

    def show_text(self, title: str, text: str) -> None:
        """Keep the text."""
        self.shown.append((title, text))
        self._waiting("text")

    def choose(self, context: ChoiceContext) -> UserAction:
        """Return the next prepared action; ``end`` when none is left. """
        self.contexts.append(context)
        self._waiting("choose")
        if not self._actions:
            return UserAction("end")
        return self._actions.pop(0)


# ---------------------------------------------------------------------------------------------
# Terminal channel (aspire session)
# ---------------------------------------------------------------------------------------------

END_OF_TEXT = "."
"""A line with only a full stop ends a text of several lines on the terminal."""


def parse_change_line(line: str, *, stated_by: str, date: str) -> TaskChange:
    """Parse one task change typed on the terminal (changes of requirements).

    Forms (the instruction text is kept verbatim):

    * ``allow <requirement id> <instruction>``: a violation of the formal requirement is reported
      without exclusion;
    * ``exclude <requirement id> <instruction>``: a violation excludes the candidate again;
    * ``tolerance <requirement id> <value> <instruction>``: a new tolerance of the formal
      requirement, in its unit;
    * ``require <text>``: an additional requirement in natural language.

    Raises :class:`ValueError` with the permitted forms on any other text.
    """
    parts = line.strip().split(None, 1)
    usage = (
        "a task change is 'allow <id> <instruction>', 'exclude <id> <instruction>', "
        "'tolerance <id> <value> <instruction>' or 'require <text>'"
    )
    if not parts:
        raise ValueError(usage)
    word = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    if word == "require":
        if not rest.strip():
            raise ValueError(usage)
        return TaskChange("add_nl_requirement", None, rest.strip(), stated_by, date)
    if word in ("allow", "exclude"):
        sub = rest.split(None, 1)
        if len(sub) < 2:
            raise ValueError(usage)
        kind = "allow_violation" if word == "allow" else "restore_exclusion"
        return TaskChange(kind, sub[0], sub[1].strip(), stated_by, date)
    if word == "tolerance":
        sub = rest.split(None, 2)
        if len(sub) < 3:
            raise ValueError(usage)
        try:
            value = float(sub[1])
        except ValueError:
            raise ValueError(f"the tolerance {sub[1]!r} is not a number; {usage}") from None
        return TaskChange("set_tolerance", sub[0], sub[2].strip(), stated_by, date, value=value)
    raise ValueError(usage)


def _num(x: Any) -> str:
    return "–" if not isinstance(x, (int, float)) else f"{x:.4g}"


def round_summary_text(report_dir: str | Path, round_number: int, pool_version: int, output: tuple[str, str] | None = None) -> str | None:
    """The results of a round as a short text for the terminal: one line per model in the agent's
    order with its training and test error, the agent's recommendation, and the files that hold
    the complete report. ``None`` when ``evaluation.json`` in ``report_dir`` cannot be read.

    The text contains results on the sealed test data; it is shown to the user and never to the agent.
    """
    folder = Path(report_dir)
    try:
        ev = json.loads((folder / "evaluation.json").read_text(encoding="utf-8"))
        cands = sorted(ev["candidates"], key=lambda c: c.get("position") or 10**6)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    name, unit = output or (str((ev.get("settings") or {}).get("measurement") or "the output"), "")
    u = f" ({unit})" if unit and unit not in ("-", "unit not supplied") else ""
    rec = ev.get("recommendation") or {}
    agent = rec.get("agent") or {}
    recommended = agent.get("label") if rec.get("present", True) else None
    entries = (((ev.get("sealed") or {}).get("ranking") or {}).get("entries")) or []
    best = entries[0]["label"] if entries else None
    rows = [("Model", "Fitted parameters", f"Training error of {name}{u}", f"Test error of {name}{u}", "")]
    for c in cands:
        sealed = c.get("sealed") or {}
        notes = []
        if c.get("label") == recommended:
            notes.append("recommended by the agent")
        if c.get("label") == best:
            notes.append("lowest test error")
        if c.get("status") != "evaluated":
            notes.append("not evaluated: " + str(c.get("status") or "").replace("_", " "))
        elif not sealed.get("eligible"):
            notes.append("excluded")
        rows.append((str(c.get("label")), str((c.get("complexity") or {}).get("fitted_parameters", "–")),
                     _num(((c.get("visible") or {}).get("train") or {}).get("pooled_rmse")), _num(sealed.get("score_S")), "; ".join(notes)))
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    lines = [f"=== Round {round_number} has ended: {len(cands)} model{'s' if len(cands) != 1 else ''} ==="]
    for i, r in enumerate(rows):
        lines.append("  " + "   ".join(r[j].ljust(widths[j]) for j in range(4)) + ("   " + r[4] if r[4] else ""))
        if i == 0:
            lines.append("  " + "   ".join("-" * widths[j] for j in range(4)))
    lines.append("")
    if recommended:
        lines.append(f"The agent recommends {recommended}. Its reason: {' '.join(str(agent.get('reason') or 'none given').split())}")
    else:
        lines.append("The agent recommends no model." + (f" Its reason: {' '.join(str(agent['reason']).split())}" if agent.get("reason") else ""))
    lines.append("Errors are root mean squared errors. The agent recommends from the training data; the model with the lowest test "
                 "error is found with the test data, in hindsight, and the agent could not make this choice.")
    if ev.get("test_informed"):
        lines.append("This round is test-informed: you had seen test errors before it started, so its test errors are not errors on unseen data.")
    page = folder.parent.parent / "report" / f"round{int(pool_version)}.html"
    lines.append("")
    if page.is_file():
        lines.append(f"Models, equations, plots and the course of the round (open in a browser): {page.resolve().as_uri()}")
    lines.append(f"Complete evaluation report of the harness: {folder / 'evaluation.md'}")
    return "\n".join(lines)


class TerminalProgress(EventSink):
    """Progress lines of ``aspire session`` on the terminal: one line per response of the agent,
    with the turn number, the execution time of the round and what the response did, and one line
    per check and evaluation of the harness. The lines are derived from the events by plain code
    (:func:`aspire_sysid.report.html_report.action_text_plain`); nothing is recorded here."""

    def __init__(self, out: TextIO) -> None:
        self.out = out
        self.turn = 0
        self.exchange_text = self.ANALYSIS_TEXT

    ANALYSIS_TEXT = "The agent is working on your analysis request. One line per response of the agent:"
    INTERVIEW_TEXT = ("The agent is preparing the task. One line per response of the agent: turn, execution time (min:s), "
                      "action. It will ask you questions.")

    def _print(self, text: str) -> None:
        self.out.write(text + "\n")
        self.out.flush()

    def emit(self, kind: str, **fields: Any) -> None:
        """Print the progress line of one event, if it has one."""
        from ..report.html_report import action_text_plain, clock

        agent = str(fields.get("agent") or "main")
        helper = agent not in ("main", "harness", "None")
        when = clock(fields.get("elapsed_s"))
        if kind == "round_start" and not helper:
            self.turn = 0
            self._print("")
            if fields.get("mode") == "exchange":
                self._print(self.exchange_text)
            else:
                self._print(f"=== Round {fields.get('round')} has started ===")
                self._print("The agent is working. One line per response of the agent: turn, execution time (min:s), action.")
        elif kind == "response":
            if not helper:
                self.turn += 1
            who = f"helper {agent}" if helper else f"turn {self.turn:>2}"
            text = action_text_plain(fields)
            self._print(f"  {who} · {when} · {text}")
        elif kind == "request_error":
            self._print(f"  harness · {when} · a request to the language model failed: {fields.get('error') or fields.get('message') or ''}")
        elif kind == "check_outcome":
            n = len(fields.get("candidates") or fields.get("evaluated") or [])
            self._print(f"  harness · {when} · checked the files of {n} model{'s' if n != 1 else ''}: {'passed' if fields.get('passed') else 'failed'}")
        elif kind == "evaluation" and fields.get("status") == "started":
            self._print(f"  harness · {when} · evaluating the models on the training and the test data")
        elif kind in ("reminder", "budget_termination"):
            what = "reminded the agent of the remaining budget" if kind == "reminder" else "a limit ended the round"
            self._print(f"  harness · {when} · {what}")


class TerminalChannel(UserChannel):
    """The user's side of a session on a text terminal (``aspire session``).

    Questions, reports and answers are written to ``out``; the user's texts are read from ``inp``.
    A text ends with a line that contains only a full stop; a text without content declines a
    question. Every input is acknowledged with a line that starts with ``[received]`` and says what
    happens next, so that the user is never left with a silent terminal after typing. At the end of the input
    (end of file), open questions are declined and the session ends at the user's request.
    ``user`` names the user in the record of task changes (who stated an
    instruction and when).
    """

    def __init__(self, inp: TextIO, out: TextIO, *, user: str = "the user", today: Callable[[], str] | None = None,
                 output: tuple[str, str] | None = None) -> None:
        self.inp = inp
        self.out = out
        self.user = user
        self.output = output  # name and unit of the scored output, for the summary of a round
        self._today = today or (lambda: _dt.date.today().isoformat())
        self.eof = False

    # -- terminal helpers ------------------------------------------------------------------

    def _print(self, text: str = "") -> None:
        self.out.write(text + "\n")
        self.out.flush()

    def _readline(self) -> str | None:
        if self.eof:
            return None
        line = self.inp.readline()
        if line == "":
            self.eof = True
            return None
        return line.rstrip("\r\n")

    def _read_text(self, prompt: str, note: str = "") -> str:
        """Read a text of one or more lines; a line that contains only a full stop ends it."""
        self._print(prompt + f" End it with a line containing only '{END_OF_TEXT}'." + note)
        lines: list[str] = []
        while True:
            line = self._readline()
            if line is None or line.strip() == END_OF_TEXT:
                break
            lines.append(line)
        return "\n".join(lines).strip("\n")

    def _received(self, text: str) -> None:
        """Acknowledge an input, so that the user knows that the harness has it and what happens next
        (the next output can take a while: the agent's response, an evaluation)."""
        self._print(f"[received] {text}")

    # -- interface -------------------------------------------------------------------------

    def ask(self, question: str, decision: str | None) -> str | None:
        """Print the agent's question and read the answer; an empty answer declines."""
        self._print("")
        self._print("=== The agent asks a question ===")
        self._print(question)
        if decision:
            self._print(f"Decision affected, as stated by the agent: {decision}")
        answer = self._read_text("Type your answer.", f" To give no answer, type only '{END_OF_TEXT}'.")
        if answer.strip():
            self._received("Your answer was passed to the agent. The agent continues.")
            return answer
        self._received("No answer. The agent was told that you gave none and continues.")
        return None

    def confirm_task(self, brief: str, summary: str = "") -> "bool | str":
        """Print the agent's summary and the task brief, and read the verdict: ``y`` accepts, ``q`` stops,
        any other text is a request for changes (several lines end with a line containing only a full
        stop). At the end of the input the session stops: an identification never starts unconfirmed."""
        self._print("")
        if summary.strip():
            self._print("=== The agent's summary of the task ===")
            self._print(summary.strip())
            self._print("")
        self._print("=== The task as the identification agent will receive it (TASK.md) ===")
        self._print(brief.rstrip())
        self._print("")
        self._print("Type y and press Enter to start the identification with this task, or q to stop here (the task folder is kept).")
        self._print(f"To change something, describe the change instead and end it with a line containing only '{END_OF_TEXT}'.")
        while True:
            line = self._readline()
            if line is None:
                return False
            word = line.strip().lower()
            if word in ("y", "yes"):
                self._received("The task is accepted. The identification starts.")
                return True
            if word in ("q", "quit"):
                self._received("Stopped. The identification does not start; the task folder is kept.")
                return False
            if not word or word == END_OF_TEXT:
                self._print("Please type y, q, or the change you want.")
                continue
            lines = [line]
            while True:
                more = self._readline()
                if more is None or more.strip() == END_OF_TEXT:
                    break
                lines.append(more)
            self._received("Your change request was passed to the agent, which continues the preparation of the task.")
            return "\n".join(lines).strip("\n")

    def show_report(self, round_number: int, pool_version: int, report_markdown: str, report_dir: str | None) -> None:
        """Print the results of the round as a short table, test errors included, and name the files
        with the complete evaluation report ("After each round, the user receives the
        complete evaluation report"). The complete report is ``evaluation.md`` in ``report_dir``
        and the page of the round in the HTML report of the session; when the evaluation file
        cannot be read, the complete report is printed instead."""
        self._print("")
        summary = None if not report_dir else round_summary_text(report_dir, round_number, pool_version, self.output)
        if summary is None:
            self._print(f"=== Evaluation report of round {round_number}, pool version {pool_version} (includes sealed test results) ===")
            if report_dir:
                self._print(f"Files: {report_dir}")
            self._print(report_markdown)
            return
        self._print(summary)

    def show_text(self, title: str, text: str) -> None:
        """Print a titled text."""
        self._print("")
        self._print(f"=== {title} ===")
        self._print(text)

    def choose(self, context: ChoiceContext) -> UserAction:
        """Offer the three choices (analysis request, new round, end) and read the user's choice and texts."""
        while True:
            self._print("")
            self._print(
                f"Remaining for this session: {context.remaining}. One analysis request may use up to "
                f"{context.analysis_limits}."
            )
            self._print("What next? Type one letter and press Enter:")
            self._print("  a  ask the agent for an analysis or an explanation (the models stay as they are)")
            self._print("  r  start a new identification round with your feedback")
            self._print("  e  end the session")
            line = self._readline()
            if line is None:
                return UserAction("end")
            choice = line.strip().lower()
            if choice in ("e", "end"):
                self._received("The session ends. The harness writes the record and the report; this can take a moment.")
                return UserAction("end")
            if choice in ("a", "analysis"):
                text = self._read_text("Type your analysis request.")
                if not text.strip():
                    self._print("An analysis request needs a text.")
                    continue
                self._received("Your analysis request was passed to the agent.")
                return UserAction("analysis", text)
            if choice in ("r", "round"):
                text = self._read_text("Type your feedback for the new round.")
                self._received("Your feedback is recorded." if text.strip() else "No feedback text.")
                changes = self._read_changes(context)
                n = len(changes)
                self._received((f"{n} task change{'s' if n != 1 else ''} recorded. " if n else "No task change. ") + "A new round starts.")
                return UserAction("new_round", text, tuple(changes))
            self._print("Please type a, r or e.")

    def _read_changes(self, context: ChoiceContext) -> list[TaskChange]:
        ids = ", ".join(context.requirement_ids) or "none"
        self._print(
            "Task changes that take effect with the new round, one per line (formal requirements: "
            f"{ids}): 'allow <id> <instruction>', 'exclude <id> <instruction>', 'tolerance <id> <value> <instruction>', "
            f"'require <text>'. End the list with a line containing only '{END_OF_TEXT}'; if you have no change, type only '{END_OF_TEXT}'."
        )
        changes: list[TaskChange] = []
        while True:
            line = self._readline()
            if line is None or line.strip() == END_OF_TEXT:
                return changes
            if not line.strip():
                continue
            try:
                changes.append(parse_change_line(line, stated_by=self.user, date=self._today()))
                self._received(f"Task change {len(changes)} recorded.")
            except ValueError as exc:
                self._print(f"Not recorded: {exc}.")
