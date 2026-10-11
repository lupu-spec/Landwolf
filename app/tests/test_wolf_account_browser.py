"""Chat → explicit review → own CRM record; no destructive or cross-account action."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 768, 1440])
def test_chat_profile_review_reset_help_and_privacy(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as p:
        browser = getattr(p, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        panel = page.locator("#wolf-chat-panel")
        log = page.locator("#wolf-chat-log")

        def ask(text):
            panel.get_by_label("Ask how to use LandWolf", exact=True).fill(text)
            panel.get_by_role("button", name="Ask the wolves", exact=True).click()

        def collapse():
            panel.get_by_role("button", name="Collapse Romulus and Remus chat", exact=True).click()

        page.locator("#wolf-chat-launcher").click()
        ask("Update my profile")
        log.get_by_role("button", name="Review my profile", exact=True).last.click()
        expect(panel.get_by_role("region", name="Account help")).to_contain_text("Sign in to edit")
        ask("Remus reset my password")
        log.get_by_role("button", name="Request password reset", exact=True).last.click()
        card = panel.get_by_role("region", name="Account help")
        card.get_by_label("Reset email address", exact=True).fill("wolf-account@example.com")
        card.get_by_role("button", name="Send password reset email", exact=True).click()
        expect(card.get_by_role("status")).to_contain_text("not configured")
        collapse()

        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Full name", exact=True).fill("Wolf Profile Fixture")
        page.get_by_label("How will you use LandWolf?", exact=True).select_option("research")
        page.get_by_label("Email address", exact=True).fill("wolf-account@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator("#workspace")).to_be_visible()
        page.locator("#wolf-chat-launcher").click()
        ask("Romulus update my phone number")
        log.get_by_role("button", name="Review my profile", exact=True).last.click()
        expect(card.get_by_label("Full name", exact=True)).to_have_value("Wolf Profile Fixture")
        card.get_by_label("Company", exact=True).fill("Private Chat Fixture Company")
        card.get_by_label("Phone", exact=True).fill("+1 212 555 0100")
        card.get_by_role("button", name="Review my changes", exact=True).click()
        expect(card.locator(".wolf-account-review")).to_contain_text("Private Chat Fixture Company")
        assert page.request.get(origin + "/api/account/profile").json()["profile"]["company"] == ""
        card.get_by_role("button", name="Keep editing", exact=True).click()
        card.get_by_label("Job title", exact=True).fill("Fixture Investor")
        card.get_by_role("button", name="Review my changes", exact=True).click()
        card.get_by_role("button", name="Save my changes", exact=True).click()
        expect(card.get_by_role("status")).to_contain_text("profile is saved")
        stored = page.request.get(origin + "/api/account/profile").json()["profile"]
        assert stored["company"] == "Private Chat Fixture Company"
        assert stored["phone"] == "+1 212 555 0100"
        assert stored["job_title"] == "Fixture Investor"
        assert page.request.get(origin + "/api/admin/crm/contacts").status == 403

        ask("Remus reset my password")
        log.get_by_role("button", name="Request password reset", exact=True).last.click()
        expect(card.get_by_label("Reset email address", exact=True)).to_have_value(
            "wolf-account@example.com"
        )
        expect(card.get_by_label("Reset email address", exact=True)).to_have_attribute(
            "readonly", ""
        )
        expect(
            card.get_by_role("button", name="Send password reset email", exact=True)
        ).to_be_disabled()
        ask("Delete my CRM data")
        expect(log.locator(".wolf-turn").last).to_contain_text("cannot delete")
        assert log.locator(".wolf-turn").last.get_by_role("button").count() == 0
        assert page.request.get(origin + "/api/account/profile").json()["profile"] == stored
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert card.evaluate("el => el.scrollWidth <= el.clientWidth")
        assert page.evaluate("localStorage.length === 0 && sessionStorage.length === 0")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(path=f"test-results/wolf-account-{engine_name}-{width}.png")
        collapse()
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.locator("#auth-submit")).to_be_visible()
        expect(log).not_to_contain_text("Private Chat Fixture Company")
        expect(panel.locator(".wolf-account-card")).to_have_count(0)
        assert not errors
        browser.close()
