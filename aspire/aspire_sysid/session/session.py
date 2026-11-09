"""An interactive session: rounds, analysis exchanges, pool versions and the session budget.

A session contains one round in autonomous operation, or several rounds and intervening analyses
in interactive operation. This module implements interactive operation on top of the turn loop
(:func:`aspire_sysid.agent.run_round`, :func:`aspire_sysid.agent.run_analysis_exchange`), the
prompts and working directory of the brief, the file and expression checks and the evaluation.

**Sequence** (:meth:`Session.run`):

0. **Two folders.** The session record (``out_dir``) and the agent's working directory are kept
   apart: the working directory is ``<workspace_root>/<random>/workspace``, by default
   under ``<system temporary folder>/aspire-sessions``, and :func:`check_separation` refuses a record
   inside the folder of the working directory or a working directory inside the record. The
   complete reports, which contain sealed results, are written to the record only. At the end of
   the session the final working directory is copied to ``<out_dir>/workspace/`` and the working
   copy is removed.
1. The harness provisions the working directory with the brief of interactive operation, renders
   the system prompt with the interactive paragraph and starts round 1 with
   the first user message. The agent may call ``ask_user`` (:mod:`.ask_user`).
2. After each round the harness (a) copies ``models/`` to ``pools/v<k>/models/`` of the session
   folder with :func:`aspire_sysid.record.snapshot_pool`, so that every pool
   version is preserved and never overwritten; (b) records the
   agent's recommendation of the round (``pools/v<k>/recommendation.json`` and the event
   ``recommendation_recorded``) **before** any test result of the round is disclosed; (c) writes the complete evaluation report (``evaluation/v<k>/``); (d) builds
   the permitted results (:mod:`.permitted`), appends the round-completion message
   to the conversation, and writes what the agent receives to
   ``pools/v<k>/agent_results.json`` (the sent text and blocks, the screen findings and the
   permitted structure before the screen) and ``pools/v<k>/agent_results.txt`` (the sent text);
   (e) shows the complete report to the user and, when it contains a sealed result (test results or
   a reference comparison), records the event ``user_shown_sealed_results``. The complete report of
   a round carries the round's label test-informed or not test-informed (header of
   ``evaluation.md``, field ``test_informed`` of ``evaluation.json`` and of its recommendation).
3. The user then chooses (:class:`~aspire_sysid.session.channel.UserChannel`): an analysis
   request (step 4), a new identification round (step 5) or the end of the session (step 6).
   Before every choice the harness tests the session budget; when it is reached, the session
   ends (step 6).
4. **Analysis exchange.** The analysis-request message starts
   :func:`~aspire_sysid.agent.run_analysis_exchange` with the task's analysis-exchange limits
   (``budget.analysis_exchange``; when the task declares none, the remaining session allowance),
   charged to the session totals. The exchange ends with the agent's completed answer, defined
   as its first response without a tool request (with or without the word ``DONE``); the
   continuation message of rounds does not apply. The exchange creates no pool version; a change
   of ``models/`` during the exchange is recorded (``models_changed``) and becomes part of the
   next round's working directory only. The answer is shown to the user.
5. **New round.** The user's task changes (:mod:`.changes`) take effect with the new round and
   are recorded with it. The harness rewrites ``check_config.json`` with the new pool version and
   the labels of the previous pool version (the field ``predecessor`` of a revised candidate must
   name one of them; rule F1 of the file check); after a task change it rewrites ``TASK.md`` for the effective
   task and records the new digest (event ``brief_regenerated``); it starts the round with the new-round message:
   previous pool, permitted results (a summary, :func:`.permitted.permitted_summary`, whose
   details are in the round-completion message of the previous round), the user's feedback
   verbatim, all task changes in force with their sources and rounds, the label "test-informed"
   or "not test-informed", the round limits and the remaining session allowance. The
   conversation continues: the agent keeps its history of the earlier rounds and exchanges.
6. **Session end** on the user's request or at the session budget: the session-completion
   message (reason, completed pool versions, unfinished work, resource use) is
   appended to the conversation, recorded and shown to the user; ``session.json`` states the
   termination reason, the unfinished work and the consumed resources. Completed models remain in
   ``pools/``. The session folder is a run folder (:mod:`aspire_sysid.record`): the transcript
   ``transcript.jsonl`` is written during the session (every event, session events included), and
   ``run_record.json`` with ``provenance.json`` at its end (one entry per round and per analysis
   exchange, with the label test-informed, the pool snapshot, the stored reports and the task changes
   in force), so that ``aspire record verify`` recomputes each pool version and ``aspire export``
   exports it.

The harness *sends* its execution messages to the agent: a message is
sent with the next request to the language model. The round-completion message of the last round
and the session-completion message are appended to the conversation and recorded, but no further
request follows them, so the language model never receives them.

**Test-informed label**. Once the user has been shown a report with any result on
sealed data, test results or a reference comparison, every
later round, its recommendation and every later analysis exchange carry
``test_informed: true``, whatever the user's message contains; the user's texts are kept
verbatim.

**Budget and time.** One :class:`SessionTracker` per session with the task's session limits is
the parent of every round's and exchange's tracker, so every turn and every cost counts toward
the session totals when it occurs, and a session limit ends a round or an exchange like its own
limit. The session's elapsed execution time is the sum of the elapsed execution times of
its rounds and exchanges; the harness's own work between them (checks and evaluation after a
round, reports) is recorded separately as ``harness_s`` and does not consume the session
allowance, in the same way as the round's final checks do not consume the round's. Every
interaction with the user runs with the execution clock paused; its duration is user waiting
time, recorded per question, per round and for the session.

**Sealing.** The session never passes a sealed path to the agent's tools; the only results that
reach the agent pass the whitelist and the leak screen of :mod:`.permitted`; a withheld part is
replaced by the neutral notice :data:`WITHHELD`, and the reason is kept in the record. The complete
report goes to the user and to the record, outside the working directory's folder. Limit: the
separation is by location only; a program of the agent can read any absolute path that the
operating-system user of the harness can read, so real runs must place the record root where that
user's agent commands cannot reach it (aspire/README.md).
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from .. import __version__
from ..agent.budget import BudgetTracker, ExecutionClock, LimitHit, format_remaining, format_seconds, format_turns, format_usd
from ..agent.config import ToolConfig
from ..agent.events import SESSION_EVENT_KINDS, EventSink, FanoutSink, NullSink
from ..agent.loop import RoundLabels, RoundResult, run_analysis_exchange, run_round
from ..agent.prices import PriceTable
from ..agent.probe import EnvironmentProbe
from ..agent.providers import Provider, UserMessage
from ..agent.tools import PipRunner, ToolRegistry, WebBackends, build_registry
from ..brief import messages as msg
from ..brief.render import BRIEF_FILE, render_brief
from ..brief.workspace import provision_workspace, render_run_texts
from ..evaluate import evaluate_pool, render_markdown, write_reports
from ..evaluate.leaks import sealed_fingerprint
from ..evaluate.report import to_json
from ..record import TRANSCRIPT_FILE, RoundEntry, TranscriptWriter, evaluation_dir, snapshot_pool, write_run_record
from ..model import write_check_files
from ..model.checks import MODELS_DIR, CheckReport
from ..task.schema import Limits, TaskSpec
from .ask_user import QuestionRecord, make_ask_user_tool
from .changes import TaskChange, TaskChangeError, apply_changes, describe_changes
from .channel import ChoiceContext, UserAction, UserChannel
from .permitted import permitted_results, permitted_summary, render_permitted_blocks, render_permitted_text, screen_blocks

__all__ = [
    "SESSION_EVENT_KINDS",
    "TERMINATION_REASONS",
    "SessionTracker",
    "RoundRecord",
    "ExchangeRecord",
    "SessionResult",
    "Session",
    "limits_text",
    "quote_verbatim",
    "check_separation",
    "sealed_result_kinds",
    "limit_phrase",
    "WITHHELD",
]

TERMINATION_REASONS: tuple[str, ...] = ("user_request", "session_limit")
"""Why a session ends: the user's request or the session budget."""


