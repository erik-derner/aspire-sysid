"""Sessions: rounds, questions to the user, analysis exchanges and pool versions.

Interactive operation: ``ask_user``, permitted results, analysis exchanges, versioned pools with
predecessor links, the "test-informed" label and the session end, with the session budget and
the separately recorded user waiting time.

* :mod:`.session`: :class:`Session` (the whole interactive session), :class:`SessionTracker`,
  the round, exchange and session records;
* :mod:`.ask_user`: the ``ask_user`` tool;
* :mod:`.permitted`: the permitted-results filter (whitelist over the evaluation) and the
  leak screen;
* :mod:`.changes`: the user's task changes and their application;
* :mod:`.channel`: the user channel (terminal and scripted);
* :mod:`.cli`: the subcommand ``aspire session``.
"""

from .ask_user import ANSWER_PREFIX, ASK_USER, QuestionRecord, make_ask_user_tool
from .changes import CHANGE_KINDS, TaskChange, TaskChangeError, apply_changes, describe_changes
from .channel import ACTION_KINDS, ChoiceContext, ScriptedChannel, TerminalChannel, UserAction, UserChannel, parse_change_line
from .permitted import (
    VISIBLE_GROUPS,
    permitted_results,
    permitted_summary,
    render_permitted_blocks,
    render_permitted_text,
    screen_blocks,
)
from .session import (
    SESSION_EVENT_KINDS,
    TERMINATION_REASONS,
    ExchangeRecord,
    RoundRecord,
    Session,
    SessionResult,
    SessionTracker,
    WITHHELD,
    check_separation,
    limit_phrase,
    limits_text,
    quote_verbatim,
    sealed_result_kinds,
)

__all__ = [
    "ACTION_KINDS",
    "ANSWER_PREFIX",
    "ASK_USER",
    "CHANGE_KINDS",
    "ChoiceContext",
    "ExchangeRecord",
    "QuestionRecord",
    "RoundRecord",
    "SESSION_EVENT_KINDS",
    "ScriptedChannel",
    "Session",
    "SessionResult",
    "SessionTracker",
    "TERMINATION_REASONS",
    "TaskChange",
    "TaskChangeError",
    "TerminalChannel",
    "UserAction",
    "UserChannel",
    "VISIBLE_GROUPS",
    "apply_changes",
    "describe_changes",
    "WITHHELD",
    "check_separation",
    "limit_phrase",
    "limits_text",
    "quote_verbatim",
    "sealed_result_kinds",
    "make_ask_user_tool",
    "parse_change_line",
    "permitted_results",
    "permitted_summary",
    "render_permitted_blocks",
    "render_permitted_text",
    "screen_blocks",
]
