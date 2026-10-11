from pathlib import Path

def test_support_email_is_in_footer_and_clickable():
    html = Path("app/static/index.html").read_text()
    assert "support.landwolf@gmail.com" in html
    assert 'href="mailto:support.landwolf@gmail.com"' in html
    assert '<footer class="site-footer">' in html
