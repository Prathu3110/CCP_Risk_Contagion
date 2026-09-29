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
from baselines import configuration_model, erdos_renyi, maximum_entropy  # noqa: E402
import splits  # noqa: E402
from generators import Network, balance_sheet, sample_network  # noqa: E402
from gvae import GVAE, fit_latent_sampler, train  # noqa: E402
from layout import match_by_degree, spring_positions, total_degree  # noqa: E402


# Every method the page can show. `role` drives colour: observed is ink blue,
# ours amber, baselines the grey ramp. Order here is the order on the page.
METHODS: tuple[tuple[str, str, str], ...] = (
    ("observed", "Simulated ground truth", "observed"),
    ("vae", "Our model", "ours"),
    ("max_entropy", "Maximum entropy", "baseline"),
    ("configuration", "Configuration model", "baseline"),
    ("erdos_renyi", "Erdos-Renyi", "baseline"),
)


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

    print("Building the train / validation / test split ...")
    split = splits.build(cfg)
    corpus = split.train
    # The page shows one test network. Test networks are never used to choose
    # anything; scripts/run_tuning.py does that on the validation split.
    observed = split.test[0]
    print(
        f"  train {len(split.train)}  validation {len(split.validation)}  "
        f"test {len(split.test)}, showing test network 1"
    )

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
            # The training corpus density, not the density of the network the
            # model is compared against. Taking it from `observed` would hand
            # the generator a true statistic about its own evaluation target,
            # which is the privileged access the baselines are criticised for.
            target_density=split.corpus_density,
            rng=np.random.default_rng(int(cfg["gvae"]["sample_seed"])),
        )

    print("Building the baseline reconstructions ...")
    systems: dict[str, Network] = {
        "observed": observed,
        "vae": generated,
        "max_entropy": maximum_entropy(observed),
        "configuration": configuration_model(observed, seed),
        "erdos_renyi": erdos_renyi(observed, seed),
    }

    print("Laying out every network on one shared set of positions ...")
    # The layout is computed once on the observed network and reused, matched by
    # degree rank. A bank in the same screen position is the comparable bank in
    # every view. Re-laying-out per method would destroy that correspondence.
    positions = spring_positions(observed.A, cfg["layout"])
    coordinates = {
        key: positions if key == "observed" else match_by_degree(observed.A, positions, net.A)
        for key, net in systems.items()
    }

    print("Running DebtRank on every bank, for every method ...")
    shock = float(cfg["contagion"]["debtrank_shock"])
    debtranks = {key: debtrank_profile(net, shock) for key, net in systems.items()}

    contagion_cfg = cfg["contagion"]
    shocks = np.linspace(
        float(contagion_cfg["shock_min"]),
        float(contagion_cfg["shock_max"]),
        int(contagion_cfg["shock_steps"]),
    )
    repeats = int(contagion_cfg["repeats"])
    print(f"Sweeping {len(shocks)} shock levels x {repeats} repeats through Eisenberg-Noe ...")
    cascades = {
        # Same seed for every method, so all of them meet an identical sequence
        # of random shock spreads and only the network differs.
        key: cascade_curve(net, shocks, repeats, np.random.default_rng(seed + 1))
        for key, net in systems.items()
    }

    out_dir = (args.config.resolve().parents[1] / cfg["export"]["out_dir"]).resolve()
    networks = {
        "n_nodes": int(cfg["network"]["n_nodes"]),
        "default_pair": ["observed", "vae"],
        "methods": {
            key: export.method_payload(key, label, role, systems[key], coordinates[key])
            for key, label, role in METHODS
        },
    }
    summary = export.summarise(observed, generated)
    metrics = {
        "training": training,
        "degree_hist": export.multi_histogram(
            {key: total_degree(net.A) for key, net in systems.items()},
            int(cfg["export"]["degree_bins"]),
        ),
        "weight_hist": export.multi_histogram(
            {key: np.log10(net.A[net.A > 0]) for key, net in systems.items()},
            int(cfg["export"]["weight_bins"]),
        ),
        "summary": {
            "by_method": {
                key: export.summarise(observed, systems[key])
                for key, _label, _role in METHODS
            }
        },
    }
    contagion_payload = {
        "shock": [round(float(s), 3) for s in shocks],
        "by_method": {
            key: {
                "debtrank": [round(float(v), 4) for v in debtranks[key]],
                "cascade": export.band(cascades[key]),
            }
            for key, _label, _role in METHODS
        },
    }

    written = export.write_all(out_dir, networks, metrics, contagion_payload)
    save_networks(args.config.resolve().parents[1] / "results", observed, generated)
    report(summary, debtranks["observed"], debtranks["vae"], cascades["observed"], cascades["vae"])
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