WITHHELD = "withheld by the harness"
"""The neutral notice that replaces a withheld part of the permitted results; the
reason is kept in the record only."""


def _within(path: Path, folder: Path) -> bool:
    try:
        path.relative_to(folder)
        return True
    except ValueError:
        return False


def check_separation(record_dir: str | Path, workspace: str | Path, workspace_root: str | Path | None = None) -> None:
    """Refuse a layout in which the session record, which holds the complete reports with sealed
    results, lies inside the workspace root (when given) or the folder that contains the working
    directory, or the working directory lies inside the record. Raises
    :class:`ValueError`.

    The check is by path only: an absolute path readable by the operating-system user of the harness
    remains readable by the agent's commands (aspire/README.md, "Interactive operation").
    """
    rec = Path(record_dir).resolve()
    ws = Path(workspace).resolve()
    if workspace_root is not None and _within(rec, Path(workspace_root).resolve()):
        raise ValueError(
            f"the session record {rec} lies inside the workspace root {Path(workspace_root).resolve()}; the complete reports "
            "would lie next to the working directories of the agent"
        )
    if _within(rec, ws.parent):
        raise ValueError(
            f"the session record {rec} lies inside {ws.parent}, the folder of the working directory; the complete "
            "reports would be reachable from the working directory"
        )
    if _within(ws, rec):
        raise ValueError(f"the working directory {ws} lies inside the session record {rec}")


def sealed_result_kinds(evaluation: Any) -> list[str]:
    """The kinds of sealed results in a complete report: ``test_results`` and ``reference_comparison``
    (any of them shown to the user makes later rounds test-informed)."""
    kinds = []
    if evaluation.test_trajectories:
        kinds.append("test_results")
    if any(c.sealed.reference is not None for c in evaluation.candidates):
        kinds.append("reference_comparison")
    return kinds


_KIND_WORD = {"turns": "turn", "time": "execution-time", "cost": "cost"}
_SCOPE_WORD = {"analysis": "analysis exchange", "round": "round", "session": "session"}


def limit_phrase(hit: LimitHit) -> str:
    """``"the turn limit of the analysis exchange"`` (wording of a reached limit)."""
    return f"the {_KIND_WORD.get(hit.kind, hit.kind)} limit of the {_SCOPE_WORD.get(hit.scope, hit.scope)}"


def quote_verbatim(text: str) -> str:
    """The user's text, unchanged, between double quotation marks, so that the message's own
    punctuation stays apart from it (the feedback is preserved verbatim)."""
    return f'"{text}"'


def limits_text(limits: Limits) -> str:
    """``"60 turns, 3600 s of execution time, 5.00 USD"`` (limits as the execution messages state them)."""
    return f"{format_turns(limits.turns)}, {format_seconds(limits.seconds)}, {format_usd(limits.usd)}"


class SessionTracker(BudgetTracker):
    """The budget tracker of a session: a session limit covers all rounds and intervening
    analyses.

    Turns, tokens and cost are charged by the rounds and exchanges, whose trackers have this one
    as parent. The elapsed execution time is the sum of the elapsed times of the rounds and
    exchanges: :meth:`open_scope` before a round or exchange, :meth:`close_scope` with its final
    elapsed time afterwards; between them the harness's own work is not counted (module
    docstring). The user waiting time is the paused time of the execution clock since the start
    of the session.
    """

    def __init__(self, limits: Limits, clock: ExecutionClock) -> None:
        super().__init__(limits, clock, scope="session")
        self._closed_s = 0.0
        self._open_at: float | None = None

    def open_scope(self) -> None:
        """Start counting the execution time of a round or exchange."""
        if self._open_at is not None:
            raise RuntimeError("a round or exchange of the session is already running")
        self._open_at = self.clock.elapsed()

    def close_scope(self, elapsed_s: float | None = None) -> None:
        """Add the elapsed execution time of the finished round or exchange.

        ``elapsed_s`` is the round's frozen elapsed time; ``None`` adds the time measured since
        :meth:`open_scope` (used when the round raised an error).
        """
        if self._open_at is None:
            raise RuntimeError("no round or exchange of the session is running")
        live = self.clock.elapsed() - self._open_at
        self._closed_s += live if elapsed_s is None else float(elapsed_s)
        self._open_at = None

    @property
    def elapsed_s(self) -> float:  # type: ignore[override]
        """Elapsed execution time of the session's rounds and exchanges, in seconds."""
        if self._frozen is not None:
            return self._frozen[0]
        live = (self.clock.elapsed() - self._open_at) if self._open_at is not None else 0.0
        return self._closed_s + live

    def freeze(self) -> None:
        """Fix the session's elapsed and waiting times at the end of the session."""
        if self._frozen is None:
            self._frozen = (self.elapsed_s, self.clock.waiting_s() - self._start_waiting)


