"use client";

import { useCallback, useMemo, useRef } from "react";
import type { CSSProperties, KeyboardEvent } from "react";

import type { NetworkGraph } from "@/lib/types";

/** Positions arrive normalised 0-1; the drawing is a unit square scaled up. */
const VIEW = 100;
/** How long the whole edge reveal takes for one network. */
const REVEAL_MS = 800;

/** Amber carries less contrast against paper than ink blue does, so matching
    opacities numerically would make the amber network look sparser than it is.
    These are matched by eye, not by value. A near-complete network such as
    maximum entropy's needs a far lower value again, or it renders as a solid
    block; the caller passes that in. */
export const RESTING_EDGE = { observed: 0.34, accented: 0.42, dense: 0.08 };

type Props = {
  graph: NetworkGraph;
  /** Resolved colour for this method, from `lib/methods.ts`. */
  colour: string;
  /** Resting opacity for edges, lowered for near-complete networks. */
  edgeOpacity?: number;
  /** Used for the accessible name, e.g. "observed system". */
  name: string;
  /** Offset into the page's one reveal, so the two networks draw in sequence. */
  revealStartMs: number;
  hoveredSlot: number | null;
  onHoverSlot: (slot: number | null) => void;
  /** Ids of banks that have defaulted. Deep red means only this. */
  failed?: ReadonlySet<number>;
  /** Ids that defaulted in the round just shown, ringed to draw the eye. */
  justFailed?: ReadonlySet<number>;
  /** Off for the simulator, whose drawings are already on screen. */
  animate?: boolean;
  /** Bank singled out to be wiped out, marked before the run starts. */
  selected?: number | null;
  onSelect?: (nodeId: number) => void;
};

const vars = (values: Record<string, string | number>) => values as CSSProperties;

