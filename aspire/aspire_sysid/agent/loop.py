"""The turn loop of an identification round.

A **turn** is one completed language-model response to the system prompt, the history, and the
descriptions of the available tools. The response may request tools or provide text. The
harness executes the permitted tool requests and includes their results in the next request to
the language model. This module implements the round with its tools and helper agents, as
:func:`run_round`, and the analysis exchange of interactive operation as
:func:`run_analysis_exchange` (used by the session layer).

Definitions used by the harness:

* **Completion message.** A response is the completion message ``DONE`` when it contains no
  tool request and the last non-empty line of its text, with surrounding white space removed,
  is exactly ``DONE`` (so a reply consisting of ``DONE`` alone, or of an explanation followed by
  a final line ``DONE``, completes). ``**DONE**``, ``Done`` or ``DONE.`` do not. A response
  with tool requests is executed normally even when its text says ``DONE``; the record marks it
  (``done_ignored``).
* **Text-only reply.** A response without tool requests that is not the completion message
  counts as a turn and is answered with the continuation message.
* **Checks after DONE.** The harness runs the file and expression checks
  (:func:`aspire_sysid.model.check_workspace` with the task, independent of the working
  directory's copy of the configuration). The round ends with outcome ``completed`` when the
  pool file is valid and at least one candidate within the pool limit passes (the condition
  under which ``check_submission.py`` exits with status 0). Otherwise the harness sends the
  check-failure message with the reasons (rule identifiers) once and the agent may correct the
  files within the remaining budget of the same tracker; a second ``DONE`` with no passing
  candidate ends the round with outcome ``checks_failed_twice``. Physical exclusions and
  numerical failures belong to the evaluation and never cause a retry.
* **Budget.** One :class:`~aspire_sysid.agent.budget.BudgetTracker` per round, shared by the
  correction attempt and the helper agents, is tested before every language-model request and
  before every tool execution. The first limit reached ends the round (outcome
  ``budget_turns``, ``budget_time`` or ``budget_cost``); tool requests of the last response
  that were not started receive the result "not executed"; a running shell command is ended by
  its own limit, which never exceeds the remaining round time. The excess over each limit is
  recorded. The request timeout is the remaining round time.
* **Reminder.** Once per round, at the first request at which the round's turn count or cost
  has reached 80 % of its limit while ``models/`` contains no candidate file, the budget
  reminder of Appendix C is sent before the request.
* **Termination.** At a budget limit the budget-termination message is recorded (appended to
  the history, not followed by a request); complete candidate files are checked, and the
  candidates that pass are handed to the evaluation callback; incomplete and missing files are
  reported separately (:class:`CandidateFiles`). The same holds after a provider error
  (outcome ``error``): valid models already produced are not discarded. A
  request that fails when a limit has been reached (for example, cut off by its timeout, which
  equals the remaining time) ends the round with that limit's outcome, not ``error``.
* **Pool file missing or invalid at a budget stop or an error.** The candidates that pass the
  checks are evaluated in file-name order, up to the pool limit, and the result states
  ``order_assigned_by_harness`` (the order is the harness's, not the agent's). At
  ``checks_failed_twice`` nothing is evaluated, because no candidate passed with a valid pool
  file. At ``completed`` the pool file is valid by definition.
* **Time accounting.** The round's tracker is frozen when the conversation stops; the final
  checks and the evaluation are timed separately (``checks_s``, ``evaluation_s``) and are not
  part of the round's elapsed time or excess.
* **Unreported usage.** When the vendor reports no usage for a response, the harness charges
  an estimate: input tokens = characters of the request divided by
  ``unreported_usage_chars_per_token`` (configuration; 2.0 by default, above the usual 3 to 4
  characters per token of English text and code), output tokens = ``max_output_tokens`` (an
  upper bound). The response event marks the estimate.
* **Helper agents.** ``start_helper`` runs a helper synchronously inside
  the tool call: a new conversation with the helper system prompt, the task text as its first
  message and the same tools without ``start_helper``. Its tracker has the limits
  ``min(requested or default turns, remaining turns)``, the remaining time and the remaining
  cost of the round, and the round's tracker as parent, so that its turns and cost count toward
  the round totals when they occur. The helper ends with its first text-only reply, which is
  returned to the main agent as the tool result, or when a limit is reached. Because helpers
  run synchronously, their activity is counted once in elapsed time.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from ..brief import messages as msg
from ..brief.prompts import HELPER_SYSTEM_PROMPT
from ..brief.workspace import provision_workspace
from ..model import checks as _checks
from ..model import check_workspace
from ..model.checks import CheckReport
from ..task.schema import Limits, TaskSpec
from .budget import BudgetTracker, ExecutionClock, LimitHit, format_remaining, format_turns, format_usd
from .config import ALL_TOOLS, ToolConfig
from .events import EventSink
from .prices import PriceTable, default_price_table
from .probe import EnvironmentProbe
from .providers import (
    AssistantMessage,
    Message,
    Provider,
    ProviderError,
    ProviderResponse,
    ToolCall,
    ToolResultMessage,
    Usage,
    UserMessage,
    message_to_dict,
)
from .shell import cap_text
from .tools import (
    PathError,
    PipRunner,
    ToolContext,
    ToolOutcome,
    ToolRegistry,
    WebBackends,
    build_registry,
    make_context,
)

__all__ = [
    "DONE",
    "OUTCOMES",
    "REMINDER_FRACTION",
    "DEFAULT_HELPER_SYSTEM_PROMPT",
    "RoundLabels",
    "CandidateFiles",
    "HelperSummary",
    "RoundResult",
    "EvaluateCallback",
    "is_completion_message",
    "candidate_files",
    "prepare_workspace",
    "run_round",
    "run_analysis_exchange",
]

DONE = "DONE"
"""The completion message."""

OUTCOMES: tuple[str, ...] = (
    "completed",
    "checks_failed_twice",
    "budget_turns",
    "budget_time",
    "budget_cost",
    "error",
    "answered",
)
"""Outcomes of a round; ``answered`` ends an analysis exchange."""

REMINDER_FRACTION = 0.8
"""The reminder is sent when turns or cost first reach this fraction of the limit."""

DEFAULT_HELPER_SYSTEM_PROMPT = HELPER_SYSTEM_PROMPT
"""System prompt of a helper agent; harness text of the brief module
(:data:`aspire_sysid.brief.prompts.HELPER_SYSTEM_PROMPT`)."""

_BUDGET_TYPE = {"turns": "turn", "time": "execution-time", "cost": "cost"}
_OUTCOME_OF_LIMIT = {"turns": "budget_turns", "time": "budget_time", "cost": "budget_cost"}


@dataclass(frozen=True)
class RoundLabels:
    """Labels of every event of a round: task, session and round identifiers.

    The pool version label is the ``pool_version`` argument of :func:`run_round`. ``exchange`` is
    the number of an analysis exchange of interactive operation:
    when set, every event of the exchange carries the label ``exchange``, so that the exchange that
    follows round ``k`` (and carries its round label) is kept apart from that round; autonomous
    rounds leave it ``None`` and their events carry no such field.
    """

    task: str
    session: str = "session-1"
    round: int = 1
    exchange: int | None = None


@dataclass(frozen=True)
class CandidateFiles:
    """The candidate files in ``models/`` at the end of a round.

    ``complete``: files that are valid JSON objects with every required field of a candidate
    file; ``incomplete``: other ``*.json`` files except ``pool.json``;
    ``missing``: labels in the pool file's order without a file. Labels in sorted order.
    """

    complete: tuple[str, ...] = ()
    incomplete: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, list[str]]:
        """JSON-serializable form."""
        return {"complete": list(self.complete), "incomplete": list(self.incomplete), "missing": list(self.missing)}


@dataclass(frozen=True)
class HelperSummary:
    """Allowance and totals of one helper agent."""

    name: str
    turns: int
    cost_usd: float
    ended: str
    allowance: Mapping[str, float]


EvaluateCallback = Callable[[CheckReport, list], Any]
"""``evaluate_callback(report, labels)``: evaluates the checked candidates ``labels`` (the
evaluation of :mod:`aspire_sysid.evaluate`); its return value is stored in :attr:`RoundResult.evaluation`."""


@dataclass
class RoundResult:
    """The result of one round or analysis exchange.

    ``limit`` names the reached limit and its scope for a budget outcome; ``excess`` holds the
    amounts by which the round exceeded its own limits; ``messages`` is the complete
    conversation history of the main agent, which the session layer continues in later rounds. ``elapsed_s``,
    ``waiting_s`` and ``excess`` are fixed when the conversation stops; the durations of the
    final checks and of the evaluation are ``checks_s`` and ``evaluation_s`` (harness time, not
    agent execution time). ``order_assigned_by_harness`` is true when the evaluated labels
    follow the file-name order because the pool file was missing or invalid.
    """

    outcome: str
    turns: int
    usage: Usage
    cost_usd: float
    elapsed_s: float
    waiting_s: float
    excess: dict[str, float]
    estimated_usage_turns: int
    limit: LimitHit | None
    correction_used: bool
    done_count: int
    reminder_sent: bool
    candidate_files: CandidateFiles
    check_report: CheckReport | None
    evaluated_labels: list[str]
    evaluation: Any
    messages: list[Message]
    helpers: list[HelperSummary]
    error: str | None = None
    final_text: str = ""
    termination_message: str | None = None
    checks_s: float = 0.0
    evaluation_s: float = 0.0
    order_assigned_by_harness: bool = False


def is_completion_message(response: ProviderResponse | AssistantMessage) -> bool:
    """Whether a response is the completion message ``DONE`` (module docstring)."""
    if response.tool_calls:
        return False
    lines = [ln.strip() for ln in response.text.splitlines() if ln.strip()]
    return bool(lines) and lines[-1] == DONE


def _says_done(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return bool(lines) and lines[-1] == DONE


def candidate_files(workspace: str | Path, report: CheckReport | None = None) -> CandidateFiles:
    """Classify the files of ``models/`` as complete, incomplete or missing.

    A complete file is a JSON object with every field of :data:`aspire_sysid.model.checks.CANDIDATE_FIELDS`;
    it may still fail other checks, which the check report states. ``missing`` are the labels
    of the report's pool order without a file.
    """
    models = Path(workspace) / _checks.MODELS_DIR
    complete: list[str] = []
    incomplete: list[str] = []
    if models.is_dir():
        for p in sorted(models.glob("*.json")):
            if not p.is_file() or p.name == _checks.POOL_FILE:
                continue
            try:
                data = _checks.read_json(p)
                ok = isinstance(data, dict) and all(k in data for k in _checks.CANDIDATE_FIELDS)
            except (ValueError, UnicodeDecodeError, OSError):
                ok = False
            (complete if ok else incomplete).append(p.stem)
    missing: list[str] = []
    if report is not None and report.order_from_pool:
        missing = sorted(lab for lab in report.order if report.candidates.get(lab) is None or report.candidates[lab].file is None)
    return CandidateFiles(tuple(complete), tuple(incomplete), tuple(missing))


def _has_candidate_file(workspace: Path) -> bool:
    models = workspace / _checks.MODELS_DIR
    return models.is_dir() and any(p.is_file() and p.name != _checks.POOL_FILE for p in models.glob("*.json"))


def prepare_workspace(task: TaskSpec, workspace: str | Path, *, interactive: bool = False) -> list[Any]:
    """Provision a working directory: brief, writing rules, data, supporting files, checking files
    and an empty ``models/``.

    Delegates to :func:`aspire_sysid.brief.provision_workspace`, the single entry
    point that writes a working directory. Returns the written files with their SHA-256 digests.
    """
    return list(provision_workspace(task, workspace, interactive=interactive).files)


def _resolved_exe(p: str) -> Path:
    try:
        return Path(p).resolve()
    except OSError:
        return Path(p)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _usage_dict(u: Usage) -> dict[str, Any]:
    return dataclasses.asdict(u)


def _call_dict(tc: ToolCall) -> dict[str, Any]:
    return {
        "id": tc.id,
        "name": tc.name,
        "arguments": dict(tc.arguments),
        "raw_arguments": tc.raw_arguments,
        "arguments_error": tc.arguments_error,
    }


def _jsonable(value: Any) -> Any:
    """A JSON-serializable copy of ``value`` (unknown objects become their text)."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        if isinstance(value, Mapping):
            return {str(k): _jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_jsonable(v) for v in value]
        return str(value)


