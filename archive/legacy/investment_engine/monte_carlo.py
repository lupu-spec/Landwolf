import numpy as np
from .distributions import sample_distribution
from .liens import sample_lien
from .repairs import sample_repair
from .financials import total_acquisition_cost, profit, roi
from .validation import validate_model


def _scalar_or_distribution(value, n, rng):
    if isinstance(value, (int, float)):
        return np.full(n, float(value))
    return sample_distribution(value, n, rng)


def _sum_configs(configs, n, rng):
    total = np.zeros(n)
    for cfg in configs or []:
        total += _scalar_or_distribution(cfg, n, rng)
    return total


class MonteCarloEngine:
    def run(self, model, iterations=25000, seed=847291, bid_override=None):
        validate_model(model)
        if iterations <= 0 or iterations > 100000:
            raise ValueError("iterations must be between 1 and 100000")

        rng = np.random.default_rng(seed)

        if bid_override is not None:
            bid = np.full(iterations, float(bid_override))
        else:
            bid_cfg = model.acquisition
            if str(bid_cfg.get("price_status", "")).upper() == "FIXED":
                bid = np.full(iterations, float(bid_cfg.get("fixed_price", 0)))
            else:
                bid = _scalar_or_distribution(bid_cfg.get("distribution", {"type":"fixed","value":0}), iterations, rng)

        government = _sum_configs(model.government_costs, iterations, rng)
        liens = sum((sample_lien(x, iterations, rng) for x in model.liens), np.zeros(iterations))
        repairs = sum((sample_repair(x, iterations, rng) for x in model.repairs), np.zeros(iterations))
        title = sum(float(v) for v in model.title_costs.values() if isinstance(v, (int,float)))
        closing = _scalar_or_distribution(model.closing_costs, iterations, rng)
        other = _scalar_or_distribution(model.other_costs, iterations, rng)

        months_cfg = model.holding_period.get("distribution", {"type":"fixed","value":0})
        months = sample_distribution(months_cfg, iterations, rng)
        monthly_holding = np.zeros(iterations)
        for key, cfg in model.holding_costs.items():
            if key == "financing":
                continue
            monthly_holding += _scalar_or_distribution(cfg, iterations, rng)
        holding = monthly_holding * months

        auction = np.zeros(iterations)
        for key, cfg in model.auction_costs.items():
            if key == "buyer_premium":
                auction += bid * _scalar_or_distribution(cfg, iterations, rng)
            else:
                auction += _scalar_or_distribution(cfg, iterations, rng)

        tac = bid + government + liens + title + repairs + holding + auction + closing + other

        vals = model.valuation
        sale_base = float(vals.get("p50", 0))
        sale = np.full(iterations, sale_base)
        growth = _scalar_or_distribution(model.market_growth or {"type":"fixed","value":0}, iterations, rng)
        sale *= np.power(1 + growth, months / 12.0)

        sell_rate = _scalar_or_distribution(
            model.selling_costs.get("rate", {"type":"fixed","value":0}),
            iterations, rng
        )
        selling = sale * sell_rate
        profits = sale - selling - tac
        cash_invested = tac
        roi_values = np.divide(
            profits, cash_invested,
            out=np.full(iterations, np.nan),
            where=cash_invested != 0,
        )

        p = lambda q: float(np.quantile(profits, q))
        loss_prob = float(np.mean(profits < 0))

        return {
            "simulation": {"iterations": iterations, "seed": seed},
            "true_acquisition_cost": {
                "p10": float(np.quantile(tac, .10)),
                "p25": float(np.quantile(tac, .25)),
                "p50": float(np.quantile(tac, .50)),
                "p75": float(np.quantile(tac, .75)),
                "p90": float(np.quantile(tac, .90)),
            },
            "profit": {"p10": p(.10), "p25": p(.25), "p50": p(.50), "p75": p(.75), "p90": p(.90)},
            "risk": {"probability_of_loss": loss_prob},
            "returns": {
                "median_roi": float(np.nanmedian(roi_values)),
                "mean_roi": float(np.nanmean(roi_values)),
            },
            "bid": {
                "current_bid": float(np.median(bid)),
                "max_rational_bid": None,
            },
        }
