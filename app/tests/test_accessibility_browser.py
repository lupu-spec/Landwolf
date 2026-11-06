"""WCAG A/AA automated regression checks; manual checks remain mandatory."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser
AXE = Path("node_modules/axe-core/axe.min.js")


def scan(page: Page, name: str) -> list[dict]:
    output = Path("test-results/accessibility")
    output.mkdir(parents=True, exist_ok=True)
    # Force a real paint before measuring inherited theme colors in WebKit.
    # The existing public-theme suite uses the same rendered-paint boundary.
    page.screenshot(path=str(output / f"{name}.png"))
    page.evaluate(AXE.read_text())
    result = page.evaluate("""async () => await axe.run(document, {
        runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']}
    })""")
    (output / f"{name}.json").write_text(json.dumps(result, indent=2))
    return [
        {"page": name, "id": v["id"], "nodes": [n["target"] for n in v["nodes"]]}
        for v in result["violations"]
    ]


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("browser_server", ["research_owner"], indirect=True)
def test_accessible_journeys(browser_server, width, theme, engine):
    origin, _ = browser_server
    failures = []
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        page.add_init_script(f"localStorage.setItem('landwolf.appearance', '{theme}')")

        def audit(name):
            failures.extend(scan(page, f"{name}-{engine}-{width}-{theme}"))

        for path in [
            "/",
            "/faq",
            "/about",
            "/land-investing",
            "/trial-terms",
            "/lupuspec",
            "/accessibility",
        ]:
            page.goto(origin + path)
            audit(path.strip("/") or "home")
        page.goto(origin)
        page.keyboard.press("Tab")
        expect(page.locator(".skip-link")).to_be_focused()
        page.keyboard.press("Enter")
        expect(page.locator("#main")).to_be_focused()
        page.locator("#forgot-password").click()
        audit("recovery-dialog")
        page.keyboard.press("Escape")
        expect(page.locator("#forgot-password")).to_be_focused()
        page.get_by_role("button", name="Create account", exact=True).click()
        audit("registration")
        page.locator("#login-tab").click()
        page.locator("#auth-submit").click()
        expect(page.locator("#email")).to_be_focused()
        assert page.locator("#email").evaluate("el => !el.validity.valid")
        page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card").first).to_be_visible()
        audit("search")
        page.get_by_role("button", name="Map", exact=True).click()
        audit("map")
        page.get_by_role("button", name="List", exact=True).click()
        opener = page.locator(".property-card button").first
        opener.focus()
        page.keyboard.press("Enter")
        expect(page.locator("#property-dialog")).to_be_visible()
        audit("property-dialog")
        page.locator("#property-dialog .wolf-chat-trigger").click()
        expect(page.locator("#wolf-chat-panel")).to_be_visible()
        audit("dialog-help")
        page.get_by_role("button", name="Collapse Romulus and Remus chat").click()
        page.keyboard.press("Escape")
        expect(opener).to_be_focused()
        for view in ["research", "hunt", "sources", "crm", "finance", "feedback", "billing"]:
            page.locator(f'#main-nav [data-nav="{view}"]').click()
            expect(page.locator("#workspace-title")).to_be_focused()
            page.wait_for_timeout(500)
            if view == "hunt":
                expect(page.get_by_role("group", name="Quick starters")).to_be_visible()
            audit(view)
            if view == "research":
                page.locator("#research-mode").select_option("address")
                page.get_by_label("Street address, city, state and ZIP", exact=True).fill(
                    "123 Test Street, Raleigh, NC"
                )
                page.get_by_role("button", name="Research location", exact=True).click()
                expect(page.locator("#research-results")).not_to_be_empty()
                audit("research-results")
                page.route(
                    "**/api/research",
                    lambda route: route.fulfill(
                        status=503,
                        content_type="application/json",
                        body='{"detail":"Research unavailable. Please try again."}',
                    ),
                )
                page.get_by_role("button", name="Research location", exact=True).click()
                expect(page.locator("#research-status")).to_contain_text("Please try again")
                expect(page.locator("#research-address")).to_have_value(
                    "123 Test Street, Raleigh, NC"
                )
                expect(page.locator("#research-submit")).to_be_enabled()
                audit("research-error")
                page.unroute("**/api/research")
            if view == "crm":
                page.get_by_text("Add contact", exact=True).click()
                audit("admin-contact-form")
            if view == "finance":
                table = page.locator(".finance-table-wrap").first
                table.focus()
                expect(table).to_be_focused()
        for link in page.locator(".site-footer a").all():
            link.focus()
            assert link.evaluate("""el => {
                const r = el.getBoundingClientRect();
                const visible = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
                return el.contains(visible);
            }""")
        page.emulate_media(reduced_motion="reduce")
        assert page.locator(".dock-tile").first.evaluate(
            "el => getComputedStyle(el).transitionDuration === '0s'"
        )
        page.screenshot(path=f"test-results/accessibility/final-{engine}-{width}-{theme}.png")
        page.set_viewport_size({"width": 320, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.set_viewport_size({"width": 1280, "height": 900})
        page.add_style_tag(
            content="""body { zoom: 2; }
            * { line-height: 1.5 !important; letter-spacing: .12em !important;
                word-spacing: .16em !important; }
            p { margin-bottom: 2em !important; }"""
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=f"test-results/accessibility/reflow-{engine}-{width}-{theme}.png")
        browser.close()
    assert failures == [], json.dumps(failures, indent=2)
