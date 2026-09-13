import numpy as np
from .distributions import sample_distribution


def sample_repair(repair, n, rng):
    p = float(repair.get("probability_required", 1.0))
    required = rng.random(n) < p
    amount = sample_distribution(repair["cost_distribution"], n, rng)
    return np.where(required, amount, 0.0)


def repair_sampler(repair, n, rng):
    return sample_repair(repair, n, rng)


def sample_conditional(parent_probability, child_probability_given_parent, n, rng):
    parent = rng.random(n) < parent_probability
    child = rng.random(n) < child_probability_given_parent
    return (parent & child).astype(float)


def conditional_repair_sampler(parent_probability, child_probability_given_parent, n, rng):
    return sample_conditional(parent_probability, child_probability_given_parent, n, rng)
