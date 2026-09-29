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

All from the committed seeded run. Seed 20260915, 60 banks, 300 training
networks, 300 epochs, 16-dim latent. 20 samples per stochastic method; maximum
entropy is deterministic and contributes 1.

### Headline table

| Method | Links recovered | Crisis-behaviour error | Structural error | Passes KS test | What it is told |
|---|---|---|---|---|---|
| Our model (graph VAE) | 0.064 | **0.123** [0.092, 0.157] | 0.091 | **19 of 20** | nothing |
| Maximum entropy | **1.000** | 0.205 | 3.214 | **0 of 1** | true row and column totals |
| Configuration model | 0.364 | 0.089 [0.072, 0.107] | 0.022 | 20 of 20 | true degree sequence + weight multiset |
| Erdős–Rényi | 0.075 | 0.397 [0.351, 0.443] | 0.250 | 0 of 20 | true density |

**The money line:** maximum entropy recovers 100% of links and is still told
apart from the real system by the behavioural test (p < 0.001). Our model
recovers 6% and passes 19 of 20.

**Do not overstate this.** Maximum entropy is deterministic, so it contributes
one sample and therefore one KS test, not twenty. The test is decisive on its
own (p is effectively zero), but "fails every time" implies repeated trials that
do not exist.

**Do not oversell the model either.** It is not best on any single crisis
measure: second on mean DebtRank, third on max DebtRank, fourth and last on
cascade size. Its aggregate lead over maximum entropy and Erdos-Renyi comes
almost entirely from mean DebtRank, where those two are catastrophic (0.556 and
0.807 against our 0.150). Strip that measure out and the lead disappears. The
honest claim is: second of four overall, beats both usable alternatives, loses
to a method that is handed the answer.

**The KS test direction is inverted and must be explained on the slide.** A
*high* p-value is the good outcome: it means the generated distribution of
systemic importance cannot be told apart from the truth. Say this out loud or it
reads as an error.

### Per-metric gaps (relative gap vs ground truth, lower is better)

| Metric | Our model | Max entropy | Configuration | Erdős–Rényi |
|---|---|---|---|---|
| Mean DebtRank | 0.150 | 0.556 | 0.097 | 0.807 |
| Max DebtRank | 0.151 | 0.054 | 0.108 | 0.344 |
| Mean cascade size | 0.066 | 0.007 | 0.062 | 0.041 |
| Edge density | 0.030 | **10.942** | 0.001 | 0.050 |
| Degree assortativity | 0.205 | 0.998 | 0.085 | 0.899 |
| Mean exposure size | 0.102 | 0.916 | 0.001 | 0.052 |
| Mean equity ratio | 0.025 | 0.000 | 0.000 | 0.000 |

Two caveats that belong on the slide if this table is shown:
- Maximum entropy has the **smallest** cascade-size gap (0.007). Cascade size
  alone does not separate the methods; the DebtRank distribution does.
- The equity-ratio zeros are free. Three methods inherit the real balance
  sheets, so they cannot miss.

### Our model against the ground truth (structural)

| Statistic | Ground truth | Our model | Gap |
|---|---|---|---|
| Mean degree | 9.23 | 9.63 | 4.3% |
| Edge count | 277 | 289 | 4.3% |
| Density | 0.0782 | 0.0816 | 4.3% |
| Mean exposure | 0.0397 | 0.0412 | 3.8% |
| Mean equity ratio | 0.0813 | 0.0837 | 2.9% |
| Degree assortativity | −0.359 | −0.424 | 18.1% |
| Max degree | 49 | 59 | 20.4% |

### Ablations (5 samples per variant)

Full model: crisis-behaviour error 0.147, log-weight spread 0.739. Ground-truth
spread is 0.825.

| Choice switched off | Error | Change | Log-weight spread |
|---|---|---|---|
| Keep top edges, not sampled | 0.249 | **+0.101** | 0.654 |
| Model equity, not the ratio | 0.207 | +0.060 | 0.736 |
| Sample from the prior | 0.197 | +0.049 | **1.232** |
| Squared error, not sampled | 0.166 | +0.019 | **0.363** |
| No balance-sheet scaling | 0.141 | **−0.007** | 0.739 |

Four of five earn their place. **The fifth is a negative result and stays on the
slide.** Balance-sheet scaling changes the score by −0.007, inside noise. The
flag can only disable decoder-side rescaling; disabling it in the ground-truth
sampler would change the target. The test does not reach the original claim.

Best mechanism story: squared error drives exposure spread down to 0.363 and
prior sampling drives it up to 1.232, against a truth of 0.825. Opposite
distortions, both wrong.

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
- 8–15%: the system tips over. At 10%, 6 of 6 core banks fail in the ground
  truth against 2 of 6 in our model.
- Past ~15%: direct failures plateau at 31 while contagion keeps climbing. Extra
  shock then kills only through the network.
- No single bank is contagious on its own — wiping out any one of the 60 fails
  only itself, in both systems.
- 2 of 60 ground-truth banks owe nobody and so can never default in
  Eisenberg–Noe by construction.

---

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
cd .. && python3 research/scripts/run_demo.py          # ~30s, writes networks.npz
python3 research/scripts/run_baselines.py              # ~3min, ensemble.json
python3 research/scripts/run_ablations.py              # ~3min, ablations.json
python3 research/scripts/stylized_facts.py             # instant
python3 research/scripts/make_tradeoff_figure.py
python3 research/scripts/make_ensemble_figure.py
python3 research/scripts/make_figure.py
```

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
