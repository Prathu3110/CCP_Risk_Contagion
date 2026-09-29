# Web & Figure Plan — visual integration

Companion to `PAPER-EXECUTION-PLAN.md`. The research stages there produce numbers; these
stages turn them into the paper's figures and update the page so it argues the new thesis.

**Run each W-stage after its matching research stage, not at the end.** W1 is the only one
the paper itself needs.

---

## 0. Skills to load, and the rule when they conflict

Tell Claude Code to load these before the relevant stage. Names may differ slightly in your
local install — run `/plugin` first and use whatever they're actually called there.

| Stage | Load |
|---|---|
| W1, W3, W4 | `dataviz` |
| W3 | `frontend-design` |
| W5 | `design:ux-copy` |
| W6 | `design:design-critique`, `design:accessibility-review` |

**The conflict rule, which must go in every prompt below:**

> This repo's `CLAUDE.md` defines a semantic colour system, a banned-treatments list, and a
> no-chart-library rule. Those are project constraints and they **override any palette,
> component pattern, or default the skill proposes**. Load the skill for its method —
> chart-form selection, scale and axis discipline, contrast checking, layout judgement —
> not for its tokens. If the skill's guidance and `CLAUDE.md` disagree, `CLAUDE.md` wins
> and you say so rather than silently picking one.

This matters most with `dataviz`, which ships its own palette. Taking it would destroy the
blue/amber/red semantics the whole page is built on.

---

## 1. The four-method colour decision

Adding baselines means five series where the design allows two. The resolution, which you
should paste into the prompts and also state in the paper's figure captions:

```
observed          ink blue    #2E5E8C   the simulated ground truth
our model         amber       #C8842A   the generative VAE
maximum entropy   grey 700    #4A4F58   ─┐
configuration     grey 500    #7C828C    ├ existing methods, deliberately unaccented
Erdős–Rényi       grey 400    #9BA1AA   ─┘
default / breach  deep red    #A3302B   unchanged, still means only this
```

Rationale to keep: the two hues stay reserved for the two systems being compared. The
baselines are a *set*, not three individuals — the reader needs to see "the field's methods
cluster over here," not to track which grey is which. Greys of increasing value order them
by how much structure they preserve (max-entropy most, ER least), so the grey ramp itself
encodes information.

---

## 2. W1 — Paper figures to publication standard

**This is the only web-plan stage the paper needs. Do it, even if you skip everything else.**

Print figures have different constraints from screen figures: they'll be viewed at ~3in
wide in a two-column layout, possibly greyscale-printed, and they must be legible without
the hover that a web chart leans on.

> Load the `dataviz` skill. Apply the conflict rule at the top of `WEB-PLAN.md`: this
> project's semantic palette in `CLAUDE.md` overrides the skill's palette, and the
> five-series mapping in section 1 of that file is fixed.
>
> Rework `research/scripts/make_figure.py`, `make_tradeoff_figure.py` and
> `make_ensemble_figure.py` to publication standard:
>
> - Vector PDF output at a 3.3in single-column and 6.9in double-column width. Set figure
>   size explicitly; never rely on `bbox_inches='tight'` to rescale type.
> - Type: one sans family throughout, 8pt labels, 7pt tick labels, 9pt axis titles. No text
>   smaller than 7pt at final size.
> - Every series must be distinguishable in greyscale — pair each colour with a distinct
>   marker shape and line dash. Verify by rendering a greyscale copy to
>   `results/greyscale_check/` and inspecting it.
> - Direct-label series at the end of lines rather than using a legend box, where it fits.
> - No gridlines unless a value must be read off the axis; then hairline, light grey,
>   behind the data.
> - Axis limits set explicitly and identically across figures showing the same quantity, so
>   the reader can compare between figures.
> - Every figure gets a `caption` string in the script, written to a sidecar `.txt`, stating
>   what it shows, the seed, and the sample count.
>
> The tradeoff scatter is the headline figure: give it the most care, label every point
> directly, and annotate the two axes with which direction is better.

**Check it yourself:** print one at actual size, or zoom to 100% at 3.3in. If you can't read
the tick labels, the paper's reviewer can't either.

---

## 3. W2 — Contract change

The page can only show baselines if the baselines reach it. This changes the JSON contract,
which `CLAUDE.md` treats as load-bearing — do it deliberately.

> Extend the JSON contract to carry all methods, not just observed and generated.
>
> In `networks.json`, replace the current `observed` / `generated` pair with:
>
> ```json
> {
>   "n_nodes": 60,
>   "methods": {
>     "observed":     { "label": "Simulated ground truth", "role": "observed", "nodes": [], "edges": [] },
>     "vae":          { "label": "Our model",              "role": "ours",     "nodes": [], "edges": [] },
>     "max_entropy":  { "label": "Maximum entropy",        "role": "baseline", "nodes": [], "edges": [] },
>     "configuration":{ "label": "Configuration model",    "role": "baseline", "nodes": [], "edges": [] },
>     "erdos_renyi":  { "label": "Erdős–Rényi",            "role": "baseline", "nodes": [], "edges": [] }
>   },
>   "default_pair": ["observed", "vae"]
> }
> ```
>
> Every method's nodes carry the same `slot` field and the **same layout coordinates** —
> compute the layout once on the observed network and reuse it for all five, so a bank in
> the same screen position is the comparable bank in every view. This is the existing
> `slot` convention from `CLAUDE.md`, extended.
>
> Add `metrics.json → by_method` and `contagion.json → by_method`, keyed identically.
>
> Update `lib/types.ts` to match exactly. Update every component that reads the old shape.
> `role` drives colour: `observed` → blue, `ours` → amber, `baseline` → the grey ramp.
> Never hardcode a colour against a method key — a sixth method must only need a JSON entry.
>
> Run `npm --prefix web run build` and both contagion verifiers. The single-seed demo output
> must stay byte-identical for observed and vae.

