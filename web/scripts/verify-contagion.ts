/**
 * Checks the browser ports in lib/contagion.ts against research/src/contagion.py.
 *
 * Two implementations of the same algorithm drift. This runs both models at a
 * sweep of uniform shock levels and prints numbers that must match the Python
 * exactly; run `python3 research/scripts/verify_contagion.py` for the other half.
 */
import networksJson from "../public/data/networks.json";
import { cascadeRounds, debtRankScore, distressRounds, toBalance } from "../lib/contagion";
import type { Networks } from "../lib/types";

const networks = networksJson as unknown as Networks;

for (const series of ["observed", "vae"] as const) {
  const balance = toBalance(networks.methods[series]);
  const cascade: string[] = [];
  for (let shock = 0.05; shock <= 0.501; shock += 0.05) {
    const rounds = cascadeRounds(balance, new Array(balance.n).fill(shock));
    const failed = rounds[rounds.length - 1].failed.length;
    cascade.push((failed / balance.n).toFixed(6));
  }

  const scores: number[] = [];
  for (let seed = 0; seed < balance.n; seed += 1) {
    scores.push(debtRankScore(balance, distressRounds(balance, seed, 0.5), seed));
  }
  const meanScore = scores.reduce((a, b) => a + b, 0) / scores.length;

  console.log(`${series} cascade ${cascade.join(" ")}`);
  console.log(
    `${series} debtrank mean ${meanScore.toFixed(6)} max ${Math.max(...scores).toFixed(6)}`,
  );
}
