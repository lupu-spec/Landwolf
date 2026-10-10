"""Responsive UI boundary; real billing decisions are exercised by API tests."""

import time
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as trial_server  # noqa: F401

from landwolf.trials import TERMS, TERMS_VERSION

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 820, 1440])
def test_trial_consent_feedback_and_cancel(trial_server, engine_name, width):  # noqa: F811
    origin, _ = trial_server
    now = int(time.time())
    trial = {
        "eligible": True,
        "email_verified": True,
        "terms_version": TERMS_VERSION,
        "terms": TERMS,
        "state": "none",
        "access_allowed": False,
        "started_at": None,
        "expires_at": None,
        "charge_at": None,
        "completed_days": [],
        "surveys": [],
    }
    membership = {
        "enabled": True,
        "livemode": True,
        "allowed": False,
        "reason": "subscription_required",
        "paid_until": None,
        "subscription_status": "none",
        "cancel_at_period_end": False,
        "has_customer": False,
        "pilot_reserved": False,
        "pilot_state": "none",
        "plans": [{"id": "monthly", "label": "$29 / month", "amount": 2900, "currency": "usd"}],
        "feedback_trial": trial,
    }
    requests = []
    pilot_invited = False
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 1000})

        def session_route(route):
            response = route.fetch()
            value = response.json()
            if value.get("authenticated"):
                value["billing"] = membership
            route.fulfill(response=response, json=value)

        def feedback_route(route):
            response = route.fetch()
            value = response.json()
            value["access_allowed"] = membership["allowed"]
            value["self_service_trial"] = trial
            if pilot_invited:
                value["state"] = "invited"
            route.fulfill(response=response, json=value)

        def checkout(route):
            requests.append(route.request.post_data_json)
            route.fulfill(status=503, json={"detail": "Synthetic Stripe outage"})

        def survey(route):
            body = route.request.post_data_json
            assert body["answers"]["usage"] == "not_used"
            trial["completed_days"] = [30]
            trial["surveys"][0]["complete"] = True
            trial["state"] = "active"
            trial["charge_at"] = None
            route.fulfill(json=trial)

        def cancel(route):
            trial["state"] = "cancelled"
            membership["allowed"] = False
            route.fulfill(json=trial)

        page.route("**/api/session", session_route)
        page.route("**/api/feedback", feedback_route)
        page.route("**/api/billing/status", lambda r: r.fulfill(json=membership))
        page.route("**/api/billing/refresh", lambda r: r.fulfill(json=membership))
        page.route("**/api/trial/checkout", checkout)
        page.route("**/api/trial/feedback", survey)
        page.route("**/api/trial/cancel", cancel)
        page.goto(origin)
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Full name", exact=True).fill("Trial UI fixture")
        page.get_by_label("How will you use LandWolf?", exact=True).select_option("research")
        page.get_by_label("Email address", exact=True).fill("trial-ui@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        card = page.locator("#billing-content .trial-card")
        start = card.get_by_role("button", name="Start feedback trial — $0 today", exact=True)
        start.click()
        expect(card.get_by_role("status")).to_contain_text("read and check")
        assert not requests
        card.get_by_label("I agree to the feedback trial billing terms").check()
        start.click()
        expect(card.get_by_role("status")).to_contain_text("Synthetic Stripe outage")
        assert requests == [{"terms_version": TERMS_VERSION, "accepted_recurring_terms": True}]
        trial.update(
            eligible=False,
            state="notice",
            started_at=now - 30 * 86400,
            expires_at=now + 60 * 86400,
            charge_at=now + 7 * 86400,
            surveys=[{"day": 30, "due_at": now, "opens_at": now - 7 * 86400, "complete": False}],
        )
        page.get_by_role("button", name="Check payment status", exact=True).click()
        expect(card).to_contain_text("$29/month billing begins")
        card.get_by_label("Have you used LandWolf?").select_option("not_used")
        card.get_by_label("What did you try or hope to do?").fill("Find my first property")
        card.get_by_label("What worked or got in the way? ‘Not used yet’ is fine.").fill(
            "Not used yet"
        )
        card.get_by_label("What would make LandWolf more useful? ‘No changes’ is fine.").fill(
            "No changes"
        )
        card.get_by_role("button", name="Send feedback", exact=True).click()
        expect(card).to_contain_text("Day 30: Completed")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(path=f"test-results/trial-{engine_name}-{width}.png")
        card.get_by_role("button", name="Cancel feedback trial", exact=True).click()
        expect(card).to_contain_text("has been cancelled")
        # A later direct owner invitation must remain usable despite trial history.
        pilot_invited = True
        page.get_by_role("button", name="Feedback", exact=True).click()
        expect(page.locator('input[name="accepted_terms"]')).to_be_visible()
        browser.close()
