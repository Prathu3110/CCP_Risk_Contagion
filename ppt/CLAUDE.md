# Slide deck — CCP Risk / synthetic financial exposure networks

You are building a presentation about this project. Everything you need is in
this file. **Do not invent a number, a citation, or a claim that is not here.**

The repo root is one level up. `../CLAUDE.md` describes the codebase; you rarely
need it. `../docs/` holds the written material.

---

## 1. The one-sentence version

Bank-to-bank exposure data is confidential, so researchers generate fake
networks. The field checks a fake network by counting how many of the real
network's links it reproduced. **That check is close to useless, and we show it
with a method that reproduces 100% of the links and still gets the crisis wrong.**

---

## 2. The three claims, in order of weight

**C1 — the evaluation protocol is wrong (the headline).**
Edge-reconstruction accuracy is misaligned with what these networks are built
for. A maximum-entropy reconstruction recovers every real link and is rejected
on every statistical test of crisis behaviour. Replace edge accuracy with a
behavioural protocol.

**C2 — the generator.**
A graph VAE with four modelling choices, each forced by measurement, each
ablated.

**C3 — the honest negative result.**
Our own model fails one of our own metrics (mean DebtRank, gap 0.150). Reported
rather than tuned away. It supports C1: a model built for contagion realism
still misses, so the protocol is doing real work.

---

## 3. Verified numbers — use these exactly

All from the committed run. Seed 20260915, 60 banks. **The data is split: 300
training networks, 20 validation, 5 test.** The model fits train, every setting
was chosen on validation, and the 5 test networks were scored once. Nothing here
was tuned against the numbers below.

Our model is averaged over 20 generated systems. Each baseline is given every
test network to reconstruct, so it contributes 5.

### Headline table

| Method | Links recovered | Contagion error | Structural error | Passes KS | What it is told |
|---|---|---|---|---|---|
| Configuration model | 0.372 | **0.102** [0.087, 0.119] | 0.060 | 4 of 5 | true degree sequence + weight multiset |
| Our model (graph VAE) | 0.089 | 0.140 [0.099, 0.198] | 0.067 | **14 of 20** | nothing |
| Maximum entropy | **1.000** | 0.218 [0.191, 0.240] | 3.012 | **0 of 5** | true row and column totals |
| Erdős–Rényi | 0.085 | 0.619 [0.402, 0.875] | 0.268 | 0 of 5 | true density |

**The money line:** maximum entropy recovers 100% of links and its distribution
of dangerous banks is still told apart from the truth on every test network
(p ≈ 7e-15). Our model recovers 9% and survives 14 of 20.

**Do not oversell the model. It is best at nothing.** Per metric: second on mean
DebtRank, third on max DebtRank, third on mean cascade size. Second of four
overall. It beats both methods that could actually be used in its place, and
loses to one that is handed the network and reshuffles it. Say that, not "our
model wins".

### Per-metric gaps (relative gap vs the test networks, lower is better)

| Metric | Our model | Max entropy | Configuration | Erdős–Rényi |
|---|---|---|---|---|
| Mean DebtRank | 0.190 | 0.541 | 0.153 | 1.336 |
| Max DebtRank | 0.188 | 0.079 | 0.104 | 0.478 |
| Mean cascade size | 0.042 | 0.033 | 0.050 | 0.041 |
| Edge density | 0.044 | **10.126** | 0.027 | 0.043 |
| Degree assortativity | 0.102 | 0.999 | 0.143 | 0.947 |
| Mean exposure size | 0.096 | 0.910 | 0.057 | 0.068 |
| Mean equity ratio | 0.024 | 0.014 | 0.014 | 0.014 |

Edge-level scores: recall / F1 / relative Frobenius are 0.089 / 0.091 / 1.336
for our model, 1.000 / 0.165 / 0.907 for maximum entropy, 0.372 / 0.375 / 1.217
for the configuration model, 0.085 / 0.085 / 1.399 for Erdős–Rényi.

Two caveats that belong on the slide if this table is shown:
- Maximum entropy has the **smallest** cascade-size gap. Cascade size does not
  separate the methods; the DebtRank distribution does.
- Maximum entropy's 10.1x density gap is why its structural error is 3.012. Its
  network is 93% dense against a true 8%.

### The leak we found and closed — worth a slide

The first version of this project did two things that would not have survived
review, and finding them is a result in itself.

1. The generator was handed the **true density of the network it was scored
   against**, to calibrate its edge threshold. That is exactly the privileged
   access the paper criticises maximum entropy for. It now uses the mean density
   of the training networks (0.0827) instead of the evaluation network's true
   value.
