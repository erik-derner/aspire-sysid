"""The transcript of a run: every event of the harness as JSON Lines.

The harness records every language-model request and response, tool request and result, user
message, reminder, check outcome and termination event. The record includes labels identifying
the task, session, round, candidate and pool version; timestamps; the model identifier and the
tool configuration; the system prompt and the brief with a cryptographic hash of each; software
and code revisions; random seeds; turns and tokens; elapsed execution time; and the cost computed
from a dated price schedule. User waiting time and any execution excess are recorded separately.

Format (schema version :data:`TRANSCRIPT_SCHEMA_VERSION`). A transcript is a UTF-8 text file
with one JSON object per line (JSON Lines). The file is opened for appending only; every line is
written, flushed and (by default) synchronized to the disk before :meth:`TranscriptWriter.emit`
returns, so that a crash of the harness loses at most the line being written. Every line has

* ``schema_version`` (this format), ``line`` (1, 2, ... in the file), ``kind`` and
  ``recorded_at`` (UTC, ISO 8601, the time of writing);
* the labels ``task``, ``session``, ``round``, ``pool_version``, ``agent`` and ``candidate``
  (``None`` where an event concerns no single candidate);
* the fields of the event (:mod:`aspire_sysid.agent.events` lists them per kind): the turn loop
  supplies ``seq``, ``timestamp`` (UTC, ISO 8601) and ``elapsed_s`` (elapsed execution time of
  the round), the full request (``round_start`` carries the system prompt, the tool
  descriptions, the model and the price entry with its verification date; each ``request``
  carries the messages added since the previous request), the full response (text, tool
  calls, usage, cost, round totals), the full tool requests and results, and the execution
  messages verbatim.

The first line is a ``transcript_start`` record with the harness version and the code revision
(git commit and dirty flag), followed by the header fields that the caller supplies (the experiment
runner passes the run identifier, seeds, model and tool configuration; the model, the tool
configuration and the dated price entry are in any case in every ``round_start`` event);
:meth:`TranscriptWriter.close` appends ``transcript_end``. A file that is opened again (a resumed
session) receives a ``transcript_resume`` line instead of a second ``transcript_start``. When the
last line of the file has no newline (a crash while it was being written), the writer cuts it off
before appending and records the repair as a ``transcript_repair`` line with the number of
discarded bytes and their text.

Additions by the writer (derived, never replacing an event field):

* ``candidate``: the label of the candidate an event concerns: a ``tool_call`` or
  ``tool_result`` whose ``path`` argument names ``models/<label>.json``, and the
  ``evaluation`` event when it concerns exactly one candidate. ``check_outcome`` and
  ``evaluation`` also list the labels they concern in ``candidates`` (for ``check_outcome``, the
  candidates within the pool limit that passed the checks).
* System prompts are written in full once. A later event with an identical system prompt (the
  same SHA-256 digest) carries ``system_prompt: null`` and ``system_prompt_omitted``, the line
  on which the text was recorded; the digest ``system_prompt_sha256`` is always present.
* Each ``request`` receives ``system_prompt_sha256`` and ``tools_line`` (the line of the
  ``round_start`` or ``helper_start`` event whose system prompt and tool descriptions the
  request used), so that every request can be reconstructed exactly
  (:func:`reconstruct_requests`).

The reader (:func:`read_transcript`, :func:`reconstruct_rounds`, :func:`reconstruct_requests`)
rebuilds the rounds (turns, tokens, cost, elapsed time, user waiting time, excess, outcome) and
every request from the file alone and states whether the totals agree with the ones the loop
recorded at the end of each round.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..portable import portable_data
from .. import __version__
from ..agent.events import EVENT_KINDS, SESSION_EVENT_KINDS, EventSink

__all__ = [
    "TRANSCRIPT_SCHEMA_VERSION",
    "RECORD_KINDS",
    "TranscriptError",
    "TranscriptWriter",
    "TranscriptContents",
    "RoundSummary",
    "ReconstructedRequest",
    "read_transcript",
    "reconstruct_rounds",
    "reconstruct_requests",
    "summarize_transcript",
]

TRANSCRIPT_SCHEMA_VERSION = 1
"""Version of the transcript format described in the module docstring."""

RECORD_KINDS: frozenset[str] = frozenset({"transcript_start", "transcript_resume", "transcript_repair", "transcript_end", "note"})
"""Kinds written by the transcript writer itself, in addition to :data:`EVENT_KINDS`."""

_MODEL_FILE = re.compile(r"^(?:\./)?models/([A-Za-z][A-Za-z0-9_-]{0,31})\.json$")
_LABEL_FIELDS = ("task", "session", "round", "pool_version", "agent", "candidate")


_PORTABLE_ROUND_START_FIELDS = ("workspace", "environment", "configuration", "price")
"""Fields of ``round_start`` whose paths are written in machine-independent form."""

class TranscriptError(ValueError):
    """A transcript line is not valid JSON, lacks a required field or has an unknown schema version. """


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    """``value`` with non-finite floats written as strings (JSON has no NaN or infinity)."""
    if isinstance(value, float) and not math.isfinite(value):
        return "nan" if value != value else ("inf" if value > 0 else "-inf")
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        return value
    return str(value)


def _candidate_of_path(path: Any) -> str | None:
    if not isinstance(path, str):
        return None
    m = _MODEL_FILE.match(path.replace("\\", "/"))
    if m and m.group(1) != "pool":
        return m.group(1)
    return None


class TranscriptWriter(EventSink):
    """JSON Lines transcript of a run; the event sink of the turn loop.

    ``path`` is the transcript file (created with its folder; appended to when it exists).
    ``header`` holds the run-level fields of the ``transcript_start`` line (run identifier, seeds,
    model, tool configuration, price schedule, code revision, ...). ``fsync`` synchronizes every
    line to the disk (crash safety); tests may switch it off. ``clock`` returns the UTC time
    stamp of each line (injectable for tests).
    """

    def __init__(
        self,
        path: str | Path,
        *,
        header: Mapping[str, Any] | None = None,
        fsync: bool = True,
        clock: Any = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fsync = fsync
        self._clock = clock or _utc_now
        resumed = self.path.exists() and self.path.stat().st_size > 0
        self._line = 0
        self._prompt_lines: dict[str, int] = {}
        self._agent_context: dict[tuple[Any, Any, str], dict[str, Any]] = {}
        self._call_candidates: dict[str, str] = {}
        repair: dict[str, Any] | None = None
        if resumed:
            repair = self._repair_end()
            prior = read_transcript(self.path, tolerate_truncated_end=False)
            self._line = len(prior.lines)
            for ev in prior.lines:
                self._learn(ev)
        self._fh = open(self.path, "a", encoding="utf-8", newline="\n")
        self.closed = False
        from .run_record import code_revision  # lazy: run_record imports the evaluation package

        head = {"harness_version": __version__, "code_revision": code_revision(), **dict(header or {})}
        self._write("transcript_resume" if resumed else "transcript_start", head)
        if repair is not None:
            self._write("transcript_repair", repair)

    def _repair_end(self) -> dict[str, Any] | None:
        """Cut a last line without its newline (the trace of a crash while writing it) before appending.

        Returns the repair record (number of discarded bytes and their text) or ``None`` when the
        file ends with a newline. 
        """
        blob = self.path.read_bytes()
        if blob.endswith(b"\n"):
            return None
        keep = blob.rfind(b"\n") + 1
        discarded = blob[keep:]
        with open(self.path, "r+b") as fh:
            fh.truncate(keep)
            fh.flush()
            if self.fsync:
                os.fsync(fh.fileno())
        return {
            "discarded_bytes": len(discarded),
            "discarded_text": discarded.decode("utf-8", errors="replace"),
            "reason": "the last line had no newline: it was being written when the previous harness process stopped",
        }

    # -- EventSink ---------------------------------------------------------------------------

    def emit(self, kind: str, **fields: Any) -> None:
        """Append one event of the turn loop or the session layer (module docstring)."""
        self._write(kind, dict(fields))

    def note(self, text: str, **fields: Any) -> None:
        """Append a free-text note of the harness (for example a crash-resume notice), kind ``note``. """
        self._write("note", {"text": text, **fields})

    def close(self, **summary: Any) -> None:
        """Append ``transcript_end`` with ``summary`` and close the file."""
        if self.closed:
            return
        self._write("transcript_end", dict(summary))
        self._fh.close()
        self.closed = True

    def __enter__(self) -> "TranscriptWriter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- internals -----------------------------------------------------------------------------

    def _learn(self, ev: Mapping[str, Any]) -> None:
        """Update the prompt registry and request context from a written (or re-read) line."""
        kind = ev.get("kind")
        if kind == "tool_call" and isinstance(ev.get("call_id"), str) and ev.get("candidate"):
            self._call_candidates[ev["call_id"]] = str(ev["candidate"])
        h = ev.get("system_prompt_sha256")
        if kind in ("round_start", "helper_start") and isinstance(h, str):
            if isinstance(ev.get("system_prompt"), str):
                self._prompt_lines.setdefault(h, int(ev.get("line", 0)))
            key = (ev.get("session"), ev.get("round"), ev.get("exchange"), str(ev.get("agent", "main")))
            self._agent_context[key] = {"system_prompt_sha256": h, "tools_line": int(ev.get("line", 0))}
            if kind == "round_start":
                # a helper uses the round's tool descriptions minus start_helper, recorded in helper_start
                self._agent_context[(ev.get("session"), ev.get("round"), ev.get("exchange"), "main")] = self._agent_context[key]

    def _derive(self, kind: str, rec: dict[str, Any]) -> None:
        """Add the writer's derived fields (module docstring)."""
        cand = rec.get("candidate")
        if cand is None and kind in ("tool_call", "tool_result"):
            call_id = rec.get("call_id")
            if kind == "tool_call":
                args = rec.get("arguments") if isinstance(rec.get("arguments"), Mapping) else {}
                cand = _candidate_of_path(args.get("path"))
                if cand is not None and isinstance(call_id, str):
                    self._call_candidates[call_id] = cand
            elif isinstance(call_id, str):
                cand = self._call_candidates.get(call_id)
        if kind == "check_outcome":
            # the checks concern the whole pool; the passing candidates within the limit are listed
            rec.setdefault("candidates", list(rec.get("evaluated") or []))
        if cand is None and kind == "evaluation":
            labels = list(rec.get("labels") or [])
            rec.setdefault("candidates", labels)
            if len(labels) == 1:
                cand = labels[0]
        rec["candidate"] = cand
        if kind in ("round_start", "helper_start") and isinstance(rec.get("system_prompt"), str):
            h = rec.get("system_prompt_sha256") or _sha256(rec["system_prompt"])
            rec["system_prompt_sha256"] = h
            if h in self._prompt_lines:
                rec["system_prompt"] = None
                rec["system_prompt_omitted"] = f"identical to the system prompt recorded on line {self._prompt_lines[h]}"
        if kind == "request":
            key = (rec.get("session"), rec.get("round"), rec.get("exchange"), str(rec.get("agent", "main")))
            ctx = self._agent_context.get(key) or self._agent_context.get((rec.get("session"), rec.get("round"), rec.get("exchange"), "main"))
            if ctx is not None:
                rec.setdefault("system_prompt_sha256", ctx["system_prompt_sha256"])
                rec.setdefault("tools_line", ctx["tools_line"])

    def _write(self, kind: str, fields: dict[str, Any]) -> None:
        if getattr(self, "closed", False):
            raise ValueError("the transcript is closed")
        if kind not in EVENT_KINDS and kind not in RECORD_KINDS and kind not in SESSION_EVENT_KINDS:
            raise TranscriptError(f"unknown event kind {kind!r}")
        self._line += 1
        rec: dict[str, Any] = {"schema_version": TRANSCRIPT_SCHEMA_VERSION, "line": self._line, "kind": kind,
                               "recorded_at": self._clock()}
        for k in _LABEL_FIELDS:
            rec[k] = fields.pop(k, None) if k in fields else None
        rec.update(fields)
        self._derive(kind, rec)
        if kind == "round_start":
            # the folders of this computer in the round's settings, not in the verbatim texts (aspire_sysid.portable)
            for key in _PORTABLE_ROUND_START_FIELDS:
                if key in rec:
                    rec[key] = portable_data(_json_safe(rec[key]))
        rec = _json_safe(rec)
        text = json.dumps(rec, ensure_ascii=False, allow_nan=False)
        self._fh.write(text + "\n")
        self._fh.flush()
        if self.fsync:
            os.fsync(self._fh.fileno())
        self._learn(rec)


