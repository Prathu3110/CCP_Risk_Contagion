# Method

Notation is fixed once and used everywhere, including in the code:

$$A_{ij} = \text{the amount bank } i \text{ owes bank } j$$

A row sum is therefore a bank's total interbank liabilities and a column sum is
its total interbank assets — what it stands to lose if its debtors fail. Write
$a_i$ for total assets, $e_i$ for equity, and $n = 60$ for the number of banks.

---

## 1. Ground truth

Real exposure data is confidential, so the "observed" system is itself
simulated. It reproduces the core-periphery structure reported for real
interbank markets (Craig and von Peter, 2014): a small set of money-centre
banks that intermediate for a sparse periphery.

A fraction $\kappa = 0.1$ of banks are core, placed at random indices. Edges are
Bernoulli with block-dependent probability

$$p_{ij} = \begin{cases}
0.85 & i, j \text{ both core} \\
0.35 & i \text{ core}, j \text{ periphery} \\
0.30 & i \text{ periphery}, j \text{ core} \\
0.02 & \text{both periphery}
\end{cases}$$

Weights are lognormal, $\log w_{ij} \sim \mathcal{N}(\mu, \sigma^2)$, multiplied
by 3 when either endpoint is core. Total assets are lognormal and 4 times larger
for core banks; equity is $e_i = 0.08 \, a_i \, \varepsilon_i$ with
$\log \varepsilon_i \sim \mathcal{N}(0, 0.2^2)$.

**One global rescaling matters more than it looks.** Interbank claims are scaled
by a single scalar so that system-wide interbank assets are 12% of system total
assets. Without it, individual exposures reach ten times the creditor's equity,
every shock destroys the system, and both contagion measures saturate — the
curves go flat and the experiment says nothing.

The balance sheet is then closed by the accounting identity, which is what makes
equity the buffer that absorbs a shock:

$$a_i^{\text{ext}} = a_i - \textstyle\sum_j A_{ji}, \qquad
\ell_i^{\text{ext}} = a_i - e_i - \textstyle\sum_j A_{ij}$$

---

## 2. The generator

A variational graph autoencoder (Kipf and Welling, 2016) over dense adjacency.
At 60 nodes this is mathematically identical to sparse message passing.

**Encoder.** With $\tilde{A}$ the symmetrised binary adjacency and
$\hat{A} = D^{-1/2}(\tilde{A} + I)D^{-1/2}$:

$$H = \mathrm{ReLU}(\hat{A} X W_0), \qquad
\mu = \hat{A} H W_\mu, \qquad
\log \sigma^2 = \hat{A} H W_\sigma$$

with $z_i \sim \mathcal{N}(\mu_i, \sigma_i^2)$ and $\dim z = 16$. Node features
$X$ are $\log a_i$ and $\log(e_i / a_i)$, standardised.

**Decoder.** Three heads on the latents:

$$\ell_{ij} = z_i^\top z_j + b(z_i) + b(z_j), \qquad
(m_{ij}, \log v_{ij}) = g([z_i; z_j]), \qquad
(m_i, \log v_i) = f(z_i)$$

$\ell_{ij}$ is an edge logit, $g$ predicts a Gaussian over the standardised log
exposure, and $f$ predicts one over the standardised log balance sheet.

**Loss.** Weighted cross-entropy on edges, Gaussian negative log-likelihood on
weights of true edges and on node attributes, and the usual KL term:

$$\mathcal{L} = \mathrm{BCE}_{\rho}(\ell, \mathbb{1}[A > 0])
+ \lambda \, \mathrm{NLL}(m, \log v)
+ \mathrm{NLL}(m_i, \log v_i)
+ \beta \, D_{\mathrm{KL}}\!\left(q(z \mid A, X) \,\|\, \mathcal{N}(0, I)\right)$$

with $\rho = 4$ correcting for edge sparsity and $\beta = 0.05$.

**Three choices that decide whether the output is usable.** Each was forced by a
measurement, not assumed:

1. *The weight and node heads are likelihoods, not point predictions.* Under MSE
   a head learns the conditional mean, and generated log-weight dispersion
   collapsed from 0.83 to 0.08 — every exposure came out the same size. Since
   contagion depends on the tail of the exposure distribution, that quietly made
   every generated system look safe.

2. *The node head models the equity ratio, not equity.* Its output is a diagonal
   Gaussian and so cannot represent the correlation between a bank's size and
   its capital. Modelling $\log e_i$ directly gave large banks small-bank
   capital and inflated mean equity by 24%.

3. *Latents are sampled from a kernel estimate of the aggregate posterior*
   (Ghosh et al., 2020), not from the $\mathcal{N}(0, I)$ prior. With a weak KL
   term the posterior never reaches the prior, so prior draws decode from a
   region the decoder never saw. A single Gaussian is not enough either: the
   latent cloud is bimodal, because core and periphery banks occupy different
   regions, and one Gaussian puts most of its mass in the empty space between.

**Sampling.** Draw $n$ latents, then calibrate a global logit shift $c$ by
bisection so that $\mathrm{mean}\,\sigma(\ell_{ij} + c)$ equals the observed edge
density, and draw each edge as $\mathrm{Bernoulli}(\sigma(\ell_{ij} + c))$.
Keeping the most probable edges instead reaches the same density but assigns
almost all of them to the hubs, giving a system of mega-banks surrounded by
isolated ones. Pinning density — the one statistic a global shift controls
directly — leaves every other statistic free to be an honest test.

---

## 3. DebtRank

Battiston, Puliga, Kaushik, Tasca and Caldarelli (2012), *DebtRank: Too central
to fail? Financial networks, the FED and systemic risk*, Scientific Reports
**2**:541.

