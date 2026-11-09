"""Output errors of one candidate on the trajectories of a data group.

Error measures (5) to (8) per trajectory and dataset, with sample counts; the pooled
score (9); numerical failures (the error before a failure is a diagnostic with the completed and
required sample counts and never enters (9)). The predictions come from
:mod:`aspire_sysid.evaluate.predict`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .compiled import CompiledModel
from .data import Trajectory
from .metrics import ErrorMeasures, error_measures, pooled_score
from .predict import Deadline, Failure, TrajectoryPrediction, predict_trajectory


@dataclass
class TrajectoryEvaluation:
    """Output errors of one candidate on one trajectory or static dataset.

    ``required`` is the size of the scoring interval ``I``; ``completed`` the number of its
    samples predicted before a failure. ``measures`` holds (5) to (8) on the full interval when
    the evaluation finished; ``prefix`` holds them on the completed samples before a failure (a
    diagnostic that never enters (9)).
    """

    group: str
    trajectory: str
    n_samples: int
    scoring: tuple[int, int]
    required: int
    completed: int
    measures: ErrorMeasures | None
    prefix: ErrorMeasures | None
    failure: Failure | None
    prediction: TrajectoryPrediction | None = field(default=None, repr=False)

    @property
    def finished(self) -> bool:
        """True when every sample of the scoring interval was predicted."""
        return self.failure is None and self.completed == self.required

    def to_dict(self) -> dict[str, Any]:
        """Plain data for the JSON report (the predictions themselves are not included)."""
        return {
            "group": self.group,
            "trajectory": self.trajectory,
            "n_samples": self.n_samples,
            "scoring_interval": list(self.scoring),
            "required_samples": self.required,
            "completed_samples": self.completed,
            "finished": self.finished,
            "measures": None if self.measures is None else self.measures.to_dict(),
            "prefix_diagnostic": None if self.prefix is None else self.prefix.to_dict(),
            "failure": None if self.failure is None else self.failure.to_dict(),
            "note": "no sample in the scoring interval: no error measures; excluded from the pooled RMSE" if self.required == 0 else None,
        }


@dataclass
class GroupEvaluation:
    """Output errors of one candidate on one data group.

    ``pooled_rmse`` is equation (9) over the trajectories of the group when every trajectory
    finished (for the test group it is the ranking score ``S``), otherwise ``None``. A trajectory
    with no sample in its scoring interval (shorter than the initialization) has no error
    measures; it is reported with that note and does not enter (9).
    """

    group: str
    trajectories: list[TrajectoryEvaluation]

    @property
    def finished(self) -> bool:
        """True when the evaluation finished on every trajectory of the group."""
        return all(t.finished for t in self.trajectories)

    @property
    def pooled_rmse(self) -> float | None:
        """Equation (9) over the group, or ``None`` when a trajectory did not finish."""
        scored = [t for t in self.trajectories if t.required > 0]
        if not scored or not self.finished:
            return None
        return pooled_score(t.measures for t in scored)

    @property
    def failures(self) -> list[Failure]:
        """The numerical failures of the group."""
        return [t.failure for t in self.trajectories if t.failure is not None]

    def to_dict(self) -> dict[str, Any]:
        """Plain data for the JSON report."""
        return {
            "group": self.group,
            "finished": self.finished,
            "pooled_rmse": self.pooled_rmse,
            "scored_samples": sum(t.required for t in self.trajectories),
            "trajectories": [t.to_dict() for t in self.trajectories],
        }


def _trajectory_evaluation(pred: TrajectoryPrediction) -> TrajectoryEvaluation:
    traj = pred.trajectory
    scoring = pred.scoring
    idx = pred.completed
    required = len(scoring)
    measures = prefix = None
    y = pred.measured
    if pred.failure is None and len(idx) == required and required > 0:
        measures = error_measures(y[idx], pred.predicted[idx])
    elif idx:
        prefix = error_measures(y[idx], pred.predicted[idx])
    return TrajectoryEvaluation(
        group=traj.group,
        trajectory=traj.trajectory,
        n_samples=traj.n,
        scoring=(scoring.start, scoring.stop),
        required=required,
        completed=len(idx),
        measures=measures,
        prefix=prefix,
        failure=pred.failure,
        prediction=pred,
    )


def evaluate_group(model: CompiledModel, trajectories: list[Trajectory], group: str) -> GroupEvaluation:
    """Output errors of one candidate on the trajectories of one data group.

    Every trajectory is evaluated on its own; one deadline of ``evaluation.time_limit_s`` covers
    the group.
    """
    deadline = Deadline(model.task.evaluation.time_limit_s)
    return GroupEvaluation(group, [_trajectory_evaluation(predict_trajectory(model, t, deadline)) for t in trajectories])
