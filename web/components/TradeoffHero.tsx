"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { scaleLinear } from "d3-scale";

import NetworkPlot, { RESTING_EDGE } from "@/components/NetworkPlot";
import { methodColours } from "@/lib/methods";
import type { Evaluation, MethodKey, Networks } from "@/lib/types";

const WIDTH = 560;
const HEIGHT = 380;
const MARGIN = { top: 26, right: 26, bottom: 58, left: 62 };

/** Above this density a network is drawn as a near-solid block, so it is
    faded rather than re-laid-out, which would break the slot correspondence. */
const DENSE_THRESHOLD = 0.4;

type Props = {
  networks: Networks;
  evaluation: Evaluation;
};

/**
 * The page's hero and its argument.
 *
 * Each point is a method: how many of the true network's edges it recovers,
 * against how wrong its contagion behaviour is. Selecting a point redraws the
 * network below against the simulated ground truth, so the reader can see what
 * a method scoring well on edges actually produces.
 */
export default function TradeoffHero({ networks, evaluation }: Props) {
  const colours = useMemo(() => methodColours(networks), [networks]);
  const keys = useMemo(
    () => Object.keys(evaluation.methods).filter((key) => networks.methods[key]),
    [evaluation, networks],
  );
  const [selected, setSelected] = useState<MethodKey>(networks.default_pair[1]);
  const [hoveredSlot, setHoveredSlot] = useState<number | null>(null);
  const pointRefs = useRef(new Map<MethodKey, SVGCircleElement>());

  const x = scaleLinear().domain([0, 1]).range([MARGIN.left, WIDTH - MARGIN.right]);
  const maxError = Math.max(...keys.map((key) => evaluation.methods[key].protocol_score.hi));
  const y = scaleLinear()
    .domain([0, maxError * 1.12])
    .range([HEIGHT - MARGIN.bottom, MARGIN.top]);

  const move = useCallback(
    (step: number) => {
      const index = keys.indexOf(selected);
      const next = keys[(index + step + keys.length) % keys.length];
      setSelected(next);
      pointRefs.current.get(next)?.focus();
    },
    [keys, selected],
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
        move(steps[event.key]);
      }
    },
    [move],
  );

  const observedKey = networks.default_pair[0];
  const chosen = evaluation.methods[selected];
  const density = (key: MethodKey) => {
    const graph = networks.methods[key];
    const n = graph.nodes.length;
    return graph.edges.length / (n * (n - 1));
  };
  const opacityFor = (key: MethodKey) =>
    density(key) > DENSE_THRESHOLD ? RESTING_EDGE.dense : RESTING_EDGE.accented;

  return (
    <div className="grid gap-x-10 gap-y-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div>
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-auto">
          <g>
            {y.ticks(5).map((tick) => (
              <line
                key={tick}
                x1={MARGIN.left}
                x2={WIDTH - MARGIN.right}
                y1={y(tick)}
                y2={y(tick)}
                stroke="var(--color-rule)"
              />
            ))}
          </g>

          <g className="tabular" fontSize={12} fill="var(--color-ink)" fillOpacity={0.55}>
            {x.ticks(5).map((tick) => (
              <text key={tick} x={x(tick)} y={HEIGHT - MARGIN.bottom + 18} textAnchor="middle">
                {Math.round(tick * 100)}%
              </text>
            ))}
            {y.ticks(5).map((tick) => (
              <text key={tick} x={MARGIN.left - 8} y={y(tick) + 4} textAnchor="end">
                {tick.toFixed(1)}
              </text>
            ))}
          </g>

          <text x={MARGIN.left} y={HEIGHT - 20} fontSize={13} fill="var(--color-ink)" fillOpacity={0.75}>
            Share of the real network&rsquo;s links recovered
          </text>
          <text x={MARGIN.left} y={HEIGHT - 4} fontSize={12} fill="var(--color-ink)" fillOpacity={0.5}>
            right means better by the usual test
          </text>
          <text
            transform={`translate(14 ${MARGIN.top + 2}) rotate(-90)`}
            fontSize={13}
            textAnchor="end"
            fill="var(--color-ink)"
            fillOpacity={0.75}
          >
            How wrong the crisis behaviour is
          </text>

          <g role="listbox" aria-label="Methods" tabIndex={-1} onKeyDown={onKeyDown}>
            {keys.map((key) => {
              const entry = evaluation.methods[key];
              const cx = x(entry.edge_recall.mean);
              const cy = y(entry.protocol_score.mean);
              const active = key === selected;
              return (
                <g key={key}>
                  <line
                    x1={cx}
                    x2={cx}
                    y1={y(entry.protocol_score.lo)}
                    y2={y(entry.protocol_score.hi)}
                    stroke={colours[key]}
                    strokeWidth={1.4}
                    opacity={active ? 0.9 : 0.4}
                  />
                  {active && (
                    <circle cx={cx} cy={cy} r={11} fill="none" stroke="var(--color-ink)" strokeWidth={1} />
                  )}
                  <circle
                    ref={(element) => {
                      if (element) pointRefs.current.set(key, element);
                      else pointRefs.current.delete(key);
                    }}
                    role="option"
                    aria-selected={active}
                    aria-label={`${entry.label}. Recovers ${Math.round(entry.edge_recall.mean * 100)} percent of links. Crisis-behaviour error ${entry.protocol_score.mean.toFixed(2)}.`}
                    tabIndex={active ? 0 : -1}
                    cx={cx}
                    cy={cy}
                    r={7}
                    fill={colours[key]}
                    className="cursor-pointer"
                    onMouseEnter={() => setSelected(key)}
                    onFocus={() => setSelected(key)}
                    onClick={() => setSelected(key)}
                  />
                  <text
                    x={cx + (entry.edge_recall.mean > 0.75 ? -14 : 14)}
                    y={cy + 4}
                    fontSize={12.5}
                    fill="var(--color-ink)"
                    textAnchor={entry.edge_recall.mean > 0.75 ? "end" : "start"}
                    opacity={active ? 1 : 0.62}
                  >
                    {entry.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        <p className="mt-4 text-sm text-ink/70 max-w-[52ch]">
          Each dot is a way of building a fake banking network. Bars show the range
          across {evaluation.samples} attempts. If recovering the real links told you
          anything about how a crisis behaves, the dots would fall on a line. They do
          not.
        </p>
      </div>

      <div>
        <div className="grid grid-cols-2 gap-x-6">
          {[observedKey, selected].map((key, index) => {
            const graph = networks.methods[key];
            return (
              <figure key={`${key}-${index}`} className="m-0">
                <NetworkPlot
                  graph={graph}
                  colour={colours[key]}
                  edgeOpacity={index === 0 ? RESTING_EDGE.observed : opacityFor(key)}
                  name={graph.label}
                  revealStartMs={index === 0 ? 120 : 420}
                  hoveredSlot={hoveredSlot}
                  onHoverSlot={setHoveredSlot}
                />
                <figcaption className="mt-3 text-sm" style={{ color: colours[key] }}>
                  {graph.label}
                </figcaption>
              </figure>
            );
          })}
        </div>

        <p className="mt-5 text-sm max-w-[48ch]">
          {selected === observedKey ? (
            <>The real system, shown against itself.</>
          ) : (
            <>
              {chosen.label} recovers{" "}
              <span className="tabular">{Math.round(chosen.edge_recall.mean * 100)}%</span> of
              the real links. Its crisis behaviour is{" "}
              <span className="tabular">{chosen.protocol_score.mean.toFixed(2)}</span> away from
              the truth, and it is told: {chosen.sees.toLowerCase()}
            </>
          )}
        </p>
      </div>
    </div>
  );
}
