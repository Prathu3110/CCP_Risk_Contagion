# Synthetic Financial Exposure Networks — Demo Build Plan

Hand this to Claude Code. Run the stages in order. Stage 1 alone is already a demo; Stages 2–3 make it presentable.

**Realistic timings:** Stage 1 ≈ 12 min · Stage 2 ≈ 8 min · Stage 3 ≈ 15 min · Stage 4 = polish if time allows.

---

## 0. The one-sentence version

Real bank-to-bank exposure data is confidential, so you train a model to invent realistic fake exposure networks — and you prove they're good not by matching edges, but by showing financial crises spread through them the same way.

---

## 1. Architecture decision (read this before starting)

**Python and the web app do not talk to each other at runtime.** Python runs once, writes three JSON files into `web/public/data/`, and exits. Next.js reads those as static files.

No API, no server, no CORS, nothing to fail while you're standing in front of an examiner. When you later want live "regenerate" buttons, you add a FastAPI layer without changing anything else.

**Graph layout is computed in Python, not the browser.** NetworkX computes node x/y positions and ships them in the JSON. The web app just draws circles and lines at given coordinates. This removes an entire class of bugs and makes the page load instantly.

---

## 2. Repo layout

```
ccp-synthetic-networks/
├─ research/
│  ├─ configs/demo.yaml
│  ├─ src/
│  │  ├─ generators.py      # ground-truth core-periphery sampler
│  │  ├─ gvae.py            # graph VAE (plain PyTorch)
│  │  ├─ contagion.py       # DebtRank + Eisenberg–Noe
│  │  ├─ layout.py          # node positions for drawing
│  │  └─ export.py          # writes JSON to web/public/data/
│  ├─ scripts/run_demo.py   # single entry point
│  ├─ results/              # figures, checkpoints (gitignored)
│  └─ requirements.txt
├─ web/                     # Next.js + TypeScript
│  ├─ app/
│  ├─ components/
│  ├─ lib/types.ts          # mirrors the JSON contract
│  └─ public/data/*.json
├─ docs/
│  └─ method.md
└─ README.md
```

**Not PyTorch Geometric for today.** PyG needs compiled wheels matched to your torch build and will eat 20 minutes. At 60 nodes a dense-adjacency VAE is mathematically the same thing. Swap to PyG when you scale up.

---

## 3. The data contract

Build this first and both halves can be built independently. Three files in `web/public/data/`.

**`networks.json`**
```json
{
  "n_nodes": 60,
  "observed": {
    "nodes": [{ "id": 0, "x": 0.51, "y": 0.42, "assets": 1.0, "core": true }],
    "edges": [{ "s": 0, "t": 4, "w": 0.031 }]
  },
  "generated": { "nodes": [], "edges": [] }
}
```
`x`, `y` are normalised 0–1. Both networks use the **same layout algorithm and the same seed** so they're visually comparable.

**`metrics.json`**
```json
{
  "training": { "epochs": [1, 2], "loss": [412.3, 260.1] },
  "degree_hist":  { "bins": [0, 2, 4], "observed": [3, 9], "generated": [4, 8] },
  "weight_hist":  { "bins": [], "observed": [], "generated": [] },
  "summary": [
    { "name": "Mean degree", "observed": 8.4, "generated": 8.1, "gap_pct": 3.6 }
  ]
}
```

**`contagion.json`**
```json
{
  "debtrank": { "observed": [0.02, 0.41], "generated": [0.03, 0.39] },
  "cascade": {
    "shock": [0.05, 0.10],
    "observed": { "mean": [], "lo": [], "hi": [] },
    "generated": { "mean": [], "lo": [], "hi": [] }
  }
}
```

---

## 4. Stage 1 — research pipeline

Paste into Claude Code:

> Build the `research/` half of the repo described in `CCP-DEMO-BUILD-PLAN.md`. Python 3.11, plain PyTorch (no PyTorch Geometric), NumPy, NetworkX. Everything seeded and reproducible from `configs/demo.yaml`.
>
> **`generators.py`** — sample core-periphery interbank exposure networks. 60 banks, 10% core. Core banks densely connected to each other and to periphery; periphery sparsely connected to each other. Edge weights lognormal, scaled so core exposures are larger. Also assign each bank total assets and equity (equity ≈ 8% of assets, lognormal noise). Return a weighted directed adjacency matrix plus a node feature table. Sample 300 of these as the training corpus.
>
> **`gvae.py`** — a graph variational autoencoder on dense adjacency. Encoder: two graph-convolution layers (implement as `A_norm @ X @ W`, symmetric normalisation) producing mu and logvar for a 16-dim latent per node. Decoder: inner product of latents through a sigmoid for edge probability, plus a small MLP head on the latent pair for edge weight. Loss: weighted BCE on edges (`pos_weight` for sparsity) + MSE on weights of true edges + KL divergence. Train on CPU, 300 epochs, log loss every 10. Sampling: draw z from the prior, decode, threshold edge probabilities, apply weight head.
>
> **`contagion.py`** — two simulators, both taking a weighted adjacency plus equity vector.
> 1. `debtrank(A, equity, shocked_node)` — Battiston's DebtRank. Impact matrix `W[i][j] = min(1, A[i][j] / equity[j])`, two-state propagation (undistressed / distressed / inactive), iterate to convergence, return fraction of system economic value destroyed.
> 2. `eisenberg_noe(A, external_assets, shock)` — the clearing-payment fixed point. Compute the clearing vector by the iterative fictitious-default algorithm, return the number of banks that fail to pay in full.
> Docstring each with the paper it comes from.
>
> **`layout.py`** — NetworkX spring layout with a fixed seed, run on the observed network; reuse the same positions for the generated network by matching nodes on degree rank so the two drawings are comparable. Normalise to 0–1.
>
> **`export.py`** and **`scripts/run_demo.py`** — run the whole pipeline and write the three JSON files in the exact schema in section 3 of the plan to `web/public/data/`. Sweep shocks from 5% to 50% in ten steps, 20 repeats each, for the cascade curves. DebtRank: shock each of the 60 banks in turn. Print a summary table to stdout at the end.
>
> Keep every module under 150 lines. Type hints throughout. No notebooks.

