"""Bounded, explicit browser-to-staging save probe; no production or saved credentials."""

import json
import secrets
import uuid
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ORIGIN = "https://landwolf-premium-staging.onrender.com"


def main() -> None:
    reports = []
    with sync_playwright() as playwright:
        for engine in [playwright.chromium, playwright.webkit]:
            report = {"browser": engine.name, "viewport_width": 390}
            reports.append(report)
            browser = engine.launch()
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            page.set_default_timeout(30000)
            created_ids = set()
            errors = []
            page.on("pageerror", lambda error: errors.append(type(error).__name__))
            try:
                version = context.request.get(f"{ORIGIN}/api/version").json()
                report["version"] = version
                assert version["environment"] == "staging"
                page.goto(ORIGIN, wait_until="domcontentloaded", timeout=90000)
                page.get_by_role("button", name="Create account", exact=True).click()
                email = f"hunt-browser-qa-{uuid.uuid4().hex}@example.com"
                password = secrets.token_urlsafe(32)
                page.get_by_label("Email address", exact=True).fill(email)
                page.get_by_label("Password", exact=True).fill(password)
                page.locator("#auth-submit").click()
                page.locator('[data-nav="hunt"]').click()
                expect(page.locator("#hunt-submit")).to_be_visible()
                with page.expect_response(
                    lambda response: response.url == f"{ORIGIN}/api/hunts"
                    and response.request.method == "POST"
                ) as pending:
                    page.locator("#hunt-submit").click()
                response = pending.value
                report["post_status"] = response.status
                assert response.status == 201
                saved = response.json()
                created_ids.add(saved["id"])
                report["saved_id"] = saved["id"]
                expect(page.locator("#hunt-list article")).to_have_count(1)
                report["confirmation"] = page.locator("#hunt-status").inner_text()
                listed = context.request.get(f"{ORIGIN}/api/hunts")
                report["get_status"] = listed.status
                report["persisted"] = any(
                    row["id"] == saved["id"] for row in listed.json()["hunts"]
                )
                assert report["persisted"]
                page.reload(wait_until="domcontentloaded")
                page.locator('[data-nav="hunt"]').click()
                expect(page.locator("#hunt-list article")).to_have_count(1)
                report["visible_after_reload"] = True
                listed = context.request.get(f"{ORIGIN}/api/hunts").json()
                report["same_id_after_reload"] = listed["hunts"][0]["id"] == saved["id"]
                assert report["same_id_after_reload"]
                page.locator("#hunt-list").get_by_role("button", name="Edit").click()
                page.locator('#hunt-form [name="name"]').fill("QA edited Hunt")
                with page.expect_response(
                    lambda response: response.url == f"{ORIGIN}/api/hunts/{saved['id']}"
                    and response.request.method == "PATCH"
                ) as pending:
                    page.locator("#hunt-submit").click()
                report["patch_status"] = pending.value.status
                assert report["patch_status"] == 200
                expect(page.locator("#hunt-list")).to_contain_text("QA edited Hunt")
                page.reload(wait_until="domcontentloaded")
                page.locator('[data-nav="hunt"]').click()
                expect(page.locator("#hunt-list")).to_contain_text("QA edited Hunt")
                report["edit_persisted_after_reload"] = True
                Path("diagnostics").mkdir(exist_ok=True)
                page.screenshot(path=f"diagnostics/hunt-save-{engine.name}.png", full_page=True)
                report["page_error_count"] = len(errors)
                assert not errors
                report["passed"] = True
            except Exception as exc:
                report["error_type"] = type(exc).__name__
                report["passed"] = False
            finally:
                # Read the session token only in memory; never print auth JSON or headers.
                try:
                    session = context.request.get(f"{ORIGIN}/api/session").json()
                    for hunt_id in tuple(created_ids):
                        deleted = context.request.delete(
                            f"{ORIGIN}/api/hunts/{hunt_id}",
                            headers={
                                "Origin": ORIGIN,
                                "Content-Type": "application/json",
                                "X-LandWolf-Client": "web",
                                "X-CSRF-Token": session.get("csrf", ""),
                            },
                            data="{}",
                        )
                        if deleted.status == 200:
                            created_ids.remove(hunt_id)
                except Exception:
                    report["cleanup_error"] = True
                report["remaining_test_hunts"] = len(created_ids)
                context.close()
                browser.close()
    print(json.dumps(reports, indent=2))
    if any(not report.get("passed") or report["remaining_test_hunts"] for report in reports):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
