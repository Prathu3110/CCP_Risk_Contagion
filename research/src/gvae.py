"""A graph variational autoencoder over dense adjacency matrices.

Follows Kipf & Welling (2016), *Variational Graph Auto-Encoders*, with two
additions the contagion experiments need:

  * a weight head, because interbank edges carry an amount, not just existence;
  * a node head, because a generated system needs its own balance sheets before
    a crisis can be simulated on it.

Both extra heads predict a Gaussian in log space and are trained by negative
log-likelihood rather than MSE. A squared-error head would learn the conditional
mean and generate networks whose exposures are all near-identical; contagion
depends on the tail of the exposure distribution, so that collapse would quietly
make every generated system look safer than it is.

At 60 nodes a dense adjacency is exactly equivalent to a sparse message-passing
implementation and avoids a PyTorch Geometric dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from torch import Tensor, nn

from ablation import resolve


def normalise_adjacency(A: Tensor) -> Tensor:
    """Symmetric normalisation D^-1/2 (A + I) D^-1/2 of a binarised adjacency."""
    binary = (A > 0).float()
    undirected = torch.maximum(binary, binary.transpose(-1, -2))
    eye = torch.eye(undirected.shape[-1], device=A.device).expand_as(undirected)
    with_self_loops = undirected + eye
    degree = with_self_loops.sum(-1).clamp(min=1.0).pow(-0.5)
    return degree.unsqueeze(-1) * with_self_loops * degree.unsqueeze(-2)


class GraphConv(nn.Module):
    """One propagation step: A_norm @ X @ W."""

    def __init__(self, in_dim: int, out_dim: int) -> None:
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim)

    def forward(self, A_norm: Tensor, X: Tensor) -> Tensor:
        return A_norm @ self.linear(X)


@dataclass
class Batch:
    """A corpus of graphs as stacked dense tensors."""

    A: Tensor  # (g, n, n) weights, standardised in log space where non-zero
    X: Tensor  # (g, n, f) node features
    mask: Tensor  # (g, n, n) 1 where an edge exists


class GVAE(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int, latent_dim: int, node_out: int = 2) -> None:
        super().__init__()
        self.shared = GraphConv(in_dim, hidden_dim)
        self.to_mu = GraphConv(hidden_dim, latent_dim)
        self.to_logvar = GraphConv(hidden_dim, latent_dim)
        # Each head emits a mean and a log-variance per target.
        self.weight_head = nn.Sequential(
            nn.Linear(2 * latent_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, 2)
        )
        self.node_head = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, 2 * node_out)
        )
        # Per-node popularity term, as in the latent-space network models of
        # Hoff, Raftery & Handcock (2002). A bare inner product ties how many
        # counterparties a bank has to where it sits in latent space; a
        # separate bias lets the decoder learn degree propensity on its own.
        self.bias_head = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, 1)
        )
        self.node_out = node_out

    def encode(self, A: Tensor, X: Tensor) -> tuple[Tensor, Tensor]:
        A_norm = normalise_adjacency(A)
        h = torch.relu(self.shared(A_norm, X))
        return self.to_mu(A_norm, h), self.to_logvar(A_norm, h).clamp(-8.0, 8.0)

    @staticmethod
    def reparameterise(mu: Tensor, logvar: Tensor) -> Tensor:
        return mu + torch.randn_like(mu) * torch.exp(0.5 * logvar)

    def edge_logits(self, z: Tensor) -> Tensor:
        bias = self.bias_head(z).squeeze(-1)
        return z @ z.transpose(-1, -2) + bias.unsqueeze(-1) + bias.unsqueeze(-2)

    def edge_weights(self, z: Tensor) -> tuple[Tensor, Tensor]:
        """(mean, log-variance) of each pair's standardised log exposure."""
        n = z.shape[-2]
        source = z.unsqueeze(-2).expand(*z.shape[:-1], n, z.shape[-1])
        target = z.unsqueeze(-3).expand(*z.shape[:-1], n, z.shape[-1])
        out = self.weight_head(torch.cat([source, target], dim=-1))
        return out[..., 0], out[..., 1].clamp(-6.0, 4.0)

    def node_attributes(self, z: Tensor) -> tuple[Tensor, Tensor]:
        """(mean, log-variance) of each bank's standardised log balance sheet."""
        out = self.node_head(z)
        return out[..., : self.node_out], out[..., self.node_out :].clamp(-6.0, 4.0)

    def forward(self, A: Tensor, X: Tensor) -> tuple[Tensor, tuple, tuple, Tensor, Tensor]:
        mu, logvar = self.encode(A, X)
        z = self.reparameterise(mu, logvar)
        return self.edge_logits(z), self.edge_weights(z), self.node_attributes(z), mu, logvar


