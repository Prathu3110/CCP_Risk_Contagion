"""Score every method on both criteria, over an ensemble, and write the results.

    python3 research/scripts/run_baselines.py              # 20 samples per method
    python3 research/scripts/run_baselines.py --samples 1  # quick single-sample table

Requires `results/networks.npz`, which `run_demo.py` writes. Run that first.

Writes `results/baselines.json` (first sample of each method, for inspection)
and `results/ensemble.json` (means, 95% bootstrap intervals, KS tests). The
paper quotes the ensemble file; a single sample cannot separate a real
difference from a lucky draw.

Maximum entropy is deterministic and therefore contributes one sample however
many are requested.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from baselines import (  # noqa: E402
    INFORMATION_ACCESS,
    configuration_model,
    erdos_renyi,
    maximum_entropy,
)
from dataset import build_batch, generate  # noqa: E402
from evaluation import (  # noqa: E402
    CONTAGION_METRICS,
    STRUCTURE_METRICS,
    behavioural_error,
    cascade_profile,
    debtrank_profile,
    reconstruction_error,
)
from generators import Network, sample_corpus  # noqa: E402
from gvae import GVAE, fit_latent_sampler  # noqa: E402
from gvae import train as train_gvae  # noqa: E402
from statistics import bootstrap_ci, ks_test  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"

LABELS = {
    "vae": "Our model (graph VAE)",
    "max_entropy": "Maximum entropy",
    "configuration": "Configuration model",
    "erdos_renyi": "Erdos-Renyi",
}
DETERMINISTIC = {"max_entropy"}


def load(name: str, cached: Any) -> Network:
    return Network(
        A=cached[f"{name}_A"],
        assets=cached[f"{name}_assets"],
        equity=cached[f"{name}_equity"],
        core=cached[f"{name}_core"],
    )


def vae_sampler(cfg: dict[str, Any], observed: Network) -> Callable[[int], Network]:
    """Retrain the model on its own seed, then draw fresh systems from it.

    Training is reproduced here rather than cached so this script depends on
    nothing `run_demo.py` leaves behind beyond the networks themselves.
    """
    seed = int(cfg["seed"])
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    corpus = sample_corpus(cfg["network"], int(cfg["corpus"]["n_train"]), rng)

    batch, scaler = build_batch(corpus)
    model = GVAE(
        in_dim=batch.X.shape[-1],
        hidden_dim=int(cfg["gvae"]["hidden_dim"]),
        latent_dim=int(cfg["gvae"]["latent_dim"]),
    )
    print(f"Training the graph VAE for {cfg['gvae']['epochs']} epochs to draw samples ...")
    train_gvae(model, batch, cfg["gvae"])
    sampler = fit_latent_sampler(model, batch, float(cfg["gvae"]["latent_bandwidth"]))
    density = float((observed.A > 0).sum()) / (observed.n * (observed.n - 1))

    def draw(sample_seed: int) -> Network:
        return generate(
            model, sampler, scaler, cfg["gvae"], cfg["network"],
            target_density=density, rng=np.random.default_rng(sample_seed),
        )

    return draw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "research" / "configs" / "demo.yaml")
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()

    cache = RESULTS / "networks.npz"
    if not cache.exists():
        raise SystemExit(f"{cache} not found. Run research/scripts/run_demo.py first.")

    cfg = yaml.safe_load(args.config.read_text())
    seed = int(cfg["seed"])
    contagion_cfg = cfg["contagion"]
    observed = load("observed", np.load(cache))
    observed_debtrank = debtrank_profile(observed, float(contagion_cfg["debtrank_shock"]))
    shocks = np.linspace(
        float(contagion_cfg["shock_min"]),
        float(contagion_cfg["shock_max"]),
        int(contagion_cfg["shock_steps"]),
    )

    draw_vae = vae_sampler(cfg, observed)
    draws: dict[str, Callable[[int], Network]] = {
        "vae": draw_vae,
        "max_entropy": lambda _s: maximum_entropy(observed),
        "configuration": lambda s: configuration_model(observed, s),
        "erdos_renyi": lambda s: erdos_renyi(observed, s),
    }

    single: dict[str, Any] = {"seed": seed, "n_nodes": int(observed.n), "methods": {}}
    ensemble: dict[str, Any] = {
        "seed": seed,
        "n_nodes": int(observed.n),
        "samples_requested": args.samples,
        "shock": [round(float(x), 4) for x in shocks],
        "observed_cascade": [
            round(float(v), 5)
            for v in cascade_profile(observed, contagion_cfg, seed).mean(axis=1)
        ],
        "methods": {},
    }

    for key, draw in draws.items():
        count = 1 if key in DETERMINISTIC else args.samples
        seeds = [seed + i for i in range(count)]
        print(f"Scoring {LABELS[key]} over {count} sample(s) ...")

        per_metric: dict[str, list[float]] = {}
        protocol, structure, recall, f1, frobenius = [], [], [], [], []
        ks_p: list[float] = []
        curves: list[np.ndarray] = []
        first: dict[str, Any] | None = None

        for sample_seed in seeds:
            net = draw(sample_seed)
            reconstruction = reconstruction_error(observed.A, net.A)
            # Shock sweeps share the observed seed so every method meets the
            # same sequence of random shock spreads.
            behavioural = behavioural_error(observed, net, contagion_cfg, seed)
            for name, value in behavioural["gaps"].items():
                per_metric.setdefault(name, []).append(value)
            protocol.append(behavioural["protocol_score"])
            structure.append(behavioural["structure_score"])
            recall.append(reconstruction["edge_recall"])
            f1.append(reconstruction["edge_f1"])
            frobenius.append(reconstruction["frobenius_relative"])
            curves.append(cascade_profile(net, contagion_cfg, seed).mean(axis=1))
            ks_p.append(
                ks_test(
                    observed_debtrank,
                    debtrank_profile(net, float(contagion_cfg["debtrank_shock"])),
                )["p_value"]
            )
            if first is None:
                first = {
                    "label": LABELS[key],
                    "sees": INFORMATION_ACCESS[key],
                    "reconstruction": reconstruction,
                    "behavioural": behavioural,
                }

        single["methods"][key] = first
        ensemble["methods"][key] = {
            "label": LABELS[key],
            "sees": INFORMATION_ACCESS[key],
            "n_samples": count,
            "seeds": seeds,
            "gaps": {name: bootstrap_ci(np.array(v), seed=seed) for name, v in per_metric.items()},
            "protocol_score": bootstrap_ci(np.array(protocol), seed=seed),
            "structure_score": bootstrap_ci(np.array(structure), seed=seed),
            "edge_recall": bootstrap_ci(np.array(recall), seed=seed),
            "edge_f1": bootstrap_ci(np.array(f1), seed=seed),
            "frobenius_relative": bootstrap_ci(np.array(frobenius), seed=seed),
            "cascade_curve": cascade_band(np.array(curves), seed),
            "ks_debtrank": {
                "median_p": float(np.median(ks_p)),
                "share_not_rejected_at_005": float(np.mean(np.array(ks_p) > 0.05)),
                "note": "A HIGH p-value is the desired outcome: it means the "
                        "generated distribution of systemic importance cannot be "
                        "distinguished from the true one.",
            },
        }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "baselines.json").write_text(json.dumps(single, indent=1) + "\n")
    (RESULTS / "ensemble.json").write_text(json.dumps(ensemble, indent=1) + "\n")
    write_web_evaluation(ensemble)
    report(ensemble)
    print(f"\nWrote {RESULTS / 'baselines.json'}\nWrote {RESULTS / 'ensemble.json'}")


def write_web_evaluation(ensemble: dict[str, Any]) -> None:
    """Ship the ensemble scores to the page, which plots them as its hero.

    Only the summary each point on the scatter needs; the page never sees the
    per-sample values.
    """
    payload = {
        "seed": ensemble["seed"],
        "samples": ensemble["samples_requested"],
        "methods": {
            key: {
                "label": entry["label"],
                "sees": entry["sees"],
                "n_samples": entry["n_samples"],
                "edge_recall": entry["edge_recall"],
                "edge_f1": entry["edge_f1"],
                "frobenius_relative": entry["frobenius_relative"],
                "protocol_score": entry["protocol_score"],
                "structure_score": entry["structure_score"],
                # Every individual metric, so the page can show the full table
                # rather than only the two headline scores.
                "gaps": entry["gaps"],
                "ks_debtrank": {
                    "median_p": entry["ks_debtrank"]["median_p"],
                    "share_not_rejected_at_005": entry["ks_debtrank"][
                        "share_not_rejected_at_005"
                    ],
                },
            }
            for key, entry in ensemble["methods"].items()
        },
    }
    out = ROOT / "web" / "public" / "data" / "evaluation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"Wrote {out}")


def cascade_band(curves: np.ndarray, seed: int) -> dict[str, list[float]]:
    """Mean default share per shock level, with a bootstrap band across samples."""
    bands = [bootstrap_ci(curves[:, i], seed=seed) for i in range(curves.shape[1])]
    return {
        "mean": [round(b["mean"], 5) for b in bands],
        "lo": [round(b["lo"], 5) for b in bands],
        "hi": [round(b["hi"], 5) for b in bands],
    }


def interval(entry: dict[str, float]) -> str:
    return f"{entry['mean']:.3f} [{entry['lo']:.3f}, {entry['hi']:.3f}]"


def report(ensemble: dict[str, Any]) -> None:
    print(f"\n{'Method':<24}{'n':>4}  {'edge recall':<22}{'contagion':<22}{'structure':<22}{'KS p':>7}")
    print("-" * 103)
    for entry in ensemble["methods"].values():
        print(
            f"{entry['label']:<24}{entry['n_samples']:>4}  "
            f"{interval(entry['edge_recall']):<22}"
            f"{interval(entry['protocol_score']):<22}"
            f"{interval(entry['structure_score']):<22}"
            f"{entry['ks_debtrank']['median_p']:>7.3f}"
        )
    print("\nIntervals are 95% bootstrap over samples (10,000 resamples).")
    print("contagion: " + ", ".join(CONTAGION_METRICS))
    print("structure: " + ", ".join(STRUCTURE_METRICS))
    print("KS p: median two-sample Kolmogorov-Smirnov p-value on the DebtRank")
    print("      distribution against the true system. HIGH is the good outcome -")
    print("      it means the two cannot be told apart.")


if __name__ == "__main__":
    main()
