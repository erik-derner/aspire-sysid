"""Provider adapters: one vendor-neutral interface to the language-model APIs.

A turn is one completed language-model response to the system prompt, the conversation history
and the descriptions of the available tools. The harness records the tokens of every request,
and every request and response with the model identifier. The agent loop talks to plain model
APIs through a thin adapter and accepts pinned model identifiers only.

This module provides

* vendor-neutral data types: :class:`ToolSpec`, :class:`ToolCall`, :class:`Usage`, the messages
  :class:`UserMessage`, :class:`AssistantMessage` and :class:`ToolResultMessage`,
  :class:`ProviderRequest` and :class:`ProviderResponse`. The system prompt is not a message; it
  is the separate argument ``system`` of :meth:`Provider.complete`, because both APIs carry it
  outside the message list;
* the abstract interface :class:`Provider`;
* :class:`ScriptedProvider`, which returns scripted responses and records every request, for
  tests; no test of the harness calls a real model;
* :class:`OpenAIProvider` and :class:`AnthropicProvider` for the two vendors, with lazy import of
  the vendor software development kit (SDK), the API key read from an environment variable only,
  bounded retries with exponential backoff and a request timeout;
* :func:`make_provider`, which accepts pinned model identifiers only.

Design: a neutral message format with conversions to both APIs, typed immutable messages,
cached-input and reasoning token counts, a retry loop owned by the harness with a deadline, and
the rejection of floating model aliases.
"""

from __future__ import annotations

import abc
import datetime as _dt
import json
import os
import re
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence, Union

import yaml

from ..paths import config_path

__all__ = [
    "ProviderError",
    "ProviderConfigError",
    "ModelIdError",
    "ScriptExhaustedError",
    "ConversationProtocolError",
    "check_conversation_protocol",
    "OPENAI_TOOL_ERROR_MARKER",
    "ToolSpec",
    "ToolCall",
    "Usage",
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "Message",
    "message_to_dict",
    "message_from_dict",
    "ProviderRequest",
    "ProviderResponse",
    "Provider",
    "ScriptStep",
    "ScriptedProvider",
    "RetryPolicy",
    "is_retryable_error",
    "call_with_retries",
    "OpenAIProvider",
    "AnthropicProvider",
    "ReasoningSettings",
    "openai_request_input",
    "openai_tools",
    "openai_parse_response",
    "anthropic_request_messages",
    "anthropic_tools",
    "anthropic_parse_response",
    "vendor_of",
    "check_pinned_model_id",
    "default_model_id",
    "load_model_allowlist",
    "make_provider",
]


# --------------------------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------------------------


class ProviderError(RuntimeError):
    """A language-model request failed (the failure is recorded by the caller).

    ``retryable`` states whether the failure is of a transient kind (rate limit, server error,
    timeout, connection error); ``attempts`` is the number of requests that were sent.

    Limitation of the cost record: a failed or timed-out attempt returns no usage
    record, so its tokens, and any charge the vendor makes for them, cannot be recorded by the
    harness. The caller records the number of failed attempts instead.
    """

    def __init__(self, message: str, *, retryable: bool = False, attempts: int = 0) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.attempts = attempts


class ProviderConfigError(ProviderError):
    """The adapter cannot be constructed: vendor SDK not installed or API key not set."""


class ModelIdError(ValueError):
    """The model identifier is not a pinned snapshot accepted by the harness."""


class ScriptExhaustedError(ProviderError):
    """A :class:`ScriptedProvider` received more requests than it has scripted responses."""


class ConversationProtocolError(ProviderError):
    """A request violates the tool-call protocol of the conversation history.

    Raised by :func:`check_conversation_protocol`; both vendor APIs reject such histories, so
    the scripted provider rejects them too.
    """


# --------------------------------------------------------------------------------------------
# Vendor-neutral data types
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolSpec:
    """Description of a tool offered to the agent (part of every request).

    ``parameters`` is a JSON Schema object describing the arguments. ``vendor_tool`` names a tool
    that the model's vendor executes itself inside a response, when the adapter of that vendor
    supports it: ``"web_search"``. An adapter without such a tool offers the
    description as an ordinary function tool, which the harness then answers.
    """

    name: str
    description: str
    parameters: Mapping[str, Any]
    vendor_tool: str | None = None


@dataclass(frozen=True)
class ToolCall:
    """One tool request of the agent.

    ``arguments`` is the decoded argument object. When the vendor returned an argument string
    that is not a JSON object, ``arguments`` is empty, ``arguments_error`` states the problem and
    ``raw_arguments`` keeps the string verbatim for the record.
    """

    id: str
    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    raw_arguments: str | None = None
    arguments_error: str | None = None


@dataclass(frozen=True)
class Usage:
    """Token counts of one or more language-model responses.

    ``input_tokens`` is the total number of input tokens processed, including cached ones;
    ``cached_input_tokens`` is the part served from the vendor's cache, or ``None`` when the
    vendor did not report it. ``output_tokens`` includes reasoning tokens; ``reasoning_tokens``
    is that part, or ``None`` when not reported. ``reported`` is false when the vendor response
    carried no usage record; the counts are then zero and the caller records the omission.
    ``web_search_calls`` is the number of web search actions that the vendor executed inside the
    responses (its built-in web search tool); the vendor charges a fee per call in addition to
    the tokens.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    reported: bool = True
    web_search_calls: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        if not isinstance(other, Usage):
            return NotImplemented

        def _sum(a: int | None, b: int | None) -> int | None:
            if a is None and b is None:
                return None
            return (a or 0) + (b or 0)

        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cached_input_tokens=_sum(self.cached_input_tokens, other.cached_input_tokens),
            reasoning_tokens=_sum(self.reasoning_tokens, other.reasoning_tokens),
            reported=self.reported and other.reported,
            web_search_calls=self.web_search_calls + other.web_search_calls,
        )


@dataclass(frozen=True)
class UserMessage:
    """A message from the user or the harness to the agent (brief, continuation message, reminder)."""

    text: str
    role: str = field(default="user", init=False)


@dataclass(frozen=True)
class ReasoningSettings:
    """Reasoning settings of every request.

    ``effort`` is the reasoning effort passed to the vendor (OpenAI ``reasoning.effort``:
    ``none``, ``low``, ``medium``, ``high``, ``xhigh``; Anthropic ``output_config.effort``, with
    ``none`` meaning thinking disabled); ``None`` leaves the model's default, which is then not
    stated in the record. ``summary`` requests a readable summary of the reasoning (OpenAI
    ``reasoning.summary``: ``auto``, ``concise``, ``detailed``; Anthropic ``display:
    summarized``); ``None`` requests none. Neither vendor returns the raw chain of thought.
    """

    effort: str | None = None
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the record."""
        return {"effort": self.effort, "summary": self.summary}


