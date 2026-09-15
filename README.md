# Synthetic financial exposure networks

Bank-to-bank exposure data is confidential. Supervisors collect it, almost
nobody else may see it, and research on financial contagion stalls as a result.

This generates a substitute — and tests it by the only measure that matters for
the purpose. Not whether the invented network has the same connections as the
real one, which no two real systems have either, but whether a financial crisis
spreads through it the same way.

Across a sweep of shocks from 5% to 50%, the cascade curves of the observed and
generated systems agree to within about 7%.

The page is not just a report of that result. It ends with a crisis you run
yourself: pick how hard to hit the system, or wipe out a single bank, and watch
the failures spread round by round through both networks at once.

## Reproduce

Everything is seeded; two runs produce byte-identical output.

```bash
python3 research/scripts/run_demo.py && npm --prefix web install && npm --prefix web run dev
```

The first command trains the model and writes three JSON files into
`web/public/data/` (about 30 seconds on a CPU). The second serves the page at
<http://localhost:3000>.

Python 3.11 or newer, with `pip install -r research/requirements.txt`. The
pinned versions are what this was verified against; a virtualenv is optional and
nothing in the code depends on one.

If the model will not train and you are out of time, `--skip-training` produces
the "generated" network from the sampler under different parameters instead. The
page and the whole validation argument still work, because the generator is a
swappable component — which is the point of the architecture.

To regenerate the six-panel figure for the paper, from the JSON that is already
committed (no retraining):

```bash
python3 research/scripts/make_figure.py
```

It writes `research/results/figure1.png` at 300 dpi and a vector `figure1.pdf`
alongside it. That directory is gitignored, since it holds regenerable output.

## How the two halves fit together

**They do not talk to each other at runtime.** Python runs once, writes three
JSON files, and exits. Next.js reads them at build time and prerenders to static
HTML. No API, no CORS, no server, and nothing that can fail while the page is on
screen. A live "regenerate" button would be a FastAPI layer added later without
changing anything else.

The interactive simulator keeps that property. Rather than calling back into
Python, the two contagion models are ported to TypeScript and re-run in the
browser at whatever shock the reader picks, on balance sheets shipped in the
JSON. Two implementations of one algorithm drift, so there is a check that they
agree:

```bash
npm --prefix web run verify:contagion   # and compare against
python3 research/scripts/verify_contagion.py
```

Both print the same 40 numbers to six decimal places.

Graph layout is computed in Python too, not in the browser. NetworkX produces
node coordinates and ships them in the JSON, so the page only draws circles and
lines at given positions.

```
research/
  configs/demo.yaml     every parameter, one seed
  src/generators.py     core-periphery sampler with realistic balance sheets
  src/gvae.py           graph VAE, plain PyTorch, no PyTorch Geometric
  src/dataset.py        log-space packing between networks and tensors
  src/contagion.py      DebtRank and Eisenberg-Noe
  src/layout.py         seeded spring layout, shared by both networks
  src/export.py         writes the JSON contract
  scripts/run_demo.py   single entry point
  scripts/make_figure.py    the same six panels as a static figure
  scripts/verify_contagion.py  reference numbers for the browser port
web/
  lib/types.ts          mirrors the JSON contract exactly
  lib/contagion.ts      browser port of the two contagion models
  components/           NetworkPlot, Histogram, CascadeChart, CrisisSimulator
  public/data/*.json    pipeline output, committed
docs/method.md          the maths, with the equations and the citations
```

## Results

From one seeded run, generated against observed:

| Statistic | Gap |
| --- | --- |
| Edge density | 4.3% |
| Mean exposure size | 3.8% |
| Mean equity ratio | 2.9% |
| Degree assortativity | 18.1% |
| Mean cascade size | 6.6% |
| Mean DebtRank | 37.0% |

The last row is the honest weak point, not a rounding error. See below.

## What this does not do yet

- The observed system is itself simulated. Real supervisory data is not wired
  in, so this shows the method works, not that it works on the real thing.
- Mean DebtRank comes out about a third below the observed system's: the model
  still does not produce quite enough very large single exposures, so the
  typical bank looks less systemic than it really is.
- There is no central counterparty and no default waterfall. That is the next
  milestone and the part that matters most for clearing risk.
- Everything here is 60 banks. A national system is thousands, and the dense
  adjacency approach will not reach that size unchanged — swapping in PyTorch
  Geometric is the intended path.

## Method

`docs/method.md` has the equations for both contagion models, the VAE
objective, and the modelling choices that were forced by measurement rather
than assumed — including the three that each, on their own, made the generated
systems look artificially safe.
