"""Cascade curves for every method, with bootstrap bands across the ensemble.

    python3 research/scripts/make_ensemble_figure.py

Single-column width. The vertical axis is fixed to 0-1 here and in the
six-panel figure, so the two can be compared directly.
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RESULTS / "figure_ensemble.pdf")
    args = parser.parse_args()

    figstyle.apply()
    data = json.loads((RESULTS / "test.json").read_text())
    shocks = data["shock"]

    fig, ax = plt.subplots(figsize=(figstyle.SINGLE_COLUMN, figstyle.SINGLE_COLUMN * 0.78))

    truth = figstyle.SERIES["observed"]
    ax.plot(shocks, data["observed_cascade"], color=truth["colour"], linewidth=1.5,
            linestyle=truth["dash"], marker=truth["marker"], label="Simulated ground truth",
            zorder=4)

    for key, entry in data["methods"].items():
        style = figstyle.SERIES[key]
        curve = entry["cascade_curve"]
        ax.fill_between(shocks, curve["lo"], curve["hi"], color=style["colour"],
                        alpha=0.16, linewidth=0)
        ax.plot(shocks, curve["mean"], color=style["colour"], linewidth=1.1,
                linestyle=style["dash"], marker=style["marker"], label=entry["label"])

    ax.set_xlabel("Outside assets destroyed")
    ax.set_ylabel("Banks that default")
    # Fixed across every figure showing this quantity.
    ax.set_ylim(0, 1)
    ax.set_xlim(min(shocks), max(shocks))
    figstyle.frame(ax, gridlines=True)
    # The five curves converge, so direct labels at the line ends would overlap.
    # A compact legend is the honest choice here.
    ax.legend(frameon=False, loc="lower right", handlelength=2.6, borderpad=0.2,
              labelspacing=0.25)

    fig.tight_layout(pad=0.5)
    caption = (
        f"Share of banks defaulting as the shock grows, for the simulated ground truth "
        f"and each method. Seed {data['seed']}, {data['n_nodes']} banks, "
        f"{data['samples_requested']} samples per stochastic method; maximum entropy is "
        "deterministic and has no band. Shaded bands are 95% bootstrap intervals across "
        "samples. Every method meets the same sequence of random shock spreads. All "
        "methods track the truth closely on this measure: cascade size is not what "
        "separates them."
    )
    for path in figstyle.save(fig, args.out, caption):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