@dataclass(frozen=True)
class AssistantMessage:
    """A response of the agent: text and tool requests.

    ``reasoning`` holds the readable reasoning summaries the vendor returned with the response
    (not the raw chain of thought). ``vendor`` and ``vendor_items`` keep the vendor's output items
    verbatim (OpenAI Responses output items, including encrypted reasoning items; Anthropic
    content blocks, including signed thinking blocks); the adapter of the same vendor sends them
    back unchanged in later requests, as both APIs require for reasoning to carry over between
    tool calls. Other adapters use ``text`` and ``tool_calls``.
    """

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    reasoning: tuple[str, ...] = ()
    vendor: str | None = None
    vendor_items: tuple[Mapping[str, Any], ...] = ()
    role: str = field(default="assistant", init=False)


@dataclass(frozen=True)
class ToolResultMessage:
    """The result of one executed tool request, returned to the agent."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False
    role: str = field(default="tool", init=False)


Message = Union[UserMessage, AssistantMessage, ToolResultMessage]


def message_to_dict(message: Message) -> dict[str, Any]:
    """JSON-serializable form of a message, for the transcript."""
    if isinstance(message, UserMessage):
        return {"role": "user", "text": message.text}
    if isinstance(message, AssistantMessage):
        out: dict[str, Any] = {
            "role": "assistant",
            "text": message.text,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": dict(tc.arguments),
                    "raw_arguments": tc.raw_arguments,
                    "arguments_error": tc.arguments_error,
                }
                for tc in message.tool_calls
            ],
        }
        # written only when present, so that records without reasoning have no such field
        if message.reasoning:
            out["reasoning"] = list(message.reasoning)
        if message.vendor_items:
            out["vendor"] = message.vendor
            out["vendor_items"] = [dict(i) for i in message.vendor_items]
        return out
    if isinstance(message, ToolResultMessage):
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "name": message.name,
            "content": message.content,
            "is_error": message.is_error,
        }
    raise TypeError(f"not a message: {message!r}")


def message_from_dict(data: Mapping[str, Any]) -> Message:
    """Inverse of :func:`message_to_dict` (a record can be replayed)."""
    role = data.get("role")
    if role == "user":
        return UserMessage(text=str(data["text"]))
    if role == "assistant":
        return AssistantMessage(
            text=str(data.get("text", "")),
            tool_calls=tuple(
                ToolCall(
                    id=str(tc["id"]),
                    name=str(tc["name"]),
                    arguments=dict(tc.get("arguments") or {}),
                    raw_arguments=tc.get("raw_arguments"),
                    arguments_error=tc.get("arguments_error"),
                )
                for tc in data.get("tool_calls", [])
            ),
            reasoning=tuple(str(x) for x in data.get("reasoning") or ()),
            vendor=data.get("vendor"),
            vendor_items=tuple(dict(i) for i in data.get("vendor_items") or ()),
        )
    if role == "tool":
        return ToolResultMessage(
            tool_call_id=str(data["tool_call_id"]),
            name=str(data["name"]),
            content=str(data["content"]),
            is_error=bool(data.get("is_error", False)),
        )
    raise ValueError(f"unknown message role {role!r}")


@dataclass(frozen=True)
class ProviderRequest:
    """One language-model request as the harness sent it (every request is recorded)."""

    model: str
    system: str
    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...]
    max_output_tokens: int
    timeout_s: float
    reasoning: ReasoningSettings | None = None


@dataclass(frozen=True)
class ProviderResponse:
    """One completed language-model response, that is, one turn.

    ``stop_reason`` is the vendor's stop reason verbatim (for example ``tool_calls``, ``stop``,
    ``length``, ``tool_use``, ``end_turn``, ``max_tokens``). ``latency_s`` is the wall-clock
    duration of :meth:`Provider.complete`, including retries and their waiting times;
    ``attempts`` is the number of requests sent. ``refusal`` is the vendor's refusal text when
    the model declined to answer (OpenAI refusal content), kept verbatim for the record
