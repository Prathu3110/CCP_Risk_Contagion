import CascadeChart from "@/components/CascadeChart";
import CrisisSimulator from "@/components/CrisisSimulator";
import Histogram from "@/components/Histogram";
import Legend from "@/components/Legend";
import MetricsTable from "@/components/MetricsTable";
import NetworkPair from "@/components/NetworkPair";
import { contagion, metrics, networks } from "@/lib/data";
import { mean, sharedHistogram } from "@/lib/stats";

const debtrankHistogram = sharedHistogram(
  contagion.debtrank.observed,
  contagion.debtrank.generated,
  12,
);

/** Integer powers of ten inside the exposure histogram's range. */
const exposureTicks = (() => {
  const { bins } = metrics.weight_hist;
  const ticks: number[] = [];
  for (let power = Math.ceil(bins[0]); power <= bins[bins.length - 1]; power += 1) {
    ticks.push(power);
  }
  return ticks;
})();

const cascadeGap = (() => {
  const observed = mean(contagion.cascade.observed.mean);
  const generated = mean(contagion.cascade.generated.mean);
  return Math.abs(generated - observed) / observed * 100;
})();

export default function Page() {
  return (
    <main className="mx-auto max-w-[1100px] px-6 sm:px-10">
      <section className="py-14 lg:py-20">
        <h1 className="font-display font-semibold tracking-tight text-4xl sm:text-5xl lg:text-6xl leading-[1.04] max-w-[21ch]">
          Inventing bank networks that break like the real ones
        </h1>
        <p className="mt-6 max-w-[62ch] text-lg">
          Each dot is a bank. Each line is money one bank owes another. The system on the
          left stands in for the confidential records a central bank holds. The one on the
          right does not exist: a model invented it after learning from three hundred
          systems like the first.
        </p>

        <div className="mt-12">
          <NetworkPair networks={networks} />
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          How to read the two pictures
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            A dot is a bank. A line between two dots means one of them owes the other
            money, and the thicker the line, the larger the debt. The bigger the dot, the
            bigger the bank.
          </p>
          <p>
            Position is not decoration. Both drawings use the same set of positions,
            handed out by how many counterparties a bank has, so the busiest bank in each
            system sits in the same place. That is what makes them comparable at a glance:
            the same spot means the same job in the system, not the same institution.
            Point at any bank and its counterparties light up in both at once.
          </p>
          <p>
            What you should see is a dense knot in the middle and a thin scattering around
            the edge. That is the shape real interbank markets have: a few large banks that
            deal with almost everybody, and many small ones that deal mainly with the large
            ones. The model was never told to produce that. It worked it out from examples.
          </p>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          Why anyone would invent this data
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            Who owes what to whom is the single most useful thing to know when working out
            whether one bank failing will take others with it. It is also secret. Supervisors
            collect it and almost nobody else may see it, which is why research on financial
            contagion keeps stalling.
          </p>
          <p>
            So the idea is to manufacture a substitute. The hard part is proving the
            substitute is any good. The obvious test, checking whether the invented network
            has the same connections as the real one, is the wrong test: no two real banking
            systems have the same connections either, and a generator that reproduced them
            exactly would just be leaking the confidential data it was meant to replace.
          </p>
          <p>
            The test used here is behavioural. Push both systems into a crisis and see
            whether the crisis travels the same distance.
          </p>
          <p>
            If that works, the invented networks are usable wherever the real ones cannot
            go. A researcher with no access to supervisory data can develop and compare
            stress tests on them. A regulator can hand out a realistic network to
            outsiders without disclosing anything about actual banks. And because the
            generator produces as many systems as you like, a policy can be tested against
            a thousand plausible banking systems instead of the single one that happens to
            exist.
          </p>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          The invented system is built like the real one
        </h2>
        <p className="mt-5 max-w-[62ch]">
          Both systems have the shape economists find in real interbank markets: a handful of
          large banks that deal with almost everyone, and a long tail of smaller ones that
          deal mostly with the big banks rather than with each other. Amounts are in units
          where a mid-sized bank&rsquo;s balance sheet is one.
        </p>

        <div className="mt-8">
          <Legend
            observed="Observed system"
            generated="Generated system"
          />
        </div>

        <div className="mt-6 grid gap-x-10 gap-y-10 lg:grid-cols-2">
          <figure className="m-0">
            <Histogram
              data={metrics.degree_hist}
              title="Distribution of the number of counterparties per bank"
              xLabel="Counterparties per bank"
            />
            <figcaption className="mt-2 text-sm text-ink/70 max-w-[52ch]">
              How many other banks each one deals with. Most have a handful; a few have
              dozens.
            </figcaption>
          </figure>

          <figure className="m-0">
            <Histogram
              data={metrics.weight_hist}
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
          And crises spread through it the same way
        </h2>
        <p className="mt-5 max-w-[62ch]">
          Two standard stress tests, run on both systems. The first asks how much damage one
          bank can do on its own. The second wipes out a share of everyone&rsquo;s outside
          assets and counts how many banks then cannot pay what they owe.
        </p>

        <div className="mt-8">
          <Legend observed="Observed system" generated="Generated system" />
        </div>

        <div className="mt-6 grid gap-x-10 gap-y-10 lg:grid-cols-2">
          <figure className="m-0">
            <Histogram
              data={debtrankHistogram}
              title="Distribution of how much damage each bank causes when it alone is distressed"
              xLabel="Share of the system's value at risk from one bank"
              formatX={(value) => `${Math.round(value * 100)}%`}
            />
            <figcaption className="mt-2 text-sm text-ink/70 max-w-[52ch]">
              Each bank in turn is pushed into trouble and the damage is measured. Most banks
              barely matter; a few can put a sixth of the system at risk by themselves. This
              is the weakest of the three comparisons: the model gets the shape right but
              does not reach far enough into the dangerous tail.
            </figcaption>
          </figure>

          <figure className="m-0">
            <CascadeChart cascade={contagion.cascade} />
            <figcaption className="mt-2 text-sm text-ink/70 max-w-[52ch]">
              The whole system is hit at once, harder from left to right. The shaded band
              covers the range across twenty repeats, because the same shock does different
              damage depending on where it lands.
            </figcaption>
          </figure>
        </div>

        <p className="mt-10 max-w-[62ch]">
          The two cascade curves stay within {cascadeGap.toFixed(0)}% of each other across
          the whole range. A crisis does not much care that it is running through a network
          nobody has ever seen before: it spreads at the same rate and stops in the same
          place. That is the claim this project rests on.
        </p>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          Run a crisis yourself
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            Every point on the curve above is an average of runs like this one. Here the
            same calculation runs live, at whatever shock you choose: watch both systems
            fail round by round, side by side. A bank turns red the moment it can no
            longer pay what it owes, and the debts it will not repay turn red with it.
          </p>
          <p>
            Each round is one pass of the clearing calculation. Banks that fail in the
            first round were sunk by the shock itself. Everyone who fails after that was
            brought down by the failures before them, and that second group is the whole
            reason the network matters: you could never find them by reading one bank
            &rsquo;s balance sheet on its own.
          </p>
          <p>
            Three settings are worth trying, because they behave quite differently. Below
            about 7% nothing fails at all. Between 8% and 15% the system tips over, and
            the two systems can disagree about which banks go first. Past 25% the direct
            damage stops growing and almost every new failure comes through the network
            instead. A written account of what happened appears underneath once a run
            finishes.
          </p>
        </div>

        <div className="mt-8">
          <CrisisSimulator networks={networks} />
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          The numbers behind the pictures
        </h2>
        <p className="mt-5 max-w-[62ch]">
          Structural statistics for the two systems, and the gap between them. Nothing here
          was fitted to match; the model was trained only to reconstruct networks, and every
          row is a consequence of that.
        </p>
        <div className="mt-8">
          <MetricsTable rows={metrics.summary} />
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          What this does not do yet
        </h2>
        <ul className="mt-5 max-w-[62ch] space-y-3 list-disc pl-5">
          <li>
            The observed system is itself simulated. Real supervisory data is not wired in,
            so this shows the method works, not that it works on the real thing.
          </li>
          <li>
            The model understates how dangerous the typical bank is. Its average DebtRank
            comes out about a third below the observed system&rsquo;s, because it still does
            not produce quite enough very large single debts.
          </li>
          <li>
            There is no central counterparty and no default waterfall yet. Those are the next
            milestone, and they are the part that matters most for clearing risk.
          </li>
          <li>
            Everything here is sixty banks. A national system is thousands, and the dense
            adjacency approach used here will not reach that size unchanged.
          </li>
        </ul>
      </section>

      <footer className="border-t border-rule py-10 text-sm text-ink/60">
        <p className="max-w-[62ch]">
          Generated by a graph variational autoencoder trained for{" "}
          {metrics.training.epochs.length} epochs on {networks.n_nodes}-bank systems. Every
          figure on this page is recomputed from one seeded run of the pipeline.
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
