"""Read-only acceptance against the established staging and production origins."""

import argparse
import json
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from landwolf.public_pages import FAQ, ORIGIN, PAGES

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=tuple(ORIGINS), required=True)
    check(parser.parse_args().environment)
