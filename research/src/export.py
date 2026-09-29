"""Builds the three JSON files the web app reads.

The schema is mirrored by `web/lib/types.ts`. Python and the web app never talk
at runtime: this module writes static files and exits.

The contract carries every method, not a hardcoded observed/generated pair, so
adding a sixth needs only a new entry. `role` drives colour in the page -
`observed` is ink blue, `ours` amber, `baseline` the grey ramp - and a colour is
never keyed to a method name.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from generators import Network, balance_sheet
from layout import total_degree


def _round(value: float, places: int = 4) -> float:
    return float(np.round(float(value), places))


def network_payload(net: Network, positions: np.ndarray) -> dict[str, Any]:
    """Nodes with normalised coordinates, and edges as source/target/weight.

    `slot` is a bank's rank by number of counterparties, 0 being the busiest.
    The two networks are laid out so that equal slots occupy the same point on
    screen, which is what lets the page highlight the comparable bank in both
    drawings at once. Node ids cannot do that job: id 7 in a system the model
    invented has nothing to do with id 7 in the observed one.

    `assets` is normalised against the largest bank, because it only sets how
    big a dot is drawn. The balance-sheet fields that follow it are raw, since
    the page re-runs the contagion models on them and a crisis is not
    scale-invariant.
    """
    assets = net.assets / net.assets.max() if net.assets.max() > 0 else net.assets
    ext_assets, ext_liabilities = balance_sheet(net)
    slots = np.empty(net.n, dtype=int)
    slots[np.argsort(-total_degree(net.A), kind="stable")] = np.arange(net.n)
    nodes = [
        {
            "id": int(i),
            "slot": int(slots[i]),
            "x": _round(positions[i, 0]),
            "y": _round(positions[i, 1]),
            "assets": _round(assets[i]),
            "core": bool(net.core[i]),
            "equity": _round(net.equity[i], 8),
            "ext_assets": _round(ext_assets[i], 8),
            "ext_liabilities": _round(ext_liabilities[i], 8),
        }
        for i in range(net.n)
    ]
    sources, targets = np.nonzero(net.A)
    # Eight decimals, not five: the browser re-runs the clearing algorithm on
    # these numbers and coarse rounding moves the default count.
    edges = [
        {"s": int(s), "t": int(t), "w": _round(net.A[s, t], 8)}
        for s, t in zip(sources, targets)
    ]
    return {"nodes": nodes, "edges": edges}


def multi_histogram(
    series: dict[str, np.ndarray], bins: int
) -> dict[str, Any]:
    """One set of bin edges shared by every method, so the curves are comparable."""
    combined = np.concatenate([values for values in series.values() if len(values)])
    edges = np.histogram_bin_edges(combined, bins=bins)
    return {
        "bins": [_round(edge) for edge in edges],
        "by_method": {
            key: [int(count) for count in np.histogram(values, bins=edges)[0]]
            for key, values in series.items()
        },
    }


def shared_histogram(
    observed: np.ndarray, generated: np.ndarray, bins: int
) -> dict[str, list[float]]:
    """One set of bin edges for both series, so the curves are comparable."""
    combined = np.concatenate([observed, generated])
    edges = np.histogram_bin_edges(combined, bins=bins)
    observed_counts, _ = np.histogram(observed, bins=edges)
    generated_counts, _ = np.histogram(generated, bins=edges)
    return {
        "bins": [_round(e) for e in edges],
        "observed": [int(c) for c in observed_counts],
        "generated": [int(c) for c in generated_counts],
    }


def summary_row(name: str, observed: float, generated: float) -> dict[str, Any]:
    """One line of the numbers table, with the gap as a percentage of observed."""
    gap = abs(generated - observed) / abs(observed) * 100.0 if observed else 0.0
    return {
        "name": name,
        "observed": _round(observed, 4),
        "generated": _round(generated, 4),
        "gap_pct": _round(gap, 1),
    }


def summarise(observed: Network, generated: Network) -> list[dict[str, Any]]:
    """The statistics a reader should check before believing the stress results."""
    rows: list[dict[str, Any]] = []
    for label, extract in (
        ("Mean degree", lambda net: total_degree(net.A).mean()),
        ("Max degree", lambda net: total_degree(net.A).max()),
        ("Edge count", lambda net: float((net.A > 0).sum())),
        ("Density", lambda net: float((net.A > 0).sum()) / (net.n * (net.n - 1))),
        ("Mean exposure", lambda net: float(net.A[net.A > 0].mean()) if (net.A > 0).any() else 0.0),
        ("Total exposure", lambda net: float(net.A.sum())),
        ("Degree assortativity", lambda net: _assortativity(net.A)),
        ("Mean equity ratio", lambda net: float((net.equity / net.assets).mean())),
    ):
        rows.append(summary_row(label, extract(observed), extract(generated)))
    return rows


def _assortativity(A: np.ndarray) -> float:
    """Pearson correlation of degrees across connected pairs; negative for hubs."""
    degree = total_degree(A)
    sources, targets = np.nonzero(A)
    if len(sources) < 2:
        return 0.0
    left, right = degree[sources], degree[targets]
    if left.std() < 1e-12 or right.std() < 1e-12:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def band(samples: Iterable[np.ndarray]) -> dict[str, list[float]]:
    """Mean and a 10th-90th percentile band across repeats, per shock level."""
    stacked = np.asarray(list(samples), dtype=float)
    return {
        "mean": [_round(v) for v in stacked.mean(axis=1)],
        "lo": [_round(v) for v in np.percentile(stacked, 10, axis=1)],
        "hi": [_round(v) for v in np.percentile(stacked, 90, axis=1)],
    }


def method_payload(
    key: str, label: str, role: str, net: Network, positions: np.ndarray
) -> dict[str, Any]:
    """One method's drawing, tagged with what it is so the page can colour it."""
    payload = network_payload(net, positions)
    payload.update({"key": key, "label": label, "role": role})
    return payload


def write_all(out_dir: Path, networks: dict, metrics: dict, contagion: dict) -> list[Path]:
    """Write the three files, creating the directory if the web app is not set up yet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, payload in (
        ("networks.json", networks),
        ("metrics.json", metrics),
        ("contagion.json", contagion),
    ):
        path = out_dir / name
        path.write_text(json.dumps(payload, indent=1) + "\n")
        written.append(path)
    return written
