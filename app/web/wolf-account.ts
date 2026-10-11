/** Explicit, session-scoped forms inside chat; conversation text never becomes API input. */
export type AccountHelpAction = "reset" | "profile";
type Api = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
type Profile = {
  email: string;
  revision: number;
  full_name: string;
  company: string;
  phone: string;
  job_title: string;
  industry: string;
  contact_type: string;
  primary_use: string;
  use_details: string;
  marketing_opt_in: boolean;
};
type ProfileResponse = {
  profile: Profile;
  categories: Record<string, Record<string, string>>;
  consent_text: string;
  mail_enabled: boolean;
};
function el<K extends keyof HTMLElementTagNameMap>(tag: K, text = "") {
  const item = document.createElement(tag);
  item.textContent = text;
  return item;
}
function button(text: string, action: () => void) {
  const item = el("button", text);
  item.type = "button";
  item.className = "wolf-chip";
  item.addEventListener("click", action);
  return item;
}

export function setupWolfAccount(api: Api, session: () => string) {
  let generation = 0;
  let active: HTMLElement | undefined;
  function clear(): void {
    generation++;
    active?.remove();
    active = undefined;
  }
  async function open(
    action: AccountHelpAction,
    host: HTMLElement,
  ): Promise<void> {
    clear();
    const sequence = generation;
    const identity = session();
    const card = el("section");
    card.className = "wolf-account-card";
    card.setAttribute("aria-label", "Account help");
    active = card;
    host.append(card);
    const alive = () =>
      sequence === generation && identity === session() && card.isConnected;
    const heading = el(
      "h3",
      action === "reset" ? "Reset your password" : "Your CRM profile",
    );
    const status = el("p");
    status.setAttribute("role", "status");
    card.append(heading, status);
    const cancel = button("Close account form", clear);
    function failure(error: unknown): void {
      if (alive())
        status.textContent =
          error instanceof Error ? error.message : "Please retry.";
    }
    if (action === "profile" && !identity) {
      status.textContent =
        "Sign in to edit your own profile, then ask us again. If you cannot sign in, request a password reset email.";
      card.append(cancel);
      return;
    }
    status.textContent = "Loading account help…";
    let data: ProfileResponse | undefined;
    try {
      if (identity) data = await api<ProfileResponse>("/api/account/profile");
      if (!alive()) return;
    } catch (error) {
      failure(error);
      if (alive())
        card.append(
          cancel,
          button("Retry account help", () => void open(action, host)),
        );
      return;
    }
    status.textContent = "";
    const form = el("form");
    const fields = el("fieldset");
    const submit = el(
      "button",
      action === "reset" ? "Send password reset email" : "Review my changes",
    );
    submit.type = "submit";
    submit.className = "primary";
    const actions = el("div");
    actions.className = "wolf-account-actions";
    actions.append(submit, cancel);
    form.append(fields, actions);
    card.append(form);
    if (action === "reset") {
      const label = el("label", "Reset email address");
      const email = el("input");
      email.type = "email";
      email.autocomplete = "email";
      email.required = true;
      email.maxLength = 254;
      email.value = data?.profile.email ?? "";
      email.readOnly = Boolean(identity);
      label.append(email);
      fields.append(
        label,
        el(
          "p",
          "Open the single-use link in your account email to verify the request and choose a new password. It expires in 30 minutes. Never enter passwords or reset links in chat.",
        ),
      );
      if (data && !data.mail_enabled) {
        status.textContent =
          "Email recovery is not configured. Use Contact support in About & privacy.";
        submit.disabled = true;
      }
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!alive() || submit.disabled) return;
        submit.disabled = true;
        fields.disabled = true;
        try {
          const result = await api<{ message: string }>(
            identity ? "/api/account/password-reset" : "/api/auth/recovery",
            "POST",
            identity ? {} : { email: email.value },
          );
          if (alive()) status.textContent = result.message;
        } catch (error) {
          failure(error);
          if (alive()) {
            submit.disabled = false;
            fields.disabled = false;
          }
        }
      });
      return;
    }
    if (!data) return;
    const original = data.profile;
    const controls: Record<
      string,
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    > = {};
    const definitions = [
      ["full_name", "Full name", 120],
      ["company", "Company", 160],
      ["phone", "Phone", 32],
      ["job_title", "Job title", 120],
      ["industry", "Industry", 40],
      ["contact_type", "Role / interest", 40],
      ["primary_use", "How will you use LandWolf?", 40],
      ["use_details", "Goals and use details", 1000],
    ] as const;
    fields.append(
      el("p", `Login email: ${original.email}`),
      el(
        "p",
        "To change your login email, contact support. Review your details below. This form cannot delete your account or CRM history.",
      ),
    );
    for (const [key, title, limit] of definitions) {
      const label = el("label", title);
      let input: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
      const options = data.categories[key];
      if (options) {
        input = el("select");
        const empty = el(
          "option",
          key === "primary_use" ? "Choose your intended use" : "Not provided",
        );
        empty.value = "";
        input.append(empty);
        const choices = { ...options };
        if (original[key] && !choices[original[key]])
          choices[original[key]] = original[key];
        for (const [value, text] of Object.entries(choices)) {
          const option = el("option", text);
          option.value = value;
          input.append(option);
        }
      } else {
        input = key === "use_details" ? el("textarea") : el("input");
        input.maxLength = limit;
        if (input instanceof HTMLInputElement)
          input.type = key === "phone" ? "tel" : "text";
      }
      input.name = key;
      input.required = key === "full_name" || key === "primary_use";
      input.value = original[key];
      controls[key] = input;
      label.append(input);
      fields.append(label);
    }
    const consent = el("input");
    consent.type = "checkbox";
    consent.checked = original.marketing_opt_in;
    const consentLabel = el("label", data.consent_text);
    consentLabel.className = "wolf-account-consent";
    consentLabel.prepend(consent);
    fields.append(consentLabel);
    const review = el("div");
    review.className = "wolf-account-review";
    form.insertBefore(review, actions);
    let draft: Record<string, string | number | boolean> | undefined;
    const edit = button("Keep editing", () => {
      draft = undefined;
      fields.disabled = false;
      review.replaceChildren();
      edit.hidden = true;
      submit.textContent = "Review my changes";
    });
    edit.hidden = true;
    actions.insertBefore(edit, cancel);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!alive() || submit.disabled) return;
      if (!draft) {
        draft = {
          revision: original.revision,
          marketing_opt_in: consent.checked,
        };
        const list = el("ul");
        for (const [key, title] of definitions) {
          const control = controls[key];
          if (!control) {
            draft = undefined;
            status.textContent = "Reopen your profile and try again.";
            return;
          }
          const value = control.value.trim();
          draft[key] = value;
          if (value !== original[key]) {
            const choices = data?.categories[key];
            list.append(
              el(
                "li",
                `${title}: ${(choices?.[original[key]] ?? original[key]) || "Not provided"} → ${(choices?.[value] ?? value) || "Not provided"}`,
              ),
            );
          }
        }
        if (consent.checked !== original.marketing_opt_in)
          list.append(
            el(
              "li",
              `Product news and offers: ${consent.checked ? "Opt in" : "Opt out"}`,
            ),
          );
        if (!list.children.length) {
          draft = undefined;
          status.textContent = "No changes to save.";
          return;
        }
        status.textContent =
          "Review these changes, then save them to your CRM profile.";
        review.replaceChildren(list);
        fields.disabled = true;
        edit.hidden = false;
        submit.textContent = "Save my changes";
        return;
      }
      submit.disabled = true;
      edit.disabled = true;
      try {
        const result = await api<{ message: string }>(
          "/api/account/profile",
          "PATCH",
          draft,
        );
        if (!alive()) return;
        status.textContent = result.message;
        form.replaceChildren(
          button("Edit my profile again", () => void open("profile", host)),
          cancel,
        );
      } catch (error) {
        failure(error);
        if (alive()) {
          submit.disabled = false;
          edit.disabled = false;
        }
      }
    });
  }
  return { open, clear };
}
