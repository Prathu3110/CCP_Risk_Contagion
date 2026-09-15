"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import NetworkPlot from "@/components/NetworkPlot";
import { cascadeRounds, toBalance, type CascadeRound } from "@/lib/contagion";
import type { Networks, Series } from "@/lib/types";

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
  const [shock, setShock] = useState(0.15);
  const [selected, setSelected] = useState<number | null>(null);
  const [step, setStep] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [hoveredSlot, setHoveredSlot] = useState<number | null>(null);

  const balances = useMemo(
    () => ({
      observed: toBalance(networks.observed),
      generated: toBalance(networks.generated),
    }),
    [networks],
  );

  const rounds = useMemo(() => {
    const run = (series: Series): CascadeRound[] => {
      const balance = balances[series];
      // One bank can be singled out and wiped out entirely, on top of whatever
      // system-wide shock is set; that is how you test whether a bank is
      // systemic on its own.
      const vector = Array.from({ length: balance.n }, (_, i) =>
        i === selected ? 1 : shock,
      );
      return cascadeRounds(balance, vector);
    };
    return { observed: run("observed"), generated: run("generated") };
  }, [balances, shock, selected]);

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

  const stateFor = (series: Series) => {
    const series_rounds = rounds[series];
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
            ? "Nothing has happened yet. Press run, or click any bank to wipe out that one bank on its own."
            : `Bank ${selected} will be wiped out completely. Press run to see who it takes with it.`
          : `Round ${step + 1}. ${observed.failed.size} of ${total} banks have failed in the observed system, ${generated.failed.size} of ${total} in the generated one.`}
      </p>

      <div className="mt-8 grid gap-x-10 gap-y-8 sm:grid-cols-2">
        {(["observed", "generated"] as Series[]).map((series) => {
          const state = series === "observed" ? observed : generated;
          return (
            <figure key={series} className="m-0">
              <NetworkPlot
                graph={networks[series]}
                series={series}
                name={`${series} system`}
                revealStartMs={0}
                animate={false}
                hoveredSlot={hoveredSlot}
                onHoverSlot={setHoveredSlot}
                failed={state.failed}
                justFailed={state.justFailed}
                selected={selected}
                onSelect={toggleSelected}
              />
              <figcaption
                className={`mt-3 ${series === "observed" ? "text-observed" : "text-generated"}`}
              >
                {series === "observed" ? "Observed system" : "Generated system"}
                <span className="tabular text-stress ml-3">
                  {state.failed.size} of {total} failed
                </span>
              </figcaption>
            </figure>
          );
        })}
      </div>
    </div>
  );
}
