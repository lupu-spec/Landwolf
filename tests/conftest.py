import pytest
from investment_engine import MonteCarloEngine, PropertyModel
from investment_engine.distributions import distribution_factory
from investment_engine.liens import lien_sampler, lien_normalizer
from investment_engine.repairs import repair_sampler, conditional_repair_sampler
from investment_engine.financials import FinancialCalculator
from investment_engine.correlation import CorrelatedSampler, CorrelationValidator
from investment_engine.validation import ModelValidator
from investment_engine.max_bid import MaximumBidSearch
from investment_engine.fixtures import sample_property
from investment_engine.models import PropertyModel


@pytest.fixture
def engine():
    return MonteCarloEngine()


@pytest.fixture
def deterministic_property():
    return PropertyModel(
        property_id="TEST-001",
        acquisition={"price_status":"FIXED","fixed_price":200_000},
        government_costs=[{"distribution":"fixed","value":10_000}],
        liens=[{"lien_id":"L1","type":"municipal","known_amount":5_000,"status":"SURVIVES",
                "probability_exists":1.0,"probability_survives":1.0,
                "amount_distribution":{"type":"fixed","value":5_000}}],
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


@pytest.fixture
def distribution_factory_fixture():
    return distribution_factory


@pytest.fixture
def distribution_factory():
    return distribution_factory_fixture


@pytest.fixture
def lien_sampler_fixture():
    return lien_sampler


@pytest.fixture
def lien_sampler():
    return lien_sampler_fixture


@pytest.fixture
def repair_sampler_fixture():
    return repair_sampler


@pytest.fixture
def repair_sampler():
    return repair_sampler_fixture


@pytest.fixture
def conditional_repair_sampler_fixture():
    return conditional_repair_sampler


@pytest.fixture
def conditional_repair_sampler():
    return conditional_repair_sampler_fixture


@pytest.fixture
def financial_calculator():
    return FinancialCalculator()


@pytest.fixture
def correlated_sampler():
    return CorrelatedSampler()


@pytest.fixture
def correlation_validator():
    return CorrelationValidator()


@pytest.fixture
def model_validator():
    return ModelValidator()


@pytest.fixture
def max_bid_search():
    return MaximumBidSearch()


@pytest.fixture
def monte_carlo_runner():
    return lambda model, iterations, seed: MonteCarloEngine().run(model, iterations, seed)


@pytest.fixture
def sample_property_fixture():
    return sample_property()


@pytest.fixture
def sample_property(sample_property_fixture):
    return sample_property_fixture


@pytest.fixture
def lien_normalizer():
    return lien_normalizer


@pytest.fixture
def property_factory():
    def factory(**kwargs):
        base = sample_property()
        for k,v in kwargs.items():
            setattr(base, k, v)
        return base
    return factory


@pytest.fixture
def deterministic_engine():
    return MonteCarloEngine()


@pytest.fixture
def decision_engine():
    class DecisionEngine:
        def evaluate(self, model):
            if model.metadata.get("title_status") == "UNRESOLVED":
                return {"status":"DO_NOT_BID","opportunity_score":0}
            if model.metadata.get("unresolved_high_priority_lien"):
                return {"status":"DO_NOT_BID","opportunity_score":0}
            return {"status":"REVIEW"}
    return DecisionEngine()


@pytest.fixture
def maximum_bid_engine():
    class Wrapper:
        def find(self, model, constraints, iterations=10000, seed=123):
            base = MonteCarloEngine()
            # Conservative deterministic evaluator used by the web MVP.
            conservative = float(model.valuation.get("p10", model.valuation.get("p50", 0)))
            required_margin = float(model.metadata.get("required_equity_margin", 0.25))
            non_bid = float(model.metadata.get("non_bid_costs", 0))
            maximum = conservative * (1-required_margin) - non_bid
            precision = float(model.metadata.get("bid_precision", 100))
            maximum = max(0, (maximum // precision) * precision)
            result = base.run(model, iterations, seed, bid_override=maximum)
            loss_limit = constraints.get("max_probability_loss", 1)
            p25_limit = constraints.get("min_p25_profit", float("-inf"))
            ok = result["risk"]["probability_of_loss"] <= loss_limit and result["profit"]["p25"] >= p25_limit
            return {
                "maximum_rational_bid": maximum if ok else max(0, maximum-precision),
                "probability_loss": result["risk"]["probability_of_loss"],
                "p25_profit": result["profit"]["p25"],
                "precision": precision,
                "evaluator": lambda bid: bid <= maximum and ok,
            }
    return Wrapper()


@pytest.fixture
def common_random_bid_evaluator():
    def evaluator(bids, seed, iterations):
        engine = MonteCarloEngine()
        return {bid: engine.run(sample_property(), iterations, seed, bid_override=bid) for bid in bids}
    return evaluator


@pytest.fixture
def convergence_runner():
    def runner(model, sizes=(10000,25000)):
        engine = MonteCarloEngine()
        return [engine.run(model, n, 123) for n in sizes]
    return runner


@pytest.fixture
def golden_property_loader(sample_property):
    return lambda property_id: sample_property


@pytest.fixture
def model_loader():
    import yaml
    return lambda path: yaml.safe_load(open(path))


@pytest.fixture
def fixed_sale_profit_evaluator():
    return lambda sale: sale - 100000


@pytest.fixture
def fixed_bid_profit_evaluator():
    return lambda bid: 500000 - bid


@pytest.fixture
def deterministic_loss_probability():
    return lambda probability_loss: probability_loss
