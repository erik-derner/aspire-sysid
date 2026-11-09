"""Agent execution: provider adapters, turn loop, tools, budget and tool configurations.

Implements the execution of a round (turns, completion message, continuation message, correction
attempt, budget, reminder, termination), the tools (the tool configuration, helper
agents, token accounting, shell limit), and the cost computation from a dated price schedule.
The modules are ``providers`` (the provider adapters), ``prices`` (the price schedule) and

* ``loop``: :func:`run_round` (one identification round) and :func:`run_analysis_exchange`;
* ``budget``: :class:`ExecutionClock` (with pause and resume for user waiting time) and
  :class:`BudgetTracker` (one per round, shared by the correction attempt and helper agents);
* ``tools``: the tool registry and the built-in tools; ``policy``: the command filters and the
  shell environment; ``shell``: commands with process-tree termination;
* ``config``: the tool configuration (``aspire/configs/tools.yaml``): one configuration with every tool;
* ``events``: the event sink interface for the transcript;
* ``probe``: the installed packages of the run environment, listed in the system prompt.
"""

from .budget import BudgetTracker, ExecutionClock, LimitHit, Remaining, format_remaining
from .config import ToolConfig, ToolConfigError, load_tool_config
from .events import EVENT_KINDS, Event, EventSink, FanoutSink, MemorySink, NullSink
from .loop import (
    DONE,
    OUTCOMES,
    CandidateFiles,
    RoundLabels,
    RoundResult,
    candidate_files,
    is_completion_message,
    prepare_workspace,
    run_analysis_exchange,
    run_round,
)
from .probe import EnvironmentProbe, probe_environment
from .tools import Tool, ToolContext, ToolOutcome, ToolRegistry, WebBackends, build_registry

__all__ = [
    "BudgetTracker",
    "CandidateFiles",
    "DONE",
    "EVENT_KINDS",
    "EnvironmentProbe",
    "Event",
    "EventSink",
    "ExecutionClock",
    "FanoutSink",
    "LimitHit",
    "MemorySink",
    "NullSink",
    "OUTCOMES",
    "Remaining",
    "RoundLabels",
    "RoundResult",
    "Tool",
    "ToolConfig",
    "ToolConfigError",
    "ToolContext",
    "ToolOutcome",
    "ToolRegistry",
    "WebBackends",
    "build_registry",
    "candidate_files",
    "format_remaining",
    "is_completion_message",
    "load_tool_config",
    "prepare_workspace",
    "probe_environment",
    "run_analysis_exchange",
    "run_round",
]
