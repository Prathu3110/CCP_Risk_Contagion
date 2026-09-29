"""Significance tests and intervals for the ensemble results.

One sample cannot separate a real difference from a lucky draw, so every number
the paper reports comes from 20 networks with an interval around it.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy import stats


def ks_test(observed: np.ndarray, generated: np.ndarray) -> dict[str, float]:
    """Two-sample Kolmogorov-Smirnov test on two DebtRank distributions.

    **The desired outcome here is a HIGH p-value.** The usual convention is
    reversed: a small p-value would mean the generated system's distribution of
    systemic importance is distinguishable from the true one, which is the
    failure case. A large p-value means the test cannot tell them apart, which
    is what a good generator should produce. Say this explicitly wherever the
    number is reported, because it reads as an error otherwise.
    """
    statistic, p_value = stats.ks_2samp(np.asarray(observed), np.asarray(generated))
    return {"statistic": float(statistic), "p_value": float(p_value)}


def bootstrap_ci(
    values: np.ndarray,
    statistic: Callable[[np.ndarray], float] = np.mean,
    n: int = 10_000,
    seed: int = 0,
    level: float = 0.95,
) -> dict[str, float]:
    """Percentile bootstrap confidence interval for a statistic of `values`."""
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return {"mean": 0.0, "lo": 0.0, "hi": 0.0}
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, array.size, size=(n, array.size))
    resampled = np.array([statistic(array[row]) for row in draws])
    tail = (1.0 - level) / 2.0
    return {
        "mean": float(statistic(array)),
        "lo": float(np.quantile(resampled, tail)),
        "hi": float(np.quantile(resampled, 1.0 - tail)),
    }
