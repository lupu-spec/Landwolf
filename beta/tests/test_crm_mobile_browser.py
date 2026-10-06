"""Contacts must open in view, not silently below a long mobile list."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 768, 1440])
def test_open_contact_moves_to_editor_and_recovers(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as p:
        browser = getattr(p, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        page.goto(origin)
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator("#workspace")).to_be_visible()
        csrf = page.request.get(origin + "/api/session").json()["csrf"]
        for i in range(30):
            response = page.request.post(
                origin + "/api/admin/crm/contacts",
                headers={"Origin": origin, "X-CSRF-Token": csrf, "X-LandWolf-Client": "web"},
                data={
                    "full_name": f"Mobile Fixture {i:02}",
                    "email": f"mobile-fixture-{i}@example.com",
                    "primary_use": "exploring",
                },
            )
            assert response.status == 201
        page.locator("#crm-nav").click()
        panel = page.locator("#crm-panel")
        expect(panel.locator(".crm-contact")).to_have_count(31)
        opener = panel.get_by_role("button", name="Open contact", exact=True).nth(2)
        card_name = opener.locator("..").locator("h3").inner_text()
        opener.click()
        detail = panel.locator(".crm-detail")
        heading = detail.get_by_role("heading", name=card_name, exact=True)
        expect(heading).to_be_focused()
        expect(heading).to_be_in_viewport()
        edit = detail.get_by_text("Edit contact profile", exact=True)
        expect(edit).to_be_in_viewport()
        edit.click()
        detail.get_by_label("Company", exact=True).fill("Mobile correction fixture")
        detail.get_by_label("Reason for profile change", exact=True).fill("Mobile regression check")
        detail.get_by_role("button", name="Save profile", exact=True).click()
        expect(panel.get_by_role("status")).to_contain_text("Profile saved")
        expect(detail).to_contain_text("Mobile correction fixture")
        expect(detail.get_by_role("heading", name=card_name, exact=True)).to_be_in_viewport()
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(path=f"test-results/mobile-contact-{engine_name}-{width}.png")
        detail.get_by_role("button", name="Back to contacts", exact=True).click()
        expect(detail).to_be_empty()
        expect(panel.locator(".crm-list button:focus")).to_be_in_viewport()
        pattern = "**/api/admin/crm/contacts/*"
        page.route(pattern, lambda route: route.fulfill(status=503, json={"detail": "Try again"}))
        opener.click()
        expect(detail.get_by_role("heading", name="Unable to open contact")).to_be_in_viewport()
        expect(detail.get_by_role("button", name="Retry opening contact")).to_be_visible()
        page.unroute(pattern)
        detail.get_by_role("button", name="Retry opening contact").click()
        expect(detail.get_by_role("heading", name=card_name, exact=True)).to_be_in_viewport()
        expect(detail.get_by_text("Edit contact profile", exact=True)).to_be_in_viewport()
        browser.close()
