"""Appearance persists and all feature surfaces follow the selected silver/glass mode."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


def assert_surface(page, selector, mode):
    node = page.locator(selector).first
    expect(node).to_be_visible()
    assert node.evaluate("el => getComputedStyle(el).color") == (
        "rgb(241, 242, 246)" if mode == "dark" else "rgb(32, 35, 43)"
    )
    assert node.evaluate("el => getComputedStyle(el).backgroundImage") != "none"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 834, 1440])
def test_appearance_across_feature_surfaces(browser_server, engine, width):
    origin, _ = browser_server
    output = Path("test-results")
    output.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        context = browser.new_context(viewport={"width": width, "height": 950}, color_scheme="dark")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        appearance = page.get_by_role("combobox", name="Appearance", exact=True)
        expect(appearance).to_have_value("system")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.emulate_media(color_scheme="light")
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        appearance.select_option("dark")
        page.reload()
        expect(appearance).to_have_value("dark")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        # The small blocking bundle must select the saved mode before app startup.
        before_app = context.new_page()
        before_app.route("**/assets/app.js", lambda route: route.abort())
        before_app.goto(origin)
        expect(before_app.locator("html")).to_have_attribute("data-theme", "dark")
        before_app.close()
        for mode in ("dark", "light"):
            appearance.select_option(mode)
            assert_surface(page, ".auth-panel", mode)
            page.screenshot(path=str(output / f"theme-auth-{mode}-{engine}-{width}.png"))
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card").first).to_be_visible()
        for mode in ("dark", "light"):
            appearance.select_option(mode)
            expect(page.locator("html")).to_have_attribute("data-theme", mode)
            expect(page.locator("#workspace-title")).to_have_css(
                "color", "rgb(241, 242, 246)" if mode == "dark" else "rgb(32, 35, 43)"
            )
            assert_surface(page, ".search-bar", mode)
            assert_surface(page, ".property-card", mode)
            if width < 640:
                dock = page.locator(".navigation-dock").bounding_box()
                assert dock and dock["y"] > 750 and dock["y"] + dock["height"] <= 950
            expected_control = "rgb(28, 31, 38)" if mode == "dark" else "rgb(243, 244, 248)"
            assert (
                page.locator("#location").evaluate("el => getComputedStyle(el).backgroundColor")
                == expected_control
            )
            # Input text must meet WCAG's normal-text contrast in each palette.
            assert page.locator("#location").evaluate(r"""el => {
                const css = getComputedStyle(el);
                const lum = color => {
                    const rgb = color.match(/[\d.]+/g).slice(0, 3).map(Number);
                    const v = rgb.map(n => { n /= 255;
                        return n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4;
                    });
                    return .2126 * v[0] + .7152 * v[1] + .0722 * v[2];
                };
                const values = [lum(css.color), lum(css.backgroundColor)].sort((a,b) => b-a);
                return (values[0] + .05) / (values[1] + .05) >= 4.5;
            }""")
            page.screenshot(path=str(output / f"theme-explore-{mode}-{engine}-{width}.png"))
            page.locator(".card-detail").first.click()
            assert_surface(page, "#property-dialog", mode)
            page.screenshot(path=str(output / f"theme-property-{mode}-{engine}-{width}.png"))
            page.locator("#close-detail").click()
            for route, panel in (
                ("research", "#research-panel"),
                ("hunt", "#hunt-panel"),
                ("sources", "#source-panel"),
                ("feedback", "#feedback-panel"),
                ("billing", "#billing-panel"),
                ("crm", "#crm-panel"),
                ("finance", ".finance-card"),
            ):
                page.locator(f'#main-nav [data-nav="{route}"]').click()
                assert_surface(page, panel, mode)
                page.screenshot(path=str(output / f"theme-{route}-{mode}-{engine}-{width}.png"))
            page.locator('#main-nav [data-nav="explore"]').click()
            page.locator("#wolf-chat-launcher").click()
            assert_surface(page, "#wolf-chat-panel", mode)
            page.screenshot(path=str(output / f"theme-chat-{mode}-{engine}-{width}.png"))
            page.get_by_role("button", name="Collapse Romulus and Remus chat").click()
        # A second tab and system changes cannot silently override an explicit choice.
        second = context.new_page()
        second.goto(origin)
        second.get_by_role("combobox", name="Appearance", exact=True).select_option("dark")
        expect(appearance).to_have_value("dark")
        page.emulate_media(color_scheme="light")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        second.evaluate("localStorage.clear()")
        expect(appearance).to_have_value("system")
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        page.emulate_media(media="print")
        assert page.locator("body").evaluate("el => getComputedStyle(el).backgroundColor") == (
            "rgb(255, 255, 255)"
        )
        assert errors == []
        context.close()
        browser.close()


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_appearance_when_storage_is_invalid_or_blocked(browser_server, engine):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        context = browser.new_context(color_scheme="dark")
        context.add_init_script("localStorage.setItem('landwolf.appearance', 'invalid');")
        page = context.new_page()
        page.goto(origin)
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        expect(page.locator("#appearance")).to_have_value("system")
        context.close()
        context = browser.new_context(color_scheme="light")
        context.add_init_script("""for (const name of ['getItem', 'setItem']) {
          Storage.prototype[name] = () => { throw new DOMException('Blocked', 'SecurityError'); };
        }""")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        page.get_by_role("combobox", name="Appearance", exact=True).select_option("dark")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        assert errors == []
        context.close()
        browser.close()
