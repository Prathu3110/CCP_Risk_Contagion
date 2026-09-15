"""Run the whole experiment and write the web app's three JSON files.

    python research/scripts/run_demo.py [--config research/configs/demo.yaml]
                                        [--skip-training]

Everything is seeded from the config, so two runs produce identical output.
`--skip-training` is the fallback described in section 9 of the build plan: the
"generated" network comes from the sampler under different parameters instead
of the model, which still exercises the whole validation argument.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import export  # noqa: E402
from contagion import cascade_size, debtrank  # noqa: E402
from dataset import build_batch, generate  # noqa: E402
from generators import Network, balance_sheet, sample_corpus, sample_network  # noqa: E402
from gvae import GVAE, fit_latent_sampler, train  # noqa: E402
from layout import match_by_degree, spring_positions, total_degree  # noqa: E402


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def density(A: np.ndarray) -> float:
    n = A.shape[0]
    return float((A > 0).sum()) / (n * (n - 1))


def fallback_network(cfg: dict[str, Any], rng: np.random.Generator) -> Network:
    """Section 9 escape hatch: the sampler with perturbed parameters."""
    perturbed = dict(cfg)
    perturbed.update(
        p_core_periphery=cfg["p_core_periphery"] * 0.9,
        p_periphery_core=cfg["p_periphery_core"] * 1.1,
        weight_mu=cfg["weight_mu"] + 0.1,
    )
    return sample_network(perturbed, rng)


def debtrank_profile(net: Network, shock: float) -> np.ndarray:
    """DebtRank of every bank in turn."""
    return np.array([debtrank(net.A, net.equity, i, shock) for i in range(net.n)])


def cascade_curve(
    net: Network, shocks: np.ndarray, repeats: int, rng: np.random.Generator
) -> np.ndarray:
    """(n_shocks, repeats) default fractions under randomly spread shocks."""
    ext_assets, ext_liabilities = balance_sheet(net)
    out = np.zeros((len(shocks), repeats))
    for i, level in enumerate(shocks):
        for r in range(repeats):
            # The shock level is the average loss of external assets; how it
            # lands across banks is random, which is what the repeats capture.
            spread = rng.lognormal(-0.18, 0.6, size=net.n)
            per_bank = np.clip(level * spread, 0.0, 1.0)
            out[i, r] = cascade_size(net.A, ext_assets, per_bank, ext_liabilities)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_config = Path(__file__).resolve().parents[1] / "configs" / "demo.yaml"
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument("--skip-training", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    seed = int(cfg["seed"])
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    started = time.time()

    print(f"Sampling {cfg['corpus']['n_train']} ground-truth networks ...")
    corpus = sample_corpus(cfg["network"], int(cfg["corpus"]["n_train"]), rng)
    observed = sample_network(cfg["network"], rng)  # held out from training

    training: dict[str, list[float]] = {"epochs": [], "loss": []}
    if args.skip_training:
        print("Skipping training (--skip-training): sampling the fallback network.")
        generated = fallback_network(cfg["network"], rng)
    else:
        batch, scaler = build_batch(corpus)
        model = GVAE(
            in_dim=batch.X.shape[-1],
            hidden_dim=int(cfg["gvae"]["hidden_dim"]),
            latent_dim=int(cfg["gvae"]["latent_dim"]),
        )
        print(f"Training the graph VAE for {cfg['gvae']['epochs']} epochs on CPU ...")
        epochs, losses = train(model, batch, cfg["gvae"])
        training = {"epochs": epochs, "loss": [round(v, 4) for v in losses]}

        sampler = fit_latent_sampler(model, batch, float(cfg["gvae"]["latent_bandwidth"]))
        generated = generate(
            model,
            sampler,
            scaler,
            cfg["gvae"],
            cfg["network"],
            target_density=density(observed.A),
            rng=np.random.default_rng(int(cfg["gvae"]["sample_seed"])),
        )

    print("Laying out both networks ...")
    positions = spring_positions(observed.A, cfg["layout"])
    generated_positions = match_by_degree(observed.A, positions, generated.A)

    print("Running DebtRank on every bank ...")
    shock = float(cfg["contagion"]["debtrank_shock"])
    debtrank_observed = debtrank_profile(observed, shock)
    debtrank_generated = debtrank_profile(generated, shock)

    contagion_cfg = cfg["contagion"]
    shocks = np.linspace(
        float(contagion_cfg["shock_min"]),
        float(contagion_cfg["shock_max"]),
        int(contagion_cfg["shock_steps"]),
    )
    repeats = int(contagion_cfg["repeats"])
    print(f"Sweeping {len(shocks)} shock levels x {repeats} repeats through Eisenberg-Noe ...")
    cascade_observed = cascade_curve(observed, shocks, repeats, np.random.default_rng(seed + 1))
    cascade_generated = cascade_curve(generated, shocks, repeats, np.random.default_rng(seed + 1))

    out_dir = (args.config.resolve().parents[1] / cfg["export"]["out_dir"]).resolve()
    networks = {
        "n_nodes": int(cfg["network"]["n_nodes"]),
        "observed": export.network_payload(observed, positions),
        "generated": export.network_payload(generated, generated_positions),
    }
    summary = export.summarise(observed, generated)
    metrics = {
        "training": training,
        "degree_hist": export.shared_histogram(
            total_degree(observed.A), total_degree(generated.A), int(cfg["export"]["degree_bins"])
        ),
        "weight_hist": export.shared_histogram(
            np.log10(observed.A[observed.A > 0]),
            np.log10(generated.A[generated.A > 0]),
            int(cfg["export"]["weight_bins"]),
        ),
        "summary": summary,
    }
    contagion_payload = {
        "debtrank": {
            "observed": [round(float(v), 4) for v in debtrank_observed],
            "generated": [round(float(v), 4) for v in debtrank_generated],
        },
        "cascade": {
            "shock": [round(float(s), 3) for s in shocks],
            "observed": export.band(cascade_observed),
            "generated": export.band(cascade_generated),
        },
    }

    written = export.write_all(out_dir, networks, metrics, contagion_payload)
    save_networks(args.config.resolve().parents[1] / "results", observed, generated)
    report(summary, debtrank_observed, debtrank_generated, cascade_observed, cascade_generated)
    print("\nWrote:")
    for path in written:
        print(f"  {path}")
    print(f"Done in {time.time() - started:.1f}s")


def save_networks(results_dir: Path, observed: Network, generated: Network) -> None:
    """Cache both systems so figures and diagnostics need no retraining."""
    results_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        results_dir / "networks.npz",
        **{f"{label}_{field}": getattr(net, field)
           for label, net in (("observed", observed), ("generated", generated))
           for field in ("A", "assets", "equity", "core")},
    )


def report(
    summary: list[dict[str, Any]],
    debtrank_observed: np.ndarray,
    debtrank_generated: np.ndarray,
    cascade_observed: np.ndarray,
    cascade_generated: np.ndarray,
) -> None:
    """Print the table an examiner would ask to see."""
    print(f"\n{'Statistic':<24}{'observed':>12}{'generated':>12}{'gap':>9}")
    print("-" * 57)
    for row in summary:
        print(f"{row['name']:<24}{row['observed']:>12.4f}{row['generated']:>12.4f}{row['gap_pct']:>8.1f}%")
    for label, obs, gen in (
        ("Mean DebtRank", debtrank_observed.mean(), debtrank_generated.mean()),
        ("Max DebtRank", debtrank_observed.max(), debtrank_generated.max()),
        ("Mean cascade size", cascade_observed.mean(), cascade_generated.mean()),
    ):
        gap = abs(gen - obs) / abs(obs) * 100.0 if obs else 0.0
        print(f"{label:<24}{obs:>12.4f}{gen:>12.4f}{gap:>8.1f}%")


if __name__ == "__main__":
    main()
