# Conference Paper — Execution Plan

**Budget: ~5 hours total. Hard cut line after Stage D.** Everything below the line is
next-paper material. Stages are ordered so that stopping at any point still leaves a
submittable paper.

---

## 1. What the paper claims

Three contributions, in order of how much weight they carry.

**C1 — The evaluation-protocol contribution (the headline).**
Synthetic financial networks are conventionally evaluated by how accurately they
reconstruct a known network's edges. We show this metric is misaligned with the purpose
the networks are generated for. A maximum-entropy reconstruction scores *better* on edge
accuracy and *worse* on contagion behaviour than a learned generator. We define a
behavioural evaluation protocol — a named set of contagion statistics — and argue it
should replace reconstruction error as the acceptance criterion.

**C2 — The generator.**
A graph VAE with four modelling choices, each empirically necessary, each ablated.

**C3 — The honest negative result.**
Our own generator passes most of the protocol and fails one metric (mean DebtRank, 37.1%
gap). We report this rather than tuning it away. It supports C1: if a model built
specifically for contagion realism still misses, the protocol is doing real work.

### Why this is safe and not derivative

The risk you named — that many papers do something similar — is real for C2 alone.
Nobody wins a novelty argument with "another graph VAE." C1 is different: it is a
*negative result about how the field measures things*, grounded in your own numbers.
Negative and methodological results are hard to scoop because they require someone to
have built both systems and compared them, which is what you've done.

**The headline figure is a scatter plot.** X-axis: reconstruction error against the true
network. Y-axis: contagion-realism error. Each point is a method. If maximum-entropy
lands bottom-right (accurate edges, wrong contagion) and your VAE lands top-left, the
paper is made. That single figure is the argument.

---

## 2. Time budget

| Stage | What | Est. | Cumulative |
|---|---|---|---|
| A | Baselines + the headline figure | 60 min | 1:00 |
| B | Ensembles, confidence intervals, significance tests | 45 min | 1:45 |
| C | Ablation table | 45 min | 2:30 |
| D | Stylized-fact calibration table | 30 min | 3:00 |
| — | **CUT LINE — you have a paper here** | | |
| E | CCP novation + Cover-2 waterfall | 90 min | 4:30 |

Estimates are Claude Code's working time; yours is review time on top. If Stage A runs
long, **cut D before cutting B or C** — B and C are what reviewers demand, D is polish.

---

## 3. Stage A — Baselines

### What this actually does, in plain English

Right now you have one method and nothing to compare it to. A reviewer's first question
is "compared to what?" You need three alternatives, all of which are standard in this
literature:

- **Maximum entropy (IPF / RAS algorithm).** The field standard. It takes the *row and
  column totals* of the exposure matrix — how much each bank owes in total and is owed in
  total — and spreads the exposures as evenly as possible subject to those totals. It's
  the natural guess when you know the aggregates but not the details. It is known to
  produce networks that are far too evenly connected, which makes them look safer than
  reality. **This is the baseline you need to beat, and the one you'll beat on contagion
  while losing on edge accuracy.** That loss is the point.
- **Configuration model.** Preserves each bank's *number* of counterparties but rewires
  who connects to whom at random. Isolates how much of the contagion behaviour comes from
  degree alone versus from structure.
- **Erdős–Rényi.** Every possible link equally likely, matched only on overall density.
  The floor. If a method can't beat this, it has learned nothing.

Then all four methods (yours plus these three) go through the contagion code you already
have, and get scored on both axes.

### Claude Code prompt

