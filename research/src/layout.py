"""Node positions, computed once in Python and shipped to the browser.

The web app draws circles and lines at given coordinates; it runs no layout
algorithm of its own. Doing it here keeps the page load instant and makes the
drawing deterministic across runs.

The two networks share one set of positions, assigned by degree rank, so that
the busiest bank in the generated system sits where the busiest bank in the
observed system sits. Without that the eye compares layouts instead of
structure.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import numpy as np


def total_degree(A: np.ndarray) -> np.ndarray:
    """Number of counterparties per bank, counting both directions."""
    binary = A > 0
    return (binary.sum(axis=0) + binary.sum(axis=1)).astype(float)


def _normalise(pos: np.ndarray, margin: float = 0.04) -> np.ndarray:
    """Map positions into [margin, 1 - margin] on both axes."""
    span = pos.max(axis=0) - pos.min(axis=0)
    span[span < 1e-9] = 1.0
    unit = (pos - pos.min(axis=0)) / span
    return margin + unit * (1.0 - 2.0 * margin)


def spring_positions(A: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """(n, 2) positions in 0-1 from a seeded spring layout on the observed graph."""
    graph = nx.from_numpy_array(np.maximum(A, A.T), create_using=nx.Graph)
    raw = nx.spring_layout(
        graph,
        weight="weight",
        seed=int(cfg["seed"]),
        iterations=int(cfg["spring_iterations"]),
    )
    pos = np.array([raw[node] for node in range(A.shape[0])], dtype=float)
    return _normalise(pos)


def match_by_degree(reference: np.ndarray, positions: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Give each target node the position of the same-degree-rank reference node.

    `reference` and `target` are adjacency matrices of the same size. Ties are
    broken by node index, so the mapping is deterministic.
    """
    reference_rank = np.argsort(np.argsort(-total_degree(reference), kind="stable"), kind="stable")
    target_order = np.argsort(-total_degree(target), kind="stable")

    slot_for_rank = np.empty(len(reference_rank), dtype=int)
    slot_for_rank[reference_rank] = np.arange(len(reference_rank))

    matched = np.empty_like(positions)
    for rank, node in enumerate(target_order):
        matched[node] = positions[slot_for_rank[rank]]
    return matched
