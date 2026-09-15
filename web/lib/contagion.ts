/**
 * Browser ports of the two contagion models in `research/src/contagion.py`.
 *
 * These exist so a crisis can be run live on the page, at any shock level the
 * reader picks, rather than only at the ten levels the pipeline precomputed.
 * They return the state after every round, because the point is to watch the
 * failure spread rather than to be told the total.
 *
 * Both follow the same convention as the Python: A[i][j] is the amount bank i
 * owes bank j, so j is the one that loses when i cannot pay. Any change here
 * must be mirrored there; `npm run verify:contagion` checks the two agree.
 */
import type { NetworkGraph } from "./types";

const MAX_ROUNDS = 200;
const TOL = 1e-10;

export interface Balance {
  /** Dense n x n matrix, A[i][j] = what i owes j. */
  A: number[][];
  equity: number[];
  extAssets: number[];
  extLiabilities: number[];
  /** Row sums: each bank's total interbank obligations. */
  obligations: number[];
  n: number;
}

/** Build the dense matrices once per network; the drawings ship edge lists. */
export function toBalance(graph: NetworkGraph): Balance {
  const n = graph.nodes.length;
  const byId = new Map(graph.nodes.map((node) => [node.id, node]));
  const A = Array.from({ length: n }, () => new Array<number>(n).fill(0));
  for (const edge of graph.edges) A[edge.s][edge.t] = edge.w;

  const at = (index: number, field: "equity" | "ext_assets" | "ext_liabilities") =>
    byId.get(index)?.[field] ?? 0;

  return {
    A,
    n,
    equity: Array.from({ length: n }, (_, i) => at(i, "equity")),
    extAssets: Array.from({ length: n }, (_, i) => at(i, "ext_assets")),
    extLiabilities: Array.from({ length: n }, (_, i) => at(i, "ext_liabilities")),
    obligations: A.map((row) => row.reduce((total, value) => total + value, 0)),
  };
}

export interface CascadeRound {
  /** Ids of every bank that cannot pay in full by the end of this round. */
  failed: number[];
  /** Ids that failed in this round only, for highlighting what just happened. */
  newlyFailed: number[];
}

/**
 * Eisenberg & Noe (2001) clearing payments, by fictitious default.
 *
 * Start by assuming everyone pays in full, then repeatedly recompute. Each pass
 * discovers the banks that cannot meet their obligations given what they
 * themselves received, which is exactly one round of the cascade. The sequence
 * decreases monotonically and converges to the greatest clearing vector.
 */
export function cascadeRounds(balance: Balance, shock: number[]): CascadeRound[] {
  const { A, n, obligations, extAssets, extLiabilities } = balance;

  const relative = A.map((row, i) =>
    obligations[i] > 0 ? row.map((value) => value / obligations[i]) : row.map(() => 0),
  );
  const resources = Array.from({ length: n }, (_, i) =>
    Math.max(0, extAssets[i] * (1 - shock[i]) - extLiabilities[i]),
  );

  let payments = [...obligations];
  const rounds: CascadeRound[] = [];
  const seen = new Set<number>();

  for (let round = 0; round < MAX_ROUNDS; round += 1) {
    const received = new Array<number>(n).fill(0);
    for (let i = 0; i < n; i += 1) {
      if (payments[i] === 0) continue;
      for (let j = 0; j < n; j += 1) {
        if (relative[i][j] !== 0) received[j] += relative[i][j] * payments[i];
      }
    }

    const updated = Array.from({ length: n }, (_, i) =>
      Math.min(obligations[i], Math.max(0, resources[i] + received[i])),
    );
    const settled = updated.every((value, i) => Math.abs(value - payments[i]) < TOL);
    payments = updated;

    const newlyFailed: number[] = [];
    for (let i = 0; i < n; i += 1) {
      if (payments[i] < obligations[i] - 1e-8 && !seen.has(i)) {
        seen.add(i);
        newlyFailed.push(i);
      }
    }
    if (newlyFailed.length > 0 || rounds.length === 0) {
      rounds.push({ failed: [...seen], newlyFailed });
    }
    if (settled) break;
  }

  return rounds;
}

export interface DistressRound {
  /** Distress in [0, 1] for every bank, after this round. */
  distress: number[];
  /** Ids that took new damage this round. */
  newlyHit: number[];
}

/**
 * Battiston et al. (2012) DebtRank, seeded on one bank.
 *
 * A bank passes distress on only in the round after it receives some, then goes
 * quiet. That one-shot rule is what stops distress circulating forever around a
 * lending cycle and being counted many times over.
 */
export function distressRounds(
  balance: Balance,
  seed: number,
  initialShock: number,
): DistressRound[] {
  const { A, n, equity } = balance;
  // impact[i][j] is the share of j's equity wiped out if i's debt is written off.
  const impact = A.map((row) => row.map((value, j) => Math.min(1, value / Math.max(equity[j], TOL))));

  const distress = new Array<number>(n).fill(0);
  distress[seed] = Math.min(1, Math.max(0, initialShock));

  let speaking = new Set<number>([seed]);
  const untouched = new Set<number>(Array.from({ length: n }, (_, i) => i));
  untouched.delete(seed);

  const rounds: DistressRound[] = [{ distress: [...distress], newlyHit: [seed] }];

  for (let round = 0; round < MAX_ROUNDS && speaking.size > 0; round += 1) {
    const incoming = new Array<number>(n).fill(0);
    for (const i of speaking) {
      for (let j = 0; j < n; j += 1) {
        if (A[i][j] !== 0 && untouched.has(j)) incoming[j] += impact[i][j] * distress[i];
      }
    }

    const newlyHit: number[] = [];
    for (let j = 0; j < n; j += 1) {
      if (incoming[j] > TOL && untouched.has(j)) {
        distress[j] = Math.min(1, distress[j] + incoming[j]);
        newlyHit.push(j);
      }
    }
    for (const j of newlyHit) untouched.delete(j);
    speaking = new Set(newlyHit);
    if (newlyHit.length === 0) break;
    rounds.push({ distress: [...distress], newlyHit });
  }

  return rounds;
}

/** Share of the system's economic value destroyed, matching the Python. */
export function debtRankScore(balance: Balance, rounds: DistressRound[], seed: number): number {
  const value = Array.from({ length: balance.n }, (_, j) =>
    balance.A.reduce((total, row) => total + row[j], 0),
  );
  const total = value.reduce((sum, v) => sum + v, 0);
  if (total <= 0) return 0;
  const final = rounds[rounds.length - 1].distress;
  const spread = final.reduce((sum, h, j) => sum + h * value[j], 0);
  return (spread - rounds[0].distress[seed] * value[seed]) / total;
}
