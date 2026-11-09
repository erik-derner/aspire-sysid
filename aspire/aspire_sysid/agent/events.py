"""Event sink: the structured events of a round, for the transcript.

The harness records every language-model request and response, tool
request and result, user message, reminder, check outcome and termination event, labeled with
task, session, round, candidate and pool version, with timestamps and elapsed execution time.
The turn loop (:mod:`aspire_sysid.agent.loop`) emits these events through the interface
:class:`EventSink`; the record layer (:mod:`aspire_sysid.record`) persists them as a JSON Lines
(JSONL) transcript.

Interface. A sink has one method, ``emit(kind, **fields)``. The loop adds to every event the
labels ``task``, ``session``, ``round``, ``pool_version`` and ``agent`` (``main`` or
``helper-<n>``), a sequence number ``seq`` (1, 2, ... within the round), the wall-clock
``timestamp`` (ISO 8601, UTC) and ``elapsed_s``, the elapsed execution time of the round. Every
field value is JSON-serializable (strings, numbers, booleans, ``None``, lists and dictionaries of
these). ``candidate`` is set where an event concerns one candidate.

Event kinds (:data:`EVENT_KINDS`):

``round_start``
    system prompt and its SHA-256 digest, tool configuration, tool descriptions, model
    identifier, limits, environment probe, pool version.
``user_message``
    the first message of the round or exchange (the brief's instruction or a message of the
    session layer).
``request``
    one language-model request: model, ``max_output_tokens``, the reasoning settings
    (``reasoning``: effort and summary), ``timeout_s``, the number of messages and the messages
    added since the previous request (``new_messages``); together with ``round_start`` and the
    earlier ``response`` events this reconstructs every request exactly.
``request_error``
    a failed request (provider error text, attempts).
``response``
    one completed response (one turn): text, tool calls, refusal, stop reason, usage, whether
    the usage was estimated, cost, latency, attempts, and the round totals after the charge;
    when the vendor returned them, the readable reasoning summaries (``reasoning``; never the
    raw chain of thought) and the vendor's output items verbatim (``vendor``, ``vendor_items``:
    OpenAI output items with encrypted reasoning, Anthropic content blocks with signed
    thinking), which later requests send back unchanged.
``tool_call`` / ``tool_result``
    one tool request and its result; the result carries the full output (``content``) and the
    text sent to the agent (``content_sent``), which may be shortened by the output cap.
``continuation``, ``reminder``, ``check_failure_message``, ``budget_termination``
    the execution messages of the harness, verbatim as sent or recorded.
``check_outcome``
    the result of the harness's file and expression checks.
``correction``
    the start of the one permitted correction attempt.
``helper_start`` / ``helper_end``
    a helper agent's allowance and totals.
``evaluation``
    the call of the evaluation callback on the checked candidates.
``round_end``
    outcome, totals, excess, candidate files.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

__all__ = ["EVENT_KINDS", "SESSION_EVENT_KINDS", "Event", "EventSink", "MemorySink", "NullSink", "FanoutSink"]

EVENT_KINDS: frozenset[str] = frozenset(
    {
        "round_start",
        "user_message",
        "request",
        "request_error",
        "response",
        "tool_call",
        "tool_result",
        "continuation",
        "reminder",
        "check_outcome",
        "check_failure_message",
        "correction",
        "budget_termination",
        "helper_start",
        "helper_end",
        "evaluation",
        "round_end",
        # added through the tool registry and the session layer of interactive operation
        "user_question",
        "user_answer",
    }
)
"""Event kinds emitted by the harness. The session layer adds ``user_question`` and ``user_answer``."""

SESSION_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "session_start",
        "task_change",
        "task_change_refused",
        "round_completion",
        "recommendation_recorded",
        "pool_version_saved",
        "permitted_results_screened",
        "user_shown_sealed_results",
        "brief_regenerated",
        "workspace_archived",
        "user_action",
        "analysis_answer",
        "session_end",
        # the task interview that precedes a session started from data files (aspire_sysid.session.interview)
        "interview_start",
        "task_check",
        "task_verdict",
        "interview_end",
    }
)
"""Event kinds emitted by the session layer of interactive operation
(:mod:`aspire_sysid.session`), in addition to :data:`EVENT_KINDS` (which lists
``user_question`` and ``user_answer`` of ``ask_user``). Session events carry ``agent = "harness"``.
Defined here, next to :data:`EVENT_KINDS`, so that the transcript writer (:mod:`aspire_sysid.record`) accepts them without
importing the session layer."""


@dataclass(frozen=True)
class Event:
    """One recorded event: its kind and its fields."""

    kind: str
    fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """The event as one JSON object, ``{"kind": ..., **fields}`` (one line of the JSONL transcript)."""
        return {"kind": self.kind, **self.fields}


class EventSink(abc.ABC):
    """Receiver of the harness's events. :mod:`aspire_sysid.record` implements the JSONL transcript."""

    @abc.abstractmethod
    def emit(self, kind: str, **fields: Any) -> None:
        """Record one event of ``kind`` with ``fields`` (JSON-serializable). """


class MemorySink(EventSink):
    """An in-memory sink that keeps every event in :attr:`events` (tests)."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def emit(self, kind: str, **fields: Any) -> None:
        """Append the event. """
        self.events.append(Event(kind=kind, fields=dict(fields)))

    def of_kind(self, kind: str) -> list[Event]:
        """The recorded events of one kind, in order."""
        return [e for e in self.events if e.kind == kind]

    def kinds(self) -> list[str]:
        """The kinds of the recorded events, in order."""
        return [e.kind for e in self.events]


class NullSink(EventSink):
    """A sink that discards every event, for callers that keep no record."""

    def emit(self, kind: str, **fields: Any) -> None:
        """Discard the event."""


class FanoutSink(EventSink):
    """A sink that passes every event to several sinks, in order."""

    def __init__(self, *sinks: EventSink) -> None:
        self.sinks = list(sinks)

    def emit(self, kind: str, **fields: Any) -> None:
        """Pass the event to every sink. """
        for s in self.sinks:
            s.emit(kind, **fields)
