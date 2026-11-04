"""Customer → same-origin API → durable service records → owner update → customer."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


def create_customer(page, email):
    page.get_by_role("button", name="SIGN IN", exact=True).click()
    page.get_by_role("button", name="CREATE ACCOUNT", exact=True).click()
    page.get_by_label("ACCOUNT NAME", exact=True).fill("Synthetic Portal Customer")
    page.get_by_label("ACCOUNT EMAIL", exact=True).fill(email)
    page.get_by_label("PASSWORD", exact=True).fill("Synthetic portal passphrase 847!")
    with page.expect_response("**/api/portal/register") as registered:
        page.locator("#auth-submit").click()
    assert registered.value.status == 201
    expect(page.locator("#account-state")).to_contain_text("SIGNED IN")


def create_project(page):
    page.locator('input[name="capability"][value="software"]').check()
    page.locator('input[name="extra"][value="fabrication"]').check()
    page.get_by_label("Project title", exact=True).fill("Synthetic workshop controller")
    page.get_by_label("Concept and requirements", exact=True).fill(
        "A Linux controller with a 3D printed enclosure. Customer-visible test requirements."
    )
    page.get_by_label("I authorize L91 LLC to contact me about this project.").check()
    with page.expect_response("**/api/portal/projects") as submitted:
        page.get_by_role("button", name="Submit project request").click()
    assert submitted.value.status == 201
    expect(page.locator("#workspace-panel")).to_be_visible()
    expect(
        page.locator("#project-detail").get_by_role("heading", name="Synthetic workshop controller")
    ).to_be_visible()


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_customer_workspace_isolation_reload_and_retry(browser_server, engine, width):
    origin, _ = browser_server
    with sync_playwright() as pw:
        browser = getattr(pw, engine).launch()
        context = browser.new_context(viewport={"width": width, "height": 950})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin + "/lupuspec")
        create_customer(page, "portal-browser-a@example.com")
        create_project(page)
        expect(page.locator(".work-row")).to_have_count(2)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        # An unavailable write preserves the customer's draft and can be retried.
        page.get_by_label("ADD A MESSAGE", exact=True).fill("Please use a matte grey enclosure.")
        page.route(
            "**/api/portal/projects/*/messages",
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"Synthetic temporary failure"}',
            ),
        )
        page.get_by_role("button", name="SEND MESSAGE").click()
        expect(page.locator(".reply-form")).to_contain_text("Synthetic temporary failure")
        expect(page.get_by_label("ADD A MESSAGE", exact=True)).to_have_value(
            "Please use a matte grey enclosure."
        )
        page.unroute("**/api/portal/projects/*/messages")
        page.get_by_role("button", name="SEND MESSAGE").click()
        expect(page.locator(".message")).to_contain_text("Please use a matte grey enclosure.")
        projects = page.request.get(origin + "/api/portal/projects").json()["projects"]
        project_id = projects[0]["id"]
        page.reload()
        expect(page.locator("#account-state")).to_contain_text("SIGNED IN")
        page.get_by_role("button", name="MY PROJECTS").click()
        page.get_by_role("button", name="Synthetic workshop controller", exact=True).click()
        expect(page.locator(".message")).to_contain_text("Please use a matte grey enclosure.")
        page.get_by_label("SERVICE", exact=True).select_option("studio")
        expect(page.locator("#project-list")).to_contain_text("NO MATCHING PROJECTS")
        page.get_by_label("SERVICE", exact=True).select_option("")
        Path("test-results").mkdir(exist_ok=True)
        page.screenshot(
            path=f"test-results/customer-workspace-{engine}-{width}.png", full_page=True
        )
        second = browser.new_context()
        other = second.new_page()
        other.goto(origin + "/lupuspec")
        create_customer(other, "portal-browser-b@example.com")
        other.get_by_role("button", name="MY PROJECTS").click()
        expect(other.locator("#project-list")).to_contain_text("NO PROJECTS YET")
        assert other.request.get(origin + "/api/portal/projects/" + project_id).status == 404
        assert other.request.get(origin + "/api/admin/finance").status == 403
        page.get_by_role("button", name="SIGN OUT", exact=True).click()
        expect(page.locator("#account-state")).to_contain_text("GUEST")
        assert page.locator("#project-detail").text_content() == ""
        assert page.locator("#project-list").text_content() == ""
        assert page.request.get(origin + "/api/portal/projects/" + project_id).status == 401
        assert errors == []
        browser.close()


@pytest.mark.parametrize("browser_server", ["finance_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_owner_customer_update_and_classified_finance(browser_server, engine):
    origin, _ = browser_server
    with sync_playwright() as pw:
        browser = getattr(pw, engine).launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(origin + "/lupuspec")
        create_customer(page, "portal-owner-journey@example.com")
        create_project(page)
        owner = browser.new_page(viewport={"width": 1440, "height": 1000})
        owner.goto(origin)
        owner.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        owner.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        with owner.expect_response("**/api/auth/login") as signed_in:
            owner.locator("#auth-submit").click()
        assert signed_in.value.status == 200
        expect(owner.locator(".property-card").first).to_be_visible()
        owner.locator("#crm-nav").click()
        owner.get_by_text("CUSTOMER WORKSPACE", exact=True).click()
        owner.get_by_label("PUBLISH TO CUSTOMER", exact=True).fill(
            "The enclosure dimensions are ready for your review."
        )
        owner.get_by_role("button", name="PUBLISH UPDATE", exact=True).click()
        expect(owner.locator("#crm-panel")).to_contain_text("TEAM: The enclosure dimensions")
        page.get_by_role("button", name="REFRESH", exact=True).click()
        page.get_by_role("button", name="Synthetic workshop controller", exact=True).click()
        expect(page.locator(".message")).to_contain_text("The enclosure dimensions are ready")
        owner.get_by_label("SOFTWARE", exact=True).select_option("approved")
        owner.get_by_label("SOFTWARE", exact=True).locator("..").locator("..").get_by_role(
            "button", name="SAVE WORK STATUS"
        ).click()
        owner.locator('details[data-work-status="approved"] summary').click()
        expect(owner.locator("#crm-panel")).to_contain_text("Factory connection is not configured")
        owner.locator("#finance-nav").click()
        owner.get_by_label("Capability", exact=True).select_option("software")
        owner.get_by_label("Customer / project work", exact=True).select_option(index=1)
        owner.get_by_label("Revenue or cost stream", exact=True).select_option("software.build")
        owner.get_by_label("Amount in USD", exact=True).fill("250.00")
        owner.get_by_label("Unique cash source reference", exact=True).fill(
            "manual.browser-receipt"
        )
        owner.get_by_role("button", name="Record LupuSpec entry").click()
        expect(
            owner.locator("#finance-panel").get_by_text("RECEIPTS · $250.00", exact=True)
        ).to_be_visible()
        expect(owner.locator("#finance-panel")).to_contain_text(
            "CUSTOMER · Synthetic Portal Customer"
        )
        expect(owner.locator("#finance-panel")).to_contain_text(
            "PROJECT · Synthetic workshop controller"
        )
        owner.get_by_text("LupuSpec recorded entries (1)", exact=True).click()
        expect(owner.locator(".finance-entry-id")).to_contain_text("ENTRY ID · ")
        assert page.request.get(origin + "/api/admin/finance").status == 403
        owner.set_viewport_size({"width": 390, "height": 950})
        assert owner.evaluate("document.documentElement.scrollWidth <= innerWidth")
        owner.set_viewport_size({"width": 1440, "height": 1000})
        Path("test-results").mkdir(exist_ok=True)
        owner.screenshot(path=f"test-results/customer-finance-{engine}.png", full_page=True)
        browser.close()
