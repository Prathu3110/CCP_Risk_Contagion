"""The paper's headline figure: edge accuracy does not buy contagion realism.

    python3 research/scripts/make_tradeoff_figure.py

Maximum entropy recovers every link in the true network and the graph VAE
recovers six percent of them, yet the VAE's crises are closer to the truth. If
the conventional criterion carried information about the behaviour these
networks are generated to study, that could not happen.

Double-column width, because it carries the argument and every point is labelled
directly rather than through a legend.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import figstyle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"

# Nudges so direct labels never sit on a point or a bar.
OFFSETS = {
    "observed": (6, 6),
    "vae": (7, -3),
    "max_entropy": (-7, 5),
    "configuration": (7, 4),
    "erdos_renyi": (7, 4),
}


def panel(ax, points, ylabel, title, log: bool = False) -> None:
    for label, x, y, key, lo, hi in points:
        style = figstyle.SERIES[key]
        ax.errorbar(
            x, y, yerr=[[max(y - lo, 0)], [max(hi - y, 0)]],
            fmt="none", ecolor=style["colour"], elinewidth=0.9, capsize=2, zorder=2,
        )
        ax.scatter(
            x, y, s=26, c=style["colour"], marker=style["marker"], zorder=3,
            edgecolors=figstyle.PAPER, linewidths=0.5,
        )
        dx, dy = OFFSETS[key]
        ax.annotate(
            label, (x, y), textcoords="offset points", xytext=(dx, dy),
            fontsize=figstyle.TICK_PT, color=figstyle.INK,
            ha="right" if dx < 0 else "left",
        )
    if log:
        ax.set_yscale("log")
    # Kept short: a longer label overflows a 3.45in panel and collides with the
    # neighbouring one. The full reading is in the caption.
    ax.set_xlabel("True links recovered (higher is better)")
    ax.set_ylabel(f"{ylabel} (lower is better)")
    ax.set_title(title, loc="left", pad=6)
    ax.set_xlim(-0.08, 1.14)
    figstyle.frame(ax, gridlines=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RESULTS / "figure_tradeoff.pdf")
    args = parser.parse_args()

    figstyle.apply()
    data = json.loads((RESULTS / "ensemble.json").read_text())

    contagion, structure = [], []
    for key, entry in data["methods"].items():
        recall = entry["edge_recall"]["mean"]
        contagion.append((entry["label"], recall, entry["protocol_score"]["mean"], key,
                          entry["protocol_score"]["lo"], entry["protocol_score"]["hi"]))
        structure.append((entry["label"], recall, entry["structure_score"]["mean"], key,
                          entry["structure_score"]["lo"], entry["structure_score"]["hi"]))

    fig, axes = plt.subplots(
        1, 2, figsize=(figstyle.DOUBLE_COLUMN, figstyle.DOUBLE_COLUMN * 0.42)
    )
    panel(axes[0], contagion, "Contagion error", "(a) Contagion realism")
    panel(axes[1], structure, "Structural error", "(b) Structural error", log=True)

    by_key = {key: (x, y) for _, x, y, key, _lo, _hi in contagion}
    vae_x, vae_y = by_key["vae"]
    dense_x, dense_y = by_key["max_entropy"]
    axes[0].annotate(
        "", xy=(dense_x, dense_y), xytext=(vae_x, vae_y),
        arrowprops=dict(arrowstyle="-", color=figstyle.STRESS, linewidth=0.8,
                        linestyle=(0, (3, 2))),
    )
    axes[0].text(
        (vae_x + dense_x) / 2, max(vae_y, dense_y) + 0.035,
        "16x apart on links recovered", fontsize=figstyle.TICK_PT,
        color=figstyle.STRESS, ha="center",
    )

    fig.tight_layout(pad=0.6)
    caption = (
        f"Edge-reconstruction accuracy, the conventional criterion, against contagion "
        "realism (a) and structural error (b, log scale). Higher on the horizontal axis "
        "is better by the conventional criterion; lower on the vertical axis is closer "
        "to the true system. "
        f"Seed {data['seed']}, {data['n_nodes']} banks, "
        f"{data['samples_requested']} samples per stochastic method; maximum entropy is "
        "deterministic and contributes one. Bars are 95% bootstrap intervals over "
        "samples. Contagion error is the mean relative gap over mean DebtRank, max "
        "DebtRank and mean cascade size. Structural error is the mean relative gap over "
        "density, degree assortativity, mean exposure size and mean equity ratio. "
        "Maximum entropy is given the true row and column totals, the configuration "
        "model the true degree sequence and weight multiset, and Erdos-Renyi the true "
        "density; the graph VAE is shown nothing about the target network."
    )
    for path in figstyle.save(fig, args.out, caption):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
