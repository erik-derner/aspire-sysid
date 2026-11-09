"""The ``ask_user`` tool of interactive operation.

During identification, the agent may ask a specific question when the answer would affect a
modeling choice. The ``ask_user`` tool suspends execution until the user answers or declines.
The response that requests this tool counts as one turn; waiting for the user does not consume
elapsed execution time. The harness records the question and the answer verbatim. A declined
question returns 'No further information is available'; the agent then states any necessary
assumptions and their implications.

Implementation:

* The tool is registered in the tool registry of every round and analysis exchange of an
  interactive session (:func:`make_ask_user_tool`); it is never offered in autonomous operation
  (the system prompt and the brief describe it only in interactive operation).
* **Turn.** The response that requests the tool is one turn of the turn loop;
  the tool execution itself is not a turn.
* **Suspension.** The handler calls the :class:`~aspire_sysid.session.channel.UserChannel`
  inside ``ctx.clock.paused``: the execution clock of the session stops while the user reads
  and answers, so the waiting time counts neither toward the round's nor the session's elapsed
  execution time; it is recorded separately as user waiting time in the event
  ``user_answer`` and in the trackers' ``waiting_s``.
* **Record.** The event ``user_question`` holds the question and the decision it affects,
  verbatim as the agent wrote them; ``user_answer`` holds the answer verbatim, whether it was
  declined, and the waiting time.
* **Declined question.** An answer of ``None`` (or only white space) is a declined question; the
  tool result is the declined-question message of the harness, verbatim.
* **Answer.** The tool result is ``"The user answered: "`` followed by the verbatim answer.
* **Helper agents.** The tool is not offered to helper agents (``helper_allowed=False``): only the
  main agent addresses the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ..agent.tools import Tool, ToolContext, ToolOutcome
from ..brief import messages as msg
from .channel import UserChannel

__all__ = ["ASK_USER", "ANSWER_PREFIX", "QuestionRecord", "make_ask_user_tool"]

ASK_USER = "ask_user"
"""Name of the tool."""

ANSWER_PREFIX = "The user answered: "
"""Start of the tool result of an answered question; the verbatim answer follows."""

DESCRIPTION = (
    "Ask the user a specific question when the answer would change a modeling choice. Execution is "
    "suspended until the user answers or declines; the waiting time does not count as execution time. "
    "State in 'decision' which modeling choice the answer affects. A declined question returns "
    "\"No further information is available\"; then state any necessary assumption and its implications."
)
"""Description of ``ask_user`` sent with every request of interactive operation."""

PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "description": "the specific question to the user"},
        "decision": {"type": "string", "description": "the modeling choice that the answer affects"},
    },
    "required": ["question"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class QuestionRecord:
    """One question of the agent and the user's reply, verbatim."""

    agent: str
    question: str
    decision: str | None
    answer: str | None
    declined: bool
    waiting_s: float
    call_elapsed_s: float

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the session record."""
        return {
            "agent": self.agent,
            "question": self.question,
            "decision": self.decision,
            "answer": self.answer,
            "declined": self.declined,
            "waiting_s": self.waiting_s,
            "execution_time_during_call_s": self.call_elapsed_s,
        }


def make_ask_user_tool(channel: UserChannel, on_record: Callable[[QuestionRecord], None] | None = None) -> Tool:
    """The ``ask_user`` tool bound to ``channel`` (module docstring).

    ``on_record`` receives every :class:`QuestionRecord` (the session keeps them in the round
    record).
    """

    def handler(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
        """Ask the user with the execution clock paused; return the answer or the declined-question
        message."""
        question = args.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("'question' must be a non-empty text")
        decision = args.get("decision")
        if decision is not None and not isinstance(decision, str):
            raise ValueError("'decision' must be a text")
        ctx.emit("user_question", question=question, decision=decision)
        clock = ctx.clock
        waiting_before = clock.waiting_s()
        elapsed_before = clock.elapsed()
        if clock.is_paused:  # never expected: the loop runs with a running clock
            answer = channel.ask(question, decision)
        else:
            with clock.paused():
                answer = channel.ask(question, decision)
        waiting = clock.waiting_s() - waiting_before
        declined = answer is None or not str(answer).strip()
        rec = QuestionRecord(
            agent=ctx.agent,
            question=question,
            decision=decision,
            answer=None if answer is None else str(answer),
            declined=declined,
            waiting_s=waiting,
            call_elapsed_s=clock.elapsed() - elapsed_before,
        )
        ctx.emit("user_answer", answer=rec.answer, declined=declined, waiting_s=waiting)
        if on_record is not None:
            on_record(rec)
        if declined:
            return ToolOutcome(msg.render_declined_question(), details={"declined": True, "waiting_s": waiting})
        return ToolOutcome(ANSWER_PREFIX + str(answer), details={"declined": False, "waiting_s": waiting})

    return Tool(ASK_USER, DESCRIPTION, PARAMETERS, handler, helper_allowed=False)
