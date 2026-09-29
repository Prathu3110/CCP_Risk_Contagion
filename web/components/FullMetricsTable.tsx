import SeriesName from "@/components/SeriesName";
import type { Evaluation, GapMetric, MethodKey } from "@/lib/types";

/** What each row measures, in words a reader can check the number against. */
const ROWS: { key: GapMetric | "edge_recall" | "edge_f1" | "frobenius_relative"; label: string; meaning: string; group: string }[] = [
  {
    key: "edge_recall",
    label: "Links recovered",
    meaning: "Of the real system's debts, the share this method also has. Higher is better.",
    group: "The conventional test",
  },
  {
    key: "edge_f1",
    label: "Link accuracy",
    meaning:
      "Recovering links counts for less if you invent many that do not exist. This balances the two. Higher is better.",
    group: "The conventional test",
  },
  {
    key: "frobenius_relative",
    label: "Error in the amounts",
    meaning:
      "How far the individual debt sizes are from the real ones, across the whole system. Lower is better.",
    group: "The conventional test",
  },
  {
    key: "mean_debtrank",
    label: "Damage the average bank can do",
    meaning:
      "Each bank in turn is pushed into trouble and the damage measured, then averaged. This is the measure our own model is worst on.",
    group: "How a crisis behaves",
  },
  {
    key: "max_debtrank",
    label: "Damage the worst bank can do",
    meaning: "The same measure, for the single most dangerous bank in the system.",
    group: "How a crisis behaves",
  },
  {
    key: "mean_cascade_size",
    label: "How many banks fail",
    meaning:
      "Average share of banks that cannot pay, across the whole sweep of shocks. Every method does well here, which is why it cannot be the only test.",
    group: "How a crisis behaves",
  },
  {
    key: "edge_density",
    label: "How crowded the network is",
    meaning: "The share of all possible bank pairs that actually owe each other something.",
    group: "What the network looks like",
  },
  {
    key: "degree_assortativity",
    label: "Do big banks deal with big banks",
    meaning:
      "Negative in a real system: large banks deal with small ones, not with each other. A method that loses this has lost the core-and-periphery shape.",
    group: "What the network looks like",
  },
  {
    key: "mean_exposure",
    label: "Typical size of one debt",
    meaning: "The average amount owed on a single link.",
    group: "What the network looks like",
  },
  {
    key: "mean_equity_ratio",
    label: "Capital held per bank",
    meaning:
      "Capital as a share of what a bank owns. The three reconstruction methods inherit the balance sheets of the network they were handed, so their small gap here is inherited rather than earned.",
    group: "What the network looks like",
  },
];

const HIGHER_IS_BETTER = new Set(["edge_recall", "edge_f1"]);

/**
 * Every metric, every method, in one place.
 *
 * Cells are the relative gap against the simulated ground truth unless the row
 * says otherwise, so lower is better almost everywhere. The two exceptions are
 * marked, because a table where the good direction flips silently is a trap.
 */
export default function FullMetricsTable({
  evaluation,
  colours,
  order,
}: {
  evaluation: Evaluation;
  colours: Record<MethodKey, string>;
  order: MethodKey[];
}) {
  const methods = order.filter((key) => evaluation.methods[key]);
  const groups = [...new Set(ROWS.map((row) => row.group))];

  const value = (key: MethodKey, row: (typeof ROWS)[number]) => {
    const entry = evaluation.methods[key];
    if (row.key === "edge_recall") return entry.edge_recall.mean;
    if (row.key === "edge_f1") return entry.edge_f1.mean;
    if (row.key === "frobenius_relative") return entry.frobenius_relative.mean;
    return entry.gaps[row.key as GapMetric].mean;
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <caption className="sr-only">
          Every performance metric for every method, against the simulated ground truth
        </caption>
        <thead>
          <tr className="border-b border-rule align-bottom">
            <th scope="col" className="py-2 pr-4 font-medium w-[38%]">
              Measure
            </th>
            {methods.map((key) => (
              <th key={key} scope="col" className="py-2 px-3 font-medium text-right">
                <SeriesName
                  label={evaluation.methods[key].label}
                  colour={colours[key]}
                  className="justify-end"
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <Fragment key={group} group={group} span={methods.length + 1}>
              {ROWS.filter((row) => row.group === group).map((row) => {
                const values = methods.map((key) => value(key, row));
                const best = HIGHER_IS_BETTER.has(row.key)
                  ? Math.max(...values)
                  : Math.min(...values);
                return (
                  <tr key={row.key} className="border-b border-rule/60 align-top">
                    <th scope="row" className="py-2 pr-4 font-normal">
                      <span className="block">{row.label}</span>
                      <span className="block text-ink/60 mt-0.5">{row.meaning}</span>
                    </th>
                    {methods.map((key, index) => (
                      <td
                        key={key}
                        className={`py-2 px-3 text-right tabular align-top ${
                          values[index] === best ? "font-medium" : "text-ink/75"
                        }`}
                      >
                        {values[index].toFixed(3)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-sm text-ink/60 max-w-[68ch]">
        Scored on {evaluation.n_test_networks} held-out test systems that nothing in this
        project was tuned against. Our model is averaged over {evaluation.samples}{" "}
        generated systems; each reconstruction method is given every test system in turn.
        Every cell except the first two rows is a gap against those test systems, so lower
        is better, and the best value in each row is set in bold. The first two rows are
        shares, where higher is better.
      </p>
    </div>
  );
}

/** A labelled band of rows. Kept local: nothing else groups a table this way. */
function Fragment({
  group,
  span,
  children,
}: {
  group: string;
  span: number;
  children: React.ReactNode;
}) {
  return (
    <>
      <tr>
        <th
          scope="colgroup"
          colSpan={span}
          className="pt-6 pb-2 text-left font-medium border-b border-rule"
        >
          {group}
        </th>
      </tr>
      {children}
    </>
  );
}