---

## 4. W3 — The new hero

The page currently opens with two networks side by side and says "one of these is invented."
That was the right hero for the demo. It's the wrong hero for the paper, whose claim is that
the field measures the wrong thing.

> Load `frontend-design` and `dataviz`. Apply the conflict rule.
>
> Replace the hero with the tradeoff scatter, made interactive.
>
> **Reading:** x-axis is edge-reconstruction accuracy, y-axis is contagion-realism error.
> Five points. The argument lands when the reader sees a point that is far right (accurate
> edges) and high (wrong contagion) — accuracy and realism disagreeing.
>
> **Interaction — exactly one idea:** hovering or focusing a point swaps the network drawing
> below it to that method's network, against the observed one. Max-entropy's near-complete
> matrix next to the observed core-periphery structure is the single most convincing thing on
> the page; the scatter explains why that dense mess scores *well* on the conventional metric.
>
> Annotate the quadrant containing the disagreement with one short sentence of plain
> language, positioned as part of the chart, not as a caption below it.
>
> Keep the existing edge-draw reveal, now triggered on method change as well as load —
> motion that answers the reader's action, per the design bans. Respect
> `prefers-reduced-motion`: swap instantly instead.
>
> Keyboard: the scatter points are a focusable list with arrow-key navigation, not
> hover-only. This is load-bearing, not a nicety — a hover-only hero is unusable on the phone
> someone will inevitably view this on.
>
> Below the hero, a one-paragraph statement of the claim. Everything currently in the page's
> opening section moves down into a "how the networks are made" section.

---

## 5. W4 — Simulator and charts

> Extend `CrisisSimulator.tsx` with a method selector — a small inline control, not a
> dropdown — letting the reader run the same shock against any of the five systems. The
> browser already has all five adjacencies from W2; `lib/contagion.ts` needs no change beyond
> accepting which one to use.
>
> The comparison that matters: at a shock where the observed system loses most of its core,
> maximum entropy loses far fewer banks. Letting the reader find that themselves is worth more
> than asserting it. Have `lib/analysis.ts` derive a sentence naming the gap at the currently
> selected shock — derived from the run, no hardcoded thresholds, per `CLAUDE.md`.
>
> Add 95% bands from `ensemble.json` to the cascade chart for the methods that have them.
> Band fill at low opacity in the series colour; never a separate hue.
>
> Add an ablation section: a small table, one row per disabled component, showing the
> protocol-score delta. Order rows by effect size, largest first. Mono tabular numerals for
> the figures, sentence-case labels, no all-caps header row.

---

## 6. W5 — The copy

The page's words currently argue the old thesis. Left alone they'll contradict the new hero.

> Load `design:ux-copy`.
>
> Rewrite the page's prose for the new argument. The thesis is no longer "we can generate
> realistic networks" — it is "the standard way of checking whether a generated network is
> realistic measures the wrong thing, and here is what to measure instead."
>
> Audience: a CS reader who does not know what an interbank exposure network is. Keep the
> existing register — plain verbs, sentence case, no filler. Concretely:
>
> - Explain maximum entropy in one sentence without the term "maximum entropy" leading:
>   spreading exposures as evenly as the known totals allow.
> - The "What this does not do yet" section keeps the 37.1% DebtRank gap and now gains the
>   reframing: our own model fails one of our own metrics, which is why the protocol is worth
>   having. Do not soften this.
> - Never let "observed" imply real data anywhere. "Simulated ground truth" throughout.
>
> Copy is design content. Cut any sentence that isn't doing a job.

---

## 7. W6 — Critique and accessibility

> Load `design:design-critique` and run it against the page as built. Report findings; do not
> act on them in the same pass.
>
> Then load `design:accessibility-review` and audit to WCAG 2.1 AA. Two things are known
> risks: the grey baseline ramp against paper may fail contrast at small sizes, and the
> scatter hero must be fully keyboard-operable. Check both explicitly.
>
> Where a fix would violate `CLAUDE.md` — for instance darkening amber for contrast — report
> the conflict and propose options rather than changing the token.

---

## 8. Order and honest time

| | | Est. | Needed for |
|---|---|---|---|
| W1 | Paper figures | 45 min | **the paper** |
| W2 | Contract change | 30 min | everything below |
| W3 | New hero | 60 min | the demo |
| W4 | Simulator + charts | 45 min | the demo |
| W5 | Copy | 30 min | the demo |
| W6 | Critique + a11y | 30 min | polish |

**Against a 5-hour week: do W1 and stop.** The paper needs figures; the page does not affect
the submission. W2–W6 are for the course demo and can happen the week after, when the
research stages are already done and the numbers have stopped moving.

If you do start W2, finish W3 as well. A contract change with half the components updated is
the worst place to leave it.

---

## 9. Two things that will break

**Layout reuse across five methods.** Max-entropy produces a near-complete graph. Drawn at
the observed network's spring coordinates it will be a solid block of edges. That is
*correct* and is the most persuasive image on the page — resist any instinct to fix it by
re-laying-out per method, which would destroy the slot correspondence and the comparison.
Reduce edge opacity for dense methods instead; note the opacity used in the caption.

**The greyscale check.** Do it before the paper deadline, not after. Five series that look
distinct in colour routinely collapse to three in print, and it's the kind of thing that
gets noticed in the version of record rather than the draft.