def _request_chars(system: str, messages: Sequence[Message], registry: ToolRegistry) -> int:
    n = len(system) + len(json.dumps([dataclasses.asdict(s) for s in registry.specs()], default=str))
    for m in messages:
        n += len(json.dumps(message_to_dict(m)))
    return n


def _check_reasons(report: CheckReport | None, error: str | None) -> str:
    """The reasons of the check-failure message: each issue with its candidate label."""
    if report is None:
        return f"the checks could not be run ({error})"
    lines = [f"pool file: {i.text()}" for i in report.pool_issues]
    ordered = [lab for lab in report.order if lab in report.candidates]
    ordered += sorted(lab for lab in report.candidates if lab not in report.order)
    for lab in ordered:
        lines += [f"candidate {lab}: {i.text()}" for i in report.candidates[lab].issues]
    if not any(r.file is not None for r in report.candidates.values()):
        lines.append(f"no candidate file exists in {_checks.MODELS_DIR}/")
    elif not report.evaluated and not lines:
        lines.append("no candidate within the pool limit passed the checks")
    return "; ".join(lines)


def _limits_text(tracker: BudgetTracker) -> tuple[str, str, str]:
    return format_remaining(tracker.remaining())


@dataclass
class _Stop:
    reason: str  # "budget", "error", "final", or an outcome decided by on_final
    hit: LimitHit | None = None
    error: str | None = None
    final_text: str = ""


