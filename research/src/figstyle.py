"""Publication figure settings.

Print figures have different constraints from screen figures. They are viewed at
about 3.3 inches wide in a two-column layout, may be printed in greyscale, and
have no hover to lean on. Everything here exists to survive that.

Type sizes are absolute: setting the figure size explicitly and never letting
`bbox_inches="tight"` rescale means 8pt here is 8pt on the page.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

# Column widths in inches, from a standard two-column conference template.
SINGLE_COLUMN = 3.3
DOUBLE_COLUMN = 6.9

INK = "#10192b"
PAPER = "#ffffff"  # White for print; the page's off-white is a screen choice.
RULE = "#d6d8d3"
STRESS = "#a3302b"
OBSERVED = "#2e5e8c"

# Colour, marker and dash together, so every series survives greyscale.
SERIES = {
    "observed": {"colour": OBSERVED, "marker": "o", "dash": "-"},
    "vae": {"colour": "#c8842a", "marker": "s", "dash": (0, (4, 1.5))},
    "max_entropy": {"colour": "#4a4f58", "marker": "^", "dash": (0, (1, 1.2))},
    "configuration": {"colour": "#7c828c", "marker": "D", "dash": (0, (5, 1, 1, 1))},
    "erdos_renyi": {"colour": "#9ba1aa", "marker": "v", "dash": (0, (2, 2))},
}

TICK_PT = 7
LABEL_PT = 8
AXIS_TITLE_PT = 9


def apply() -> None:
    """One sans family and fixed point sizes throughout."""
    matplotlib.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": LABEL_PT,
        "axes.labelsize": AXIS_TITLE_PT,
        "axes.titlesize": AXIS_TITLE_PT,
        "xtick.labelsize": TICK_PT,
        "ytick.labelsize": TICK_PT,
        "legend.fontsize": TICK_PT,
        "axes.edgecolor": RULE,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.2,
        "lines.markersize": 3.2,
        "pdf.fonttype": 42,  # Embed TrueType, not Type 3: required by most venues.
        "ps.fonttype": 42,
    })


def frame(ax: plt.Axes, gridlines: bool = False) -> None:
    """Hairline gridlines only where a value must be read off the axis."""
    if gridlines:
        ax.grid(color=RULE, linewidth=0.5, alpha=0.9)
        ax.set_axisbelow(True)
    else:
        ax.grid(False)


def save(fig: plt.Figure, out: Path, caption: str) -> list[Path]:
    """Write the vector PDF, a PNG, a caption sidecar and a greyscale proof.

    The greyscale copy is not decoration. Five series that look distinct in
    colour routinely collapse to three in print, and that is the kind of thing
    noticed in the version of record rather than the draft.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)  # No bbox_inches: the figure size is the page size.
    png = out.with_suffix(".png")
    fig.savefig(png, dpi=400)
    out.with_suffix(".txt").write_text(caption.strip() + "\n")

    proof = out.parent / "greyscale_check" / png.name
    proof.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        Image.open(png).convert("L").save(proof)
    except ImportError:  # pragma: no cover - Pillow is optional
        proof = None

    written = [out, png, out.with_suffix(".txt")]
    if proof is not None:
        written.append(proof)
    return written
