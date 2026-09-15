import type { Histogram } from "./types";

/** Bin two series of raw values onto one shared set of edges. */
export function sharedHistogram(
  observed: number[],
  generated: number[],
  binCount: number,
): Histogram {
  const all = [...observed, ...generated];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const width = (max - min) / binCount || 1;

  const bins = Array.from({ length: binCount + 1 }, (_, i) => min + i * width);
  const count = (values: number[]) => {
    const counts = new Array<number>(binCount).fill(0);
    for (const value of values) {
      const index = Math.min(binCount - 1, Math.floor((value - min) / width));
      counts[index] += 1;
    }
    return counts;
  };

  return { bins, observed: count(observed), generated: count(generated) };
}

export const mean = (values: number[]) =>
  values.reduce((total, value) => total + value, 0) / values.length;
