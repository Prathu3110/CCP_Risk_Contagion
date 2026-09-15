"""Render the page's six panels as one static figure for the paper.

    python research/scripts/make_figure.py [--out research/results/figure1.png]

Reads the JSON the pipeline already wrote, so this needs no retraining and
always matches whatever is on the page. Colour carries the same meaning here as
it does there: ink blue is observed, amber is generated, and deep red appears
only where a bank has defaulted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

INK = "#10192b"
PAPER = "#f5f6f4"
OBSERVED = "#2e5e8c"
GENERATED = "#c8842a"
STRESS = "#a3302b"
RULE = "#d6d8d3"

COLOUR = {"observed": OBSERVED, "generated": GENERATED}
DATA_DIR = Path(__file__).resolve().parents[2] / "web" / "public" / "data"


def style_axes(ax: plt.Axes, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_facecolor(PAPER)
    ax.set_title(title, color=INK, fontsize=11, loc="left", pad=10)
    ax.set_xlabel(xlabel, color=INK, fontsize=9)
    ax.set_ylabel(ylabel, color=INK, fontsize=9)
    ax.tick_params(colors=INK, labelsize=8, length=3)
    for side, spine in ax.spines.items():
        spine.set_visible(side == "bottom")
        spine.set_color(RULE)
    ax.grid(axis="y", color=RULE, linewidth=0.7)
    ax.set_axisbelow(True)


def draw_network(ax: plt.Axes, graph: dict[str, Any], series: str, title: str) -> None:
    """Nodes and edges at the coordinates Python already computed."""
    position = {node["id"]: (node["x"], node["y"]) for node in graph["nodes"]}
    max_weight = max((edge["w"] for edge in graph["edges"]), default=1.0)

    segments = [[position[edge["s"]], position[edge["t"]]] for edge in graph["edges"]]
    widths = [0.15 + 0.9 * np.sqrt(edge["w"] / max_weight) for edge in graph["edges"]]
    ax.add_collection(
        LineCollection(segments, linewidths=widths, colors=COLOUR[series], alpha=0.38)
    )

    xs = [node["x"] for node in graph["nodes"]]
    ys = [node["y"] for node in graph["nodes"]]
    sizes = [8 + 150 * node["assets"] for node in graph["nodes"]]
    ax.scatter(xs, ys, s=sizes, c=COLOUR[series], edgecolors=PAPER, linewidths=0.6, zorder=3)

    ax.set_title(title, color=COLOUR[series], fontsize=11, loc="left", pad=10)
    ax.set_xlim(-0.04, 1.04)
    # Inverted, so the drawing matches the web page's coordinate system.
    ax.set_ylim(1.04, -0.04)
    ax.set_aspect("equal")
    ax.set_facecolor(PAPER)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def draw_histogram(ax: plt.Axes, bins: np.ndarray, counts: dict[str, np.ndarray], **labels: str) -> None:
    for series, values in counts.items():
        ax.stairs(values, bins, color=COLOUR[series], linewidth=1.8, label=series.capitalize())
        ax.stairs(values, bins, color=COLOUR[series], fill=True, alpha=0.08)
    style_axes(ax, labels["xlabel"], "Number of banks", labels["title"])
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)


def shared_histogram(observed: list[float], generated: list[float], bins: int):
    edges = np.histogram_bin_edges(np.concatenate([observed, generated]), bins=bins)
    return edges, {
        "observed": np.histogram(observed, bins=edges)[0],
        "generated": np.histogram(generated, bins=edges)[0],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_out = Path(__file__).resolve().parents[1] / "results" / "figure1.png"
    parser.add_argument("--out", type=Path, default=default_out)
    args = parser.parse_args()

    networks = json.loads((DATA_DIR / "networks.json").read_text())
    metrics = json.loads((DATA_DIR / "metrics.json").read_text())
    contagion = json.loads((DATA_DIR / "contagion.json").read_text())

    fig, axes = plt.subplots(3, 2, figsize=(10.5, 13.5))
    fig.patch.set_facecolor(PAPER)

    draw_network(axes[0][0], networks["observed"], "observed", "Observed system")
    draw_network(axes[0][1], networks["generated"], "generated", "Generated system")

    degree = metrics["degree_hist"]
    draw_histogram(
        axes[1][0],
        np.array(degree["bins"]),
        {"observed": np.array(degree["observed"]), "generated": np.array(degree["generated"])},
        xlabel="Counterparties per bank",
        title="Counterparties per bank",
    )

    weight = metrics["weight_hist"]
    draw_histogram(
        axes[1][1],
        np.array(weight["bins"]),
        {"observed": np.array(weight["observed"]), "generated": np.array(weight["generated"])},
        xlabel="Size of a single debt (log10)",
        title="Individual exposure sizes",
    )

    edges, counts = shared_histogram(
        contagion["debtrank"]["observed"], contagion["debtrank"]["generated"], 12
    )
    draw_histogram(
        axes[2][0],
        edges,
        counts,
        xlabel="Share of system value at risk from one bank",
        title="DebtRank, every bank shocked in turn",
    )

    cascade = contagion["cascade"]
    ax = axes[2][1]
    shocks = np.array(cascade["shock"])
    for series in ("observed", "generated"):
        band = cascade[series]
        ax.fill_between(shocks, band["lo"], band["hi"], color=COLOUR[series], alpha=0.18, linewidth=0)
        ax.plot(shocks, band["mean"], color=COLOUR[series], linewidth=2, marker="o",
                markersize=3.5, label=series.capitalize())
    # Deep red means one thing in this project: a bank has defaulted.
    ax.axhline(0.5, color=STRESS, linewidth=1, linestyle=(0, (3, 3)), alpha=0.8)
    ax.text(shocks[-1], 0.52, "half the system has failed", color=STRESS, fontsize=8, ha="right")
    ax.set_ylim(0, 1)
    style_axes(ax, "Share of outside assets destroyed", "Share of banks that default",
               "How far a crisis travels")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="lower right")

    fig.tight_layout(pad=2.4)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=300, facecolor=PAPER)
    vector = args.out.with_suffix(".pdf")
    fig.savefig(vector, facecolor=PAPER)
    print(f"Wrote {args.out}\nWrote {vector}")


if __name__ == "__main__":
    main()
