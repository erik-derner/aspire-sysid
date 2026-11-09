"""Error measures (5) to (8) and the pooled score (9).

 For one trajectory or static dataset with scoring interval ``I`` of ``N``
samples, measured output ``y[k]`` and prediction or simulation ``ŷ[k]``:

- (5) ``μ = (1/N) Σ_{k∈I} y[k]`` and the population standard deviation
  ``σ = sqrt((1/N) Σ_{k∈I} (y[k] − μ)²)``;
- (6) ``RMSE = sqrt((1/N) Σ_{k∈I} (ŷ[k] − y[k])²)``, in the unit of the output;
- (7) ``NRMSE = RMSE / σ``, dimensionless;
- (8) ``R² = 1 − Σ (ŷ[k] − y[k])² / Σ (y[k] − μ)²``, dimensionless;
- (9) the pooled score over the test trajectories ``j = 1, …, J``:
  ``S = sqrt(Σ_j Σ_{k∈I_j} (ŷ_j[k] − y_j[k])² / Σ_j N_j)``, in the unit of the output; each
  trajectory contributes in proportion to its number of scored samples.

If ``σ = 0`` (a constant measured output), NRMSE and R² are undefined (``None``) and RMSE is
still reported. The sum of squared errors (SSE) is kept for (9).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class ErrorMeasures:
    """The error measures of one trajectory or dataset.

    ``n`` is the number of samples used, ``mean`` and ``std`` are μ and σ of (5), ``sse`` the sum
    of squared errors. ``nrmse`` and ``r2`` are ``None`` when σ = 0.
    """

    n: int
    mean: float
    std: float
    sse: float
    rmse: float
    nrmse: float | None
    r2: float | None

    def to_dict(self) -> dict:
        """Plain data for the JSON report."""
        return {
            "n": self.n,
            "mean": self.mean,
            "std": self.std,
            "sse": self.sse,
            "rmse": self.rmse,
            "nrmse": self.nrmse,
            "r2": self.r2,
        }


def error_measures(measured: np.ndarray, predicted: np.ndarray) -> ErrorMeasures:
    """Error measures (5) to (8) (module docstring) on the samples of one scoring interval.

    ``measured`` and ``predicted`` are the values ``y[k]`` and ``ŷ[k]`` for ``k ∈ I`` (equal
    length, at least one sample, finite predictions). Raises ``ValueError`` otherwise.
    """
    y = np.asarray(measured, dtype=float)
    yh = np.asarray(predicted, dtype=float)
    if y.shape != yh.shape or y.ndim != 1 or y.size == 0:
        raise ValueError("measured and predicted values must be non-empty vectors of equal length")
    if not (np.all(np.isfinite(y)) and np.all(np.isfinite(yh))):
        raise ValueError("error measures require finite measured and predicted values")
    n = int(y.size)
    mu = float(np.mean(y))
    dev = y - mu
    sst = float(np.sum(dev * dev))
    sigma = math.sqrt(sst / n)
    e = yh - y
    sse = float(np.sum(e * e))
    rmse = math.sqrt(sse / n)
    if sigma > 0.0:
        nrmse: float | None = rmse / sigma
        r2: float | None = 1.0 - sse / sst
    else:
        nrmse = r2 = None
    return ErrorMeasures(n=n, mean=mu, std=sigma, sse=sse, rmse=rmse, nrmse=nrmse, r2=r2)


def pooled_score(parts: Iterable[ErrorMeasures]) -> float:
    """The pooled RMSE ``S`` of equation (9) over the given trajectories.

    ``S = sqrt(Σ_j SSE_j / Σ_j N_j)``. Raises ``ValueError`` for an empty collection.
    """
    parts = list(parts)
    total_n = sum(p.n for p in parts)
    if total_n == 0:
        raise ValueError("the pooled score needs at least one scored sample")
    return math.sqrt(sum(p.sse for p in parts) / total_n)