@dataclass
class RoundRecord:
    """The record of one round of a session."""

    round: int
    pool_version: int
    test_informed: bool
    first_message: str
    feedback: str | None
    changes: list[dict[str, Any]]
    previous_labels: list[str]
    result: RoundResult | None = None
    questions: list[QuestionRecord] = field(default_factory=list)
    predecessors: dict[str, str | None] = field(default_factory=dict)
    recommendation: dict[str, Any] | None = None
    pool_dir: str | None = None
    report_dir: str | None = None
    agent_results_text: str | None = None
    agent_results: dict[str, Any] | None = None
    screened_findings: list[dict[str, str]] = field(default_factory=list)
    completion_message: str | None = None
    user_shown_sealed_results: list[str] = field(default_factory=list)
    brief_sha256: str | None = None
    summary_screen_findings: list[dict[str, str]] = field(default_factory=list)
    evaluation: Any = None
    harness_s: float = 0.0

    @property
    def evaluated_labels(self) -> list[str]:
        """The labels evaluated in this round."""
        return list(self.result.evaluated_labels) if self.result is not None else []

    @property
    def completed(self) -> bool:
        """True when at least one candidate of this pool version was evaluated: a completed pool version."""
        return bool(self.evaluated_labels) and self.evaluation is not None

    def labels(self) -> list[str]:
        """The labels of this pool version: the pool file's order, or every candidate file when the
        pool file is missing or invalid (predecessor links of the next round)."""
        rep: CheckReport | None = self.result.check_report if self.result is not None else None
        if rep is None:
            return []
        if rep.order_from_pool:
            return list(rep.order)
        return sorted(rep.candidates)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for ``session.json``."""
        r = self.result
        d: dict[str, Any] = {
            "round": self.round,
            "pool_version": self.pool_version,
            "test_informed": self.test_informed,
            "first_message": self.first_message,
            "feedback": self.feedback,
            "task_changes_taking_effect": self.changes,
            "previous_labels": self.previous_labels,
            "questions": [q.to_dict() for q in self.questions],
            "predecessors": self.predecessors,
            "recommendation": self.recommendation,
            "pool_dir": self.pool_dir,
            "report_dir": self.report_dir,
            "agent_results_screened_findings": self.screened_findings,
            "completion_message": self.completion_message,
            "user_shown_sealed_results": list(self.user_shown_sealed_results),
            "brief_sha256": self.brief_sha256,
            "new_round_summary_screen_findings": self.summary_screen_findings,
            "harness_s": self.harness_s,
        }
        if r is not None:
            d.update(
                {
                    "outcome": r.outcome,
                    "limit": None if r.limit is None else {"kind": r.limit.kind, "scope": r.limit.scope},
                    "turns": r.turns,
                    "input_tokens": r.usage.input_tokens,
                    "output_tokens": r.usage.output_tokens,
                    "cost_usd": r.cost_usd,
                    "elapsed_s": r.elapsed_s,
                    "waiting_s": r.waiting_s,
                    "excess": r.excess,
                    "estimated_usage_turns": r.estimated_usage_turns,
                    "correction_used": r.correction_used,
                    "done_count": r.done_count,
                    "reminder_sent": r.reminder_sent,
                    "candidate_files": r.candidate_files.to_dict(),
                    "evaluated_labels": list(r.evaluated_labels),
                    "order_assigned_by_harness": r.order_assigned_by_harness,
                    "checks_s": r.checks_s,
                    "evaluation_s": r.evaluation_s,
                    "error": r.error,
                    "termination_message": r.termination_message,
                    "helpers": [dataclasses.asdict(h) for h in r.helpers],
                }
            )
        return d


@dataclass
class ExchangeRecord:
    """The record of one analysis exchange."""

    index: int
    after_round: int
    pool_version: int
    test_informed: bool
    request: str
    message: str
    limits: dict[str, Any]
    result: RoundResult | None = None
    answer: str | None = None
    questions: list[QuestionRecord] = field(default_factory=list)
    models_changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for ``session.json``."""
        r = self.result
        d: dict[str, Any] = {
            "index": self.index,
            "after_round": self.after_round,
            "pool_version": self.pool_version,
            "test_informed": self.test_informed,
            "request": self.request,
            "message": self.message,
            "limits": self.limits,
            "answer": self.answer,
            "questions": [q.to_dict() for q in self.questions],
            "models_changed": self.models_changed,
        }
        if r is not None:
            d.update(
                {
                    "outcome": r.outcome,
                    "limit": None if r.limit is None else {"kind": r.limit.kind, "scope": r.limit.scope},
                    "turns": r.turns,
                    "input_tokens": r.usage.input_tokens,
                    "output_tokens": r.usage.output_tokens,
                    "cost_usd": r.cost_usd,
                    "elapsed_s": r.elapsed_s,
                    "waiting_s": r.waiting_s,
                    "excess": r.excess,
                    "error": r.error,
                }
            )
        return d


@dataclass
class SessionResult:
    """The outcome of a session: termination reason, records and totals."""

    reason: str
    limit: LimitHit | None
    rounds: list[RoundRecord]
    exchanges: list[ExchangeRecord]
    totals: dict[str, Any]
    completion_message: str
    unfinished: list[str]
    out_dir: Path

    @property
    def completed_pool_versions(self) -> list[int]:
        """The pool versions with at least one evaluated candidate."""
        return [r.pool_version for r in self.rounds if r.completed]


def _code_revision() -> dict[str, Any]:
    from ..record import code_revision

    return code_revision()


def _models_digest(ws: Path) -> str:
    h = hashlib.sha256()
    models = ws / MODELS_DIR
    if models.is_dir():
        for p in sorted(models.rglob("*")):
            if p.is_file():
                h.update(p.relative_to(models).as_posix().encode("utf-8") + b"\0")
                h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