Distress travels along the fraction of a creditor's equity each debt represents:

$$W_{ij} = \min\!\left(1, \frac{A_{ij}}{e_j}\right)$$

Each bank carries a continuous distress $h_i \in [0, 1]$ and a state
$s_i \in \{U, D, I\}$ — undistressed, distressed, inactive. Shock bank $s$ with
$h_s(0) = \psi$; all others start undistressed. Then

$$h_j(t + 1) = \min\!\left(1, \; h_j(t) + \sum_{i \,:\, s_i(t) = D} W_{ij} \, h_i(t)\right)$$

with $s_j \to D$ on the step its distress first rises, and $D \to I$ immediately
after. A bank therefore transmits exactly once. That rule is the whole point of
DebtRank: it is what stops distress circulating forever round a lending cycle
and being counted many times over.

With economic-value weights $v_j$ (interbank assets, normalised to sum to one),

$$R = \sum_j h_j(T) \, v_j - h_s(0) \, v_s$$

subtracting the initial shock so $R$ measures only what propagation added.

---

## 4. Eisenberg–Noe clearing

Eisenberg and Noe (2001), *Systemic risk in financial systems*, Management
Science **47**(2):236–249.

Total obligations and relative liabilities:

$$\bar{p}_i = \sum_j A_{ij}, \qquad
\Pi_{ij} = \frac{A_{ij}}{\bar{p}_i} \;\; (\bar{p}_i > 0)$$

Under a shock $s_i$ destroying that share of external assets, the resources bank
$i$ can put towards its interbank creditors are

$$c_i = \max\!\left(0, \; (1 - s_i) \, a_i^{\text{ext}} - \ell_i^{\text{ext}}\right)$$

External liabilities belong in that expression. Leaving them out makes every
bank look solvent against obligations worth a tenth of its balance sheet, and no
plausible shock ever causes a default. The clearing vector is the fixed point

$$p_i^* = \min\!\left(\bar{p}_i, \; \max\!\left(0, \; c_i + \sum_j \Pi_{ji} \, p_j^*\right)\right)$$

found by the fictitious default algorithm: start at $p^0 = \bar{p}$ and iterate.
The sequence decreases monotonically and converges to the greatest clearing
vector. Bank $i$ has defaulted when $p_i^* < \bar{p}_i$.

The cascade curve sweeps the mean shock from 5% to 50%. Each bank's actual loss
is $s_i = \mathrm{clip}(s \cdot \xi_i, 0, 1)$ with $\xi_i$ lognormal of unit
mean, so the shock lands unevenly; 20 repeats give the confidence band.

---

## 5. What is actually being claimed

Two networks having the same edges is the wrong test. No two real banking
systems have the same edges, and a generator that reproduced them exactly would
be leaking the confidential data it exists to replace.

The test here is behavioural: push both systems into a crisis under identical
rules and compare how far it travels. On that test the cascade curves agree to
about 7% across the whole range of shocks.

The same measurement names the limitation. Mean DebtRank comes out roughly a
third below the observed system's, because the generated upper tail of exposures
is still thinner than the ground truth. The typical bank therefore looks less
systemic than it is — and that is a statement about the model, left here rather
than tuned away.

---

## 6. Running it in the browser

The page lets a reader choose any shock level and any starting bank, so the
clearing model has to run live rather than replay the ten levels the pipeline
precomputed. It runs in the browser, which keeps the property that nothing on
the page depends on a server being up.

That means `web/lib/contagion.ts` is a second implementation of section 4, and
two implementations of one algorithm drift apart. `networks.json` therefore
carries raw balance-sheet figures rather than normalised ones — a crisis is not
scale-invariant — and edge weights are rounded to eight decimals rather than
five, because coarser rounding moves the default count. The two are checked
against each other by running both of

```bash
npm --prefix web run verify:contagion
python3 research/scripts/verify_contagion.py
```

which print the cascade size at ten shock levels and the mean and maximum
DebtRank, for both systems. They currently agree on all 40 values to six
decimal places.

The browser version additionally returns the state after every round, since the
point on the page is to watch a failure spread rather than be told the total.
`web/lib/analysis.ts` turns those rounds into prose. Every sentence it produces
is derived from that run's own numbers rather than selected by a hardcoded
threshold, so the account cannot drift out of step with what the model did:
a run in which nothing fails, one in which failures are all direct, and one
carried by contagion each take a different branch.
For Eisenberg–Noe those rounds are not a presentational device: each pass of the
fictitious default algorithm is one genuine round of the cascade, so banks that
go red in round 1 were sunk by the shock itself and everyone after them was
brought down by the failures before.

---

## References

- Battiston, S., Puliga, M., Kaushik, R., Tasca, P. and Caldarelli, G. (2012).
  DebtRank: Too central to fail? *Scientific Reports* 2:541.
- Craig, B. and von Peter, G. (2014). Interbank tiering and money center banks.
  *Journal of Financial Intermediation* 23(3):322–347.
- Eisenberg, L. and Noe, T. (2001). Systemic risk in financial systems.
  *Management Science* 47(2):236–249.
- Ghosh, P., Sajjadi, M., Vergari, A., Black, M. and Schölkopf, B. (2020).
  From variational to deterministic autoencoders. *ICLR*.
- Hoff, P., Raftery, A. and Handcock, M. (2002). Latent space approaches to
  social network analysis. *JASA* 97(460):1090–1098.
- Kipf, T. and Welling, M. (2016). Variational graph auto-encoders.
  *NeurIPS Bayesian Deep Learning Workshop*.
