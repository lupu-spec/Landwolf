"""Browser → authenticated API → isolated database source/state filter regressions."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["commercial_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_commercial_state_source_filters_details_and_themes(browser_server, engine, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        page.goto(origin)
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card")).to_have_count(4)
        state, category, source = (
            page.locator("#state"),
            page.locator("#category"),
            page.locator("#source-filter"),
        )
        state.select_option("TX")
        category.select_option("seller_listing")
        expect(source.locator("option[value^='craigslist_']")).to_have_count(1)
        source.select_option("zillow_tx")
        page.locator("#search-submit").click()
        expect(page.locator(".property-card")).to_have_count(1)
        expect(page.locator(".card-source")).to_have_text("Zillow")
        page.locator(".card-detail").click()
        expect(page.locator("#property-dialog")).to_contain_text("not independently verified")
        expect(page.locator("#property-dialog a[href*='zillow.com']").first).to_have_attribute(
            "rel", "noopener noreferrer"
        )
        page.locator("#close-detail").click()
        source.select_option("compass_tx")
        page.locator("#search-submit").click()
        expect(page.locator(".card-source")).to_have_text("Compass")
        source.select_option("craigslist_tx")
        state.select_option("CA")
        expect(source).to_have_value("craigslist_ca")
        page.locator("#search-submit").click()
        expect(page.locator(".property-card")).to_have_count(1)
        expect(page.locator(".card-source")).to_have_text("Craigslist")
        expect(page.locator("#state")).to_have_value("CA")
        Path("test-results").mkdir(exist_ok=True)
        for mode in ("light", "dark", "system"):
            page.get_by_role("combobox", name="Appearance", exact=True).select_option(mode)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(
                path=f"test-results/commercial-{engine}-{width}-{mode}.png", full_page=True
            )
        page.locator("#location").fill("no-synthetic-listing-matches-this-filter")
        page.locator("#search-submit").click()
        expect(page.locator("#empty-state")).to_be_visible()
        page.locator("#reset-filters").click()
        expect(state).to_have_value("US")
        expect(source).to_have_value("")
        expect(page.locator(".property-card")).to_have_count(4)
        browser.close()


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_default_publisher_links_follow_state_without_imports(browser_server, engine, width):
    from landwolf.commercial import PAGE_GROUPS

    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        page.goto(origin)
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        state = page.locator("#state")
        source = page.locator("#source-filter")
        state.select_option("TX")
        page.locator("#category").select_option("seller_listing")
        source.select_option("craigslist_tx")
        state.select_option("CA")
        expect(source).to_have_value("craigslist_ca")
        panel = page.locator("#publisher-searches")
        expect(panel).to_be_visible()
        panel.locator("summary").focus()
        page.keyboard.press("Enter")
        expect(panel.locator("a")).to_have_count(len(PAGE_GROUPS["craigslist_ca"]))
        expect(panel).to_contain_text("Automatic import is not enabled")
        assert [a.get_attribute("href") for a in panel.locator("a").all()] == list(
            PAGE_GROUPS["craigslist_ca"]
        )
        assert all(
            a.get_attribute("rel") == "noopener noreferrer" for a in panel.locator("a").all()
        )
        for mode in ("light", "dark", "system"):
            page.get_by_role("combobox", name="Appearance", exact=True).select_option(mode)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(
                path=f"test-results/publisher-links-{engine}-{width}-{mode}.png", full_page=True
            )
        page.locator("#search-submit").click()
        expect(page.locator("#empty-state")).to_be_visible()
        expect(page.locator(".property-card")).to_have_count(0)
        state.select_option("TX")
        source.select_option("zillow_tx")
        expect(panel.locator("a")).to_have_attribute("href", PAGE_GROUPS["zillow_tx"][0])
        source.select_option("compass_tx")
        expect(panel.locator("a")).to_have_attribute("href", PAGE_GROUPS["compass_tx"][0])
        page.locator("#reset-filters").click()
        expect(panel).to_be_hidden()
        expect(panel.locator("a")).to_have_count(0)
        browser.close()
