"""Verify both research editors on an exact hosted release using a smoke account.

The production smoke account needs an explicitly audited, temporary owner grant.
This tool never calls Stripe, changes entitlements, or reads another user's data.
Keyboard geometry and transport failures are explicitly emulated in the browser;
successful requests use the actual hosted backend and its database.
"""

import argparse
import re
import secrets
import time
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

from landwolf.version import VERSION

ORIGINS = {
    "staging": "https://landwolf-premium-staging.onrender.com",
    "production": "https://landwolf.ai",
}
TAG = "mobile-research-20261010-a867d1"


def require(condition: bool) -> None:
    if not condition:
        raise AssertionError("Hosted research acceptance check failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=tuple(ORIGINS), required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.commit):
        raise SystemExit("An exact deployment commit is required")
    origin = ORIGINS[args.environment]
    with httpx.Client(base_url=origin, timeout=60) as client:
        require(
            client.get("/api/version").json()
            == {"version": VERSION, "environment": args.environment, "commit": args.commit}
        )
        require(client.get("/api/health").json()["status"] == "ok")
    email = f"{args.environment}-smoke-{TAG}@example.com"
    password = secrets.token_urlsafe(32)
    output = Path("test-results/hosted-mobile-research") / args.environment
    output.mkdir(parents=True, exist_ok=True)
    registered = False
    expect.set_options(timeout=45000)
    with sync_playwright() as playwright:
        for engine in ("chromium", "webkit"):
            for width in (390, 834, 1440):
                mobile = width < 1100
                browser = getattr(playwright, engine).launch()
                context = browser.new_context(
                    viewport={"width": width, "height": 950}, has_touch=mobile
                )
                try:
                    page = context.new_page()
                    errors = []
                    page.on(
                        "pageerror", lambda error, sink=errors: sink.append(type(error).__name__)
                    )
                    page.add_init_script(
                        """const viewport = new EventTarget();
                        Object.assign(viewport, {height: 950, offsetTop: 0, scale: 1});
                        Object.defineProperty(window, 'visualViewport', {
                            configurable: true, value: viewport
                        });"""
                    )
                    page.goto(origin, wait_until="domcontentloaded", timeout=90000)
                    page.get_by_role(
                        "button", name="Sign in" if registered else "Create account", exact=True
                    ).click()
                    if not registered:
                        page.get_by_label("Full name", exact=True).fill(
                            "Release verification account"
                        )
                        page.get_by_label("How will you use LandWolf?", exact=True).select_option(
                            "research"
                        )
                    page.get_by_label("Email address", exact=True).fill(email)
                    page.get_by_label("Password", exact=True).fill(password)
                    page.locator("#auth-submit").click()
                    expect(page.locator("#workspace")).to_be_visible()
                    registered = True
                    deadline = time.monotonic() + 600
                    while True:
                        state = context.request.get(f"{origin}/api/session").json()
                        require(state["authenticated"] and (not state["is_owner"]))
                        if not state["payments_enabled"] or state["billing"]["allowed"]:
                            break
                        if time.monotonic() >= deadline:
                            raise RuntimeError("Temporary smoke-account grant was not observed")
                        time.sleep(5)
                    if args.environment == "production":
                        page.reload(wait_until="domcontentloaded")
                    expect(page.locator(".property-card").first).to_be_visible()
                    for endpoint in ("/api/admin/accounts", "/api/admin/feedback/users.csv"):
                        require(context.request.get(f"{origin}{endpoint}").status == 403)

                    def viewport(height: int, top: int = 0, scale: int = 1, page=page) -> None:
                        page.evaluate(
                            """geometry => {
                                Object.assign(window.visualViewport, geometry);
                                window.visualViewport.dispatchEvent(new Event('resize'));
                                window.visualViewport.dispatchEvent(new Event('scroll'));
                            }""",
                            {"height": height, "offsetTop": top, "scale": scale},
                        )
                        page.wait_for_function(
                            "() => document.documentElement.dataset.viewportFit === "
                            + ("'true'" if scale == 1 else "'false'")
                            + (
                                " && document.documentElement.style.getPropertyValue"
                                "('--app-viewport-height') === '" + str(height) + "px'"
                                if scale == 1
                                else ""
                            )
                        )

                    page.locator('#main-nav [data-nav="research"]').click()
                    page.locator("#research-new").click()
                    address = page.locator("#research-address")
                    if mobile:
                        expect(address).not_to_be_focused()
                    address.fill("1500 Marilla St, Dallas, TX 75201")
                    viewport(420, 60)
                    if mobile:
                        done = page.locator(
                            ".navigation-dock .keyboard-done"
                            if width == 390
                            else "body > .keyboard-done-floating"
                        )
                        expect(done).to_be_visible()
                        require(address.evaluate("el => getComputedStyle(el).fontSize") == "16px")
                        box = done.bounding_box()
                        require(box["y"] >= 60 and box["y"] + box["height"] <= 480)
                        done.tap()
                        expect(address).not_to_be_focused()
                        expect(address).to_have_value("1500 Marilla St, Dallas, TX 75201")
                    viewport(950)
                    address.fill("short")
                    page.locator("#research-submit").click()
                    expect(address).to_be_focused()
                    expect(address).to_have_value("short")
                    page.locator("#research-mode").select_option("coordinates")
                    page.locator("#research-latitude").fill("32.7767")
                    page.locator("#research-longitude").fill("-96.7970")
                    page.route(
                        "**/api/research",
                        lambda route: route.fulfill(
                            status=503,
                            content_type="application/json",
                            body='{"detail":"Emulated transport failure"}',
                        ),
                    )
                    page.locator("#research-submit").click()
                    expect(page.locator("#research-status")).to_contain_text(
                        "Emulated transport failure"
                    )
                    expect(page.locator("#research-latitude")).to_have_value("32.7767")
                    expect(page.locator("#research-longitude")).to_have_value("-96.7970")
                    page.unroute("**/api/research")
                    page.locator("#research-submit").click()
                    expect(page.locator(".research-source")).to_have_count(5, timeout=120000)
                    page.screenshot(path=str(output / f"property-{engine}-{width}.png"))
                    page.locator("#research-latitude").focus()
                    viewport(420, 60)
                    nav = page.locator('#main-nav [data-nav="explore"]')
                    nav.tap() if mobile else nav.click()
                    expect(page.locator("#research-latitude")).not_to_be_focused()
                    viewport(950)
                    page.locator(".property-card").first.get_by_role(
                        "button", name="View property"
                    ).click()
                    page.locator("#detail-actions").get_by_role(
                        "button", name="Decision research", exact=True
                    ).click()
                    workspace = page.locator("#decision-workspace")
                    cost = workspace.get_by_label("Known additional costs ($)", exact=True)
                    cost.fill("12345")
                    viewport(420, 60)
                    if mobile:
                        done = page.locator(".detail-topbar .keyboard-done")
                        expect(done).to_be_visible()
                        dialog = page.locator("#property-dialog").bounding_box()
                        require(dialog["y"] >= 60 and dialog["y"] + dialog["height"] <= 480)
                        require(page.locator(".detail-topbar").bounding_box()["height"] <= 90)
                        require(cost.evaluate("el => getComputedStyle(el).fontSize") == "16px")
                        page.screenshot(
                            path=str(output / f"decision-keyboard-{engine}-{width}.png")
                        )
                        done.tap()
                        expect(cost).not_to_be_focused()
                        expect(cost).to_have_value("12345")
                        viewport(420, 60, 2)
                    viewport(950)
                    page.route(
                        "**/api/decision-cases/*",
                        lambda route: route.fulfill(
                            status=503,
                            content_type="application/json",
                            body='{"detail":"Emulated storage failure"}',
                        ),
                    )
                    workspace.get_by_role("button", name="Record research", exact=True).click()
                    expect(workspace.get_by_role("status")).to_contain_text(
                        "Emulated storage failure"
                    )
                    expect(cost).to_have_value("12345")
                    page.unroute("**/api/decision-cases/*")
                    workspace.get_by_role("button", name="Record research", exact=True).click()
                    expect(workspace.get_by_role("status")).to_contain_text("Research recorded")
                    expect(cost).to_have_value("12345")
                    cost.focus()
                    viewport(420, 60)
                    page.locator("#close-detail").click()
                    expect(page.locator("#property-dialog")).not_to_be_visible()
                    expect(cost).not_to_be_focused()
                    viewport(950)
                    page.get_by_role("button", name="Sign out", exact=True).click()
                    expect(page.locator("#auth-submit")).to_be_visible()
                    require(
                        not context.request.get(f"{origin}/api/session").json()["authenticated"]
                    )
                    require(not errors)
                    print(
                        f"Passed: {args.environment} {engine} {width}px both research views, "
                        "Done, keyboard geometry, validation, failure/retry, preserved values, "
                        "navigation, privacy and logout",
                        flush=True,
                    )
                finally:
                    context.close()
                    browser.close()


if __name__ == "__main__":
    main()