class Session:
    """One interactive session on one task (module docstring).

    ``out_dir`` is the session record folder (absent or empty), a run folder:
    ``transcript.jsonl``, ``pools/v<k>/`` and ``evaluation/v<k>/`` per pool version, ``session.json``
    and, at the end of the session, ``run_record.json``, ``provenance.json`` and ``workspace/``, a copy
    of the final working directory. ``isolate_environment`` derives the agent's shell environment as
    the experiment runner does (used by ``aspire session``); ``fsync`` is passed to the transcript
    writer; ``extra_record`` is added to the ``extra`` field of the run record. The agent's working directory itself lives outside the record, in
    ``<workspace_root>/<random>/workspace`` (``workspace_root`` defaults to
    ``<system temporary folder>/aspire-sessions``); :meth:`start` refuses a record folder that lies
    inside the folder that contains the working directory, and a working directory inside the record
    folder, so that the complete reports, which contain sealed results, are never written next to or
    below the working directory. ``channel`` is the user's
    side (:class:`~aspire_sysid.session.channel.UserChannel`); ``sink`` receives every event
    (the transcript writer of :mod:`aspire_sysid.record`). The remaining arguments are those of
    :func:`aspire_sysid.agent.run_round`. ``plots`` draws the plots of the complete report.
    """

    def __init__(
        self,
        task: TaskSpec,
        provider: Provider,
        config: ToolConfig,
        channel: UserChannel,
        out_dir: str | Path,
        *,
        sink: EventSink | None = None,
        session_id: str = "session-1",
        probe: EnvironmentProbe | None = None,
        python_executable: str | None = None,
        clock: ExecutionClock | None = None,
        price_table: PriceTable | None = None,
        web: WebBackends | None = None,
        pip_runner: PipRunner | None = None,
        wall_clock: Callable[[], _dt.datetime] | None = None,
        base_env: Mapping[str, str] | None = None,
        plots: bool = True,
        workspace_root: str | Path | None = None,
        isolate_environment: bool = False,
        fsync: bool = True,
        extra_record: Mapping[str, Any] | None = None,
    ) -> None:
        self.task = task
        self.effective_task = task
        self.provider = provider
        self.config = config
        self.channel = channel
        self.out_dir = Path(out_dir)
        self.sink: EventSink = sink or NullSink()
        self.report_index: Path | None = None
        self.report_error: str | None = None
        self._external_sink = self.sink
        self.transcript: TranscriptWriter | None = None
        self.fsync = fsync
        self.isolate_environment = isolate_environment
        self.environment_note: dict[str, Any] | None = None
        self.extra_record = dict(extra_record or {})
        self._entries: list[RoundEntry] = []
        self.run_record: dict[str, Any] | None = None
        self.session_id = session_id
        self.probe = probe
        self.python_executable = python_executable
        self.clock = clock or ExecutionClock()
        self.price_table = price_table
        self.web = web
        self.pip_runner = pip_runner
        self.wall_clock = wall_clock or (lambda: _dt.datetime.now(_dt.timezone.utc))
        self.base_env = base_env
        self.plots = plots
        self.tracker = SessionTracker(task.budget.session, self.clock)
        self.workspace_root = Path(workspace_root) if workspace_root is not None else Path(tempfile.gettempdir()) / "aspire-sessions"
        from ..experiment.workspace import opaque_attempt_folder

        # <root>/<random>/workspace: the path names no task, session, context or configuration (as in the experiment runner)
        self.workspace = opaque_attempt_folder(self.workspace_root) / "workspace"
        self.brief_sha256: str | None = None
        self.messages: list[Any] = []
        self.rounds: list[RoundRecord] = []
        self.exchanges: list[ExchangeRecord] = []
        self.changes: list[tuple[int, TaskChange]] = []
        self.refused_changes: list[dict[str, Any]] = []
        self.test_seen = False
        self.test_seen_at: dict[str, Any] | None = None
        self.harness_s = 0.0
        self._seq = 0
        self._questions: list[QuestionRecord] = []
        self._texts = None
        self._manifest = None
        self._fingerprint = None
        self._started = False
        self.archived_workspace: Path | None = None
        self.result: SessionResult | None = None

    # -- records and events ------------------------------------------------------------------

    @property
    def current_round(self) -> int:
        """The number of the last started round, 0 before round 1 (label of the record)."""
        return len(self.rounds)

    @property
    def current_pool_version(self) -> int:
        """The pool version of the last started round, 0 before round 1 (label of the record)."""
        return self.rounds[-1].pool_version if self.rounds else 0

    def emit(self, kind: str, **fields: Any) -> None:
        """Record one session event with the session's labels."""
        self._seq += 1
        base = {
            "task": self.task.id,
            "session": self.session_id,
            "round": self.current_round,
            "pool_version": self.current_pool_version,
            "agent": "harness",
            "seq": self._seq,
            "timestamp": self.wall_clock().isoformat(),
            "elapsed_s": self.tracker.elapsed_s,
        }
        base.update(json.loads(json.dumps(fields, default=str)))
        self.sink.emit(kind, **base)

    def _write_record(self) -> None:
        (self.out_dir / "session.json").write_text(to_json(self.record()), encoding="utf-8", newline="\n")

    def _report_info(self) -> dict[str, Any]:
        """What the HTML report of the session shows besides the results: the title, the output, the
        columns and the texts that the agent received (agent-visible information only)."""
        from ..brief import format_reference
        from ..task.public import public_view

        out = self.task.column(self.task.output)
        texts = self._texts
        return {
            "title": self.task.title,
            "output": {"name": out.name, "unit": out.unit},
            "columns": list(public_view(self.task).get("columns") or []),
            "tools": list(self.config.tools),
            "reasoning_effort": self.config.requests.reasoning_effort,
            "texts": {} if texts is None else {"brief": texts.brief, "system_prompt": texts.system_prompt,
                                               "first_user_message": texts.first_user_message},
            "format_reference": format_reference(),
        }

    def write_report(self) -> Path | None:
        """Write the session record and the HTML report of the session (``report/index.html`` and one
        page per evaluated round; :mod:`aspire_sysid.report.session_report`). Returns the index page,
        or ``None`` when the report could not be written: a failure of the report never ends a
        session, and its reason is kept in :attr:`report_error`."""
        from ..report.session_report import build_session_report

        self._write_record()
        try:
            self.report_index = build_session_report(self.out_dir)
            self.report_error = None
        except Exception as exc:  # noqa: BLE001 - the report is a convenience for the user; the record is complete without it
            self.report_index = None
            self.report_error = f"{type(exc).__name__}: {exc}"
        return self.report_index

    def record(self) -> dict[str, Any]:
        """The session record written to ``session.json``."""
        texts = self._texts
        return {
            "format_version": 1,
            "task_id": self.task.id,
            "session": self.session_id,
            "operation": "interactive",
            "configuration": self.config.name,
            "model": self.provider.model_id,
            "hashes": dict(texts.hashes) if texts is not None else {},
            "workspace_manifest": self._manifest.to_dict() if self._manifest is not None else None,
            "harness": {"version": __version__, "code_revision": _code_revision()},
            "working_directory": str(self.workspace),
            "working_directory_copy": None if self.archived_workspace is None else str(self.archived_workspace),
            "budget": {
                "round": dataclasses.asdict(self.task.budget.round),
                "session": dataclasses.asdict(self.task.budget.session),
                "analysis_exchange": None if self.task.budget.analysis_exchange is None else dataclasses.asdict(self.task.budget.analysis_exchange),
            },
            "task_changes": [dict(ch.to_dict(), effective_round=rnd) for rnd, ch in self.changes],
            "task_changes_refused": list(self.refused_changes),
            "test_informed_from": self.test_seen_at,
            "report": self._report_info(),
            "rounds": [r.to_dict() for r in self.rounds],
            "exchanges": [e.to_dict() for e in self.exchanges],
            "totals": dict(self.tracker.totals(), harness_s=self.harness_s),
            "termination": None
            if self.result is None
            else {
                "reason": self.result.reason,
                "limit": None if self.result.limit is None else dataclasses.asdict(self.result.limit),
                "unfinished": list(self.result.unfinished),
                "message": self.result.completion_message,
            },
        }

    # -- user interaction (clock paused) -----------------------------------------------------

    def _with_user(self, fn: Callable[[], Any]) -> tuple[Any, float]:
        before = self.clock.waiting_s()
        with self.clock.paused():
            value = fn()
        return value, self.clock.waiting_s() - before

    def _registry(self) -> ToolRegistry:
        reg = build_registry(self.config)
        reg.register(make_ask_user_tool(self.channel, self._questions.append))
        return reg

    def _remaining_text(self) -> str:
        t, s, c = format_remaining(self.tracker.remaining())
        return f"{t}, {s}, {c}"

    def _analysis_limits(self) -> Limits:
        ae = self.task.budget.analysis_exchange
        if ae is not None:
            return ae
        rem = self.tracker.remaining()
        return Limits(turns=rem.turns, seconds=rem.seconds, usd=rem.usd)

    # -- start ---------------------------------------------------------------------------------

    def start(self) -> None:
        """Provision the working directory and render the texts of interactive operation (system prompt and brief)."""
        if self._started:
            raise RuntimeError("the session has already started")
        if self.out_dir.exists() and (not self.out_dir.is_dir() or any(self.out_dir.iterdir())):
            raise FileExistsError(f"the session folder {self.out_dir} exists and is not empty; earlier results are never overwritten")
        from ..experiment.workspace import check_workspace_root

        check_workspace_root(self.workspace_root)  # outside every git repository
        check_separation(self.out_dir, self.workspace, self.workspace_root)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.transcript = TranscriptWriter(
            self.out_dir / TRANSCRIPT_FILE,
            header={"run_id": self.out_dir.name, "session": self.session_id, "operation": "interactive", "task": self.task.id,
                    "configuration": self.config.name, "model": self.provider.model_id, "vendor": self.provider.vendor},
            fsync=self.fsync,
        )
        self.sink = FanoutSink(self.transcript, self._external_sink)
        self._manifest = provision_workspace(self.task, self.workspace, interactive=True)
        if self.isolate_environment:
            from ..experiment.runner import agent_base_environment

            packages = self.workspace.parent / "packages"
            packages.mkdir(parents=True, exist_ok=True)
            self.base_env, self.environment_note = agent_base_environment(packages)
        self.brief_sha256 = self._manifest.brief_sha256
        self._texts = render_run_texts(self.task, self.config, self.probe, interactive=True)
        self._fingerprint = sealed_fingerprint(self.task)
        self._started = True
        self.emit(
            "session_start",
            configuration=self.config.name,
            model=self.provider.model_id,
            limits=dataclasses.asdict(self.task.budget.session),
            round_limits=dataclasses.asdict(self.task.budget.round),
            analysis_exchange_limits=None if self.task.budget.analysis_exchange is None else dataclasses.asdict(self.task.budget.analysis_exchange),
            hashes=dict(self._texts.hashes),
            workspace=str(self.workspace),
            record_dir=str(self.out_dir),
            manifest=self._manifest.to_dict(),
        )
        self._write_record()

    # -- rounds --------------------------------------------------------------------------------

    def _apply_changes(self, round_number: int, changes: tuple[TaskChange, ...]) -> list[TaskChange]:
        applied: list[TaskChange] = []
        for ch in changes:
            try:
                self.effective_task = apply_changes(self.effective_task, [ch])
            except TaskChangeError as exc:
                self.refused_changes.append(dict(ch.to_dict(), round=round_number, reason=str(exc)))
                self.emit("task_change_refused", change=ch.to_dict(), reason=str(exc), effective_round=round_number)
                self._with_user(lambda exc=exc: self.channel.show_text("Task change not applied", str(exc)))
                continue
            self.changes.append((round_number, ch))
            applied.append(ch)
            self.emit("task_change", change=ch.to_dict(), effective_round=round_number, text=ch.text())
        return applied

    def identification_round(self, feedback: str | None = None, changes: tuple[TaskChange, ...] = ()) -> RoundRecord:
        """Run the next identification round and its after-round steps (module
        docstring steps 1, 2 and 5). ``feedback`` is the user's verbatim text (``None`` for round 1)."""
        if not self._started:
            self.start()
        k = self.current_round + 1
        version = k
        test_informed = self.test_seen
        previous_labels: list[str] = []
        applied: list[TaskChange] = []
        summary_findings: list[dict[str, str]] = []
        if k == 1:
            if changes or feedback is not None:
                raise ValueError("round 1 has no feedback and no task changes")
            assert self._texts is not None
            first = self._texts.first_user_message
        else:
            applied = self._apply_changes(k, changes)
            prev = self.rounds[-1]
            previous_labels = prev.labels()
            write_check_files(self.effective_task, self.workspace, pool_version=version, previous_labels=previous_labels, overwrite=True)
            if applied:
                self._regenerate_brief(k)
            if prev.agent_results is not None:
                results = permitted_summary(prev.agent_results)
                _, findings = screen_blocks([("summary", results)], self.task, fingerprint=self._fingerprint)
                if findings:
                    summary_findings = findings
                    results = WITHHELD
                    self.emit("permitted_results_screened", scope="new_round_summary", effective_round=k, findings=findings)
                results += f" (details in the round-completion message of round {prev.round})"
            else:
                results = f"no candidate of pool version {prev.pool_version} was evaluated (details in the round-completion message of round {prev.round})"
            first = msg.render_new_round(
                f"pool version {prev.pool_version} (round {prev.round})",
                results,
                quote_verbatim(feedback if feedback is not None else ""),
                describe_changes(self.changes),
                test_informed,
                limits_text(self.task.budget.round),
                self._remaining_text(),
            )
        rec = RoundRecord(
            round=k,
            pool_version=version,
            test_informed=test_informed,
            first_message=first,
            feedback=feedback,
            changes=[ch.to_dict() for ch in applied],
            previous_labels=previous_labels,
            brief_sha256=self.brief_sha256,
            summary_screen_findings=summary_findings,
        )
        self.rounds.append(rec)
        eval_task = self.effective_task

        def evaluate(report: CheckReport, labels: list) -> Any:
            """Evaluate the checked pool under the task settings of this round."""
            return evaluate_pool(eval_task, report)

        self._questions = rec.questions
        self.tracker.open_scope()
        try:
            result = run_round(
                self.provider,
                self._texts.system_prompt,
                first,
                self.workspace,
                eval_task,
                self.config,
                self.task.budget.round,
                self.sink,
                evaluate_callback=evaluate,
                labels=RoundLabels(task=self.task.id, session=self.session_id, round=k),
                clock=self.clock,
                parent_tracker=self.tracker,
                price_table=self.price_table,
                registry=self._registry(),
                web=self.web,
                pip_runner=self.pip_runner,
                probe=self.probe,
                python_executable=self.python_executable,
                history=self.messages,
                pool_version=version,
                previous_labels=previous_labels,
                wall_clock=self.wall_clock,
                base_env=self.base_env,
            )
        except BaseException:
            self.tracker.close_scope(None)
            raise
        self.tracker.close_scope(result.elapsed_s)
        rec.result = result
        rec.evaluation = result.evaluation
        self.messages = list(result.messages)
        self.harness_s += result.checks_s + result.evaluation_s
        self._after_round(rec, eval_task)
        self._entries.append(RoundEntry(
            result,
            session=self.session_id,
            round=k,
            pool_version=version,
            previous_labels=list(previous_labels),
            evaluation=rec.evaluation if rec.report_dir is not None else None,
            test_informed=test_informed,
            mode="round",
            pool_snapshot=rec.pool_dir,
            reports_dir=rec.report_dir,
            task_changes=[ch.to_dict() for rnd, ch in self.changes if rnd <= k],
        ))
        self._write_record()
        return rec

    def _after_round(self, rec: RoundRecord, eval_task: TaskSpec) -> None:
        """Preserve the pool version, record the recommendation, write the reports, send the
        permitted results and show the complete report (module docstring, step 2)."""
        result = rec.result
        assert result is not None
        started = self.clock.now()
        # (a) the pool version, copied by snapshot_pool (never overwritten; snapshot.json lists the digests)
        pool_dir = snapshot_pool(self.out_dir, self.workspace, rec.pool_version, session=self.session_id, round=rec.round)
        rec.pool_dir = str(pool_dir)
        report = result.check_report
        if report is not None:
            rec.predecessors = {
                lab: (res.candidate.predecessor if res.candidate is not None else None)
                for lab, res in sorted(report.candidates.items())
            }
        self.emit(
            "pool_version_saved",
            pool_dir=str(pool_dir),
            files=sorted(p.relative_to(pool_dir).as_posix() for p in pool_dir.rglob("*") if p.is_file()),
            predecessors=rec.predecessors,
            previous_labels=rec.previous_labels,
        )

        # (b) the recommendation, recorded before any test result of the round is disclosed
        pool = report.pool if report is not None else None
        recommendation = None if pool is None else pool.recommendation
        rec.recommendation = {
            "round": rec.round,
            "pool_version": rec.pool_version,
            "recommendation": None if recommendation is None else dict(recommendation),
            "pool_file_valid": bool(report is not None and report.pool_ok),
            "test_informed": rec.test_informed,
            "recorded_before_test_disclosure": True,
            "recorded_at": self.wall_clock().isoformat(),
        }
        (pool_dir / "recommendation.json").write_text(to_json(rec.recommendation), encoding="utf-8", newline="\n")
        self.emit("recommendation_recorded", **rec.recommendation)

        # (c) the complete report (sealed results included), for the user
        ev = rec.evaluation
        report_md = None
        if ev is not None:
            report_dir = evaluation_dir(self.out_dir, rec.pool_version)
            if report_dir.exists():
                raise FileExistsError(f"{report_dir} exists; an evaluation is never overwritten")
            write_reports(ev, eval_task, report_dir, plots=self.plots, test_informed=rec.test_informed)
            rec.report_dir = str(report_dir)
            report_md = render_markdown(ev, eval_task, include_sealed=True, test_informed=rec.test_informed)

        # (d) the permitted results and the round-completion message
        if ev is not None:
            permitted = permitted_results(ev, eval_task, pool_version=rec.pool_version)
            rec.agent_results = permitted
            blocks = render_permitted_blocks(permitted)
        else:
            check_text = report.text() if report is not None else f"the checks could not be run ({result.error})"
            blocks = [(
                "checks",
                f"Pool version {rec.pool_version}: no candidate was evaluated (round outcome {result.outcome}). "
                f"File and expression checks:\n{check_text}",
            )]
        screened, findings = screen_blocks(blocks, self.task, fingerprint=self._fingerprint)
        rec.screened_findings = findings
        if findings:
            self.emit("permitted_results_screened", scope="round_completion", findings=findings)
        text = render_permitted_text(screened)
        rec.agent_results_text = text
        record = {
            "round": rec.round,
            "pool_version": rec.pool_version,
            "sent_text": text,
            "sent_blocks": [{"block": label, "text": t} for label, t in screened],
            "screen_findings": findings,
            "withheld_blocks": sorted({f["block"] for f in findings}),
            "permitted_before_screen": rec.agent_results,
        }
        (pool_dir / "agent_results.json").write_text(to_json(record), encoding="utf-8", newline="\n")
        (pool_dir / "agent_results.txt").write_text(text, encoding="utf-8", newline="\n")
        completion = msg.render_round_completion(f"{rec.round} (pool version {rec.pool_version})", text)
        rec.completion_message = completion
        self.messages.append(UserMessage(completion))
        self.emit("round_completion", text=completion, text_sha256=hashlib.sha256(completion.encode("utf-8")).hexdigest())
        # the HTML pages of the session, so that the user can open the page of this round
        self.write_report()
        self.harness_s += self.clock.now() - started
        rec.harness_s = self.clock.now() - started

        # (e) the complete report to the user; from now on, later rounds are test-informed when the
        # report contained any sealed result: test results or a reference comparison
        if ev is not None and report_md is not None:
            _, waited = self._with_user(lambda: self.channel.show_report(rec.round, rec.pool_version, report_md, rec.report_dir))
            kinds = sealed_result_kinds(ev)
            if kinds:
                rec.user_shown_sealed_results = kinds
                if not self.test_seen:
                    self.test_seen = True
                    self.test_seen_at = {"round": rec.round, "pool_version": rec.pool_version, "kinds": kinds,
                                         "at": self.wall_clock().isoformat()}
                self.emit("user_shown_sealed_results", shown_round=rec.round, shown_pool_version=rec.pool_version,
                          kinds=kinds, report_dir=rec.report_dir, waiting_s=waited)
        else:
            summary = f"Round {rec.round} ended with outcome {result.outcome}; no candidate was evaluated.\n" + blocks[0][1]
            self._with_user(lambda: self.channel.show_text(f"Round {rec.round}", summary))

    # -- analysis exchanges ------------------------------------------------------------------

    def analysis_exchange(self, request: str) -> ExchangeRecord:
        """Run one analysis exchange on the user's verbatim ``request`` (module
        docstring step 4)."""
        if not self.rounds:
            raise RuntimeError("an analysis exchange follows a round")
        limits = self._analysis_limits()
        message = msg.render_analysis_request(quote_verbatim(request), limits_text(limits), self._remaining_text())
        ex = ExchangeRecord(
            index=len(self.exchanges) + 1,
            after_round=self.current_round,
            pool_version=self.current_pool_version,
            test_informed=self.test_seen,
            request=request,
            message=message,
            limits=dataclasses.asdict(limits),
        )
        self.exchanges.append(ex)
        self._questions = ex.questions
        before = _models_digest(self.workspace)
        self.tracker.open_scope()
        try:
            result = run_analysis_exchange(
                self.provider,
                self._texts.system_prompt,
                message,
                self.workspace,
                self.effective_task,
                self.config,
                limits,
                self.sink,
                labels=RoundLabels(task=self.task.id, session=self.session_id, round=self.current_round, exchange=ex.index),
                clock=self.clock,
                parent_tracker=self.tracker,
                price_table=self.price_table,
                registry=self._registry(),
                web=self.web,
                pip_runner=self.pip_runner,
                python_executable=self.python_executable,
                history=self.messages,
                wall_clock=self.wall_clock,
                base_env=self.base_env,
                pool_version=self.current_pool_version,
            )
        except BaseException:
            self.tracker.close_scope(None)
            raise
        self.tracker.close_scope(result.elapsed_s)
        ex.result = result
        self.messages = list(result.messages)
        ex.models_changed = _models_digest(self.workspace) != before
        if result.outcome == "answered":
            ex.answer = result.final_text
            shown = result.final_text
        else:
            where = limit_phrase(result.limit) if result.limit is not None else f"an error ({result.error})"
            shown = f"The exchange ended at {where} without a completed answer."
        self.emit("analysis_answer", index=ex.index, outcome=result.outcome, answer=ex.answer,
                  models_changed=ex.models_changed, test_informed=ex.test_informed)
        self._with_user(lambda: self.channel.show_text(f"Answer to analysis request {ex.index}", shown))
        self._entries.append(RoundEntry(result, session=self.session_id, round=ex.after_round, pool_version=ex.pool_version,
                                        test_informed=ex.test_informed, mode="exchange",
                                        task_changes=[ch.to_dict() for _, ch in self.changes]))
        self.write_report()
        return ex

    # -- end -----------------------------------------------------------------------------------

    def _unfinished(self) -> list[str]:
        out: list[str] = []
        for r in self.rounds:
            res = r.result
            if res is None or res.outcome == "completed":
                continue
            if res.limit is not None:
                why = f"ended at {limit_phrase(res.limit)} before the agent sent DONE"
            elif res.outcome == "checks_failed_twice":
                why = "ended after a second completion attempt without a candidate that passed the checks"
            else:
                why = f"ended with outcome {res.outcome}" + (f" ({res.error})" if res.error else "")
            files = res.candidate_files
            detail = f"; {len(files.complete)} complete, {len(files.incomplete)} incomplete and {len(files.missing)} missing candidate files; {len(res.evaluated_labels)} candidates evaluated"
            out.append(f"round {r.round} (pool version {r.pool_version}) {why}{detail}")
        for e in self.exchanges:
            if e.result is not None and e.result.outcome != "answered":
                lim = e.result.limit
                why = limit_phrase(lim) if lim is not None else f"an error ({e.result.error})"
                out.append(f"analysis request {e.index} ended at {why} without a completed answer")
        return out

    def end(self, reason: str, limit: LimitHit | None = None) -> SessionResult:
        """End the session (module docstring step 6). ``reason`` is ``user_request``
        or ``session_limit``."""
        if reason not in TERMINATION_REASONS:
            raise ValueError(f"unknown termination reason {reason!r}; the defined reasons are {TERMINATION_REASONS}")
        self.tracker.freeze()
        if reason == "user_request":
            reason_text = "the user requested it"
        else:
            kind = {"turns": "turn", "time": "execution-time", "cost": "cost"}[limit.kind] if limit is not None else "budget"
            reason_text = f"the session {kind} limit was reached"
        completed = [r for r in self.rounds if r.completed]
        identifiers = ", ".join(f"pool version {r.pool_version} (round {r.round})" for r in completed) or "none"
        unfinished = self._unfinished()
        t = self.tracker
        resource = (
            f"{format_turns(t.turns)}; {t.usage.input_tokens} input tokens and {t.usage.output_tokens} output tokens; "
            f"{t.elapsed_s:.1f} s of execution time; {t.cost_usd:.4f} USD"
        )
        text = msg.render_session_completion(reason_text, identifiers, "; ".join(unfinished) or "none", resource)
        self.messages.append(UserMessage(text))
        self.result = SessionResult(
            reason=reason,
            limit=limit,
            rounds=list(self.rounds),
            exchanges=list(self.exchanges),
            totals=dict(t.totals(), harness_s=self.harness_s),
            completion_message=text,
            unfinished=unfinished,
            out_dir=self.out_dir,
        )
        leak = self._leak_scan()
        copy = self._archive_workspace()
        self.emit("session_end", reason=reason, limit=None if limit is None else dataclasses.asdict(limit), text=text,
                  unfinished=unfinished, completed_pool_versions=[r.pool_version for r in completed],
                  totals=self.result.totals)
        self._with_user(lambda: self.channel.show_text("Session completed", text))
        if self.transcript is not None:
            self.transcript.close(reason=reason, completed_pool_versions=[r.pool_version for r in completed])
        self.run_record = write_run_record(
            self.out_dir,
            self.task,
            configuration=self.config,
            model_id=self.provider.model_id,
            vendor=self.provider.vendor,
            rounds=self._entries,
            run_texts=self._texts,
            manifest=self._manifest,
            run_id=self.out_dir.name,
            probe=self.probe,
            price_table=self.price_table,
            session_outcome=reason,
            session_termination=reason_text,
            plots=self.plots,
            session_totals={
                **self.result.totals,
                "note": "the whole session: elapsed_s is the execution time of the rounds and exchanges; waiting_s the user "
                "waiting time inside and between them; harness_s the harness's checks, evaluation and reports",
            },
            extra={
                "session": {
                    "operation": "interactive",
                    "session_id": self.session_id,
                    "session_file": "session.json",
                    "completion_message": text,
                    "unfinished": unfinished,
                    "totals": self.result.totals,
                    "test_informed_from": self.test_seen_at,
                    "task_changes": [dict(ch.to_dict(), effective_round=rnd) for rnd, ch in self.changes],
                },
                "workspace": {"path": str(self.workspace), "root": str(self.workspace_root), "copy": copy},
                "shell_environment": self.environment_note,
                "leak_scan": leak,
                **self.extra_record,
            },
        )
        self.write_report()
        return self.result

    def _leak_scan(self) -> dict[str, Any] | None:
        """Search the transcript and the files that the agent wrote for sealed information (the scan of the experiment runner)."""
        if not self.workspace.is_dir():
            return None
        from ..experiment.runner import leak_scan

        return leak_scan(self.task, self.out_dir, self.workspace, self._manifest)

    def _archive_workspace(self) -> dict[str, Any] | None:
        """Copy the final working directory into the record (``workspace/``, with the copy rules of the
        experiment runner) and remove the session's folder outside the record (the
        record is retained; module docstring). Returns the copy's record."""
        if not self.workspace.is_dir():
            return None
        from ..experiment.workspace import copy_workspace

        dst = self.out_dir / "workspace"
        copy = copy_workspace(self.workspace, dst).to_dict()
        self.emit("workspace_archived", source=str(self.workspace), destination=str(dst), copy=copy)
        shutil.rmtree(self.workspace.parent, ignore_errors=True)
        self.archived_workspace = dst
        return copy

    def _regenerate_brief(self, round_number: int) -> None:
        """Rewrite ``TASK.md`` for the effective task after a task change and record its new SHA-256
        digest (the brief and its hash are recorded)."""
        text = render_brief(self.effective_task, interactive=True)
        (self.workspace / BRIEF_FILE).write_text(text, encoding="utf-8", newline="\n")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.emit("brief_regenerated", effective_round=round_number, brief_sha256=digest, previous_brief_sha256=self.brief_sha256)
        self.brief_sha256 = digest

    # -- the whole session ---------------------------------------------------------------------

    def _choice_context(self) -> ChoiceContext:
        return ChoiceContext(
            last_round=self.current_round,
            completed_pool_versions=tuple(r.pool_version for r in self.rounds if r.completed),
            remaining=self._remaining_text(),
            analysis_limits=limits_text(self._analysis_limits()),
            requirement_ids=tuple(r.id for r in self.effective_task.requirements),
        )

    def run(self) -> SessionResult:
        """Run the whole session with the user's choices from the channel (module docstring)."""
        self.start()
        self.identification_round()
        while True:
            hit = self.tracker.limit_reached()
            if hit is not None:
                return self.end("session_limit", hit)
            action, waited = self._with_user(lambda: self.channel.choose(self._choice_context()))
            assert isinstance(action, UserAction)
            self.emit("user_action", action=action.kind, text=action.text, changes=[c.to_dict() for c in action.changes],
                      waiting_s=waited, test_informed=self.test_seen)
            if action.kind == "end":
                return self.end("user_request")
            if action.kind == "analysis":
                self.analysis_exchange(action.text)
            else:
                self.identification_round(action.text, action.changes)
