"use client";

import { useState } from "react";

import NetworkPlot from "@/components/NetworkPlot";
import type { Networks } from "@/lib/types";

/**
 * The two drawings, sharing one hover state.
 *
 * Both networks are laid out on the same grid of positions, assigned by how
 * many counterparties a bank has. Pointing at a bank in either drawing
 * therefore highlights the comparable bank in both, which is the whole point:
 * you are meant to compare who deals with whom, not node numbering.
 */
export default function NetworkPair({ networks }: { networks: Networks }) {
  const [hoveredSlot, setHoveredSlot] = useState<number | null>(null);

  return (
    <div>
      <div className="grid gap-x-10 gap-y-8 sm:grid-cols-2">
        <figure className="m-0">
          <NetworkPlot
            graph={networks.observed}
            series="observed"
            name="observed system"
            revealStartMs={120}
            hoveredSlot={hoveredSlot}
            onHoverSlot={setHoveredSlot}
          />
          <figcaption className="mt-3 text-observed">
            Observed system, standing in for supervisory data
          </figcaption>
        </figure>

        <figure className="m-0">
          <NetworkPlot
            graph={networks.generated}
            series="generated"
            name="generated system"
            revealStartMs={820}
            hoveredSlot={hoveredSlot}
            onHoverSlot={setHoveredSlot}
          />
          <figcaption className="mt-3 text-generated">
            Generated system, invented by the model
          </figcaption>
        </figure>
      </div>

      <p className="mt-6 text-sm text-ink/60 min-h-6" aria-live="polite">
        {hoveredSlot === null
          ? "Point at any bank to light up everyone it deals with, in both systems at once."
          : `Showing the ${hoveredSlot === 0 ? "busiest" : `${ordinal(hoveredSlot + 1)} busiest`} bank in each system, and every counterparty it owes or is owed by.`}
      </p>
    </div>
  );
}

function ordinal(value: number): string {
  const tens = value % 100;
  if (tens >= 11 && tens <= 13) return `${value}th`;
  const suffix = { 1: "st", 2: "nd", 3: "rd" }[value % 10] ?? "th";
  return `${value}${suffix}`;
}
