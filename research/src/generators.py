"""Ground-truth sampler for core-periphery interbank exposure networks.

Convention used by every module in this package:

    A[i, j] = the amount bank i owes bank j.

So a row sum is a bank's total interbank liabilities, and a column sum is its
total interbank assets (what it stands to lose if its debtors fail). Drawn as a
directed graph, the edge i -> j means "money i owes j".

Core-periphery structure follows the stylised facts reported for real interbank
markets (Craig & von Peter, 2014, *Interbank tiering and money center banks*):
a small, densely interconnected core of money-centre banks intermediating for a
sparse periphery that rarely faces itself directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

FEATURE_NAMES: tuple[str, ...] = ("assets", "equity", "core")


@dataclass(frozen=True)
class Network:
    """One sampled banking system."""

    A: np.ndarray  # (n, n) float, A[i, j] = amount i owes j, zero diagonal
    assets: np.ndarray  # (n,) total assets per bank
    equity: np.ndarray  # (n,) equity buffer per bank
    core: np.ndarray  # (n,) bool, True for core banks

    @property
    def n(self) -> int:
        return self.A.shape[0]

    @property
    def features(self) -> np.ndarray:
        """(n, 3) node feature table in FEATURE_NAMES order."""
        return np.column_stack([self.assets, self.equity, self.core.astype(float)])


def _edge_probabilities(core: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """(n, n) matrix of per-pair edge probabilities from the four block rates."""
    debtor_core = core[:, None]
    creditor_core = core[None, :]
    p = np.where(
        debtor_core & creditor_core,
        cfg["p_core_core"],
        np.where(
            debtor_core & ~creditor_core,
            cfg["p_core_periphery"],
            np.where(~debtor_core & creditor_core, cfg["p_periphery_core"], cfg["p_periphery_periphery"]),
        ),
    )
    np.fill_diagonal(p, 0.0)
    return p.astype(float)


def sample_network(cfg: dict[str, Any], rng: np.random.Generator) -> Network:
    """Sample one core-periphery system from the `network` config block."""
    n = int(cfg["n_nodes"])
    n_core = max(1, int(round(n * float(cfg["core_fraction"]))))

    # Core membership is placed at random indices, not at fixed ones, so the
    # model has to learn that a core exists rather than memorise where it sits.
    core = np.zeros(n, dtype=bool)
    core[rng.choice(n, size=n_core, replace=False)] = True

    adjacency_mask = rng.random((n, n)) < _edge_probabilities(core, cfg)

    weights = rng.lognormal(cfg["weight_mu"], cfg["weight_sigma"], size=(n, n))
    touches_core = core[:, None] | core[None, :]
    weights = np.where(touches_core, weights * float(cfg["core_weight_scale"]), weights)
    A = np.where(adjacency_mask, weights, 0.0)
    np.fill_diagonal(A, 0.0)

    assets = rng.lognormal(cfg["assets_mu"], cfg["assets_sigma"], size=n)
    assets = np.where(core, assets * float(cfg["core_assets_scale"]), assets)

    # Interbank claims are only a slice of a real balance sheet. Rescale the
    # whole matrix by one scalar so system-wide interbank assets hit the
    # configured share of system total assets; this preserves the relative
    # structure while keeping leverage in a range where a crisis can spread
    # without every shock trivially wiping out the system.
    total = A.sum()
    if total > 0:
        A *= float(cfg["interbank_share"]) * assets.sum() / total
    # A bank's total assets must still cover what it is owed.
    assets = np.maximum(assets, A.sum(axis=0))
    equity = assets * float(cfg["equity_ratio"]) * rng.lognormal(0.0, cfg["equity_noise_sigma"], size=n)

    return Network(A=A, assets=assets, equity=equity, core=core)


def sample_corpus(cfg: dict[str, Any], n_graphs: int, rng: np.random.Generator) -> list[Network]:
    """Sample the training corpus."""
    return [sample_network(cfg, rng) for _ in range(n_graphs)]


def balance_sheet(net: Network) -> tuple[np.ndarray, np.ndarray]:
    """Split each bank into its non-interbank assets and liabilities.

    Returns (external assets, external liabilities). Interbank assets are the
    column sums of A and interbank liabilities the row sums, so what is left
    over on each side is external. External liabilities are pinned by the
    accounting identity assets - liabilities = equity, which makes equity
    exactly the buffer that absorbs a shock to external assets.
    """
    interbank_assets = net.A.sum(axis=0)
    interbank_liabilities = net.A.sum(axis=1)
    ext_assets = np.maximum(net.assets - interbank_assets, 0.0)
    ext_liabilities = np.maximum(net.assets - net.equity - interbank_liabilities, 0.0)
    return ext_assets, ext_liabilities
