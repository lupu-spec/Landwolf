/** Trial consent, cancellation and feedback always use server-owned state. */
export type TrialStatus = {
  eligible: boolean;
  email_verified: boolean;
  terms_version: string;
  terms: string;
  state: string;
  access_allowed: boolean;
  started_at: number | null;
  expires_at: number | null;
  charge_at: number | null;
  completed_days: number[];
  surveys: {
    day: number;
    due_at: number;
    opens_at: number;
    complete: boolean;
  }[];
};
type API = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
const date = (value: number) => new Date(value * 1000).toLocaleString();
function node<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  value = "",
): HTMLElementTagNameMap[K] {
  const result = document.createElement(tag);
  result.textContent = value;
  return result;
}
export function renderTrial(
  parent: HTMLElement,
  trial: TrialStatus | undefined,
  api: API,
  refresh: () => Promise<void>,
  isCurrent: () => boolean = () => true,
): void {
  if (!trial || (!trial.eligible && trial.state === "none")) return;
  const section = node("section");
  section.className = "trial-card";
  section.setAttribute("aria-label", "Feedback trial");
  section.append(node("h3", "Help shape LandWolf"));
  const message = node("p");
  message.setAttribute("role", "status");
  function button(
    label: string,
    action: () => Promise<void>,
  ): HTMLButtonElement {
    const result = node("button", label);
    result.type = "button";
    result.className = "button secondary";
    result.addEventListener("click", async () => {
      if (!isCurrent()) return;
      result.disabled = true;
      try {
        await action();
      } catch (error) {
        message.textContent =
          error instanceof Error
            ? error.message
            : "Please retry or contact support.";
      } finally {
        result.disabled = false;
      }
    });
    return result;
  }
  if (trial.eligible || trial.state === "setup") {
    section.append(
      node(
        "p",
        "Explore LandWolf for up to 90 days in exchange for short, honest feedback on days 30, 60 and 90. A payment method is required, but there is no charge to start.",
      ),
    );
    section.append(
      node(
        "p",
        "If feedback is missing, we’ll email a notice and give you at least seven days to complete it or cancel. Otherwise, your membership starts at $29/month. Complete all three check-ins and your trial ends without an automatic charge.",
      ),
    );
    const label = node("label");
    label.className = "billing-terms";
    const consent = node("input");
    consent.type = "checkbox";
    consent.setAttribute(
      "aria-label",
      "I agree to the feedback trial billing terms",
    );
    label.append(consent, node("span", trial.terms));
    section.append(label);
    section.append(
      button("Start feedback trial — $0 today", async () => {
        if (!consent.checked) {
          message.textContent =
            "Please read and check the trial billing agreement to continue.";
          consent.focus();
          return;
        }
        if (!trial.email_verified) {
          message.textContent =
            "Verify your email using the account controls first. We need to send your trial dates and billing notices.";
          return;
        }
        const response = await api<{ url: string }>(
          "/api/trial/checkout",
          "POST",
          {
            terms_version: trial.terms_version,
            accepted_recurring_terms: true,
          },
        );
        if (!isCurrent()) return;
        const url = new URL(response.url);
        if (
          url.protocol !== "https:" ||
          url.hostname !== "checkout.stripe.com" ||
          url.username ||
          url.password ||
          url.port
        )
          throw new Error("Unable to verify secure checkout.");
        window.location.assign(url.href);
      }),
    );
    if (!trial.email_verified)
      section.append(node("p", "Please verify your email before enrolling."));
  } else {
    const labels: Record<string, string> = {
      active:
        "Your feedback trial is active. Thanks for helping improve LandWolf.",
      notice:
        "A feedback check-in needs your attention. Complete it or cancel before the billing date below to avoid conversion.",
      converting:
        "Your trial conversion is being reconciled with Stripe. Check payment status before taking another billing action.",
      subscribed:
        "Your feedback trial converted to a monthly membership. Manage billing lets you view invoices and cancel renewal.",
      cancelled:
        "Your feedback trial has been cancelled. No new trial conversion will be initiated. If a conversion was already processing, check Manage billing for its result.",
      completed:
        "Thank you for all three check-ins. Your trial finished with no automatic charge. Choose a membership whenever you’re ready.",
      blocked:
        "Automatic trial conversion is on hold. Contact support or cancel the trial before choosing a membership.",
    };
    section.append(
      node("p", labels[trial.state] ?? "Review your trial details below."),
    );
    if (trial.expires_at)
      section.append(node("p", `Trial access ends ${date(trial.expires_at)}.`));
    if (trial.charge_at)
      section.append(
        node(
          "p",
          `Complete the missing feedback or cancel before ${date(trial.charge_at)}. Otherwise, $29/month billing begins on that date and renews until cancelled.`,
        ),
      );
    const list = node("ul");
    for (const survey of trial.surveys)
      list.append(
        node(
          "li",
          `Day ${survey.day}: ${survey.complete ? "Completed" : `due ${date(survey.due_at)}`}`,
        ),
      );
    section.append(list);
    const due = trial.surveys.find(
      (s) => !s.complete && s.opens_at * 1000 <= Date.now(),
    );
    if (due && ["active", "notice"].includes(trial.state)) {
      const form = node("form");
      form.className = "feedback-form";
      form.append(
        node("h4", `Day ${due.day} feedback`),
        node(
          "p",
          "A few sentences are enough. Honest criticism and ‘I haven’t used it yet’ both count. Please leave out sensitive personal or financial information.",
        ),
      );
      function field(title: string): HTMLTextAreaElement {
        const label = node("label", title);
        const input = node("textarea");
        input.maxLength = 1500;
        input.required = true;
        input.rows = 2;
        label.append(input);
        form.append(label);
        return input;
      }
      const usageLabel = node("label", "Have you used LandWolf?");
      const usage = node("select");
      for (const [value, label] of [
        ["", "Choose an answer"],
        ["not_used", "Not yet"],
        ["used", "Yes"],
      ] as const) {
        const option = node("option", label);
        option.value = value;
        usage.append(option);
      }
      usage.required = true;
      usageLabel.append(usage);
      form.append(usageLabel);
      const ratingLabel = node(
        "label",
        "How useful is it so far? (1–5; required if used)",
      );
      const rating = node("input");
      rating.type = "number";
      rating.min = "1";
      rating.max = "5";
      rating.step = "1";
      usage.addEventListener("change", () => {
        rating.required = usage.value === "used";
      });
      ratingLabel.append(rating);
      form.append(ratingLabel);
      const task = field("What did you try or hope to do?");
      const blocker = field(
        "What worked or got in the way? ‘Not used yet’ is fine.",
      );
      const improvement = field(
        "What would make LandWolf more useful? ‘No changes’ is fine.",
      );
      const submit = node("button", "Send feedback");
      submit.className = "button primary";
      submit.type = "submit";
      form.append(submit);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        submit.disabled = true;
        try {
          await api("/api/trial/feedback", "POST", {
            day: due.day,
            answers: {
              usage: usage.value,
              last_attempted_task: task.value,
              blocker: blocker.value,
              feature_request: improvement.value,
              feature_reason: improvement.value,
              no_changes: false,
              priority: null,
              value_rating: rating.value ? Number(rating.value) : null,
            },
          });
          if (isCurrent()) await refresh();
        } catch (error) {
          message.textContent =
            error instanceof Error
              ? error.message
              : "Feedback was not saved; please retry.";
        } finally {
          submit.disabled = false;
        }
      });
      section.append(form);
    }
  }
  if (
    ["setup", "active", "notice", "converting", "blocked"].includes(trial.state)
  )
    section.append(
      button("Cancel feedback trial", async () => {
        await api("/api/trial/cancel", "POST", {});
        if (isCurrent()) await refresh();
      }),
    );
  const terms = node("a", "Read or save the trial terms");
  terms.href = "/trial-terms";
  terms.target = "_blank";
  terms.rel = "noopener";
  section.append(message, terms);
  parent.append(section);
}
