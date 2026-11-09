"""Evaluation of candidates on training, validation and sealed test data.

Implements the evaluation modes, initialization, input hold and integration, the error
measures (5) to (8), the pooled score (9), eligibility, numerical failures and ranking, the
constraint assessment, complexity, structures and the sensitivity rank test, the reference
comparison, plots and the candidate and pool reports. This is the
only package that opens ``tasks/<id>/test/`` and ``tasks/<id>/reference/``:
``sealed.py`` reads the sealed test trajectories and the reference expression, and ``leaks.py``
searches files and texts for sealed information.

Modules: ``data`` (trajectories of the data groups), ``compiled`` (numerical form of the
expressions), ``predict`` (algebraic evaluation, one-step prediction, simulation, numerical
failures), ``metrics`` (equations (5) to (9)), ``errors`` (errors per trajectory and data group), ``constraints`` with ``symbolic``,
``symbolic_jobs`` and ``interval`` (requirement assessment), ``complexity`` (complexity and
structures), ``sensitivity`` (rank test), ``reference`` (reference comparison), ``pool`` (the
top-level :func:`evaluate_pool`, eligibility, ranking, permitted view), ``plots`` and ``report``.

Public interface:

- :func:`evaluate_pool` ``(task, models) -> PoolEvaluation``: a pure function of the task
  specification and the candidate files; ``models`` is a working directory, its
  ``models`` folder or a :class:`aspire_sysid.model.CheckReport`;
- :func:`permitted_view` ``(evaluation) -> dict``: the part the agent may receive;
- :func:`write_reports` ``(evaluation, task, out_dir, plots=True)``, :func:`render_markdown`,
  :func:`summary_text`, :func:`to_json`;
- :func:`evaluate_group` and :class:`CompiledModel` for single candidates (re-verification);
- :func:`error_measures`, :func:`pooled_score`.
"""

from .compiled import CompiledModel
from .metrics import ErrorMeasures, error_measures, pooled_score
from .errors import GroupEvaluation, TrajectoryEvaluation, evaluate_group
from .pool import (
    RANKING_LABEL,
    TIE_RELATIVE_TOLERANCE,
    TOP_K,
    CandidateEvaluation,
    PoolEvaluation,
    evaluate_pool,
    permitted_view,
)
from .report import render_markdown, summary_text, to_json, write_reports

__all__ = [
    "RANKING_LABEL",
    "TIE_RELATIVE_TOLERANCE",
    "TOP_K",
    "CandidateEvaluation",
    "CompiledModel",
    "ErrorMeasures",
    "GroupEvaluation",
    "PoolEvaluation",
    "TrajectoryEvaluation",
    "error_measures",
    "evaluate_group",
    "evaluate_pool",
    "permitted_view",
    "pooled_score",
    "render_markdown",
    "summary_text",
    "to_json",
    "write_reports",
]
