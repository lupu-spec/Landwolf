"""Real-browser LupuSpec public intake on both desktop and mobile."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_lupuspec_customer_portal(browser_server, engine, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(origin + "/lupuspec")
        assert response and response.status == 200
        expect(page.get_by_role("heading", name="LupuSpec", exact=True)).to_be_visible()
        assert page.locator('input[name="capability"]').count() == 4
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_text("Fabrication", exact=True).click()
        page.get_by_label("Project title").fill("Synthetic 3D printed enclosure")
        page.get_by_label("Concept and requirements").fill(
            "Create a 3D printable prototype enclosure for an electronics project."
        )
        page.get_by_label("Full name").fill("Browser Synthetic Customer")
        page.get_by_label("Email", exact=True).fill("lupuspec-browser@example.com")
        page.get_by_label("I authorize L91 LLC to contact me about this project.").check()
        with page.expect_response("**/api/lupuspec/requests") as submitted:
            page.get_by_role("button", name="Submit project request").click()
        assert submitted.value.status == 201
        expect(page.locator("#submission-status")).to_contain_text("Request received. Reference:")
        assert page.request.get(origin + "/api/admin/lupuspec/requests").status == 401
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(
            path="test-results/lupuspec-" + engine + "-" + str(width) + ".png",
            full_page=True,
        )
        assert not errors
        browser.close()
