# CCP Risk — synthetic financial exposure networks

Bank-to-bank exposure data is confidential, so this project trains a model to
invent realistic fake exposure networks. The networks are validated
**behaviourally**: not by whether they reproduce the real network's edges, but by
whether financial crises spread through them the same way.

That distinction drives every design decision here. A generator that reproduced
real edges exactly would be leaking the confidential data it exists to replace.
So the tests that matter are the contagion tests, not the reconstruction error.

## The two halves never talk at runtime

Python runs once, writes three JSON files into `web/public/data/`, and exits.
Next.js reads them at build time and prerenders to static HTML. There is no API,
no CORS, no server, and nothing that can fail while the page is on screen.

**Do not introduce a runtime call from the web app to Python.** If live
regeneration is ever needed, add a FastAPI layer without disturbing this.

Graph layout is also computed in Python. NetworkX produces node coordinates that
ship in the JSON; the browser only draws circles and lines at given positions and
runs no layout algorithm.

## Layout

```
research/
  configs/demo.yaml      every parameter and the single seed
  src/generators.py      core-periphery sampler with realistic balance sheets
  src/gvae.py            graph VAE, plain PyTorch, no PyTorch Geometric
  src/dataset.py         log-space packing between Network objects and tensors
  src/contagion.py       DebtRank and Eisenberg-Noe
  src/layout.py          seeded spring layout, shared by both networks
  src/export.py          writes the JSON contract
  scripts/run_demo.py         single entry point for the pipeline
  scripts/make_figure.py      six-panel static figure for the paper
  scripts/verify_contagion.py reference numbers for the browser port
  results/               gitignored: figures, cached networks.npz
web/
  lib/types.ts           mirrors the JSON contract exactly
  lib/contagion.ts       browser port of the two contagion models
  lib/analysis.ts        turns one run into plain-language explanation
  components/            NetworkPlot, NetworkPair, CrisisSimulator, charts
  public/data/*.json     pipeline output, committed
docs/method.md           the maths, equations and citations
docs/data.md             what data is used, and why none of it is real
docs/related-work.md     literature survey skeleton, all citations TODO-VERIFY
docs/calibration.md      stylized facts, all published ranges TODO-VERIFY
CCP-DEMO-BUILD-PLAN.md   the original brief this was built from
```

## Commands

```bash
python3 research/scripts/run_demo.py          # train + write the 3 JSON files (~30s CPU)
python3 research/scripts/run_demo.py --skip-training   # fallback: sampler instead of the model
python3 research/scripts/make_figure.py       # results/figure1.png + .pdf
npm --prefix web run dev                      # http://localhost:3000
npm --prefix web run build                    # must stay fully static
```

Environment: system Python 3.13 with torch 2.9, numpy, networkx, PyYAML, scipy,
matplotlib (see `research/requirements.txt`). No virtualenv is in use, but
nothing depends on that — a venv can be dropped in without code changes.

## Conventions that must not drift

**Exposure direction.** `A[i][j]` is the amount bank `i` owes bank `j`. Row sums
are interbank liabilities, column sums are interbank assets. This holds in every
Python module *and* in `web/lib/contagion.ts`. Getting it backwards silently
inverts who is harmed by a default.

**Colour is semantic, never decorative.** Ink blue `#2E5E8C` always means
observed data. Amber `#C8842A` always means generated data. Deep red `#A3302B`
means one thing only: a bank has defaulted. Paper `#F5F6F4`, ink `#10192B`, rule
`#D6D8D3`.

**Amber and blue are not matched numerically.** Amber carries less contrast
against paper, so edge opacities are matched by eye (`RESTING_EDGE` in
`NetworkPlot.tsx`). Setting them equal makes the generated network look sparser
than it is.

**`slot`, not `id`, links the two networks.** A node's `slot` is its rank by
counterparty count. Both networks are laid out so equal slots occupy the same
screen position, which is what lets a hover highlight the comparable bank in
both. Node ids cannot do this — id 7 in an invented system has nothing to do
with id 7 in the observed one.

**Balance-sheet fields in the JSON are raw, `assets` is normalised.** `assets`
only sets dot size. `equity`, `ext_assets`, `ext_liabilities` and edge `w` are
raw and rounded to 8 decimals, because the browser re-runs the clearing model on
them and a crisis is not scale-invariant. Five decimals was enough to move the
default count.

**Design bans** (from the original brief): no all-caps eyebrow labels, no meta
strings joined by middle dots, no arrows appended to link text, no rounded cards
with soft grey shadows, no one-word colour accent inside a headline, no
fade-and-slide-up on every section. Sentence case everywhere. Mono tabular
numerals for figures in tables and axes only, never labels or headings. The only
non-interactive motion is the one edge-draw reveal on load.

**Charts are hand-rolled SVG** over `d3-scale` and `d3-shape`. Do not add a chart
library.

**Colour goes on marks, never on text.** Amber (2.85:1) and two of the three
baseline greys (3.57:1, 2.40:1) fall below WCAG AA against paper. Darkening them
would break the semantic palette, so a method's name is set in ink with a
coloured swatch beside it — see `components/SeriesName.tsx`. Do not set a
method's label in its own colour.