class _Engine:
    """Shared machinery of the main agent and the helper agents of one round."""

    def __init__(
        self,
        *,
        provider: Provider,
        config: ToolConfig,
        sink: EventSink,
        labels: RoundLabels,
        tracker: BudgetTracker,
        clock: ExecutionClock,
        price_table: PriceTable,
        wall_clock: Callable[[], _dt.datetime],
        helper_system_prompt: str,
        pool_version: int = 1,
    ) -> None:
        self.pool_version = pool_version
        self.provider = provider
        self.config = config
        self.sink = sink
        self.labels = labels
        self.tracker = tracker
        self.clock = clock
        self.prices = price_table
        self.wall_clock = wall_clock
        self.helper_system_prompt = helper_system_prompt
        self.seq = 0
        self.helpers: list[HelperSummary] = []
        self.registry: ToolRegistry | None = None
        self.ctx: ToolContext | None = None

    # -- events --------------------------------------------------------------------------

    def emit(self, kind: str, agent: str = "main", **fields: Any) -> None:
        """Record one event with the round's labels."""
        self.seq += 1
        base = {
            "task": self.labels.task,
            "session": self.labels.session,
            "round": self.labels.round,
            "pool_version": self.pool_version,
            "agent": agent,
            **({"exchange": self.labels.exchange} if self.labels.exchange is not None else {}),
            "seq": self.seq,
            "timestamp": self.wall_clock().isoformat(),
            "elapsed_s": self.tracker.elapsed_s,
        }
        base.update({k: _jsonable(v) for k, v in fields.items()})
        self.sink.emit(kind, **base)

    # -- one conversation ----------------------------------------------------------------

    def converse(
        self,
        *,
        agent: str,
        system: str,
        messages: list[Message],
        registry: ToolRegistry,
        tracker: BudgetTracker,
        ctx: ToolContext,
        pending: list[tuple[str, str]],
        on_final: Callable[[ProviderResponse], tuple[str | None, list[tuple[str, str]]]],
        before_request: Callable[[], list[tuple[str, str]]] | None = None,
    ) -> _Stop:
        """Run turns until ``on_final`` stops, a limit is reached or a request fails."""
        sent_upto = 0
        cfg = self.config.requests
        while True:
            hit = tracker.limit_reached()
            if hit is not None:
                return _Stop("budget", hit=hit)
            if before_request is not None:
                pending.extend(before_request())
            for kind, text in pending:
                messages.append(UserMessage(text))
                self.emit(kind, agent=agent, text=text)
            pending.clear()
            timeout = tracker.remaining().seconds
            self.emit(
                "request",
                agent=agent,
                model=self.provider.model_id,
                max_output_tokens=cfg.max_output_tokens,
                reasoning=cfg.reasoning().to_dict(),
                timeout_s=timeout,
                n_messages=len(messages),
                new_messages=[message_to_dict(m) for m in messages[sent_upto:]],
            )
            sent_upto = len(messages)
            try:
                resp = self.provider.complete(
                    system, messages, registry.specs(), max_output_tokens=cfg.max_output_tokens, timeout_s=timeout,
                    reasoning=cfg.reasoning(),
                )
            except ProviderError as exc:
                error = f"{type(exc).__name__}: {exc}"
                hit = tracker.limit_reached()
                self.emit("request_error", agent=agent, error=error, attempts=exc.attempts,
                          limit=None if hit is None else {"kind": hit.kind, "scope": hit.scope})
                if hit is not None:
                    # the request was cut off by the remaining-time timeout: the limit ends the round
                    return _Stop("budget", hit=hit, error=error)
                return _Stop("error", error=error)
            usage = resp.usage
            estimated = False
            if not usage.reported:
                chars = _request_chars(system, messages, registry)
                usage = Usage(
                    input_tokens=int(math.ceil(chars / cfg.unreported_usage_chars_per_token)),
                    output_tokens=cfg.max_output_tokens,
                    reported=False,
                )
                estimated = True
            cost = self.prices.cost_usd(self.provider.model_id, usage)
            tracker.charge_turn(usage, cost, estimated=estimated)
            messages.append(resp.to_message())
            sent_upto = len(messages)
            done = is_completion_message(resp)
            self.emit(
                "response",
                agent=agent,
                text=resp.text,
                tool_calls=[_call_dict(tc) for tc in resp.tool_calls],
                refusal=resp.refusal,
                stop_reason=resp.stop_reason,
                model=resp.model,
                usage=_usage_dict(resp.usage),
                usage_charged=_usage_dict(usage),
                usage_estimated=estimated,
                cost_usd=cost,
                latency_s=resp.latency_s,
                attempts=resp.attempts,
                done=done,
                done_ignored=bool(resp.tool_calls) and _says_done(resp.text),
                totals=self.tracker.totals(),
                agent_totals=tracker.totals() if tracker is not self.tracker else None,
                # the vendor's reasoning summaries, and its output items verbatim (including the
                # encrypted reasoning that later requests send back), so that every request can be
                # reconstructed exactly
                **({"reasoning": list(resp.reasoning)} if resp.reasoning else {}),
                # web searches that the vendor executed inside this response (its built-in tool)
                **({"web_searches": [dict(w) for w in resp.web_searches]} if resp.web_searches else {}),
                **({"vendor": resp.vendor, "vendor_items": [dict(i) for i in resp.vendor_items]} if resp.vendor_items else {}),
            )
            if resp.tool_calls:
                # the tool results follow the assistant message and are new messages of the next request
                self._execute_tools(agent, resp.tool_calls, messages, registry, tracker, ctx)
                continue
            stop, more = on_final(resp)
            if stop is not None:
                return _Stop(stop, final_text=resp.text)
            pending.extend(more)

    def _execute_tools(
        self,
        agent: str,
        calls: Sequence[ToolCall],
        messages: list[Message],
        registry: ToolRegistry,
        tracker: BudgetTracker,
        ctx: ToolContext,
    ) -> None:
        """Execute the tool requests of one response in order; test the budget before each."""
        out_cfg = self.config.output
        stopped: LimitHit | None = None
        for call in calls:
            if stopped is None:
                stopped = tracker.limit_reached()
            if stopped is not None:
                text = (
                    f"Not executed: the {_BUDGET_TYPE[stopped.kind]} limit of the {stopped.scope} was reached "
                    "before this tool request was started."
                )
                messages.append(ToolResultMessage(call.id, call.name, text, is_error=True))
                self.emit(
                    "tool_result",
                    agent=agent,
                    call_id=call.id,
                    tool=call.name,
                    executed=False,
                    content=text,
                    content_sent=text,
                    is_error=True,
                    denied=False,
                    limit={"kind": stopped.kind, "scope": stopped.scope},
                )
                continue
            self.emit("tool_call", agent=agent, call_id=call.id, tool=call.name, arguments=dict(call.arguments),
                      raw_arguments=call.raw_arguments, arguments_error=call.arguments_error)
            tool = registry.get(call.name)
            started = self.clock.elapsed()
            if call.arguments_error:
                outcome = ToolOutcome(f"The arguments of {call.name} could not be read: {call.arguments_error}", is_error=True)
            elif tool is None:
                outcome = ToolOutcome(
                    f"The tool {call.name!r} is not available. "
                    f"Available tools: {', '.join(registry.names())}.",
                    is_error=True,
                    denied=True,
                )
            else:
                try:
                    outcome = tool.handler(ctx, call.arguments)
                except (PathError, ValueError) as exc:
                    outcome = ToolOutcome(f"{call.name} refused: {exc}", is_error=True, denied=isinstance(exc, PathError))
                except OSError as exc:
                    outcome = ToolOutcome(f"{call.name} failed: {exc}", is_error=True)
                except Exception as exc:  # noqa: BLE001 - a tool failure is reported to the agent and recorded
                    outcome = ToolOutcome(f"{call.name} failed: {type(exc).__name__}: {exc}", is_error=True)
            sent, truncated = cap_text(outcome.content, out_cfg.agent_cap_chars)
            recorded, record_truncated = cap_text(outcome.content, out_cfg.record_cap_chars)
            messages.append(ToolResultMessage(call.id, call.name, sent, is_error=outcome.is_error))
            self.emit(
                "tool_result",
                agent=agent,
                call_id=call.id,
                tool=call.name,
                executed=True,
                content=recorded,
                content_chars=len(outcome.content),
                content_sent=sent,
                truncated_for_agent=truncated,
                truncated_in_record=record_truncated,
                is_error=outcome.is_error,
                denied=outcome.denied,
                details=outcome.details,
                duration_s=self.clock.elapsed() - started,
            )

    # -- helper agents -------------------------------------------------------------------

    def run_helper(self, task_text: str, max_turns: int | None) -> ToolOutcome:
        """Run one helper agent within the main agent's remaining allowance."""
        assert self.ctx is not None and self.registry is not None
        hcfg = self.config.helpers
        if hcfg is None:
            return ToolOutcome("start_helper is unavailable in this configuration.", is_error=True, denied=True)
        if len(self.helpers) >= hcfg.max_helpers:
            return ToolOutcome(f"Refused: the round already used its {hcfg.max_helpers} helper agents.", is_error=True, denied=True)
        rem = self.tracker.remaining()
        turns = min(max_turns if max_turns is not None else hcfg.default_turns, rem.turns)
        if turns <= 0 or rem.seconds <= 0 or rem.usd <= 0:
            return ToolOutcome("Refused: no allowance remains for a helper agent.", is_error=True)
        name = f"helper-{len(self.helpers) + 1}"
        allowance = Limits(turns=turns, seconds=rem.seconds, usd=rem.usd)
        htracker = BudgetTracker(allowance, self.clock, scope=name, parent=self.tracker)
        hctx = dataclasses.replace(
            self.ctx,
            tracker=htracker,
            agent=name,
            helper_runner=None,
            emit=lambda kind, **f: self.emit(kind, agent=name, **f),
        )
        hreg = self.registry.for_helpers()
        self.emit("helper_start", agent=name, task_text=task_text, requested_turns=max_turns,
                  allowance={"turns": turns, "seconds": rem.seconds, "usd": rem.usd},
                  tools=hreg.names(), system_prompt=self.helper_system_prompt,
                  system_prompt_sha256=_sha256(self.helper_system_prompt))
        hmessages: list[Message] = [UserMessage(task_text)]
        stop = self.converse(
            agent=name,
            system=self.helper_system_prompt,
            messages=hmessages,
            registry=hreg,
            tracker=htracker,
            ctx=hctx,
            pending=[],
            on_final=lambda resp: ("final", []),
        )
        ended = stop.reason if stop.hit is None else f"limit:{stop.hit.kind}:{stop.hit.scope}"
        summary = HelperSummary(name, htracker.turns, htracker.cost_usd, ended,
                                {"turns": turns, "seconds": rem.seconds, "usd": rem.usd})
        self.helpers.append(summary)
        self.emit("helper_end", agent=name, ended=ended, totals=htracker.totals(), error=stop.error)
        spent = f"{format_turns(htracker.turns)}, {htracker.cost_usd:.4f} USD"
        if stop.reason == "final":
            return ToolOutcome(f"Helper {name} finished ({spent}). Its final reply:\n{stop.final_text}",
                               details={"helper": name, "ended": ended})
        last = next((m.text for m in reversed(hmessages) if isinstance(m, AssistantMessage) and m.text.strip()), "")
        if stop.hit is not None:
            why = f"the {_BUDGET_TYPE[stop.hit.kind]} limit of the {stop.hit.scope} was reached"
        else:
            why = f"its request failed ({stop.error})"
        return ToolOutcome(
            f"Helper {name} stopped because {why} ({spent}). Its last text:\n{last or '(none)'}",
            is_error=True,
            details={"helper": name, "ended": ended},
        )


