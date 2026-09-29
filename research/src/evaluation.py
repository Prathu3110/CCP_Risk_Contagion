"""The two scores the paper is built on.

`reconstruction_error` is the conventional criterion: how accurately does a
generated network reproduce the true network's edges?

`behavioural_error` is the proposed one: does a crisis spread through the
generated network the way it spreads through the true one?

The paper's claim is that these two disagree. Both are defined here once and
imported everywhere; do not recompute either formula in another file.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from contagion import cascade_size, debtrank
from generators import Network, balance_sheet

# The protocol proper: quantities that describe how a crisis behaves. Kept
# explicit so it is a named, fixed set rather than whatever a function happened
# to return that day.
CONTAGION_METRICS: tuple[str, ...] = (
    "mean_debtrank",
    "max_debtrank",
    "mean_cascade_size",
)

# Reported alongside, never mixed in. These describe what a network looks like,
# not how it fails. Folding them into one score lets a large structural gap
# drown the contagion signal the protocol exists to measure: maximum entropy's
# density gap alone is an order of magnitude larger than any contagion gap.
# `mean_equity_ratio` is also trivially zero for any method that inherits the
# observed balance sheet, which would flatter every baseline against a
# generator that invents its own.
STRUCTURE_METRICS: tuple[str, ...] = (
    "edge_density",
    "degree_assortativity",
    "mean_exposure",
    "mean_equity_ratio",
)

PROTOCOL_METRICS: tuple[str, ...] = CONTAGION_METRICS + STRUCTURE_METRICS


def _relative_gap(true_value: float, generated: float) -> float:
    """Absolute relative gap, falling back to absolute difference at zero."""
    if true_value == 0:
        return abs(generated)
    return abs(generated - true_value) / abs(true_value)


def reconstruction_error(A_true: np.ndarray, A_generated: np.ndarray) -> dict[str, float]:
    """The conventional criterion: edge-level accuracy against the true matrix."""
    denominator = np.linalg.norm(A_true)
    frobenius = float(np.linalg.norm(A_generated - A_true) / denominator) if denominator > 0 else 0.0

    true_edges = A_true > 0
    generated_edges = A_generated > 0
    true_positives = float((true_edges & generated_edges).sum())
    precision = true_positives / generated_edges.sum() if generated_edges.any() else 0.0
    recall = true_positives / true_edges.sum() if true_edges.any() else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

    return {
        "frobenius_relative": frobenius,
        "edge_precision": float(precision),
        "edge_recall": float(recall),
        "edge_f1": float(f1),
    }


def degree_assortativity(A: np.ndarray) -> float:
    """Pearson correlation of degrees across connected pairs; negative for hubs."""
    binary = A > 0
    degree = (binary.sum(axis=0) + binary.sum(axis=1)).astype(float)
    sources, targets = np.nonzero(A)
    if len(sources) < 2:
        return 0.0
    left, right = degree[sources], degree[targets]
    if left.std() < 1e-12 or right.std() < 1e-12:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def debtrank_profile(net: Network, shock: float) -> np.ndarray:
    """DebtRank of every bank in turn."""
    return np.array([debtrank(net.A, net.equity, i, shock) for i in range(net.n)])


def cascade_profile(
    net: Network, cfg: dict[str, Any], seed: int
) -> np.ndarray:
    """(n_shocks, repeats) default fractions under randomly spread shocks.

    Mirrors the sweep in `scripts/run_demo.py`: the shock level is the average
    loss of external assets and how it lands across banks is random, which is
    what the repeats capture.
    """
    rng = np.random.default_rng(seed)
    shocks = np.linspace(
        float(cfg["shock_min"]), float(cfg["shock_max"]), int(cfg["shock_steps"])
    )
    repeats = int(cfg["repeats"])
    ext_assets, ext_liabilities = balance_sheet(net)

    out = np.zeros((len(shocks), repeats))
    for i, level in enumerate(shocks):
        for r in range(repeats):
            spread = rng.lognormal(-0.18, 0.6, size=net.n)
            per_bank = np.clip(level * spread, 0.0, 1.0)
            out[i, r] = cascade_size(net.A, ext_assets, per_bank, ext_liabilities)
    return out


def describe(net: Network, cfg: dict[str, Any], seed: int) -> dict[str, float]:
    """Every protocol quantity for one network, in raw units."""
    debtranks = debtrank_profile(net, float(cfg["debtrank_shock"]))
    cascade = cascade_profile(net, cfg, seed)
    edges = net.A > 0
    return {
        "mean_debtrank": float(debtranks.mean()),
        "max_debtrank": float(debtranks.max()),
        "mean_cascade_size": float(cascade.mean()),
        "edge_density": float(edges.sum()) / (net.n * (net.n - 1)),
        "degree_assortativity": degree_assortativity(net.A),
        "mean_exposure": float(net.A[edges].mean()) if edges.any() else 0.0,
        "mean_equity_ratio": float((net.equity / net.assets).mean()),
    }


def reference_statistics(
    nets: list[Network], cfg: dict[str, Any], seed: int
) -> dict[str, float]:
    """Average protocol statistics across a set of networks.

    A generator should match the distribution its training data came from, not
    one particular draw from it. Selecting hyperparameters against a single
    network rewards whichever setting happens to suit that draw, so tuning
    compares against the mean of the validation set instead.
    """
    described = [describe(net, cfg, seed) for net in nets]
    return {
        name: float(np.mean([entry[name] for entry in described]))
        for name in described[0]
    }


def error_against(
    reference: dict[str, float],
    net_generated: Network,
    cfg: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    """Score one generated network against pre-computed reference statistics."""
    generated_values = describe(net_generated, cfg, seed)
    gaps = {
        name: _relative_gap(reference[name], generated_values[name])
        for name in PROTOCOL_METRICS
    }
    return {
        "gaps": gaps,
        "protocol_score": float(np.mean([gaps[name] for name in CONTAGION_METRICS])),
        "structure_score": float(np.mean([gaps[name] for name in STRUCTURE_METRICS])),
    }


def behavioural_error(
    net_true: Network,
    net_generated: Network,
    cfg: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    """The proposed criterion: does a crisis behave the same way?

    Returns the relative gap on each metric, the raw values behind them,
    `protocol_score` (mean gap across the contagion metrics) and
    `structure_score` (mean gap across the structural ones). Lower is better.
    The two are kept apart deliberately: the paper's claim is about contagion
    behaviour, and a structural gap must not be allowed to stand in for it.

    The same `seed` is used for both networks' shock sweeps, so the two see an
    identical sequence of random shock spreads and any difference between them
    is the network rather than the draw.
    """
    true_values = describe(net_true, cfg, seed)
    generated_values = describe(net_generated, cfg, seed)
    gaps = {
        name: _relative_gap(true_values[name], generated_values[name])
        for name in PROTOCOL_METRICS
    }
    return {
        "gaps": gaps,
        "observed_values": true_values,
        "generated_values": generated_values,
        "protocol_score": float(np.mean([gaps[name] for name in CONTAGION_METRICS])),
        "structure_score": float(np.mean([gaps[name] for name in STRUCTURE_METRICS])),
    }
