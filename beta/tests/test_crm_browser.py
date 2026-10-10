"""Real signup → database → owner CRM, including mobile and private-state cleanup."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_signup_crm_and_download(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Email address", exact=True).fill("crm-browser@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator("#workspace")).to_be_hidden()
        page.get_by_label("Full name", exact=True).fill("Fixture CRM Person")
        page.get_by_label("How will you use LandWolf?", exact=True).select_option("investing")
        page.get_by_label("Company (optional)", exact=True).fill("Fixture CRM Company")
        page.get_by_label("Phone (optional)", exact=True).fill("+1 555 010 1234")
        page.get_by_label("Job title (optional)", exact=True).fill("Principal")
        page.get_by_label("Industry (optional)", exact=True).select_option("real_estate")
        expect(page.locator("#signup-marketing")).not_to_be_checked()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        output = Path("test-results")
        output.mkdir(exist_ok=True)
        page.screenshot(
            path=str(output / f"crm-registration-{engine_name}-{width}.png"), full_page=True
        )
        page.locator("#auth-submit").click()
        expect(page.locator("#workspace")).to_be_visible()
        expect(page.locator("#crm-nav")).to_be_hidden()
        assert page.request.get(f"{origin}/api/admin/crm/contacts").status == 403
        page.get_by_role("button", name="Sign out", exact=True).click()
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.locator("#registration-profile")).to_be_hidden()
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator("#workspace")).to_be_visible()
        page.locator("#crm-nav").click()
        expect(page.locator("#workspace-title")).to_have_text("L91 LLC CRM")
        panel = page.locator("#crm-panel")
        expect(panel).to_contain_text("Fixture CRM Person")
        panel.get_by_label("Search name, email or company", exact=True).fill("Fixture CRM")
        panel.get_by_role("button", name="Filter contacts", exact=True).click()
        expect(panel.get_by_role("status")).to_contain_text("1 contacts")
        panel.get_by_role("button", name="Open contact", exact=True).click()
        expect(page.locator(".crm-detail")).to_contain_text("+1 555 010 1234")
        panel.get_by_label("Lifecycle stage", exact=True).select_option("qualified")
        panel.get_by_label("Tags (comma separated)", exact=True).fill("Priority, Land")
        panel.get_by_label("Follow-up date", exact=True).fill("2026-12-01")
        panel.get_by_role("button", name="Save contact", exact=True).click()
        expect(panel.get_by_role("status")).to_contain_text("Contact saved")
        panel.get_by_label("Add a follow-up note", exact=True).fill(
            "<img src=x onerror=alert(1)> Fixture note"
        )
        panel.get_by_role("button", name="Add note", exact=True).click()
        expect(page.locator(".crm-detail")).to_contain_text("Fixture note")
        assert panel.locator("img").count() == 0
        with page.expect_download() as download:
            panel.get_by_role("button", name="Export contacts CSV", exact=True).click()
        assert download.value.suggested_filename == "l91-llc-crm-contacts.csv"
        assert "Fixture CRM Person" in Path(download.value.path()).read_text()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(output / f"l91-crm-{engine_name}-{width}.png"), full_page=True)
        # Failed authorization after rendering must erase all previously loaded contacts.
        page.route(
            "**/api/admin/crm/contacts?*",
            lambda route: route.fulfill(
                status=403,
                content_type="application/json",
                body='{"detail":"Owner authorization required"}',
            ),
        )
        panel.get_by_role("button", name="Filter contacts", exact=True).click()
        expect(panel).to_be_empty()
        expect(page.locator("#crm-nav")).to_be_hidden()
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(panel).to_be_empty()
        assert not errors
        browser.close()