> Add a baselines module to the research half of the repo.
>
> Create `research/src/baselines.py` with three generators, each taking the observed
> `Network` object and returning a new `Network` with the same node count and the same
> balance-sheet fields (`equity`, `ext_assets`, `ext_liabilities`), differing only in the
> interbank adjacency matrix:
>
> 1. `maximum_entropy(net)` — IPF/RAS. Target row sums are the observed interbank
>    liabilities per bank, target column sums the observed interbank assets. Start from a
>    matrix of ones with a zero diagonal, alternately rescale rows and columns until both
>    marginals match to 1e-9 or 500 iterations. Note in the docstring that this produces a
>    nearly complete matrix — that is the known behaviour, not a bug.
> 2. `configuration_model(net, seed)` — preserve each node's in- and out-degree, rewire
>    endpoints at random, reassign the observed edge weights at random to the new edges.
> 3. `erdos_renyi(net, seed)` — edges drawn independently at probability equal to observed
>    density; weights drawn from the observed weight distribution.
>
> Create `research/src/evaluation.py` defining the two scores used throughout the paper:
>
> - `reconstruction_error(A_true, A_gen)` — returns a dict with relative Frobenius error
>   on the weight matrix, and precision/recall/F1 on edge presence.
> - `behavioural_error(net_true, net_gen)` — returns a dict with the absolute relative gap
>   in: mean DebtRank, max DebtRank, mean cascade size across the shock sweep, edge
>   density, degree assortativity, mean exposure size, mean equity ratio. Plus a single
>   scalar `protocol_score` = the mean of the relative gaps. Define this once here and
>   import it everywhere; do not recompute these formulas in any other file.
>
> Create `research/scripts/run_baselines.py` that runs all four methods (VAE, max-entropy,
> configuration, ER) against the observed network, computes both scores for each, writes
> `research/results/baselines.json`, and prints a table to stdout.
>
> Then add `research/scripts/make_tradeoff_figure.py` producing `results/figure_tradeoff.pdf`:
> a scatter with reconstruction F1 on the x-axis (higher = better edge accuracy) and
> `protocol_score` on the y-axis (lower = better contagion realism), one labelled point per
> method. Use the existing palette. This is the paper's headline figure.
>
> Do not change anything in `contagion.py`, `gvae.py`, or the web app.

### Before moving on

Check that maximum entropy really does win on reconstruction F1. If it doesn't, something
is wrong with the IPF implementation — it produces a near-complete matrix, which should
give it very high recall. **Do not proceed to Stage B until the headline figure shows the
disagreement, or shows clearly that it doesn't exist.** If the disagreement isn't there,
the paper's argument changes and you need to know that now, not after writing.

---

## 4. Stage B — Ensembles and statistics

### What this actually does

Every number in your README comes from a single run. A reviewer will point out that you
can't tell a real difference from random variation with one sample. So you generate 20
networks instead of one, report the average with an interval around it, and run a
statistical test that answers: *could this difference have happened by chance?*

The test for the DebtRank comparison is the **two-sample Kolmogorov–Smirnov test**. It
compares two distributions and returns a p-value. Here you *want a high p-value* — it
means you cannot distinguish generated from observed, which is the goal. This is the
opposite of the usual convention and you should say so explicitly in the paper, because
it's the kind of thing that looks like an error if unexplained.

### Claude Code prompt

> Add ensemble evaluation.
>
> Extend `run_baselines.py` to draw 20 independent samples from each stochastic method
> (VAE, configuration, ER; maximum entropy is deterministic so it contributes one). Use
> seeds `base_seed + i` and record the seed with each sample so any single run can be
> reproduced.
>
> For every metric in `behavioural_error`, report mean and a 95% bootstrap confidence
> interval over the 20 samples (10,000 resamples).
>
> Add `research/src/statistics.py` with:
> - `ks_test(observed_debtrank, generated_debtrank)` — two-sample Kolmogorov–Smirnov via
>   `scipy.stats.ks_2samp`, returning statistic and p-value. Docstring must state that in
>   this application a high p-value is the desired outcome.
> - `bootstrap_ci(values, statistic, n=10000, seed)`.
>
> Write `research/results/ensemble.json` and print a table: method, each metric as
> `mean [lo, hi]`, and the KS p-value against observed.
>
> Add `research/scripts/make_ensemble_figure.py` → `results/figure_ensemble.pdf`: the
> cascade curve with shaded 95% bands for all four methods on one axis.
>
> Keep the existing single-seed demo run untouched and still byte-identical — the web app
> depends on it.

