"""Execution clock and budget tracker of an identification round.

A **round** is one attempt to produce or revise a pool within stated limits on turns, elapsed
execution time and monetary cost; these limits are the **budget**. This module
provides

* :class:`ExecutionClock`: the elapsed execution time of a session, measured on a monotonic
  clock, with :meth:`ExecutionClock.pause` and :meth:`ExecutionClock.resume` so that the time
  in which the harness waits for the user (the ``ask_user`` tool of interactive operation) is
  not counted as execution time and is recorded separately;
* :class:`BudgetTracker`: the turns, token usage, cost and elapsed execution time of one scope
  (a session, a round, or a helper agent), checked against its :class:`~aspire_sysid.task.schema.Limits`.
  Trackers form a chain: a charge to a helper's tracker is also a charge to its round's tracker
  and, when present, to the session's tracker, at the moment it occurs ("live" accounting), and a limit of any tracker in the chain stops the work of every tracker below
  it. The correction attempt after a failed completion check uses the same round tracker
  ("within the remaining budget").

Elapsed time. All trackers of a session read the same :class:`ExecutionClock`; each measures
the execution time since its own start. Helper agents run synchronously inside a tool call of
the main agent, so the time of a helper is counted once, in the helper's tracker and in the
round's tracker over the same interval ("Concurrent activity counts once in
elapsed time").

Limit test. A limit is reached when the count equals or exceeds it: ``turns >= limits.turns``,
``elapsed_s >= limits.seconds`` or ``cost_usd >= limits.usd``. The harness tests the limits
before every language-model request and every tool execution; the response that pushes the
cost or time past a limit has already been paid for, and the difference is recorded as the
excess of the round ("any unavoidable excess is recorded").
"""

from __future__ import annotations

import contextlib
import math
import time
from dataclasses import dataclass
from typing import Callable, Iterator

from ..task.schema import Limits
from .providers import Usage

__all__ = [
    "LIMIT_KINDS",
    "ExecutionClock",
    "LimitHit",
    "Remaining",
    "BudgetTracker",
    "format_turns",
    "format_seconds",
    "format_usd",
    "format_remaining",
]

LIMIT_KINDS: tuple[str, ...] = ("turns", "time", "cost")
"""The three limit kinds of a budget, in the order in which they are tested."""


class ExecutionClock:
    """Elapsed execution time with pauses for user waiting time.

    ``monotonic`` is the time source in seconds (default :func:`time.monotonic`); tests inject
    a fake clock. :meth:`elapsed` is the time since construction minus the paused time.
    Pauses do not nest: :meth:`pause` while paused and :meth:`resume` while running raise
    :class:`RuntimeError`.
    """

    def __init__(self, monotonic: Callable[[], float] = time.monotonic) -> None:
        self._now = monotonic
        self._origin = monotonic()
        self._paused_total = 0.0
        self._paused_at: float | None = None

    def now(self) -> float:
        """The raw reading of the time source (seconds). """
        return self._now()

    @property
    def is_paused(self) -> bool:
        """True while the clock is paused (the harness waits for the user). """
        return self._paused_at is not None

    def waiting_s(self) -> float:
        """Total paused time in seconds, including a pause in progress (user waiting time)."""
        extra = (self._now() - self._paused_at) if self._paused_at is not None else 0.0
        return self._paused_total + extra

    def elapsed(self) -> float:
        """Elapsed execution time in seconds: time since construction minus paused time. """
        return (self._now() - self._origin) - self.waiting_s()

    def pause(self) -> None:
        """Stop counting execution time, for example while the user answers ``ask_user``."""
        if self._paused_at is not None:
            raise RuntimeError("the execution clock is already paused")
        self._paused_at = self._now()

    def resume(self) -> None:
        """Resume counting execution time after :meth:`pause`."""
        if self._paused_at is None:
            raise RuntimeError("the execution clock is not paused")
        self._paused_total += self._now() - self._paused_at
        self._paused_at = None

    @contextlib.contextmanager
    def paused(self) -> Iterator[None]:
        """Context manager: the enclosed waiting time is excluded from execution time."""
        self.pause()
        try:
            yield
        finally:
            self.resume()


@dataclass(frozen=True)
class LimitHit:
    """A reached limit: its kind (``turns``, ``time`` or ``cost``) and the scope of the tracker
    that reached it (``session``, ``round`` or ``helper-<n>``). """

    kind: str
    scope: str


@dataclass(frozen=True)
class Remaining:
    """Remaining allowance: turns, execution seconds and USD, each at least zero."""

    turns: int
    seconds: float
    usd: float


