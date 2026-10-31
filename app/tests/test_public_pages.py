"""Crawlable public content without exposing private application records."""

import json
import subprocess
from pathlib import Path
from xml.etree import ElementTree

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from landwolf.public_pages import FAQ, ORIGIN, PAGES, render_home


@pytest.fixture(scope="session", autouse=True)
def built_public_assets() -> None:
    # HTTP document assertions need the actual packaged frontend, even in a clean checkout.
    subprocess.run(
        ["npm", "run", "build"], cwd=Path(__file__).resolve().parents[1], check=True, timeout=60
    )


@pytest.mark.parametrize("path", ["/", *PAGES, "/trial-terms"])
def test_public_document(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200 and not response.history
    assert "noindex" not in response.headers.get("x-robots-tag", "")
    html = BeautifulSoup(response.text, "html.parser")
    assert len(html.select("h1")) == 1
    assert len(html.select('meta[name="description"]')) == 1
    assert len(html.select_one('meta[name="description"]')["content"]) > 60
    assert html.select_one('link[rel="canonical"]')["href"] == ORIGIN + path
    assert html.title and "LandWolf" in html.title.text
    assert not html.select('meta[name="robots"][content*="noindex"]')
    for image in html.select("img"):
        assert image.has_attr("alt") and image.has_attr("width") and image.has_attr("height")
    for link in html.select('a[href^="/"]'):
        assert client.get(link["href"]).status_code == 200, link["href"]


def test_faq_schema(client: TestClient) -> None:
    html = BeautifulSoup(client.get("/faq").text, "html.parser")
    breadcrumb, faq = json.loads(html.select_one('script[type="application/ld+json"]').string)
    assert breadcrumb["@type"] == "BreadcrumbList"
    assert breadcrumb["itemListElement"][-1]["item"] == ORIGIN + "/faq"
    assert faq["@type"] == "FAQPage"
    assert [(q["name"], q["acceptedAnswer"]["text"]) for q in faq["mainEntity"]] == list(FAQ)
    for question, answer in FAQ:
        assert question in html.get_text() and answer in html.get_text()


def test_production_crawl_policy(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client.app.state.settings, "environment", "production")
    robots = client.get("/robots.txt")
    assert "Allow: /\n" in robots.text and "Disallow: /\n" not in robots.text
    assert "Disallow: /api/\n" in robots.text
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in robots.text
    response = client.get("/sitemap.xml")
    assert response.headers["content-type"].startswith("application/xml")
    root = ElementTree.fromstring(response.text)
    urls = [loc.text for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert urls == [ORIGIN + path for path in ("/", *PAGES, "/trial-terms")]
    for url in urls:
        assert client.get(url.removeprefix(ORIGIN)).status_code == 200
    assert client.get("/api/session").headers["x-robots-tag"] == "noindex, nofollow"


@pytest.mark.parametrize("environment", ["test", "development", "staging"])
def test_nonproduction_not_submitted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setattr(client.app.state.settings, "environment", environment)
    assert client.get("/robots.txt").text == "User-agent: *\nDisallow: /\n"
    assert "<url>" not in client.get("/sitemap.xml").text
    if environment == "staging":
        assert client.get("/faq").headers["x-robots-tag"] == "noindex, nofollow"


def test_no_soft_404_or_path_override(client: TestClient) -> None:
    assert client.get("/missing-seo-test-page").status_code == 404
    assert client.get("/api/properties/private-record").status_code == 401
    response = client.get("/faq?path=%3Cscript%3Ealert(1)%3C/script%3E")
    assert response.status_code == 200 and "alert(1)" not in response.text
    assert client.get("/faq/", follow_redirects=False).headers["location"].endswith("/faq")
    assert len(client.get("/faq/").history) == 1


@pytest.mark.parametrize("path", [*PAGES, "/trial-terms"])
def test_slash_redirect_retains_transport(client: TestClient, path: str) -> None:
    response = client.get(
        path + "/?tracking=discarded",
        headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "untrusted.example"},
        follow_redirects=False,
    )
    assert response.status_code == 308
    assert response.headers["location"] == path
    assert client.get(path).status_code == 200


def test_no_orphan_pages(client: TestClient) -> None:
    home = BeautifulSoup(client.get("/").text, "html.parser")
    assert set(PAGES).issubset({a.get("href") for a in home.select("a")})
    for path in PAGES:
        response = client.get(path)
        assert len(response.content) < 15_000
        assert "/assets/app.js" not in response.text
        assert "default-src 'self'" in response.headers["content-security-policy"]


@pytest.mark.parametrize("enabled", [False, True])
def test_home_renders_public_availability(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, enabled: bool
) -> None:
    # Exercise both presentation states; policy computation has separate trial tests.
    monkeypatch.setattr("landwolf.main.trials.enabled", lambda _settings: enabled)
    response = client.get("/")
    offer = BeautifulSoup(response.text, "html.parser").select_one("#trial-signup-offer")
    assert offer.has_attr("hidden") is not enabled
    assert client.get("/api/session").json()["feedback_trial_enabled"] is enabled
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("source", ["no marker", 'id="trial-signup-offer" hidden' * 2])
def test_home_rejects_ambiguous_template(source: str) -> None:
    with pytest.raises(ValueError, match="one trial-offer visibility marker"):
        render_home(source, trial_enabled=True)
