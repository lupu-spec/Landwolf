import { renderTrial, type TrialStatus } from "./trial";
/** Payment results are always checked on the server, never inferred from the URL. */
export type BillingStatus = {
  feedback_trial?: TrialStatus;
  enabled: boolean;
  livemode: boolean;
  allowed: boolean;
  reason: string;
  paid_until: number | null;
  subscription_status: string;
  cancel_at_period_end: boolean;
  has_customer: boolean;
  pilot_reserved: boolean;
  pilot_state: string;
  plans: {
    id: "monthly" | "annual";
    label: string;
    amount: number;
    currency: string;
  }[];
};
type API = <T>(path: string, method?: string, body?: unknown) => Promise<T>;

export function billingDestination(status: BillingStatus | null): string {
  return status?.reason === "pilot_invited" ||
    status?.reason === "feedback_required"
    ? "feedback"
    : "billing";
}

export function setupBilling(
  api: API,
  changed: (status: BillingStatus) => Promise<void>,
) {
  let status: BillingStatus | null = null;
  let generation = 0;
  let rendered = "";
  const panel = document.getElementById("billing-content");
  if (!panel) throw new Error("Missing billing panel");
  const content = panel;

  function text(tag: string, value: string): HTMLElement {
    const el = document.createElement(tag);
    el.textContent = value;
    return el;
  }
  function render(): void {
    const signature = JSON.stringify(status);
    if (signature === rendered) return;
    rendered = signature;
    content.replaceChildren();
    if (!status) {
      content.append(text("p", "Checking your access…"));
      return;
    }
    content.append(
      text(
        "h2",
        status.allowed ? "Your LandWolf access" : "Choose your LandWolf plan",
      ),
    );
    const messages: Record<string, string> = {
      owner:
        "Your owner account has complimentary access. No subscription is required.",
      complimentary:
        "Your account has owner-granted complimentary access. No subscription is required.",
      pilot:
        "Your three-month feedback pilot is active. No card is required and no automatic charge follows. See Feedback for your expiry and surveys.",
      pilot_invited:
        "Your pilot is reserved. Open Feedback to accept the invitation and starting survey. No card or subscription is required.",
      pilot_verification:
        "A marketing pilot invitation is reserved for this email. Verify your email using the account controls, or reply to your invitation so support can confirm and enroll your account. You do not need to pay.",
      feedback_required:
        "Your pilot feedback is overdue. Complete the survey in Feedback to restore the remaining pilot term without paying.",
      payments_disabled: "Subscriptions are not enabled in this environment.",
      subscription: "Your subscription is active.",
      feedback_trial:
        "Your feedback trial is active. Your dates and check-ins are below.",
      subscription_required:
        "Subscribe to unlock property searches, research, deal analysis and new Hunt matches. Existing saved Hunts and account support remain available.",
    };
    content.append(
      text("p", messages[status.reason] ?? "Review your account access below."),
    );
    if (status.paid_until) {
      const date = new Date(status.paid_until * 1000).toLocaleDateString();
      content.append(
        text(
          "p",
          status.cancel_at_period_end
            ? `Cancellation is scheduled. Access continues through ${date}.`
            : `Current subscription period ends ${date}.`,
        ),
      );
    }
    content.append(
      text(
        "p",
        "Coverage is partial public-source inventory, not every property or MLS listing. Deal results are hypothetical scenarios, not appraisals or investment advice.",
      ),
    );
    const message = text("p", "");
    message.setAttribute("role", "status");
    message.id = "billing-message";
    async function redirect(path: string, body?: unknown): Promise<void> {
      const ownGeneration = generation;
      try {
        const result = await api<{ url: string }>(path, "POST", body);
        if (generation !== ownGeneration) return;
        const url = new URL(result.url);
        const host = path.endsWith("portal")
          ? "billing.stripe.com"
          : "checkout.stripe.com";
        if (
          url.protocol !== "https:" ||
          url.hostname !== host ||
          url.username ||
          url.password ||
          url.port
        )
          throw new Error(
            "The payment link could not be verified. Contact support.",
          );
        window.location.assign(url.href);
      } catch (error) {
        message.textContent =
          error instanceof Error
            ? error.message
            : "Billing request failed. Please retry.";
      }
    }
    function button(
      label: string,
      action: () => Promise<void>,
    ): HTMLButtonElement {
      const el = document.createElement("button");
      el.type = "button";
      el.className = "button secondary";
      el.textContent = label;
      el.addEventListener("click", async () => {
        el.disabled = true;
        message.textContent = "Connecting securely…";
        try {
          await action();
        } catch (error) {
          message.textContent =
            error instanceof Error
              ? error.message
              : "Billing could not be refreshed. Please retry.";
        } finally {
          el.disabled = false;
        }
      });
      return el;
    }
    const trialGeneration = generation;
    renderTrial(
      content,
      status.feedback_trial,
      api,
      async () => {
        const next = await api<BillingStatus>(
          "/api/billing/refresh",
          "POST",
          {},
        );
        if (generation !== trialGeneration) return;
        status = next;
        render();
        await changed(next);
      },
      () => generation === trialGeneration,
    );
    if (
      status.enabled &&
      !status.allowed &&
      !["setup", "active", "notice", "converting", "blocked"].includes(
        status.feedback_trial?.state ?? "none",
      ) &&
      !["pilot_invited", "pilot_verification"].includes(status.reason)
    ) {
      content.append(
        text(
          "p",
          "Pick a plan below. You’ll review the total on Stripe before any payment is submitted.",
        ),
      );

      const plans = document.createElement("div");
      plans.className = "billing-plan-grid";
      let selectedPlan =
        status.plans.find((plan) => plan.id === "monthly") ?? status.plans[0];

      const planInputs: HTMLInputElement[] = [];
      for (const plan of status.plans) {
        const card = document.createElement("label");
        card.className = "billing-plan-card";

        const input = document.createElement("input");
        input.type = "radio";
        input.name = "billing-plan";
        input.value = plan.id;
        input.checked = plan.id === selectedPlan?.id;
        input.addEventListener("change", () => {
          selectedPlan = plan;
          for (const item of planInputs)
            item
              .closest(".billing-plan-card")
              ?.classList.toggle("selected", item.checked);
          checkout.textContent = `Continue to secure checkout — ${plan.label}`;
        });
        planInputs.push(input);

        const copy = document.createElement("span");
        copy.className = "billing-plan-copy";
        copy.append(
          text("strong", plan.id === "monthly" ? "Monthly" : "Annual"),
          text("span", plan.label),
        );
        if (plan.id === "annual") {
          const savings = text(
            "span",
            "Save $49 vs. paying monthly for a year",
          );
          savings.className = "billing-plan-note";
          copy.append(savings);
        }
        card.append(input, copy);
        plans.append(card);
      }
      planInputs
        .find((input) => input.checked)
        ?.closest(".billing-plan-card")
        ?.classList.add("selected");
      content.append(plans);

      const terms = document.createElement("label");
      terms.className = "billing-terms";
      const consent = document.createElement("input");
      consent.type = "checkbox";
      consent.id = "billing-consent";
      const termsCopy = document.createElement("span");
      termsCopy.textContent =
        "I agree to recurring billing. The selected plan renews automatically until I cancel. I can cancel from Manage billing and keep access through the paid period.";
      terms.append(consent, termsCopy);
      content.append(terms);

      const checkout = button(
        `Continue to secure checkout — ${selectedPlan?.label ?? ""}`,
        async () => {
          if (!consent.checked) {
            message.textContent =
              "Check the recurring billing box above to continue to Stripe.";
            consent.focus();
            return;
          }
          if (!selectedPlan) {
            message.textContent = "Choose a plan to continue.";
            return;
          }
          checkout.textContent = "Opening secure Stripe checkout…";
          await redirect("/api/billing/checkout", {
            plan: selectedPlan.id,
            accepted_recurring_terms: true,
          });
        },
      );
      checkout.className = "button primary billing-checkout";
      content.append(
        checkout,
        text(
          "p",
          "Secure checkout is handled by Stripe. Nothing is charged until you review and submit payment there.",
        ),
      );
    }
    if (status.enabled && status.has_customer)
      content.append(
        button("Manage billing", () => redirect("/api/billing/portal")),
      );
    content.append(
      button("Check payment status", async () => {
        const ownGeneration = generation;
        const next = await api<BillingStatus>("/api/billing/refresh", "POST");
        if (generation !== ownGeneration) return;
        status = next;
        render();
        await changed(next);
        const result = document.getElementById("billing-message");
        if (result)
          result.textContent = next.allowed
            ? "Your access is ready."
            : "No active paid access yet. A pending payment may take a moment; do not pay a second time.";
      }),
    );
    const support = document.createElement("a");
    support.href = "mailto:support.landwolf@gmail.com";
    support.textContent = "Contact LandWolf support";
    content.append(message, support);
  }
  return {
    get state() {
      return status;
    },
    set(value: BillingStatus): void {
      status = value;
      render();
    },
    async refresh(): Promise<BillingStatus | null> {
      const ownGeneration = generation;
      const next = await api<BillingStatus>("/api/billing/status");
      if (generation !== ownGeneration) return null;
      status = next;
      render();
      return next;
    },
    clear(): void {
      generation++;
      status = null;
      rendered = "";
      content.replaceChildren();
    },
  };
}
