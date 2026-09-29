"""Score every method on both criteria and write results/baselines.json.

    python3 research/scripts/run_baselines.py

Requires `results/networks.npz`, which `run_demo.py` writes. Run that first.

The paper's argument lives or dies on the table this prints: if maximum entropy
wins on edge accuracy and loses on contagion realism, the two criteria disagree
and the evaluation protocol is doing real work.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from baselines import configuration_model, erdos_renyi, maximum_entropy  # noqa: E402
from evaluation import behavioural_error, reconstruction_error  # noqa: E402
from generators import Network  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"

LABELS = {
    "vae": "Our model (graph VAE)",
    "max_entropy": "Maximum entropy",
    "configuration": "Configuration model",
    "erdos_renyi": "Erdos-Renyi",
}


def load(name: str, cached: Any) -> Network:
    return Network(
        A=cached[f"{name}_A"],
        assets=cached[f"{name}_assets"],
        equity=cached[f"{name}_equity"],
        core=cached[f"{name}_core"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "research" / "configs" / "demo.yaml")
    args = parser.parse_args()

    cache = RESULTS / "networks.npz"
    if not cache.exists():
        raise SystemExit(f"{cache} not found. Run research/scripts/run_demo.py first.")

    cfg = yaml.safe_load(args.config.read_text())
    seed = int(cfg["seed"])
    contagion_cfg = cfg["contagion"]
    cached = np.load(cache)

    observed = load("observed", cached)
    methods = {
        "vae": load("generated", cached),
        "max_entropy": maximum_entropy(observed),
        "configuration": configuration_model(observed, seed),
        "erdos_renyi": erdos_renyi(observed, seed),
    }

    results: dict[str, Any] = {"seed": seed, "n_nodes": int(observed.n), "methods": {}}
    for key, net in methods.items():
        reconstruction = reconstruction_error(observed.A, net.A)
        behavioural = behavioural_error(observed, net, contagion_cfg, seed)
        results["methods"][key] = {
            "label": LABELS[key],
            "reconstruction": reconstruction,
            "behavioural": behavioural,
        }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "baselines.json").write_text(json.dumps(results, indent=1) + "\n")
    report(results)
    print(f"\nWrote {RESULTS / 'baselines.json'}")


def report(results: dict[str, Any]) -> None:
    print(f"\n{'Method':<24}{'edge F1':>9}{'Frobenius':>11}{'protocol':>10}{'mean DR':>10}{'cascade':>9}")
    print("-" * 73)
    for entry in results["methods"].values():
        reconstruction = entry["reconstruction"]
        behavioural = entry["behavioural"]
        print(
            f"{entry['label']:<24}"
            f"{reconstruction['edge_f1']:>9.3f}"
            f"{reconstruction['frobenius_relative']:>11.3f}"
            f"{behavioural['protocol_score']:>10.3f}"
            f"{behavioural['gaps']['mean_debtrank']:>10.3f}"
            f"{behavioural['gaps']['mean_cascade_size']:>9.3f}"
        )
    print("\nedge F1: higher is better (conventional criterion).")
    print("protocol / mean DR / cascade: relative gaps, lower is better (proposed criterion).")


if __name__ == "__main__":
    main()
