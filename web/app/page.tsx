import CascadeChart from "@/components/CascadeChart";
import CrisisSimulator from "@/components/CrisisSimulator";
import Histogram from "@/components/Histogram";
import Legend from "@/components/Legend";
import MetricsTable from "@/components/MetricsTable";
import ProtocolTable from "@/components/ProtocolTable";
import TradeoffHero from "@/components/TradeoffHero";
import { contagion, evaluation, metrics, networks } from "@/lib/data";
import { methodColours } from "@/lib/methods";
import { binEdges, countInto } from "@/lib/stats";

const colours = methodColours(networks);
const order = Object.keys(networks.methods);
const ours = networks.default_pair[1];

const legend = order.map((key) => ({
  key,
  label: networks.methods[key].label,
  colour: colours[key],
}));

const histogramSeries = (by_method: Record<string, number[]>) =>
  order.map((key) => ({
    key,
    label: networks.methods[key].label,
    colour: colours[key],
    counts: by_method[key],
  }));

/** Integer powers of ten inside the exposure histogram's range. */
const exposureTicks = (() => {
  const { bins } = metrics.weight_hist;
  const ticks: number[] = [];
  for (let power = Math.ceil(bins[0]); power <= bins[bins.length - 1]; power += 1) {
    ticks.push(power);
  }
  return ticks;
})();

const debtrankHistogram = (() => {
  // One set of bins across every method, so the curves can be compared.
  const bins = binEdges(
    order.flatMap((key) => contagion.by_method[key].debtrank),
    12,
  );
  return {
    bins,
    series: order.map((key) => ({
      key,
      label: networks.methods[key].label,
      colour: colours[key],
      counts: countInto(contagion.by_method[key].debtrank, bins),
    })),
  };
})();

const cascadeSeries = order.map((key) => ({
  key,
  label: networks.methods[key].label,
  colour: colours[key],
  band: contagion.by_method[key].cascade,
}));

