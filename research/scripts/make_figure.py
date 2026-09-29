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

import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import figstyle  # noqa: E402

INK = figstyle.INK
PAPER = figstyle.PAPER
OBSERVED = figstyle.SERIES["observed"]["colour"]
GENERATED = figstyle.SERIES["vae"]["colour"]
STRESS = figstyle.STRESS
RULE = figstyle.RULE

COLOUR = {"observed": OBSERVED, "generated": GENERATED}
MARKER = {"observed": figstyle.SERIES["observed"]["marker"], "generated": figstyle.SERIES["vae"]["marker"]}
DASH = {"observed": figstyle.SERIES["observed"]["dash"], "generated": figstyle.SERIES["vae"]["dash"]}
DATA_DIR = Path(__file__).resolve().parents[2] / "web" / "public" / "data"


def style_axes(ax: plt.Axes, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_facecolor(PAPER)
    ax.set_title(title, color=INK, loc="left", pad=5)
    ax.set_xlabel(xlabel, color=INK)
    ax.set_ylabel(ylabel, color=INK)
    for side, spine in ax.spines.items():
        spine.set_visible(side in ("bottom", "left"))
        spine.set_color(RULE)
    ax.grid(axis="y", color=RULE, linewidth=0.5)
    ax.set_axisbelow(True)


def draw_network(ax: plt.Axes, graph: dict[str, Any], series: str, title: str) -> None:
    """Nodes and edges at the coordinates Python already computed."""
    position = {node["id"]: (node["x"], node["y"]) for node in graph["nodes"]}
    max_weight = max((edge["w"] for edge in graph["edges"]), default=1.0)

    segments = [[position[edge["s"]], position[edge["t"]]] for edge in graph["edges"]]
    widths = [0.08 + 0.45 * np.sqrt(edge["w"] / max_weight) for edge in graph["edges"]]
    ax.add_collection(
        LineCollection(segments, linewidths=widths, colors=COLOUR[series], alpha=0.38)
    )

    xs = [node["x"] for node in graph["nodes"]]
    ys = [node["y"] for node in graph["nodes"]]
    sizes = [3 + 42 * node["assets"] for node in graph["nodes"]]
    ax.scatter(xs, ys, s=sizes, c=COLOUR[series], edgecolors=PAPER, linewidths=0.3, zorder=3)

    ax.set_title(title, color=COLOUR[series], loc="left", pad=5)
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
        label = "Simulated ground truth" if series == "observed" else "Our model"
        ax.stairs(values, bins, color=COLOUR[series], linewidth=1.1,
                  linestyle=DASH[series], label=label)
        ax.stairs(values, bins, color=COLOUR[series], fill=True, alpha=0.08)
    style_axes(ax, labels["xlabel"], "Number of banks", labels["title"])
    ax.legend(frameon=False, labelcolor=INK, handlelength=2.4, borderpad=0.2)


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

    figstyle.apply()
    fig, axes = plt.subplots(3, 2, figsize=(figstyle.DOUBLE_COLUMN, figstyle.DOUBLE_COLUMN * 1.18))
    fig.patch.set_facecolor(PAPER)

    draw_network(axes[0][0], networks["methods"]["observed"], "observed", "Simulated ground truth")
    draw_network(axes[0][1], networks["methods"]["vae"], "generated", "Our model")

    degree = metrics["degree_hist"]
    draw_histogram(
        axes[1][0],
        np.array(degree["bins"]),
        {
            "observed": np.array(degree["by_method"]["observed"]),
            "generated": np.array(degree["by_method"]["vae"]),
        },
        xlabel="Counterparties per bank",
        title="Counterparties per bank",
    )

    weight = metrics["weight_hist"]
    draw_histogram(
        axes[1][1],
        np.array(weight["bins"]),
        {
            "observed": np.array(weight["by_method"]["observed"]),
            "generated": np.array(weight["by_method"]["vae"]),
        },
        xlabel="Size of a single debt (log10)",
        title="Individual exposure sizes",
    )

    edges, counts = shared_histogram(
        contagion["by_method"]["observed"]["debtrank"],
        contagion["by_method"]["vae"]["debtrank"],
        12,
    )
    draw_histogram(
        axes[2][0],
        edges,
        counts,
        xlabel="Share of system value at risk from one bank",
        title="DebtRank, every bank shocked in turn",
    )

    ax = axes[2][1]
    shocks = np.array(contagion["shock"])
    for series, key in (("observed", "observed"), ("generated", "vae")):
        band = contagion["by_method"][key]["cascade"]
        ax.fill_between(shocks, band["lo"], band["hi"], color=COLOUR[series], alpha=0.18, linewidth=0)
        label = "Simulated ground truth" if series == "observed" else "Our model"
        ax.plot(shocks, band["mean"], color=COLOUR[series], linewidth=1.2,
                linestyle=DASH[series], marker=MARKER[series], label=label)
    # Deep red means one thing in this project: a bank has defaulted.
    ax.axhline(0.5, color=STRESS, linewidth=0.8, linestyle=(0, (3, 3)), alpha=0.85)
    ax.text(shocks[-1], 0.52, "half the system has failed", color=STRESS,
            fontsize=figstyle.TICK_PT, ha="right")
    # Fixed across every figure showing this quantity.
    ax.set_ylim(0, 1)
    style_axes(ax, "Share of outside assets destroyed", "Share of banks that default",
               "How far a crisis travels")
    ax.legend(frameon=False, labelcolor=INK, loc="lower right", handlelength=2.4, borderpad=0.2)

    fig.tight_layout(pad=0.7)
    caption = (
        f"The simulated ground truth against the graph VAE. {networks['n_nodes']} banks, "
        "one seeded sample. Top: both systems drawn on the same "
        "layout, so a bank in the same position is the comparable bank. Middle: "
        "counterparties per bank and individual exposure sizes; bin edges span every "
        "method in the study, so the horizontal range is wider than these two systems "
        "use. Bottom: DebtRank with "
        "every bank shocked in turn, and the share of banks defaulting as the shock "
        "grows, with 10th-90th percentile bands over 20 repeats."
    )
    out = args.out.with_suffix(".pdf")
    for path in figstyle.save(fig, out, caption):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