2. `latent_bandwidth` was chosen by comparing contagion gaps **against the same
   network the results were then reported on**. Selection on the test set.

Closing both moved our model from 0.123 to 0.140. The ordering did not change.
Report the honest number and say why it went up.

### Ablations (validation split, 5 samples per variant)

Full model: contagion error 0.109, log-weight spread 0.735. Validation target
spread is 0.780.

| Choice switched off | Error | Change | Log-weight spread |
|---|---|---|---|
| Sample from the prior | 0.244 | **+0.135** | 1.108 |
| Keep top edges, not sampled | 0.227 | +0.118 | 0.660 |
| Squared error, not sampled | 0.190 | +0.082 | 0.400 |
| Model equity, not the ratio | 0.166 | +0.057 | 0.743 |
| No balance-sheet scaling | 0.134 | +0.025 | 0.735 |

**All five earn their place.** An earlier run scored these against a single
network and reported that balance-sheet scaling was worth nothing; that was an
artefact of judging a generator on one draw. Best mechanism story: squared error
pushes the exposure spread down to 0.400 and prior sampling pushes it up to
1.108, against a target of 0.780. Opposite distortions, both wrong.

### The negative result worth a slide

A Student-t weight head was added specifically to fix the thin exposure tail,
which is the diagnosed cause of the DebtRank gap. **It fixes the tail and still
scores worse.** Spread 0.788 against a validation target of 0.780, where
Gaussian gives 0.735 — and worse contagion at every bandwidth tried. Matching
the weight distribution is not sufficient for matching contagion behaviour.

### Ground truth stylized facts

| Statistic | Value |
|---|---|
| Edge density | 0.0782 |
| Core share of banks | 0.100 |
| Degree tail exponent (Hill) | 0.95 |
| Degree assortativity | −0.359 |
| Mean counterparties | 9.23 |
| Max counterparties | 49 |
| Density within core | 0.967 |
| Density within periphery | 0.0220 |
| Links touching the core | 0.773 |

Last three are the tiering result: core almost fully interconnected, periphery
barely faces itself, three quarters of links touch a core bank.

### Simulator behaviour (measured, safe to state)

- Below ~7% shock nothing fails; capital absorbs it.
- 8–15%: the system tips over.
- Past ~15%: direct failures plateau while contagion keeps climbing. Extra shock
  then kills only through the network.
- No single bank is contagious on its own — wiping out any one of the 60 fails
  only itself.

## 4. Figures — use these, do not redraw

Vector PDFs, publication-styled, 3.3in single-column and 6.9in double-column.
Each has a `.txt` caption sidecar next to it; **use that caption text.**

| File | What it shows |
|---|---|
| `../research/results/figure_tradeoff.pdf` | **The headline.** Links recovered vs crisis error (a) and structural error (b, log). Two panels. |
| `../research/results/figure_ensemble.pdf` | Cascade curves, all methods, bootstrap bands. |
| `../research/results/figure1.pdf` | Six panels: both networks, degree and exposure histograms, DebtRank, cascade. |
| `../research/results/greyscale_check/*.png` | Greyscale proofs. Check these if the deck may be printed. |

PNGs sit beside each PDF at 400 dpi if the deck tool cannot place vector.

**`research/results/` is gitignored, so a fresh clone has no figures.** If the
files above are missing, regenerate them. The pipeline is seeded, so the numbers
come out identical to the ones in this file:

```bash
cd .. && python3 research/scripts/run_demo.py     # ~60s, web display data
python3 research/scripts/run_test.py              # ~70s, results/test.json (figures need this)
python3 research/scripts/run_ablations.py         # ~6min, ablations.json
python3 research/scripts/stylized_facts.py        # instant
python3 research/scripts/make_tradeoff_figure.py
python3 research/scripts/make_ensemble_figure.py
python3 research/scripts/make_figure.py
```

`run_test.py` must run before the two figure scripts, which read
`results/test.json`. Do **not** run `run_tuning.py` unless you intend to redo
hyperparameter selection; it takes about nine minutes and only touches the
validation split.

If any number you generate disagrees with section 3, stop and say so rather than
using the new one. Output is meant to be byte-identical across runs.

**The single most persuasive visual** is not a chart. It is the maximum-entropy
network drawn next to the ground truth: a near-solid mesh against a sparse core
and periphery. Screenshot it from the live page (section "The clearest case",
select Maximum entropy in the scatter) or take the top-left/top-right panels of
`figure1.pdf` as the pattern.

