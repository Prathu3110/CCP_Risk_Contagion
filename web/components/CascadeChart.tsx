import { scaleLinear } from "d3-scale";
import { area, line } from "d3-shape";

import ChartFrame, { MARGIN } from "@/components/ChartFrame";
import type { Band } from "@/lib/types";

const WIDTH = 620;
const HEIGHT = 340;

export interface CascadeSeries {
  key: string;
  label: string;
  colour: string;
  band: Band;
}

type Point = { shock: number; mean: number; lo: number; hi: number };

/**
 * How far a crisis travels, as the size of the initial hit grows.
 *
 * The shaded band is the 10th to 90th percentile over repeats: the same shock
 * lands differently depending on which banks absorb it, and the band is the
 * honest width of that spread.
 */
export default function CascadeChart({
  shock,
  series,
}: {
  shock: number[];
  series: CascadeSeries[];
}) {
  const x = scaleLinear()
    .domain([shock[0], shock[shock.length - 1]])
    .range([MARGIN.left, WIDTH - MARGIN.right]);
  const y = scaleLinear().domain([0, 1]).range([HEIGHT - MARGIN.bottom, MARGIN.top]);

  const points = (band: Band): Point[] =>
    shock.map((level, index) => ({
      shock: level,
      mean: band.mean[index],
      lo: band.lo[index],
      hi: band.hi[index],
    }));

  const toLine = line<Point>()
    .x((point) => x(point.shock))
    .y((point) => y(point.mean));
  const toBand = area<Point>()
    .x((point) => x(point.shock))
    .y0((point) => y(point.lo))
    .y1((point) => y(point.hi));

  const half = y(0.5);

  return (
    <ChartFrame
      width={WIDTH}
      height={HEIGHT}
      x={x}
      y={y}
      xLabel="Share of outside assets destroyed"
      yLabel="Share of banks that default"
      xTicks={shock.filter((_, index) => index % 2 === 0)}
      yTicks={[0, 0.25, 0.5, 0.75, 1]}
      formatX={(value) => `${Math.round(value * 100)}%`}
      formatY={(value) => `${Math.round(value * 100)}%`}
      title="Share of banks that default as the initial shock grows"
    >
      {/* Deep red means one thing on this page: a bank has defaulted. */}
      <line
        x1={MARGIN.left}
        x2={WIDTH - MARGIN.right}
        y1={half}
        y2={half}
        stroke="var(--color-stress)"
        strokeWidth={1}
        strokeDasharray="3 3"
        opacity={0.75}
      />
      <text
        x={WIDTH - MARGIN.right}
        y={half - 7}
        textAnchor="end"
        fontSize={12.5}
        fill="var(--color-stress)"
      >
        half the system has failed
      </text>

      {series.map((entry) => {
        const data = points(entry.band);
        return (
          <g key={entry.key}>
            <path d={toBand(data) ?? ""} fill={entry.colour} fillOpacity={0.18} />
            <path
              d={toLine(data) ?? ""}
              fill="none"
              stroke={entry.colour}
              strokeWidth={2.4}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {data.map((point) => (
              <circle
                key={point.shock}
                cx={x(point.shock)}
                cy={y(point.mean)}
                r={2.8}
                fill={entry.colour}
              />
            ))}
          </g>
        );
      })}
    </ChartFrame>
  );
}
