"""Score every method on the held-out test networks. Run once, at the end.

    python3 research/scripts/run_test.py [--samples 20]

Nothing in this file may be used to choose anything. Hyperparameters come from
`scripts/run_tuning.py`, which sees only the validation split. If a number here
disappoints, the honest response is to report it, not to return to the grid.

Every method is scored against the same reference: the mean protocol statistics
of the test networks. The three baselines are additionally handed each test
network to reconstruct, which is the privileged access the paper is about. The
graph VAE is handed the training-corpus density and nothing else.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import splits  # noqa: E402
from baselines import (  # noqa: E402
    INFORMATION_ACCESS,
    configuration_model,
    erdos_renyi,
    maximum_entropy,
)
from dataset import build_batch, generate  # noqa: E402
from evaluation import (  # noqa: E402
    debtrank_profile,
    error_against,
    reference_statistics,
)
from gvae import GVAE, fit_latent_sampler, train  # noqa: E402
from statistics import bootstrap_ci, ks_test  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"

LABELS = {
    "vae": "Our model (graph VAE)",
    "max_entropy": "Maximum entropy",
    "configuration": "Configuration model",
    "erdos_renyi": "Erdos-Renyi",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "research" / "configs" / "demo.yaml")
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    seed = int(cfg["seed"])
    contagion_cfg = cfg["contagion"]
    shock = float(contagion_cfg["debtrank_shock"])
    started = time.time()

    split = splits.build(cfg)
    print(f"Test networks: {len(split.test)}. Computing reference statistics ...")
    reference = reference_statistics(split.test, contagion_cfg, seed)
    test_debtrank = np.concatenate([debtrank_profile(net, shock) for net in split.test])

    print(f"Training with the configuration chosen on validation ...")
    torch.manual_seed(seed)
    batch, scaler = build_batch(split.train)
    model = GVAE(
        in_dim=batch.X.shape[-1],
        hidden_dim=int(cfg["gvae"]["hidden_dim"]),
        latent_dim=int(cfg["gvae"]["latent_dim"]),
    )
    train(model, batch, cfg["gvae"])
    sampler = fit_latent_sampler(model, batch, float(cfg["gvae"]["latent_bandwidth"]))

    def score(nets: list, key: str) -> dict[str, Any]:
        protocol, structure, ks_p = [], [], []
        per_metric: dict[str, list[float]] = {}
        for net in nets:
            result = error_against(reference, net, contagion_cfg, seed)
            protocol.append(result["protocol_score"])
            structure.append(result["structure_score"])
            for name, value in result["gaps"].items():
                per_metric.setdefault(name, []).append(value)
            ks_p.append(ks_test(test_debtrank, debtrank_profile(net, shock))["p_value"])
        return {
            "label": LABELS[key],
            "sees": INFORMATION_ACCESS[key],
            "n_samples": len(nets),
            "protocol_score": bootstrap_ci(np.array(protocol), seed=seed),
            "structure_score": bootstrap_ci(np.array(structure), seed=seed),
            "gaps": {n: bootstrap_ci(np.array(v), seed=seed) for n, v in per_metric.items()},
            "ks_debtrank": {
                "median_p": float(np.median(ks_p)),
                "share_not_rejected_at_005": float(np.mean(np.array(ks_p) > 0.05)),
            },
        }

    print(f"Generating {args.samples} systems from the model ...")
    generated = [
        generate(
            model, sampler, scaler, cfg["gvae"], cfg["network"],
            target_density=split.corpus_density,
            rng=np.random.default_rng(seed + i),
        )
        for i in range(args.samples)
    ]

    print("Reconstructing each test network with the baselines ...")
    methods = {
        "vae": generated,
        "max_entropy": [maximum_entropy(net) for net in split.test],
        "configuration": [configuration_model(net, seed + i) for i, net in enumerate(split.test)],
        "erdos_renyi": [erdos_renyi(net, seed + i) for i, net in enumerate(split.test)],
    }

    payload: dict[str, Any] = {
        "seed": seed,
        "n_test_networks": len(split.test),
        "corpus_density": split.corpus_density,
        "chosen": {
            k: cfg["gvae"][k] for k in ("weight_likelihood", "latent_bandwidth", "epochs")
        },
        "methods": {key: score(nets, key) for key, nets in methods.items()},
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "test.json").write_text(json.dumps(payload, indent=1) + "\n")

    header = f"{'Method':<24}{'n':>4}{'protocol score':>24}{'structure':>11}{'KS p':>8}{'passes':>9}"
    print(f"\n{header}")
    print("-" * len(header))
    for entry in payload["methods"].values():
        score_ci = entry["protocol_score"]
        interval = f"{score_ci['mean']:.3f} [{score_ci['lo']:.3f}, {score_ci['hi']:.3f}]"
        passes = round(
            entry["ks_debtrank"]["share_not_rejected_at_005"] * entry["n_samples"]
        )
        print(
            f"{entry['label']:<24}{entry['n_samples']:>4}{interval:>24}"
            f"{entry['structure_score']['mean']:>11.3f}"
            f"{entry['ks_debtrank']['median_p']:>8.3f}"
            f"{passes:>6}/{entry['n_samples']}"
        )

    print(f"\nChosen on validation: {payload['chosen']}")
    print(f"Wrote {RESULTS / 'test.json'}\nDone in {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
