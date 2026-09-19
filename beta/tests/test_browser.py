"""Real Chromium → HTTP → FastAPI → fresh database journeys.

Default CI data is explicitly synthetic. LANDWOLF_E2E_LIVE=1 instead copies only
listing/source records from a successful local live sync, never existing accounts.
"""

import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from conftest import seed, seed_national
from playwright.sync_api import Route, expect, sync_playwright
from sqlalchemy import select

from landwolf.db import Listing, SourceState, database, initialize

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["research"], indirect=True)
def test_saved_locations_and_manual_properties_survive_reload(
    browser_server: tuple[str, int],
) -> None:
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
            args=["--no-sandbox", "--disable-gpu"],
        )
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors: list[str] = []
        research_requests: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: (
                research_requests.append(request.method)
                if request.url.endswith("/api/research")
                else None
            ),
        )
        page.goto(origin)
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Email address", exact=True).fill("saved-locations@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        card = page.locator(".property-card").filter(has_text="Test fixture 99002")
        save = card.get_by_role("button", name="Save property 99002", exact=True)
        expect(save).to_be_visible()
        expect(save).to_have_text("Save property")
        save.click()
        expect(save).to_have_attribute("aria-pressed", "true")
        card.get_by_role("button", name="View property 99002", exact=True).click()
        expect(page.locator("#detail-actions .property-save")).to_be_visible()
        page.locator("#close-detail").click()
        # The top navigation must carry the last opened property, too.
        page.get_by_role("button", name="Property research", exact=True).click()
        expect(page.locator("#research-address")).to_have_value(
            "123 Fixture St, Test City, TX 75000"
        )
        expect(page.locator("#research-status")).to_contain_text("Review it")
        assert research_requests == []
        page.locator("#research-address").fill("456 Revised St, Test City, TX 75000")
        page.locator("#research-save").click()
        expect(page.locator("#research-save-status")).to_contain_text("Saved to your account")
        page.reload()
        page.get_by_role("button", name="Saved properties", exact=True).click()
        expect(page.locator(".property-card")).to_have_count(1)
        page.locator(".property-card").get_by_role(
            "button", name="Research property", exact=True
        ).click()
        expect(page.locator("#research-address")).to_have_value(
            "456 Revised St, Test City, TX 75000"
        )
        assert research_requests == []

        page.locator("#research-new").click()
        expect(page.locator("#research-address")).to_have_value("")
        page.locator("#research-name").fill("My synthetic property")
        page.locator("#research-address").fill("789 Manual St, Test City, TX 75000")

        def fail_save(route: Route) -> None:
            expect(page.locator("#research-save")).to_be_disabled()
            route.fulfill(status=503, json={"detail": "Synthetic database outage"})

        page.route("**/api/saved", fail_save)
        page.locator("#research-save").click()
        expect(page.locator("#research-save-status")).to_contain_text("Save failed")
        page.unroute("**/api/saved", fail_save)
        page.locator("#research-save").click()
        expect(page.locator("#research-save-status")).to_contain_text("Saved to your account")
        page.reload()
        page.get_by_role("button", name="Saved properties", exact=True).click()
        expect(page.locator(".property-card")).to_have_count(2)
        manual = page.locator(".manual-property")
        expect(manual).to_contain_text("789 Manual St")
        manual.get_by_role("button", name="Research property", exact=True).click()
        expect(page.locator("#research-name")).to_have_value("My synthetic property")
        expect(page.locator("#research-address")).to_have_value(
            "789 Manual St, Test City, TX 75000"
        )
        page.locator("#research-mode").select_option("coordinates")
        page.locator("#research-latitude").fill("35.7804")
        page.locator("#research-longitude").fill("-78.6391")
        page.locator("#research-save").click()
        expect(page.locator("#research-save-status")).to_contain_text("Saved to your account")
        page.reload()
        page.get_by_role("button", name="Saved properties", exact=True).click()
        page.locator(".manual-property").get_by_role(
            "button", name="Research property", exact=True
        ).click()
        expect(page.locator("#research-mode")).to_have_value("coordinates")
        expect(page.locator("#research-latitude")).to_have_value("35.7804")
        expect(page.locator("#research-longitude")).to_have_value("-78.6391")
        page.get_by_role("button", name="Research location", exact=True).click()
        expect(page.locator(".research-source")).to_have_count(5)
        expect(page.locator(".research-context")).to_contain_text("User-supplied coordinate")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(path="test-results/saved-location-mobile.png", full_page=True)
        page.get_by_role("button", name="Saved properties", exact=True).click()
        page.screenshot(path="test-results/saved-properties-mobile.png", full_page=True)
        page.locator(".manual-property").get_by_role(
            "button", name="Remove from Saved", exact=True
        ).click()
        expect(page.locator(".property-card")).to_have_count(1)
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.locator("#research-name")).to_have_value("")
        assert errors == []
        browser.close()


