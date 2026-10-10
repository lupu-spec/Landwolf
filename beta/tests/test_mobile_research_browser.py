"""Research navigation under keyboard viewport emulation, not native OS input."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["research"], indirect=True)
@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 834, 1440])
def test_research_keyboard_navigation(browser_server, engine_name, width):
    origin, _ = browser_server
    mobile = width < 1100
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950}, has_touch=mobile)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # Desktop Playwright cannot open an OS keyboard. Model its resize/pan
        # events while retaining real DOM, API, validation and database behavior.
        page.add_init_script("""const viewport = new EventTarget();
            Object.assign(viewport, {height: 950, offsetTop: 0, scale: 1});
            Object.defineProperty(window, 'visualViewport', {configurable: true, value: viewport});
        """)
        page.goto(origin)
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Full name", exact=True).fill("Fixture User")
        page.get_by_label("How will you use LandWolf?", exact=True).select_option("research")
        page.get_by_label("Email address", exact=True).fill("keyboard-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card")).to_have_count(2)
        page.locator('#main-nav [data-nav="research"]').click()
        address = page.locator("#research-address")
        address.fill("1 Synthetic Way, Fixture, NC 27000")
        expect(page.locator("html")).to_have_attribute("data-mobile-editing", str(mobile).lower())

        def viewport(height, top=0, scale=1):
            page.evaluate(
                """geometry => {
                Object.assign(window.visualViewport, geometry);
                window.visualViewport.dispatchEvent(new Event('resize'));
                window.visualViewport.dispatchEvent(new Event('scroll'));
            }""",
                {"height": height, "offsetTop": top, "scale": scale},
            )
            condition = (
                "document.documentElement.style.getPropertyValue('--app-viewport-height') === '"
                + str(height)
                + "px'"
                if scale == 1
                else "document.documentElement.dataset.viewportFit === 'false'"
            )
            page.wait_for_function("() => " + condition)

        viewport(420, 60)
        if mobile:
            bounds = address.bounding_box()
            assert bounds["y"] >= 60 and bounds["y"] + bounds["height"] <= 390
            # Scrolling away while editing must not snap back to the input.
            before = page.evaluate("scrollY")
            page.evaluate("""() => {
                scrollBy(0, 100);
                window.visualViewport.dispatchEvent(new Event('scroll'));
            }""")
            page.wait_for_timeout(50)
            assert page.evaluate("scrollY") >= before + 99
        done = page.locator(".navigation-dock .keyboard-done")
        if width == 390:
            expect(done).to_be_visible()
            dock = page.locator(".navigation-dock").bounding_box()
            assert dock["y"] >= 60 and dock["y"] + dock["height"] <= 480
            assert dock["height"] <= 72
            done.tap()
            expect(address).not_to_be_focused()
            expect(done).to_be_hidden()
            expect(address).to_have_value("1 Synthetic Way, Fixture, NC 27000")
        elif mobile:
            assert address.evaluate("el => getComputedStyle(el).fontSize") == "16px"
            tablet_done = page.locator("body > .keyboard-done-floating")
            expect(tablet_done).to_be_visible()
            tablet_done.tap()
            expect(address).not_to_be_focused()
        else:
            expect(done).to_be_hidden()
        viewport(950)
        page.locator("#research-submit").click()
        expect(page.locator(".research-source")).to_have_count(5)
        expect(address).not_to_be_focused()
        page.locator("#research-new").click()
        if mobile:
            expect(address).not_to_be_focused()
        address.fill("short")
        page.locator("#research-submit").click()
        expect(address).to_be_focused()
        address.fill("1 Synthetic Way, Fixture, NC 27000")
        page.route(
            "**/api/research",
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"Synthetic provider unavailable"}',
            ),
        )
        page.locator("#research-submit").click()
        expect(page.locator("#research-status")).to_contain_text("Synthetic provider unavailable")
        expect(address).to_have_value("1 Synthetic Way, Fixture, NC 27000")
        page.unroute("**/api/research")
        page.locator("#research-submit").click()
        expect(page.locator(".research-source")).to_have_count(5)
        address.focus()
        explore = page.locator('#main-nav [data-nav="explore"]')
        if mobile:
            explore.tap()
        else:
            explore.click()
        expect(address).not_to_be_focused()
        page.locator(".property-card").first.get_by_role("button", name="View property").click()
        page.locator("#detail-actions").get_by_role(
            "button", name="Decision research", exact=True
        ).click()
        workspace = page.locator("#decision-workspace")
        cost = workspace.get_by_label("Known additional costs ($)", exact=True)
        cost.fill("12345")
        viewport(420, 60)
        dialog = page.locator("#property-dialog")
        close = page.locator("#close-detail")
        modal_done = page.locator(".detail-topbar .keyboard-done")
        if mobile:
            expect(modal_done).to_be_visible()
            assert cost.evaluate("el => getComputedStyle(el).fontSize") == "16px"
            bounds = dialog.bounding_box()
            assert bounds["y"] >= 60 and bounds["y"] + bounds["height"] <= 480
            topbar = page.locator(".detail-topbar").bounding_box()
            assert topbar["height"] <= 90
            assert cost.bounding_box()["y"] >= topbar["y"] + topbar["height"]
            Path("test-results").mkdir(exist_ok=True)
            page.screenshot(path=f"test-results/research-keyboard-{engine_name}-{width}.png")
            modal_done.tap()
            expect(cost).not_to_be_focused()
            expect(cost).to_have_value("12345")
            cost.focus()
            viewport(420, 60, 2)
            assert (
                page.evaluate(
                    "document.documentElement.style.getPropertyValue('--app-viewport-height')"
                )
                == ""
            )
            viewport(420, 60)
        else:
            expect(modal_done).to_be_hidden()
        viewport(950)
        page.route(
            "**/api/decision-cases/glo-99001",
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"Synthetic storage unavailable"}',
            ),
        )
        workspace.get_by_role("button", name="Record research", exact=True).click()
        expect(workspace.get_by_role("status")).to_contain_text("Synthetic storage unavailable")
        expect(cost).to_have_value("12345")
        page.unroute("**/api/decision-cases/glo-99001")
        workspace.get_by_role("button", name="Record research", exact=True).click()
        expect(workspace.get_by_role("status")).to_contain_text("Research recorded")
        expect(cost).not_to_be_focused()
        cost.focus()
        viewport(420, 60)
        close.click()
        expect(dialog).not_to_be_visible()
        expect(cost).not_to_be_focused()
        page.evaluate("""() => {
            Object.defineProperty(window, 'visualViewport', {configurable: true, value: undefined});
            window.dispatchEvent(new Event('resize'));
        }""")
        page.wait_for_function(
            "() => document.documentElement.style.getPropertyValue('--app-viewport-bottom')"
            " === '0px'"
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert errors == []
        browser.close()
