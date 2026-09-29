# Related work

**Every citation slot in this file is `TODO-VERIFY`.** The argument, the
grouping and the claim each cited work must support are written out; the author,
year and venue are not. Fill them in by hand against publisher records.

This discipline is deliberate. AI-generated citations have already introduced
errors in this project once, and a fabricated reference is the single fastest
way to lose a reviewer. Where a work is already cited in `docs/method.md` it is
marked **(already cited)** — those six still need checking against the
publisher record before submission, but they are not new inventions.

Read each entry as: *what this slot must establish* → *what to find*.

---

## 1. Why the data problem exists

**1.1 — Confidentiality of bilateral exposure data.**
Must establish: supervisors hold bank-level bilateral exposures and do not
publish them, so researchers outside central banks cannot obtain the network.
Find: a central-bank or BIS methodological paper stating the access restriction.
`TODO-VERIFY`

**1.2 — What aggregate statistics do and do not contain.**
Must establish: BIS locational and consolidated banking statistics are
country-and-sector aggregates, containing no bank-level network. This slot
exists to pre-empt the most common reviewer misunderstanding, and to justify the
claim in `docs/data.md` that no BIS calibration is possible.
Find: the BIS statistical methodology documentation.
`TODO-VERIFY`

**1.3 — Studies that did have supervisory access.**
Must establish: the small set of papers that analysed real national interbank
networks, and that each required privileged access. These are the source of the
stylized facts in section 2.
Find: national interbank network studies, typically central-bank working papers.
`TODO-VERIFY`

---

## 2. What real interbank networks look like

These works supply the empirical ranges that `docs/calibration.md` compares the
simulated ground truth against. **Each entry here must be matched to a row in
that file.**

**2.1 — Core-periphery structure and tiering.**
Must establish: real interbank markets have a small densely connected core of
money-centre banks intermediating for a sparse periphery, and a method for
detecting it.
Find: Craig & von Peter, *Interbank tiering and money center banks*
**(already cited in method.md)** `TODO-VERIFY`

**2.2 — Low density.**
Must establish: real interbank networks are sparse, with a published density
range. Compare against our 0.0782.
`TODO-VERIFY`

**2.3 — Heavy-tailed degree distribution.**
Must establish: a few banks have very many counterparties, with a published tail
exponent range. Compare against our Hill estimate of 0.95.
`TODO-VERIFY`

**2.4 — Negative degree assortativity.**
Must establish: large banks connect to small ones rather than to each other.
Compare against our −0.359.
`TODO-VERIFY`

---

## 3. Reconstructing an unknown network

The baselines in `research/src/baselines.py` come from here. This section must
make clear that these are *reconstruction* methods: each is handed a summary of
a network that already exists, and cannot generate one from nothing.

**3.1 — Maximum entropy / iterative proportional fitting.**
Must establish: the RAS algorithm as the field standard for reconstructing a
network from known row and column totals.
Find: the econometric or interbank-specific statement of IPF/RAS.
`TODO-VERIFY`

**3.2 — Maximum entropy understates contagion.**
Must establish, and this is load-bearing for our argument: reconstructions that
spread exposures evenly produce systems that look safer than reality, because
the concentration that drives contagion is smoothed away. Our result — maximum
entropy recovering every true link while its DebtRank distribution is still
rejected against the truth — is a sharper version of this finding, and the paper
should say which prior work it sharpens. Note when writing it up that maximum
entropy is deterministic and contributes one sample, so this is one decisive
test rather than a rate.
`TODO-VERIFY`

**3.3 — Sparser reconstruction methods.**
Must establish: later methods that produce sparse reconstructions rather than
near-complete ones, and how they are evaluated. If any of them are evaluated
behaviourally rather than on edge accuracy, that is directly relevant to our
contribution and must be acknowledged rather than glossed.
`TODO-VERIFY`

**3.4 — Configuration model as a null.**
Must establish: degree-preserving rewiring as a standard null model, and that it
requires the true degree sequence. This supports our framing of it as an upper
bound rather than a competitor.
Find: Hoff, Raftery & Handcock is cited for latent-space models
**(already cited in method.md)**; the configuration model needs its own source.
`TODO-VERIFY`

---

