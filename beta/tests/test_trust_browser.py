"""Chromium and WebKit journeys through real UI/API/database at phone and desktop sizes."""

import json
import os
import time
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [320, 390, 768, 1440])
@pytest.mark.parametrize("browser_server", ["research"], indirect=True)
def test_trust_summary_evidence_and_responsive_navigation(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        engine = getattr(playwright, engine_name)
        options = {"args": ["--no-sandbox", "--disable-gpu"]} if engine_name == "chromium" else {}
        if engine_name == "chromium" and os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
            options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"]
        browser = engine.launch(**options)
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        page.get_by_role("button", name="Forgot password?", exact=True).click()
        expect(page.locator("#account-dialog")).to_be_visible()
        page.get_by_label("Account email address", exact=True).fill("fixture@example.com")
        page.get_by_role("button", name="Request reset email", exact=True).click()
        expect(page.locator("#account-action-message")).to_contain_text("not configured")
        assert page.locator("#account-dialog").evaluate("el => el.scrollWidth <= el.clientWidth")
        page.locator("#close-account-action").click()
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Email address", exact=True).fill(
            f"trust-{engine_name}-{width}@example.com"
        )
        page.get_by_label("Password", exact=True).fill("Synthetic browser passphrase 941!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card")).to_have_count(2)
        expect(page.locator(".evidence-badge").first).to_have_text("Parcel match needs review")
        if width <= 800:
            expect(page.get_by_role("button", name="List", exact=True)).to_have_attribute(
                "aria-pressed", "true"
            )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(
            path=f"test-results/trust-explore-{engine_name}-{width}.png", full_page=True
        )
        page.locator(".property-card").first.get_by_role("button", name="View property").click()
        expect(page.locator("#detail-content .trust-panel")).to_contain_text(
            "Parcel identity unresolved"
        )
        page.locator(".evidence-details summary").click()
        expect(page.locator(".evidence-list")).to_be_visible()
        assert page.locator("#property-dialog").evaluate("el => el.scrollWidth <= el.clientWidth")
        page.locator("#close-detail").click()
        page.locator(".property-card").first.get_by_role(
            "button", name="Research property", exact=True
        ).click()
        expect(page.locator(".research-summary")).to_be_visible()
        expect(page.locator(".research-source")).to_have_count(5)
        expect(page.locator(".research-summary")).to_contain_text("not established")
        page.locator(".research-evidence summary").first.click()
        expect(page.locator(".research-section").first).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(
            path=f"test-results/trust-research-{engine_name}-{width}.png", full_page=True
        )
        page.get_by_role("button", name="Data coverage", exact=True).click()
        page.locator(".beta-framework summary").click()
        expect(page.locator(".roadmap-item")).to_have_count(4)
        expect(page.locator("#beta-roadmap")).to_contain_text("data sharing are disabled")
        page.get_by_label("Coverage state", exact=True).select_option("MN")
        expect(page.locator("#source-cards")).to_contain_text(
            "Minnesota Department of Transportation"
        )
        page.locator("#source-cards .source-history summary").first.click()
        expect(page.locator("#source-cards")).to_contain_text("No refresh history")
        page.locator(".county-coverage summary").click()
        expect(page.locator("#county-coverage")).to_contain_text("No county records")
        page.screenshot(
            path=f"test-results/trust-coverage-{engine_name}-{width}.png", full_page=True
        )
        page.add_style_tag(content="html { font-size: 200% !important; }")
        page.screenshot(path=f"test-results/trust-zoom-{engine_name}-{width}.png", full_page=True)
        overflow = page.evaluate("""() => Array.from(document.querySelectorAll('body *'))
          .filter(el => el.getBoundingClientRect().width > 0 &&
                        el.getBoundingClientRect().right > innerWidth)
          .map(el => ({tag:el.tagName, id:el.id, css:el.className,
                      right:el.getBoundingClientRect().right})).slice(0,20)""")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), overflow
        assert page.locator("#main-nav button").first.evaluate(
            "el => parseFloat(getComputedStyle(el).fontSize) >= 28"
        )
        assert errors == []
        context.close()
        browser.close()


@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("browser_server", ["mail"], indirect=True)
def test_account_email_and_recovery_journey(browser_server, engine_name, tmp_path):
    """Only delivery is captured locally; browser, token consumption and sessions are real."""
    origin, _ = browser_server
    mailbox = tmp_path / "mailbox.json"

    def received(purpose):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if mailbox.exists():
                data = json.loads(mailbox.read_text())
                if data["purpose"] == purpose:
                    return data["token"]
            time.sleep(0.05)
        raise AssertionError("Test transport did not capture requested account email")

    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(origin)
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Email address", exact=True).fill("mail-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Synthetic first passphrase 835!")
        page.locator("#auth-submit").click()
        page.locator("#verify-email").click()
        token = received("verify")
        page.goto("about:blank")
        page.goto(f"{origin}/#action=verify&token={token}")
        expect(page.locator("#account-dialog")).to_be_visible()
        assert page.evaluate("location.hash") == ""
        page.get_by_role("button", name="Verify email", exact=True).click()
        expect(page.locator("#account-action-message")).to_contain_text("verified")
        page.locator("#close-account-action").click()
        page.reload()
        expect(page.locator("#email-status")).to_have_text("Email verified")
        page.get_by_role("button", name="Sign out", exact=True).click()
        page.get_by_role("button", name="Forgot password?", exact=True).click()
        page.get_by_label("Account email address", exact=True).fill("mail-fixture@example.com")
        page.get_by_role("button", name="Request reset email", exact=True).click()
        expect(page.locator("#account-action-message")).to_contain_text(
            "If the account is eligible"
        )
        token = received("reset")
        page.goto("about:blank")
        page.goto(f"{origin}/#action=reset&token={token}")
        expect(page.locator("#account-dialog")).to_be_visible()
        assert page.evaluate("location.hash") == ""
        page.get_by_label("New password (12–128 characters)", exact=True).fill(
            "Synthetic second passphrase 953!"
        )
        page.get_by_role("button", name="Update password", exact=True).click()
        expect(page.locator("#account-action-message")).to_contain_text("All sessions signed out")
        page.locator("#close-account-action").click()
        page.get_by_label("Email address", exact=True).fill("mail-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Synthetic second passphrase 953!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card")).to_have_count(2)
        assert page.evaluate("Object.keys(localStorage).length") == 0
        browser.close()