---

## 5. Stage C — Ablations

### What this actually does

Your `CLAUDE.md` documents four modelling choices, each found by measuring, each of which
made generated systems look artificially safe when absent. That's an ablation study that
already happened — it just isn't written down as numbers. An ablation is simply: turn one
piece off, rerun, report how much worse it got. It's how you prove each piece earns its
place rather than being decoration.

### Claude Code prompt

> Turn the four documented modelling choices into config-level ablations.
>
> Add to `configs/demo.yaml` an `ablations` block with four boolean flags, all true by
> default:
> - `scale_interbank_claims`
> - `sample_weight_head` (false = regress under MSE instead of sampling a Gaussian)
> - `model_equity_ratio` (false = model log-equity directly)
> - `bernoulli_edges` (false = keep the top-k most probable edges)
>
> Plus a fifth: `kde_latent_sampling` (false = sample from the N(0,I) prior).
>
> Thread each flag through `gvae.py` and `dataset.py` at the point where that choice is
> made. Do not restructure those files — add branches at the existing decision points.
>
> Add `research/scripts/run_ablations.py`: run the full model once, then once with each
> flag individually disabled, 5 seeds each, and report `protocol_score` plus mean DebtRank
> and log-weight standard deviation for each variant. Write `results/ablations.json` and
> print a table with a delta column against the full model.
>
> Restore all flags to true at the end. Verify the full-model run still reproduces the
> committed numbers exactly.

---

## 6. Stage D — Stylized-fact calibration

### What this actually does, and the correction

**You cannot calibrate to BIS locational banking statistics.** LBS reports aggregate
cross-border claims between *countries*, not between banks. There is no bank-level network
in it. Any claim that your 60-node network is calibrated to BIS data would be wrong and
would not survive review.

What the field does instead — and what you should do — is calibrate to **published
stylized facts**: empirical regularities that studies of real interbank systems have
reported, each citable. The known ones are roughly: very low density, a small densely
connected core with a sparse periphery, a heavy-tailed degree distribution, negative
degree assortativity (big banks connect to small ones, not to each other), and tiering.

This stage does **not retune your generator** — that would risk everything you've already
calibrated. It only produces a table showing your *simulated ground truth* sits inside the
published ranges. That converts "we made up a network" into "our ground truth reproduces
the documented empirical regularities of real systems," at near-zero risk.

### Claude Code prompt

> Add `research/scripts/stylized_facts.py`, computing for the observed network: edge
> density, core size as a fraction of nodes, degree distribution tail exponent (Hill
> estimator), degree assortativity, mean and max degree, and a tiering statistic.
>
> Write `research/results/stylized_facts.json` and produce a markdown table in
> `docs/calibration.md` with columns: statistic, our value, published empirical range,
> source, and whether it falls inside the range.
>
> **Leave every "published empirical range" and "source" cell as the literal string
> `TODO-VERIFY`.** Do not fill these in from your own knowledge and do not search for them.
> They will be filled by hand from verified sources.
>
> Do not modify the generator, the config, or any existing results.

### Your job here

Those `TODO-VERIFY` cells are the highest-risk part of the whole paper for an automated
reviewer — a wrong or invented citation is fatal. **Bring the generated table back to me
and I'll find and verify each source against publisher records before you fill anything
in.** This is also a standing rule from your earlier work: AI-generated citation lists have
already introduced errors in this project once.

---

## 7. Below the cut line — Stage E: the CCP layer

Only start this if Stages A–D are done and the paper draft exists. This is the
contribution that would make it a *strong* paper rather than a solid one, but a
half-built waterfall is worse than an honest "future work" section.

