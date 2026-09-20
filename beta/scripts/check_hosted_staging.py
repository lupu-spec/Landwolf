"""Exercise the deployed staging site with disposable accounts and live public data.

This never accepts a target URL: production and arbitrary hosts are out of scope.
No traces, cookies, passwords or account response bodies are written to artifacts.
"""

import secrets
import uuid
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

ORIGIN = "https://landwolf-premium-staging.onrender.com"
OUTPUT = Path("test-results/hosted-staging")


def main() -> None:
    with httpx.Client(base_url=ORIGIN, timeout=60, follow_redirects=False) as client:
        health = client.get("/api/health")
        health.raise_for_status()
        assert health.json() == {"status": "ok", "version": "0.2.0", "payments_enabled": False}
        session = client.get("/api/session")
        session.raise_for_status()
        assert session.json()["environment"] == "staging", "Refusing non-staging target"
        assert session.json()["email_delivery_enabled"] is False
        root = client.get("/")
        root.raise_for_status()
        assert "noindex" in root.headers["x-robots-tag"]
        for path in ("/api/sources", "/api/capabilities"):
            assert client.get(path).status_code == 401
        assert client.post("/api/search", json={}).status_code == 401
        assert client.get("/api/saved").status_code == 404
    print("Passed: HTTPS health, staging boundary, noindex, disabled billing/mail, authentication")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Reserved example.com addresses cannot contact a real customer. Mail must be disabled.
    email = f"staging-smoke-{uuid.uuid4().hex}@example.com"
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
                    page.goto(ORIGIN, wait_until="domcontentloaded", timeout=90000)
                    page.get_by_role(
                        "button", name="Sign in" if registered else "Create account", exact=True
                    ).click()
                    page.get_by_label("Email address", exact=True).fill(email)
                    page.get_by_label("Password", exact=True).fill(password)
                    page.locator("#auth-submit").click()
                    expect(page.locator(".property-card").first).to_be_visible()
                    registered = True
                    if engine == "chromium" and width == 390:
                        state = context.request.get(f"{ORIGIN}/api/session").json()
                        headers = {
                            "Origin": ORIGIN,
                            "X-LandWolf-Client": "web",
                            "X-CSRF-Token": state["csrf"],
                        }
                        denied = context.request.post(f"{ORIGIN}/api/search", data={})
                        assert denied.status == 403
                        sources = context.request.get(f"{ORIGIN}/api/sources")
                        assert sources.status == 200
                        summary = [
                            {"id": source["id"], "status": source["status"]}
                            for source in sources.json()["sources"]
                            if source["automated"]
                        ]
                        print(f"Observed live inventory source status: {summary}")
                        report = context.request.post(
                            f"{ORIGIN}/api/research",
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
                        path=str(OUTPUT / f"explore-{engine}-{width}.png"), full_page=True
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
                        path=str(OUTPUT / f"detail-{engine}-{width}.png"), full_page=True
                    )
                    page.locator("#property-dialog").get_by_role(
                        "button", name="Research property", exact=True
                    ).click()
                    expect(page.locator("#research-property-context")).not_to_be_empty()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(
                        path=str(OUTPUT / f"research-{engine}-{width}.png"), full_page=True
                    )

                    page.get_by_role("button", name="Data coverage", exact=True).click()
                    expect(page.locator("#county-coverage")).not_to_be_empty()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(
                        path=str(OUTPUT / f"coverage-{engine}-{width}.png"), full_page=True
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
    print("Passed: four hosted browser journeys; one disposable staging account retained")


if __name__ == "__main__":
    main()