def _run(
    mode: str,
    provider: Provider,
    system_prompt: str,
    first_user_message: str,
    workspace: str | Path,
    task: TaskSpec,
    config: ToolConfig,
    limits: Limits,
    sink: EventSink,
    *,
    evaluate_callback: EvaluateCallback | None,
    labels: RoundLabels | None,
    clock: ExecutionClock | None,
    parent_tracker: BudgetTracker | None,
    price_table: PriceTable | None,
    registry: ToolRegistry | None,
    web: WebBackends | None,
    pip_runner: PipRunner | None,
    probe: EnvironmentProbe | None,
    python_executable: str | None,
    history: Iterable[Message],
    pool_version: int,
    previous_labels: Iterable[str],
    helper_system_prompt: str,
    wall_clock: Callable[[], _dt.datetime] | None,
    base_env: Mapping[str, str] | None,
) -> RoundResult:
    ws = Path(workspace).resolve()
    python_executable = str(python_executable or sys.executable)
    if probe is not None and _resolved_exe(probe.python_executable) != _resolved_exe(python_executable):
        raise ValueError(
            f"the environment probe describes {probe.python_executable}, but the shell uses {python_executable}; "
            "probe the interpreter of the agent's shell"
        )
    prices = price_table or default_price_table()
    prices.price(provider.model_id)  # fail before any request when the model has no verified price
    clock = clock or (parent_tracker.clock if parent_tracker is not None else ExecutionClock())
    tracker = BudgetTracker(limits, clock, scope="round" if mode == "round" else "analysis", parent=parent_tracker)
    labels = labels or RoundLabels(task=task.id)
    registry = registry or build_registry(config)
    stray = [n for n in registry.names() if n in ALL_TOOLS and n not in config.tools]
    if stray:
        raise ValueError(f"the registry offers {stray}, which the tool configuration does not list")
    previous = list(previous_labels)
    history = list(history)
    engine = _Engine(
        provider=provider,
        config=config,
        sink=sink,
        labels=labels,
        tracker=tracker,
        clock=clock,
        price_table=prices,
        wall_clock=wall_clock or (lambda: _dt.datetime.now(_dt.timezone.utc)),
        helper_system_prompt=helper_system_prompt,
        pool_version=pool_version,
    )
    ctx = make_context(
        workspace=ws,
        config=config,
        clock=clock,
        tracker=tracker,
        emit=lambda kind, **f: engine.emit(kind, agent="main", **f),
        task_dir=task.task_dir,
        python_executable=python_executable,
        web=web,
        pip_runner=pip_runner,
        base_env=base_env,
    )
    if "start_helper" in registry:
        ctx.helper_runner = engine.run_helper
    engine.ctx = ctx
    engine.registry = registry

    engine.emit(
        "round_start",
        mode=mode,
        model=provider.model_id,
        vendor=provider.vendor,
        configuration=config.to_dict(),
        tools=[dataclasses.asdict(s) for s in registry.specs()],
        system_prompt=system_prompt,
        system_prompt_sha256=_sha256(system_prompt),
        limits={"turns": limits.turns, "seconds": limits.seconds, "usd": limits.usd},
        parent_scope=parent_tracker.scope if parent_tracker is not None else None,
        environment=probe.to_dict() if probe is not None else None,
        price={"model": provider.model_id, "input_usd_per_mtok": prices.price(provider.model_id).input_usd_per_mtok,
               "output_usd_per_mtok": prices.price(provider.model_id).output_usd_per_mtok,
               "verified": prices.price(provider.model_id).verified.isoformat(), "table": prices.origin},
        workspace=str(ws),
        history_messages=[message_to_dict(m) for m in history],
        pool_version=pool_version,
        previous_labels=previous,
    )
    messages: list[Message] = list(history)
    messages.append(UserMessage(first_user_message))
    engine.emit("user_message", text=first_user_message, text_sha256=_sha256(first_user_message))

    state = {"correction_used": False, "done_count": 0, "reminder_sent": False, "report": None, "check_error": None}

    def run_checks() -> CheckReport | None:
        try:
            report = check_workspace(ws, task, pool_version=pool_version, previous_labels=previous)
            state["check_error"] = None
        except Exception as exc:  # noqa: BLE001 - recorded; the round continues with the outcome
            state["check_error"] = f"{type(exc).__name__}: {exc}"
            report = None
        state["report"] = report
        engine.emit(
            "check_outcome",
            passed=bool(report and report.passed),
            evaluated=list(report.evaluated) if report else [],
            issues=[{"rule": i.rule, "where": i.where, "message": i.message} for i in report.issues] if report else [],
            report_text=report.text() if report else None,
            error=state["check_error"],
        )
        return report

    def on_final_round(resp: ProviderResponse) -> tuple[str | None, list[tuple[str, str]]]:
        if not is_completion_message(resp):
            t, s, c = _limits_text(tracker)
            return None, [("continuation", msg.render_continuation(t, s, c))]
        state["done_count"] += 1
        report = run_checks()
        if report is not None and report.passed:
            return "completed", []
        if state["correction_used"]:
            return "checks_failed_twice", []
        state["correction_used"] = True
        reasons, _ = cap_text(_check_reasons(report, state["check_error"]), config.output.agent_cap_chars)
        t, s, c = _limits_text(tracker)
        text = msg.render_check_failure(reasons, f"{t}, {s}, {c}")
        engine.emit("correction", remaining={"turns": tracker.remaining().turns, "seconds": tracker.remaining().seconds,
                                             "usd": tracker.remaining().usd})
        return None, [("check_failure_message", text)]

    def on_final_exchange(resp: ProviderResponse) -> tuple[str | None, list[tuple[str, str]]]:
        return "answered", []

    def before_request() -> list[tuple[str, str]]:
        if mode != "round" or state["reminder_sent"]:
            return []
        kind = None
        if tracker.fraction_used("turns") >= REMINDER_FRACTION:
            kind = "turns"
        elif tracker.fraction_used("cost") >= REMINDER_FRACTION:
            kind = "cost"
        if kind is None or _has_candidate_file(ws):
            return []
        state["reminder_sent"] = True
        pct = int(math.floor(tracker.fraction_used(kind) * 100 + 1e-9))
        used = f"{pct} % ({format_turns(tracker.turns)})" if kind == "turns" else f"{pct} % ({format_usd(tracker.cost_usd)})"
        t, s, c = _limits_text(tracker)
        text = msg.render_budget_reminder(used, "turn" if kind == "turns" else "cost", f"{_checks.MODELS_DIR}/", t, s, c)
        return [("reminder", text)]

    stop = engine.converse(
        agent="main",
        system=system_prompt,
        messages=messages,
        registry=registry,
        tracker=tracker,
        ctx=ctx,
        pending=[],
        on_final=on_final_round if mode == "round" else on_final_exchange,
        before_request=before_request,
    )

    tracker.freeze()
    termination: str | None = None
    if stop.reason == "budget":
        assert stop.hit is not None
        outcome = _OUTCOME_OF_LIMIT[stop.hit.kind]
    elif stop.reason == "error":
        outcome = "error"
    else:
        outcome = stop.reason

    report: CheckReport | None = state["report"]
    files = CandidateFiles()
    evaluated: list[str] = []
    evaluation: Any = None
    checks_s = 0.0
    evaluation_s = 0.0
    harness_order = False
    if mode == "round":
        if outcome not in ("completed", "checks_failed_twice"):
            files_now = candidate_files(ws)
            if stop.hit is not None:
                btype = _BUDGET_TYPE[stop.hit.kind]
                if stop.hit.scope not in ("round", "analysis"):
                    btype = f"{stop.hit.scope} {btype}"
                termination = msg.render_budget_termination(btype, len(files_now.complete), len(files_now.incomplete))
                messages.append(UserMessage(termination))
                engine.emit("budget_termination", text=termination, limit={"kind": stop.hit.kind, "scope": stop.hit.scope},
                            complete=list(files_now.complete), incomplete=list(files_now.incomplete))
            t0 = clock.now()
            report = run_checks()
            checks_s = clock.now() - t0
        files = candidate_files(ws, report)
        if report is not None and outcome != "checks_failed_twice":
            evaluated = list(report.evaluated)
            harness_order = bool(evaluated) and not report.order_from_pool
        if evaluated and evaluate_callback is not None:
            engine.emit("evaluation", labels=evaluated, status="started", order_assigned_by_harness=harness_order)
            t0 = clock.now()
            try:
                evaluation = evaluate_callback(report, list(evaluated))
                evaluation_s = clock.now() - t0
                engine.emit("evaluation", labels=evaluated, status="finished", duration_s=evaluation_s)
            except Exception as exc:  # noqa: BLE001 - recorded; the round result is kept
                evaluation_s = clock.now() - t0
                engine.emit("evaluation", labels=evaluated, status="failed", error=f"{type(exc).__name__}: {exc}",
                            duration_s=evaluation_s)
                evaluation = None

    result = RoundResult(
        outcome=outcome,
        turns=tracker.turns,
        usage=tracker.usage,
        cost_usd=tracker.cost_usd,
        elapsed_s=tracker.elapsed_s,
        waiting_s=tracker.waiting_s,
        excess=tracker.excess(),
        estimated_usage_turns=tracker.estimated_turns,
        limit=stop.hit,
        correction_used=state["correction_used"],
        done_count=state["done_count"],
        reminder_sent=state["reminder_sent"],
        candidate_files=files,
        check_report=report,
        evaluated_labels=evaluated,
        evaluation=evaluation,
        messages=messages,
        helpers=list(engine.helpers),
        error=stop.error,
        final_text=stop.final_text,
        termination_message=termination,
        checks_s=checks_s,
        evaluation_s=evaluation_s,
        order_assigned_by_harness=harness_order,
    )
    engine.emit(
        "round_end",
        outcome=outcome,
        limit=None if stop.hit is None else {"kind": stop.hit.kind, "scope": stop.hit.scope},
        totals=tracker.totals(),
        excess=result.excess,
        correction_used=result.correction_used,
        done_count=result.done_count,
        reminder_sent=result.reminder_sent,
        candidate_files=files.to_dict(),
        evaluated=evaluated,
        helpers=[dataclasses.asdict(h) for h in engine.helpers],
        error=stop.error,
        checks_s=checks_s,
        evaluation_s=evaluation_s,
        order_assigned_by_harness=harness_order,
    )
    return result


