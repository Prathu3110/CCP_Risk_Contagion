"""Conversion between `Network` objects and the tensors the GVAE consumes.

Edge weights and balance-sheet figures are lognormal, so everything is carried
through the model in standardised log space and mapped back on the way out.
Keeping that bookkeeping in one place stops the generated networks from coming
out in the wrong units, which is the easiest way to get a plausible-looking
graph that behaves nothing like the real one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch

from ablation import resolve
from generators import Network
from gvae import GVAE, Batch, LatentSampler

_FLOOR = 1e-12


@dataclass(frozen=True)
class Scaler:
    """Mean and standard deviation of log weights and log node features."""

    weight_mean: float
    weight_std: float
    feature_mean: np.ndarray
    feature_std: np.ndarray

    def to_weights(self, standardised: np.ndarray) -> np.ndarray:
        return np.exp(standardised * self.weight_std + self.weight_mean)

    def to_features(self, standardised: np.ndarray) -> np.ndarray:
        return np.exp(standardised * self.feature_std + self.feature_mean)


def _log_features(net: Network, model_ratio: bool = True) -> np.ndarray:
    """Log assets and log equity *ratio*, not log equity.

    The node head has a diagonal Gaussian output, so it cannot represent the
    correlation between a bank's size and its capital. Feeding it the ratio
    makes the two targets close to independent, which is the assumption the
    head actually makes; modelling log equity directly lets big banks come back
    with small-bank capital and quietly changes how fragile the system is.
    """
    second = net.equity / np.maximum(net.assets, _FLOOR) if model_ratio else net.equity
    return np.log(np.column_stack([net.assets, second]) + _FLOOR)


def build_batch(
    corpus: list[Network], ablations: dict[str, Any] | None = None
) -> tuple[Batch, Scaler]:
    """Stack a corpus into dense tensors and fit the log-space scaler."""
    model_ratio = resolve(ablations)["model_equity_ratio"]
    stacked = np.stack([net.A for net in corpus])
    features = np.stack([_log_features(net, model_ratio) for net in corpus])

    present = stacked > 0
    log_weights = np.log(stacked[present])
    scaler = Scaler(
        weight_mean=float(log_weights.mean()),
        weight_std=float(log_weights.std() or 1.0),
        feature_mean=features.reshape(-1, features.shape[-1]).mean(axis=0),
        feature_std=features.reshape(-1, features.shape[-1]).std(axis=0),
    )

    standardised = np.zeros_like(stacked)
    standardised[present] = (log_weights - scaler.weight_mean) / scaler.weight_std
    X = (features - scaler.feature_mean) / scaler.feature_std

    return (
        Batch(
            A=torch.tensor(standardised, dtype=torch.float32),
            X=torch.tensor(X, dtype=torch.float32),
            mask=torch.tensor(present, dtype=torch.float32),
        ),
        scaler,
    )


def _calibrate(logits: np.ndarray, target_density: float, iterations: int = 60) -> float:
    """Logit offset that makes the mean edge probability match a target density.

    Density is the one statistic a global shift controls directly. Pinning it
    here means every other statistic - degree spread, exposure sizes, how a
    crisis travels - stays an honest test of what the model learned.
    """
    low, high = -20.0, 20.0
    for _ in range(iterations):
        mid = 0.5 * (low + high)
        if (1.0 / (1.0 + np.exp(-(logits + mid)))).mean() < target_density:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


@torch.no_grad()
def generate(
    model: GVAE,
    sampler: LatentSampler,
    scaler: Scaler,
    cfg: dict[str, Any],
    network_cfg: dict[str, Any],
    target_density: float,
    rng: np.random.Generator,
    ablations: dict[str, Any] | None = None,
) -> Network:
    """Decode one fresh banking system from a latent draw."""
    flags = resolve(ablations)
    model.eval()
    n = int(network_cfg["n_nodes"])
    z_t = torch.tensor(sampler.sample(n, rng), dtype=torch.float32)

    logits = model.edge_logits(z_t).numpy()
    off_diagonal = ~np.eye(n, dtype=bool)
    shift = _calibrate(logits[off_diagonal], target_density)
    probabilities = 1.0 / (1.0 + np.exp(-(logits + shift)))

    configured = cfg.get("edge_threshold")
    if configured is not None:
        mask = (probabilities > float(configured)) & off_diagonal
    elif not flags["bernoulli_edges"]:
        # Ablation: keep the most probable edges instead of drawing them.
        count = int(round(target_density * n * (n - 1)))
        cutoff = np.sort(probabilities[off_diagonal])[::-1][max(count - 1, 0)]
        mask = (probabilities >= cutoff) & off_diagonal
    else:
        # Draw each edge independently, which is the generative model the
        # decoder was actually trained under. Keeping the most probable edges
        # instead would be a deterministic shortcut to the right density, but
        # it hands every edge to the hubs and produces a system of mega-banks
        # surrounded by isolated ones.
        mask = (rng.random((n, n)) < probabilities) & off_diagonal

    # Sample from the predicted distributions rather than taking their means:
    # the spread of exposures is what drives contagion, and a mean-only decode
    # would produce a system where every exposure is the same size.
    weight_mu, weight_logvar = (t.numpy() for t in model.edge_weights(z_t))
    if not flags["sample_weight_head"]:
        sampled = weight_mu
    elif str(cfg.get("weight_likelihood", "gaussian")) == "student_t":
        # Sample from the same distribution the head was fitted under.
        df = float(cfg.get("weight_df", 4.0))
        scale = np.exp(0.5 * weight_logvar)
        sampled = weight_mu + scale * rng.standard_t(df, size=weight_mu.shape)
    else:
        sampled = weight_mu + np.exp(0.5 * weight_logvar) * rng.standard_normal(weight_mu.shape)
    A = np.where(mask, scaler.to_weights(sampled), 0.0)

    node_mu, node_logvar = (t.numpy() for t in model.node_attributes(z_t))
    node_draw = (
        node_mu + np.exp(0.5 * node_logvar) * rng.standard_normal(node_mu.shape)
        if flags["sample_weight_head"]
        else node_mu
    )
    attributes = scaler.to_features(node_draw)
    assets, second = attributes[:, 0], attributes[:, 1]
    total = A.sum()
    if total > 0 and flags["scale_interbank_claims"]:
        A *= float(network_cfg["interbank_share"]) * assets.sum() / total
    assets = np.maximum(assets, A.sum(axis=0))
    # `second` is the equity ratio by default, or equity itself when that
    # choice is ablated.
    equity_level = assets * second if flags["model_equity_ratio"] else second
    equity = np.clip(equity_level, _FLOOR, assets)

    # "Core" is a drawing label here, not an input: the largest banks the model
    # chose to build are marked as core so the two pictures read the same way.
    n_core = max(1, int(round(n * float(network_cfg["core_fraction"]))))
    degree = (A > 0).sum(axis=0) + (A > 0).sum(axis=1)
    core = np.zeros(n, dtype=bool)
    core[np.argsort(-degree, kind="stable")[:n_core]] = True

    return Network(A=A, assets=assets, equity=equity, core=core)
