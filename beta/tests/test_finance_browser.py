"""Responsive owner finance and failure recovery using disposable synthetic accounts."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["finance_owner"], indirect=True)
@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 834, 1440])
def test_owner_finance_responsive_and_recovery(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card").first).to_be_visible()
        page.locator("#finance-nav").click()
        panel = page.locator("#finance-panel")
        expect(
            panel.get_by_role("heading", name="Next three months · scenario planning")
        ).to_be_visible()
        expect(panel.locator("svg[role=img]")).to_have_count(3)
        expect(panel.get_by_role("table")).to_have_count(3)
        expect(panel.get_by_role("button", name="Refresh Stripe")).to_be_disabled()
        expect(panel.locator(".finance-card").first).to_contain_text("$145.00")
        expect(panel.locator(".finance-card").last).to_contain_text("$145.00")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        panel.get_by_label("Forecast scenario").select_option("growth")
        panel.get_by_label("Expense amount dollars").fill("7.01")
        panel.get_by_label("Expense business allocation %").fill("50")
        if width < 1100:
            assert (
                panel.get_by_label("Expense amount dollars").evaluate(
                    "el => getComputedStyle(el).fontSize"
                )
                == "16px"
            )
        page.route(
            "**/api/admin/finance/expenses",
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"Synthetic retry failure"}',
            ),
        )
        panel.get_by_role("button", name="Record business expense").click()
        expect(panel.get_by_role("status")).to_have_text("Synthetic retry failure")
        expect(panel.get_by_label("Expense amount dollars")).to_have_value("7.01")
        expect(panel.get_by_label("Expense business allocation %")).to_have_value("50")
        page.unroute("**/api/admin/finance/expenses")
        panel.get_by_role("button", name="Record business expense").click()
        expect(panel.locator(".finance-card").nth(1)).to_contain_text("$3.51")
        # Retry a duplicate without discarding the owner's values.
        panel.get_by_label("Expense amount dollars").fill("7.01")
        panel.get_by_label("Expense business allocation %").fill("50")
        panel.get_by_role("button", name="Record business expense").click()
        expect(panel.get_by_role("status")).to_contain_text("Possible duplicate")
        expect(panel.get_by_label("Expense amount dollars")).to_have_value("7.01")
        panel.get_by_text("Preview an Amex CSV import", exact=True).click()
        panel.get_by_label("Amex CSV file").set_input_files(
            {
                "name": "synthetic-business.csv",
                "mimeType": "text/csv",
                "buffer": b"Date,Description,Amount\n2026-09-01,Spaceship,12.00\n"
                b"2026-09-02,Personal sensitive charge,22.00\n",
            }
        )
        panel.get_by_role("button", name="Preview selected expenses").click()
        expect(panel.get_by_role("button", name="Confirm business expense import")).to_be_visible()
        expect(panel).not_to_contain_text("Personal sensitive charge")
        panel.get_by_role("button", name="Confirm business expense import").click()
        expect(panel.get_by_role("button", name="Confirm business expense import")).to_be_hidden()
        # The import is durable; it is not a speculative cost inferred from a card vendor name.
        panel.get_by_text("Recorded expenses (2) · current six-month period", exact=True).click()
        expect(panel).to_contain_text("spaceship · $12.00")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(
            path=f"test-results/finance-synthetic-{engine_name}-{width}.png", full_page=True
        )
        page.locator("#signout").click()
        expect(page.locator("#auth-view")).to_be_visible()
        expect(page.locator("#finance-nav")).to_be_hidden()
        assert panel.text_content() == ""
        assert not errors
        browser.close()
