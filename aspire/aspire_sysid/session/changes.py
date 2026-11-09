"""Task changes by the user during an interactive session.

The implementation lives in :mod:`aspire_sysid.task.changes`, a neutral module that the session
layer (which records the changes) and the record module (which re-applies them when it recomputes
an evaluation) both use; this module re-exports it for the session layer.
"""

from ..task.changes import CHANGE_KINDS, TaskChange, TaskChangeError, apply_changes, describe_changes

__all__ = ["CHANGE_KINDS", "TaskChange", "TaskChangeError", "apply_changes", "describe_changes"]
