/**
 * Mirrors the JSON contract in section 3 of CCP-DEMO-BUILD-PLAN.md.
 *
 * These three files are written by `research/scripts/run_demo.py` and read at
 * build time. If you change a shape here, change `research/src/export.py` too.
 */

/** Which of the two systems a value belongs to. Drives colour everywhere. */
export type Series = "observed" | "generated";

export interface NetworkNode {
  id: number;
  /** Rank by number of counterparties, 0 being the busiest. */
  slot: number;
  /** Normalised 0-1 layout coordinates, computed in Python. */
  x: number;
  y: number;
  /** Total assets, scaled so the largest bank is 1. Sets the dot size only. */
  assets: number;
  core: boolean;
  /* Raw balance-sheet figures, not normalised: the page re-runs the contagion
     models on these and a crisis is not scale-invariant. */
  equity: number;
  ext_assets: number;
  ext_liabilities: number;
}

/** `s` owes `t` an amount `w`. */
export interface NetworkEdge {
  s: number;
  t: number;
  w: number;
}

export interface NetworkGraph {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface Networks {
  n_nodes: number;
  observed: NetworkGraph;
  generated: NetworkGraph;
}

export interface TrainingCurve {
  epochs: number[];
  loss: number[];
}

/** Counts per bin, with one set of bin edges shared by both series. */
export interface Histogram {
  bins: number[];
  observed: number[];
  generated: number[];
}

export interface SummaryRow {
  name: string;
  observed: number;
  generated: number;
  gap_pct: number;
}

export interface Metrics {
  training: TrainingCurve;
  degree_hist: Histogram;
  weight_hist: Histogram;
  summary: SummaryRow[];
}

/** Mean and a 10th-90th percentile band across repeats, one entry per shock. */
export interface Band {
  mean: number[];
  lo: number[];
  hi: number[];
}

export interface Cascade {
  shock: number[];
  observed: Band;
  generated: Band;
}

export interface Contagion {
  /** One DebtRank value per bank, from shocking that bank alone. */
  debtrank: Record<Series, number[]>;
  cascade: Cascade;
}
