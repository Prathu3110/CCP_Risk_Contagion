"""Measure what each modelling choice is worth, by switching it off.

    python3 research/scripts/run_ablations.py [--seeds 5]

Trains the full model, then retrains with each choice disabled in turn, and
reports how much worse the generated systems get. Writes
`results/ablations.json` and prints a table with a delta column.

Each variant is trained once and sampled `--seeds` times; the deltas are on the
sample means.
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

from ablation import DEFAULTS  # noqa: E402
from dataset import build_batch, generate  # noqa: E402
from evaluation import behavioural_error  # noqa: E402
from generators import Network, sample_corpus  # noqa: E402
from gvae import GVAE, fit_latent_sampler, train  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"

LABELS = {
    "scale_interbank_claims": "No balance-sheet scaling",
    "sample_weight_head": "Squared error, not sampled",
    "model_equity_ratio": "Model equity, not the ratio",
    "bernoulli_edges": "Keep top edges, not sampled",
    "kde_latent_sampling": "Sample from the prior",
}


def variant(
    cfg: dict[str, Any],
    observed: Network,
    ablations: dict[str, bool],
    seeds: int,
) -> dict[str, float]:
    """Train once under these flags, sample several systems, average the scores."""
    seed = int(cfg["seed"])
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    corpus = sample_corpus(cfg["network"], int(cfg["corpus"]["n_train"]), rng)

    batch, scaler = build_batch(corpus, ablations)
    model = GVAE(
        in_dim=batch.X.shape[-1],
        hidden_dim=int(cfg["gvae"]["hidden_dim"]),
        latent_dim=int(cfg["gvae"]["latent_dim"]),
    )
    train(model, batch, cfg["gvae"], ablations)
    sampler = fit_latent_sampler(model, batch, float(cfg["gvae"]["latent_bandwidth"]), ablations)
    density = float((observed.A > 0).sum()) / (observed.n * (observed.n - 1))

    protocol, debtrank, spread = [], [], []
    for index in range(seeds):
        net = generate(
            model, sampler, scaler, cfg["gvae"], cfg["network"],
            target_density=density,
            rng=np.random.default_rng(seed + index),
            ablations=ablations,
        )
        scores = behavioural_error(observed, net, cfg["contagion"], seed)
        protocol.append(scores["protocol_score"])
        debtrank.append(scores["gaps"]["mean_debtrank"])
        weights = net.A[net.A > 0]
        spread.append(float(np.log(weights).std()) if weights.size > 1 else 0.0)

    return {
        "protocol_score": float(np.mean(protocol)),
        "mean_debtrank_gap": float(np.mean(debtrank)),
        "log_weight_std": float(np.mean(spread)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "research" / "configs" / "demo.yaml")
    parser.add_argument("--seeds", type=int, default=5)
    args = parser.parse_args()

    cache = RESULTS / "networks.npz"
    if not cache.exists():
        raise SystemExit(f"{cache} not found. Run research/scripts/run_demo.py first.")
    cached = np.load(cache)
    observed = Network(
        A=cached["observed_A"],
        assets=cached["observed_assets"],
        equity=cached["observed_equity"],
        core=cached["observed_core"],
    )

    cfg = yaml.safe_load(args.config.read_text())
    started = time.time()

    print(f"Training the full model ({args.seeds} samples) ...")
    full = variant(cfg, observed, dict(DEFAULTS), args.seeds)

    rows: list[dict[str, Any]] = []
    for flag in DEFAULTS:
        print(f"Retraining without: {LABELS[flag]} ...")
        flags = dict(DEFAULTS)
        flags[flag] = False
        scores = variant(cfg, observed, flags, args.seeds)
        rows.append({
            "flag": flag,
            "label": LABELS[flag],
            **scores,
            "protocol_delta": scores["protocol_score"] - full["protocol_score"],
        })

    rows.sort(key=lambda row: row["protocol_delta"], reverse=True)
    payload = {
        "seed": int(cfg["seed"]),
        "samples_per_variant": args.seeds,
        "full_model": full,
        "observed_log_weight_std": float(np.log(observed.A[observed.A > 0]).std()),
        "rows": rows,
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "ablations.json").write_text(json.dumps(payload, indent=1) + "\n")
    web = ROOT / "web" / "public" / "data" / "ablations.json"
    web.write_text(json.dumps(payload, indent=1) + "\n")

    report(payload)
    print(f"\nWrote {RESULTS / 'ablations.json'}\nWrote {web}")
    print(f"Done in {time.time() - started:.1f}s")


def report(payload: dict[str, Any]) -> None:
    full = payload["full_model"]
    header = f"{'Disabled choice':<30}{'protocol':>10}{'delta':>9}{'mean DR gap':>13}{'log-w std':>11}"
    print(f"\n{header}")
    print("-" * len(header))
    print(
        f"{'(none: the full model)':<30}{full['protocol_score']:>10.3f}{'':>9}"
        f"{full['mean_debtrank_gap']:>13.3f}{full['log_weight_std']:>11.3f}"
    )
    for row in payload["rows"]:
        print(
            f"{row['label']:<30}{row['protocol_score']:>10.3f}{row['protocol_delta']:>+9.3f}"
            f"{row['mean_debtrank_gap']:>13.3f}{row['log_weight_std']:>11.3f}"
        )
    print(f"\nlog-w std for the simulated ground truth: {payload['observed_log_weight_std']:.3f}")
    print("protocol: mean relative gap over the three contagion metrics, lower is better.")
    print("delta: change against the full model. Positive means the choice was earning its place.")


if __name__ == "__main__":
    main()
