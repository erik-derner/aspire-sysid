"""Changes of the task by the user during an interactive session.

If the user changes a requirement or allows a violation without exclusion, the
harness records the instruction and the round in which it takes effect. A
demonstrated violation of a formal requirement excludes a candidate unless the user explicitly
allows it. The user states a change together with a request for a new identification round; it
takes effect with that round and every later one, and the evaluation of each pool version uses
the task settings in force for its round: the current pool is evaluated under the recorded task
settings. Earlier pool versions keep the evaluation made under their own settings.

Change kinds (:data:`CHANGE_KINDS`):

* ``allow_violation``: a violation of the formal requirement ``requirement`` is reported without
  exclusion (``exclude_on_violation`` false, with the user's instruction as the exception);
* ``restore_exclusion``: a violation of ``requirement`` excludes the candidate again;
* ``set_tolerance``: the tolerance of ``requirement`` becomes ``value`` in the unit of the
  requirement;
* ``add_nl_requirement``: an additional requirement in natural language, assessed by the human
.

The instruction text is kept verbatim. Changes of other task information (data, model variables,
evaluation settings) are not supported in a session: they define a different task.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Iterable

from .schema import NLRequirement, Source, TaskSpec, Tolerance

__all__ = ["CHANGE_KINDS", "TaskChange", "TaskChangeError", "apply_changes", "describe_changes"]

CHANGE_KINDS: tuple[str, ...] = ("allow_violation", "restore_exclusion", "set_tolerance", "add_nl_requirement")
"""The task changes a user can make in a session (module docstring)."""


class TaskChangeError(ValueError):
    """A task change names an unknown requirement or is malformed."""


@dataclass(frozen=True)
class TaskChange:
    """One change of the task stated by the user.

    ``requirement`` is the identifier of the formal requirement (``None`` for
    ``add_nl_requirement``); ``instruction`` is the user's verbatim text; ``stated_by`` and
    ``date`` attribute it; ``value`` is the new tolerance of ``set_tolerance``.
    """

    kind: str
    requirement: str | None
    instruction: str
    stated_by: str
    date: str
    value: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in CHANGE_KINDS:
            raise TaskChangeError(f"unknown task change {self.kind!r}; supported: {', '.join(CHANGE_KINDS)}")
        if not self.instruction.strip():
            raise TaskChangeError("a task change needs the user's instruction")
        if self.kind == "set_tolerance" and (self.value is None or not (self.value >= 0)):
            raise TaskChangeError("a tolerance must be a non-negative number")
        if self.kind != "add_nl_requirement" and not self.requirement:
            raise TaskChangeError(f"the change {self.kind} names no requirement")

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the session record."""
        return dataclasses.asdict(self)

    def text(self) -> str:
        """One sentence stating the change and its source, for the new-round message."""
        src = f"instruction of {self.stated_by} ({self.date}): \"{self.instruction}\""
        if self.kind == "allow_violation":
            return f"a violation of requirement {self.requirement} is reported without exclusion; {src}"
        if self.kind == "restore_exclusion":
            return f"a demonstrated violation of requirement {self.requirement} excludes the candidate again; {src}"
        if self.kind == "set_tolerance":
            return f"the tolerance of requirement {self.requirement} is {self.value:g} in the unit of the requirement; {src}"
        return f"additional requirement in natural language, assessed by the human; {src}"


def _nl_id(task: TaskSpec) -> str:
    taken = {r.id for r in task.requirements} | {r.id for r in task.requirements_nl}
    k = 1
    while f"U{k}" in taken:
        k += 1
    return f"U{k}"


def apply_changes(task: TaskSpec, changes: Iterable[TaskChange]) -> TaskSpec:
    """The task with ``changes`` applied in order.

    Returns a new :class:`TaskSpec`; ``task`` is not modified. The sealed part and every other
    field are kept. Raises :class:`TaskChangeError` for an unknown requirement identifier. An
    added natural-language requirement receives the identifier ``U1``, ``U2``, ... (the first
    free one).
    """
    for ch in changes:
        if ch.kind == "add_nl_requirement":
            nl = NLRequirement(id=_nl_id(task), text=ch.instruction, source=Source(ch.stated_by, ch.date))
            task = dataclasses.replace(task, requirements_nl=task.requirements_nl + (nl,))
            continue
        ids = [r.id for r in task.requirements]
        if ch.requirement not in ids:
            raise TaskChangeError(
                f"requirement {ch.requirement!r} is not a formal requirement of task {task.id} ({', '.join(ids) or 'none'})"
            )
        new = []
        for r in task.requirements:
            if r.id == ch.requirement:
                src = Source(ch.stated_by, ch.date, note=ch.instruction)
                if ch.kind == "allow_violation":
                    r = dataclasses.replace(r, exclude_on_violation=False, exception=src)
                elif ch.kind == "restore_exclusion":
                    r = dataclasses.replace(r, exclude_on_violation=True, exception=None)
                else:
                    assert ch.value is not None
                    r = dataclasses.replace(r, tolerance=Tolerance(float(ch.value), r.tolerance.unit))
            new.append(r)
        task = dataclasses.replace(task, requirements=tuple(new))
    return task


def describe_changes(changes: Iterable[tuple[int, TaskChange]]) -> str:
    """The effective task changes as text, each with the round in which it took effect."""
    items = [f"from round {rnd}: {ch.text()}" for rnd, ch in changes]
    return "; ".join(items) if items else "none"
