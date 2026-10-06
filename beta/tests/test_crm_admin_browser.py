"""Owner manages a pre-registration trial and then administers its registered account."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 768, 1440])
def test_owner_account_administration(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as p:
        browser = getattr(p, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(origin)
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        page.locator("#crm-nav").click()
        panel = page.locator("#crm-panel")
        panel.get_by_text("Add contact", exact=True).click()
        panel.get_by_label("Contact full name", exact=True).fill("Managed Browser Fixture")
        panel.get_by_label("Contact email", exact=True).fill("managed-browser@example.com")
        panel.get_by_role("button", name="Create contact", exact=True).click()
        detail = page.locator(".crm-detail")
        expect(detail).to_contain_text("Registration pending")
        detail.get_by_label("Reason for account action", exact=True).fill("Fixture trial request")
        detail.get_by_label("Access duration (days)", exact=True).fill("14")
        detail.get_by_role("button", name="Reserve trial", exact=True).click()
        expect(panel.get_by_role("status")).to_contain_text("Trial reserved")
        expect(detail).to_contain_text("trial · reserved · 14 days")
        # The real signup form must attach the manual CRM row, not fail or duplicate it.
        customer = browser.new_page()
        customer.goto(origin)
        customer.get_by_role("button", name="Create account", exact=True).click()
        customer.get_by_label("Email address", exact=True).fill("managed-browser@example.com")
        customer.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        customer.get_by_label("Full name", exact=True).fill("Managed Browser Fixture")
        customer.get_by_label("How will you use LandWolf?", exact=True).select_option("exploring")
        customer.locator("#auth-submit").click()
        expect(customer.locator("#workspace")).to_be_visible()
        assert customer.request.get(origin + "/api/admin/crm/contacts").status == 403
        panel.get_by_label("Search name, email or company", exact=True).fill(
            "managed-browser@example.com"
        )
        panel.get_by_role("button", name="Filter contacts", exact=True).click()
        expect(panel.get_by_role("status")).to_contain_text("1 contacts")
        panel.get_by_role("button", name="Open contact", exact=True).click()
        expect(detail.get_by_role("button", name="Activate trial", exact=True)).to_be_visible()
        detail.get_by_label("Reason for account action", exact=True).fill(
            "Owner reviewed fixture identity"
        )
        detail.get_by_label("Access duration (days)", exact=True).fill("30")
        detail.get_by_role("button", name="Activate trial", exact=True).click()
        expect(panel.get_by_role("status")).to_contain_text("Trial activated")
        expect(detail).to_contain_text("trial · activated · 30 days")
        detail.get_by_text("Edit contact profile", exact=True).click()
        detail.get_by_label("Company", exact=True).fill("Updated Fixture Company")
        detail.get_by_label("Reason for profile change", exact=True).fill(
            "Fixture profile correction"
        )
        detail.get_by_role("button", name="Save profile", exact=True).click()
        expect(panel.get_by_role("status")).to_contain_text("Profile saved")
        expect(detail).to_contain_text("Updated Fixture Company")
        detail.get_by_label("Reason for account action", exact=True).fill("Fixture suspension test")
        detail.get_by_role("button", name="Suspend account", exact=True).click()
        expect(detail).to_contain_text("Suspended")
        customer.reload()
        expect(customer.locator("#auth-submit")).to_be_visible()
        detail.get_by_label("Reason for account action", exact=True).fill("Restore fixture account")
        detail.get_by_role("button", name="Restore account", exact=True).click()
        expect(detail.get_by_role("button", name="Suspend account", exact=True)).to_be_visible()
        expect(
            detail.get_by_role("button", name="Send password reset", exact=True)
        ).to_be_disabled()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(path=f"test-results/crm-admin-{engine_name}-{width}.png", full_page=True)
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(panel).to_be_empty()
        assert not errors
        browser.close()
