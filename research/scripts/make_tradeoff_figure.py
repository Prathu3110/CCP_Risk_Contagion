"""The paper's headline figure: do the two criteria disagree?

    python3 research/scripts/make_tradeoff_figure.py

Left panel is the protocol as specified: edge F1 against the full protocol
score. Right panel is a diagnostic, because F1 and the full protocol score both
turned out to hide the effect the paper is about. F1 punishes maximum entropy
for its density even though it recovers every true edge, and the full protocol
score is dominated by structural gaps rather than contagion ones. The right
panel therefore plots edge recall against a contagion-only score.

Colours follow docs/WEB-PLAN.md section 1: amber is our model, the baselines are
a deliberately unaccented grey ramp ordered by how much structure they preserve.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

INK = "#10192b"
PAPER = "#f5f6f4"
RULE = "#d6d8d3"

STYLE = {
    "vae": ("#c8842a", "o"),
    "max_entropy": ("#4a4f58", "s"),
    "configuration": ("#7c828c", "^"),
    "erdos_renyi": ("#9ba1aa", "D"),
}
CONTAGION_METRICS = ("mean_debtrank", "max_debtrank", "mean_cascade_size")

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"


def panel(ax: plt.Axes, points: list[tuple], xlabel: str, ylabel: str, title: str) -> None:
    for label, x, y, key in points:
        colour, marker = STYLE[key]
        ax.scatter(x, y, s=70, c=colour, marker=marker, zorder=3, edgecolors=PAPER, linewidths=0.8)
        ax.annotate(
            label,
            (x, y),
            textcoords="offset points",
            xytext=(8, 5),
            fontsize=8,
            color=INK,
        )
    ax.set_xlabel(f"{xlabel}\n(right = better by the conventional criterion)", fontsize=9, color=INK)
    ax.set_ylabel(f"{ylabel}\n(down = better contagion realism)", fontsize=9, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left", pad=10)
    ax.set_facecolor(PAPER)
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
    specified: list[tuple] = []
    diagnostic: list[tuple] = []
    for key, entry in data["methods"].items():
        label = entry["label"]
        reconstruction = entry["reconstruction"]
        gaps = entry["behavioural"]["gaps"]
        specified.append((label, reconstruction["edge_f1"], entry["behavioural"]["protocol_score"], key))
        contagion_only = float(np.mean([gaps[name] for name in CONTAGION_METRICS]))
        diagnostic.append((label, reconstruction["edge_recall"], contagion_only, key))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    fig.patch.set_facecolor(PAPER)
    panel(axes[0], specified, "Edge F1", "Protocol score", "As specified: edge F1 against the full protocol score")
    panel(
        axes[1],
        diagnostic,
        "Edge recall",
        "Contagion-only score",
        "Diagnostic: recall against contagion metrics alone",
    )

    fig.tight_layout(pad=2.0)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, facecolor=PAPER)
    png = args.out.with_suffix(".png")
    fig.savefig(png, dpi=200, facecolor=PAPER)

    caption = (
        f"Reconstruction accuracy against contagion realism, seed {data['seed']}, "
        f"{data['n_nodes']} banks, one sample per method. Left panel uses the metrics "
        "named in the execution plan. Right panel replaces edge F1 with recall and "
        "restricts the vertical axis to the three contagion metrics.\n"
    )
    args.out.with_suffix(".txt").write_text(caption)
    print(f"Wrote {args.out}\nWrote {png}\nWrote {args.out.with_suffix('.txt')}")


if __name__ == "__main__":
    main()
