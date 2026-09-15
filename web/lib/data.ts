/**
 * Build-time data access.
 *
 * The three files are static output from the research pipeline, so they are
 * imported directly rather than fetched. Nothing on the page loads at runtime
 * and there are no loading states anywhere in the app.
 */
import contagionJson from "@/public/data/contagion.json";
import metricsJson from "@/public/data/metrics.json";
import networksJson from "@/public/data/networks.json";

import type { Contagion, Metrics, Networks } from "./types";

export const networks = networksJson as Networks;
export const metrics = metricsJson as Metrics;
export const contagion = contagionJson as Contagion;
