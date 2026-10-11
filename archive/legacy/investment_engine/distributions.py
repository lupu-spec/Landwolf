import numpy as np


def sample_distribution(config, n, rng):
    kind = str(config.get("type", config.get("distribution", "fixed"))).lower()
    if kind == "fixed":
        value = float(config.get("value", config.get("fixed_price", 0)))
        return np.full(n, value, dtype=float)
    if kind == "triangular":
        return rng.triangular(float(config["low"]), float(config["mode"]), float(config["high"]), n)
    if kind == "normal":
        return np.maximum(0, rng.normal(float(config["mean"]), float(config["std"]), n))
    if kind == "categorical":
        outcomes = np.asarray(config["outcomes"], dtype=float)
        probs = np.asarray(config["probabilities"], dtype=float)
        probs = probs / probs.sum()
        return rng.choice(outcomes, size=n, p=probs)
    raise ValueError(f"Unsupported distribution: {kind}")


class Distribution:
    def __init__(self, config):
        self.config = config

    def sample(self, n, rng):
        return sample_distribution(self.config, n, rng)


def distribution_factory(config):
    return Distribution(config)
