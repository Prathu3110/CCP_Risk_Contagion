/**
 * Build-time data access.
 *
 * The three files are static output from the research pipeline, so they are
 * imported directly rather than fetched. Nothing on the page loads at runtime
 * and there are no loading states anywhere in the app.
 */
import ablationsJson from "@/public/data/ablations.json";
import contagionJson from "@/public/data/contagion.json";
import evaluationJson from "@/public/data/evaluation.json";
import metricsJson from "@/public/data/metrics.json";
import networksJson from "@/public/data/networks.json";

import type { Ablations, Contagion, Evaluation, Metrics, Networks } from "./types";

export const networks = networksJson as unknown as Networks;
export const metrics = metricsJson as unknown as Metrics;
export const contagion = contagionJson as unknown as Contagion;
export const evaluation = evaluationJson as unknown as Evaluation;
export const ablations = ablationsJson as unknown as Ablations;
