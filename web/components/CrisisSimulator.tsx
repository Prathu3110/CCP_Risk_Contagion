"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import NetworkPlot from "@/components/NetworkPlot";
import SeriesName from "@/components/SeriesName";
import {
  analyse,
  compare,
  describeRound,
  describeRun,
  describeSingleBank,
} from "@/lib/analysis";
import { cascadeRounds, toBalance, type CascadeRound } from "@/lib/contagion";
import { methodColours } from "@/lib/methods";
import type { MethodKey, Networks } from "@/lib/types";

const ROUND_MS = 750;

/**
 * A crisis the reader runs themselves.
 *
 * The clearing model is re-run in the browser at whatever shock is chosen,
 * rather than played back from precomputed frames, so any shock level and any
 * starting bank can be tried. `lib/contagion.ts` is a port of the Python and is
 * checked against it; the numbers here are the same ones behind the chart above.
 */
export default function CrisisSimulator({ networks }: { networks: Networks }) {
  const [comparison, setComparison] = useState<MethodKey>(networks.default_pair[1]);
  const [shock, setShock] = useState(0.15);
  const [selected, setSelected] = useState<number | null>(null);
  const [step, setStep] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [hoveredSlot, setHoveredSlot] = useState<number | null>(null);

  const colours = useMemo(() => methodColours(networks), [networks]);
  const truth = networks.default_pair[0];
  // Memoised because it is a useMemo dependency; a fresh array each render
  // would rerun every cascade.
  const sides = useMemo<[MethodKey, MethodKey]>(() => [truth, comparison], [truth, comparison]);

  const balances = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(networks.methods).map(([key, graph]) => [key, toBalance(graph)]),
      ),
    [networks],
  );

  const rounds = useMemo(() => {
    const run = (key: MethodKey): CascadeRound[] => {
      const balance = balances[key];
      // One bank can be singled out and wiped out entirely, on top of whatever
      // system-wide shock is set; that is how you test whether a bank is
      // systemic on its own.
      const vector = Array.from({ length: balance.n }, (_, i) =>
        i === selected ? 1 : shock,
      );
      return cascadeRounds(balance, vector);
    };
    return { observed: run(sides[0]), generated: run(sides[1]) };
  }, [balances, shock, selected, sides]);

  const lastStep = Math.max(rounds.observed.length, rounds.generated.length) - 1;
  // Derived rather than stored, so the run stops on its own when it reaches the
  // last round without an effect having to write state back.
  const isRunning = playing && step < lastStep;

  useEffect(() => {
    if (!isRunning) return;
    const timer = setTimeout(() => setStep((current) => current + 1), ROUND_MS);
    return () => clearTimeout(timer);
  }, [isRunning, step]);

  /** Changing the scenario rewinds it; doing that here keeps it out of an effect. */
  const rewind = useCallback(() => {
    setStep(-1);
    setPlaying(false);
  }, []);

  const changeShock = useCallback(
    (value: number) => {
      setShock(value);
      rewind();
    },
    [rewind],
  );

  const toggleSelected = useCallback(
    (id: number) => {
      setSelected((current) => (current === id ? null : id));
      rewind();
    },
    [rewind],
  );

  const run = useCallback(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setStep(lastStep);
      return;
    }
    setStep(-1);
    setPlaying(true);
  }, [lastStep]);

  const reset = useCallback(() => {
    setSelected(null);
    rewind();
  }, [rewind]);

  const stateFor = (side: "observed" | "generated") => {
    const series_rounds = rounds[side];
    if (step < 0) return { failed: new Set<number>(), justFailed: new Set<number>() };
    const round = series_rounds[Math.min(step, series_rounds.length - 1)];
    const isCurrent = step < series_rounds.length;
    return {
      failed: new Set(round.failed),
      justFailed: isCurrent ? new Set(round.newlyFailed) : new Set<number>(),
    };
  };

  const observed = stateFor("observed");
  const generated = stateFor("generated");
  const total = networks.n_nodes;

  const settled = step >= lastStep;
  const analysis = {
    observed: analyse(rounds.observed, networks.methods[sides[0]], step),
    generated: analyse(rounds.generated, networks.methods[sides[1]], step),
  };

  // The log is rebuilt from the rounds rather than accumulated in state, so
  // scrubbing or re-running can never leave a stale entry behind.
  const log =
    step < 0
      ? []
      : Array.from({ length: step + 1 }, (_, index) => {
          const forSeries = (side: "observed" | "generated") => {
            const list = rounds[side];
            const round = list[index];
            if (!round) return null;
            const running = round.failed.length;
            return describeRound(index, round.newlyFailed.length, running);
          };
          return { index, observed: forSeries("observed"), generated: forSeries("generated") };
        }).filter((entry) => entry.observed || entry.generated);

  return (
    <div>
      <div className="flex flex-wrap items-end gap-x-8 gap-y-5">
        <label className="flex flex-col gap-2">
          <span className="text-sm">
            Destroy{" "}
            <span className="tabular">{Math.round(shock * 100)}%</span> of every
            bank&rsquo;s outside assets
          </span>
          <input
            type="range"
            min={0}
            max={50}
            step={1}
            value={Math.round(shock * 100)}
            onChange={(event) => changeShock(Number(event.target.value) / 100)}
            className="w-72 max-w-full accent-[var(--color-stress)]"
          />
        </label>

        <fieldset className="border-0 p-0 m-0">
          <legend className="text-sm mb-2">Run it against</legend>
          <div className="flex flex-wrap gap-2">
            {Object.values(networks.methods)
              .filter((method) => method.key !== truth)
              .map((method) => {
                const active = method.key === comparison;
                return (
                  <button
                    key={method.key}
                    type="button"
                    onClick={() => {
                      setComparison(method.key);
                      rewind();
                    }}
                    aria-pressed={active}
                    className="border px-3 py-1 text-sm"
                    style={{
                      borderColor: active ? colours[method.key] : "var(--color-rule)",
                      color: "var(--color-ink)",
                      borderWidth: active ? 2 : 1,
                    }}
                  >
                    {method.label}
                  </button>
                );
              })}
          </div>
        </fieldset>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={run}
            disabled={isRunning}
            className="border border-ink px-4 py-1.5 hover:bg-ink hover:text-paper disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-ink"
          >
            {isRunning ? "Running" : "Run the crisis"}
          </button>
          <button
            type="button"
            onClick={reset}
            className="border border-rule px-4 py-1.5 hover:border-ink"
          >
            Reset
          </button>
        </div>
      </div>

      <p className="mt-5 text-sm text-ink/70 min-h-6" aria-live="polite">
        {step < 0
          ? selected === null
            ? "Nothing has happened yet. Press run, or click any bank first to wipe that one out as well."
            : `Bank ${selected} will be wiped out completely, on top of the shock above. Press run.`
          : `Round ${step + 1}. ${observed.failed.size} of ${total} banks have failed in the real system, ${generated.failed.size} of ${total} in ${networks.methods[comparison].label.toLowerCase()}.`}
      </p>

      <div className="mt-8 grid gap-x-10 gap-y-8 sm:grid-cols-2">
        {sides.map((key, index) => {
          const state = index === 0 ? observed : generated;
          const graph = networks.methods[key];
          const dense = graph.edges.length / (total * (total - 1)) > 0.4;
          return (
            <figure key={`${key}-${index}`} className="m-0">
              <NetworkPlot
                graph={graph}
                colour={colours[key]}
                edgeOpacity={dense ? 0.08 : index === 0 ? 0.34 : 0.42}
                name={graph.label}
                revealStartMs={0}
                animate={false}
                hoveredSlot={hoveredSlot}
                onHoverSlot={setHoveredSlot}
                failed={state.failed}
                justFailed={state.justFailed}
                selected={selected}
                onSelect={toggleSelected}
              />
              <figcaption className="mt-3">
                <SeriesName label={graph.label} colour={colours[key]} />
                <span className="tabular text-stress ml-3">
                  {state.failed.size} of {total} failed
                </span>
              </figcaption>
            </figure>
          );
        })}
      </div>

      {step >= 0 && (
        <div className="mt-10 border-t border-rule pt-8">
          <h3 className="font-display font-semibold tracking-tight text-lg">
            What is happening
          </h3>

          <ol className="mt-4 space-y-3 max-w-[62ch]">
            {log.map((entry) => (
              <li key={entry.index} className="grid grid-cols-[auto_1fr] gap-x-4">
                <span className="tabular text-sm text-ink/50 pt-0.5">
                  {String(entry.index + 1).padStart(2, "0")}
                </span>
                <span className="space-y-1">
                  {entry.observed && (
                    <span className="block text-sm">
                      <span className="text-observed">Real system.</span>{" "}
                      {entry.observed}
                    </span>
                  )}
                  {entry.generated && (
                    <span className="block text-sm">
                      <SeriesName
                        label={`${networks.methods[comparison].label}.`}
                        colour={colours[comparison]}
                      />{" "}
                      {entry.generated}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ol>

          {settled && (
            <div className="mt-8 space-y-6 max-w-[62ch]">
              {selected !== null && (
                <p className="text-sm">
                  {describeSingleBank(selected, analysis.observed, shock > 0)}
                </p>
              )}

              <div>
                <p className="text-sm"><SeriesName label={`In ${networks.methods[truth].label.toLowerCase()}`} colour={colours[truth]} /></p>
                {describeRun(analysis.observed, total).map((line) => (
                  <p key={line} className="mt-2 text-sm">
                    {line}
                  </p>
                ))}
              </div>

              <div>
                <p className="text-sm"><SeriesName label={`In ${networks.methods[comparison].label.toLowerCase()}`} colour={colours[comparison]} /></p>
                {describeRun(analysis.generated, total).map((line) => (
                  <p key={line} className="mt-2 text-sm">
                    {line}
                  </p>
                ))}
              </div>

              <div className="border-t border-rule pt-6">
                <p className="text-sm">So what does the comparison say?</p>
                {compare(analysis.observed, analysis.generated, total).map((line) => (
                  <p key={line} className="mt-2 text-sm">
                    {line}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
