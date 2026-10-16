"""Owner-only source disclosures, age boundaries, keyboard use and preserved details."""

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_source_list_disclosure_and_live_age(browser_server, engine, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        now = int(time.time())
        page.clock.install(time=datetime.fromtimestamp(now, UTC))
        assert abs(page.evaluate("Date.now()") / 1000 - now) < 5

        def source_response(route):
            response = route.fetch()
            assert response.status == 200
            body = response.json()
            template = body["sources"][0]
            body["sources"] = [
                {
                    **template,
                    "id": f"age-{index}",
                    "name": name,
                    "automated": automated,
                    "last_success": stamp,
                    "last_attempt": now,
                    "message": "Latest attempt failed; retained last successful snapshot.",
                    "status": "failed",
                    "history": [],
                }
                for index, (name, automated, stamp) in enumerate(
                    [
                        ("Fresh snapshot", True, now - 23 * 3600),
                        ("Aging snapshot", True, now - 25 * 3600),
                        ("Old snapshot", True, now - 36 * 3600),
                        ("No snapshot", True, None),
                        ("Directory only", False, None),
                        ("Boundary snapshot", True, now - 24 * 3600 + 30),
                        ("<img src=x onerror=alert(1)>", True, now),
                    ]
                )
            ]
            route.fulfill(response=response, json=body)

        page.route("**/api/sources", source_response)
        page.goto(origin)
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card").first).to_be_visible()
        page.get_by_role("button", name="Data coverage", exact=True).click()
        rows = page.locator("#source-cards .source-row")
        expect(rows).to_have_count(7)
        for index, color in enumerate(
            ["green", "yellow", "red", "red", "neutral", "green", "green"]
        ):
            expect(rows.nth(index).locator(".source-health")).to_have_attribute(
                "data-health", color
            )
        expect(page.locator("#source-cards img")).to_have_count(0)
        expect(rows.nth(0).locator(".source-row-detail")).to_be_hidden()
        summary = rows.nth(0).locator("summary").first
        summary.focus()
        page.keyboard.press("Enter")
        expect(rows.nth(0).locator(".source-row-detail")).to_be_visible()
        expect(rows.nth(0)).to_contain_text("Latest attempt failed")
        expect(rows.nth(0).get_by_role("link")).to_have_attribute("rel", "noopener noreferrer")
        page.clock.fast_forward(60_000)
        expect(rows.nth(5).locator(".source-health")).to_have_attribute("data-health", "yellow")
        expect(rows.nth(0).locator(".source-row-detail")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(path=f"test-results/source-list-{engine}-{width}.png", full_page=True)
        page.keyboard.press("Enter")
        expect(rows.nth(0).locator(".source-row-detail")).to_be_hidden()
        page.add_style_tag(content="html { font-size: 200% !important; }")
        name_box = rows.nth(0).locator(".source-row-name").bounding_box()
        assert name_box is not None and name_box["width"] > 40
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=f"test-results/source-list-zoom-{engine}-{width}.png", full_page=True)
        page.get_by_label("Coverage state", exact=True).select_option("HI")
        # These synthetic sources retain the first real fixture source's state coverage.
        expect(page.locator("#source-cards")).to_contain_text("No sources match these filters.")
        browser.close()
