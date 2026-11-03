"""Owner browser → authorization → durable request → factory transport → private result."""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server
from test_customer_portal_browser import create_customer, create_project

pytestmark = pytest.mark.browser


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
        owner.locator("#auth-submit").click()
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
        owner.get_by_role("button", name="REFRESH RUN", exact=True).click()
        expect(owner.locator("#crm-panel")).to_contain_text("COMPLETED")
        expect(owner.get_by_label("PROPOSED CODE", exact=True)).to_have_value(
            "--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-pass\n+print('fixture')\n"
        )
        before = owner.request.get(origin + path).json()
        owner.get_by_role("button", name="REFRESH RUN", exact=True).click()
        assert owner.request.get(origin + path).json() == before
        assert customer.request.get(origin + path).status == 403
        assert (
            "factory"
            not in customer.request.get(origin + "/api/portal/projects/" + project["id"]).text()
        )
        assert owner.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()
