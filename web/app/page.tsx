import AblationTable from "@/components/AblationTable";
import CascadeChart from "@/components/CascadeChart";
import FullMetricsTable from "@/components/FullMetricsTable";
import CrisisSimulator from "@/components/CrisisSimulator";
import Histogram from "@/components/Histogram";
import Legend from "@/components/Legend";
import MetricsTable from "@/components/MetricsTable";
import ProtocolTable from "@/components/ProtocolTable";
import TradeoffHero from "@/components/TradeoffHero";
import { ablations, contagion, evaluation, metrics, networks } from "@/lib/data";
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
          The whole thing, without the jargon
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            Banks lend to each other constantly, in enormous amounts and overnight. That
            makes a web. If one bank cannot pay, the banks expecting that money have a
            hole, and if the hole is big enough they cannot pay either.
          </p>
          <p>
            Anyone who wants to know how bad a banking crisis could get needs a map of
            that web. Regulators have one. Nobody else is allowed to see it, and for good
            reason: it is a list of exactly where the system is weak.
          </p>
          <p>
            So researchers build fake maps. The question this page is about is how you
            check whether a fake map is any good.
          </p>
          <p>
            The obvious check is to compare it against a real map and count how many
            connections it got right. Think of it as a street map: count how many of the
            real streets appear. That is what the field does.
          </p>
          <p>
            We think that check is close to useless, and there is a simple way to see why.
            One popular method connects nearly every bank to nearly every other, a little
            bit. That map contains every real connection, so it scores almost perfectly on
            the count. But a map where every street exists tells you nothing about which
            routes traffic actually takes. Push a crisis through it and the crisis has
            nowhere to concentrate, so it behaves nothing like the real thing.
          </p>
          <p>
            Our proposal is to stop counting connections and start running crises. Take
            the real system and the fake one, hit both with the same disaster, and see
            whether the same sort of damage happens. That is a harder test, and a more
            useful one, because spreading crises is the only reason anyone wanted the map.
          </p>
          <p>
            Everything below is that argument with the numbers attached. There is also a
            crisis further down you can run yourself, one shock at a time, and watch banks
            fail in order.
          </p>
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
          Every measure, every method
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            The table above gives two summary scores. Those scores are averages of the
            measures below, and averages hide things, so here is everything that goes into
            them.
          </p>
          <p>
            Ten measures in three groups. The first group is the conventional test: does
            the method reproduce the real network&rsquo;s links and amounts. The second is
            the test we argue should replace it: does a crisis behave the same way. The
            third describes the shape of the network, which is not the claim but explains
            most of the second group&rsquo;s results.
          </p>
          <p>
            Read one row at a time and the argument appears without any interpretation
            from us. The evenly spread method wins the first group outright and loses the
            third by an order of magnitude.
          </p>
        </div>
        <div className="mt-8">
          <FullMetricsTable evaluation={evaluation} colours={colours} order={order} />
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          How good is our model, honestly
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            Good on the measure that matters, and it has one clear weakness we have not
            fixed.
          </p>
          <p>
            Against the two methods that are genuine alternatives, it wins. Its crisis
            behaviour is{" "}
            <span className="tabular">{model.protocol_score.mean.toFixed(3)}</span> away
            from the truth, against{" "}
            <span className="tabular">{dense.protocol_score.mean.toFixed(3)}</span> for the
            evenly spread method and{" "}
            <span className="tabular">
              {evaluation.methods.erdos_renyi.protocol_score.mean.toFixed(3)}
            </span>{" "}
            for random wiring. On the statistical test, its pattern of dangerous banks
            could not be told apart from the real system&rsquo;s in{" "}
            {Math.round(
              model.ks_debtrank.share_not_rejected_at_005 * model.n_samples,
            )}{" "}
            of {model.n_samples} attempts. The evenly spread method failed that test every
            single time, despite recovering every real link.
          </p>
          <p>
            The weakness: it understates how dangerous the typical bank is, by about a
            third. It does not produce quite enough very large single debts, and it is the
            rare large debt that makes one bank able to sink another. We report this
            rather than tuning it away. It is also the best argument for the test itself.
            A model built specifically for crisis realism still misses one of the
            measures, which is exactly what a test is supposed to catch.
          </p>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          Why one method beats ours, and why it does not count
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            The configuration model scores best of everything on the table, at{" "}
            <span className="tabular">
              {evaluation.methods.configuration.protocol_score.mean.toFixed(3)}
            </span>
            . It would be dishonest to leave it out, and misleading to leave it in without
            explaining what it is.
          </p>
          <p>
            It is not a way of building a banking system. It is a way of shuffling one you
            already have. It is handed the real network, told exactly how many
            counterparties each bank has and exactly what the full list of debt sizes is,
            and then it deals those same debts out to different pairs. It is a reshuffle
            of the answer.
          </p>
          <p>
            So it cannot do the job. Ask it to produce a banking system when you have no
            real one, which is the entire problem here, and it produces nothing: it has
            nothing to shuffle. It sits on the table as a ceiling, showing roughly how well
            anything could do while keeping the real degree structure. Our model gets
            within {(
              (evaluation.methods.vae.protocol_score.mean /
                evaluation.methods.configuration.protocol_score.mean -
                1) *
              100
            ).toFixed(0)}
            % of that ceiling having been shown none of it.
          </p>
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
            supervisory data. It is called the simulated ground truth throughout, never
            &ldquo;the real data&rdquo;.
          </p>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          What &ldquo;simulated&rdquo; actually means here
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            No file of real bank data is used anywhere in this project. Every number
            traces back to a single starting seed. It is worth being precise about what
            that does and does not mean.
          </p>
          <p>
            A recipe builds a banking system from scratch. Sixty banks. Six of them are
            marked as core. Then, for every possible pair, a coin is flipped to decide
            whether one owes the other anything, and the coin is weighted by who the two
            banks are: core banks lend to each other almost always, a periphery bank
            lends to another periphery bank about one time in fifty. Where a debt exists,
            its size is drawn from a distribution that produces many small debts and a few
            very large ones, with core banks involved in the larger. Each bank gets a
            size, and capital worth about 8% of it.
          </p>
          <p>
            Run that recipe three hundred times and you have the training set. The model
            sees those three hundred systems and nothing else. Run it once more, keep that
            one aside, and you have the system every method is scored against. The model
            never sees it. That is what makes the comparison meaningful: the model is
            being asked to invent a system like the ones it studied, and then judged
            against one it has never encountered.
          </p>
          <p>
            The recipe is not arbitrary. Its shape comes from what studies of real
            interbank markets report: very low density, a small tightly connected core, a
            long tail of small banks, and large banks connecting to small ones rather than
            to each other. Our simulated system reproduces those. Whether its numbers sit
            inside the published ranges is recorded separately and is still being checked
            against sources by hand.
          </p>
          <p>
            What simulation cannot do is guarantee that a real system would not surprise
            us in some way the recipe never considered. That is the honest limit, and no
            amount of sampling removes it.
          </p>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          Why not just use real data
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            The obvious objection. The answer is that the data does not exist in public in
            the form this needs.
          </p>
          <p>
            What is needed is a list of which bank owes which other bank how much.
            Supervisors collect exactly that and do not release it, because publishing a
            map of who is exposed to whom would itself be a financial stability risk. It
            names institutions and their weak points.
          </p>
          <p>
            The source people reach for first is the Bank for International Settlements,
            and it is worth being clear about why that does not work. The BIS publishes
            how much the banking system of one country is owed by the banking system of
            another. Countries, not banks. There are no individual institutions in it, so
            there is no network to extract. A paper claiming a sixty-bank network
            calibrated to BIS figures would be making a false claim, and we do not make
            it.
          </p>
          <p>
            There is a real improvement available, and it is worth naming because it is
            the next thing to do. The links between banks have to be invented. The
            balance sheets do not: bank sizes and capital ratios are published. Pinning
            those to real figures, while leaving the network generated, would change the
            claim from &ldquo;we invented a banking system&rdquo; to &ldquo;we invented
            the links between banks whose balance sheets match a real one&rdquo;. The
            machinery for that is in place and switched off, waiting on figures with
            citations attached.
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
          How a crisis actually spreads
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            A bank has things it owns and things it owes. The gap between them is its
            capital, and capital is what absorbs losses. Here it is about 8% of what a
            bank owns, which is roughly what regulators require. Lose less than that and
            you survive. Lose more and you cannot pay everyone.
          </p>
          <p>
            Most of what a bank owns is outside the banking system: loans to companies and
            households, government bonds, property. The shock hits that. It is the
            recession, the property crash, the sovereign losing its credit rating. This is
            the thing that starts a crisis, and it has nothing to do with the network.
          </p>
          <p>
            The network is what happens next. When a bank cannot pay, the banks it owed
            money to do not receive what they expected. That is a loss, and it lands on
            their capital, which was sized for ordinary times rather than for a
            counterparty disappearing. If it is large enough, they cannot pay either, and
            their creditors take the next loss.
          </p>
          <p>
            Two questions follow, and the two stress tests answer one each. How much
            damage can a single bank do by itself, before anyone actually fails? That is
            what the first chart measures. And when everyone is hit at once, how many banks
            end up unable to pay? That is the second.
          </p>
          <p>
            The second is the one you can watch below, because it settles in rounds. Round
            one is everyone the shock sank directly. Round two is everyone who was fine
            until round one stopped paying them. Round three is everyone sunk by round two.
            It keeps going until nobody new fails. Only round one is about the shock. Every
            round after it is the network, and those are the failures no amount of reading
            a single bank&rsquo;s accounts would have predicted.
          </p>
          <p>
            One result is worth knowing before you start. Past roughly a 25% shock the
            number of banks sunk directly stops growing. Their buffers are already gone, so
            a bigger shock cannot sink them any harder. Every additional failure after that
            point arrives through the network.
          </p>
        </div>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          Measuring it, method by method
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
          What the simulation below is doing, in plain terms
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            Give every bank a pile of things it owns and a list of people it owes. The
            slider destroys part of what every bank owns. That is the disaster: a property
            crash, a recession, a government defaulting.
          </p>
          <p>
            Then ask each bank one question in turn. After that loss, and after collecting
            whatever your debtors actually manage to pay you, can you still pay everyone
            you owe? If yes, nothing happens to you. If no, you turn red.
          </p>
          <p>
            The catch is that the answer depends on everyone else&rsquo;s answer. You
            cannot know what you will collect until you know who is paying. So the question
            is asked again, and again, until the answers stop changing. Each pass is one of
            the rounds you will see counted.
          </p>
          <p>
            That is the entire calculation. It is not a guess or a rule of thumb: it is the
            unique settlement where everybody pays exactly what they can and no more, and
            it has been the standard way of working this out since 2001.
          </p>
          <p>
            Two things make it worth watching rather than just reading. First, round one is
            the disaster and every round after it is the web, so you can see the difference
            directly. Second, the same disaster is applied to both systems at once, so any
            difference you see is the map, not the shock.
          </p>
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
          Which parts of the model earn their place
        </h2>
        <p className="mt-5 max-w-[62ch]">
          Five decisions went into the model, each added because measurement demanded it.
          Here each one is switched off in turn and the model retrained, to see how much
          worse it gets without it.
        </p>
        <div className="mt-8">
          <AblationTable ablations={ablations} />
        </div>
        <p className="mt-6 max-w-[62ch]">
          Four of the five earn their place. The last one does not: removing it changes
          nothing we can distinguish from noise. It was added for a reason that applies to
          how the ground truth is built rather than how the model decodes, so this test
          does not really reach it, and we leave the row in rather than quietly dropping a
          result that did not go our way.
        </p>
      </section>

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          What this would change
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            Regulators already run stress tests. They hit banks with a bad scenario and
            check who survives. What most of those tests cannot do well is the second part
            of this page: the failures that arrive through the network rather than from the
            shock. Doing that needs the map of who owes whom, and only the supervisor has
            it.
          </p>
          <p>
            So the method that gets used instead is the evenly spread reconstruction shown
            here. Its appeal is that it needs only totals, which are published. Its problem
            is visible in the picture it draws: everyone owes a little to everyone, nobody
            is dangerously exposed to anybody, and a failure has nowhere to concentrate.
            Our results say its picture of which banks are dangerous is distinguishable
            from the truth on every attempt, and that recovering all the real links did not
            save it.
          </p>
          <p>
            Three things change if generated networks can be trusted. A researcher with no
            supervisory access can develop and compare contagion methods on realistic
            systems. A regulator can hand a realistic network to outside researchers
            without disclosing anything about actual banks. And because the generator
            produces as many systems as you want, a policy can be tested against a thousand
            plausible banking systems instead of the single one that happens to exist,
            which is the only way to find out whether a rule is robust or merely lucky.
          </p>
          <p>
            None of that is worth anything if the generated networks fail in the wrong way.
            That is why the test comes first and the generator second.
          </p>
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

      <section className="border-t border-rule py-12 lg:py-16">
        <h2 className="font-display font-semibold tracking-tight text-2xl sm:text-3xl">
          Where this sits in the research literature
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-4">
          <p>
            This work sits at the meeting point of three bodies of research, and takes
            something from each.
          </p>
          <p>
            The first studied real interbank networks, using access researchers outside
            central banks do not have. Those studies are where the shape of our simulated
            system comes from: the small dense core, the sparse periphery, the fact that
            large banks connect to small ones rather than to each other.
          </p>
          <p>
            The second asked how to reconstruct a network you cannot see, from the totals
            you can. That is where the evenly spread method comes from, and it has been
            known for some time that it produces systems that look safer than reality. Our
            contribution to that thread is to show how far the problem goes: the method
            recovers every real link and is still rejected on every sample by the
            behavioural test.
          </p>
          <p>
            The third is machine learning on graphs, which is where the generator itself
            comes from. Ours is a variational graph autoencoder with three additions the
            contagion problem forced: a weight head, a balance-sheet head, and a per-bank
            popularity term.
          </p>
          <p>
            The claim we make is in none of those three. It is that the field is using the
            wrong acceptance criterion, and that a behavioural one should replace it.
          </p>
          <p className="text-sm text-ink/70">
            The full survey lives in <code>docs/related-work.md</code>. Every citation slot
            in it is marked <code>TODO-VERIFY</code> and is being checked by hand against
            publisher records. Nothing on this page cites a source we have not confirmed,
            which is why no names appear above.
          </p>
        </div>
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
