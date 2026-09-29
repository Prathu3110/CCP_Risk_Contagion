"""Train, validation and test networks, drawn once from one seed.

Why this module exists: the first version of this project sampled 300 training
networks and one evaluation network, then chose hyperparameters by comparing
contagion gaps against that evaluation network. That is selection on the test
set. Any score produced that way is optimistic and a reviewer is entitled to
discard it.

The rule enforced here:

  * `train`      — the model fits these.
  * `validation` — every hyperparameter and modelling decision is made against
    these, and they may be inspected freely.
  * `test`       — scored once, at the end. Nothing is ever selected on them.

`corpus_density` is the other half of the fix. The generator needs a target
density to calibrate its edge threshold against. Taking it from the evaluation
network hands the model a true statistic about the thing it is being judged on,
which is precisely the privileged access the baselines are criticised for. It
comes from the training corpus instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from generators import Network, sample_corpus


@dataclass(frozen=True)
class Split:
    train: list[Network]
    validation: list[Network]
    test: list[Network]

    @property
    def corpus_density(self) -> float:
        """Mean edge density of the training networks.

        The one statistic the generator is entitled to know, because it comes
        from the data it was trained on rather than from the data it is judged
        against.
        """
        return float(np.mean([density(net) for net in self.train]))


def density(net: Network) -> float:
    return float((net.A > 0).sum()) / (net.n * (net.n - 1))


def build(cfg: dict[str, Any]) -> Split:
    """Draw all three sets from one seeded stream, train first."""
    rng = np.random.default_rng(int(cfg["seed"]))
    corpus_cfg = cfg["corpus"]
    network_cfg = cfg["network"]

    train = sample_corpus(network_cfg, int(corpus_cfg["n_train"]), rng)
    validation = sample_corpus(network_cfg, int(corpus_cfg.get("n_validation", 20)), rng)
    test = sample_corpus(network_cfg, int(corpus_cfg.get("n_test", 5)), rng)
    return Split(train=train, validation=validation, test=test)
