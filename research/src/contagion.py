"""Two standard interbank contagion models.

Both take the exposure convention from `generators`: A[i, j] is the amount bank
i owes bank j, so bank j is the one that loses when bank i is in trouble.

  * `debtrank`  - Battiston, Puliga, Kaushik, Tasca & Caldarelli (2012),
    *DebtRank: Too central to fail? Financial networks, the FED and systemic
    risk*, Scientific Reports 2:541. Measures distress propagation as a
    fraction of system economic value, without requiring anyone to default.

  * `eisenberg_noe` - Eisenberg & Noe (2001), *Systemic risk in financial
    systems*, Management Science 47(2):236-249. Solves the clearing payment
    fixed point and reports who cannot pay in full.
"""

from __future__ import annotations

import numpy as np

_MAX_ITERS = 200
_TOL = 1e-10


def impact_matrix(A: np.ndarray, equity: np.ndarray) -> np.ndarray:
    """W[i, j] = share of j's equity destroyed if i's debt is fully written off."""
    safe_equity = np.maximum(equity, _TOL)
    return np.minimum(1.0, A / safe_equity[None, :])


def debtrank(
    A: np.ndarray,
    equity: np.ndarray,
    shocked_node: int,
    initial_shock: float = 1.0,
    economic_value: np.ndarray | None = None,
) -> float:
    """Fraction of total system economic value destroyed by distressing one bank.

    Nodes carry a continuous distress h in [0, 1] and a state in
    {undistressed, distressed, inactive}. A node only ever transmits distress on
    the round immediately after it receives some; afterwards it goes inactive.
    That one-shot rule is what stops distress cycling round a loop forever.
    """
    n = A.shape[0]
    W = impact_matrix(A, equity)
    value = np.asarray(economic_value, dtype=float) if economic_value is not None else A.sum(axis=0)
    total_value = value.sum()
    if total_value <= 0:
        return 0.0

    h = np.zeros(n)
    h[shocked_node] = float(np.clip(initial_shock, 0.0, 1.0))
    undistressed = np.ones(n, dtype=bool)
    undistressed[shocked_node] = False
    distressed = np.zeros(n, dtype=bool)
    distressed[shocked_node] = True

    for _ in range(_MAX_ITERS):
        if not distressed.any():
            break
        # Only currently-distressed senders transmit, and only into nodes that
        # have not yet had their turn.
        incoming = W[distressed, :].T @ h[distressed]
        new_h = np.minimum(1.0, h + np.where(undistressed, incoming, 0.0))
        newly_hit = undistressed & (new_h > h + _TOL)
        # This round's distressed nodes have now spoken; they go inactive.
        distressed = newly_hit
        undistressed = undistressed & ~newly_hit
        if not np.any(np.abs(new_h - h) > _TOL):
            h = new_h
            break
        h = new_h

    baseline = h[shocked_node] * value[shocked_node]
    return float((h @ value - baseline) / total_value)


def eisenberg_noe(
    A: np.ndarray,
    external_assets: np.ndarray,
    shock: float | np.ndarray,
    external_liabilities: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Clearing vector via the fictitious default algorithm.

    `shock` is the fraction of external assets wiped out, either system-wide as
    a scalar or per bank as a vector. `external_liabilities` are obligations
    outside the interbank system (deposits and the like), which rank alongside
    interbank claims and so are settled out of external assets first; leaving
    them out makes every bank look implausibly solvent. Returns (clearing
    payments, defaulted mask), where a bank has defaulted if it cannot settle
    its interbank obligations in full.
    """
    obligations = A.sum(axis=1)  # row sum = what i owes everyone
    with np.errstate(invalid="ignore", divide="ignore"):
        pi = np.where(obligations[:, None] > 0, A / np.maximum(obligations, _TOL)[:, None], 0.0)

    outside = np.zeros_like(external_assets) if external_liabilities is None else external_liabilities
    surviving_external = np.maximum(external_assets * (1.0 - np.asarray(shock, dtype=float)) - outside, 0.0)
    payments = obligations.copy()  # start optimistic: everyone pays in full

    for _ in range(_MAX_ITERS):
        resources = surviving_external + pi.T @ payments
        updated = np.minimum(obligations, np.maximum(resources, 0.0))
        if np.max(np.abs(updated - payments)) < _TOL:
            payments = updated
            break
        payments = updated

    defaulted = payments < obligations - 1e-8
    return payments, defaulted


def cascade_size(
    A: np.ndarray,
    external_assets: np.ndarray,
    shock: float | np.ndarray,
    external_liabilities: np.ndarray | None = None,
) -> float:
    """Share of banks that fail to pay in full under a given shock."""
    _, defaulted = eisenberg_noe(A, external_assets, shock, external_liabilities)
    return float(defaulted.mean())
