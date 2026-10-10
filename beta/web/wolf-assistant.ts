import {
  answerHelp,
  availableTopics,
  MAX_QUESTION,
  suggestedTopics,
  SUPPORT_EMAIL,
  type HelpContext,
  type HelpTopic,
  type HelpView,
} from "./help-guide";
import { setupWolfAccount } from "./wolf-account";

type Bridge = {
  context: () => HelpContext;
  navigate: (view: HelpView) => Promise<boolean>;
  api: <T>(path: string, method?: string, body?: unknown) => Promise<T>;
  session: () => string;
};
const MAX_TURNS = 12;
function node<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  text = "",
  css = "",
): HTMLElementTagNameMap[K] {
  const result = document.createElement(tag);
  result.textContent = text;
  result.className = css;
  return result;
}
function button(
  text: string,
  action: () => void,
  css = "wolf-chip",
): HTMLButtonElement {
  const result = node("button", text, css);
  result.type = "button";
  result.addEventListener("click", action);
  return result;
}
function portrait(name: "Romulus" | "Remus"): HTMLImageElement {
  const img = node("img", "", "wolf-portrait");
  img.src = `/assets/${name.toLowerCase()}.svg`;
  img.alt = `${name}, the ${name === "Romulus" ? "black" : "white"} wolf`;
  img.width = img.height = 44;
  return img;
}
function twins(): HTMLElement {
  const pair = node("span", "", "wolf-twins");
  pair.append(portrait("Romulus"), portrait("Remus"));
  return pair;
}
function visible(element: HTMLElement): boolean {
  return (
    element.getClientRects().length > 0 &&
    !element.closest("[hidden]") &&
    getComputedStyle(element).visibility !== "hidden"
  );
}

