import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from landwolf.analysis import analyze
from landwolf.schemas import AnalysisInput, Range


def test_bid_scenario_provenance_and_zero_cost_warnings(scenario: AnalysisInput) -> None:
    spec = scenario.model_copy(update={"resale_basis": "bid_scenario", "lien_reserve": 0})
    result = analyze(spec)
    assert result["assumptions"]["resale_basis"] == "bid_scenario"
    assert any("hypothetical asking-price/bid" in note for note in result["limitations"])
    assert any("zero placeholders" in note for note in result["limitations"])
    assert (
        result["profit"]
        == analyze(spec.model_copy(update={"resale_basis": "custom_scenario"}))["profit"]
    )


def test_analysis_rejects_fabricated_provenance(scenario: AnalysisInput) -> None:
    with pytest.raises(ValidationError):
        AnalysisInput.model_validate(
            {**scenario.model_dump(), "resale_basis": "verified_appraisal"}
        )


def test_fixed_scenario_matches_independent_arithmetic(scenario: AnalysisInput) -> None:
    result = analyze(scenario)
    # 200k less 6% selling costs minus (100k bid + 10% premium + 12% interest + 26k).
    assert result["profit"] == {"p10": 40000, "p50": 40000, "p90": 40000}
    assert result["acquisition_cost"]["p50"] == 148000
    assert result["median_roi_pct"] == 27.03
    assert result["loss_probability_pct"] == 0
    assert result["maximum_bid"] == 107103.82
    assert sum(bin["count"] for bin in result["histogram"]) == 1000


def test_seed_reproducible_and_maximum_bid_enforces_all_gates(scenario: AnalysisInput) -> None:
    spec = scenario.model_copy(
        update={
            "resale": Range(low=140000, likely=200000, high=260000),
            "repairs": Range(low=1000, likely=15000, high=60000),
        }
    )
    result = analyze(spec)
    assert result == analyze(spec)
    bid = result["maximum_bid"]
    assert bid is not None
    assert analyze(spec.model_copy(update={"purchase_price": bid}))["current_bid_meets_targets"]
    assert not analyze(spec.model_copy(update={"purchase_price": bid + 0.02}))[
        "current_bid_meets_targets"
    ]
    assert analyze(spec.model_copy(update={"seed": 43}))["profit"] != result["profit"]
    json.dumps(result, allow_nan=False)


@given(st.floats(min_value=0, max_value=1000000, allow_nan=False))
@settings(max_examples=30, deadline=None)
def test_higher_cost_never_improves_bid_or_profit(extra: float) -> None:
    spec = AnalysisInput(
        purchase_price=100000,
        resale=Range(low=180000, likely=200000, high=240000),
        repairs=Range(low=0, likely=10000, high=25000),
        lien_reserve=0,
        closing_costs=5000,
        holding_months=6,
        monthly_holding=500,
        buyer_premium_pct=0,
        selling_cost_pct=6,
        annual_financing_pct=0,
        target_roi_pct=20,
        min_profit=20000,
        max_loss_probability_pct=10,
        iterations=1000,
    )
    before = analyze(spec)
    after = analyze(spec.model_copy(update={"lien_reserve": extra}))
    assert after["profit"]["p50"] <= before["profit"]["p50"]
    assert after["loss_probability_pct"] >= before["loss_probability_pct"]
    assert (after["maximum_bid"] or 0) <= before["maximum_bid"]


def test_no_feasible_bid_is_distinct_from_zero(scenario: AnalysisInput) -> None:
    result = analyze(scenario.model_copy(update={"lien_reserve": 1000000}))
    assert result["maximum_bid"] is None
    assert not result["feasible"]
    assert result["loss_probability_pct"] == 100


def test_zero_investment_does_not_serialize_nan_or_infinity(scenario: AnalysisInput) -> None:
    result = analyze(
        scenario.model_copy(
            update={
                "purchase_price": 0,
                "repairs": Range(low=0, likely=0, high=0),
                "lien_reserve": 0,
                "closing_costs": 0,
                "monthly_holding": 0,
            }
        )
    )
    assert result["median_roi_pct"] is None
    assert result["scenario_score"] is None
    assert result["current_bid_meets_targets"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "field,value",
    [
        ("purchase_price", -1),
        ("purchase_price", float("nan")),
        ("lien_reserve", float("inf")),
        ("iterations", 999),
        ("iterations", 25001),
        ("seed", -1),
        ("seed", 2**32),
        ("holding_months", 121),
        ("resale", {"low": 0, "likely": 1, "high": 2}),
        ("resale", {"low": 3, "likely": 1, "high": 2}),
        ("extra", 1),
    ],
)
def test_invalid_scenarios_rejected(scenario: AnalysisInput, field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        AnalysisInput.model_validate({**scenario.model_dump(), field: value})
