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
from tempfile import TemporaryDirectory

import httpx
from playwright.sync_api import Playwright, expect, sync_playwright

from landwolf.version import VERSION

ORIGINS = {
    "staging": "https://landwolf-premium-staging.onrender.com",
    "production": "https://landwolf.ai",
}


def check_persistence(
    playwright: Playwright, origin: str, email: str, password: str, payments_enabled: bool
) -> None:
    """Restart real browser profiles; never export cookies/tokens to CI artifacts."""
    for engine_name in ("chromium", "webkit"):
        engine = getattr(playwright, engine_name)
        with TemporaryDirectory(prefix="landwolf-browser-") as profile:

            def launch(engine=engine, profile=profile):
                return engine.launch_persistent_context(
                    profile, viewport={"width": 390, "height": 900}
                )

            context = launch()
            try:
                page = context.new_page()
                page.goto(origin, wait_until="domcontentloaded", timeout=90000)
                page.get_by_role("button", name="Sign in", exact=True).click()
                page.get_by_label("Email address", exact=True).fill(email)
                page.get_by_label("Password", exact=True).fill(password)
                page.locator("#auth-submit").click()
                target = "#billing-panel" if payments_enabled else ".property-card"
                expect(page.locator(target).first).to_be_visible()
                cookie = next(c for c in context.cookies() if c["name"] == "landwolf_session")
                assert cookie["httpOnly"] and cookie["secure"]
                assert cookie["sameSite"] == "Strict"
                assert cookie["expires"] > time.time() + 364 * 86400
                assert "landwolf_session" not in page.evaluate("document.cookie")
                page.evaluate("""async () => {
                    localStorage.clear(); sessionStorage.clear();
                    for (const key of await caches.keys()) await caches.delete(key);
                }""")
                if engine_name == "chromium":
                    context.new_cdp_session(page).send("Network.clearBrowserCache")
                context.close()
                context = launch()
                page = context.new_page()
                page.goto(origin, wait_until="domcontentloaded", timeout=90000)
                expect(page.locator(target).first).to_be_visible()
                expect(page.locator("#coverage-nav")).to_be_hidden()
                assert context.request.get(f"{origin}/api/session").json()["authenticated"]
                page.get_by_role("button", name="Sign out", exact=True).click()
                expect(page.locator("#auth-submit")).to_be_visible()
                context.close()
                context = launch()
                page = context.new_page()
                page.goto(origin, wait_until="domcontentloaded", timeout=90000)
                expect(page.locator("#auth-submit")).to_be_visible()
                assert context.request.get(f"{origin}/api/session").json()["authenticated"] is False
                print(
                    f"Passed: {engine_name} persistent cookie, cache clear, browser restart, logout"
                )
            finally:
                context.close()


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
        payments_enabled = health.json()["payments_enabled"]
        assert isinstance(payments_enabled, bool)
        assert payments_enabled is (args.environment == "production"), "Unexpected billing mode"
        assert health.json() == {
            "status": "ok",
            "version": VERSION,
            "payments_enabled": payments_enabled,
        }
        session = client.get("/api/session")
        session.raise_for_status()
        assert session.json()["environment"] == args.environment, (
            "Refusing a mismatched environment"
        )
        assert session.json()["email_delivery_enabled"] is False
        assert session.json()["payments_enabled"] is payments_enabled
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
        for path in (
            "/api/sources",
            "/api/capabilities",
            "/api/feedback",
            "/api/admin/feedback/users.csv",
            "/api/decision-cases/unknown",
            "/api/hunts/unknown/research",
        ):
            assert client.get(path).status_code == 401
        assert client.post("/api/search", json={}).status_code == 401
        assert client.get("/api/saved").status_code == 404
    print(
        "Passed: exact release identity, HTTPS, environment, billing mode, "
        "disabled mail, authentication"
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
                    expect(page.locator("#workspace")).to_be_visible()
                    registered = True
                    expect(page.locator("#coverage-nav")).to_be_hidden()
                    for endpoint in (
                        "/api/sources",
                        "/api/capabilities",
                        "/api/admin/accounts",
                        "/api/admin/feedback",
                        "/api/admin/feedback/responses",
                        "/api/admin/feedback/users.csv",
                    ):
                        assert context.request.get(f"{origin}{endpoint}").status == 403
                    page.locator('#main-nav [data-nav="feedback"]').click()
                    expect(page.locator("#feedback-admin")).to_be_hidden()
                    expect(page.locator("#feedback-admin")).to_be_empty()
                    expect(page.get_by_role("button", name="Export users CSV")).to_have_count(0)
                    if payments_enabled:
                        page.locator('#main-nav [data-nav="billing"]').click()
                        # Verify the unpaid customer's access boundary without creating a charge.
                        expect(page.locator("#billing-panel")).to_be_visible()
                        state = context.request.get(f"{origin}/api/session").json()
                        assert state["is_owner"] is False
                        assert state["billing"]["allowed"] is False
                        headers = {
                            "Origin": origin,
                            "X-LandWolf-Client": "web",
                            "X-CSRF-Token": state["csrf"],
                        }
                        assert (
                            context.request.post(
                                f"{origin}/api/search", headers=headers, data={}
                            ).status
                            == 402
                        )
                        assert context.request.get(f"{origin}/api/hunts").status == 200
                        assert (
                            context.request.get(f"{origin}/api/decision-cases/unknown").status
                            == 402
                        )
                        assert (
                            context.request.get(f"{origin}/api/hunts/unknown/research").status
                            == 402
                        )
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        page.screenshot(
                            path=str(output / f"membership-{engine}-{width}.png"), full_page=True
                        )
                        page.reload(wait_until="domcontentloaded")
                        expect(page.locator("#billing-panel")).to_be_visible()
                        expect(page.locator("#coverage-nav")).to_be_hidden()
                        page.get_by_role("button", name="Sign out", exact=True).click()
                        expect(page.locator("#auth-submit")).to_be_visible()
                        assert context.request.get(f"{origin}/api/sources").status == 401
                        assert not errors
                        print(
                            f"Passed: {engine} {width}px login, owner-only coverage, "
                            "paywall, logout"
                        )
                        continue
                    page.locator('#main-nav [data-nav="explore"]').click()
                    expect(page.locator(".property-card").first).to_be_visible()
                    if engine == "chromium" and width == 390:
                        state = context.request.get(f"{origin}/api/session").json()
                        headers = {
                            "Origin": origin,
                            "X-LandWolf-Client": "web",
                            "X-CSRF-Token": state["csrf"],
                        }
                        denied = context.request.post(f"{origin}/api/search", data={})
                        assert denied.status == 403
                        assert context.request.get(f"{origin}/api/sources").status == 403
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
                    expect(page.locator("#main-nav button:visible")).to_have_count(5)
                    page.screenshot(
                        path=str(output / f"explore-{engine}-{width}.png"), full_page=True
                    )

                    # The public signup must never silently enroll an investor or grant admin.
                    pilot = context.request.get(f"{origin}/api/feedback")
                    assert pilot.status == 200
                    assert pilot.json()["state"] == "none"
                    assert pilot.json()["access_allowed"] is True
                    for path in ("/api/admin/feedback", "/api/admin/feedback/responses"):
                        assert context.request.get(f"{origin}{path}").status == 403
                    page.locator('#main-nav [data-nav="feedback"]').click()
                    expect(page.locator("#feedback-content")).to_contain_text(
                        "Investor feedback program"
                    )
                    expect(page.locator("#feedback-admin")).to_be_hidden()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(
                        path=str(output / f"feedback-{engine}-{width}.png"), full_page=True
                    )
                    page.locator('#main-nav [data-nav="explore"]').click()

                    page.locator(".property-card").first.get_by_role(
                        "button", name="View property"
                    ).click()
                    expect(page.locator("#property-dialog .trust-panel")).to_be_visible()
                    research_workspace = page.locator("#decision-workspace")
                    expect(
                        research_workspace.get_by_role("button", name="Record research", exact=True)
                    ).to_be_visible()
                    research_workspace.get_by_label("Acquisition basis", exact=True).select_option(
                        "entered"
                    )
                    research_workspace.get_by_label("Acquisition assumption ($)", exact=True).fill(
                        "100000"
                    )
                    research_workspace.get_by_label("Known additional costs ($)", exact=True).fill(
                        "25000"
                    )
                    research_workspace.get_by_label("Unresolved work — low ($)", exact=True).fill(
                        "18000"
                    )
                    research_workspace.get_by_label("Unresolved work — high ($)", exact=True).fill(
                        "18000"
                    )
                    research_workspace.get_by_text(
                        "Investment assumptions and stress controls", exact=True
                    ).click()
                    research_workspace.get_by_label(
                        "Net exit proceeds after selling costs ($, optional)", exact=True
                    ).fill("160000")
                    research_workspace.get_by_role(
                        "button", name="Record research", exact=True
                    ).click()
                    expect(research_workspace.get_by_role("status")).to_contain_text(
                        "Research recorded"
                    )
                    expect(research_workspace.locator(".decision-output")).to_contain_text(
                        "$8,333.33"
                    )
                    expect(research_workspace.locator(".decision-output")).to_contain_text("11.89%")
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

                    expect(page.locator("#coverage-nav")).to_be_hidden()
                    assert context.request.get(f"{origin}/api/capabilities").status == 403
                    page.reload(wait_until="domcontentloaded")
                    expect(page.locator(".property-card").first).to_be_visible()
                    page.get_by_role("button", name="Sign out", exact=True).click()
                    expect(page.locator("#auth-submit")).to_be_visible()
                    assert not errors, "Browser raised an uncaught script error"
                    print(
                        f"Passed: {engine} {width}px authentication, evidence, handoff, "
                        "coverage restriction"
                    )
                finally:
                    context.close()
                    browser.close()
        check_persistence(playwright, origin, email, password, payments_enabled)
    print(
        "Passed: four hosted customer journeys, persistent sign-in "
        "and owner-only coverage boundary; "
        "one disposable non-cohort test account retained. "
        "Invitation, consent and due-date transitions are covered in isolated CI, not here."
    )


if __name__ == "__main__":
    main()
