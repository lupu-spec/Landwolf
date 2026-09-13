from pathlib import Path
def test_value_copy_is_clear_and_non_identifying():
    js=Path("app/static/app.js").read_text().lower()
    api=Path("app/api/search.py").read_text().lower()
    html=Path("app/static/index.html").read_text().lower()
    for phrase in ["opportunity preview","opportunity landscape","without identifying individual properties"]:
        assert phrase in js
    for phrase in ["property-level intelligence","due-diligence data","risk context","valuation support","acquisition analysis"]:
        assert phrase in api
    assert "turn signals into actionable property research" in html
