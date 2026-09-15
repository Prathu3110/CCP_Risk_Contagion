import type { ReactNode } from "react";
import type { ScaleLinear } from "d3-scale";

type Props = {
  width: number;
  height: number;
  x: ScaleLinear<number, number>;
  y: ScaleLinear<number, number>;
  xLabel: string;
  yLabel: string;
  xTicks?: number[];
  yTicks?: number[];
  formatX?: (value: number) => string;
  formatY?: (value: number) => string;
  title: string;
  children: ReactNode;
};

const MARGIN = { top: 14, right: 14, bottom: 50, left: 56 };

/**
 * Axes, gridlines and labels shared by every chart on the page.
 *
 * Gridlines are hairlines in the rule colour so they never compete with the
 * data, and every figure is set in tabular mono so columns of digits line up.
 */
export default function ChartFrame({
  width,
  height,
  x,
  y,
  xLabel,
  yLabel,
  xTicks,
  yTicks,
  formatX = String,
  formatY = String,
  title,
  children,
}: Props) {
  const xs = xTicks ?? x.ticks(6);
  const ys = yTicks ?? y.ticks(5);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-auto"
      role="img"
      aria-label={title}
    >
      <g>
        {ys.map((tick) => (
          <line
            key={tick}
            x1={MARGIN.left}
            x2={width - MARGIN.right}
            y1={y(tick)}
            y2={y(tick)}
            stroke="var(--color-rule)"
            strokeWidth={1}
          />
        ))}
      </g>

      {children}

      <line
        x1={MARGIN.left}
        x2={width - MARGIN.right}
        y1={height - MARGIN.bottom}
        y2={height - MARGIN.bottom}
        stroke="var(--color-rule)"
        strokeWidth={1}
      />

      <g className="tabular" fontSize={13} fill="var(--color-ink)" fillOpacity={0.6}>
        {xs.map((tick) => (
          <text key={tick} x={x(tick)} y={height - MARGIN.bottom + 18} textAnchor="middle">
            {formatX(tick)}
          </text>
        ))}
        {ys.map((tick) => (
          <text key={tick} x={MARGIN.left - 8} y={y(tick) + 4.5} textAnchor="end">
            {formatY(tick)}
          </text>
        ))}
      </g>

      <text
        x={MARGIN.left}
        y={height - 8}
        fontSize={14}
        fill="var(--color-ink)"
        fillOpacity={0.7}
      >
        {xLabel}
      </text>
      <text
        transform={`translate(13 ${MARGIN.top + 4}) rotate(-90)`}
        fontSize={14}
        textAnchor="end"
        fill="var(--color-ink)"
        fillOpacity={0.7}
      >
        {yLabel}
      </text>
    </svg>
  );
}

export { MARGIN };
