"""Twin-guide UI, contextual walkthroughs, offline answers and session privacy."""

import re
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import browser_server as browser_server

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("browser_server", ["nationwide_owner"], indirect=True)
@pytest.mark.parametrize("engine_name", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [390, 1440])
def test_twin_wolves_help_on_every_screen(browser_server, engine_name, width):
    origin, _ = browser_server
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine_name).launch()
        context = browser.new_context(viewport={"width": width, "height": 950})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        launcher = page.locator("#wolf-chat-launcher")
        panel = page.locator("#wolf-chat-panel")
        log = page.locator("#wolf-chat-log")
        question = page.locator("#wolf-question")
        toolbar = page.locator(".site-header .wolf-chat-trigger")
        expect(toolbar).to_have_text("AI Chat with Romulus and Remus")
        expect(panel).to_be_hidden()

        def open_chat():
            launcher.click()
            expect(panel).to_be_visible()
            expect(question).to_be_focused()

        def ask(text):
            question.fill(text)
            panel.get_by_role("button", name="Ask the wolves", exact=True).click()

        def collapse():
            panel.get_by_role("button", name="Collapse Romulus and Remus chat").click()
            expect(panel).to_be_hidden()

        def login(email):
            page.get_by_label("Email address", exact=True).fill(email)
            page.get_by_label("Password", exact=True).fill("Test-only passphrase 847!")
            page.locator("#auth-submit").click()
            expect(page.locator("#workspace")).to_be_visible()

        toolbar.click()
        expect(question).to_be_focused()
        expect(panel).to_contain_text("prepared answers matched on your device")
        page.wait_for_function(
            "Array.from(document.querySelectorAll('.wolf-chat-heading img'))"
            ".every(image => image.complete && image.naturalWidth > 0)"
        )
        for image in panel.locator(".wolf-chat-heading img").all():
            assert image.evaluate("image => image.complete && image.naturalWidth > 0")
        ask("How do I save a Hunt?")
        expect(log).to_contain_text("Save Hunt & view matches")
        context.set_offline(True)
        ask("How do I reset my password?")
        expect(log).to_contain_text("Forgot password?")
        ask('PRIVATE-CHAT-FIXTURE <img src=x onerror="window.wolfXss=true">')
        expect(log).to_contain_text("I don’t have a reliable guide answer")
        assert page.evaluate("window.wolfXss === undefined")
        assert page.locator(".wolf-message-user img").count() == 0
        context.set_offline(False)
        question.press("Escape")
        expect(panel).to_be_hidden()
        expect(toolbar).to_be_focused()
        open_chat()
        expect(log).to_contain_text("PRIVATE-CHAT-FIXTURE")
        panel.get_by_role("button", name="Clear chat", exact=True).click()
        expect(log).not_to_contain_text("PRIVATE-CHAT-FIXTURE")
        panel.get_by_role("button", name="Ask the wolves", exact=True).click()
        expect(page.locator("#wolf-chat-status")).to_contain_text("Enter a question")
        collapse()

        # Native modal dialogs make the page inert: the helper must move into them.
        page.get_by_role("button", name="Forgot password?", exact=True).click()
        expect(page.locator("#account-dialog #wolf-assistant")).to_have_count(1)
        open_chat()
        expect(panel.locator(".wolf-context")).to_contain_text("account recovery")
        question.press("Escape")
        expect(page.locator("#account-dialog")).to_be_visible()
        page.locator("#close-account-action").click()
        expect(page.locator("body > #wolf-assistant")).to_have_count(1)

        page.get_by_role("button", name="Create account", exact=True).click()
        login("wolf-guide-fixture@example.com")
        open_chat()
        expect(log).not_to_contain_text("Enter a question")
        ask("How do I save a Hunt?")
        log.get_by_role("button", name="Walk me through it", exact=True).click()
        coach = page.locator("#wolf-coach")
        expect(panel).to_be_hidden()
        expect(coach).to_contain_text("Step 1 of 5")
        expect(page.locator('#hunt-form [name="state"]')).to_have_class(
            re.compile(r".*wolf-guide-highlight.*")
        )
        coach.get_by_role("button", name="Next", exact=True).click()
        expect(coach).to_contain_text("Step 2 of 5")
        assert page.request.get(f"{origin}/api/hunts").json()["hunts"] == []
        coach.get_by_role("button", name="End tour", exact=True).click()
        expect(page.locator(".wolf-guide-highlight")).to_have_count(0)
        expect(coach).to_be_hidden()

        for view in ("research", "feedback", "billing", "explore"):
            page.locator(f'#main-nav [data-nav="{view}"]').click()
            open_chat()
            expect(log).to_contain_text("Save Hunt & view matches")
            expect(
                panel.get_by_role("button", name="Export feedback users", exact=True)
            ).to_have_count(0)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            collapse()

        page.locator(".property-card").first.get_by_role("button", name="View property").click()
        expect(page.locator("#property-dialog #wolf-assistant")).to_have_count(1)
        open_chat()
        expect(panel.locator(".wolf-context")).to_contain_text("property details")
        ask("How can I run a deal scenario?")
        expect(log).to_contain_text("Run 10,000 scenarios")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        output = Path("test-results")
        output.mkdir(exist_ok=True)
        page.screenshot(path=str(output / f"wolf-chat-{engine_name}-{width}.png"), full_page=True)
        page.set_viewport_size({"width": width, "height": 400})
        expect(panel.get_by_role("button", name="Ask the wolves", exact=True)).to_be_in_viewport()
        expect(question).to_be_in_viewport()
        expect(
            panel.get_by_role("button", name="Collapse Romulus and Remus chat")
        ).to_be_in_viewport()
        page.set_viewport_size({"width": width, "height": 950})
        # Screen-reader controls, mobile layout and print output keep distinct responsibilities.
        box = panel.bounding_box()
        assert box and box["x"] >= 0 and box["x"] + box["width"] <= width + 1
        assert box["y"] >= 0 and box["y"] + box["height"] <= 951
        page.emulate_media(media="print")
        expect(page.locator("#wolf-assistant")).to_be_hidden()
        page.emulate_media(media="screen")
        question.press("Escape")
        expect(page.locator("#property-dialog")).to_be_visible()
        page.get_by_role("button", name="Close property details", exact=True).click()
        page.get_by_role("button", name="Sign out", exact=True).click()
        open_chat()
        expect(log).not_to_contain_text("Save Hunt & view matches")
        expect(log).not_to_contain_text("Run 10,000 scenarios")
        collapse()

        page.get_by_role("button", name="Sign in", exact=True).click()
        login("owner-fixture@example.com")
        page.locator('#main-nav [data-nav="feedback"]').click()
        open_chat()
        panel.get_by_role("button", name="Export feedback users", exact=True).click()
        expect(log).to_contain_text("The export is owner-only")
        for index in range(15):
            ask(f"Unknown fixture question {index}")
        assert log.locator(":scope > .wolf-turn").count() == 12
        collapse()
        page.get_by_role("button", name="Sign out", exact=True).click()
        open_chat()
        expect(log).not_to_contain_text("The export is owner-only")
        assert page.evaluate("localStorage.length === 0 && sessionStorage.length === 0")
        assert not errors
        browser.close()
