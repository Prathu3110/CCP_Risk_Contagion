/**
 * Mirrors the JSON written by `research/src/export.py`.
 *
 * The contract carries every method rather than a fixed observed/generated
 * pair, so adding a sixth needs only a new entry in the JSON. Colour is keyed
 * to `role`, never to a method name.
 *
 * If you change a shape here, change `research/src/export.py` too.
 */

/** Drives colour everywhere: ink blue, amber, or the grey ramp. */
export type Role = "observed" | "ours" | "baseline";

export type MethodKey = string;

export interface NetworkNode {
  id: number;
  /** Rank by number of counterparties, 0 being the busiest. */
  slot: number;
  /** Normalised 0-1 layout coordinates, computed once on the observed network. */
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

export interface MethodNetwork extends NetworkGraph {
  key: MethodKey;
  label: string;
  role: Role;
}

export interface Networks {
  n_nodes: number;
  /** The two methods the page opens on. */
  default_pair: [MethodKey, MethodKey];
  methods: Record<MethodKey, MethodNetwork>;
}

export interface TrainingCurve {
  epochs: number[];
  loss: number[];
}

/** Counts per bin, with one set of bin edges shared by every method. */
export interface MultiHistogram {
  bins: number[];
  by_method: Record<MethodKey, number[]>;
}

export interface SummaryRow {
  name: string;
  observed: number;
  generated: number;
  gap_pct: number;
}

export interface Metrics {
  training: TrainingCurve;
  degree_hist: MultiHistogram;
  weight_hist: MultiHistogram;
  summary: { by_method: Record<MethodKey, SummaryRow[]> };
}

/** Mean and a 10th-90th percentile band across repeats, one entry per shock. */
export interface Band {
  mean: number[];
  lo: number[];
  hi: number[];
}

export interface Contagion {
  shock: number[];
  by_method: Record<MethodKey, { debtrank: number[]; cascade: Band }>;
}

/** Mean with a 95% bootstrap interval across ensemble samples. */
export interface Interval {
  mean: number;
  lo: number;
  hi: number;
}

export interface MethodEvaluation {
  label: string;
  /** What this method is shown about the network it must reproduce. */
  sees: string;
  n_samples: number;
  edge_recall: Interval;
  edge_f1: Interval;
  protocol_score: Interval;
  structure_score: Interval;
  ks_debtrank: {
    /** HIGH is the desired outcome: the two cannot be told apart. */
    median_p: number;
    share_not_rejected_at_005: number;
  };
}

export interface Evaluation {
  seed: number;
  samples: number;
  methods: Record<MethodKey, MethodEvaluation>;
}
