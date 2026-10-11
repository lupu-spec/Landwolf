from pathlib import Path

def test_footer_uses_dynamic_calendar_year():
    html = Path("app/static/index.html").read_text()
    js = Path("app/static/app.js").read_text()
    assert 'id="copyright-year"' in html
    assert "L91 LLC" in html
    assert "new Date().getFullYear()" in js