export default function Page() {
  const model = evaluation.methods[ours];
  const dense = evaluation.methods.max_entropy;

  return (
    <main className="mx-auto max-w-[1100px] px-6 sm:px-10">
      <section className="py-14 lg:py-20">
        <h1 className="font-display font-semibold tracking-tight text-4xl sm:text-5xl lg:text-6xl leading-[1.04] max-w-[24ch]">
          The usual way of checking a fake bank network measures the wrong thing
        </h1>
        <p className="mt-6 max-w-[62ch] text-lg">
          Records of who owes what to whom between banks are confidential, so researchers
          build fake ones instead. The standard way to judge a fake is to count how many of
          the real network&rsquo;s links it got right. That number turns out to say almost
          nothing about the only thing these networks are built for: working out how far a
          financial crisis would spread.
        </p>

        <div className="mt-12">
          <TradeoffHero networks={networks} evaluation={evaluation} />
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          The clearest case
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            One of those methods knows only how much each bank owes in total and is owed in
            total, and spreads the money as evenly as those totals allow. It is the field
            standard, and by the usual test it is close to perfect: it recovers{" "}
            <span className="tabular">{Math.round(dense.edge_recall.mean * 100)}%</span> of the
            real links, because it connects nearly every bank to nearly every other, so the
            real links are all in there somewhere.
          </p>
          <p>
            Select it above and look at what it draws. A real banking system is a small
            dense core with a thin scattering around it. This one is an almost solid block.
            Every bank owes a little to everyone, nobody is exposed to anybody in
            particular, and a failure has nowhere to concentrate.
          </p>
          <p>
            Our own model sees none of the real network. It recovers{" "}
            <span className="tabular">{Math.round(model.edge_recall.mean * 100)}%</span> of the
            links, and its crises behave closer to the truth.
          </p>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          How well each method does on both tests
        </h2>
        <p className="mt-5 max-w-[62ch]">
          Every stochastic method was run {evaluation.samples} times. The crisis-behaviour
          test compares how much damage each bank can do, how much the worst one can do, and
          how many banks fail across a sweep of shocks. The last column asks whether a
          statistical test can tell the fake system&rsquo;s pattern of dangerous banks apart
          from the real one&rsquo;s.
        </p>
        <div className="mt-8">
          <ProtocolTable evaluation={evaluation} colours={colours} order={order} />
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          How the networks are made
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            A dot is a bank. A line between two dots means one owes the other money, and the
            thicker the line, the larger the debt. The bigger the dot, the bigger the bank.
          </p>
          <p>
            All the drawings share one set of positions, handed out by how many
            counterparties a bank has, so the busiest bank sits in the same place in every
            view. The same spot means the same job in the system, not the same institution.
          </p>
          <p>
            The system everything is measured against is itself simulated, not real
            supervisory data. It is built to reproduce the patterns that studies of real
            interbank markets report, and it is called the simulated ground truth
            throughout, never &ldquo;the real data&rdquo;.
          </p>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          What the systems look like
        </h2>
        <p className="mt-5 max-w-[62ch]">
          Two ways of describing a network&rsquo;s shape. Amounts are in units where a
          mid-sized bank&rsquo;s balance sheet is one.
        </p>

        <div className="mt-8">
          <Legend series={legend} />
        </div>

        <div className="mt-6 grid gap-x-10 gap-y-10 lg:grid-cols-2">
          <figure className="m-0">
            <Histogram
              bins={metrics.degree_hist.bins}
              series={histogramSeries(metrics.degree_hist.by_method)}
              title="Distribution of the number of counterparties per bank"
              xLabel="Counterparties per bank"
            />
            <figcaption className="mt-2 text-sm text-ink/70 max-w-[52ch]">
              How many other banks each one deals with. The evenly spread method sits far to
              the right, off on its own: it gives almost every bank a hundred-odd
              counterparties where the real system gives most of them a handful.
            </figcaption>
          </figure>

          <figure className="m-0">
            <Histogram
              bins={metrics.weight_hist.bins}
              series={histogramSeries(metrics.weight_hist.by_method)}
              title="Distribution of individual exposure sizes"
              xLabel="Size of a single debt, log scale"
              xTicks={exposureTicks}
              formatX={(value) => formatPower(value)}
            />
            <figcaption className="mt-2 text-sm text-ink/70 max-w-[52ch]">
              How large individual debts are. The spread matters more than the average: it is
              the rare large debt that sinks a lender.
            </figcaption>
          </figure>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          How crises spread through them
        </h2>
        <p className="mt-5 max-w-[62ch]">
          Two stress tests. The first asks how much damage each bank can do on its own. The
          second wipes out a share of everyone&rsquo;s outside assets and counts how many
          banks then cannot pay what they owe.
        </p>

        <div className="mt-8">
          <Legend series={legend} />
        </div>

        <div className="mt-6 grid gap-x-10 gap-y-10 lg:grid-cols-2">
          <figure className="m-0">
            <Histogram
              bins={debtrankHistogram.bins}
              series={debtrankHistogram.series}
              title="Distribution of how much damage each bank causes when it alone is distressed"
              xLabel="Share of the system's value at risk from one bank"
              formatX={(value) => `${Math.round(value * 100)}%`}
            />
            <figcaption className="mt-2 text-sm text-ink/70 max-w-[52ch]">
              This is the test that separates the methods. The real system has a few banks
              that can put a sixth of it at risk alone. The evenly spread method has none:
              every bank matters the same small amount.
            </figcaption>
          </figure>

          <figure className="m-0">
            <CascadeChart shock={contagion.shock} series={cascadeSeries} />
            <figcaption className="mt-2 text-sm text-ink/70 max-w-[52ch]">
              And this is the test that does not separate them. Every method traces roughly
              the same curve, which is worth saying plainly: a single headline number can
              agree while the systems underneath behave quite differently.
            </figcaption>
          </figure>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          Run a crisis yourself
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            Choose how hard to hit the system and which method to test, then watch both fail
            round by round. A bank turns red the moment it can no longer pay what it owes,
            and the debts it will not repay turn red with it.
          </p>
          <p>
            Each round is one pass of the clearing calculation. Banks that fail in the first
            round were sunk by the shock itself. Everyone who fails after that was brought
            down by the failures before them, and you could never find that second group by
            reading one bank&rsquo;s balance sheet on its own.
          </p>
          <p>
            Three settings behave quite differently. Below about 7% nothing fails at all.
            Between 8% and 15% the system tips over. Past 25% the direct damage stops growing
            and almost every new failure comes through the network instead.
          </p>
        </div>

        <div className="mt-8">
          <CrisisSimulator networks={networks} />
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          Our model against the simulated ground truth
        </h2>
        <p className="mt-5 max-w-[62ch]">
          Structural statistics for the two systems, and the gap between them. Nothing here
          was fitted to match; the model was trained only to reconstruct networks, and every
          row is a consequence of that.
        </p>
        <div className="mt-8">
          <MetricsTable rows={metrics.summary.by_method[ours]} />
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          What this does not do yet
        </h2>
        <ul className="mt-5 max-w-[62ch] space-y-3 list-disc pl-5">
          <li>
            The system everything is measured against is simulated. Real supervisory data is
            not wired in, so this shows the method works, not that it works on the real
            thing.
          </li>
          <li>
            Our own model fails one of our own tests. It understates how dangerous the
            typical bank is, by about a third. We report it rather than tuning it away, and
            it is the strongest argument for the test: a model built specifically for crisis
            realism still misses, which is exactly what a test is supposed to catch.
          </li>
          <li>
            One of the methods here is a rewiring of the real network, and it scores best.
            It is not a rival generator: it cannot produce anything without being handed the
            real system first, including every bank&rsquo;s exact number of counterparties.
          </li>
          <li>
            There is no central counterparty and no default waterfall yet. Those are the next
            milestone, and the part that matters most for clearing risk.
          </li>
          <li>
            Everything here is sixty banks. A national system is thousands.
          </li>
        </ul>
      </section>

      <footer className="border-t border-rule py-10 text-sm text-ink/60">
        <p className="max-w-[62ch]">
          Generated by a graph variational autoencoder trained for{" "}
          {metrics.training.epochs.length} epochs on {networks.n_nodes}-bank systems, and
          scored over {evaluation.samples} samples per method. Every figure on this page is
          recomputed from one seeded run of the pipeline.
        </p>
      </footer>
    </main>
  );
}

function formatPower(power: number): string {
  const value = Math.pow(10, power);
  if (value >= 1) return String(value);
  return value.toFixed(Math.max(0, -Math.round(power)));
}