export default function NetworkPlot({
  graph,
  colour,
  edgeOpacity = RESTING_EDGE.observed,
  name,
  revealStartMs,
  hoveredSlot,
  onHoverSlot,
  failed,
  justFailed,
  animate = true,
  selected = null,
  onSelect,
}: Props) {
  const nodeRefs = useRef(new Map<number, SVGCircleElement>());

  const { nodes, edges, bySlot, degrees } = useMemo(() => {
    const byId = new Map(graph.nodes.map((node) => [node.id, node]));
    const bySlot = new Map(graph.nodes.map((node) => [node.slot, node]));

    const degrees = new Map<number, number>(graph.nodes.map((node) => [node.id, 0]));
    for (const edge of graph.edges) {
      degrees.set(edge.s, (degrees.get(edge.s) ?? 0) + 1);
      degrees.set(edge.t, (degrees.get(edge.t) ?? 0) + 1);
    }

    const maxWeight = graph.edges.reduce((max, edge) => Math.max(max, edge.w), 0) || 1;

    // Draw the busiest banks' edges first, so the core forms and the periphery
    // then attaches to it rather than the whole picture arriving at once.
    const edges = graph.edges
      .map((edge) => {
        const source = byId.get(edge.s)!;
        const target = byId.get(edge.t)!;
        const x1 = source.x * VIEW;
        const y1 = source.y * VIEW;
        const x2 = target.x * VIEW;
        const y2 = target.y * VIEW;
        return {
          ...edge,
          x1,
          y1,
          x2,
          y2,
          length: Math.hypot(x2 - x1, y2 - y1),
          width: 0.07 + 0.45 * Math.sqrt(edge.w / maxWeight),
          rank: Math.min(source.slot, target.slot),
        };
      })
      .sort((a, b) => a.rank - b.rank);

    return { nodes: graph.nodes, edges, bySlot, degrees };
  }, [graph]);

  const focus = hoveredSlot === null ? null : (bySlot.get(hoveredSlot) ?? null);

  const neighbours = useMemo(() => {
    if (!focus) return null;
    const ids = new Set<number>();
    for (const edge of edges) {
      if (edge.s === focus.id) ids.add(edge.t);
      else if (edge.t === focus.id) ids.add(edge.s);
    }
    return ids;
  }, [edges, focus]);

  const rovingSlot = hoveredSlot ?? 0;

  const moveTo = useCallback(
    (slot: number) => {
      const clamped = Math.max(0, Math.min(nodes.length - 1, slot));
      onHoverSlot(clamped);
      nodeRefs.current.get(clamped)?.focus();
    },
    [nodes.length, onHoverSlot],
  );

  const onKeyDown = useCallback(
    (event: KeyboardEvent<SVGGElement>) => {
      const steps: Record<string, number> = {
        ArrowRight: 1,
        ArrowDown: 1,
        ArrowLeft: -1,
        ArrowUp: -1,
      };
      if (event.key in steps) {
        event.preventDefault();
        moveTo(rovingSlot + steps[event.key]);
      } else if (event.key === "Home") {
        event.preventDefault();
        moveTo(0);
      } else if (event.key === "End") {
        event.preventDefault();
        moveTo(nodes.length - 1);
      } else if (event.key === "Escape") {
        onHoverSlot(null);
      }
    },
    [moveTo, nodes.length, onHoverSlot, rovingSlot],
  );

  return (
    <svg
      viewBox={`0 0 ${VIEW} ${VIEW}`}
      className="w-full h-auto overflow-visible"
      onMouseLeave={() => onHoverSlot(null)}
    >
      <g fill="none" strokeLinecap="round">
        {edges.map((edge, index) => {
          const touched = focus !== null && (edge.s === focus.id || edge.t === focus.id);
          // The debtor has failed, so this is money that will not be repaid.
          const defaulted = failed?.has(edge.s) ?? false;
          return (
            <line
              key={`${edge.s}-${edge.t}`}
              className={animate ? "edge" : undefined}
              x1={edge.x1}
              y1={edge.y1}
              x2={edge.x2}
              y2={edge.y2}
              stroke={defaulted ? "var(--color-stress)" : colour}
              strokeWidth={edge.width}
              opacity={
                focus !== null && !touched
                  ? 0.05
                  : defaulted
                    ? 0.72
                    : focus !== null
                      ? 0.95
                      : edgeOpacity
              }
              style={vars({
                "--len": edge.length,
                "--delay": `${revealStartMs + (index / edges.length) * REVEAL_MS}ms`,
              })}
            />
          );
        })}
      </g>

      <g
        role="listbox"
        aria-label={`Banks in the ${name}`}
        tabIndex={-1}
        onKeyDown={onKeyDown}
      >
        {nodes.map((node) => {
          const radius = 0.9 + 2.1 * Math.sqrt(node.assets);
          const isFocus = focus?.id === node.id;
          const isNeighbour = neighbours?.has(node.id) ?? false;
          const dimmed = focus !== null && !isFocus && !isNeighbour;
          const counterparties = degrees.get(node.id) ?? 0;
          const hasFailed = failed?.has(node.id) ?? false;
          const fill = hasFailed ? "var(--color-stress)" : colour;

          return (
            <g
              key={node.id}
              className={animate ? "node-reveal" : undefined}
              style={vars({ "--delay": `${revealStartMs + REVEAL_MS * 0.35}ms` })}
              opacity={dimmed ? 0.12 : 1}
            >
              {isFocus && (
                <circle
                  cx={node.x * VIEW}
                  cy={node.y * VIEW}
                  r={radius + 1.6}
                  fill="none"
                  stroke="var(--color-ink)"
                  strokeWidth={0.5}
                />
              )}
              {selected === node.id && !hasFailed && (
                <circle
                  cx={node.x * VIEW}
                  cy={node.y * VIEW}
                  r={radius + 2.2}
                  fill="none"
                  stroke="var(--color-stress)"
                  strokeWidth={0.6}
                  strokeDasharray="1.4 1.2"
                />
              )}
              {justFailed?.has(node.id) && (
                <circle
                  cx={node.x * VIEW}
                  cy={node.y * VIEW}
                  r={radius + 2.2}
                  fill="none"
                  stroke="var(--color-stress)"
                  strokeWidth={0.6}
                  opacity={0.9}
                />
              )}
              {/* Opaque backing, so the edges running underneath a bank do not
                  show through it and make the dot look hollow. */}
              <circle
                cx={node.x * VIEW}
                cy={node.y * VIEW}
                r={radius}
                fill="var(--color-paper)"
              />
              <circle
                cx={node.x * VIEW}
                cy={node.y * VIEW}
                r={radius}
                fill={fill}
                fillOpacity={hasFailed || node.core ? 1 : 0.85}
                stroke="var(--color-paper)"
                strokeWidth={0.3}
              />
              {/* Separate, invisible hit area. The drawn dots carry the size of
                  the bank and several are far too small to point at. */}
              <circle
                ref={(element) => {
                  if (element) nodeRefs.current.set(node.slot, element);
                  else nodeRefs.current.delete(node.slot);
                }}
                role="option"
                aria-selected={isFocus}
                aria-label={`Bank ${node.id}, ${counterparties} counterparties`}
                tabIndex={node.slot === rovingSlot ? 0 : -1}
                cx={node.x * VIEW}
                cy={node.y * VIEW}
                r={Math.max(radius + 1.1, 2.6)}
                fill="transparent"
                onMouseEnter={() => onHoverSlot(node.slot)}
                onFocus={() => onHoverSlot(node.slot)}
                onClick={onSelect ? () => onSelect(node.id) : undefined}
                className="cursor-pointer"
              />
            </g>
          );
        })}
      </g>
    </svg>
  );
}
