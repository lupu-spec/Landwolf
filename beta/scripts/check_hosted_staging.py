"""Exercise an explicitly selected LandWolf environment after its release deploys.

Only the two fixed owner-approved origins are accepted; never arbitrary hosts.
No traces, cookies, passwords or account response bodies are written to artifacts.
"""

import argparse
import os
import re
import secrets
import time
import uuid
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

from landwolf.version import VERSION

ORIGINS = {
    "staging": "https://landwolf-premium-staging.onrender.com",
    "production": "https://landwolf.ai",
}


def main() -> None:
    expect.set_options(timeout=45000)
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=tuple(ORIGINS), default="staging")
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        raise SystemExit("An exact expected deployment commit is required")
    origin = ORIGINS[args.environment]
    output = Path("test-results/hosted-staging")
    with httpx.Client(base_url=origin, timeout=60, follow_redirects=False) as client:
        # Push-triggered checks can start before the explicitly approved deploy.
        # Never exercise accounts until the exact expected runtime is live.
        deadline = time.monotonic() + 600
        while True:
            try:
                identity = client.get("/api/version")
                if identity.status_code == 200 and identity.json() == {
                    "version": VERSION,
                    "environment": args.environment,
                    "commit": args.commit,
                }:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError("Expected release was not observed; no account tests ran")
            time.sleep(10)
        health = client.get("/api/health")
        health.raise_for_status()
        assert health.json() == {"status": "ok", "version": VERSION, "payments_enabled": False}
        session = client.get("/api/session")
        session.raise_for_status()
        assert session.json()["environment"] == args.environment, (
            "Refusing a mismatched environment"
        )
        assert session.json()["email_delivery_enabled"] is False
        root = client.get("/")
        root.raise_for_status()
        if args.environment == "staging":
            assert "noindex" in root.headers["x-robots-tag"]
        else:
            assert "noindex" not in root.headers.get("x-robots-tag", "")
            with httpx.Client(timeout=60, follow_redirects=False) as www:
                redirect = www.get("https://www.landwolf.ai/")
                assert redirect.status_code in {301, 302, 307, 308}
                assert redirect.headers["location"] == "https://landwolf.ai/"
        for path in ("/api/sources", "/api/capabilities"):
            assert client.get(path).status_code == 401
        assert client.post("/api/search", json={}).status_code == 401
        assert client.get("/api/saved").status_code == 404
    print(
        "Passed: exact release identity, HTTPS, environment, disabled billing/mail, authentication"
    )

    output.mkdir(parents=True, exist_ok=True)
    # Reserved example.com addresses cannot contact a real customer. Mail must be disabled.
    email = f"{args.environment}-smoke-{uuid.uuid4().hex}@example.com"
    password = secrets.token_urlsafe(32)
    registered = False
    with sync_playwright() as playwright:
        for engine in ("chromium", "webkit"):
            for width in (390, 1440):
                browser = getattr(playwright, engine).launch()
                context = browser.new_context(viewport={"width": width, "height": 900})
                page = context.new_page()
                page.set_default_timeout(45000)
                errors: list[str] = []
                page.on("pageerror", lambda error, sink=errors: sink.append(type(error).__name__))
                try:
                    page.goto(origin, wait_until="domcontentloaded", timeout=90000)
                    expect(page.locator("#release-version")).to_contain_text(f"v{VERSION}")
                    page.get_by_role(
                        "button", name="Sign in" if registered else "Create account", exact=True
                    ).click()
                    page.get_by_label("Email address", exact=True).fill(email)
                    page.get_by_label("Password", exact=True).fill(password)
                    page.locator("#auth-submit").click()
                    expect(page.locator(".property-card").first).to_be_visible()
                    registered = True
                    if engine == "chromium" and width == 390:
                        state = context.request.get(f"{origin}/api/session").json()
                        headers = {
                            "Origin": origin,
                            "X-LandWolf-Client": "web",
                            "X-CSRF-Token": state["csrf"],
                        }
                        denied = context.request.post(f"{origin}/api/search", data={})
                        assert denied.status == 403
                        sources = context.request.get(f"{origin}/api/sources")
                        assert sources.status == 200
                        summary = [
                            {"id": source["id"], "status": source["status"]}
                            for source in sources.json()["sources"]
                            if source["automated"]
                        ]
                        print(f"Observed live inventory source status: {summary}")
                        report = context.request.post(
                            f"{origin}/api/research",
                            headers=headers,
                            data={"latitude": 35.7804, "longitude": -78.6391},
                            timeout=90000,
                        )
                        assert report.status == 200
                        research = report.json()
                        assert len(research["sources"]) == 5
                        assert any(s["status"] == "ready" for s in research["sources"])
                        print(
                            "Passed: live research response, CSRF rejection; research status: "
                            + research["status"]
                        )
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    expect(page.locator("#main-nav button")).to_have_count(3)
                    page.screenshot(
                        path=str(output / f"explore-{engine}-{width}.png"), full_page=True
                    )

                    page.locator(".property-card").first.get_by_role(
                        "button", name="View property"
                    ).click()
                    expect(page.locator("#property-dialog .trust-panel")).to_be_visible()
                    page.get_by_text("Inspect field evidence", exact=True).click()
                    expect(page.locator("#property-dialog .evidence-list")).to_be_visible()
                    assert page.locator("#property-dialog").evaluate(
                        "el => el.scrollWidth <= el.clientWidth"
                    )
                    page.screenshot(
                        path=str(output / f"detail-{engine}-{width}.png"), full_page=True
                    )
                    for name, value in {
                        "purchase_price": "100000",
                        "resale_low": "95000",
                        "resale_likely": "100000",
                        "resale_high": "120000",
                    }.items():
                        page.locator(f'input[name="{name}"]').fill(value)
                    page.locator("#zero-cost-ack").check()
                    page.locator("#run-analysis").click()
                    expect(page.locator("#analysis-results")).to_be_visible()
                    expect(page.locator(".metric .label")).to_have_text(
                        ["MEDIAN NET PROFIT", "PROBABILITY OF LOSS", "MEDIAN ROI"]
                    )
                    expect(page.locator(".primary-metric")).to_have_count(0)
                    assert (
                        "maximum bid" not in page.locator("#property-dialog").inner_text().lower()
                    )
                    assert page.locator("#property-dialog").evaluate(
                        "el => el.scrollWidth <= el.clientWidth"
                    )
                    page.screenshot(
                        path=str(output / f"simulation-{engine}-{width}.png"), full_page=True
                    )
                    page.locator("#property-dialog").get_by_role(
                        "button", name="Research property", exact=True
                    ).click()
                    expect(page.locator("#research-property-context")).not_to_be_empty()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(
                        path=str(output / f"research-{engine}-{width}.png"), full_page=True
                    )

                    page.get_by_role("button", name="Data coverage", exact=True).click()
                    expect(page.locator("#county-coverage")).not_to_be_empty()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(
                        path=str(output / f"coverage-{engine}-{width}.png"), full_page=True
                    )
                    page.reload(wait_until="domcontentloaded")
                    expect(page.locator(".property-card").first).to_be_visible()
                    page.get_by_role("button", name="Sign out", exact=True).click()
                    expect(page.locator("#auth-submit")).to_be_visible()
                    assert not errors, "Browser raised an uncaught script error"
                    print(f"Passed: {engine} {width}px authentication, evidence, handoff, coverage")
                finally:
                    context.close()
                    browser.close()
    print("Passed: four hosted browser journeys; one disposable test account retained")


if __name__ == "__main__":
    main()
