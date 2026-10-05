"""Real browser/API/database research journeys; only explicit synthetic fixtures."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_complete_decision_workflow(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        page = browser.new_page(viewport={"width": width, "height": 950})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Email address", exact=True).fill("research-browser@example.com")
        page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        page.locator("#auth-submit").click()
        expect(page.locator(".property-card")).to_have_count(2)
        page.locator('#main-nav [data-nav="hunt"]').click()
        page.locator('#hunt-form select[name="state"]').select_option("TX")
        page.locator('#hunt-form select[name="size"]').select_option("5-50")
        page.locator("#hunt-submit").click()
        hunt = page.locator("#hunt-results .decision-workspace")
        expect(hunt.get_by_role("button", name="Update Hunt research goal")).to_be_visible()
        hunt.get_by_label("Total project budget ($, optional)", exact=True).fill("300000")
        hunt.get_by_label("Specific use (optional)", exact=True).fill("One cabin")
        with page.expect_response(lambda response: "/research-goal" in response.url):
            hunt.get_by_role("button", name="Update Hunt research goal").click()
        expect(hunt.get_by_label("Total project budget ($, optional)", exact=True)).to_have_value(
            "300000"
        )

        for tract in ("99001", "99002"):
            page.locator(".hunt-result-card").filter(has_text=f"Test fixture {tract}").get_by_role(
                "button", name="View property", exact=True
            ).click()
            workspace = page.locator("#decision-workspace")
            expect(
                workspace.get_by_label("Total project budget ($, optional)", exact=True)
            ).to_have_value("300000")
            workspace.get_by_label("Known additional costs ($)", exact=True).fill("25000")
            workspace.get_by_label("Unresolved work — low ($)", exact=True).fill("18000")
            workspace.get_by_label("Unresolved work — high ($)", exact=True).fill("18000")
            workspace.get_by_text("Record evidence and answers", exact=True).click()
            workspace.get_by_label("Planning authority for shared questions", exact=True).fill(
                "Fixture county planning"
            )
            workspace.get_by_label(
                "I confirmed this planning authority has jurisdiction", exact=True
            ).check()
            if tract == "99001":
                workspace.get_by_text(
                    "Investment assumptions and stress controls", exact=True
                ).click()
                workspace.get_by_label(
                    "Net exit proceeds after selling costs ($, optional)", exact=True
                ).fill("160000")
                workspace.get_by_text("Pause this property and remember why", exact=True).click()
                workspace.get_by_label("Reason to pause", exact=True).select_option("budget")
                workspace.get_by_label("Pause note", exact=True).fill(
                    '<img src=x onerror="window.badResearch=true">'
                )
                # A failed request retains the customer's edits and offers a normal retry.
                page.route(
                    "**/api/decision-cases/glo-99001",
                    lambda route: route.fulfill(
                        status=503,
                        content_type="application/json",
                        body='{"detail":"Synthetic storage unavailable"}',
                    ),
                )
                workspace.get_by_role("button", name="Record research", exact=True).click()
                expect(workspace.get_by_role("status")).to_contain_text(
                    "Synthetic storage unavailable"
                )
                expect(
                    workspace.get_by_label("Known additional costs ($)", exact=True)
                ).to_have_value("25000")
                page.unroute("**/api/decision-cases/glo-99001")
            workspace.get_by_role("button", name="Record research", exact=True).click()
            expect(workspace.get_by_role("status")).to_contain_text("Research recorded")
            if tract == "99001":
                expect(workspace.locator(".decision-output")).to_contain_text("$8,333.33")
                expect(workspace.locator(".decision-output")).to_contain_text("11.89%")
                assert page.evaluate("window.badResearch === undefined")
            assert page.locator("#property-dialog").evaluate(
                "el => el.scrollWidth <= el.clientWidth"
            )
            page.locator("#close-detail").click()

        page.locator("#hunt-list").get_by_role("button", name="View matches", exact=True).click()
        expect(hunt.locator(".decision-cases article")).to_have_count(2)
        hunt.get_by_label("Property A", exact=True).select_option("glo-99001")
        hunt.get_by_label("Property B", exact=True).select_option("glo-99002")
        hunt.get_by_role("button", name="Explain the trade-off", exact=True).click()
        expect(hunt).to_contain_text("$100,000.00")
        expect(hunt).to_contain_text("Unresolved requirements remain blockers")
        hunt.get_by_text("Shared research questions", exact=True).click()
        expect(hunt).to_contain_text("Fixture county planning — Permitted use")
        expect(hunt).to_contain_text("2 properties")
        # Do not return the assigned function: Playwright would invoke it immediately.
        page.evaluate(
            "() => { window.print = () => { window.researchPrinted = "
            "document.querySelector('#decision-print').textContent; }; }"
        )
        hunt.get_by_role("button", name="Print shared research brief").click()
        assert "Fixture county planning" in page.evaluate("window.researchPrinted")
        assert "99001" in page.evaluate("window.researchPrinted")
        assert "99002" in page.evaluate("window.researchPrinted")
        assert page.locator("#decision-print").count() == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(
            path=f"test-results/decisions-hunt-{engine_name}-{width}.png", full_page=True
        )

        page.reload()
        expect(page.locator("#workspace")).to_be_visible()
        page.locator(".property-card").filter(has_text="Test fixture 99001").get_by_role(
            "button", name="View property 99001", exact=True
        ).click()
        workspace = page.locator("#decision-workspace")
        expect(workspace.get_by_label("Known additional costs ($)", exact=True)).to_have_value(
            "25000"
        )
        expect(workspace.locator(".decision-output")).to_contain_text("$8,333.33")
        workspace.get_by_label("Unresolved work — low ($)", exact=True).fill("5000")
        workspace.get_by_label("Unresolved work — high ($)", exact=True).fill("5000")
        workspace.get_by_role("button", name="Record research", exact=True).click()
        expect(workspace.get_by_role("status")).to_contain_text("Research recorded")
        expect(workspace.locator(".decision-output")).to_contain_text("That condition is now met")
        workspace.get_by_text("Research changes", exact=True).click()
        expect(workspace).to_contain_text("Other requirements still need attention")
        page.evaluate(
            "() => { window.print = () => { window.researchPrinted = "
            "document.querySelector('#decision-print').textContent; }; }"
        )
        workspace.get_by_role("button", name="Print displayed research").click()
        assert "One cabin" in page.evaluate("window.researchPrinted")
        assert "<img src=x" in page.evaluate("window.researchPrinted")
        assert page.evaluate("window.badResearch === undefined")
        page.screenshot(
            path=f"test-results/decisions-property-{engine_name}-{width}.png", full_page=True
        )
        page.locator("#close-detail").click()
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.locator("#decision-workspace")).to_be_empty()
        assert page.context.request.get(f"{origin}/api/decision-cases/glo-99001").status == 401
        assert errors == []
        browser.close()
