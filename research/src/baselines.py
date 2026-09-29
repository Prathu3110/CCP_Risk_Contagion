"""Standard reconstruction methods, used as baselines for the evaluation protocol.

Each takes the observed `Network` and returns a new one with the same node
count and the same balance sheet, differing only in the interbank adjacency
matrix. Holding assets and equity fixed means any difference in contagion comes
from the network and nothing else.

These are reconstruction methods, and they are not competing on equal terms
with a generator. Each is handed some summary of the network it is trying to
reproduce: maximum entropy gets the exact row and column totals, the
configuration model gets the exact degree sequence and the exact multiset of
edge weights, Erdos-Renyi gets the density. The graph VAE is shown none of
these. It never sees the target network at all.

`INFORMATION_ACCESS` records that asymmetry so the paper can state it rather
than be caught by it. It is not a caveat: a from-scratch generator matching an
informed reconstruction on contagion behaviour is the result, not a confound in
it.

All of them inherit the observed balance sheet, which is why `evaluation.py`
scores balance-sheet metrics separately from contagion ones.
"""

from __future__ import annotations

import numpy as np

from generators import Network

_TOL = 1e-9
_MAX_IPF = 500

# What each method is given about the network it must reproduce.
INFORMATION_ACCESS: dict[str, str] = {
    "vae": "Nothing. Trained on other systems; never sees this network.",
    "max_entropy": "Exact row and column totals of the true matrix.",
    "configuration": "Exact degree sequence and exact multiset of true edge weights.",
    "erdos_renyi": "Edge density of the true matrix.",
}


def _rescale_to(A: np.ndarray, target_total: float) -> np.ndarray:
    """Match the observed total interbank volume, so scale is never the difference."""
    total = A.sum()
    return A * (target_total / total) if total > 0 else A


def maximum_entropy(net: Network) -> Network:
    """Iterative proportional fitting (the RAS algorithm) on the observed marginals.

    Takes only how much each bank owes in total and is owed in total, and
    spreads exposures as evenly as those totals allow. This is the field
    standard for reconstructing an unknown interbank network.

    It produces a nearly complete matrix: almost every bank ends up facing
    almost every other. That is the documented behaviour of the method, not a
    bug here, and it is exactly why the resulting system understates contagion
    while scoring well on edge recall.
    """
    row_target = net.A.sum(axis=1)  # what each bank owes in total
    column_target = net.A.sum(axis=0)  # what each bank is owed in total

    A = np.ones_like(net.A)
    np.fill_diagonal(A, 0.0)

    for _ in range(_MAX_IPF):
        row_sums = A.sum(axis=1, keepdims=True)
        A = A * np.divide(row_target[:, None], row_sums, out=np.zeros_like(A), where=row_sums > 0)
        column_sums = A.sum(axis=0, keepdims=True)
        A = A * np.divide(column_target[None, :], column_sums, out=np.zeros_like(A), where=column_sums > 0)
        np.fill_diagonal(A, 0.0)
        if (
            np.abs(A.sum(axis=1) - row_target).max() < _TOL
            and np.abs(A.sum(axis=0) - column_target).max() < _TOL
        ):
            break

    return Network(A=A, assets=net.assets, equity=net.equity, core=net.core)


def configuration_model(net: Network, seed: int) -> Network:
    """Keep every bank's number of counterparties, randomise who they are.

    In- and out-degree are preserved exactly; the observed edge weights are
    dealt out at random to the rewired edges, so total volume is unchanged.
    Isolates how much contagion behaviour comes from degree alone rather than
    from which banks actually face each other.
    """
    rng = np.random.default_rng(seed)
    n = net.n
    out_degree = (net.A > 0).sum(axis=1)
    in_degree = (net.A > 0).sum(axis=0)

    # Stub matching, rejecting self-loops and repeats by redrawing the target.
    adjacency = np.zeros((n, n), dtype=bool)
    targets = np.repeat(np.arange(n), in_degree)
    rng.shuffle(targets)
    cursor = 0
    for source in np.repeat(np.arange(n), out_degree):
        placed = False
        for offset in range(len(targets)):
            index = (cursor + offset) % len(targets)
            target = targets[index]
            if target != source and not adjacency[source, target]:
                adjacency[source, target] = True
                targets = np.delete(targets, index)
                placed = True
                break
        if not placed:
            # No legal stub left; drop this one rather than force a self-loop.
            continue
        cursor = 0

    weights = net.A[net.A > 0]
    rng.shuffle(weights)
    A = np.zeros_like(net.A)
    rows, columns = np.nonzero(adjacency)
    A[rows, columns] = weights[: len(rows)]
    A = _rescale_to(A, net.A.sum())

    return Network(A=A, assets=net.assets, equity=net.equity, core=net.core)


def erdos_renyi(net: Network, seed: int) -> Network:
    """Every link equally likely, matched only on overall density.

    The floor. A method that cannot beat this has learned nothing about
    structure.
    """
    rng = np.random.default_rng(seed)
    n = net.n
    observed_edges = net.A > 0
    density = observed_edges.sum() / (n * (n - 1))

    adjacency = rng.random((n, n)) < density
    np.fill_diagonal(adjacency, False)

    observed_weights = net.A[observed_edges]
    A = np.zeros_like(net.A)
    drawn = rng.choice(observed_weights, size=int(adjacency.sum()), replace=True)
    A[adjacency] = drawn
    A = _rescale_to(A, net.A.sum())

    return Network(A=A, assets=net.assets, equity=net.equity, core=net.core)
