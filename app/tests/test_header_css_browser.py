"""Compare shared header layout with immutable approved v0.15.0 stylesheets.

CI fetches BASELINE_COMMIT explicitly; no customer data or network baseline is used.
Screenshots compare within one browser run, avoiding cross-platform font goldens.
"""

import hashlib
import subprocess
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser
BASELINE_COMMIT = "55a35648140ffb3d3dead8c2e09a54d55dfc0e63"
ROOT = Path(__file__).resolve().parents[2]
WIDTHS = (
    360,
    361,
    390,
    480,
    481,
    639,
    640,
    800,
    801,
    834,
    1000,
    1001,
    1050,
    1051,
    1150,
    1151,
    1440,
)


def approved_css(name):
    result = subprocess.run(
        ["git", "show", f"{BASELINE_COMMIT}:app/web/{name}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return result.stdout


def settle_header(page):
    page.evaluate("window.scrollTo(0, 0)")
    page.mouse.move(0, 940)
    page.locator("#dock-track").evaluate("el => { el.scrollLeft = 0; }")
    page.evaluate("""() => new Promise(resolve => requestAnimationFrame(() =>
        requestAnimationFrame(resolve)))""")


def stable_screenshot(node, path=None):
    """Require two identical paints; rounded image edges can repaint after resize."""
    previous = None
    for _ in range(6):
        current = node.screenshot(animations="disabled", scale="css")
        if current == previous:
            if path is not None:
                path.write_bytes(current)
            return current
        previous = current
    raise AssertionError("Header screenshot did not stabilize within six captures")


def computed_header(page, details=False):
    return page.locator(".site-header").evaluate(
        """async (header, details) => {
        const nodes = [header, ...header.querySelectorAll('*')];
        const values = nodes.map(el => {
            const styles = pseudo => {
                const css = getComputedStyle(el, pseudo);
                return Object.fromEntries(
                    Array.from(css).map(key => [key, css.getPropertyValue(key)]));
            };
            const r = el.getBoundingClientRect();
            return {tag: el.tagName, id: el.id, classes: el.getAttribute('class'),
                css: styles(null), before: styles('::before'), after: styles('::after'),
                rect: [r.x, r.y, r.width, r.height]};
        });
        const json = JSON.stringify(values);
        if (details) return json;
        // Keep every property while avoiding huge browser-to-Python transfers.
        const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(json));
        return Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, '0')).join('');
    }""",
        details,
    )


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_header_cascade_matches_approved_release(browser_server, engine):
    origin, _ = browser_server
    baseline = {name: approved_css(name) for name in ("styles.css", "graphite.css")}
    candidate = {name: (ROOT / "app/web" / name).read_text() for name in baseline}
    output = Path("test-results/header-css")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": 1440, "height": 950}, reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        expect(page.locator(".brand img")).to_have_js_property("naturalWidth", 1536)
        # Replace links in place, retaining leaflet/theme/source order.
        page.evaluate("""() => {
            for (const name of ['styles.css', 'graphite.css']) {
                const link = document.querySelector(`link[href='/assets/${name}']`);
                const style = document.createElement('style');
                style.id = `comparison-${name}`;
                link.replaceWith(style);
            }
        }""")

        def apply(css):
            page.evaluate(
                """css => {
                for (const [name, text] of Object.entries(css)) {
                    document.getElementById(`comparison-${name}`).textContent = text;
                }
            }""",
                css,
            )
            settle_header(page)

        def compare(label, screenshots=True):
            apply(baseline)
            expected = computed_header(page)
            images = {}
            for selector in (".site-header", ".navigation-dock"):
                node = page.locator(selector)
                if screenshots and node.is_visible():
                    images[selector] = stable_screenshot(node)
            apply(candidate)
            actual = computed_header(page)
            if actual != expected:
                for name, css in (("approved", baseline), ("candidate", candidate)):
                    apply(css)
                    (output / f"{engine}-{label}-{name}-styles.json").write_text(
                        computed_header(page, details=True)
                    )
                raise AssertionError(f"Computed header changed: {engine}/{label}")
            for selector, image in images.items():
                name = "header" if selector == ".site-header" else "dock"
                (output / f"{engine}-{label}-{name}-approved.png").write_bytes(image)
                current = stable_screenshot(
                    page.locator(selector), output / f"{engine}-{label}-{name}-candidate.png"
                )
                # Compare exact bytes via digests to avoid dumping entire PNGs on failure.
                assert hashlib.sha256(current).hexdigest() == hashlib.sha256(image).hexdigest(), (
                    f"Screenshot changed: {engine}/{label}/{name}"
                )

        apply(candidate)
        for signed_in in (False, True):
            if signed_in:
                page.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
                page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
                page.locator("#auth-submit").click()
                expect(page.locator(".property-card").first).to_be_visible()
            for mode, device in (
                ("light", "dark"),
                ("dark", "light"),
                ("system", "light"),
                ("system", "dark"),
            ):
                page.emulate_media(color_scheme=device)
                page.locator("#appearance").select_option(mode)
                expect(page.locator("html")).to_have_attribute(
                    "data-theme", device if mode == "system" else mode
                )
                for width in WIDTHS:
                    page.set_viewport_size({"width": width, "height": 950})
                    compare(
                        f"{'owner' if signed_in else 'guest'}-{mode}-{device}-{width}",
                        screenshots=width in (390, 834, 1440) and mode != "system",
                    )
            page.set_viewport_size({"width": 390, "height": 450})
            compare(f"{'owner' if signed_in else 'guest'}-short")
            page.set_viewport_size({"width": 834, "height": 950})
            page.evaluate("document.documentElement.style.fontSize = '200%'")
            compare(f"{'owner' if signed_in else 'guest'}-large-text")
            page.evaluate("document.documentElement.style.fontSize = ''")
            page.emulate_media(media="print")
            compare(f"{'owner' if signed_in else 'guest'}-print")
            page.emulate_media(media="screen")
        assert errors == []
        browser.close()
