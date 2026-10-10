"""Responsive simple/advanced investment journeys through the real isolated API."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 820, 1440])
def test_simple_deal_inputs_preserve_advanced_assumptions(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        errors = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: (
                requests.append(request.post_data_json)
                if request.url.endswith("/api/analysis") and request.method == "POST"
                else None
            ),
        )
        page.goto(origin)
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Full name", exact=True).fill("Investment regression fixture")
        page.get_by_label("How will you use LandWolf?", exact=True).select_option("research")
        page.get_by_label("Email address", exact=True).fill("investment-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        page.locator(".property-card").first.get_by_role("button", name="View property").click()
        form = page.locator("#analysis-form")
        advanced = page.locator("#analysis-advanced")
        toggle = advanced.locator("summary")

        def field(name):
            return form.locator(f'input[name="{name}"]')

        expect(form.locator('input[type="number"]:visible')).to_have_count(4)
        expect(advanced).not_to_have_attribute("open", "")
        expect(page.get_by_label("Expected sale price ($)", exact=True)).to_be_visible()
        field("resale_likely").fill("150000")
        field("repairs_likely").fill("5000")
        field("closing_costs").fill("3000")
        expect(field("resale_low")).to_have_value("142500")
        expect(field("resale_high")).to_have_value("180000")
        expect(field("repairs_low")).to_have_value("5000")
        expect(field("repairs_high")).to_have_value("5000")
        page.locator("#run-analysis").click()
        expect(page.locator("#analysis-results")).to_be_hidden()
        assert requests == []  # Zero-cost acknowledgement is still required.
        page.locator("#zero-cost-ack").check()
        page.locator("#run-analysis").click()
        expect(page.locator("#analysis-results")).to_be_visible()
        assert requests[-1]["resale"] == {"low": 142500, "likely": 150000, "high": 180000}
        assert requests[-1]["repairs"] == {"low": 5000, "likely": 5000, "high": 5000}
        assert requests[-1]["closing_costs"] == 3000

        Path("test-results").mkdir(exist_ok=True)
        form.scroll_into_view_if_needed()
        page.screenshot(path=f"test-results/investment-simple-{engine_name}-{width}.png")
        toggle.click()
        field("resale_low").fill("120000")
        field("repairs_high").fill("9000")
        field("selling_cost_pct").fill("6")
        field("holding_months").fill("6")
        field("seed").fill("4294967296")
        toggle.click()
        page.locator("#zero-cost-ack").check()
        count = len(requests)
        page.locator("#run-analysis").click()
        expect(advanced).to_have_attribute("open", "")
        assert len(requests) == count  # Invalid hidden input opens, never posts.
        field("seed").fill("4294967295")
        field("repairs_low").fill("7000")
        toggle.click()
        page.locator("#zero-cost-ack").check()
        page.locator("#run-analysis").click()
        expect(advanced).to_have_attribute("open", "")
        expect(page.locator("#analysis-error")).to_contain_text("Each range must be ordered")
        assert len(requests) == count
        field("repairs_low").fill("5000")
        toggle.click()
        field("resale_likely").fill("160000")
        field("repairs_likely").fill("6000")
        expect(field("resale_low")).to_have_value("120000")
        expect(field("resale_high")).to_have_value("192000")
        expect(field("repairs_low")).to_have_value("5000")
        expect(field("repairs_high")).to_have_value("9000")
        page.locator("#zero-cost-ack").check()
        page.locator("#run-analysis").click()
        expect(page.locator("#analysis-results")).to_be_visible()
        assert requests[-1]["resale"] == {"low": 120000, "likely": 160000, "high": 192000}
        assert requests[-1]["repairs"] == {"low": 5000, "likely": 6000, "high": 9000}
        assert requests[-1]["selling_cost_pct"] == 6
        assert requests[-1]["holding_months"] == 6
        assert requests[-1]["seed"] == 4294967295
        expect(form.locator('input[type="number"]:visible')).to_have_count(4)
        assert page.locator("#property-dialog").evaluate("el => el.scrollWidth <= el.clientWidth")
        toggle.click()
        page.screenshot(path=f"test-results/investment-advanced-{engine_name}-{width}.png")
        page.locator("#close-detail").click()
        page.locator(".property-card").first.get_by_role("button", name="View property").click()
        expect(form.locator('input[type="number"]:visible')).to_have_count(4)
        expect(field("selling_cost_pct")).to_have_value("6")
        expect(field("repairs_high")).to_have_value("9000")
        page.locator("#close-detail").click()
        page.get_by_role("button", name="Sign out", exact=True).click()
        page.locator("#login-tab").click()
        page.get_by_label("Email address", exact=True).fill("investment-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        page.locator(".property-card").first.get_by_role("button", name="View property").click()
        expect(field("resale_likely")).to_have_value("100000")
        expect(field("repairs_high")).to_have_value("0")
        expect(field("selling_cost_pct")).to_have_value("0")
        assert errors == []
        browser.close()