export function setupWolfAssistant(bridge: Bridge) {
  const accountHelp = setupWolfAccount(bridge.api, bridge.session);
  const root = node("aside", "", "wolf-assistant");
  root.id = "wolf-assistant";
  root.setAttribute("aria-label", "Romulus and Remus app help");
  const panel = node("section", "", "wolf-chat-panel");
  panel.id = "wolf-chat-panel";
  panel.setAttribute("aria-labelledby", "wolf-chat-title");
  panel.hidden = true;
  panel.tabIndex = -1;
  const heading = node("header", "", "wolf-chat-heading");
  const titleBlock = node("div", "", "wolf-title-block");
  const title = node("h2", "Romulus & Remus");
  title.id = "wolf-chat-title";
  titleBlock.append(title, node("p", "Your LandWolf guides"));
  const close = button("⌄", () => toggle(false), "wolf-icon-button");
  close.setAttribute("aria-label", "Collapse Romulus and Remus chat");
  close.title = "Collapse chat";
  const clear = button(
    "↺",
    () => {
      reset();
      focusComposer();
    },
    "wolf-icon-button",
  );
  clear.setAttribute("aria-label", "Clear chat");
  clear.title = "Clear chat";
  const headingActions = node("div", "", "wolf-heading-actions");
  headingActions.append(clear, close);
  heading.append(twins(), titleBlock, headingActions);
  const info = node("details", "", "wolf-info");
  const infoTitle = node("summary", "Guide-based help · About & privacy");
  const disclosure = node(
    "p",
    "Guide-based help • prepared answers matched on your device. Messages stay in this tab and clear on sign-out or reload. Account forms securely read your own CRM profile; only confirmed changes and reset requests are sent to LandWolf.",
    "wolf-disclosure",
  );
  const support = node("a", "Contact support ↗", "wolf-support");
  support.href = `mailto:${SUPPORT_EMAIL}`;
  info.append(infoTitle, disclosure, support);
  const contextLabel = node("p", "", "wolf-context");
  const quick = node("div", "", "wolf-quick-topics wolf-suggestions");
  quick.setAttribute("aria-label", "Suggested help topics");
  const log = node("div", "", "wolf-chat-log");
  log.id = "wolf-chat-log";
  log.setAttribute("role", "log");
  log.setAttribute("aria-label", "Conversation with Romulus and Remus");
  log.setAttribute("aria-live", "polite");
  log.setAttribute("aria-relevant", "additions");
  log.tabIndex = 0;
  const form = node("form", "", "wolf-chat-form");
  const label = node("label", "Ask how to use LandWolf", "sr-only");
  label.htmlFor = "wolf-question";
  const input = node("textarea");
  input.id = "wolf-question";
  input.name = "question";
  input.rows = 1;
  input.maxLength = MAX_QUESTION;
  input.placeholder = "Ask Romulus & Remus…";
  input.autocomplete = "off";
  input.setAttribute("aria-describedby", "wolf-question-note wolf-chat-status");
  const note = node(
    "p",
    `Up to ${MAX_QUESTION} characters. Keep passwords and payment details out of chat.`,
    "sr-only",
  );
  note.id = "wolf-question-note";
  const status = node("p", "", "wolf-chat-status");
  status.id = "wolf-chat-status";
  status.setAttribute("role", "status");
  const send = node("button", "↑", "wolf-send");
  send.type = "submit";
  send.setAttribute("aria-label", "Ask the wolves");
  send.title = "Send question";
  const composer = node("div", "", "wolf-composer");
  composer.append(input, send);
  const hint = node(
    "p",
    "Private to this tab · App guidance",
    "wolf-composer-hint",
  );
  form.append(label, composer, note, status, hint);
  panel.append(heading, info, contextLabel, quick, log, form);
  const coach = node("section", "", "wolf-coach");
  coach.id = "wolf-coach";
  coach.setAttribute("aria-label", "Guided walkthrough");
  coach.hidden = true;
  const launcher = button(
    "",
    () => {
      opener = launcher;
      toggle(panel.hidden);
    },
    "wolf-launcher",
  );
  launcher.id = "wolf-chat-launcher";
  launcher.setAttribute("aria-label", "AI Chat with Romulus and Remus");
  launcher.setAttribute("aria-controls", panel.id);
  launcher.append(twins(), node("span", "Ask Romulus & Remus"));
  root.append(panel, coach, launcher);
  document.body.append(root);
  let expanded = false;
  let opener: HTMLElement = launcher;
  let previous: string | undefined;
  let lastContext = "";
  let generation = 0;
  let tour: { topic: HelpTopic; index: number } | undefined;
  let highlight: HTMLElement | undefined;
  let showingStep = false;
  const phone = matchMedia("(max-width: 639px)");
  const touch = matchMedia("(pointer: coarse)");
  const inertSiblings = new Map<HTMLElement, boolean>();
  function releaseBackground(): void {
    for (const [element, original] of inertSiblings) element.inert = original;
    inertSiblings.clear();
    document.documentElement.classList.remove("wolf-sheet-open");
  }
  function present(): void {
    releaseBackground();
    root.dataset.expanded = String(expanded);
    root.dataset.sheet = String(phone.matches);
    panel.setAttribute("role", phone.matches && expanded ? "dialog" : "region");
    if (phone.matches && expanded) {
      panel.setAttribute("aria-modal", "true");
      document.documentElement.classList.add("wolf-sheet-open");
      let branch: HTMLElement = root;
      while (branch.parentElement) {
        for (const sibling of branch.parentElement.children)
          if (sibling !== branch && sibling instanceof HTMLElement) {
            inertSiblings.set(sibling, sibling.inert);
            sibling.inert = true;
          }
        branch = branch.parentElement;
        if (branch === document.body) break;
      }
    } else panel.removeAttribute("aria-modal");
  }
  function focusComposer(): void {
    (phone.matches || touch.matches ? close : input).focus({
      preventScroll: true,
    });
  }
  function sizeInput(): void {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, root.dataset.compact === "true" ? 64 : 112)}px`;
  }
  input.addEventListener("input", sizeInput);

  function context(): HelpContext {
    return bridge.context();
  }
  function allowed(topic: HelpTopic): boolean {
    return availableTopics(context()).some((item) => item.id === topic.id);
  }
  function removeHighlight(): void {
    highlight?.classList.remove("wolf-guide-highlight");
    highlight = undefined;
  }
  function stopTour(): void {
    generation++;
    tour = undefined;
    showingStep = false;
    removeHighlight();
    coach.hidden = true;
    coach.replaceChildren();
  }
  function toggle(open: boolean): void {
    const hadFocus = panel.contains(document.activeElement);
    expanded = open;
    present();
    panel.hidden = !open;
    launcher.hidden = open;
    coach.hidden = open || !tour;
    for (const control of document.querySelectorAll<HTMLElement>(
      ".wolf-chat-trigger, #wolf-chat-launcher",
    ))
      control.setAttribute("aria-expanded", String(open));
    if (open) {
      updateContext();
      focusComposer();
      sizeInput();
    } else if (hadFocus) {
      const target =
        opener.isConnected &&
        visible(opener) &&
        !opener.closest("[inert]") &&
        !document.querySelector("dialog[open]")
          ? opener
          : launcher;
      target.focus({ preventScroll: true });
    }
  }
  function bubble(
    speaker: "Romulus" | "Remus" | "You",
    text: string,
    steps?: string[],
  ): HTMLElement {
    const item = node(
      "article",
      "",
      `wolf-message${speaker === "You" ? " wolf-message-user" : ""}`,
    );
    const author = node("div", "", "wolf-message-author");
    if (speaker !== "You") author.append(portrait(speaker));
    author.append(node("strong", speaker));
    item.append(author, node("p", text));
    if (steps) {
      const list = node("ol");
      for (const step of steps) list.append(node("li", step));
      item.append(list);
    }
    return item;
  }
  function welcome(): void {
    const turn = node("div", "", "wolf-turn");
    turn.append(
      bubble(
        "Romulus",
        "I’ll show you where to go and what to do. You can also ask me to reset your password or update your profile.",
      ),
      bubble(
        "Remus",
        "I’ll explain the details and things to check. For an account problem we can’t resolve, Contact support opens your email app.",
      ),
    );
    log.replaceChildren(turn);
  }
  function trim(): void {
    while (log.children.length > MAX_TURNS) log.firstElementChild?.remove();
    const latest = log.lastElementChild;
    if (latest)
      log.scrollTop +=
        latest.getBoundingClientRect().top -
        log.getBoundingClientRect().top -
        12;
  }
  function showTopic(topic: HelpTopic, turn?: HTMLElement): void {
    if (!allowed(topic)) {
      status.textContent = "That help topic is not available for this account.";
      return;
    }
    previous = topic.id;
    const group = turn ?? node("div", "", "wolf-turn");
    group.append(
      bubble("Romulus", topic.title, topic.steps),
      bubble("Remus", topic.tip),
    );
    const accountAction = topic.accountAction;
    if (accountAction)
      group.append(
        button(
          accountAction === "reset"
            ? "Request password reset"
            : "Review my profile",
          () => {
            void accountHelp.open(accountAction, group);
          },
        ),
      );
    if (topic.tour)
      group.append(
        button("Walk me through it", () => {
          if (!allowed(topic)) return;
          stopTour();
          tour = { topic, index: 0 };
          toggle(false);
          void showStep();
        }),
      );
    if (!turn) log.append(group);
    trim();
  }
  function choices(turn: HTMLElement, options: HelpTopic[]): void {
    const list = node("div", "", "wolf-quick-topics");
    for (const topic of options)
      list.append(
        button(topic.title, () => {
          if (list.dataset.chosen) return;
          list.dataset.chosen = "true";
          list.remove();
          showTopic(topic, turn);
        }),
      );
    turn.append(list);
  }
  function ask(): void {
    const question = input.value.trim();
    const answer = answerHelp(question, context(), previous);
    if (answer.kind === "invalid") {
      status.textContent = `Enter a question of 1–${MAX_QUESTION} characters.`;
      return;
    }
    status.textContent = "";
    const turn = node("div", "", "wolf-turn");
    turn.append(bubble("You", question));
    log.append(turn);
    input.value = "";
    if (answer.kind === "answer" && answer.topics[0])
      showTopic(answer.topics[0], turn);
    else {
      turn.append(
        bubble(
          "Romulus",
          answer.kind === "clarify"
            ? "Which of these do you mean?"
            : "I don’t have a reliable guide answer for that. Try one of these app topics, or contact support for an account-specific question.",
        ),
      );
      choices(turn, answer.topics);
    }
    trim();
    sizeInput();
    if (phone.matches || touch.matches) input.blur();
    else input.focus({ preventScroll: true });
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    ask();
  });
  input.addEventListener("keydown", (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.isComposing &&
      ((!phone.matches && !touch.matches) || event.ctrlKey || event.metaKey)
    ) {
      event.preventDefault();
      ask();
    }
  });

  async function showStep(): Promise<void> {
    const active = tour;
    const step = active?.topic.tour?.[active.index];
    if (!active || !step || !allowed(active.topic) || showingStep) return;
    showingStep = true;
    removeHighlight();
    const token = ++generation;
    coach.hidden = expanded;
    coach.replaceChildren(node("p", "Romulus is finding this control…"));
    let result = "";
    let timeout: ReturnType<typeof setTimeout> | undefined;
    try {
      const moved = await Promise.race([
        bridge.navigate(step.view),
        new Promise<boolean>((_, reject) => {
          timeout = setTimeout(
            () =>
              reject(
                new Error(
                  "The screen is taking longer than expected. Retry this step.",
                ),
              ),
            12000,
          );
        }),
      ]);
      if (token !== generation || tour !== active) return;
      if (!moved)
        result =
          step.view === "property"
            ? "Open a property first, then retry this step."
            : step.view === "auth"
              ? "Return to the sign-in screen for this step. If you are already signed in, choose a topic for your current screen."
              : "This screen requires sign-in or account access. Use Membership or Contact support, then retry.";
      else {
        const target = [
          ...document.querySelectorAll<HTMLElement>(step.selector),
        ].find(visible);
        if (target) {
          highlight = target;
          target.classList.add("wolf-guide-highlight");
          target.scrollIntoView({ block: "center", behavior: "instant" });
        } else
          result =
            "This control is not visible yet. Complete the instruction on this screen, then retry the step.";
      }
    } catch (error) {
      if (token === generation)
        result =
          error instanceof Error
            ? error.message
            : "Unable to open this step. Please retry.";
    } finally {
      clearTimeout(timeout);
      if (token === generation) showingStep = false;
    }
    if (token !== generation || tour !== active) return;
    const row = node("div", "", "wolf-coach-title");
    row.setAttribute("role", "status");
    row.append(
      portrait("Romulus"),
      node(
        "strong",
        `Step ${active.index + 1} of ${active.topic.tour?.length}: ${step.title}`,
      ),
    );
    const actions = node("div", "", "wolf-coach-actions");
    const back = button("Back", () => {
      if (tour && !showingStep && tour.index > 0) {
        tour.index--;
        void showStep();
      }
    });
    back.disabled = active.index === 0;
    const next = button(
      active.index + 1 === active.topic.tour?.length ? "Finish" : "Next",
      () => {
        if (!tour || showingStep) return;
        if (tour.index + 1 === tour.topic.tour?.length) {
          stopTour();
          return;
        }
        tour.index++;
        void showStep();
      },
    );
    actions.append(
      back,
      button("Retry step", () => void showStep()),
      next,
      button("End tour", stopTour),
    );
    const feedback = node("p", result, "wolf-tour-status");
    feedback.setAttribute("role", "status");
    coach.replaceChildren(row, node("p", step.detail), feedback, actions);
    coach.hidden = expanded;
  }
  function updateContext(): void {
    const current = context();
    const signature = JSON.stringify(current);
    if (signature === lastContext) return;
    lastContext = signature;
    contextLabel.textContent = `Help for ${{ auth: "sign-in", account: "account recovery", explore: "Explore properties", hunt: "Hunt", research: "Property research", property: "property details", feedback: "Feedback", billing: "Membership", sources: "Data coverage" }[current.view]}`;
    quick.replaceChildren(
      ...suggestedTopics(current).map((topic) =>
        button(topic.title, () => showTopic(topic)),
      ),
    );
    if (tour && !allowed(tour.topic)) stopTour();
  }
  function moveToActiveScreen(): void {
    const dialogs = [
      ...document.querySelectorAll<HTMLDialogElement>("dialog[open]"),
    ];
    const host = dialogs.at(-1) ?? document.body;
    if (root.parentElement !== host) {
      releaseBackground();
      host.append(root);
      present();
    }
    updateContext();
  }
  function reset(): void {
    accountHelp.clear();
    stopTour();
    previous = undefined;
    input.value = "";
    input.style.height = "";
    info.open = false;
    status.textContent = "";
    lastContext = "";
    welcome();
    updateContext();
  }
  for (const control of document.querySelectorAll<HTMLButtonElement>(
    ".wolf-chat-trigger",
  )) {
    control.setAttribute("aria-controls", panel.id);
    control.setAttribute("aria-expanded", "false");
    control.addEventListener("click", () => {
      opener = control;
      moveToActiveScreen();
      toggle(true);
    });
  }
  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key === "Tab" && expanded && phone.matches) {
        const controls = [
          ...panel.querySelectorAll<HTMLElement>(
            "button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, a, [tabindex='0']",
          ),
        ].filter(visible);
        const first = controls[0];
        const last = controls.at(-1);
        if (
          event.shiftKey &&
          (document.activeElement === first || document.activeElement === panel)
        ) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
      if (
        event.key === "Escape" &&
        expanded &&
        root.contains(document.activeElement)
      ) {
        event.preventDefault();
        event.stopPropagation();
        toggle(false);
      }
    },
    true,
  );
  // Modal dialogs make siblings inert; keep the same assistant inside the active top layer.
  const observer = new MutationObserver(moveToActiveScreen);
  for (const dialog of document.querySelectorAll("dialog"))
    observer.observe(dialog, { attributes: true, attributeFilter: ["open"] });
  function fitViewport(): void {
    const viewport = window.visualViewport;
    const height = viewport?.height ?? window.innerHeight;
    const covered = Math.max(
      0,
      window.innerHeight - height - (viewport?.offsetTop ?? 0),
    );
    root.style.setProperty("--wolf-visible-height", `${height}px`);
    root.style.setProperty(
      "--wolf-viewport-top",
      `${viewport?.offsetTop ?? 0}px`,
    );
    root.style.setProperty("--wolf-keyboard-bottom", `${covered + 12}px`);
    root.dataset.compact = String(height < 520);
    if (height < 520) info.open = false;
    sizeInput();
  }
  window.addEventListener("resize", fitViewport, { passive: true });
  window.visualViewport?.addEventListener("resize", fitViewport, {
    passive: true,
  });
  window.visualViewport?.addEventListener("scroll", fitViewport, {
    passive: true,
  });
  phone.addEventListener("change", () => {
    present();
    fitViewport();
  });
  present();
  fitViewport();
  welcome();
  updateContext();
  launcher.setAttribute("aria-expanded", "false");
  return {
    update: updateContext,
    clear(): void {
      reset();
      toggle(false);
    },
  };
}
