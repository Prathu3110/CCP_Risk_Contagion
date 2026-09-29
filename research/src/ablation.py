"""The modelling choices that can be switched off, one at a time.

Each flag turns off one decision that measurement forced during development.
`CLAUDE.md` records why each was needed; this module turns those notes into an
experiment that reports how much worse the model gets without each one.

All flags default to on, so any code path that does not pass an override
behaves exactly as the committed pipeline does.
"""

from __future__ import annotations

from typing import Any

DEFAULTS: dict[str, bool] = {
    # Scale generated interbank claims to a share of the balance sheet. Off:
    # leave the decoder's raw scale, which lets exposures dwarf equity.
    "scale_interbank_claims": True,
    # Train the weight head as a Gaussian and sample it. Off: regress under MSE
    # and decode the mean, which collapses the spread of exposure sizes.
    "sample_weight_head": True,
    # Model equity as a ratio of assets. Off: model log equity directly, which
    # a diagonal Gaussian cannot correlate with bank size.
    "model_equity_ratio": True,
    # Draw edges as calibrated Bernoulli samples. Off: keep the most probable
    # edges, which reaches the same density but hands them all to the hubs.
    "bernoulli_edges": True,
    # Sample latents from a kernel estimate of the aggregate posterior. Off:
    # sample from the N(0, I) prior, where the decoder was never fitted.
    "kde_latent_sampling": True,
}


def resolve(overrides: dict[str, Any] | None = None) -> dict[str, bool]:
    """Merge overrides onto the defaults, rejecting unknown flag names."""
    flags = dict(DEFAULTS)
    for name, value in (overrides or {}).items():
        if name not in DEFAULTS:
            raise KeyError(f"Unknown ablation flag: {name}")
        flags[name] = bool(value)
    return flags
