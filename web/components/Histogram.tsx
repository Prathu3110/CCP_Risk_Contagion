import { scaleLinear } from "d3-scale";
import { area, line } from "d3-shape";

import ChartFrame, { MARGIN } from "@/components/ChartFrame";
import type { Histogram as HistogramData, Series } from "@/lib/types";

const WIDTH = 620;
const HEIGHT = 320;

const COLOUR: Record<Series, string> = {
  observed: "var(--color-observed)",
  generated: "var(--color-generated)",
};

type Props = {
  data: HistogramData;
  title: string;
  xLabel: string;
  xTicks?: number[];
  formatX?: (value: number) => string;
};

/**
 * Two counts on one set of bins, drawn as overlaid step outlines.
 *
 * Bars would have to be either side by side, which reads as two separate
 * things, or stacked, which hides the comparison. An outline lets one curve
 * sit on top of the other and be judged by how closely they track.
 */
export default function Histogram({ data, title, xLabel, xTicks, formatX = String }: Props) {
  const counts = [...data.observed, ...data.generated];
  const x = scaleLinear()
    .domain([data.bins[0], data.bins[data.bins.length - 1]])
    .range([MARGIN.left, WIDTH - MARGIN.right]);
  const y = scaleLinear()
    .domain([0, Math.max(...counts)])
    .nice()
    .range([HEIGHT - MARGIN.bottom, MARGIN.top]);

  /** Trace the top of each bar, giving the exact outline of the histogram. */
  const steps = (values: number[]) =>
    values.flatMap((count, index) => [
      { value: data.bins[index], count },
      { value: data.bins[index + 1], count },
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
      {(["observed", "generated"] as Series[]).map((series) => {
        const points = steps(data[series]);
        return (
          <g key={series}>
            <path d={toArea(points) ?? ""} fill={COLOUR[series]} fillOpacity={0.07} />
            <path
              d={toLine(points) ?? ""}
              fill="none"
              stroke={COLOUR[series]}
              strokeWidth={2.2}
              strokeLinejoin="round"
            />
          </g>
        );
      })}
    </ChartFrame>
  );
}
