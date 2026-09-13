from .models import PropertyModel
from .financials import FinancialCalculator
from .liens import lien_sampler, lien_normalizer
from .repairs import repair_sampler, conditional_repair_sampler
from .correlation import CorrelatedSampler, CorrelationValidator
from .validation import ModelValidator
from .max_bid import MaximumBidSearch


def sample_property():
    return PropertyModel(
        property_id="SAMPLE-001",
        acquisition={"price_status":"FIXED","fixed_price":200_000},
        government_costs=[{"distribution":"fixed","value":10_000}],
        liens=[{"lien_id":"L1","known_amount":5_000,"probability_exists":1.0,
                "probability_survives":1.0,"amount_distribution":{"type":"fixed","value":5_000}}],
        title_costs={"title_search":500,"attorney":1500},
        repairs=[{"component":"roof","probability_required":1.0,
                  "cost_distribution":{"type":"fixed","value":20_000}}],
        holding_period={"distribution":{"type":"categorical","outcomes":[12],"probabilities":[1.0]}},
        holding_costs={"property_tax":{"type":"fixed","value":500},
                       "insurance":{"type":"fixed","value":200},
                       "utilities":{"type":"fixed","value":0},
                       "maintenance":{"type":"fixed","value":0},
                       "financing":{"enabled":False}},
        auction_costs={"buyer_premium":{"type":"fixed","value":0.0}},
        closing_costs={"type":"fixed","value":2_000},
        other_costs={"type":"fixed","value":3_000},
        valuation={"p10":350_000,"p25":350_000,"p50":350_000,"p75":350_000,"p90":350_000},
        market_growth={"type":"fixed","value":0.0},
        selling_costs={"rate":{"type":"fixed","value":0.06}},
        inspection_quality=1.0,
    )