; it is not part of ``text``. ``reasoning``, ``vendor`` and ``vendor_items`` are
    those of :class:`AssistantMessage`. ``web_searches`` lists the web search actions that the
    vendor executed inside this response, each with ``action`` (``search``, ``open_page`` or
    ``find_in_page``), ``query`` or ``url`` and, when the vendor returned them, ``sources``.
    """

    text: str
    tool_calls: tuple[ToolCall, ...]
    usage: Usage
    model: str
    stop_reason: str
    latency_s: float = 0.0
    attempts: int = 1
    refusal: str | None = None
    reasoning: tuple[str, ...] = ()
    vendor: str | None = None
    vendor_items: tuple[Mapping[str, Any], ...] = ()
    web_searches: tuple[Mapping[str, Any], ...] = ()

    def to_message(self) -> AssistantMessage:
        """The response as an entry of the conversation history."""
        return AssistantMessage(text=self.text, tool_calls=self.tool_calls, reasoning=self.reasoning,
                                vendor=self.vendor, vendor_items=self.vendor_items)


class Provider(abc.ABC):
    """Vendor-neutral language-model interface.

    ``model_id`` is the pinned model identifier; ``vendor`` is ``openai``, ``anthropic`` or
    ``scripted``.
    """

    vendor: str = "abstract"

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    @abc.abstractmethod
    def complete(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        *,
        max_output_tokens: int,
        timeout_s: float,
        reasoning: ReasoningSettings | None = None,
    ) -> ProviderResponse:
        """Send one request and return the completed response (one turn).

        ``reasoning`` holds the reasoning settings of the request (``None``: the model's defaults).
        ``timeout_s`` is the deadline of the whole call, including retries; it must be positive.
        The bound is approximate: the vendor SDK applies its timeout per network operation, so a
        request can end somewhat after the deadline. Raises :class:`ProviderError`.
        """


def check_conversation_protocol(messages: Sequence[Message]) -> None:
    """Check the tool-call protocol of a conversation history (tool results are
    included in the next request).

    Rules: the tool-call identifiers of one assistant message are distinct; every tool call of an
    assistant message is answered exactly once by a tool result, with the same tool name, and
    these results directly follow that assistant message, with no other message in between; no
    tool result appears without a preceding tool call it answers; a history does not end with an
    unanswered tool call. Raises :class:`ConversationProtocolError` naming the message index.
    """
    pending: dict[str, str] = {}  # tool-call id -> tool name, awaiting a result
    pending_from: int | None = None
    for i, m in enumerate(messages):
        if isinstance(m, ToolResultMessage):
            if m.tool_call_id not in pending:
                raise ConversationProtocolError(
                    f"message {i}: tool result for id {m.tool_call_id!r} answers no pending tool call "
                    "of the directly preceding assistant message (orphan or duplicate result)"
                )
            expected = pending.pop(m.tool_call_id)
            if m.name != expected:
                raise ConversationProtocolError(
                    f"message {i}: tool result for id {m.tool_call_id!r} names tool {m.name!r}, "
                    f"but the call was to {expected!r}"
                )
            continue
        if pending:
            raise ConversationProtocolError(
                f"message {i} ({m.role}): tool calls {sorted(pending)} of message {pending_from} "
                "are not answered by tool results before the next message"
            )
        if isinstance(m, AssistantMessage):
            ids = [tc.id for tc in m.tool_calls]
            if len(set(ids)) != len(ids):
                raise ConversationProtocolError(f"message {i}: duplicate tool-call identifiers {ids}")
            if any(not x for x in ids):
                raise ConversationProtocolError(f"message {i}: a tool call has an empty identifier")
            pending = {tc.id: tc.name for tc in m.tool_calls}
            pending_from = i
        elif not isinstance(m, UserMessage):
            raise ConversationProtocolError(f"message {i}: not a message: {m!r}")
    if pending:
        raise ConversationProtocolError(
            f"end of history: tool calls {sorted(pending)} of message {pending_from} are not answered"
        )


# --------------------------------------------------------------------------------------------
# Scripted provider (tests)
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ScriptStep:
    """One scripted response of a :class:`ScriptedProvider`.

    Tool calls with an empty ``id`` receive the identifier ``call-<turn>-<index>``. When
    ``stop_reason`` is ``None``, it is ``tool_calls`` if tool calls are present, else ``stop``.
    """

    text: str = ""
    tool_calls: Sequence[ToolCall] = ()
    usage: Usage = field(default_factory=Usage)
    stop_reason: str | None = None
    latency_s: float = 0.0
    reasoning: Sequence[str] = ()


ScriptEntry = Union[
    ScriptStep,
    ProviderResponse,
    str,
    BaseException,
    Callable[[ProviderRequest], Union[ScriptStep, ProviderResponse, str]],
]


class ScriptedProvider(Provider):
    """A provider that returns a scripted sequence of responses; for tests only.

    Each script entry is one of: a :class:`ScriptStep`; a :class:`ProviderResponse` returned as
    given; a string, meaning a text-only response with zero usage; an exception instance, which
    is raised (to test failure handling); or a callable that receives the
    :class:`ProviderRequest` and returns one of the first three kinds (for tests whose response
    depends on what the harness sent). Every request is appended to :attr:`requests` before the
    entry is consumed, so a test can inspect exactly what was sent to the agent.
    A request beyond the end of the script raises :class:`ScriptExhaustedError`.

    Like the real adapters, the scripted provider rejects a non-positive ``timeout_s`` with
    :class:`ProviderError`. With ``check_protocol`` (the default) it also rejects a history that
    violates the tool-call protocol (:func:`check_conversation_protocol`) with
    :class:`ConversationProtocolError`, so that a harness test cannot pass on a history that a
    vendor API would refuse. A rejected request is recorded but consumes no script entry.
    """

    vendor = "scripted"

    def __init__(
        self,
        script: Iterable[ScriptEntry],
        model_id: str = "scripted",
        *,
        check_protocol: bool = True,
    ) -> None:
        super().__init__(model_id)
        self._script: list[ScriptEntry] = list(script)
        self._next = 0
        self.check_protocol = check_protocol
        self.requests: list[ProviderRequest] = []

    @property
    def remaining(self) -> int:
        """Number of script entries not yet consumed."""
        return len(self._script) - self._next

    def complete(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        *,
        max_output_tokens: int,
        timeout_s: float,
        reasoning: ReasoningSettings | None = None,
    ) -> ProviderResponse:
        """Record the request and return the next scripted response."""
        request = ProviderRequest(
            model=self.model_id,
            system=system,
            messages=tuple(messages),
            tools=tuple(tools),
            max_output_tokens=max_output_tokens,
            timeout_s=timeout_s,
            reasoning=reasoning,
        )
        self.requests.append(request)
        turn = len(self.requests)
        if not timeout_s > 0:
            raise ProviderError(f"scripted provider: no time remaining (timeout {timeout_s} s)", attempts=0)
        if self.check_protocol:
            check_conversation_protocol(request.messages)
        if self._next >= len(self._script):
            raise ScriptExhaustedError(
                f"scripted provider: request {turn} received, but the script has only "
                f"{len(self._script)} responses",
                attempts=1,
            )
        entry = self._script[self._next]
        self._next += 1
        if isinstance(entry, BaseException):
            raise entry
        if callable(entry) and not isinstance(entry, (ScriptStep, ProviderResponse, str)):
            entry = entry(request)
        if isinstance(entry, ProviderResponse):
            return entry
        if isinstance(entry, str):
            entry = ScriptStep(text=entry)
        if not isinstance(entry, ScriptStep):
            raise TypeError(f"scripted provider: invalid script entry {entry!r}")
        calls = tuple(
            tc if tc.id else replace(tc, id=f"call-{turn}-{i}")
            for i, tc in enumerate(entry.tool_calls, start=1)
        )
        stop = entry.stop_reason or ("tool_calls" if calls else "stop")
        return ProviderResponse(
            text=entry.text,
            tool_calls=calls,
            usage=entry.usage,
            model=self.model_id,
            stop_reason=stop,
            latency_s=entry.latency_s,
            attempts=1,
            reasoning=tuple(entry.reasoning),
        )


# --------------------------------------------------------------------------------------------
# Retries
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry with exponential backoff (retries and timeouts).

    The delay before retry ``j`` (``j = 1, 2, ...``) is ``min(max_delay_s, base_delay_s * 2**(j-1))``
    seconds, without random jitter so that the behavior is reproducible. At most
    ``max_attempts`` requests are sent, and no retry is started whose delay would pass the
    deadline of the call. Each attempt has the request timeout
    ``min(attempt_timeout_s, remaining time to the deadline)``, so that a timed-out attempt
    leaves time for a retry when the deadline of the call is longer than ``attempt_timeout_s``.
    """

    max_attempts: int = 5
    base_delay_s: float = 2.0
    max_delay_s: float = 60.0
    attempt_timeout_s: float = 600.0

    def delay_s(self, retry_index: int) -> float:
        """Waiting time before retry number ``retry_index`` (1-based). """
        return min(self.max_delay_s, self.base_delay_s * 2 ** (retry_index - 1))


_RETRYABLE_STATUS = {408, 409, 429}
_RETRYABLE_NAMES = {
    "APITimeoutError",
    "APIConnectionError",
    "RateLimitError",
    "InternalServerError",
    "OverloadedError",
    "ServiceUnavailableError",
    "DeadlineExceededError",
}


def is_retryable_error(exc: BaseException) -> bool:
    """Whether a failed request is of a transient kind: rate limit, server error, timeout or connection.

 The classification uses the HTTP
    status code (408, 409, 429 or at least 500) or the class name of the SDK exception, so that
    it works for both vendor SDKs without importing them.
    """
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and (status in _RETRYABLE_STATUS or status >= 500):
        return True
    return any(cls.__name__ in _RETRYABLE_NAMES for cls in type(exc).__mro__)


def call_with_retries(
    send: Callable[[float], Any],
    *,
    policy: RetryPolicy,
    timeout_s: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    what: str = "request",
) -> tuple[Any, int]:
    """Call ``send(attempt_timeout_s)`` with bounded retries; return ``(result, attempts)``.

 ``timeout_s`` is the
    deadline of the whole call; each attempt receives ``min(policy.attempt_timeout_s, remaining
    time)`` as its request timeout. The deadline is approximate, because the vendor SDK applies
    the timeout per network operation. A non-transient failure (:func:`is_retryable_error`
    false) is raised at once. Raises :class:`ProviderError`.
    """
    if timeout_s <= 0:
        raise ProviderError(f"{what}: no time remaining (timeout {timeout_s} s)", attempts=0)
    deadline = clock() + timeout_s
    attempt = 0
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            raise ProviderError(
                f"{what}: deadline of {timeout_s} s reached after {attempt} attempts",
                retryable=True,
                attempts=attempt,
            )
        attempt += 1
        try:
            return send(min(policy.attempt_timeout_s, remaining)), attempt
        except Exception as exc:  # noqa: BLE001 - classified below, re-raised as ProviderError
            retryable = is_retryable_error(exc)
            summary = f"{type(exc).__name__}: {exc}"
            if not retryable:
                raise ProviderError(
                    f"{what} failed (not retried): {summary}", retryable=False, attempts=attempt
                ) from exc
            if attempt >= policy.max_attempts:
                raise ProviderError(
                    f"{what} failed after {attempt} attempts: {summary}",
                    retryable=True,
                    attempts=attempt,
                ) from exc
            delay = policy.delay_s(attempt)
            if clock() + delay >= deadline:
                raise ProviderError(
                    f"{what} failed after {attempt} attempts; the next retry would pass the "
                    f"deadline of {timeout_s} s: {summary}",
                    retryable=True,
                    attempts=attempt,
                ) from exc
            sleep(delay)


def _api_key(env_var: str) -> str:
    key = os.environ.get(env_var, "").strip()
    if not key:
        raise ProviderConfigError(
            f"environment variable {env_var} is not set; the API key is read from the environment only"
        )
    return key


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Attribute or mapping access, so that SDK objects and plain dictionaries are both accepted."""
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------------------------
# OpenAI
# --------------------------------------------------------------------------------------------


OPENAI_TOOL_ERROR_MARKER = "ERROR: "
"""Prefix of the output of a failed tool result sent to the OpenAI Responses API, which has no
error flag for function-call outputs."""

_EMPTY_ASSISTANT_TEXT = "(empty response)"
"""Placeholder for an assistant message with neither text nor tool calls, which both vendor APIs
reject as empty content. The placeholder appears only in the request to the vendor, never in the
harness's history."""


def _jsonable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_none=True)
    if isinstance(obj, Mapping):
        return {str(k): _jsonable(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if hasattr(obj, "__dict__"):
        return {k: _jsonable(v) for k, v in vars(obj).items() if v is not None and not k.startswith("_")}
    return str(obj)


def _plain(obj: Any) -> dict[str, Any]:
    """A vendor SDK object (or mapping, or plain object in tests) as a JSON-serializable
    dictionary without null fields, for the record and for sending the item back unchanged
."""
    out = _jsonable(obj)
    if not isinstance(out, dict):
        raise TypeError(f"not a vendor output item: {obj!r}")
    return out


def _replayable_openai_items(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The output items of an earlier response to send back, without trailing reasoning items.

    A response that ended during its reasoning (``status: incomplete``, reason
    ``max_output_tokens``) has a reasoning item and no item after it; the API rejects a reasoning
    item without its following item. The record keeps the dropped items.
    """
    out = [dict(i) for i in items]
    while out and out[-1].get("type") == "reasoning":
        out.pop()
    return out


def openai_request_input(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """Convert the neutral history to Responses API input items.

    User messages become input messages. An assistant message that came from the OpenAI adapter
    is sent back as its output items, verbatim: reasoning items with their encrypted content,
    message items and function-call items, in the order of the response (OpenAI reasoning guide:
    "pass back every output item"). Other assistant messages become an assistant message and
    ``function_call`` items. Tool results become ``function_call_output`` items; the Responses API
    has no error flag for them, so a failed result carries :data:`OPENAI_TOOL_ERROR_MARKER`.
    """
    out: list[dict[str, Any]] = []
    for m in messages:
        if isinstance(m, UserMessage):
            out.append({"role": "user", "content": m.text})
        elif isinstance(m, AssistantMessage):
            if m.vendor == "openai" and m.vendor_items:
                items = _replayable_openai_items(m.vendor_items)
                if items:
                    out.extend(items)
                    continue
            if m.text or not m.tool_calls:
                out.append({"role": "assistant", "content": m.text or _EMPTY_ASSISTANT_TEXT})
            for tc in m.tool_calls:
                out.append(
                    {
                        "type": "function_call",
                        "call_id": tc.id,
                        "name": tc.name,
                        "arguments": tc.raw_arguments
                        if tc.raw_arguments is not None and tc.arguments_error
                        else json.dumps(dict(tc.arguments)),
                    }
                )
        elif isinstance(m, ToolResultMessage):
            content = f"{OPENAI_TOOL_ERROR_MARKER}{m.content}" if m.is_error else m.content
            out.append({"type": "function_call_output", "call_id": m.tool_call_id, "output": content})
        else:
            raise TypeError(f"not a message: {m!r}")
    return out


OPENAI_WEB_SEARCH_TOOL: dict[str, Any] = {"type": "web_search"}
"""The built-in web search tool of the Responses API (OpenAI, "Web search" guide, consulted
2026-10-05): the vendor executes the searches inside a response and returns ``web_search_call``
output items; default settings (``search_context_size: medium``)."""

OPENAI_WEB_SEARCH_INCLUDE = "web_search_call.action.sources"
"""Requests the complete list of the addresses consulted by a search action, for the record."""


def openai_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    """Convert tool descriptions to Responses API tools.

    A description with ``vendor_tool == "web_search"`` becomes the vendor's built-in web search
    tool (:data:`OPENAI_WEB_SEARCH_TOOL`); every other one becomes a function tool. ``strict`` is
    false: strict mode requires every property to be required, and optional arguments
    (``read_file``'s ``offset``) would then be rejected.
    """
    out: list[dict[str, Any]] = []
    for t in tools:
        if t.vendor_tool == "web_search":
            out.append(dict(OPENAI_WEB_SEARCH_TOOL))
            continue
        out.append({"type": "function", "name": t.name, "description": t.description, "parameters": dict(t.parameters),
                    "strict": False})
    return out


def _openai_web_search(item: Any) -> dict[str, Any]:
    """One ``web_search_call`` output item as a readable record."""
    action = _get(item, "action")
    out: dict[str, Any] = {"action": str(_get(action, "type") or "search"), "status": _get(item, "status")}
    for key in ("query", "url", "pattern"):
        value = _get(action, key)
        if value:
            out[key] = str(value)
    queries = _get(action, "queries")
    if queries:
        out["queries"] = [str(q) for q in queries]
    sources = _get(action, "sources")
    if sources:
        out["sources"] = [str(_get(s, "url") or s) for s in sources]
    return out


def _decode_arguments(raw: Any) -> tuple[dict[str, Any], str | None, str | None]:
    """Decode a JSON argument string: ``(arguments, raw_arguments, arguments_error)``."""
    if raw is None or raw == "":
        return {}, None, None
    if isinstance(raw, Mapping):
        return dict(raw), None, None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        return {}, str(raw), f"arguments are not valid JSON: {exc}"
    if not isinstance(value, dict):
        return {}, str(raw), f"arguments are JSON of type {type(value).__name__}, not an object"
    return value, None, None


def openai_parse_response(response: Any, *, latency_s: float = 0.0, attempts: int = 1) -> ProviderResponse:
    """Convert a Responses API response to a :class:`ProviderResponse`.

    Output items: the ``output_text`` parts of ``message`` items form ``text`` and their
    ``refusal`` parts ``refusal``; ``function_call`` items become tool calls (the neutral
    identifier is the ``call_id``); the ``summary_text`` parts of ``reasoning`` items become
    ``reasoning``; ``web_search_call`` items (searches that the vendor executed inside the
    response) become ``web_searches`` and are counted in ``usage.web_search_calls``. Every output
    item is kept verbatim in ``vendor_items``. Usage: ``input_tokens``
    (including cached) becomes ``input_tokens``, ``input_tokens_details.cached_tokens``
    ``cached_input_tokens``, ``output_tokens`` (including reasoning) ``output_tokens`` and
    ``output_tokens_details.reasoning_tokens`` ``reasoning_tokens``. The stop reason is
    ``tool_calls`` or ``stop`` for a completed response, else ``<status>:<reason>`` (for example
    ``incomplete:max_output_tokens``). A response with status ``failed`` raises
    :class:`ProviderError`.
    """
    status = str(_get(response, "status") or "completed")
    error = _get(response, "error")
    if status == "failed" or error:
        raise ProviderError(f"OpenAI response failed: {_get(error, 'code')}: {_get(error, 'message')}", attempts=attempts)
    texts: list[str] = []
    refusals: list[str] = []
    reasoning: list[str] = []
    calls: list[ToolCall] = []
    searches: list[dict[str, Any]] = []
    output = list(_get(response, "output") or [])
    for item in output:
        kind = _get(item, "type")
        if kind == "web_search_call":
            searches.append(_openai_web_search(item))
        elif kind == "message":
            for part in _get(item, "content") or []:
                pk = _get(part, "type")
                if pk == "output_text":
                    texts.append(str(_get(part, "text") or ""))
                elif pk == "refusal":
                    refusals.append(str(_get(part, "refusal") or ""))
        elif kind == "function_call":
            args, raw, err = _decode_arguments(_get(item, "arguments"))
            calls.append(
                ToolCall(
                    id=str(_get(item, "call_id") or ""),
                    name=str(_get(item, "name") or ""),
                    arguments=args,
                    raw_arguments=raw,
                    arguments_error=err,
                )
            )
        elif kind == "reasoning":
            for s in _get(item, "summary") or []:
                t = _get(s, "text")
                if t:
                    reasoning.append(str(t))
    u = _get(response, "usage")
    if u is None:
        usage = Usage(reported=False, web_search_calls=len(searches))
    else:
        usage = Usage(
            input_tokens=_int_or_none(_get(u, "input_tokens")) or 0,
            output_tokens=_int_or_none(_get(u, "output_tokens")) or 0,
            cached_input_tokens=_int_or_none(_get(_get(u, "input_tokens_details"), "cached_tokens")),
            reasoning_tokens=_int_or_none(_get(_get(u, "output_tokens_details"), "reasoning_tokens")),
            web_search_calls=len(searches),
        )
    if status == "completed":
        stop = "tool_calls" if calls else "stop"
    else:
        stop = f"{status}:{_get(_get(response, 'incomplete_details'), 'reason') or 'unknown'}"
    return ProviderResponse(
        text="".join(texts),
        tool_calls=tuple(calls),
        usage=usage,
        model=str(_get(response, "model") or ""),
        stop_reason=stop,
        latency_s=latency_s,
        attempts=attempts,
        refusal="".join(refusals) or None,
        reasoning=tuple(reasoning),
        vendor="openai",
        vendor_items=tuple(_plain(i) for i in output),
        web_searches=tuple(searches),
    )


class OpenAIProvider(Provider):
    """Adapter for the OpenAI Responses API with function tools.

    Choice of API: OpenAI recommends the Responses API for new work; its Chat Completions API
    remains supported but, from GPT-5.4 on, rejects function tools together with a reasoning
    effort other than ``none``, carries no reasoning from one turn to the next and returns no
    reasoning summaries (OpenAI, "Migrate to the Responses API" and "Reasoning models" guides,
    consulted 2026-09-28). The adapter uses the Responses API statelessly: ``store`` is false,
    every request carries the system prompt (``instructions``), the complete history and the tool
    descriptions, and the reasoning items of earlier responses are sent back with their encrypted
    content, which the vendor decrypts only in memory. The request recorded by the harness is
    therefore still exactly what the model received; the encrypted reasoning is
    recorded as an opaque string. The raw chain of thought is never returned; with
    ``reasoning.summary`` the vendor returns a readable summary written by a separate summarizer.

    Web search: the tool ``web_search`` is offered as the vendor's built-in web
    search tool. The vendor executes the searches inside a response; the harness executes
    nothing for them. Each search action is returned as a ``web_search_call`` output item, which
    the adapter records (query, address, sources), counts for the fee per call and sends back
    with the other output items in later requests.

    The SDK is imported when the adapter is constructed; the API key is read from the
    environment variable ``api_key_env``, unless the caller passes the key itself as ``api_key``
    (the experiment workers receive it through standard input, so that it is not in their process
    environment). The SDK's own retries are disabled; retries are
    made by :func:`call_with_retries` under ``retry``. A ``client`` object with the SDK's
    ``responses.create`` method may be injected (tests).
    """

    vendor = "openai"

    def __init__(
        self,
        model_id: str,
        *,
        api_key_env: str = "OPENAI_API_KEY",
        api_key: str | None = None,
        retry: RetryPolicy = RetryPolicy(),
        client: Any = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(model_id)
        self.retry = retry
        self._clock = clock
        self._sleep = sleep
        if client is None:
            try:
                import openai  # noqa: PLC0415 - lazy import (optional extra "runner")
            except ImportError as exc:
                raise ProviderConfigError(
                    "the OpenAI SDK is not installed; install the extra: pip install -e aspire[runner]"
                ) from exc
            client = openai.OpenAI(api_key=api_key if api_key else _api_key(api_key_env), max_retries=0)
        self._client = client

    def request_kwargs(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        *,
        max_output_tokens: int,
        reasoning: ReasoningSettings | None = None,
    ) -> dict[str, Any]:
        """The arguments of one ``responses.create`` call."""
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "instructions": system,
            "input": openai_request_input(messages),
            "max_output_tokens": max_output_tokens,
            "store": False,
            "include": ["reasoning.encrypted_content"],
        }
        if tools:
            kwargs["tools"] = openai_tools(tools)
            if any(t.vendor_tool == "web_search" for t in tools):
                kwargs["include"] = [*kwargs["include"], OPENAI_WEB_SEARCH_INCLUDE]
        if reasoning is not None and (reasoning.effort or reasoning.summary):
            r: dict[str, Any] = {}
            if reasoning.effort:
                r["effort"] = reasoning.effort
            if reasoning.summary:
                r["summary"] = reasoning.summary
            kwargs["reasoning"] = r
        return kwargs

    def complete(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        *,
        max_output_tokens: int,
        timeout_s: float,
        reasoning: ReasoningSettings | None = None,
    ) -> ProviderResponse:
        """One Responses API request with retries."""
        kwargs = self.request_kwargs(system, messages, tools, max_output_tokens=max_output_tokens, reasoning=reasoning)
        start = self._clock()
        raw, attempts = call_with_retries(
            lambda remaining: self._client.responses.create(**kwargs, timeout=remaining),
            policy=self.retry,
            timeout_s=timeout_s,
            clock=self._clock,
            sleep=self._sleep,
            what=f"OpenAI request ({self.model_id})",
        )
        return openai_parse_response(raw, latency_s=self._clock() - start, attempts=attempts)


# --------------------------------------------------------------------------------------------
# Anthropic
# --------------------------------------------------------------------------------------------

def anthropic_request_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """Convert the neutral history to Messages API messages.

    Tool results become ``tool_result`` blocks in a user message. Consecutive user-side entries
    (several tool results, or tool results followed by a harness message) are merged into one
    user message, because the Messages API expects user and assistant messages to alternate;
    within it, the ``tool_result`` blocks precede the text blocks. Whitespace-only assistant text
    counts as empty. An assistant message that came from the Anthropic adapter is sent back as
    its content blocks, verbatim: thinking blocks must be passed back unchanged, with their
    signature (Anthropic, "Thinking", preserving thinking blocks).
    """
    out: list[dict[str, Any]] = []

    def _add_user_blocks(blocks: list[dict[str, Any]]) -> None:
        if out and out[-1]["role"] == "user":
            out[-1]["content"].extend(blocks)
        else:
            out.append({"role": "user", "content": blocks})

    for m in messages:
        if isinstance(m, UserMessage):
            _add_user_blocks([{"type": "text", "text": m.text}])
        elif isinstance(m, ToolResultMessage):
            block: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": m.tool_call_id,
                "content": m.content,
            }
            if m.is_error:
                block["is_error"] = True
            _add_user_blocks([block])
        elif isinstance(m, AssistantMessage):
            if m.vendor == "anthropic" and m.vendor_items:
                out.append({"role": "assistant", "content": [dict(b) for b in m.vendor_items]})
                continue
            blocks: list[dict[str, Any]] = []
            if m.text.strip():
                blocks.append({"type": "text", "text": m.text})
            for tc in m.tool_calls:
                blocks.append(
                    {"type": "tool_use", "id": tc.id, "name": tc.name, "input": dict(tc.arguments)}
                )
            if not blocks:
                blocks.append({"type": "text", "text": _EMPTY_ASSISTANT_TEXT})
            out.append({"role": "assistant", "content": blocks})
        else:
            raise TypeError(f"not a message: {m!r}")
    # Within a merged user message, tool_result blocks come before text blocks (the Messages API
    # expects the results of the preceding tool calls first). The sort is stable.
    for entry in out:
        if entry["role"] == "user":
            entry["content"].sort(key=lambda b: 0 if b["type"] == "tool_result" else 1)
    return out


def anthropic_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    """Convert tool descriptions to Messages API tools."""
    return [
        {"name": t.name, "description": t.description, "input_schema": dict(t.parameters)}
        for t in tools
    ]


def anthropic_parse_response(response: Any, *, latency_s: float = 0.0, attempts: int = 1) -> ProviderResponse:
    """Convert a Messages API response to a :class:`ProviderResponse`.

    Text blocks are concatenated; ``tool_use`` blocks become tool calls; the text of ``thinking``
    blocks (a summary of the reasoning with ``display: summarized``, empty with ``omitted``)
    becomes ``reasoning``; ``redacted_thinking`` blocks carry no readable text. Every content
    block is kept verbatim in ``vendor_items``. Usage: ``input_tokens`` of the vendor counts only
    uncached input, so the total input is ``input_tokens + cache_read_input_tokens +
    cache_creation_input_tokens``; ``cache_read_input_tokens`` becomes ``cached_input_tokens``;
    ``output_tokens_details.thinking_tokens`` becomes ``reasoning_tokens`` (``None`` when the
    vendor does not report it).
    """
    text_parts: list[str] = []
    reasoning: list[str] = []
    calls: list[ToolCall] = []
    content = list(_get(response, "content") or [])
    for block in content:
        kind = _get(block, "type")
        if kind == "thinking":
            t = _get(block, "thinking")
            if t:
                reasoning.append(str(t))
        elif kind == "text":
            text_parts.append(str(_get(block, "text") or ""))
        elif kind == "tool_use":
            args, raw, err = _decode_arguments(_get(block, "input"))
            calls.append(
                ToolCall(
                    id=str(_get(block, "id") or ""),
                    name=str(_get(block, "name") or ""),
                    arguments=args,
                    raw_arguments=raw,
                    arguments_error=err,
                )
            )
    u = _get(response, "usage")
    if u is None:
        usage = Usage(reported=False)
    else:
        uncached = _int_or_none(_get(u, "input_tokens")) or 0
        cache_read = _int_or_none(_get(u, "cache_read_input_tokens"))
        cache_write = _int_or_none(_get(u, "cache_creation_input_tokens"))
        usage = Usage(
            input_tokens=uncached + (cache_read or 0) + (cache_write or 0),
            output_tokens=_int_or_none(_get(u, "output_tokens")) or 0,
            cached_input_tokens=cache_read,
            reasoning_tokens=_int_or_none(_get(_get(u, "output_tokens_details"), "thinking_tokens")),
        )
    return ProviderResponse(
        text="".join(text_parts),
        tool_calls=tuple(calls),
        usage=usage,
        model=str(_get(response, "model") or ""),
        stop_reason=str(_get(response, "stop_reason") or ""),
        latency_s=latency_s,
        attempts=attempts,
        reasoning=tuple(reasoning),
        vendor="anthropic",
        vendor_items=tuple(_plain(b) for b in content),
    )


class AnthropicProvider(Provider):
    """Adapter for the Anthropic Messages API with tools.

    The SDK is imported when the adapter is constructed; the API key is read from the
    environment variable ``api_key_env``, unless the caller passes the key itself as ``api_key``
    (the experiment workers receive it through standard input, so that it is not in their process
    environment). The SDK's own retries are disabled; retries are
    made by :func:`call_with_retries` under ``retry``. A ``client`` object with the SDK's
    ``messages.create`` method may be injected (tests).
    """

    vendor = "anthropic"

    def __init__(
        self,
        model_id: str,
        *,
        api_key_env: str = "ANTHROPIC_API_KEY",
        api_key: str | None = None,
        retry: RetryPolicy = RetryPolicy(),
        client: Any = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(model_id)
        self.retry = retry
        self._clock = clock
        self._sleep = sleep
        if client is None:
            try:
                import anthropic  # noqa: PLC0415 - lazy import (optional extra "runner")
            except ImportError as exc:
                raise ProviderConfigError(
                    "the Anthropic SDK is not installed; install the extra: pip install -e aspire[runner]"
                ) from exc
            client = anthropic.Anthropic(api_key=api_key if api_key else _api_key(api_key_env), max_retries=0)
        self._client = client

    def request_kwargs(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        *,
        max_output_tokens: int,
        reasoning: ReasoningSettings | None = None,
    ) -> dict[str, Any]:
        """The arguments of one ``messages.create`` call.

        Reasoning (Anthropic, "Thinking", consulted 2026-09-28): effort ``none`` disables
        thinking; otherwise thinking is adaptive (the model decides when and how much to think,
        also between tool calls), ``display`` is ``summarized`` when a summary is requested and
        ``omitted`` otherwise, and the effort is ``output_config.effort`` (``low``, ``medium``,
        ``high``, ``xhigh``, ``max``). Adaptive thinking requires Claude 4.6 or later.
        """
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "system": system,
            "messages": anthropic_request_messages(messages),
            "max_tokens": max_output_tokens,
        }
        if tools:
            kwargs["tools"] = anthropic_tools(tools)
        if reasoning is not None and (reasoning.effort or reasoning.summary):
            if reasoning.effort == "none":
                kwargs["thinking"] = {"type": "disabled"}
            else:
                kwargs["thinking"] = {"type": "adaptive", "display": "summarized" if reasoning.summary else "omitted"}
                if reasoning.effort:
                    kwargs["output_config"] = {"effort": reasoning.effort}
        return kwargs

    def complete(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        *,
        max_output_tokens: int,
        timeout_s: float,
        reasoning: ReasoningSettings | None = None,
    ) -> ProviderResponse:
        """One Messages API request with retries."""
        kwargs = self.request_kwargs(system, messages, tools, max_output_tokens=max_output_tokens, reasoning=reasoning)
        start = self._clock()
        raw, attempts = call_with_retries(
            lambda remaining: self._client.messages.create(**kwargs, timeout=remaining),
            policy=self.retry,
            timeout_s=timeout_s,
            clock=self._clock,
            sleep=self._sleep,
            what=f"Anthropic request ({self.model_id})",
        )
        return anthropic_parse_response(raw, latency_s=self._clock() - start, attempts=attempts)


# --------------------------------------------------------------------------------------------
# Pinned model identifiers and the factory
# --------------------------------------------------------------------------------------------

_OPENAI_PREFIX = re.compile(r"^(gpt-|o[0-9]+(-|$))")
_OPENAI_PINNED = re.compile(r"^(?P<base>[a-z0-9][a-z0-9.\-]*?)-(?P<date>\d{4}-\d{2}-\d{2})$")


def vendor_of(model_id: str) -> str:
    """Vendor of a model identifier: ``openai`` (``gpt-*``, ``o<digit>*``) or ``anthropic`` (``claude-*``).

    The harness supports the plain model APIs of OpenAI and Anthropic. Raises
    :class:`ModelIdError` for an identifier of neither vendor.
    """
    if _OPENAI_PREFIX.match(model_id):
        return "openai"
    if model_id.startswith("claude-"):
        return "anthropic"
    raise ModelIdError(f"model identifier {model_id!r} belongs to no supported vendor (OpenAI, Anthropic)")


def load_model_allowlist(path: str | Path | None = None) -> dict[str, frozenset[str]]:
    """Read the lists of accepted identifiers without a date from ``aspire/configs/models.yaml``.

    Only pinned identifiers are accepted. Returns ``{"anthropic": ids,
    "openai": ids}``: the pinned Anthropic identifiers and the OpenAI identifiers for which the
    vendor publishes no dated snapshot (``openai.undated``).
    """
    p = Path(path) if path is not None else config_path("models.yaml")
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ModelIdError(f"model allowlist {p}: cannot be read ({exc})") from exc
    pinned = ((data.get("anthropic") or {}).get("pinned")) or []
    if not isinstance(pinned, list) or not all(isinstance(x, str) for x in pinned):
        raise ModelIdError(f"model allowlist {p}: 'anthropic.pinned' must be a list of strings")
    undated = ((data.get("openai") or {}).get("undated")) or []
    if not isinstance(undated, list) or not all(isinstance(x, str) for x in undated):
        raise ModelIdError(f"model allowlist {p}: 'openai.undated' must be a list of strings")
    return {"anthropic": frozenset(pinned), "openai": frozenset(undated)}


def default_model_id(path: str | Path | None = None) -> str:
    """The default model, ``default_model`` of ``aspire/configs/models.yaml``: the model of ``aspire session`` when none is named. Raises :class:`ModelIdError`
    when the file names none."""
    p = Path(path) if path is not None else config_path("models.yaml")
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ModelIdError(f"model list {p}: cannot be read ({exc})") from exc
    model = data.get("default_model")
    if not isinstance(model, str) or not model.strip():
        raise ModelIdError(f"model list {p}: 'default_model' is missing; name a model with --model")
    return model.strip()


def check_pinned_model_id(model_id: str, *, allowlist_path: str | Path | None = None) -> str:
    """Accept a model identifier and return its vendor; reject a floating alias.

    A model is named by its dated
    snapshot identifier where the vendor publishes one. OpenAI identifiers must end with a valid
    snapshot date ``YYYY-MM-DD`` (``gpt-5.5-2026-04-23``); ``gpt-5`` or ``gpt-5.5`` are rejected.
    An identifier listed under ``openai.undated`` in ``aspire/configs/models.yaml`` is accepted
    without a date: a model for which the vendor publishes no dated snapshot, so that the
    identifier is the only one there is (``gpt-6.1-sol``). Results obtained with such an
    identifier are reported with the dates of the runs, because the harness cannot show that the
    model behind it stayed the same. Anthropic
    identifiers must be listed in ``aspire/configs/models.yaml``. An identifier containing
    ``latest`` is always rejected. Raises :class:`ModelIdError`.
    """
    if not isinstance(model_id, str) or not model_id.strip() or model_id != model_id.strip():
        raise ModelIdError(f"model identifier {model_id!r} is empty or has surrounding whitespace")
    if "latest" in model_id.lower():
        raise ModelIdError(f"model identifier {model_id!r} is a floating alias; use a pinned snapshot")
    vendor = vendor_of(model_id)
    if vendor == "openai":
        m = _OPENAI_PINNED.match(model_id)
        if m is None:
            if model_id in load_model_allowlist(allowlist_path)["openai"]:
                return vendor
            raise ModelIdError(
                f"model identifier {model_id!r} is a floating alias: an OpenAI snapshot identifier "
                "ends with its date YYYY-MM-DD, for example gpt-5.5-2026-04-23 (identifiers of models without a "
                "dated snapshot are listed under openai.undated in aspire/configs/models.yaml)"
            )
        try:
            _dt.date.fromisoformat(m.group("date"))
        except ValueError:
            raise ModelIdError(
                f"model identifier {model_id!r}: {m.group('date')} is not a valid snapshot date"
            ) from None
        return vendor
    allowed = load_model_allowlist(allowlist_path)["anthropic"]
    if model_id not in allowed:
        listed = ", ".join(sorted(allowed)) or "none"
        raise ModelIdError(
            f"Anthropic model identifier {model_id!r} is not in the allowlist of pinned snapshots "
            f"(aspire/configs/models.yaml; listed: {listed})"
        )
    return vendor


def make_provider(model_id: str, *, allowlist_path: str | Path | None = None, **kwargs: Any) -> Provider:
    """Construct the adapter for a pinned model identifier.

    Floating aliases are rejected by :func:`check_pinned_model_id` before any SDK is imported.
    Keyword arguments are passed to the adapter (for example ``retry``, or ``api_key`` to give the
    key directly instead of reading it from the environment).
    """
    vendor = check_pinned_model_id(model_id, allowlist_path=allowlist_path)
    if vendor == "openai":
        return OpenAIProvider(model_id, **kwargs)
    return AnthropicProvider(model_id, **kwargs)
