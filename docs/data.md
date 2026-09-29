# What data this uses, and why none of it is real

Short answer: no external dataset is used anywhere. Everything traces to one
integer, `seed: 20260915` in `research/configs/demo.yaml`.

This is not a shortcut. It is forced, and understanding why is the whole reason
the project exists.

## Why there is no real network

A bilateral interbank exposure network is a list of which bank owes which other
bank how much. That object is collected by supervisors and is not published,
anywhere, at bank level. It identifies individual institutions and their
vulnerabilities, so releasing it would itself be a financial stability risk.

**BIS statistics do not contain it.** This matters because it is the most common
mistake in this area. The BIS locational and consolidated banking statistics
report claims aggregated by *country* and by *sector* — how much the banking
system of one country is owed by the banking system of another. There are no
individual banks in them and therefore no bank-level network. A claim that a
60-node bank network is calibrated to BIS data is false and would not survive
review. No such claim is made here.

The same holds for the other sources people reach for first: published stress
test results give bank-level balance sheets but no bilateral links; payment
system data is restricted; commercial datasets cover traded instruments rather
than the full exposure network.

## What that leaves

The field's standard response is to work with a *simulated ground truth*: build
a synthetic system whose structure reproduces the regularities that studies of
real interbank markets report, then treat it as the thing to be matched.

That is what happens here. `research/src/generators.py` samples a system from
the parameters in `configs/demo.yaml`:

- 60 banks, 10% of them core.
- Links drawn from four block probabilities, so core banks deal with almost
  everyone and periphery banks deal mainly with the core.
- Exposure sizes lognormal, larger when a core bank is involved.
- Bank sizes lognormal, larger for core banks.
- Equity at a target ratio of assets, with lognormal noise.
- One global rescaling so system-wide interbank claims are a set share of system
  total assets.

The corpus the model trains on is 300 independent draws from that sampler. The
system every method is scored against is one more draw, held out from training.
It is called the **simulated ground truth** everywhere in the code, the page and
the paper — never "the real data", never "observed" on its own — so that no
reader can mistake it for supervisory records.

## What is measured, and what is not

`docs/calibration.md` reports what the simulated ground truth looks like against
published stylized facts: density, core size, degree tail, assortativity,
tiering. **Every published range and source cell in that file is `TODO-VERIFY`
and must be filled in by hand from a publisher record.** They are deliberately
empty. An invented citation is fatal at review, and this project has already had
AI-generated citations introduce errors once.

That table is the only place real-world evidence enters the work. It is
therefore the highest-risk part of it.

## The honest improvement available

The *network* has to be synthetic. The *balance sheets* do not.

Bank sizes, capital ratios and interbank shares are reported in public
supervisory disclosures. Pinning the balance-sheet parameters to real published
figures, while leaving the network generated, upgrades the claim from

> we invented a banking system

to

> we invented the links between banks whose balance sheets match a real system

That is a materially stronger position for the same amount of synthetic
structure, and it costs nothing in confidentiality because balance sheets are
already public.

`configs/demo.yaml` now carries a `calibration` block for exactly this. It is
`enabled: false` and every field is `TODO-VERIFY`. The pipeline ignores it until
those are filled in from a named source with a reporting date. Nothing is
guessed and no figure is used until it has a citation attached.

## What would change if a real network appeared

If a researcher with supervisory access ran this pipeline on a real network,
almost nothing in the code would change. The simulated ground truth would be
swapped for the real one, and every score in the paper would be recomputed
against it. The generator, the baselines, the contagion models and the
evaluation protocol are all indifferent to where the target network came from.

That is the point of separating the protocol from the generator: the protocol is
the contribution, and it outlives the synthetic data used to demonstrate it.
