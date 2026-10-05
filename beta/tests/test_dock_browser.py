"""Real pointer/keyboard dock interactions, wraparound, labels and reduced motion."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 834, 1440])
def test_glass_dock_navigation(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950}, has_touch=width < 1100)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        expect(page.locator("#main-nav")).to_be_hidden()
        expect(page.locator(".site-header .wolf-chat-trigger")).to_be_visible()
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card").first).to_be_visible()
        track = page.locator("#dock-track")
        shell = page.locator(".navigation-dock")
        expect(shell).to_have_attribute("data-overflow", "true")
        expect(page.locator("#coverage-nav")).to_be_visible()
        for item in page.locator("#main-nav button").all():
            assert item.get_attribute("aria-label")
            assert item.locator("svg[aria-hidden='true']").count() == 1
        # Scrolling the dock is browsing; it must not navigate or submit requests.
        track.evaluate("el => { el.scrollLeft = 0; }")
        box = track.bounding_box()
        assert box
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.wheel(0, 120)
        page.wait_for_function("() => document.querySelector('#dock-track').scrollLeft > 20")
        expect(page.locator('[data-nav="explore"]')).to_have_attribute("aria-current", "page")
        track.evaluate("el => { el.scrollLeft = el.scrollWidth; }")
        page.get_by_role("button", name="Next dock options", exact=True).click()
        page.wait_for_function("() => document.querySelector('#dock-track').scrollLeft < 2")
        # A real horizontal pointer drag must scroll without activating the button beneath it.
        box = track.bounding_box()
        assert box
        x, y = box["x"] + box["width"] - 25, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x - 110, y, steps=12)
        page.mouse.up()
        assert track.evaluate("el => el.scrollLeft") > 25
        expect(page.locator('[data-nav="explore"]')).to_have_attribute("aria-current", "page")
        if engine_name == "chromium" and width == 390:
            track.evaluate("el => { el.scrollLeft = 0; }")
            # Real touch input exercises the same swipe users make on a phone.
            cdp = page.context.new_cdp_session(page)
            cdp.send(
                "Input.dispatchTouchEvent",
                {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]},
            )
            for distance in (25, 50, 75, 100):
                cdp.send(
                    "Input.dispatchTouchEvent",
                    {"type": "touchMove", "touchPoints": [{"x": x - distance, "y": y}]},
                )
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            assert track.evaluate("el => el.scrollLeft") > 25
            expect(page.locator('[data-nav="explore"]')).to_have_attribute("aria-current", "page")
            cdp.detach()
        # Keyboard focus can reach every icon, including options outside the clipped window.
        explore = page.locator('[data-nav="explore"]')
        explore.focus()
        page.keyboard.press("ArrowRight")
        research = page.locator('[data-nav="research"]')
        expect(research).to_be_focused()
        page.keyboard.press("Enter")
        expect(page.locator("#research-panel")).to_be_visible()
        expect(research).to_have_attribute("aria-current", "page")
        research.focus()
        page.keyboard.press("End")
        expect(page.locator(".site-header .wolf-chat-trigger")).to_be_focused()
        page.keyboard.press("ArrowRight")
        expect(explore).to_be_focused()
        # A partially clipped option must stay under the pointer until release.
        hunt = page.locator('[data-nav="hunt"]')
        track.evaluate("el => { el.scrollLeft = 0; }")
        hunt.click()
        expect(page.locator("#hunt-submit")).to_be_visible()
        expect(hunt).to_have_attribute("aria-current", "page")
        page.locator('[data-nav="feedback"]').click()
        expect(page.locator('[data-nav="feedback"]')).to_have_attribute("aria-current", "page")
        explore.click()
        expect(explore).to_have_attribute("aria-current", "page")
        # Pointer magnification is decorative and respects the OS motion preference.
        if width == 1440:
            explore.hover()
            page.wait_for_function(
                "() => parseFloat(document.querySelector('[data-nav=explore]')"
                ".style.getPropertyValue('--dock-scale')) > 1.3"
            )
            page.emulate_media(reduced_motion="reduce")
            expect(explore.locator(".dock-tile")).to_have_css("transform", "none")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        output = Path("test-results")
        output.mkdir(exist_ok=True)
        page.screenshot(path=str(output / f"glass-dock-{engine_name}-{width}.png"))
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.locator("#coverage-nav")).to_be_hidden()
        expect(page.locator("#main-nav")).to_be_hidden()
        expect(page.locator(".site-header .wolf-chat-trigger")).to_be_visible()
        assert not errors
        browser.close()
