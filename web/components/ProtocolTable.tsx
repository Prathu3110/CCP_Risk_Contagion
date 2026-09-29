import SeriesName from "@/components/SeriesName";
import type { Evaluation, MethodKey } from "@/lib/types";

const percent = (value: number) => `${Math.round(value * 100)}%`;

/**
 * Both criteria side by side, with what each method is allowed to see.
 *
 * The access column is not a footnote. Three of these methods are handed a
 * summary of the network they are copying; ours is handed nothing.
 */
export default function ProtocolTable({
  evaluation,
  colours,
  order,
}: {
  evaluation: Evaluation;
  colours: Record<MethodKey, string>;
  order: MethodKey[];
}) {
  const rows = order.filter((key) => evaluation.methods[key]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">
          Edge recovery, crisis-behaviour error and the Kolmogorov-Smirnov test for each
          method
        </caption>
        <thead>
          <tr className="border-b border-rule align-bottom">
            <th scope="col" className="py-2 pr-4 font-medium">
              Method
            </th>
            <th scope="col" className="py-2 px-4 font-medium text-right">
              Links recovered
            </th>
            <th scope="col" className="py-2 px-4 font-medium text-right">
              Crisis-behaviour error
            </th>
            <th scope="col" className="py-2 px-4 font-medium text-right">
              Passes the test
            </th>
            <th scope="col" className="py-2 pl-4 font-medium">
              What it is told
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((key) => {
            const entry = evaluation.methods[key];
            const passes = entry.ks_debtrank.share_not_rejected_at_005;
            return (
              <tr key={key} className="border-b border-rule/60 align-top">
                <td className="py-2 pr-4">
                  <SeriesName label={entry.label} colour={colours[key]} />
                </td>
                <td className="py-2 px-4 text-right tabular">
                  {percent(entry.edge_recall.mean)}
                </td>
                <td className="py-2 px-4 text-right tabular">
                  {entry.protocol_score.mean.toFixed(3)}
                  <span className="text-ink/45">
                    {" "}
                    [{entry.protocol_score.lo.toFixed(2)}, {entry.protocol_score.hi.toFixed(2)}]
                  </span>
                </td>
                <td className="py-2 px-4 text-right tabular">
                  {Math.round(passes * entry.n_samples)} of {entry.n_samples}
                </td>
                <td className="py-2 pl-4 text-sm text-ink/70">{entry.sees}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 text-sm text-ink/60 max-w-[62ch]">
        Crisis-behaviour error is the mean relative gap over three measures, with a 95%
        interval across samples; lower is better. &ldquo;Passes the test&rdquo; counts the
        samples whose pattern of dangerous banks a Kolmogorov-Smirnov test could not tell
        apart from the simulated ground truth, which is the outcome you want.
      </p>
    </div>
  );
}
