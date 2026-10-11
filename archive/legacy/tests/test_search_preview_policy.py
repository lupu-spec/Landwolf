from pathlib import Path

def test_preview_is_login_gated_but_not_subscription_gated():
    text = Path("app/api/search.py").read_text().lower()
    preview = text.split('@router.post("/preview"',1)[1].split('@router.post(""',1)[0]
    assert "user=depends(current_user)" in preview
    assert "require_subscription(user)" not in preview
    for phrase in ["address", "parcel id", "owner information", "coordinates", "individual valuation"]:
        assert phrase in preview

def test_full_search_remains_subscription_gated():
    text = Path("app/api/search.py").read_text().lower()
    assert "require_subscription(user)" in text.split('@router.post(""',1)[1]

def test_frontend_uses_preview_for_unpaid_accounts():
    text = Path("app/static/app.js").read_text().lower()
    assert "/api/search/preview" in text
    assert "renderpreview" in text
    assert "opportunity preview" in text
