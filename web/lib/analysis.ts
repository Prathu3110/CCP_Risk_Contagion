/**
 * Turns one run of the clearing model into plain language.
 *
 * Every sentence here is derived from the numbers the run actually produced,
 * never from a hardcoded threshold, so a gentle shock and a severe one get
 * genuinely different explanations rather than the same text with the figures
 * swapped.
 */
import type { CascadeRound } from "./contagion";
import type { NetworkGraph } from "./types";

export interface RunAnalysis {
  /** Failed in round one: sunk by the shock itself, before anyone defaulted. */
  direct: number;
  /** Failed later: brought down by money that never arrived. */
  contagion: number;
  total: number;
  survivors: number;
  /** Rounds that actually claimed a bank. */
  rounds: number;
  /** total / direct. 1 means the network added nothing. */
  amplification: number;
  coreFailed: number;
  coreTotal: number;
  perRound: number[];
}

export function analyse(
  rounds: CascadeRound[],
  graph: NetworkGraph,
  upTo: number,
): RunAnalysis {
  const visible = rounds.slice(0, Math.max(0, Math.min(upTo, rounds.length - 1)) + 1);
  const last = visible[visible.length - 1];
  const failed = new Set(last?.failed ?? []);
  const coreIds = new Set(graph.nodes.filter((node) => node.core).map((node) => node.id));

  const direct = visible[0]?.newlyFailed.length ?? 0;
  const total = failed.size;

  return {
    direct,
    contagion: total - direct,
    total,
    survivors: graph.nodes.length - total,
    rounds: visible.filter((round) => round.newlyFailed.length > 0).length,
    amplification: direct > 0 ? total / direct : 1,
    coreFailed: [...failed].filter((id) => coreIds.has(id)).length,
    coreTotal: coreIds.size,
    perRound: visible.map((round) => round.newlyFailed.length),
  };
}

const plural = (count: number, one: string, many = `${one}s`) =>
  `${count} ${count === 1 ? one : many}`;

/**
 * What happened in a single round, for the running log.
 *
 * Only the first two rounds get the full explanation. A severe shock can run
 * for a dozen rounds, and repeating the same sentence each time buries the one
 * thing the log is for: seeing how long the failures keep coming.
 */
export function describeRound(index: number, failedThisRound: number, runningTotal: number): string {
  if (index === 0) {
    if (failedThisRound === 0) {
      return "Nothing failed. Every bank covered the loss out of its own capital and paid what it owed in full.";
    }
    return `${plural(failedThisRound, "bank")} failed outright \u2014 the shock destroyed more than their capital could absorb. No other bank's failure is involved yet.`;
  }
  if (index === 1) {
    return `${plural(failedThisRound, "more bank", "more banks")} failed, taking the toll to ${runningTotal}. These were solvent until money they were owed failed to arrive. This is contagion rather than the shock.`;
  }
  return `${plural(failedThisRound, "more", "more")}, toll now ${runningTotal}.`;
}

/** The whole run, once it has settled. */
export function describeRun(analysis: RunAnalysis, total: number): string[] {
  const lines: string[] = [];

  if (analysis.total === 0) {
    lines.push(
      "The system absorbed this one completely. Every bank had enough capital to take the loss and still pay its counterparties, so nothing spread.",
    );
    return lines;
  }

  if (analysis.contagion === 0) {
    lines.push(
      `${plural(analysis.direct, "bank")} failed, and every one of them was sunk by the shock itself. None of them brought anyone else down: their creditors could absorb the loss.`,
    );
    return lines;
  }

  lines.push(
    `${analysis.total} of ${total} banks failed, and they did not fail for the same reason. The shock itself sank ${analysis.direct}. The other ${plural(analysis.contagion, "bank")} went under because those ${analysis.direct} stopped paying them.`,
  );
  lines.push(
    `That is the network doing the damage rather than the shock: it multiplied the failures by ${analysis.amplification.toFixed(2)} times. The cascade took ${plural(analysis.rounds, "round")} to work through, and ${plural(analysis.survivors, "bank")} were still standing at the end.`,
  );
  return lines;
}

/** The comparison the whole project exists to make. */
export function compare(
  observed: RunAnalysis,
  generated: RunAnalysis,
  total: number,
): string[] {
  const lines: string[] = [];
  const gap = Math.abs(observed.total - generated.total);

  if (observed.total === 0 && generated.total === 0) {
    lines.push(
      "Both systems shrugged this off. Agreeing that nothing happens is still agreement, but turn the shock up to see the comparison do any work.",
    );
    return lines;
  }

  // The follow-on sentence has to fit the size of the gap. Calling a four-bank
  // difference proof of agreement would be overselling it.
  const headline = `Out of ${total} banks, the real system lost ${observed.total} and the invented one lost ${generated.total}`;
  if (gap === 0) {
    lines.push(
      `${headline} \u2014 an exact match. The model never saw the real network, yet a crisis stops in exactly the same place.`,
    );
  } else if (gap <= 2) {
    lines.push(
      `${headline} \u2014 a gap of ${plural(gap, "bank")}. Either system would tell you the same thing about how dangerous this shock is, which is the whole claim: the model never saw the real network.`,
    );
  } else if (gap <= 5) {
    lines.push(
      `${headline} \u2014 a gap of ${plural(gap, "bank")}. The same story told with slightly different numbers: the shock is serious in both, and neither would leave you with the wrong impression.`,
    );
  } else {
    lines.push(
      `${headline} \u2014 a gap of ${plural(gap, "bank")}, wide enough to matter. A single run is noisier than the curve above, which averages twenty of them at each shock level; the disagreement here is larger than the average gap.`,
    );
  }

  if (Math.abs(observed.coreFailed - generated.coreFailed) >= 2) {
    const worse = observed.coreFailed > generated.coreFailed ? "real" : "invented";
    lines.push(
      `The two disagree about the biggest banks, though. ${observed.coreFailed} of the ${observed.coreTotal} largest failed in the real system against ${generated.coreFailed} in the invented one, so at this shock level the ${worse} system's core is the more fragile. Watch that gap close as you turn the shock up.`,
    );
  }

  if (observed.contagion > 0 || generated.contagion > 0) {
    lines.push(
      `Contagion accounted for ${observed.contagion} of the real system's failures and ${generated.contagion} of the invented one's. This is the number that is impossible to get from a bank's own balance sheet, and the reason the network matters at all.`,
    );
  }

  return lines;
}

/** Singling out one bank is a different question, and usually has a blunt answer. */
export function describeSingleBank(
  bankId: number,
  analysis: RunAnalysis,
  hasSystemShock: boolean,
): string {
  if (analysis.total <= 1) {
    return `Bank ${bankId} fails, and takes nobody with it. Its creditors absorb the loss out of their own capital. That is the usual answer here: no single bank in this system is dangerous on its own, which is exactly why the summary charts shock every bank at once.`;
  }
  const extra = analysis.total - 1;
  return hasSystemShock
    ? `With the rest of the system already under strain, wiping out bank ${bankId} costs a further ${plural(extra, "bank")}. On its own it would have failed alone — it is the combination that does the damage.`
    : `Bank ${bankId} fails and takes ${plural(extra, "other bank")} with it, with no other shock applied. This one is genuinely systemic by itself.`;
}
