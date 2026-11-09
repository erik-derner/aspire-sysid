"""Task specification: schema, loader, validation and sealing rules.

Implements the data, the notation, the static and dynamic formulations, the required
and optional task information and the formal and natural-language requirements of a task.
This package never opens the sealed test
data or the sealed reference expression; only ``aspire_sysid.evaluate`` does.

Public interface:

- :func:`load_task` (loader, no sealed access) and :func:`validate_task` (loader plus the sealed
  checks of ``aspire_sysid.evaluate.sealed``);
- :class:`TaskSpec` and the other data classes of :mod:`aspire_sysid.task.schema`;
- :func:`required_expression_keys` and :func:`argument_names` (expression-key convention);
- :func:`public_view` (the agent-visible part of a task);
- :func:`provision_data` (copies the agent-visible data into a working directory).
"""

from .loader import load_task
from .provision import WORKSPACE_TRAIN, WORKSPACE_VAL, ProvisionedFile, provision_data
from .public import public_view
from .schema import (
    DEFAULT_FUNCTIONS,
    REQUIREMENT_TYPES,
    Requirement,
    TaskError,
    TaskSpec,
    argument_names,
    required_expression_keys,
)
from .validate import validate_task

__all__ = [
    "DEFAULT_FUNCTIONS",
    "REQUIREMENT_TYPES",
    "ProvisionedFile",
    "Requirement",
    "TaskError",
    "TaskSpec",
    "WORKSPACE_TRAIN",
    "WORKSPACE_VAL",
    "argument_names",
    "load_task",
    "provision_data",
    "public_view",
    "required_expression_keys",
    "validate_task",
]
