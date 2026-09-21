"""Seeded scenario model. Estimates are user assumptions, never an appraisal."""

import math
from typing import Any

import numpy as np
from numpy.typing import NDArray

from landwolf.schemas import AnalysisInput, Range


def sample(rng: np.random.Generator, spec: Range, count: int) -> NDArray[np.float64]:
    if spec.low == spec.high:
        return np.full(count, spec.low, dtype=np.float64)
    return rng.triangular(spec.low, spec.likely, spec.high, count)


def analyze(spec: AnalysisInput) -> dict[str, Any]:
    rng = np.random.default_rng(spec.seed)
    sale = sample(rng, spec.resale, spec.iterations)
    repairs = sample(rng, spec.repairs, spec.iterations)
    fixed = spec.lien_reserve + spec.closing_costs + spec.holding_months * spec.monthly_holding
    costs = repairs + fixed
    # Financing assumes the entire bid is financed with simple interest, no amortization.
    multiplier = (
        1
        + spec.buyer_premium_pct / 100
        + spec.annual_financing_pct / 100 * spec.holding_months / 12
    )
    proceeds = sale * (1 - spec.selling_cost_pct / 100)

    def outcomes(bid: float) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        invested = costs + bid * multiplier
        return proceeds - invested, invested

    def qualifies(bid: float) -> bool:
        profits, invested = outcomes(bid)
        # Positive proceeds with zero investment satisfy the return gate, but have
        # no finite ROI to display. Test median ROI directly, including even samples.
        returns = np.divide(
            profits, invested, out=np.full_like(profits, np.inf), where=invested > 0
        )
        return bool(
            np.mean(profits < 0) <= spec.max_loss_probability_pct / 100
            and np.median(profits) >= spec.min_profit
            and np.median(returns) >= spec.target_roi_pct / 100
        )

    feasible = qualifies(0)
    low, high = 0.0, spec.resale.high / multiplier
    if feasible:
        # Common random numbers make each gate non-increasing with bid.
        for _ in range(48):
            mid = (low + high) / 2
            if qualifies(mid):
                low = mid
            else:
                high = mid
    max_bid = math.floor(low * 100) / 100 if feasible else None
    profits, invested = outcomes(spec.purchase_price)
    loss_probability = float(np.mean(profits < 0))
    # Wilson interval reports sampling uncertainty, not uncertainty in the assumptions.
    n, z = spec.iterations, 1.96
    center = (loss_probability + z * z / (2 * n)) / (1 + z * z / n)
    radius = (
        z
        * math.sqrt(loss_probability * (1 - loss_probability) / n + z * z / (4 * n * n))
        / (1 + z * z / n)
    )
    valid = invested > 0
    median_roi = float(np.median(profits[valid] / invested[valid]) * 100) if valid.any() else None
    target = max(spec.target_roi_pct, 1)
    score = (
        None
        if median_roi is None
        else round(100 * (1 - loss_probability) * min(1, max(0, median_roi / target)))
    )
    counts, edges = np.histogram(profits, bins=20)

    def percentiles(values: NDArray[np.float64]) -> dict[str, float]:
        return {f"p{q}": round(float(np.percentile(values, q)), 2) for q in (10, 50, 90)}

    return {
        "model_version": "beta-1.0",
        "iterations": n,
        "seed": spec.seed,
        "profit": percentiles(profits),
        "acquisition_cost": percentiles(invested),
        "median_roi_pct": None if median_roi is None else round(median_roi, 2),
        "loss_probability_pct": round(loss_probability * 100, 2),
        "loss_probability_interval_pct": [
            round(max(0, center - radius) * 100, 2),
            round(min(1, center + radius) * 100, 2),
        ],
        "maximum_bid": max_bid,
        "feasible": feasible,
        "current_bid_meets_targets": qualifies(spec.purchase_price),
        "scenario_score": score,
        "histogram": [
            {
                "low": round(float(edges[i]), 2),
                "high": round(float(edges[i + 1]), 2),
                "count": int(counts[i]),
            }
            for i in range(len(counts))
        ],
        "assumptions": spec.model_dump(),
        "limitations": [
            "Scenario estimate, not an appraisal, title opinion, or bid recommendation.",
            (
                "Resale uses hypothetical asking-price/bid scenarios, not a market valuation "
                "or statistically estimated confidence bounds."
                if spec.resale_basis == "bid_scenario"
                else "Resale uses user-edited assumptions, not an independently verified valuation."
            ),
            *(
                [
                    "One or more costs or the holding period are zero. "
                    "Unestimated zero placeholders "
                    "exclude costs and can overstate returns; verify every zero."
                ]
                if 0
                in [
                    spec.repairs.low,
                    spec.repairs.likely,
                    spec.repairs.high,
                    spec.lien_reserve,
                    spec.closing_costs,
                    spec.holding_months,
                    spec.monthly_holding,
                    spec.buyer_premium_pct,
                    spec.selling_cost_pct,
                    spec.annual_financing_pct,
                ]
                else []
            ),
            "Resale and repair ranges are scenario assumptions sampled independently; "
            "correlated shocks are not modeled.",
            "Lien reserve is a user estimate, not a determination of which liens survive a sale.",
            "Financing is simple interest on 100% of the bid; "
            "taxes belong in monthly holding costs.",
            "Loss-probability interval covers Monte Carlo sampling error only, "
            "not model or market uncertainty.",
        ],
    }
