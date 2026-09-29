"""Measure the simulated ground truth against published stylized facts.

    python3 research/scripts/stylized_facts.py

This does not retune the generator. It reports what the simulated ground truth
looks like, so the paper can state which documented empirical regularities of
real interbank systems it reproduces.

**Every "published range" and "source" cell is written as the literal string
TODO-VERIFY and must be filled in by hand from verified publisher records.** A
wrong or invented citation is fatal at review, so nothing is guessed here.

Note also what cannot be claimed: BIS locational banking statistics report
aggregate cross-border claims between countries, not between banks. There is no
bank-level network in them, so no calibration to BIS data is possible or
claimed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation import degree_assortativity  # noqa: E402
from generators import Network  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research" / "results"
PLACEHOLDER = "TODO-VERIFY"


def hill_exponent(degrees: np.ndarray, tail_fraction: float = 0.25) -> float:
    """Hill estimator of the degree distribution's tail exponent.

    Uses the largest `tail_fraction` of degrees. A smaller exponent means a
    heavier tail, so a few banks have very many counterparties.
    """
    positive = np.sort(degrees[degrees > 0])[::-1]
    k = max(2, int(len(positive) * tail_fraction))
    top = positive[:k]
    threshold = positive[k - 1]
    if threshold <= 0:
        return float("nan")
    logs = np.log(top / threshold)
    mean_log = logs[logs > 0].mean() if (logs > 0).any() else np.nan
    return float(1.0 / mean_log) if mean_log and mean_log > 0 else float("nan")


def statistics(net: Network) -> dict[str, float]:
    binary = net.A > 0
    n = net.n
    degrees = (binary.sum(axis=0) + binary.sum(axis=1)).astype(float)
    core = net.core
    periphery = ~core

    core_to_core = binary[np.ix_(core, core)].sum()
    periphery_to_periphery = binary[np.ix_(periphery, periphery)].sum()
    edges = binary.sum()

    core_pairs = core.sum() * (core.sum() - 1)
    periphery_pairs = periphery.sum() * (periphery.sum() - 1)

    return {
        "edge_density": float(edges) / (n * (n - 1)),
        "core_fraction": float(core.sum()) / n,
        "degree_tail_exponent": hill_exponent(degrees),
        "degree_assortativity": degree_assortativity(net.A),
        "mean_degree": float(degrees.mean()),
        "max_degree": float(degrees.max()),
        # Tiering: a tiered system has a densely linked core and a periphery
        # that barely faces itself, dealing through the core instead.
        "core_internal_density": float(core_to_core) / core_pairs if core_pairs else 0.0,
        "periphery_internal_density": (
            float(periphery_to_periphery) / periphery_pairs if periphery_pairs else 0.0
        ),
        "share_of_links_touching_core": float(
            edges - periphery_to_periphery
        ) / float(edges) if edges else 0.0,
    }


ROWS: tuple[tuple[str, str, str], ...] = (
    ("edge_density", "Edge density", "{:.4f}"),
    ("core_fraction", "Core banks as a share of all banks", "{:.3f}"),
    ("degree_tail_exponent", "Degree tail exponent (Hill)", "{:.2f}"),
    ("degree_assortativity", "Degree assortativity", "{:+.3f}"),
    ("mean_degree", "Mean counterparties per bank", "{:.2f}"),
    ("max_degree", "Maximum counterparties for one bank", "{:.0f}"),
    ("core_internal_density", "Density within the core", "{:.3f}"),
    ("periphery_internal_density", "Density within the periphery", "{:.4f}"),
    ("share_of_links_touching_core", "Share of links touching the core", "{:.3f}"),
)


def markdown(values: dict[str, float]) -> str:
    lines = [
        "# Calibration against published stylized facts",
        "",
        "The system every method is measured against is simulated, not real. This table",
        "reports what it looks like, so the paper can state which documented empirical",
        "regularities of real interbank systems it reproduces.",
        "",
        "**Every cell marked `TODO-VERIFY` must be filled in by hand against a verified",
        "publisher record.** They are deliberately left empty: an invented or misremembered",
        "citation is fatal at review, and this project has already had AI-generated",
        "citations introduce errors once.",
        "",
        "No calibration to BIS locational banking statistics is possible or claimed. Those",
        "report aggregate cross-border claims between countries, not between banks, so they",
        "contain no bank-level network.",
        "",
        "| Statistic | Our value | Published range | Source | Inside the range? |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key, label, fmt in ROWS:
        lines.append(
            f"| {label} | {fmt.format(values[key])} | {PLACEHOLDER} | {PLACEHOLDER} | {PLACEHOLDER} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "calibration.md")
    args = parser.parse_args()

    cache = RESULTS / "networks.npz"
    if not cache.exists():
        raise SystemExit(f"{cache} not found. Run research/scripts/run_demo.py first.")
    cached = np.load(cache)
    observed = Network(
        A=cached["observed_A"],
        assets=cached["observed_assets"],
        equity=cached["observed_equity"],
        core=cached["observed_core"],
    )

    values = statistics(observed)
    payload: dict[str, Any] = {
        "statistics": values,
        "published_range": {key: PLACEHOLDER for key, _label, _fmt in ROWS},
        "source": {key: PLACEHOLDER for key, _label, _fmt in ROWS},
        "inside_range": {key: PLACEHOLDER for key, _label, _fmt in ROWS},
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "stylized_facts.json").write_text(json.dumps(payload, indent=1) + "\n")
    args.out.write_text(markdown(values))

    print(f"\n{'Statistic':<40}{'Our value':>12}")
    print("-" * 52)
    for key, label, fmt in ROWS:
        print(f"{label:<40}{fmt.format(values[key]):>12}")
    print(f"\nWrote {RESULTS / 'stylized_facts.json'}\nWrote {args.out}")
    print(f"\nEvery published range and source is left as {PLACEHOLDER}.")


if __name__ == "__main__":
    main()
