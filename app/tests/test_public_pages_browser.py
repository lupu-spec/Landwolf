"""Responsive screenshots, no-JS navigation and local public-page budgets."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

from landwolf.version import VERSION

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 834, 1440])
def test_public_pages(browser_server: tuple[str, int], engine: str, width: int) -> None:
    origin, _ = browser_server
    output = Path("test-results/public-seo")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        context = browser.new_context(viewport={"width": width, "height": 950})
        page = context.new_page()
        page.add_init_script("""window.seoShifts = 0;
            if (PerformanceObserver.supportedEntryTypes.includes('layout-shift')) {
                new PerformanceObserver(list => { for (const e of list.getEntries()) {
                    if (!e.hadRecentInput) window.seoShifts += e.value;
                }}).observe({type: 'layout-shift', buffered: true});
            }""")
        metrics = []
        page.goto(origin + "/faq")
        for mode in ("light", "dark", "system"):
            page.evaluate("mode => localStorage.setItem('landwolf.appearance', mode)", mode)
            page.emulate_media(color_scheme="dark" if mode == "system" else "light")
            for path in ("/land-investing", "/faq", "/about"):
                response = page.goto(origin + path)
                assert response and response.status == 200 and "<h1>" in response.text()
                expect(page.locator("h1")).to_be_visible()
                expect(page.locator("html")).to_have_attribute(
                    "data-theme", "light" if mode == "light" else "dark"
                )
                assert page.locator("body").evaluate("el => getComputedStyle(el).color") == (
                    "rgb(32, 35, 43)" if mode == "light" else "rgb(241, 242, 246)"
                )
                if mode == "system":
                    page.emulate_media(color_scheme="light")
                    expect(page.locator("html")).to_have_attribute("data-theme", "light")
                    page.emulate_media(color_scheme="dark")
                    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                assert page.locator("h1").count() == 1
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                expect(page.locator("header img")).to_have_js_property("complete", True)
                page.screenshot(
                    path=str(output / f"{path[1:]}-{mode}-{engine}-{width}.png"), full_page=True
                )
                timing = page.evaluate("""() => ({path: location.pathname, cls: window.seoShifts,
                    clsSupported: PerformanceObserver.supportedEntryTypes.includes('layout-shift'),
                    load: performance.getEntriesByType('navigation')[0].loadEventEnd,
                    bytes: performance.getEntriesByType('resource')
                        .reduce((n, r) => n + r.transferSize, 0)})""")
                assert timing["cls"] <= 0.1
                assert 0 < timing["load"] < 2000  # Local CI budget, not field speed.
                metrics.append(timing)
        page.goto(origin)
        expect(page.locator("#release-version")).to_contain_text(f"v{VERSION}")
        expect(page.locator(".brand img")).to_have_js_property("complete", True)
        assert page.locator(".brand img").evaluate("el => el.currentSrc.endsWith('.webp')")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(output / f"home-auto-{engine}-{width}.png"), full_page=True)
        timing = page.evaluate("""() => ({path: location.pathname, cls: window.seoShifts,
            clsSupported: PerformanceObserver.supportedEntryTypes.includes('layout-shift'),
            load: performance.getEntriesByType('navigation')[0].loadEventEnd})""")
        assert timing["cls"] <= 0.1
        assert 0 < timing["load"] < 2000
        metrics.append(timing)
        (output / f"metrics-{engine}-{width}.json").write_text(json.dumps(metrics, indent=2))
        context.close()
        context = browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(origin + "/faq")
        expect(
            page.get_by_role("heading", name="What does LandWolf help me research?")
        ).to_be_visible()
        page.get_by_role("link", name="About LandWolf").click()
        expect(page.get_by_role("heading", name="About LandWolf", exact=True)).to_be_visible()
        browser.close()