def run_round(
    provider: Provider,
    system_prompt: str,
    first_user_message: str,
    workspace: str | Path,
    task: TaskSpec,
    config: ToolConfig,
    limits: Limits,
    sink: EventSink,
    *,
    evaluate_callback: EvaluateCallback | None = None,
    labels: RoundLabels | None = None,
    clock: ExecutionClock | None = None,
    parent_tracker: BudgetTracker | None = None,
    price_table: PriceTable | None = None,
    registry: ToolRegistry | None = None,
    web: WebBackends | None = None,
    pip_runner: PipRunner | None = None,
    probe: EnvironmentProbe | None = None,
    python_executable: str | None = None,
    history: Iterable[Message] = (),
    pool_version: int = 1,
    previous_labels: Iterable[str] = (),
    helper_system_prompt: str = DEFAULT_HELPER_SYSTEM_PROMPT,
    wall_clock: Callable[[], _dt.datetime] | None = None,
    base_env: Mapping[str, str] | None = None,
) -> RoundResult:
    """Run one identification round and return its result.

    ``system_prompt`` is the system prompt of the harness; ``first_user_message``
    starts the round (the brief's instruction, or the new-round message of the session layer); ``workspace`` is the
    provisioned working directory (:func:`prepare_workspace`); ``task`` is the loaded task
    (the harness's checks read the training data from the task store); ``config`` is the tool
    configuration; ``limits`` is the round budget, normally ``task.budget.round``; ``sink``
    receives the events. Optional: ``evaluate_callback(report, labels)`` evaluates the checked
    candidates at the end; ``parent_tracker`` is the session tracker, to which every
    charge is propagated and whose limits also end the round; ``history`` is the conversation of
    earlier rounds; ``pool_version`` and ``previous_labels`` configure the checks of a
    later round; ``registry`` replaces the built-in tools of ``config`` (the session layer adds ``ask_user``);
    ``clock`` is the execution clock (shared by the session; tests inject a fake time source);
    ``price_table`` defaults to ``aspire/configs/prices.yaml``; ``web`` and ``pip_runner`` are
    the backends of the web and package-installation tools; ``probe`` is recorded in the ``round_start`` event;
    ``python_executable`` is the interpreter of the agent's shell; ``base_env`` replaces the
    harness environment from which the shell environment is derived.
    """
    return _run(
        "round", provider, system_prompt, first_user_message, workspace, task, config, limits, sink,
        evaluate_callback=evaluate_callback, labels=labels, clock=clock, parent_tracker=parent_tracker,
        price_table=price_table, registry=registry, web=web, pip_runner=pip_runner, probe=probe,
        python_executable=python_executable, history=history, pool_version=pool_version,
        previous_labels=previous_labels, helper_system_prompt=helper_system_prompt, wall_clock=wall_clock,
        base_env=base_env,
    )


