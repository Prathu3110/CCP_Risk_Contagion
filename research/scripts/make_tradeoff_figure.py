"""The paper's headline figure: edge accuracy does not buy contagion realism.

    python3 research/scripts/make_tradeoff_figure.py

Left panel is the argument. Maximum entropy recovers every true edge and the
graph VAE recovers four percent of them, yet the two score the same on
contagion behaviour. If the conventional criterion carried information about
the behaviour these networks are generated to study, that could not happen.

Right panel shows the same failure is not rescued by looking at structure:
perfect recall goes with a structural error an order of magnitude worse than
the blind generator's.

Colours follow docs/WEB-PLAN.md section 1: amber is our model, the baselines are
a deliberately unaccented grey ramp ordered by how much they are told.
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
STRESS = "#a3302b"

STYLE = {
    "vae": ("#c8842a", "o"),
    "max_entropy": ("#4a4f58", "s"),
    "configuration": ("#7c828c", "^"),
    "erdos_renyi": ("#9ba1aa", "D"),
}
OFFSETS = {"vae": (8, -18), "max_entropy": (-10, 12), "configuration": (10, 6), "erdos_renyi": (10, 6)}

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"


def panel(ax, points, ylabel, title) -> None:
    for label, x, y, key in points:
        colour, marker = STYLE[key]
        ax.scatter(x, y, s=80, c=colour, marker=marker, zorder=3, edgecolors=PAPER, linewidths=0.9)
        dx, dy = OFFSETS[key]
        ha = "right" if dx < 0 else "left"
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(dx, dy),
                    fontsize=8, color=INK, ha=ha)
    ax.set_xlabel("Share of true edges recovered\n(right = better by the conventional criterion)",
                  fontsize=9, color=INK)
    ax.set_ylabel(f"{ylabel}\n(down = closer to the true system)", fontsize=9, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left", pad=10)
    ax.set_facecolor(PAPER)
    ax.set_xlim(-0.08, 1.12)
    ax.tick_params(colors=INK, labelsize=8)
    for side, spine in ax.spines.items():
        spine.set_visible(side in ("bottom", "left"))
        spine.set_color(RULE)
    ax.grid(color=RULE, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RESULTS / "figure_tradeoff.pdf")
    args = parser.parse_args()

    data = json.loads((RESULTS / "baselines.json").read_text())
    contagion, structure = [], []
    for key, entry in data["methods"].items():
        recall = entry["reconstruction"]["edge_recall"]
        contagion.append((entry["label"], recall, entry["behavioural"]["protocol_score"], key))
        structure.append((entry["label"], recall, entry["behavioural"]["structure_score"], key))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.9))
    fig.patch.set_facecolor(PAPER)
    panel(axes[0], contagion, "Contagion error", "Edge accuracy against contagion realism")
    panel(axes[1], structure, "Structural error", "The same recall against structural error")
    axes[1].set_yscale("log")

    # Mark the disagreement the paper is about.
    by_key = {key: (x, y) for _, x, y, key in contagion}
    vae_x, vae_y = by_key["vae"]
    maxent_x, maxent_y = by_key["max_entropy"]
    axes[0].annotate(
        "", xy=(maxent_x, maxent_y), xytext=(vae_x, vae_y),
        arrowprops=dict(arrowstyle="-", color=STRESS, linewidth=1.1, linestyle=(0, (4, 3))),
    )
    axes[0].text(
        (vae_x + maxent_x) / 2, max(vae_y, maxent_y) + 0.012,
        "same contagion error, 25x apart on edge recall",
        fontsize=8, color=STRESS, ha="center",
    )

    fig.tight_layout(pad=2.0)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, facecolor=PAPER)
    fig.savefig(args.out.with_suffix(".png"), dpi=200, facecolor=PAPER)

    args.out.with_suffix(".txt").write_text(
        f"Edge-reconstruction accuracy against contagion realism and structural error. "
        f"Seed {data['seed']}, {data['n_nodes']} banks, one sample per method. Contagion "
        "error is the mean relative gap over mean DebtRank, max DebtRank and mean cascade "
        "size; structural error is the mean relative gap over density, degree "
        "assortativity, mean exposure size and mean equity ratio (log scale). Maximum "
        "entropy is given the true row and column totals; the configuration model the true "
        "degree sequence and weight multiset; Erdos-Renyi the true density. The graph VAE "
        "is shown nothing about the target network.\n"
    )
    print(f"Wrote {args.out} and .png, .txt")


if __name__ == "__main__":
    main()
