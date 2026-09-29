import { scaleLinear } from "d3-scale";
import { area, line } from "d3-shape";

import ChartFrame, { MARGIN } from "@/components/ChartFrame";

const WIDTH = 620;
const HEIGHT = 320;

export interface HistogramSeries {
  key: string;
  label: string;
  colour: string;
  counts: number[];
}

type Props = {
  bins: number[];
  series: HistogramSeries[];
  title: string;
  xLabel: string;
  xTicks?: number[];
  formatX?: (value: number) => string;
};

/**
 * Several counts on one set of bins, drawn as overlaid step outlines.
 *
 * Bars would have to be side by side, which reads as separate things, or
 * stacked, which hides the comparison. Outlines let the curves sit on top of
 * one another and be judged by how closely they track.
 */
export default function Histogram({ bins, series, title, xLabel, xTicks, formatX = String }: Props) {
  const counts = series.flatMap((entry) => entry.counts);
  const x = scaleLinear()
    .domain([bins[0], bins[bins.length - 1]])
    .range([MARGIN.left, WIDTH - MARGIN.right]);
  const y = scaleLinear()
    .domain([0, Math.max(...counts)])
    .nice()
    .range([HEIGHT - MARGIN.bottom, MARGIN.top]);

  /** Trace the top of each bar, giving the exact outline of the histogram. */
  const steps = (values: number[]) =>
    values.flatMap((count, index) => [
      { value: bins[index], count },
      { value: bins[index + 1], count },
    ]);

  const toLine = line<{ value: number; count: number }>()
    .x((point) => x(point.value))
    .y((point) => y(point.count));
  const toArea = area<{ value: number; count: number }>()
    .x((point) => x(point.value))
    .y0(y(0))
    .y1((point) => y(point.count));

  return (
    <ChartFrame
      width={WIDTH}
      height={HEIGHT}
      x={x}
      y={y}
      xLabel={xLabel}
      yLabel="Number of banks"
      xTicks={xTicks}
      formatX={formatX}
      title={title}
    >
      {series.map((entry) => {
        const points = steps(entry.counts);
        return (
          <g key={entry.key}>
            <path d={toArea(points) ?? ""} fill={entry.colour} fillOpacity={0.07} />
            <path
              d={toLine(points) ?? ""}
              fill="none"
              stroke={entry.colour}
              strokeWidth={2.2}
              strokeLinejoin="round"
            />
          </g>
        );
      })}
    </ChartFrame>
  );
}
