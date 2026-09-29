"""Cascade curves for every method, with bootstrap bands across the ensemble.

    python3 research/scripts/make_ensemble_figure.py

The true system is drawn in ink blue as the reference the others are judged
against; our model is amber; the baselines are the grey ramp from
docs/WEB-PLAN.md section 1, ordered by how much each is told about the network
it must reproduce.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

INK = "#10192b"
PAPER = "#f5f6f4"
RULE = "#d6d8d3"
OBSERVED = "#2e5e8c"

STYLE = {
    "vae": ("#c8842a", "o", "-"),
    "max_entropy": ("#4a4f58", "s", "--"),
    "configuration": ("#7c828c", "^", "-."),
    "erdos_renyi": ("#9ba1aa", "D", ":"),
}

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RESULTS / "figure_ensemble.pdf")
    args = parser.parse_args()

    data = json.loads((RESULTS / "ensemble.json").read_text())
    shocks = data["shock"]

    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)

    ax.plot(shocks, data["observed_cascade"], color=OBSERVED, linewidth=2.4,
            marker="o", markersize=4, label="Simulated ground truth", zorder=4)

    for key, entry in data["methods"].items():
        colour, marker, dash = STYLE[key]
        curve = entry["cascade_curve"]
        ax.fill_between(shocks, curve["lo"], curve["hi"], color=colour, alpha=0.16, linewidth=0)
        ax.plot(shocks, curve["mean"], color=colour, linewidth=1.8, linestyle=dash,
                marker=marker, markersize=3.6, label=entry["label"])

    ax.set_xlabel("Share of outside assets destroyed", fontsize=9, color=INK)
    ax.set_ylabel("Share of banks that default", fontsize=9, color=INK)
    ax.set_ylim(0, 1)
    ax.tick_params(colors=INK, labelsize=8)
    for side, spine in ax.spines.items():
        spine.set_visible(side in ("bottom", "left"))
        spine.set_color(RULE)
    ax.grid(color=RULE, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="lower right")

    fig.tight_layout(pad=1.6)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, facecolor=PAPER)
    fig.savefig(args.out.with_suffix(".png"), dpi=200, facecolor=PAPER)
    args.out.with_suffix(".txt").write_text(
        f"Share of banks defaulting as the shock grows, for the simulated ground truth "
        f"and each method. Seed {data['seed']}, {data['n_nodes']} banks, "
        f"{data['samples_requested']} samples per stochastic method (maximum entropy is "
        "deterministic and has no band). Shaded bands are 95% bootstrap intervals across "
        "samples. Every method is scored against the same sequence of random shock "
        "spreads.\n"
    )
    print(f"Wrote {args.out} and .png, .txt")


if __name__ == "__main__":
    main()
