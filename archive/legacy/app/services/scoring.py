def opportunity_score(
    acquisition_discount,
    risk_adjusted_equity,
    roi_irr,
    distress,
    property_development,
    liquidity,
    rental,
    competition,
    data_confidence,
):
    # Inputs are normalized 0..1; weights total 100.
    weights = {
        "acquisition_discount": 20,
        "risk_adjusted_equity": 20,
        "roi_irr": 15,
        "distress": 10,
        "property_development": 10,
        "liquidity": 5,
        "rental": 5,
        "competition": 5,
        "data_confidence": 10,
    }
    values = locals()
    return round(sum(weights[k] * max(0, min(1, float(values[k]))) for k in weights), 2)