### What it would do

Take a generated bilateral network and apply **novation**: the transformation where a
central counterparty steps into the middle of every trade, so instead of Bank A owing
Bank B directly, A owes the CCP and the CCP owes B. Every bank now faces one
counterparty instead of many. Then give the CCP a default waterfall — the ordered stack
of resources it burns when a member fails: that member's initial margin, then its default
fund contribution, then the CCP's own capital, then everyone else's default fund
contributions. **Cover-2** is the regulatory standard requiring the CCP to survive its two
largest members failing at once.

The experiment: run the same shock sweep on the same system, bilateral versus centrally
cleared, across the whole synthetic ensemble, and measure whether central clearing reduces
total system losses or merely concentrates them in the CCP. This is a live policy question
and it cannot be studied with real data because CCP exposures are confidential — which is
exactly the argument for why a generator was needed.

### Claude Code prompt (for later)

> Add `research/src/ccp.py`:
> - `novate(net, cleared_fraction)` — replace a given fraction of bilateral edges with
>   paired member↔CCP edges, preserving each member's net position. Add the CCP as node
>   index `n`.
> - `initial_margin(net, quantile)` — per-member margin sized at a quantile of its
>   simulated exposure change.
> - `default_fund(net, cover)` — sized so the fund plus margin covers the `cover` largest
>   members failing simultaneously (cover=2 is the regulatory standard).
> - `waterfall(net, defaulted_members)` — consume in order: defaulter's margin,
>   defaulter's fund contribution, CCP capital, surviving members' fund contributions.
>   Return per-member losses and whether the CCP itself is breached.
>
> Then `research/scripts/run_ccp_experiment.py`: for each of 20 generated networks, run the
> shock sweep bilaterally and with `cleared_fraction` in {0.25, 0.5, 0.75, 1.0}, reporting
> total system loss, number of member defaults, and CCP breach frequency. Write
> `results/ccp.json` and a figure with cleared fraction on the x-axis.
>
> Every parameter choice (margin quantile, capital size, cover level) must be a named
> config value with a docstring citing where the convention comes from — mark citations
> `TODO-VERIFY`.

---

## 8. Paper structure, mapped to outputs

| Section | Comes from |
|---|---|
| Introduction — data is confidential, so generate it | existing `docs/method.md` |
| Related work — reconstruction methods and their evaluation | to write |
| Problem: what should "realistic" mean? | the C1 argument |
| **The behavioural protocol** — formal metric definitions | `src/evaluation.py` |
| Generator | `src/gvae.py`, existing docstrings |
| Experiments: baselines | Stage A, `figure_tradeoff.pdf` |
| Experiments: ensembles + significance | Stage B, `figure_ensemble.pdf` |
| Experiments: ablations | Stage C table |
| Ground-truth calibration | Stage D table |
| **Limitations** — the DebtRank gap, stated plainly | existing numbers |
| Future work — CCP layer, real data, scale | Stage E scope |

Write Limitations **before** Results. It's the section that most often reads as an
afterthought, and it's the one carrying your strongest honesty signal.

---

## 9. Error-proofing checklist

Run through this before submitting anything.

- [ ] Every citation verified against the publisher record. No exceptions, no "probably."
- [ ] No claim of BIS bank-level data anywhere in the paper.
- [ ] Every number in the text traceable to a JSON file in `results/`.
- [ ] The KS-test direction explained — high p-value is the good outcome here.
- [ ] The 37.1% DebtRank gap appears in the abstract or introduction, not only in
      limitations. Burying it is what gets caught.
- [ ] "Observed" never implies real data. Use "simulated ground truth" throughout.
- [ ] Ablations and baselines use the same seeds and the same `evaluation.py` functions.
- [ ] Reproducibility statement: one command, fixed seed, byte-identical output.
- [ ] The web demo still builds and its numbers still match `results/`.
