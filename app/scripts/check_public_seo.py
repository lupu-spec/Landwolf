"""Read-only acceptance against the established staging and production origins."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import expect, sync_playwright

from landwolf.public_pages import FAQ, ORIGIN, PAGES
from landwolf.version import VERSION

ORIGINS = {"production": ORIGIN, "staging": "https://landwolf-premium-staging.onrender.com"}


def check(environment: str) -> None:
    metrics = []
    with httpx.Client(base_url=ORIGINS[environment], timeout=45, follow_redirects=False) as client:
        for path in ("/", *PAGES, "/trial-terms"):
            started = time.monotonic()
            response = client.get(path)
            response.raise_for_status()
            assert response.status_code == 200
            elapsed = round((time.monotonic() - started) * 1000)
            if path != "/":
                slash = client.get(path + "/")
                assert slash.status_code == 308 and slash.headers["location"] == path, path
            html = BeautifulSoup(response.text, "html.parser")
            assert len(html.select("h1")) == 1, path
            assert html.select_one('meta[name="description"]')["content"], path
            assert html.select_one('link[rel="canonical"]')["href"] == ORIGIN + path, path
            assert ("noindex" in response.headers.get("x-robots-tag", "")) is (
                environment == "staging"
            )
            for link in html.select('a[href^="/"]'):
                assert client.get(link["href"]).status_code == 200, link["href"]
            for img in html.select("img"):
                assert img.has_attr("alt") and img.has_attr("width") and img.has_attr("height")
            metrics.append(
                {"path": path, "response_ms": elapsed, "html_bytes": len(response.content)}
            )
        faq = BeautifulSoup(client.get("/faq").text, "html.parser")
        data = json.loads(faq.select_one('script[type="application/ld+json"]').string)
        assert data[1]["@type"] == "FAQPage" and len(data[1]["mainEntity"]) == len(FAQ)
        assert client.get("/missing-seo-acceptance-page").status_code == 404
        assert client.get("/api/session").headers["x-robots-tag"] == "noindex, nofollow"
        assets = {
            "styles.css": Path("web/styles.css"),
            "public.css": Path("web/assets/public.css"),
            **{
                name: Path("web/assets") / name
                for name in ("landscape.webp", "landwolf-logo.webp", "no-photo-available.webp")
            },
        }
        for name, source in assets.items():
            asset = client.get("/assets/" + name)
            asset.raise_for_status()
            assert (
                hashlib.sha256(asset.content).digest()
                == hashlib.sha256(source.read_bytes()).digest()
            ), name
        robots = client.get("/robots.txt")
        sitemap = client.get("/sitemap.xml")
        robots.raise_for_status()
        sitemap.raise_for_status()
        if environment == "production":
            assert "Disallow: /\n" not in robots.text
            assert f"Sitemap: {ORIGIN}/sitemap.xml" in robots.text
            for path in ("/", *PAGES, "/trial-terms"):
                assert f"<loc>{ORIGIN}{path}</loc>" in sitemap.text
            for url in ("http://landwolf.ai/", "https://www.landwolf.ai/"):
                redirect = client.get(url)
                assert redirect.status_code in {301, 308}, (url, redirect.status_code)
                assert redirect.headers["location"] == ORIGIN + "/", url
        else:
            assert robots.text == "User-agent: *\nDisallow: /\n" and "<url>" not in sitemap.text
    output = Path("test-results/hosted-staging")
    output.mkdir(parents=True, exist_ok=True)
    (output / "public-seo.json").write_text(json.dumps(metrics, indent=2))
    print(f"Passed: {environment} public documents, crawl policy, links, schema and genuine 404")
    print(json.dumps(metrics))


def check_browsers(environment: str) -> None:
    origin = ORIGINS[environment]
    output = Path("test-results/hosted-staging")
    output.mkdir(parents=True, exist_ok=True)
    metrics = []
    with sync_playwright() as playwright:
        for engine in ("chromium", "webkit"):
            browser = getattr(playwright, engine).launch()
            for width in (390, 1440):
                context = browser.new_context(viewport={"width": width, "height": 950})
                page = context.new_page()
                page.add_init_script("""window.publicCLS = 0;
                    if (PerformanceObserver.supportedEntryTypes.includes('layout-shift')) {
                        new PerformanceObserver(list => { for (const e of list.getEntries()) {
                            if (!e.hadRecentInput) window.publicCLS += e.value;
                        }}).observe({type: 'layout-shift', buffered: true});
                    }""")
                page.goto(origin + "/faq", timeout=90000)
                for mode in ("light", "dark", "system"):
                    page.get_by_label("Appearance", exact=True).select_option(mode)
                    page.emulate_media(color_scheme="dark" if mode == "system" else "light")
                    for path in ("/", *PAGES):
                        response = page.goto(origin + path, timeout=90000)
                        assert response and response.status == 200
                        if path == "/":
                            expect(page.locator("#release-version")).to_contain_text(f"v{VERSION}")
                        expected = "light" if mode == "light" else "dark"
                        expect(page.locator("html")).to_have_attribute("data-theme", expected)
                        name = path.strip("/") or "home"
                        page.screenshot(
                            path=str(output / f"public-{name}-{engine}-{width}-{mode}.png"),
                            full_page=True,
                        )
                        expect(page.locator("body")).to_have_css(
                            "color",
                            "rgb(32, 35, 43)" if expected == "light" else "rgb(241, 242, 246)",
                        )
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        timing = page.evaluate("""() => ({
                            load_ms: performance.getEntriesByType('navigation')[0].loadEventEnd,
                            cls: window.publicCLS,
                            cls_supported: PerformanceObserver.supportedEntryTypes
                                .includes('layout-shift')
                        })""")
                        timing.update(engine=engine, width=width, mode=mode, path=path)
                        metrics.append(timing)
                        (output / "public-browser-metrics.json").write_text(
                            json.dumps(metrics, indent=2)
                        )
                        assert 0 < timing["load_ms"] < 2000, (engine, width, mode, path, timing)
                        if timing["cls_supported"]:
                            assert timing["cls"] <= 0.1, (engine, width, mode, path, timing)
                        if mode == "system":
                            page.emulate_media(color_scheme="light")
                            expect(page.locator("html")).to_have_attribute("data-theme", "light")
                            page.emulate_media(color_scheme="dark")
                            expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                context.close()
            browser.close()
    (output / "public-browser-metrics.json").write_text(json.dumps(metrics, indent=2))
    print("Passed: hosted public responsive screenshots, exact themes, load and layout budgets")
    print(json.dumps(metrics))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=tuple(ORIGINS), required=True)
    environment = parser.parse_args().environment
    check(environment)
    check_browsers(environment)
