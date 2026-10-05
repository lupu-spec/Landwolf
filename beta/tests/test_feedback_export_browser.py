"""Owner CSV download and private-list lifecycle through real browser requests."""

import csv
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_feedback_users_and_csv_are_private(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950}, accept_downloads=True)
        errors = []
        downloads = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("download", lambda download: downloads.append(download))
        page.goto(origin)

        def login(email):
            page.get_by_label("Email address", exact=True).fill(email)
            page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
            page.locator("#auth-submit").click()
            expect(page.locator("#workspace")).to_be_visible()

        def open_feedback():
            page.locator('#main-nav [data-nav="feedback"]').click()
            expect(page.locator("#feedback-content")).to_be_visible()

        page.get_by_role("button", name="Create account", exact=True).click()
        login("csv-customer@example.com")
        open_feedback()
        admin = page.locator("#feedback-admin")
        expect(admin).to_be_hidden()
        expect(admin).to_be_empty()
        assert page.request.get(f"{origin}/api/admin/feedback/users.csv").status == 403
        page.get_by_role("button", name="Sign out", exact=True).click()
        page.get_by_role("button", name="Sign in", exact=True).click()
        login("owner-fixture@example.com")
        open_feedback()
        expect(admin).to_contain_text("csv-customer@example.com")
        export = admin.get_by_role("button", name="Export users CSV", exact=True)
        page.route(
            "**/api/admin/feedback/users.csv",
            lambda route: route.fulfill(
                status=503, content_type="application/json", body='{"detail":"Fixture unavailable"}'
            ),
        )
        export.click()
        expect(admin.get_by_role("status")).to_contain_text("Unable to export users")
        assert len(downloads) == 0
        expect(export).to_be_enabled()
        page.unroute("**/api/admin/feedback/users.csv")
        with page.expect_download() as event:
            export.click()
        download = event.value
        assert re.fullmatch(r"landwolf-users-\d{4}-\d{2}-\d{2}\.csv", download.suggested_filename)
        with Path(download.path()).open(encoding="utf-8-sig", newline="") as stream:
            exported = list(csv.DictReader(stream))
        assert {row["Email"] for row in exported} == {
            "csv-customer@example.com",
            "owner-fixture@example.com",
        }
        expect(admin.get_by_role("status")).to_contain_text("CSV download started")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        output = Path("test-results")
        output.mkdir(exist_ok=True)
        page.screenshot(
            path=str(output / f"feedback-export-{engine_name}-{width}.png"), full_page=True
        )

        # A failed authority refresh must erase previously rendered account details.
        page.route(
            "**/api/feedback",
            lambda route: route.fulfill(
                status=503, content_type="application/json", body='{"detail":"Fixture unavailable"}'
            ),
        )
        page.get_by_role("button", name="Refresh status", exact=True).click()
        expect(admin).to_be_hidden()
        expect(admin).to_be_empty()
        page.unroute("**/api/feedback")
        open_feedback()
        expect(export).to_be_visible()

        # Simulate authorization loss after the list loaded: no download or stale identifiers.
        page.route(
            "**/api/admin/feedback/users.csv",
            lambda route: route.fulfill(
                status=403,
                content_type="application/json",
                body='{"detail":"Owner authorization required"}',
            ),
        )
        export.click()
        expect(admin).to_be_hidden()
        expect(admin).to_be_empty()
        assert len(downloads) == 1
        page.unroute("**/api/admin/feedback/users.csv")
        open_feedback()
        expect(export).to_be_visible()
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(admin).to_be_empty()
        assert page.request.get(f"{origin}/api/admin/feedback/users.csv").status == 401
        login("csv-customer@example.com")
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        open_feedback()
        expect(admin).to_be_hidden()
        expect(admin).to_be_empty()
        assert not any("/api/admin/" in url for url in requests)
        assert not errors
        browser.close()
