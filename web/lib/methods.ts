/**
 * Colour and ordering for the five methods.
 *
 * Colour is derived from `role`, never from a method name, so a sixth method
 * needs only a JSON entry. Ink blue and amber stay reserved for the two systems
 * being compared; the baselines are a deliberately unaccented grey ramp whose
 * value order says how much each is told about the network it reproduces.
 */
import type { MethodKey, Networks, Role } from "./types";

const BASELINE_RAMP = [
  "var(--color-baseline-1)",
  "var(--color-baseline-2)",
  "var(--color-baseline-3)",
];

export function methodColours(networks: Networks): Record<MethodKey, string> {
  const colours: Record<MethodKey, string> = {};
  let baseline = 0;
  for (const method of Object.values(networks.methods)) {
    if (method.role === "observed") colours[method.key] = "var(--color-observed)";
    else if (method.role === "ours") colours[method.key] = "var(--color-generated)";
    else {
      colours[method.key] = BASELINE_RAMP[Math.min(baseline, BASELINE_RAMP.length - 1)];
      baseline += 1;
    }
  }
  return colours;
}

/** Page order: the ground truth, then ours, then the baselines. */
export function methodOrder(networks: Networks): MethodKey[] {
  return Object.keys(networks.methods);
}

export const roleOf = (networks: Networks, key: MethodKey): Role =>
  networks.methods[key].role;

export const labelOf = (networks: Networks, key: MethodKey): string =>
  networks.methods[key].label;
