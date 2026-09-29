/** Binning helpers for values the pipeline ships raw, such as DebtRank. */

/** Equal-width bin edges spanning every value given. */
export function binEdges(values: number[], count: number): number[] {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = (max - min) / count || 1;
  return Array.from({ length: count + 1 }, (_, i) => min + i * width);
}

/** Count values into bins defined by `edges`, clamping the ends. */
export function countInto(values: number[], edges: number[]): number[] {
  const counts = new Array<number>(edges.length - 1).fill(0);
  const width = edges[1] - edges[0];
  for (const value of values) {
    const index = Math.min(counts.length - 1, Math.max(0, Math.floor((value - edges[0]) / width)));
    counts[index] += 1;
  }
  return counts;
}

export const mean = (values: number[]) =>
  values.reduce((total, value) => total + value, 0) / values.length;
