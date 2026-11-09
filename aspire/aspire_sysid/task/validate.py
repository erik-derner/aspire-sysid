"""Complete validation of a task folder, including its sealed part.

 :func:`validate_task` loads the specification with
:func:`aspire_sysid.task.loader.load_task` and then asks ``aspire_sysid.evaluate.sealed`` to
check the sealed test files and the reference expression; this module itself never resolves a
sealed path.
"""

from __future__ import annotations

from pathlib import Path

from .loader import load_task
from .schema import TaskError, TaskSpec


def validate_task(task_dir: str | Path) -> TaskSpec:
    """Load ``task_dir`` and validate every part of it; return the task or raise :class:`TaskError`.

    Validates the task information, the test trajectories and the reference
    (the loader validations, and in addition: the reference expression, where present, evaluates to
    finite values on the training data).
    """
    from ..evaluate.sealed import validate_sealed

    task = load_task(task_dir)
    errors = validate_sealed(task)
    if errors:
        raise TaskError(errors, task.task_dir)
    return task
