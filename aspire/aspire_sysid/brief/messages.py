"""The execution messages of the harness.

The harness sends these messages to the agent. Text in braces is replaced by the corresponding
information from the current session record. Each message states the event and any required
action, using only information the agent is permitted to receive.

:data:`TEMPLATES` holds the nine messages with their fixed wording, including the placeholders
in braces. Each
``render_*`` function replaces the placeholders of one message, in their order of appearance,
by the texts given by the caller (:func:`fill`). The turn loop uses
continuation, budget reminder, check failure and budget termination; the session layer
uses round completion, new identification round, analysis request, declined question and
session completion. The caller is responsible for passing only information the agent may
receive; these functions insert the texts unchanged.

The limit texts are produced by :func:`aspire_sysid.agent.budget.format_remaining`, for example
``"12 turns"``, ``"1834 s of execution time"`` and ``"2.41 USD"``.
"""

from __future__ import annotations

import re
from typing import Sequence

__all__ = [
    "MESSAGE_IDS",
    "TEMPLATES",
    "placeholders",
    "fill",
    "render_continuation",
    "render_budget_reminder",
    "render_check_failure",
    "render_budget_termination",
    "render_round_completion",
    "render_new_round",
    "render_analysis_request",
    "render_declined_question",
    "render_session_completion",
]

TEMPLATES: dict[str, str] = {
    "continuation": (
        "Your reply contained no tool request and no DONE. Continue the identification, or send "
        "DONE when your candidate files are complete and checked. Remaining limits: {turns}, "
        "{execution time}, {cost}."
    ),
    "budget_reminder": (
        "{used} of the {turn or cost} allowance has been consumed, and no candidate file exists. "
        "Write complete candidate files in {folder} within the remaining allowance. Your remaining "
        "limits are {turns}, {execution time}, and {cost}."
    ),
    "check_failure": (
        "No candidate passed the file and expression checks. Reasons: {candidate labels and "
        "errors, with references to the published rules}. You may correct the files and send DONE "
        "once more within the remaining budget: {limits}."
    ),
    "budget_termination": (
        "The round ended because the {budget type} limit was reached. The harness retained "
        "{number} complete candidate files and recorded {number} incomplete files. Complete "
        "candidates will be checked and evaluated. This message does not request further work."
    ),
    "round_completion": (
        "Round {identifier} is complete. The evaluation report is available to the user. Your "
        "permitted results are {file and expression checks, training and validation errors, "
        "authorized constraint assessments, and diagnostics}. No test results or reference "
        "comparisons are included."
    ),
    "new_round": (
        "The user requests a new identification round. Previous pool: {identifier}. Permitted "
        "results: {results}. User feedback: {verbatim text}. Effective task changes: {changes and "
        "sources}. Produce a new pool version, preserving links to any revised candidates. This "
        "round is {test-informed or not test-informed}. Its limits are {limits}; the remaining "
        "session allowance is {allowance}."
    ),
    "analysis_request": (
        "The user requests an explanation or analysis: {verbatim request}. Answer using your "
        "permitted information and tools. Do not start a new identification round unless the user "
        "requests new or revised candidates. Analysis limits: {limits}. Remaining session "
        "allowance: {allowance}."
    ),
    "declined_question": (
        "No further information is available. Continue using the available evidence. If the "
        "decision requires an assumption, state the assumption and explain how it limits the "
        "result."
    ),
    "session_completion": (
        "The session ended because {user request or session limit}. Completed pool versions: "
        "{identifiers}. Remaining unfinished work: {description}. Resource use: {turns, tokens, "
        "execution time, and cost}. The recorded results remain available for human assessment."
    ),
}
"""The nine execution messages, with their placeholders."""

MESSAGE_IDS: tuple[str, ...] = tuple(TEMPLATES)
"""Identifiers of the messages, in the order of :data:`TEMPLATES`."""

_PLACEHOLDER = re.compile(r"\{[^{}]*\}")


def placeholders(message_id: str) -> list[str]:
    """The placeholders of a message in order of appearance, without braces."""
    return [m.group(0)[1:-1] for m in _PLACEHOLDER.finditer(TEMPLATES[message_id])]


def fill(message_id: str, values: Sequence[str]) -> str:
    """Replace the placeholders of a message, in order of appearance, by ``values``.

    Raises :class:`ValueError` when the number of values differs from the number of
    placeholders. The values are inserted unchanged.
    """
    template = TEMPLATES[message_id]
    slots = list(_PLACEHOLDER.finditer(template))
    if len(values) != len(slots):
        raise ValueError(
            f"message {message_id!r} has {len(slots)} placeholders "
            f"({', '.join(placeholders(message_id))}), got {len(values)} values"
        )
    out: list[str] = []
    pos = 0
    for m, v in zip(slots, values):
        out.append(template[pos : m.start()])
        out.append(str(v))
        pos = m.end()
    out.append(template[pos:])
    return "".join(out)


def render_continuation(turns: str, execution_time: str, cost: str) -> str:
    """Continuation message for a text-only reply without ``DONE`` (Appendix C)."""
    return fill("continuation", [turns, execution_time, cost])


def render_budget_reminder(used: str, turn_or_cost: str, folder: str, turns: str, execution_time: str, cost: str) -> str:
    """Budget reminder at 80 % of the turn or cost limit without a candidate file (App. C).

    ``used`` is the consumed part, for example ``"80 % (48 turns)"``; ``turn_or_cost`` is
    ``"turn"`` or ``"cost"``; ``folder`` is the model folder, ``"models/"``.
    """
    return fill("budget_reminder", [used, turn_or_cost, folder, turns, execution_time, cost])


def render_check_failure(reasons: str, limits: str) -> str:
    """Message after ``DONE`` when no candidate passed the checks (Appendix C).

    ``reasons`` lists the candidate labels and errors with the rule identifiers; ``limits`` is
    the remaining allowance of the round.
    """
    return fill("check_failure", [reasons, limits])


def render_budget_termination(budget_type: str, complete: int, incomplete: int) -> str:
    """Message recorded when a budget limit ends the round (Appendix C).

    ``budget_type`` is ``"turn"``, ``"execution-time"`` or ``"cost"`` (with the prefix
    ``"session "`` when the session limit was reached).
    """
    return fill("budget_termination", [budget_type, str(complete), str(incomplete)])


def render_round_completion(identifier: str, permitted_results: str) -> str:
    """Message at the end of a round in interactive operation (Appendix C)."""
    return fill("round_completion", [identifier, permitted_results])


def render_new_round(
    previous_pool: str,
    results: str,
    feedback: str,
    changes: str,
    test_informed: bool,
    limits: str,
    allowance: str,
) -> str:
    """Message that starts a new identification round (Appendix C).

    ``test_informed`` selects "test-informed" or "not test-informed".
    """
    label = "test-informed" if test_informed else "not test-informed"
    return fill("new_round", [previous_pool, results, feedback, changes, label, limits, allowance])


def render_analysis_request(request: str, limits: str, allowance: str) -> str:
    """Message that starts an analysis exchange (Appendix C)."""
    return fill("analysis_request", [request, limits, allowance])


def render_declined_question() -> str:
    """Result of an ``ask_user`` request that the user declined (Appendix C)."""
    return fill("declined_question", [])


def render_session_completion(reason: str, identifiers: str, unfinished: str, resource_use: str) -> str:
    """Message recorded at the end of a session (Appendix C)."""
    return fill("session_completion", [reason, identifiers, unfinished, resource_use])