# ---------------------------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------------------------


@dataclass
class TranscriptContents:
    """The lines of a transcript. ``truncated_end`` is true when the last line was
    cut off (a crash while writing it) and has been left out."""

    path: Path
    lines: list[dict[str, Any]]
    truncated_end: bool = False

    def of_kind(self, kind: str) -> list[dict[str, Any]]:
        """The lines of one kind, in order. """
        return [ev for ev in self.lines if ev.get("kind") == kind]

    def kinds(self) -> list[str]:
        """The kinds of the lines, in order. """
        return [str(ev.get("kind")) for ev in self.lines]


def read_transcript(path: str | Path, *, tolerate_truncated_end: bool = True) -> TranscriptContents:
    """Read a transcript. Raises :class:`TranscriptError` on a malformed line.

    A final line without its newline that is not valid JSON is the trace of a crash during
    writing; with ``tolerate_truncated_end`` it is dropped and reported in ``truncated_end``.
    """
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    parts = raw.split("\n")
    complete_end = raw.endswith("\n") or raw == ""
    out: list[dict[str, Any]] = []
    truncated = False
    for i, text in enumerate(parts):
        if text == "":
            continue
        last = i == len(parts) - 1
        try:
            ev = json.loads(text)
        except json.JSONDecodeError as exc:
            if last and not complete_end and tolerate_truncated_end:
                truncated = True
                break
            raise TranscriptError(f"{p}: line {i + 1} is not valid JSON: {exc}") from exc
        if not isinstance(ev, dict) or "kind" not in ev:
            raise TranscriptError(f"{p}: line {i + 1} is not an event object")
        if ev.get("schema_version") != TRANSCRIPT_SCHEMA_VERSION:
            raise TranscriptError(f"{p}: line {i + 1} has schema version {ev.get('schema_version')!r}, expected {TRANSCRIPT_SCHEMA_VERSION}")
        out.append(ev)
    return TranscriptContents(p, out, truncated)


