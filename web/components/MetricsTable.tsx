import SeriesName from "@/components/SeriesName";
import type { SummaryRow } from "@/lib/types";

/** Figures are set in tabular mono so the columns of digits line up. */
export default function MetricsTable({ rows }: { rows: SummaryRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">
          Network statistics for the simulated ground truth and our model, with the gap
          between them
        </caption>
        <thead>
          <tr className="border-b border-rule">
            <th scope="col" className="py-2 pr-4 font-medium">
              Statistic
            </th>
            <th scope="col" className="py-2 px-4 font-medium text-right">
              <SeriesName
                label="Ground truth"
                colour="var(--color-observed)"
                className="justify-end"
              />
            </th>
            <th scope="col" className="py-2 px-4 font-medium text-right">
              <SeriesName
                label="Our model"
                colour="var(--color-generated)"
                className="justify-end"
              />
            </th>
            <th scope="col" className="py-2 pl-4 font-medium text-right">
              Gap
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name} className="border-b border-rule/60">
              <td className="py-2 pr-4">{row.name}</td>
              <td className="py-2 px-4 text-right tabular">{format(row.observed)}</td>
              <td className="py-2 px-4 text-right tabular">{format(row.generated)}</td>
              <td className="py-2 pl-4 text-right tabular">{row.gap_pct.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function format(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return Math.abs(value) >= 1 ? value.toFixed(2) : value.toFixed(3);
}