---

## 5. Palette and design rules

Colour is semantic. Never decorative. Carry this into the deck.

```
ink        #10192B   text
paper      #F5F6F4   background
observed   #2E5E8C   simulated ground truth, always
generated  #C8842A   our model, always
baseline 1 #4A4F58   maximum entropy   ─┐
baseline 2 #7C828C   configuration      ├ the field's methods, unaccented
baseline 3 #9BA1AA   Erdős–Rényi       ─┘
stress     #A3302B   a bank has defaulted, and nothing else
rule       #D6D8D3   hairlines
```

The baselines are a **set**, not three individuals. The reader should see "the
field's methods cluster here", not track which grey is which. Grey value orders
them by how much each is told.

**Contrast warning.** Amber is 2.85:1 against paper and the two lighter greys
are 3.57:1 and 2.40:1. All fail as text. Put the colour on a swatch or marker
and set the label in ink. Do not darken the tokens.

Type: sentence case throughout. No all-caps labels. Tabular numerals for
figures only.

---

## 6. Things you must not say

- **Never claim BIS data.** BIS locational and consolidated statistics are
  country-and-sector aggregates. They contain no bank-level network. This is the
  most common mistake in this area and a reviewer will check it.
- **Never call the ground truth "real data" or "observed" alone.** It is
  simulated. Say "simulated ground truth" every time.
- **Never cite a paper by name.** Every citation slot in `../docs/related-work.md`
  is still `TODO-VERIFY`, and 28 cells in `../docs/calibration.md` are too.
  Nothing has been confirmed against a publisher record. If a slide needs a
  citation, leave a visible placeholder.
- **Never present the configuration model as a rival we lost to.** It is handed
  the true degree sequence and the true multiset of weights and reshuffles them.
  It cannot produce anything without a real network first. It is a ceiling, not
  a competitor.
- **Never drop the DebtRank gap.** It appears in the abstract-level summary, not
  only in limitations.

---

## 7. Suggested structure

Adjust to the time slot. The first six carry the argument.

1. **The problem.** Who owes whom between banks decides whether one failure
   becomes many. It is confidential. Research stalls.
2. **The workaround and its test.** People generate fake networks. They check
   them by counting recovered links.
3. **Why that test fails.** Maximum entropy: 100% of links recovered, near-solid
   mesh, rejected on every behavioural test. *Use the side-by-side networks.*
4. **The proposal.** A behavioural protocol: three contagion measures, scored
   against the same system.
5. **Results.** The headline table and `figure_tradeoff.pdf`.
6. **Our generator.** Graph VAE, four measured choices, the ablation table.
7. **Limitations.** DebtRank 0.150. Ground truth is simulated. No CCP layer yet.
   60 banks.
8. **What it would change.** Research without supervisory access; regulators
   sharing realistic networks without disclosure; policy tested against a
   thousand plausible systems instead of the one that exists.

If there is a live demo slot, the crisis simulator is the thing to show: pick a
shock, press run, watch both systems fail round by round, red banks and red
unpaid debts. Run `npm --prefix ../web run dev`.

---

## 8. Talk track for the hard questions

**"Isn't this just another graph VAE?"**
The generator is not the contribution. The evaluation protocol is, and it is a
negative result about how the field measures things. Hard to scoop, because it
required building both systems and comparing them.

**"Your model loses to the configuration model."**
Yes, and the configuration model cannot generate anything. It is given the
answer and shuffles it. Ours is given nothing and lands within 38% of that
ceiling.

**"Why is your DebtRank a third off?"**
Our upper tail of exposure sizes is still thinner than the ground truth, so the
typical bank looks less systemic than it is. We report it because a protocol
that only ever passes is not a protocol.

**"Your ground truth is made up."**
It is, and it is called that throughout. No bilateral exposure data is published
anywhere. If someone with supervisory access ran this pipeline on a real
network, nothing in the code would change — the protocol outlives the synthetic
data used to demonstrate it.

**"Could you calibrate to real data?"**
The network cannot be. The balance sheets can: bank sizes and capital ratios are
public. `configs/demo.yaml` carries a `calibration` block for exactly that,
switched off, every field `TODO-VERIFY` until filled from a named source.

---

## 9. Producing the file

A `pptx-deck:create-deck` skill is available in this environment; use it rather
than hand-rolling XML. Ask the user for the venue, time slot and slide count
before drafting if they have not said.