def run_analysis_exchange(
    provider: Provider,
    system_prompt: str,
    request_message: str,
    workspace: str | Path,
    task: TaskSpec,
    config: ToolConfig,
    limits: Limits,
    sink: EventSink,
    *,
    labels: RoundLabels | None = None,
    clock: ExecutionClock | None = None,
    parent_tracker: BudgetTracker | None = None,
    price_table: PriceTable | None = None,
    registry: ToolRegistry | None = None,
    web: WebBackends | None = None,
    pip_runner: PipRunner | None = None,
    python_executable: str | None = None,
    history: Iterable[Message] = (),
    helper_system_prompt: str = DEFAULT_HELPER_SYSTEM_PROMPT,
    wall_clock: Callable[[], _dt.datetime] | None = None,
    base_env: Mapping[str, str] | None = None,
    pool_version: int = 1,
) -> RoundResult:
    """Run one analysis exchange: the user's request and the agent's tool use.

    "The agent's completed answer ends the exchange": the first text-only reply of the main
    agent ends it with outcome ``answered`` (:attr:`RoundResult.final_text` holds the answer).
    ``limits`` are the task's analysis-exchange limits; ``parent_tracker`` is the session
    tracker, to which the exchange is charged. No checks, reminder or evaluation take place.
    ``pool_version`` labels the events with the current pool version of the session (the
    exchange writes no pool). Used by the session layer.
    """
    return _run(
        "exchange", provider, system_prompt, request_message, workspace, task, config, limits, sink,
        evaluate_callback=None, labels=labels, clock=clock, parent_tracker=parent_tracker,
        price_table=price_table, registry=registry, web=web, pip_runner=pip_runner, probe=None,
        python_executable=python_executable, history=history, pool_version=pool_version, previous_labels=(),
        helper_system_prompt=helper_system_prompt, wall_clock=wall_clock, base_env=base_env,
    )