def _events(source: Any) -> list[dict[str, Any]]:
    if isinstance(source, TranscriptContents):
        return source.lines
    if isinstance(source, (str, Path)):
        return read_transcript(source).lines
    return list(source)


@dataclass
class RoundSummary:
    """One round or analysis exchange rebuilt from the transcript alone.

    ``turns`` counts the completed responses of all agents (main agent and helpers), ``turns_main``
    those of the main agent; ``cost_usd`` and the token counts are the sums over the response
    events; ``elapsed_s``, ``waiting_s`` and ``excess`` are those recorded at the end of the round.
    ``recorded_totals`` are the round totals of the ``round_end`` event; ``consistent`` states
    whether the reconstruction agrees with them (turns and tokens exactly, cost within 1e-9 USD).
    """

    session: Any
    round: Any
    mode: str | None
    pool_version: Any
    model: str | None
    configuration: str | None
    exchange: Any = None
    turns: int = 0
    turns_main: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_usage_turns: int = 0
    cost_usd: float = 0.0
    requests: int = 0
    request_errors: int = 0
    tool_calls: int = 0
    tool_results: int = 0
    reminders: int = 0
    continuations: int = 0
    check_outcomes: list[bool] = field(default_factory=list)
    outcome: str | None = None
    limit: Any = None
    elapsed_s: float | None = None
    waiting_s: float | None = None
    excess: dict[str, Any] | None = None
    price: dict[str, Any] | None = None
    recorded_totals: dict[str, Any] | None = None
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    candidates_written: list[str] = field(default_factory=list)

    @property
    def consistent(self) -> bool | None:
        """Agreement of the reconstruction with the loop's recorded totals; ``None`` without ``round_end``. """
        t = self.recorded_totals
        if t is None:
            return None
        return (
            int(t.get("turns", -1)) == self.turns
            and int(t.get("input_tokens", -1)) == self.input_tokens
            and int(t.get("output_tokens", -1)) == self.output_tokens
            and abs(float(t.get("cost_usd", math.nan)) - self.cost_usd) <= 1e-9
        )

    def to_dict(self) -> dict[str, Any]:
        """Plain data."""
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        d["consistent"] = self.consistent
        return d