**Sanity check before moving on:** mean degree of generated should be within ~20% of observed, and the DebtRank distributions should overlap visibly. If generated networks come out empty or fully connected, the edge threshold or `pos_weight` needs tuning — say so rather than faking it.

---

## 5. Stage 2 — Next.js scaffold

```bash
npx create-next-app@latest web --typescript --tailwind --app --eslint --no-src-dir
```

Then:

> Scaffold the `web/` app. Read the three JSON files from `public/data/` at build time (they're static, so import them directly or use `fs` in a server component — no client fetching, no loading states).
>
> Define `lib/types.ts` mirroring the JSON contract exactly.
>
> Charts: no chart library. Hand-rolled SVG with `d3-scale` and `d3-shape` only. Install `d3-scale`, `d3-shape`, and their `@types`. A chart library will make this look like every other dashboard.
>
> Components: `NetworkPlot`, `Histogram`, `CascadeChart`, `MetricsTable`. Each takes typed props, no internal fetching.

---

## 6. Stage 3 — the page, and how it should look

Give Claude Code this design brief verbatim. It's written to avoid the defaults.

> **Subject:** an instrument for reading a financial-network experiment. Audience: CS faculty who don't know finance. Job: convince them in 60 seconds that the generated networks behave like the real ones under stress.
>
> **Two-colour semantic rule, applied everywhere without exception:** observed data is ink blue, generated data is amber. Never use these two hues decoratively. A third colour, deep red, means only one thing: a bank has defaulted.
>
> **Palette**
> `ink #10192B` · `paper #F5F6F4` · `observed #2E5E8C` · `generated #C8842A` · `stress #A3302B` · `rule #D6D8D3`
> Paper background, ink text. No gradients, no shadows, no glass.
>
> **Type**
> Display: Archivo, weight 600, tight tracking, large. Body: Public Sans, 16px, line length under 70 characters. Numerals: Geist Mono with `font-variant-numeric: tabular-nums` — used for figures in tables and axes only, never for labels or headings. Sentence case everywhere.
>
> **Hero:** the two network drawings, side by side, filling the first screen. Not a big number, not a stat row. On load, run one orchestrated reveal — edges draw in over about 800ms, observed first then generated, then it stops. That is the only non-interactive motion on the page.
>
> **Layout:** single column, left-aligned, generous margins, content max-width ~1100px. Sections separated by 1px hairlines in `rule`, not by cards. Each section is a claim in plain language followed by its evidence.
>
> **Sections in order**
> 1. Hero — the two networks, and one sentence: which is real, which the model invented.
> 2. Structure — degree and weight histograms, two overlaid curves each.
> 3. Stress — DebtRank distributions overlaid, then the cascade curve with shaded confidence bands.
> 4. Numbers — the summary table, observed / generated / gap.
>
> **Interaction:** hovering a bank in either network highlights its counterparties in both drawings simultaneously. That's the one interactive idea; don't add more.
>
> **Banned:** all-caps eyebrow labels above headings, meta strings joined by middle dots, arrows appended to link text, identical rounded cards with soft grey shadows, a one-word colour accent inside a headline, fade-and-slide-up on every section.
>
> **Copy:** write it for someone who doesn't know what an exposure network is. "Each dot is a bank. Each line is money one bank owes another." Not "node embeddings" and "latent representations."
>
> Responsive to mobile, visible keyboard focus, `prefers-reduced-motion` respected.

---

## 7. Stage 4 — if time remains

- `docs/method.md`: the maths, one page, with the DebtRank and Eisenberg–Noe equations.
- README with a reproduce-in-one-command block.
- `results/figure1.png` — the same six panels as a static figure, for the paper.

---

## 8. What to say while it's on screen

1. "Bank exposure data is confidential. Nobody outside a central bank can get it, which is why this research area is stuck."
2. "So we generate it. Left is a simulated real system; right is one the model invented from scratch."
3. "The usual test is whether the fake network has the same edges. That's the wrong test — no two real networks have the same edges."
4. "Our test is behavioural. We push both systems into a crisis and check whether the crisis spreads the same way." → cascade chart.
5. "The curves match within X%. The generated networks are usable substitutes for stress testing."

**Say plainly what isn't done.** It's a stronger position than pretending: real BIS data isn't wired in yet (synthetic ground truth for now), the CCP layer and default waterfall are the next milestone, and the model is trained on 60-node graphs, not the full system. Examiners trust a student who draws that line themselves.

---

## 9. If Stage 1 breaks and you're out of time

Run `scripts/run_demo.py` with the VAE training loop skipped and the "generated" network produced by the sampler with different parameters. The page still demonstrates the full pipeline and the validation argument. Tell the examiner the generator is the swappable component — which is true, and is the point of the architecture.
