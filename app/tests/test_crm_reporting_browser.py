"""Real browser filters, customer counts, test hiding, CSV and private-state cleanup."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_customer_statistics_and_smoke_filter(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950}, accept_downloads=True)
        page.goto(origin)
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator("#workspace")).to_be_visible()
        csrf = page.request.get(origin + "/api/session").json()["csrf"]
        headers = {"Origin": origin, "X-CSRF-Token": csrf, "X-LandWolf-Client": "web"}
        response = page.request.post(
            origin + "/api/admin/crm/contacts",
            headers=headers,
            data={
                "email": "production-smoke-browser@example.com",
                "full_name": "Hidden QA Contact",
                "primary_use": "research",
            },
        )
        assert response.status == 201
        # Register an ordinary customer in an isolated API context, not the owner session.
        context = playwright.request.new_context(base_url=origin)
        result = context.post(
            "/api/auth/register",
            headers={"Origin": origin, "X-LandWolf-Client": "web"},
            data={
                "email": "reporting-user@example.com",
                "password": "Test-only passphrase 847!",
                "profile": {"full_name": "Reporting Customer", "primary_use": "research"},
            },
        )
        assert result.status == 201
        context.dispose()
        data = page.request.get(origin + "/api/admin/crm/contacts?account_category=user").json()
        contact = next(c for c in data["contacts"] if c["email"] == "reporting-user@example.com")
        assert (
            page.request.post(
                origin + f"/api/admin/crm/contacts/{contact['id']}/access",
                headers=headers,
                data={
                    "revision": contact["revision"],
                    "reason": "Synthetic reporting test",
                    "action": "trial",
                    "days": 30,
                },
            ).status
            == 200
        )
        page.locator("#crm-nav").click()
        panel = page.locator("#crm-panel")
        expect(panel).to_contain_text("Reporting Customer")
        expect(panel).not_to_contain_text("Hidden QA Contact")
        expect(panel.get_by_role("button", name="Show trial users: 1", exact=True)).to_be_visible()
        panel.get_by_role("button", name="Show trial users: 1", exact=True).click()
        expect(panel.locator(".crm-contact")).to_have_count(1)
        expect(panel.get_by_label("Account category", exact=True)).to_have_value("user")
        expect(panel.get_by_label("Membership", exact=True)).to_have_value("trial")
        with page.expect_download() as download:
            panel.get_by_role("button", name="Export contacts CSV", exact=True).click()
        csv = Path(download.value.path()).read_text()
        assert "reporting-user@example.com" in csv and "production-smoke" not in csv
        assert "account_category" in csv and "membership" in csv
        panel.get_by_label("Account category", exact=True).select_option("smoke_test")
        panel.get_by_label("Membership", exact=True).select_option("")
        panel.get_by_role("button", name="Filter contacts", exact=True).click()
        expect(panel.locator(".crm-contact")).to_have_count(1)
        expect(panel).to_contain_text("Hidden QA Contact")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(
            path=f"test-results/crm-reporting-{engine_name}-{width}.png", full_page=True
        )
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(panel).to_be_empty()
        browser.close()