def loss_function(
    logits: Tensor,
    weights: tuple[Tensor, Tensor],
    node_pred: tuple[Tensor, Tensor],
    mu: Tensor,
    logvar: Tensor,
    batch: Batch,
    cfg: dict[str, Any],
    ablations: dict[str, Any] | None = None,
) -> tuple[Tensor, dict[str, float]]:
    """Weighted edge BCE + Gaussian NLL on true edge weights and nodes + KL."""
    flags = resolve(ablations)
    off_diagonal = 1.0 - torch.eye(batch.mask.shape[-1], device=logits.device)
    pos_weight = torch.tensor(float(cfg["pos_weight"]), device=logits.device)
    bce = nn.functional.binary_cross_entropy_with_logits(
        logits, batch.mask, pos_weight=pos_weight, reduction="none"
    )
    edge_loss = (bce * off_diagonal).sum() / off_diagonal.sum() / batch.mask.shape[0]

    present = batch.mask > 0
    weight_mu, weight_logvar = weights
    node_mu, node_logvar = node_pred
    if flags["sample_weight_head"]:
        weight_loss = (
            nn.functional.gaussian_nll_loss(
                weight_mu[present], batch.A[present], weight_logvar[present].exp()
            )
            if present.any()
            else torch.zeros((), device=logits.device)
        )
        node_loss = nn.functional.gaussian_nll_loss(node_mu, batch.X, node_logvar.exp())
    else:
        # Squared error learns the conditional mean and nothing about spread.
        weight_loss = (
            nn.functional.mse_loss(weight_mu[present], batch.A[present])
            if present.any()
            else torch.zeros((), device=logits.device)
        )
        node_loss = nn.functional.mse_loss(node_mu, batch.X)
    kl = (-0.5 * (1 + logvar - mu.pow(2) - logvar.exp()).sum(-1)).mean()

    total = edge_loss + float(cfg["weight_loss_scale"]) * weight_loss + node_loss + float(cfg["kl_scale"]) * kl
    parts = {
        "edge": edge_loss.item(),
        "weight": weight_loss.item(),
        "node": node_loss.item(),
        "kl": kl.item(),
    }
    return total, parts


def train(
    model: GVAE,
    batch: Batch,
    cfg: dict[str, Any],
    ablations: dict[str, Any] | None = None,
) -> tuple[list[int], list[float]]:
    """Full-batch training on CPU. Returns (epochs, losses) for the loss curve."""
    optimiser = torch.optim.Adam(model.parameters(), lr=float(cfg["lr"]))
    epochs: list[int] = []
    losses: list[float] = []
    for epoch in range(1, int(cfg["epochs"]) + 1):
        model.train()
        optimiser.zero_grad()
        total, parts = loss_function(*model(batch.A, batch.X), batch, cfg, ablations)
        total.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimiser.step()
        epochs.append(epoch)
        losses.append(total.item())
        if epoch % int(cfg["log_every"]) == 0 or epoch == 1:
            detail = "  ".join(f"{k}={v:.4f}" for k, v in parts.items())
            print(f"  epoch {epoch:>4}  loss={total.item():.4f}   {detail}")
    return epochs, losses


@dataclass
class LatentSampler:
    """Draws fresh node latents from the region the decoder was trained on.

    Sampling from the N(0, I) prior is the textbook choice, but with a weak KL
    term the encoder never pushes the posterior all the way onto the prior, so
    prior draws land where the decoder was never fitted. Fitting a density to
    the latents the model actually produces (Ghosh et al., 2020, *From
    Variational to Deterministic Autoencoders*) fixes that.

    The density is a kernel estimate rather than one Gaussian, because the
    latent cloud is genuinely bimodal: core banks and periphery banks occupy
    different regions. A single Gaussian fitted across both puts most of its
    mass in the empty space between them, which decodes into systems made of
    isolated banks and implausible mega-hubs.
    """

    latents: np.ndarray  # (n_graphs * n_nodes, latent_dim) encoded means
    covariance: np.ndarray
    bandwidth: float
    use_kde: bool = True

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        if not self.use_kde:
            # The textbook choice, and the ablation: draw from the prior, where
            # a weakly-regularised decoder was never fitted.
            return rng.standard_normal((n, self.latents.shape[1]))
        chosen = self.latents[rng.integers(0, len(self.latents), size=n)]
        jitter = rng.multivariate_normal(
            np.zeros(self.latents.shape[1]), self.covariance * self.bandwidth**2, size=n
        )
        return chosen + jitter


@torch.no_grad()
def fit_latent_sampler(
    model: GVAE,
    batch: Batch,
    bandwidth: float,
    ablations: dict[str, Any] | None = None,
) -> LatentSampler:
    """Collect every encoded node latent and wrap it in a kernel density."""
    model.eval()
    mu, _ = model.encode(batch.A, batch.X)
    flat = mu.reshape(-1, mu.shape[-1]).cpu().numpy()
    return LatentSampler(
        latents=flat,
        covariance=np.cov(flat, rowvar=False),
        bandwidth=bandwidth,
        use_kde=resolve(ablations)["kde_latent_sampling"],
    )
