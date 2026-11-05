"""Owner browser → authorization → durable request → factory transport → private result."""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server
from test_customer_portal_browser import create_customer, create_project

pytestmark = pytest.mark.browser


def refresh_factory(owner):
    """Wait for the actual async response, then retain the rendered-state assertions."""
    with owner.expect_response("**/api/admin/portal/work/*/factory") as refreshed:
        owner.get_by_role("button", name="REFRESH RUN", exact=True).click()
    assert refreshed.value.status == 200
    refreshed.value.json()


@pytest.mark.parametrize("browser_server", ["factory_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_approve_run_lost_acknowledgement_and_private_result(browser_server, engine, width):
    origin, _ = browser_server
    with sync_playwright() as pw:
        browser = getattr(pw, engine).launch()
        customer = browser.new_page()
        customer.goto(origin + "/lupuspec")
        create_customer(customer, "factory-customer@example.com")
        create_project(customer)
        project = customer.request.get(origin + "/api/portal/projects").json()["projects"][0]
        work = next(w for w in project["services"] if w["service"] == "software")
        path = "/api/admin/portal/work/" + work["id"] + "/factory"
        owner = browser.new_page(viewport={"width": width, "height": 950})
        owner.goto(origin)
        owner.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        owner.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        with owner.expect_response("**/api/search") as listings:
            owner.locator("#auth-submit").click()
        assert listings.value.status == 200
        expect(owner.locator(".property-card").first).to_be_visible()
        owner.locator("#crm-nav").click()
        owner.get_by_text("CUSTOMER WORKSPACE", exact=True).click()
        owner.get_by_label("SOFTWARE", exact=True).select_option("approved")
        owner.get_by_label("SOFTWARE", exact=True).locator("..").locator("..").get_by_role(
            "button", name="SAVE WORK STATUS"
        ).click()
        owner.locator('details[data-work-status="approved"] summary').click()
        expect(owner.locator("#crm-panel")).to_contain_text("Customer-visible test requirements")
        owner.get_by_label("ACCEPTANCE REQUIREMENTS", exact=True).fill("RETURN SYNTHETIC RESULT")
        owner.get_by_role("button", name="RUN REQUEST", exact=True).click()
        assert owner.request.get(origin + path).json()["dispatch"] is None
        owner.get_by_label(
            "I REVIEWED THIS REQUEST AND APPROVE RUNNING IT ON MY MACHINE.", exact=True
        ).check()
        owner.get_by_role("button", name="RUN REQUEST", exact=True).click()
        expect(owner.locator("#crm-panel")).to_contain_text(
            "Factory unavailable; retry this request"
        )
        refresh_factory(owner)
        expect(owner.locator("#crm-panel")).to_contain_text("COMPLETED")
        expect(owner.get_by_label("PROPOSED CODE", exact=True)).to_have_value(
            "--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-pass\n+print('fixture')\n"
        )
        before = owner.request.get(origin + path).json()
        refresh_factory(owner)
        assert owner.request.get(origin + path).json() == before
        assert customer.request.get(origin + path).status == 403
        assert (
            "factory"
            not in customer.request.get(origin + "/api/portal/projects/" + project["id"]).text()
        )
        assert owner.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()


@pytest.mark.parametrize("browser_server", ["factory_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_guest_inquiry_prepared_approved_and_result_persists(browser_server, engine, width):
    origin, _ = browser_server
    with sync_playwright() as pw:
        browser = getattr(pw, engine).launch()
        guest = browser.new_page()
        guest.goto(origin + "/lupuspec")
        assert guest.locator('input[name="capability"]:checked').count() == 0
        guest.get_by_text("Studio", exact=True).click()
        guest.get_by_label("Project title", exact=True).fill("Guest calculator request")
        guest.get_by_label("Concept and requirements", exact=True).fill(
            "Create a calculator webpage with a funny animated cartoon character."
        )
        guest.get_by_label("Full name", exact=True).fill("Guest Test Customer")
        guest.get_by_label("Email", exact=True).fill("guest-calculator@example.com")
        guest.get_by_label("I authorize L91 LLC to contact me about this project.").check()
        with guest.expect_response("**/api/lupuspec/requests") as submitted:
            guest.get_by_role("button", name="Submit project request").click()
        request_id = submitted.value.json()["request_id"]
        expect(guest.locator("#submission-status")).to_contain_text("WAITING FOR OWNER REVIEW")
        owner = browser.new_page(viewport={"width": width, "height": 950})
        owner.goto(origin)
        owner.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        owner.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        with owner.expect_response("**/api/search") as listings:
            owner.locator("#auth-submit").click()
        assert listings.value.status == 200
        expect(owner.locator(".property-card").first).to_be_visible()
        owner.locator("#crm-nav").click()
        owner.get_by_text("CUSTOMER WORKSPACE", exact=True).click()
        owner.get_by_label("WORK SERVICE", exact=True).select_option("software")
        owner.get_by_role("button", name="PREPARE WORK", exact=True).click()
        owner.get_by_label("SOFTWARE", exact=True).select_option("approved")
        owner.get_by_role("button", name="SAVE WORK STATUS", exact=True).click()
        owner.locator('details[data-work-status="approved"] summary').click()
        expect(owner.locator("#crm-panel")).to_contain_text("Create a calculator webpage")
        owner.get_by_label("ACCEPTANCE REQUIREMENTS", exact=True).fill("RETURN SYNTHETIC RESULT")
        owner.get_by_label(
            "I REVIEWED THIS REQUEST AND APPROVE RUNNING IT ON MY MACHINE.", exact=True
        ).check()
        owner.get_by_role("button", name="RUN REQUEST", exact=True).click()
        expect(owner.locator("#crm-panel")).to_contain_text(
            "Factory unavailable; retry this request"
        )
        refresh_factory(owner)
        expect(owner.locator("#crm-panel")).to_contain_text("RESULT FOR OWNER REVIEW")
        owner.reload()
        owner.locator("#crm-nav").click()
        owner.get_by_text("CUSTOMER WORKSPACE", exact=True).click()
        owner.locator('details[data-work-status="approved"] summary').click()
        expect(owner.locator("#crm-panel")).to_contain_text("COMPLETED")
        assert guest.request.get(origin + "/api/admin/portal/projects/" + request_id).status == 401
        assert owner.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()


@pytest.mark.parametrize("browser_server", ["factory_owner"], indirect=True)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_release_delivers_product_and_private_source(browser_server, engine, width):
    origin, _ = browser_server
    with sync_playwright() as pw:
        browser = getattr(pw, engine).launch()
        customer = browser.new_page()
        customer.goto(origin + "/lupuspec")
        create_customer(customer, "factory-customer@example.com")
        create_project(customer)
        project = customer.request.get(origin + "/api/portal/projects").json()["projects"][0]
        work = next(w for w in project["services"] if w["service"] == "software")
        path = "/api/admin/portal/work/" + work["id"] + "/factory"
        owner = browser.new_page(viewport={"width": width, "height": 950})
        owner.goto(origin)
        owner.get_by_label("Email address", exact=True).fill("owner-fixture@example.com")
        owner.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
        with owner.expect_response("**/api/search") as listings:
            owner.locator("#auth-submit").click()
        assert listings.value.status == 200
        expect(owner.locator(".property-card").first).to_be_visible()
        owner.locator("#crm-nav").click()
        owner.get_by_text("CUSTOMER WORKSPACE", exact=True).click()
        owner.get_by_label("SOFTWARE", exact=True).select_option("approved")
        owner.get_by_label("SOFTWARE", exact=True).locator("..").locator("..").get_by_role(
            "button", name="SAVE WORK STATUS"
        ).click()
        owner.locator('details[data-work-status="approved"] summary').click()
        expect(owner.locator("#crm-panel")).to_contain_text("Customer-visible test requirements")
        owner.get_by_label("ACCEPTANCE REQUIREMENTS", exact=True).fill("RETURN SYNTHETIC RELEASE")
        owner.get_by_role("button", name="RUN REQUEST", exact=True).click()
        assert owner.request.get(origin + path).json()["dispatch"] is None
        owner.get_by_label(
            "I REVIEWED THIS REQUEST AND APPROVE RUNNING IT ON MY MACHINE.", exact=True
        ).check()
        owner.get_by_role("button", name="RUN REQUEST", exact=True).click()
        expect(owner.locator("#crm-panel")).to_contain_text(
            "Factory unavailable; retry this request"
        )
        refresh_factory(owner)
        expect(owner.locator("#crm-panel")).to_contain_text("COMPLETED")
        owner.get_by_text("CUSTOMER WORKSPACE", exact=True).click()
        with owner.expect_response("**/api/admin/portal/projects/*") as workspace:
            owner.get_by_text("CUSTOMER WORKSPACE", exact=True).click()
        assert workspace.value.status == 200
        workspace.value.json()
        expect(owner.get_by_role("link", name="OPEN PRODUCT", exact=True)).to_have_attribute(
            "href", "https://fixture-calculator.pages.dev"
        )
        customer.reload()
        expect(customer.locator("#account-state")).to_contain_text("SIGNED IN")
        customer.get_by_role("button", name="MY PROJECTS", exact=True).click()
        customer.get_by_role("button", name="Synthetic workshop controller").click()
        expect(customer.get_by_role("link", name="OPEN PRODUCT", exact=True)).to_be_visible()
        with customer.expect_download() as download:
            customer.get_by_role("link", name="DOWNLOAD SOURCE", exact=True).click()
        assert download.value.suggested_filename == "source-1.0.0.zip"
        assert customer.request.get(origin + path).status == 403
        assert customer.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert owner.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()