**Accepted accessibility deviation.** Bank nodes inside a network drawing are
11-23px, below the 24px target guidance. Sixty nodes cannot carry 44px targets
in a panel that size without overlapping, so the mitigation is keyboard: every
drawing is a roving-tabindex listbox with arrow-key navigation. The scatter
points in the hero are 25px and were widened deliberately; keep them there.

## The two implementations that must agree

`research/src/contagion.py` and `web/lib/contagion.ts` are the same two
algorithms written twice — the browser needs to run a crisis at any shock the
reader picks, without a server. Two implementations drift, so there is a check:

```bash
npm --prefix web run verify:contagion
python3 research/scripts/verify_contagion.py
```

Both print the same 40 numbers (cascade size at ten shock levels, mean and max
DebtRank, for both systems). **They currently agree to six decimal places. Run
both after touching either file.**

## Four modelling choices forced by measurement

These were each found by measuring, not by reasoning ahead. Each one, alone, made
the generated systems look artificially safe. Do not "simplify" them away.

1. **Interbank claims are scaled to a share of the balance sheet, and banks carry
   external liabilities.** Without both, single exposures ran to 10x a creditor's
   equity while no shock could ever cause a default.
2. **The weight and node heads predict Gaussians and are sampled, not regressed
   under MSE.** Squared error collapses the generated log-weight spread — every
   exposure comes out the same size, and contagion depends on the tail. Measured
   in isolation against today's model (`run_ablations.py`) the effect is 0.739 to
   0.363, against a ground truth of 0.825. The larger 0.83-to-0.08 figure quoted
   during development predates the bias head, kernel latent sampling and
   Bernoulli edges.
3. **The node head models the equity *ratio*, not equity.** Its diagonal output
   cannot represent the size/capital correlation; modelling log-equity directly
   inflated mean equity by 24%.
4. **Edges are drawn as calibrated Bernoulli samples.** Keeping the most probable
   edges hits the right density but hands nearly all of them to the hubs.

Latents are sampled from a kernel estimate of the aggregate posterior, not the
N(0, I) prior — the latent cloud is bimodal (core vs periphery banks) and a
single Gaussian puts most of its mass in the empty space between the modes.

## Current results

From the committed seeded run, generated against observed:

| Statistic | Gap |
| --- | --- |
| Mean equity ratio | 2.9% |
| Mean exposure size | 3.8% |
| Edge density | 4.3% |
| Mean cascade size | 6.6% |
| Degree assortativity | 18.1% |
| Max degree | 20.4% |
| **Mean DebtRank** | **37.1%** |

Mean DebtRank is the honest weak point, not noise — it held across a four-way
sweep of bandwidth, epochs and KL weight. The generated upper tail of exposures
is still thinner than ground truth, so the typical bank looks less systemic than
it is. **It is documented in the README, in `docs/method.md`, in the page's "What
this does not do yet" section, and in the caption of the chart that shows it. Do
not quietly tune it away or drop the disclosure.**

Pipeline output is byte-identical across runs. If a change makes it non-reproducible,
that is a bug.

## Behaviour of the live simulator

`CrisisSimulator.tsx` re-runs Eisenberg-Noe in the browser. Facts about this
calibration, established by measurement — check before writing copy that claims
otherwise:

- Below ~7% shock **nothing fails**; capital absorbs it.
- Between 8% and 15% the system tips over, and the two systems can disagree about
  which banks go first (at 10%, 6 of 6 core banks fail in the observed system
  against 2 of 6 in the generated one).
- Past ~15% direct failures **plateau** (31 observed) while contagion keeps
  climbing — those banks' buffers are already floored, so extra shock kills only
  through the network.
- **No single bank is contagious on its own** — wiping out any one of the 60
  fails only itself, in both systems.
- 2 of 60 observed banks (5 of 60 generated) owe nobody and so can never default
  in Eisenberg-Noe by construction.

`lib/analysis.ts` derives every sentence from the numbers a run actually
produced. Never introduce hardcoded thresholds there — the explanation must not
be able to drift out of step with the model.

## Known state

- Root `CLAUDE.md` is this file. `web/CLAUDE.md` and `web/AGENTS.md` are
  create-next-app boilerplate; `next dev` rewrites `AGENTS.md` if removed.
- `.claude/launch.json` is a dev-server config for the browser preview, not
  project code.
- `research/src/gvae.py` (209 lines) and `scripts/run_demo.py` (211) exceed the
  build plan's 150-line guideline. Most of the overage is docstrings recording
  why each modelling choice was made; splitting them for a line count would cost
  more than it buys.
- The observed system is itself simulated. Real supervisory data is not wired in,
  and cannot be: no bilateral bank-to-bank exposure data is published anywhere.
  BIS statistics are country-and-sector aggregates and contain no bank-level
  network — never claim calibration to them. `configs/demo.yaml` carries a
  `calibration` block for pinning balance-sheet parameters to public figures; it
  is `enabled: false` and every field is `TODO-VERIFY` until filled from a named
  source. See `docs/data.md`.
- No central counterparty and no default waterfall yet — the next milestone, and
  the part that matters most for clearing risk.
- 60 banks only. The dense-adjacency approach will not reach national scale
  unchanged; PyTorch Geometric is the intended path.

## Working agreement

The user handles all commits and pushes. Make changes, verify them, and hand
back — **do not run `git commit` or `git push`** unless explicitly asked.