class BudgetTracker:
    """Turns, tokens, cost and elapsed execution time of one scope, against its limits.

    One budget per round; the first limit reached ends the round; the correction attempt runs
    within the remaining budget. Helper turns and costs count toward the round totals, and helpers
    receive limits within the main agent's remaining allowance. A session tracker keeps the session totals.
    ``parent`` is the tracker of the enclosing scope; every charge is propagated to it.
    """

    def __init__(
        self,
        limits: Limits,
        clock: ExecutionClock,
        *,
        scope: str = "round",
        parent: "BudgetTracker | None" = None,
    ) -> None:
        if limits.turns < 0 or not (limits.seconds >= 0) or not (limits.usd >= 0):
            raise ValueError(f"limits must be non-negative, got {limits!r}")
        self.limits = limits
        self.clock = clock
        self.scope = scope
        self.parent = parent
        self._start_elapsed = clock.elapsed()
        self._start_waiting = clock.waiting_s()
        self.turns = 0
        self.usage = Usage()
        self.cost_usd = 0.0
        self.estimated_turns = 0
        self._frozen: tuple[float, float] | None = None

    # -- measurements --------------------------------------------------------------------

    @property
    def elapsed_s(self) -> float:
        """Execution time since this tracker was created, or until :meth:`freeze`, in seconds."""
        if self._frozen is not None:
            return self._frozen[0]
        return self.clock.elapsed() - self._start_elapsed

    @property
    def waiting_s(self) -> float:
        """User waiting time since this tracker was created, or until :meth:`freeze`, in seconds."""
        if self._frozen is not None:
            return self._frozen[1]
        return self.clock.waiting_s() - self._start_waiting

    @property
    def frozen(self) -> bool:
        """True after :meth:`freeze`."""
        return self._frozen is not None

    def freeze(self) -> None:
        """Fix the elapsed and waiting times at their current values.

        Called when the agent's work in the scope has stopped, so that the harness's own work
        afterwards (final checks, evaluation) is not counted as the round's execution time or
        excess. Further charges are refused.
        """
        if self._frozen is None:
            self._frozen = (self.clock.elapsed() - self._start_elapsed, self.clock.waiting_s() - self._start_waiting)

    def chain(self) -> list["BudgetTracker"]:
        """This tracker followed by its enclosing trackers (helper, round, session). """
        out: list[BudgetTracker] = []
        t: BudgetTracker | None = self
        while t is not None:
            out.append(t)
            t = t.parent
        return out

    # -- charging ------------------------------------------------------------------------

    def charge_turn(self, usage: Usage, cost_usd: float, *, estimated: bool = False) -> None:
        """Count one completed language-model response with its usage and cost.

        The charge is applied to this tracker and to every enclosing tracker. ``estimated`` marks
        a response whose usage was not reported by the vendor and was estimated by the harness.
        """
        if self._frozen is not None:
            raise RuntimeError(f"the {self.scope} tracker is frozen; no further turns can be charged")
        if not math.isfinite(cost_usd) or cost_usd < 0:
            raise ValueError(f"cost must be finite and non-negative, got {cost_usd!r}")
        for t in self.chain():
            t.turns += 1
            t.usage = t.usage + usage
            t.cost_usd += cost_usd
            if estimated:
                t.estimated_turns += 1

    # -- limits --------------------------------------------------------------------------

    def own_limit_reached(self) -> str | None:
        """The kind of this tracker's own limit that is reached, or ``None``. """
        if self.turns >= self.limits.turns:
            return "turns"
        if self.elapsed_s >= self.limits.seconds:
            return "time"
        if self.cost_usd >= self.limits.usd:
            return "cost"
        return None

    def limit_reached(self) -> LimitHit | None:
        """The first reached limit in the chain, tested from the outermost scope inwards.

 The outermost scope is tested first, so that a helper that
        exhausts the round's allowance reports the round's limit.
        """
        for t in reversed(self.chain()):
            kind = t.own_limit_reached()
            if kind is not None:
                return LimitHit(kind=kind, scope=t.scope)
        return None

    def remaining(self) -> Remaining:
        """The smallest remaining allowance over the chain, each part at least zero. """
        turns = min(t.limits.turns - t.turns for t in self.chain())
        seconds = min(t.limits.seconds - t.elapsed_s for t in self.chain())
        usd = min(t.limits.usd - t.cost_usd for t in self.chain())
        return Remaining(turns=max(0, turns), seconds=max(0.0, seconds), usd=max(0.0, usd))

    def fraction_used(self, kind: str) -> float:
        """Used fraction of this tracker's own ``turns`` or ``cost`` limit (reminder at 80 %)."""
        if kind == "turns":
            return self.turns / self.limits.turns if self.limits.turns > 0 else math.inf
        if kind == "cost":
            return self.cost_usd / self.limits.usd if self.limits.usd > 0 else math.inf
        raise ValueError(f"fraction_used is defined for 'turns' and 'cost', not {kind!r}")

    def excess(self) -> dict[str, float]:
        """Amounts by which this tracker's totals exceed its own limits.

        Keys ``turns``, ``seconds`` and ``usd``; zero when the total is within its limit.
        """
        return {
            "turns": float(max(0, self.turns - self.limits.turns)),
            "seconds": max(0.0, self.elapsed_s - self.limits.seconds),
            "usd": max(0.0, self.cost_usd - self.limits.usd),
        }

    def totals(self) -> dict[str, object]:
        """JSON-serializable totals of this tracker for the record."""
        return {
            "scope": self.scope,
            "turns": self.turns,
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "cost_usd": self.cost_usd,
            "elapsed_s": self.elapsed_s,
            "waiting_s": self.waiting_s,
            "estimated_turns": self.estimated_turns,
            "limits": {"turns": self.limits.turns, "seconds": self.limits.seconds, "usd": self.limits.usd},
        }


# -- formatting of limits in execution messages ----------------------------------------------


def format_turns(n: int) -> str:
    """``"12 turns"`` or ``"1 turn"`` (remaining limits in execution messages)."""
    return f"{n} turn" if n == 1 else f"{n} turns"


def format_seconds(s: float) -> str:
    """``"1834 s of execution time"``, rounded down to whole seconds."""
    return f"{int(math.floor(max(0.0, s)))} s of execution time"


def format_usd(usd: float) -> str:
    """``"2.41 USD"``, rounded down to whole cents.

    Rounding down never shows the agent more allowance than remains.
    """
    cents = math.floor(max(0.0, usd) * 100 + 1e-9)
    return f"{cents / 100:.2f} USD"


def format_remaining(r: Remaining) -> tuple[str, str, str]:
    """The three remaining limits as texts: turns, execution time, cost."""
    return format_turns(r.turns), format_seconds(r.seconds), format_usd(r.usd)
