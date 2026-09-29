"""Choose hyperparameters on the validation networks. Never on the test ones.

    python3 research/scripts/run_tuning.py [--samples 5]

Writes `results/tuning.json` and prints the grid ordered by validation score.

This script exists because the first version of this project picked its kernel
bandwidth by comparing contagion gaps against the single network it then
reported results on. That is selection on the test set. Every candidate here is
scored against the mean statistics of the validation split, and the test split
is not loaded at all.
"""

from __future__ import annotations

import argparse
import itertools
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
from dataset import build_batch, generate  # noqa: E402
from evaluation import error_against, reference_statistics  # noqa: E402
from gvae import GVAE, fit_latent_sampler, train  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"

# Deliberately small. A wide grid scored on validation still risks overfitting
# the validation set, and every extra cell costs a full retrain.
GRID: dict[str, list[Any]] = {
    "weight_likelihood": ["gaussian", "student_t"],
    "latent_bandwidth": [0.25, 0.40, 0.55],
    "epochs": [300, 600],
}


def evaluate(
    cfg: dict[str, Any],
    split: splits.Split,
    reference: dict[str, float],
    samples: int,
) -> dict[str, float]:
    """Train under this config and score the samples it produces."""
    seed = int(cfg["seed"])
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)

    batch, scaler = build_batch(split.train)
    model = GVAE(
        in_dim=batch.X.shape[-1],
        hidden_dim=int(cfg["gvae"]["hidden_dim"]),
        latent_dim=int(cfg["gvae"]["latent_dim"]),
    )
    train(model, batch, cfg["gvae"])
    sampler = fit_latent_sampler(model, batch, float(cfg["gvae"]["latent_bandwidth"]))

    scores, structure, spread = [], [], []
    for index in range(samples):
        net = generate(
            model, sampler, scaler, cfg["gvae"], cfg["network"],
            # The training corpus density, never the density of anything the
            # model is scored against.
            target_density=split.corpus_density,
            rng=np.random.default_rng(seed + index),
        )
        result = error_against(reference, net, cfg["contagion"], seed)
        scores.append(result["protocol_score"])
        structure.append(result["structure_score"])
        weights = net.A[net.A > 0]
        spread.append(float(np.log(weights).std()) if weights.size > 1 else 0.0)

    return {
        "validation_protocol": float(np.mean(scores)),
        "validation_structure": float(np.mean(structure)),
        "log_weight_std": float(np.mean(spread)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "research" / "configs" / "demo.yaml")
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args()

    base = yaml.safe_load(args.config.read_text())
    seed = int(base["seed"])
    started = time.time()

    print("Building the train / validation / test split ...")
    split = splits.build(base)
    print(
        f"  train {len(split.train)}  validation {len(split.validation)}  "
        f"test {len(split.test)} (not loaded for scoring)"
    )
    print("Computing validation reference statistics ...")
    reference = reference_statistics(split.validation, base["contagion"], seed)
    truth_spread = float(
        np.mean([np.log(net.A[net.A > 0]).std() for net in split.validation])
    )

    keys = list(GRID)
    rows: list[dict[str, Any]] = []
    for values in itertools.product(*(GRID[key] for key in keys)):
        setting = dict(zip(keys, values))
        cfg = yaml.safe_load(args.config.read_text())
        cfg["gvae"].update(setting)
        label = "  ".join(f"{k}={v}" for k, v in setting.items())
        print(f"Training: {label} ...")
        rows.append({**setting, **evaluate(cfg, split, reference, args.samples)})

    rows.sort(key=lambda row: row["validation_protocol"])
    payload = {
        "seed": seed,
        "samples_per_candidate": args.samples,
        "validation_size": len(split.validation),
        "validation_log_weight_std": truth_spread,
        "corpus_density": split.corpus_density,
        "grid": GRID,
        "rows": rows,
        "best": rows[0],
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "tuning.json").write_text(json.dumps(payload, indent=1) + "\n")

    header = f"{'likelihood':<12}{'bandwidth':>11}{'epochs':>8}{'val protocol':>14}{'val structure':>15}{'log-w std':>11}"
    print(f"\n{header}")
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['weight_likelihood']:<12}{row['latent_bandwidth']:>11.2f}"
            f"{row['epochs']:>8}{row['validation_protocol']:>14.4f}"
            f"{row['validation_structure']:>15.4f}{row['log_weight_std']:>11.3f}"
        )
    print(f"\nValidation log-weight spread to match: {truth_spread:.3f}")
    print(f"Training-corpus density used for calibration: {split.corpus_density:.4f}")
    print(f"\nBest on validation: {payload['best']}")
    print(f"Wrote {RESULTS / 'tuning.json'}\nDone in {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
