"""Prints the reference numbers that web/scripts/verify-contagion.ts must match."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import json  # noqa: E402

from contagion import cascade_size, debtrank  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "web" / "public" / "data" / "networks.json"


def main() -> None:
    payload = json.loads(DATA.read_text())
    n = payload["n_nodes"]

    for series in ("observed", "generated"):
        graph = payload[series]
        A = np.zeros((n, n))
        for edge in graph["edges"]:
            A[edge["s"], edge["t"]] = edge["w"]
        order = sorted(graph["nodes"], key=lambda node: node["id"])
        equity = np.array([node["equity"] for node in order])
        ext_assets = np.array([node["ext_assets"] for node in order])
        ext_liabilities = np.array([node["ext_liabilities"] for node in order])

        cascade = [
            f"{cascade_size(A, ext_assets, shock, ext_liabilities):.6f}"
            for shock in np.arange(0.05, 0.501, 0.05)
        ]
        scores = np.array([debtrank(A, equity, i, 0.5) for i in range(n)])
        print(f"{series} cascade {' '.join(cascade)}")
        print(f"{series} debtrank mean {scores.mean():.6f} max {scores.max():.6f}")


if __name__ == "__main__":
    main()
