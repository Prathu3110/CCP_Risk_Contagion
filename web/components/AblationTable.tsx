import type { Ablations } from "@/lib/types";

/**
 * What each modelling choice is worth, measured by switching it off.
 *
 * Rows are ordered by effect size. A positive delta means the model got worse
 * without that choice, so the choice was earning its place.
 */
export default function AblationTable({ ablations }: { ablations: Ablations }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">
          Crisis-behaviour error with each modelling choice disabled in turn
        </caption>
        <thead>
          <tr className="border-b border-rule">
            <th scope="col" className="py-2 pr-4 font-medium">
              Choice switched off
            </th>
            <th scope="col" className="py-2 px-4 font-medium text-right">
              Crisis-behaviour error
            </th>
            <th scope="col" className="py-2 px-4 font-medium text-right">
              Change
              <span className="block font-normal text-ink/55">
                positive = the choice earns its place
              </span>
            </th>
            <th scope="col" className="py-2 pl-4 font-medium text-right">
              Spread of debt sizes
            </th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-rule/60">
            <td className="py-2 pr-4">Nothing: the full model</td>
            <td className="py-2 px-4 text-right tabular">
              {ablations.full_model.protocol_score.toFixed(3)}
            </td>
            <td className="py-2 px-4 text-right tabular text-ink/40">&mdash;</td>
            <td className="py-2 pl-4 text-right tabular">
              {ablations.full_model.log_weight_std.toFixed(2)}
            </td>
          </tr>
          {ablations.rows.map((row) => (
            <tr key={row.flag} className="border-b border-rule/60">
              <td className="py-2 pr-4">{row.label}</td>
              <td className="py-2 px-4 text-right tabular">
                {row.protocol_score.toFixed(3)}
              </td>
              <td className="py-2 px-4 text-right tabular">
                {row.protocol_delta >= 0 ? "+" : ""}
                {row.protocol_delta.toFixed(3)}
              </td>
              <td className="py-2 pl-4 text-right tabular">
                {row.log_weight_std.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-sm text-ink/60 max-w-[62ch]">
        Lower error is better, so a positive change means the model got worse without
        that choice. The real system&rsquo;s spread of debt sizes is{" "}
        <span className="tabular">{ablations.observed_log_weight_std.toFixed(2)}</span>;
        a method that drives it far from that is distorting how a crisis travels.
        Averaged over {ablations.samples_per_variant} systems per variant.
      </p>
    </div>
  );
}