@pytest.mark.parametrize("browser_server", ["research"], indirect=True)
def test_save_scenario_defaults_and_property_handoffs(browser_server: tuple[str, int]) -> None:
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
            args=["--no-sandbox", "--disable-gpu"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Email address", exact=True).fill("handoff@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        page.locator(".property-card").first.get_by_role("button", name="View property").click()
        save = page.locator(".property-save")

        def fail_save(route: Route) -> None:
            expect(save).to_be_disabled()
            route.fulfill(status=503, json={"detail": "Synthetic save failure"})

        page.route("**/api/saved/*", fail_save)
        save.click()
        expect(page.locator("#detail-save-status")).to_contain_text("failed")
        expect(save).to_have_attribute("aria-pressed", "false")
        expect(save).to_be_enabled()
        page.unroute("**/api/saved/*", fail_save)
        save.click()
        expect(save).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#detail-save-status")).to_contain_text("Saved to your account")

        def field(name: str):
            return page.locator(f'input[name="{name}"]')

        expect(field("resale_low")).to_have_value("95000")
        expect(field("resale_likely")).to_have_value("100000")
        expect(field("resale_high")).to_have_value("120000")
        for input_ in page.locator("[data-unestimated-cost]").all():
            expect(input_).to_have_value("0")
        page.locator("#run-analysis").click()
        expect(page.locator("#analysis-results")).to_be_hidden()
        page.locator("#zero-cost-ack").check()
        page.locator("#run-analysis").click()
        expect(page.locator("#analysis-results")).to_be_visible()
        expect(page.locator("#analysis-results")).to_contain_text("zero placeholders")
        expect(page.locator("#analysis-results")).to_contain_text("hypothetical asking-price/bid")
        field("resale_high").fill("155000")
        field("purchase_price").fill("110000")
        expect(field("resale_low")).to_have_value("104500")
        expect(field("resale_high")).to_have_value("155000")
        expect(page.locator("#analysis-results")).to_be_hidden()
        field("closing_costs").fill("3000")
        page.locator("#property-dialog").get_by_role(
            "button", name="Research property", exact=True
        ).click()
        expect(page.locator("#research-latitude")).to_have_value("32.48455")
        expect(page.locator("#research-property-context")).to_contain_text("Test fixture 99001")
        expect(page.locator(".research-source")).to_have_count(5)
        page.get_by_role("button", name="Open deal scenario", exact=True).click()
        expect(field("resale_high")).to_have_value("155000")
        expect(field("closing_costs")).to_have_value("3000")
        page.locator("#property-dialog").get_by_role(
            "button", name="Find similar properties", exact=True
        ).click()
        expect(page.locator("#state")).to_have_value("TX")
        expect(page.locator("#location")).to_have_value("Fixture Eastland")
        expect(page.locator("#min-acres")).to_have_value("10")
        expect(page.locator("#category")).to_have_value("government_land")
        expect(page.locator("#max-price")).to_have_value("")
        page.locator("#state").select_option("CA")
        page.locator("#search-submit").click()
        expect(page.locator("#empty-state")).to_be_visible()
        page.get_by_role("button", name="Saved properties", exact=True).click()
        expect(page.locator("#state")).to_have_value("US")
        expect(page.locator(".property-card")).to_have_count(1)
        page.locator(".property-card").get_by_role("button", name="View property").click()
        expect(field("resale_high")).to_have_value("155000")
        page.locator("#reapply-bid-range").click()
        expect(field("resale_high")).to_have_value("132000")
        field("purchase_price").fill("")
        expect(field("resale_low")).to_have_value("")
        field("purchase_price").fill("100000")
        field("upside_pct").fill("30")
        expect(field("resale_high")).to_have_value("130000")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("#property-dialog").evaluate("el => el.scrollWidth <= el.clientWidth")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(path="test-results/property-save-scenario-mobile.png", full_page=True)
        save.click()
        expect(save).to_have_attribute("aria-pressed", "false")
        expect(page.locator("#detail-save-status")).to_contain_text("Removed")
        page.locator("#close-detail").click()
        expect(page.locator("#empty-state")).to_be_visible()
        page.get_by_role("button", name="Sign out", exact=True).click()
        page.locator("#login-tab").click()
        page.get_by_label("Email address", exact=True).fill("handoff@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        page.locator(".property-card").first.get_by_role("button", name="View property").click()
        expect(field("closing_costs")).to_have_value("0")
        expect(field("upside_pct")).to_have_value("20")
        assert errors == []
        browser.close()


@pytest.mark.parametrize("browser_server", ["research"], indirect=True)
def test_public_research_authentication_sources_mobile_and_stale_results(
    browser_server: tuple[str, int],
) -> None:
    # Only upstream public HTTP transport is synthetic; browser, API, parsers,
    # authentication, rate limits and database are real.
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
            args=["--no-sandbox", "--disable-gpu"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        expect(page.locator("#research-form")).to_be_hidden()
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Email address", exact=True).fill("research@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator("#workspace")).to_be_visible()
        page.get_by_role("button", name="Property research", exact=True).click()
        expect(page.locator("#search-form")).to_be_hidden()
        page.get_by_label("Street address, city, state and ZIP", exact=True).fill(
            "1 Synthetic Way, Fixture, NC 27000"
        )
        page.get_by_role("button", name="Research location", exact=True).click()
        expect(page.locator(".research-source")).to_have_count(5)
        expect(page.locator(".research-context")).to_contain_text("Census address approximation")
        expect(page.locator(".research-context")).to_contain_text("neighboring land")
        text = page.locator("#research-results").inner_text()
        assert "FIXTURE-999" in text and "Not published" in text
        assert "OWNER FIELD" not in text
        assert "0.00" in text and "even Zone X can flood" in text
        assert page.get_by_role("link", name="View public source & limitations").count() == 5
        assert page.locator('input[name="resale_likely"]').input_value() == ""
        # At this breakpoint the decorative breaks are hidden; words must not join.
        page.set_viewport_size({"width": 790, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(path="test-results/research-mobile.png", full_page=True)
        page.get_by_role("button", name="Data coverage", exact=True).click()
        expect(page.locator("#research-catalog .source-card")).to_have_count(5)
        expect(page.locator("#source-panel")).to_contain_text("Live MLS is not connected")
        page.get_by_role("button", name="Property research", exact=True).click()
        page.get_by_label("Research by", exact=True).select_option("coordinates")
        expect(page.locator("#research-results")).to_be_empty()
        page.get_by_label("Latitude", exact=True).fill("35.7804")
        page.get_by_label("Longitude", exact=True).fill("-78.6391")
        page.get_by_role("button", name="Research location", exact=True).click()
        expect(page.locator(".research-source")).to_have_count(5)
        expect(page.locator(".research-context")).to_contain_text("User-supplied coordinate")

        def edit_during_research(route: Route) -> None:
            result = route.fetch()
            page.get_by_label("Latitude", exact=True).fill("36")
            route.fulfill(response=result)

        page.route("**/api/research", edit_during_research)
        page.get_by_role("button", name="Research location", exact=True).click()
        expect(page.locator("#research-submit")).to_be_enabled()
        expect(page.locator("#research-results")).to_be_empty()
        page.unroute("**/api/research", edit_during_research)

        def sign_out_during_research(route: Route) -> None:
            result = route.fetch()
            page.get_by_role("button", name="Sign out", exact=True).click()
            expect(page.locator("#auth-form")).to_be_visible()
            route.fulfill(response=result)

        page.route("**/api/research", sign_out_during_research)
        page.get_by_role("button", name="Research location", exact=True).click()
        expect(page.locator("#auth-form")).to_be_visible()
        expect(page.locator("#research-results")).to_be_empty()
        expect(page.locator("#research-address")).to_have_value("")
        expect(page.locator("#research-catalog")).to_be_empty()
        assert page.evaluate("Object.keys(localStorage).length") == 0
        assert errors == []
        browser.close()


@pytest.fixture
def browser_server(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[tuple[str, int]]:
    url = f"sqlite:///{tmp_path / 'browser.db'}"
    engine, factory = database(url)
    initialize(engine)
    if os.environ.get("LANDWOLF_E2E_LIVE") == "1":
        source_engine, source_factory = database("sqlite:///./landwolf-beta.db")
        with source_factory() as source, factory() as target, target.begin():
            state = source.get(SourceState, "tx_glo_public")
            if state is None or state.status != "ready" or state.last_success is None:
                raise RuntimeError("Live browser check requires an observed successful sync")
            records = source.scalars(select(Listing).where(Listing.active.is_(True))).all()
            for record in records:
                target.add(
                    Listing(id=record.id, source=record.source, active=True, payload=record.payload)
                )
            target.add(
                SourceState(
                    id=state.id,
                    last_success=state.last_success,
                    status=state.status,
                    message=state.message,
                    record_count=len(records),
                )
            )
        source_engine.dispose()
    elif getattr(request, "param", "") == "nationwide":
        seed_national(factory)
    else:
        seed(factory)
        if getattr(request, "param", "") == "research":
            with factory() as session, session.begin():
                entry = session.get(Listing, "glo-99002")
                entry.payload = {
                    **entry.payload,
                    "source": "us_treasury",
                    "latitude": None,
                    "longitude": None,
                    "location_description": "123 Fixture St, Test City, TX 75000",
                }
    with factory() as session:
        count = len(session.scalars(select(Listing).where(Listing.active.is_(True))).all())
    engine.dispose()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    environment = {
        **os.environ,
        "LANDWOLF_ENVIRONMENT": "test",
        "LANDWOLF_DATABASE_URL": url,
        "LANDWOLF_PUBLIC_ORIGIN": origin,
        "LANDWOLF_AUTO_SYNC": "false",
    }
    with (tmp_path / "server.log").open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "research_fixture:create_fixture_app"
                if getattr(request, "param", "") == "research"
                else "landwolf.main:create_app",
                "--app-dir",
                "tests",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            env=environment,
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 15
            with httpx.Client(trust_env=False, timeout=1) as client:
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError("Browser test server exited before becoming ready")
                    try:
                        if client.get(origin + "/api/health").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Browser test server startup timed out")
            yield origin, count
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_complete_free_beta_journey(browser_server: tuple[str, int]) -> None:
    origin, count = browser_server
    screenshots = Path("test-results")
    screenshots.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        proxy = None
        if os.environ.get("LANDWOLF_BROWSER_PROXY") == "1":
            proxy = {"server": os.environ["HTTPS_PROXY"], "bypass": "127.0.0.1,localhost"}
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
            args=["--no-sandbox", "--disable-gpu"],
            proxy=proxy,
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        page = context.new_page()
        page_errors: list[str] = []
        api_failures: list[int] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "response",
            lambda response: (
                api_failures.append(response.status)
                if response.url.startswith(origin + "/api/") and response.status >= 400
                else None
            ),
        )
        page.goto(origin)
        expect(page.locator("#auth-form")).to_be_visible()
        expect(page.locator("#search-form")).to_be_hidden()
        # At this breakpoint the decorative line spans are inline; words must not join.
        page.set_viewport_size({"width": 790, "height": 1000})
        expect(page.locator(".story-heading-line")).to_have_css("display", "inline")
        expect(page.locator(".auth-heading-line")).to_have_css("display", "inline")
        assert re.search(
            r"Understand\s+the opportunity\.", page.locator(".story-copy h1").text_content()
        )
        assert re.search(
            r"Your next opportunity\s+starts here\.", page.locator("#auth-title").text_content()
        )
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.screenshot(path=str(screenshots / "login.png"), full_page=True)

        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Email address", exact=True).fill("preview@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator("#workspace")).to_be_visible()
        expect(page.locator(".property-card")).to_have_count(min(12, count))
        assert str(count) in page.locator("#results-title").inner_text()
        assert 1 <= page.locator(".leaflet-marker-icon").count() <= min(12, count)
        assert (
            f"{min(12, count)} of {min(12, count)} locations"
            in page.locator("#map-count").inner_text()
        )
        assert not page.locator("#property-map").evaluate("node => node.offsetWidth === 0")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        if os.environ.get("LANDWOLF_E2E_LIVE") == "1":
            # A map widget and pins alone do not prove that real photos/tiles loaded.
            expect(page.locator(".property-image img").first).not_to_have_js_property(
                "naturalWidth", 0, timeout=30000
            )
            expect(page.locator(".leaflet-tile-loaded").first).to_have_js_property(
                "naturalWidth", 256, timeout=30000
            )
        page.screenshot(path=str(screenshots / "explore.png"))

        page.get_by_role("button", name="List", exact=True).click()
        expect(page.locator(".map-panel")).to_be_hidden()
        page.get_by_role("button", name="Map", exact=True).click()
        expect(page.locator("#property-list")).to_be_hidden()
        expect(page.locator(".map-panel")).to_be_visible()
        page.locator(".leaflet-marker-icon").first.click()
        choices = page.locator(".map-property-choice")
        if os.environ.get("LANDWOLF_E2E_LIVE") != "1":
            # Both fixture records intentionally share a source point: both must be selectable.
            expect(choices).to_have_count(2)
        if choices.count():
            choices.first.click()
        expect(page.locator("#property-dialog")).to_be_visible()
        page.locator("#close-detail").click()
        page.get_by_role("button", name="Split", exact=True).click()
        expect(page.locator("#property-list")).to_be_visible()

        page.get_by_label("State", exact=True).select_option("CA")
        page.locator("#search-submit").click()
        expect(page.locator("#empty-state")).to_be_visible()
        assert "coverage" in page.locator("#empty-state").inner_text().lower()
        page.get_by_label("State", exact=True).select_option("TX")
        page.locator("#search-submit").click()
        expect(page.locator(".property-card")).to_have_count(min(12, count))

        first = page.locator(".property-card").first
        first.locator(".save-button").click()
        page.get_by_role("button", name="Saved properties", exact=True).click()
        expect(page.locator(".property-card")).to_have_count(1)
        page.locator(".property-card").first.get_by_role("button", name="View property").click()
        expect(page.locator("#property-dialog")).to_be_visible()
        assert "glo.texas.gov" in page.get_by_role(
            "link", name="View official listing"
        ).get_attribute("href")
        assert (
            page.locator('input[name="resale_likely"]').input_value()
            == page.locator('input[name="purchase_price"]').input_value()
        )
        for name, value in {
            "resale_low": 350000,
            "resale_likely": 400000,
            "resale_high": 450000,
            "repairs_low": 10000,
            "repairs_likely": 15000,
            "repairs_high": 30000,
            "lien_reserve": 2500,
            "closing_costs": 6000,
            "monthly_holding": 500,
            "buyer_premium_pct": 0,
            "annual_financing_pct": 8,
            "holding_months": 6,
            "selling_cost_pct": 6,
        }.items():
            page.locator(f'input[name="{name}"]').fill(str(value))
        page.locator("#zero-cost-ack").check()
        page.locator("#run-analysis").click()
        expect(page.locator("#analysis-results")).to_be_visible()
        expect(page.locator(".metric")).to_have_count(4)
        assert "beta-1.0" in page.locator("#analysis-results").inner_text()
        page.screenshot(path=str(screenshots / "analysis.png"), full_page=True)
        page.locator('input[name="lien_reserve"]').fill("3000")
        expect(page.locator("#analysis-results")).to_be_hidden()

        # Regression: editing assumptions while an actual API response is in flight
        # must not present that response as analysis of the newly entered values.
        def edit_during_response(route: Route) -> None:
            result = route.fetch()
            page.locator('input[name="lien_reserve"]').fill("4000")
            route.fulfill(response=result)

        page.route("**/api/analysis", edit_during_response)
        page.locator("#zero-cost-ack").check()
        page.locator("#run-analysis").click()
        expect(page.locator("#run-analysis")).to_be_enabled()
        expect(page.locator("#analysis-results")).to_be_hidden()
        page.unroute("**/api/analysis", edit_during_response)
        page.locator("#close-detail").click()

        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
        page.reload()
        expect(page.locator("#workspace")).to_be_visible()
        page.get_by_role("button", name="Saved properties", exact=True).click()
        expect(page.locator(".property-card")).to_have_count(1)
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.locator("#auth-form")).to_be_visible()
        expect(page.locator("#property-list")).to_be_empty()
        page.reload()
        expect(page.locator("#workspace")).to_be_hidden()
        assert page.evaluate("Object.keys(localStorage).length") == 0
        assert page_errors == []
        assert api_failures == []
        context.close()
        browser.close()


@pytest.mark.parametrize("browser_server", ["nationwide"], indirect=True)
def test_nationwide_categories_unknown_prices_and_coverage(browser_server: tuple[str, int]) -> None:
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
            args=["--no-sandbox", "--disable-gpu"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        expect(page.locator("#search-form")).to_be_hidden()
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Email address", exact=True).fill("nationwide@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card")).to_have_count(3)
        assert page.locator("#state option").count() == 51
        page.get_by_label("State", exact=True).select_option("AR")
        page.get_by_label("Category", exact=True).select_option("tax_sale")
        page.locator("#search-submit").click()
        expect(page.locator(".property-card")).to_have_count(1)
        expect(page.locator(".card-price")).to_have_text("Not available")
        assert "null" not in page.locator(".property-card").inner_text()
        page.locator(".card-detail").click()
        expect(page.locator("#property-dialog")).to_be_visible()
        assert page.locator('input[name="purchase_price"]').input_value() == ""
        assert "Source-reported taxes" in page.locator("#detail-content").inner_text()
        assert (
            page.get_by_role("link", name="View official listing")
            .get_attribute("href")
            .startswith("https://cosl.org/")
        )
        page.locator("#close-detail").click()
        page.get_by_label("Category", exact=True).select_option("pre_foreclosure")
        page.locator("#search-submit").click()
        expect(page.locator("#empty-state")).to_be_visible()
        assert "not connected" in page.locator("#empty-description").inner_text()
        page.get_by_role("button", name="Data coverage", exact=True).click()
        expect(page.locator(".coverage-table tbody tr")).to_have_count(50)
        page.get_by_label("Coverage state", exact=True).select_option("AK")
        expect(page.locator(".coverage-table tbody tr")).to_have_count(1)
        page.get_by_label("Sale type coverage", exact=True).select_option("government_land")
        expect(page.locator("#source-cards .source-card")).to_have_count(1)
        assert "Alaska" in page.locator("#source-cards .source-card").inner_text()
        expect(page.locator("#research-catalog .source-card")).to_have_count(5)
        page.locator(".coverage-table").get_by_role("button", name="Alaska", exact=True).click()
        expect(page.locator(".property-card")).to_have_count(1)
        page.locator(".card-detail").click()
        expect(page.locator("#detail-content")).to_contain_text("Alaska residents only")
        assert page.locator('input[name="purchase_price"]').input_value() == "25000"
        page.locator("#close-detail").click()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path="test-results/nationwide-mobile.png", full_page=True)
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.locator("#state-coverage")).to_be_empty()
        assert errors == []
        browser.close()
