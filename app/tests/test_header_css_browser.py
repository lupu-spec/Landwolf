"""Compare shared header layout with immutable approved v0.16.0 stylesheets.

CI fetches BASELINE_COMMIT explicitly; no customer data or network baseline is used.
Screenshots compare within one browser run, avoiding cross-platform font goldens.
"""

import hashlib
import subprocess
import time
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

from landwolf.version import VERSION

pytestmark = pytest.mark.browser
BASELINE_COMMIT = "168eb749ae4a2396b98b7b1e48a9862fc915ebb3"
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
    page.bring_to_front()
    page.evaluate("""async () => {
        await document.fonts.ready;
        await Promise.all(Array.from(document.querySelectorAll('.site-header img'),
            image => image.decode()));
        window.scrollTo(0, 0);
    }""")
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
                // Custom-property enumeration order differs across documents.
                return Object.fromEntries(
                    Array.from(css).sort().map(key => [key, css.getPropertyValue(key)]));
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


def stable_computed_header(page):
    """Wait for two identical complete snapshots after dock resize scheduling."""
    previous = None
    for _ in range(6):
        settle_header(page)
        current = computed_header(page)
        if current == previous:
            return current
        previous = current
    raise AssertionError("Computed header did not stabilize within six snapshots")


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_header_cascade_matches_approved_release(browser_server, engine):
    origin, _ = browser_server
    baseline = {name: approved_css(name) for name in ("styles.css", "graphite.css")}
    output = Path("test-results/header-css")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        # Chromium's deterministic compositor flags keep image decoding and
        # compositing synchronized without changing CSS or image tolerances.
        # Do not enable BeginFrameControl: Playwright drives normal frame ticks.
        args = (
            [
                "--run-all-compositor-stages-before-draw",
                "--disable-new-content-rendering-timeout",
                "--disable-image-animation-resync",
                "--disable-threaded-animation",
                "--disable-checker-imaging",
            ]
            if engine == "chromium"
            else []
        )
        browser = getattr(playwright, engine).launch(args=args)
        contexts = [
            browser.new_context(viewport={"width": 1440, "height": 950}, reduced_motion="reduce")
            for _ in range(2)
        ]

        # Independent page loads keep CSS replacement and prior paint history
        # out of the comparison. Both renders use normal external stylesheets.
        def serve_approved(route):
            name = route.request.url.rsplit("/", 1)[-1]
            route.fulfill(body=baseline[name], content_type="text/css")

        for name in baseline:
            contexts[0].route(f"**/assets/{name}", serve_approved)
        pages = [context.new_page() for context in contexts]
        errors = []
        for page in pages:
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin)
            expect(page.locator(".brand img")).to_have_js_property("naturalWidth", 1536)

        last_owner_load = 0.0

        def load_at_size(width, height, signed_in):
            nonlocal last_owner_load
            # Two contexts share one fixture account. Respect its real 60/minute
            # search limit rather than changing auth or retrying rejected requests.
            if signed_in:
                time.sleep(max(0.0, 2.2 - (time.monotonic() - last_owner_load)))
                last_owner_load = time.monotonic()
            # A hidden WebKit subtree can retain viewport-unit values after a
            # resize. Fresh loads compare each target viewport without stale CSS.
            for page in pages:
                page.set_viewport_size({"width": width, "height": height})
                page.reload()
                expect(page.locator("#release-version")).to_contain_text(f"v{VERSION}")
                expect(page.locator(".brand img")).to_have_js_property("naturalWidth", 1536)
                if signed_in:
                    expect(page.locator(".property-card").first).to_be_visible()
                else:
                    expect(page.locator(".auth-panel")).to_be_visible()

        def compare(label, screenshots=True):
            snapshots = []
            for page in pages:
                snapshots.append(stable_computed_header(page))
            expected, actual = snapshots
            if actual != expected:
                for name, page in zip(("approved", "candidate"), pages, strict=True):
                    (output / f"{engine}-{label}-{name}-styles.json").write_text(
                        computed_header(page, details=True)
                    )
                raise AssertionError(f"Computed header changed: {engine}/{label}")
            if not screenshots:
                return
            for selector in (".site-header", ".navigation-dock"):
                nodes = [page.locator(selector) for page in pages]
                assert nodes[0].is_visible() == nodes[1].is_visible()
                if not nodes[0].is_visible():
                    continue
                name = "header" if selector == ".site-header" else "dock"
                images = []
                for version, page, node in zip(
                    ("approved", "candidate"), pages, nodes, strict=True
                ):
                    settle_header(page)
                    images.append(
                        stable_screenshot(node, output / f"{engine}-{label}-{name}-{version}.png")
                    )
                # Exact equality, with bounded failure output rather than PNG dumps.
                assert (
                    hashlib.sha256(images[0]).hexdigest() == hashlib.sha256(images[1]).hexdigest()
                ), f"Screenshot changed: {engine}/{label}/{name}"

        for signed_in in (False, True):
            if signed_in:
                for page in pages:
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
                for page in pages:
                    page.emulate_media(color_scheme=device)
                    page.locator("#appearance").select_option(mode)
                    expect(page.locator("html")).to_have_attribute(
                        "data-theme", device if mode == "system" else mode
                    )
                for width in WIDTHS:
                    load_at_size(width, 950, signed_in)
                    for page in pages:
                        expect(page.locator("html")).to_have_attribute(
                            "data-theme", device if mode == "system" else mode
                        )
                    compare(
                        f"{'owner' if signed_in else 'guest'}-{mode}-{device}-{width}",
                        screenshots=width in (390, 834, 1440) and mode != "system",
                    )
            load_at_size(390, 450, signed_in)
            compare(f"{'owner' if signed_in else 'guest'}-short")
            load_at_size(834, 950, signed_in)
            for page in pages:
                page.evaluate("document.documentElement.style.fontSize = '200%'")
            compare(f"{'owner' if signed_in else 'guest'}-large-text")
            for page in pages:
                page.evaluate("document.documentElement.style.fontSize = ''")
                page.emulate_media(media="print")
            compare(f"{'owner' if signed_in else 'guest'}-print")
            for page in pages:
                page.emulate_media(media="screen")
        assert errors == []
        for context in contexts:
            context.close()
        browser.close()