## 4. Generative models for graphs

**4.1 — Variational graph autoencoders.**
Must establish: the encoder/decoder formulation our generator extends.
Find: Kipf & Welling, *Variational graph auto-encoders*
**(already cited in method.md)** `TODO-VERIFY`

**4.2 — Latent-space network models with node effects.**
Must establish: per-node popularity terms in latent-space models, which is the
bias head in our decoder.
Find: Hoff, Raftery & Handcock **(already cited in method.md)** `TODO-VERIFY`

**4.3 — Sampling from the aggregate posterior.**
Must establish: that drawing from a density fitted to encoded latents, rather
than from the prior, addresses the mismatch a weak KL term leaves behind.
Find: Ghosh et al., *From variational to deterministic autoencoders*
**(already cited in method.md)** `TODO-VERIFY`

**4.4 — Generative models applied to financial networks.**
Must establish: prior attempts to *generate* rather than reconstruct financial
networks, and how they were evaluated. **This is the slot most likely to contain
a paper that anticipates part of our contribution.** Search it hardest, and if
something does anticipate the behavioural evaluation idea, say so plainly and
position against it rather than around it.
`TODO-VERIFY`

---

## 5. Contagion models

These are what "behaviour" means in our protocol.

**5.1 — DebtRank.**
Must establish: distress propagation as a fraction of system economic value,
without requiring default, and the one-shot transmission rule that stops
distress circulating round a lending cycle.
Find: Battiston, Puliga, Kaushik, Tasca & Caldarelli
**(already cited in method.md)** `TODO-VERIFY`

**5.2 — Clearing payment vectors.**
Must establish: the clearing fixed point and the fictitious default algorithm,
whose iterations are the rounds the page animates.
Find: Eisenberg & Noe **(already cited in method.md)** `TODO-VERIFY`

**5.3 — Which contagion channel dominates.**
Must establish: that pure counterparty-default contagion is often found to be
small, and that amplification comes from funding and fire-sale channels our
model does not include. **This belongs in Limitations, not buried here.**
`TODO-VERIFY`

---

## 6. How synthetic data is usually evaluated

This section carries the paper's contribution, so it must be the most complete.

**6.1 — Reconstruction accuracy as the acceptance criterion.**
Must establish: that edge-level accuracy against a known network is the
conventional way this field judges a generated or reconstructed network.
`TODO-VERIFY`

**6.2 — Behavioural or task-based evaluation elsewhere.**
Must establish: evaluating synthetic data by whether downstream conclusions
survive, in any field — synthetic tabular data, simulation, privacy. Our
protocol is an instance of a general idea, and saying so is a strength.
`TODO-VERIFY`

**6.3 — Evaluation of generated graphs.**
Must establish: how the graph generation literature evaluates samples, including
statistics-based comparisons. If a standard suite exists, our protocol should be
positioned as its domain-specific counterpart.
`TODO-VERIFY`

**6.4 — Privacy and disclosure.**
Must establish: that a generator reproducing the true network too exactly leaks
the data it was meant to replace. This is our argument for why high edge
accuracy is not merely uninformative but undesirable, so the slot must be filled
or the argument dropped.
`TODO-VERIFY`

---

## 7. Central clearing

Future work only. No claim in the current paper depends on this section.

**7.1 — Novation and CCP structure.** `TODO-VERIFY`

**7.2 — Default waterfalls and Cover-2.**
Must establish: the ordered resource stack and the regulatory standard requiring
a CCP to survive its two largest members failing.
`TODO-VERIFY`

**7.3 — Does central clearing reduce or concentrate risk.**
Must establish: that this is open and contested, which is what makes it worth a
generator.
`TODO-VERIFY`

---

## Filling this in

1. Work top to bottom. Sections 3 and 6 carry the contribution; do them first.
2. For each slot, confirm the work says what the slot claims it says. A paper
   that is merely *about* the topic is not enough.
3. Record the DOI or a stable publisher link, not a search result.
4. Where no suitable work exists, **delete the slot and weaken the claim it
   supported** rather than stretching an unrelated citation to cover it.
5. Section 4.4 and section 6.2 are where a scooping risk would appear. If one
   does, the honest move is to cite it prominently and narrow our claim.