def reconstruct_rounds(source: Any) -> list[RoundSummary]:
    """Rebuild every round and analysis exchange of a transcript.

    ``source`` is a path, :class:`TranscriptContents` or a list of event dictionaries. The rounds
    are returned in the order of their ``round_start`` events.
    """
    rounds: dict[tuple[Any, Any, Any], RoundSummary] = {}
    order: list[tuple[Any, Any, Any]] = []
    for ev in _events(source):
        kind = ev.get("kind")
        if kind in RECORD_KINDS or kind in SESSION_EVENT_KINDS:
            continue  # session events belong to no round or exchange
        # an analysis exchange of interactive operation carries the label ``exchange`` on every
        # event, so that it is kept apart from the round whose round label it shares
        key = (ev.get("session"), ev.get("round"), ev.get("exchange"))
        rs = rounds.get(key)
        if kind == "round_start" or rs is None:
            if kind == "round_start" and rs is not None and rs.recorded_totals is not None:
                # a new round with the same labels (not produced by the harness); keep them apart
                key = (ev.get("session"), f"{ev.get('round')}#{len(order) + 1}", ev.get("exchange"))
            if key not in rounds:
                cfg = ev.get("configuration") if isinstance(ev.get("configuration"), Mapping) else {}
                rs = RoundSummary(session=key[0], round=ev.get("round"), mode=ev.get("mode"), pool_version=ev.get("pool_version"),
                                  model=ev.get("model"), configuration=cfg.get("name") if cfg else None, price=ev.get("price"),
                                  exchange=ev.get("exchange"))
                rounds[key] = rs
                order.append(key)
            rs = rounds[key]
        ts = ev.get("timestamp")
        if isinstance(ts, str):
            rs.first_timestamp = rs.first_timestamp or ts
            rs.last_timestamp = ts
        if kind == "response":
            rs.turns += 1
            if ev.get("agent", "main") == "main":
                rs.turns_main += 1
            charged = ev.get("usage_charged") or ev.get("usage") or {}
            rs.input_tokens += int(charged.get("input_tokens", 0) or 0)
            rs.output_tokens += int(charged.get("output_tokens", 0) or 0)
            rs.estimated_usage_turns += bool(ev.get("usage_estimated"))
            c = ev.get("cost_usd")
            if isinstance(c, (int, float)):
                rs.cost_usd += float(c)
        elif kind == "request":
            rs.requests += 1
        elif kind == "request_error":
            rs.request_errors += 1
        elif kind == "tool_call":
            rs.tool_calls += 1
            if ev.get("candidate") and ev["candidate"] not in rs.candidates_written:
                rs.candidates_written.append(ev["candidate"])
        elif kind == "tool_result":
            rs.tool_results += 1
        elif kind == "reminder":
            rs.reminders += 1
        elif kind == "continuation":
            rs.continuations += 1
        elif kind == "check_outcome":
            rs.check_outcomes.append(bool(ev.get("passed")))
        elif kind == "round_end":
            rs.outcome = ev.get("outcome")
            rs.limit = ev.get("limit")
            totals = ev.get("totals") if isinstance(ev.get("totals"), Mapping) else {}
            rs.recorded_totals = dict(totals)
            rs.elapsed_s = totals.get("elapsed_s")
            rs.waiting_s = totals.get("waiting_s")
            rs.excess = ev.get("excess")
    return [rounds[k] for k in order]


