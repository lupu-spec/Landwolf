import numpy as np
from .distributions import sample_distribution


def sample_lien(lien, n, rng):
    p_exists = float(lien.get("probability_exists", 1.0))
    p_survives = float(lien.get("probability_survives", 1.0))
    exists = rng.random(n) < p_exists
    survives = rng.random(n) < p_survives
    amount_cfg = lien.get("amount_distribution", {"type": "fixed", "value": lien.get("known_amount", 0)})
    amount = sample_distribution(amount_cfg, n, rng)
    return np.where(exists & survives, amount, 0.0)


def lien_sampler(lien, n, rng):
    return sample_lien(lien, n, rng)


def normalize_lien(lien):
    x = dict(lien)
    x.setdefault("probability_exists", 1.0)
    x.setdefault("probability_survives", 1.0 if str(x.get("status","")).upper() == "SURVIVES" else 0.0)
    return x


def lien_normalizer(lien):
    return normalize_lien(lien)