@dataclass(frozen=True)
class ReconstructedRequest:
    """One language-model request rebuilt from the transcript: the system prompt,
    the tool descriptions and the complete message list, as sent."""

    line: int
    session: Any
    round: Any
    agent: str
    model: str | None
    system_prompt: str | None
    system_prompt_sha256: str | None
    tools: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    max_output_tokens: Any
    timeout_s: Any
    reasoning: Any = None


def reconstruct_requests(source: Any) -> list[ReconstructedRequest]:
    """Rebuild every language-model request of a transcript exactly.

    The messages of a request are, in order, the messages added before each request of the same
    agent in the round (``request.new_messages``; the first request of a round includes the
    history of earlier rounds and the first user message, that of a helper its task text) and
    each earlier response of that agent as an assistant message. The
    system prompt is resolved through its digest, also where the writer omitted a repeated text.
    """
    evs = _events(source)
    prompts: dict[str, str] = {}
    tools_at: dict[int, list[dict[str, Any]]] = {}
    convo: dict[tuple[Any, Any, Any, str], list[dict[str, Any]]] = {}
    out: list[ReconstructedRequest] = []
    for ev in evs:
        kind = ev.get("kind")
        agent = str(ev.get("agent") or "main")
        key = (ev.get("session"), ev.get("round"), ev.get("exchange"), agent)
        if kind in ("round_start", "helper_start"):
            if isinstance(ev.get("system_prompt"), str):
                prompts[str(ev.get("system_prompt_sha256"))] = ev["system_prompt"]
            if kind == "round_start":
                tools_at[int(ev.get("line", 0))] = list(ev.get("tools") or [])
                # the first request's new_messages start with the history of earlier rounds
                convo[key] = []
            else:
                names = set(ev.get("tools") or [])
                base = next((t for ln, t in sorted(tools_at.items(), reverse=True) if ln < int(ev.get("line", 0))), [])
                tools_at[int(ev.get("line", 0))] = [t for t in base if t.get("name") in names]
                convo[key] = []
        elif kind == "request":
            msgs = convo.setdefault(key, [])
            msgs.extend(ev.get("new_messages") or [])
            h = ev.get("system_prompt_sha256")
            out.append(
                ReconstructedRequest(
                    line=int(ev.get("line", 0)),
                    session=ev.get("session"),
                    round=ev.get("round"),
                    agent=agent,
                    model=ev.get("model"),
                    system_prompt=prompts.get(str(h)),
                    system_prompt_sha256=h,
                    tools=tools_at.get(int(ev.get("tools_line") or 0), []),
                    messages=[dict(m) for m in msgs],
                    max_output_tokens=ev.get("max_output_tokens"),
                    timeout_s=ev.get("timeout_s"),
                    reasoning=ev.get("reasoning"),
                )
            )
        elif kind == "response":
            # the same form as providers.message_to_dict: reasoning and vendor items only when recorded
            msg: dict[str, Any] = {"role": "assistant", "text": ev.get("text", ""), "tool_calls": list(ev.get("tool_calls") or [])}
            if ev.get("reasoning"):
                msg["reasoning"] = list(ev["reasoning"])
            if ev.get("vendor_items"):
                msg["vendor"] = ev.get("vendor")
                msg["vendor_items"] = list(ev["vendor_items"])
            convo.setdefault(key, []).append(msg)
    return out


def summarize_transcript(source: Any) -> dict[str, Any]:
    """A plain summary of a transcript for ``aspire record show``."""
    contents = source if isinstance(source, TranscriptContents) else None
    evs = _events(source)
    kinds: dict[str, int] = {}
    for ev in evs:
        kinds[str(ev.get("kind"))] = kinds.get(str(ev.get("kind")), 0) + 1
    rounds = reconstruct_rounds(evs)
    return {
        "lines": len(evs),
        "truncated_end": bool(contents.truncated_end) if contents is not None else False,
        "kinds": dict(sorted(kinds.items())),
        "rounds": [r.to_dict() for r in rounds],
    }


def iter_labels(events: Iterable[Mapping[str, Any]]) -> Iterable[tuple[str, dict[str, Any]]]:
    """``(kind, labels)`` of every event: the label fields (task, session, round, pool version, agent, candidate; helper for tests and reports)."""
    for ev in events:
        yield str(ev.get("kind")), {k: ev.get(k) for k in _LABEL_FIELDS}
