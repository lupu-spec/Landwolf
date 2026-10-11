/** Owner account controls. Never render credentials or persist private records locally. */
import type { Api, Catalog, Contact } from "./crm";

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, text = "") => {
  const result = document.createElement(tag);
  result.textContent = text;
  return result;
};
function field(label: string, value = "", type = "text", maximum = 160) {
  const wrap = el("label", label);
  const input = el("input");
  input.type = type;
  input.value = value;
  input.maxLength = maximum;
  wrap.append(input);
  return { wrap, input };
}
function choice(label: string, items: Record<string, string>, value: string) {
  const wrap = el("div");
  const caption = el("label", label);
  const input = el("select");
  input.id = `crm-admin-${crypto.randomUUID()}`;
  caption.htmlFor = input.id;
  for (const [id, text] of Object.entries(items)) {
    const option = el("option", text);
    option.value = id;
    input.append(option);
  }
  if (value && !(value in items)) {
    const option = el("option", value);
    option.value = value;
    input.append(option);
  }
  input.value = value;
  wrap.append(caption, input);
  return { wrap, input };
}
function profile(catalog: Catalog, c?: Contact) {
  const form = el("form");
  form.className = "crm-fields";
  const full_name = field("Contact full name", c?.full_name, "text", 120);
  const email = field("Contact email", c?.email, "email", 254);
  full_name.input.required = email.input.required = true;
  const company = field("Company", c?.company);
  const phone = field("Phone", c?.phone, "tel", 32);
  const job_title = field("Job title", c?.job_title, "text", 120);
  const industry = choice(
    "Contact industry",
    { "": "Not provided", ...catalog.categories.industries },
    c?.industry || "",
  );
  const contact_type = choice(
    "Contact role",
    { "": "Not provided", ...catalog.categories.contact_types },
    c?.contact_type || "",
  );
  const primary_use = choice(
    "Contact primary use",
    catalog.categories.uses,
    c?.primary_use || "other",
  );
  const goals = el("label", "Use details");
  const use_details = el("textarea");
  use_details.maxLength = 1000;
  use_details.value = c?.use_details || "";
  goals.append(use_details);
  const fields = {
    full_name,
    email,
    company,
    phone,
    job_title,
    industry,
    contact_type,
    primary_use,
  };
  form.append(...Object.values(fields).map((f) => f.wrap), goals);
  const values = () => ({
    ...Object.fromEntries(
      Object.entries(fields).map(([k, f]) => [k, f.input.value]),
    ),
    use_details: use_details.value,
  });
  return { form, values, email: email.input };
}
function submit(
  form: HTMLFormElement,
  label: string,
  action: () => Promise<void>,
  error: (e: unknown) => void,
) {
  const button = el("button", label);
  button.type = "submit";
  button.className = "button primary";
  form.append(button);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    button.disabled = true;
    try {
      await action();
    } catch (e) {
      error(e);
    } finally {
      button.disabled = false;
    }
  });
}
export function addContactForm(
  catalog: Catalog,
  api: Api,
  done: (id: string) => Promise<void>,
  error: (e: unknown) => void,
) {
  const container = el("details");
  container.className = "crm-admin-section";
  container.append(
    el("summary", "Add contact"),
    el(
      "p",
      "Create a CRM record before registration, then reserve trial or complimentary access from the contact. The person creates their own login.",
    ),
  );
  const p = profile(catalog);
  const project = choice(
    "Contact project",
    Object.fromEntries(catalog.projects.map((v) => [v.id, v.name])),
    "landwolf",
  );
  p.form.prepend(project.wrap);
  submit(
    p.form,
    "Create contact",
    async () => {
      const created = await api<Contact>("/api/admin/crm/contacts", "POST", {
        ...p.values(),
        project_id: project.input.value,
      });
      p.form.reset();
      container.open = false;
      await done(created.id);
    },
    error,
  );
  container.append(p.form);
  return container;
}
type AccountDetails = {
  supported: boolean;
  registered: boolean;
  owner?: boolean;
  id?: string;
  verified?: boolean;
  suspended?: boolean;
  active_sessions?: number;
  last_seen?: number | null;
  created_at?: number;
  complimentary?: boolean;
  expires_at?: number | null;
  subscription_status?: string;
  paid_until?: number | null;
  cancel_at_period_end?: boolean;
  billing_synced_at?: number | null;
  mail_enabled: boolean;
  reservation: {
    kind: string;
    state: string;
    days: number | null;
    expires_at: number | null;
  } | null;
  pilot?: { state: string; expires_at: number | null };
};
const date = (value?: number | null) =>
  value ? new Date(value * 1000).toLocaleString() : "None";

export async function renderAccountAdmin(
  container: HTMLElement,
  c: Contact,
  catalog: Catalog,
  api: Api,
  refresh: (message: string) => Promise<void>,
  error: (e: unknown) => void,
  current: () => boolean,
) {
  const data = await api<AccountDetails>(
    `/api/admin/crm/contacts/${c.id}/account`,
  );
  if (!current()) return;
  const edit = el("details");
  edit.className = "crm-admin-section";
  edit.append(el("summary", "Edit contact profile"));
  const p = profile(catalog, c);
  const reason = field("Reason for profile change", "", "text", 500);
  reason.input.required = true;
  reason.input.minLength = 5;
  p.form.append(reason.wrap);
  if (data.owner) p.email.disabled = true;
  edit.append(
    el(
      "p",
      "Changing a login email signs the user out, clears email verification and resets marketing consent. Billing history remains attached to the account.",
    ),
  );
  submit(
    p.form,
    "Save profile",
    async () => {
      if (
        p.email.value.trim().toLowerCase() !== c.email &&
        !window.confirm(
          "Change this email and sign out all sessions for this account?",
        )
      )
        return;
      await api(`/api/admin/crm/contacts/${c.id}/profile`, "PATCH", {
        ...p.values(),
        revision: c.revision,
        reason: reason.input.value,
      });
      await refresh("Profile saved.");
    },
    error,
  );
  edit.append(p.form);
  container.append(edit);
  if (!data.supported) {
    container.append(
      el(
        "p",
        "Account access for this contact is managed in its connected project.",
      ),
    );
    return;
  }
  const section = el("section");
  section.className = "crm-admin-section";
  section.append(el("h4", "Account administration"));
  const facts = el("dl");
  facts.className = "crm-facts";
  const summary: Record<string, string> = {
    "Account status": data.registered
      ? data.suspended
        ? "Suspended"
        : "Registered"
      : "Registration pending",
    "Email verified": data.verified ? "Yes" : "No",
    "Owner access": data.owner ? "Protected owner account" : "No",
    "Account created": date(data.created_at),
    "Last activity": date(data.last_seen),
    "Active sessions": String(data.active_sessions || 0),
    "Access grant": data.complimentary
      ? `Active · ${data.expires_at ? `expires ${date(data.expires_at)}` : "no expiration"}`
      : "None active",
    "Access reservation": data.reservation
      ? `${data.reservation.kind} · ${data.reservation.state}${data.reservation.days ? ` · ${data.reservation.days} days` : ""}`
      : "None",
    "Paid subscription": data.subscription_status || "none",
    "Paid access through": date(data.paid_until),
    "Cancellation scheduled": data.cancel_at_period_end ? "Yes" : "No",
    "Billing last synchronized": date(data.billing_synced_at),
    "Feedback pilot": data.pilot?.state || "none",
    "Pilot expires": date(data.pilot?.expires_at),
  };
  for (const [name, value] of Object.entries(summary))
    facts.append(el("dt", name), el("dd", value));
  section.append(facts);
  if (data.owner) {
    section.append(
      el("p", "Owner access cannot be suspended, revoked, or reassigned here."),
    );
    container.append(section);
    return;
  }
  section.append(
    el(
      "p",
      "Trial and complimentary grants control app access. Existing paid subscriptions continue billing until changed in Stripe. Suspension signs the user out and blocks sign-in.",
    ),
  );
  if (!data.registered)
    section.append(
      el(
        "p",
        "Reserved access starts after registration and email verification. If email delivery is unavailable, review the registered account and activate access here.",
      ),
    );
  const reasonAction = field("Reason for account action", "", "text", 500);
  reasonAction.input.required = true;
  reasonAction.input.minLength = 5;
  const days = field("Access duration (days)", "90", "number");
  days.input.min = "1";
  days.input.max = "365";
  days.input.step = "1";
  section.append(reasonAction.wrap, days.wrap);
  const actions = el("div");
  actions.className = "crm-actions";
  let busy = false;
  function action(
    label: string,
    path: string,
    payload: () => Record<string, unknown>,
    success: string,
    enabled = true,
    confirm = "",
    method = "POST",
    includeRevision = true,
  ) {
    const button = el("button", label);
    button.type = "button";
    button.className = "button secondary";
    button.disabled = !enabled;
    button.addEventListener("click", async () => {
      if (busy || !reasonAction.input.reportValidity()) return;
      if (confirm && !window.confirm(confirm)) return;
      busy = true;
      const buttons = Array.from(actions.querySelectorAll("button"));
      const previous = buttons.map((b) => b.disabled);
      buttons.forEach((b) => {
        b.disabled = true;
      });
      try {
        await api(path, method, {
          ...(includeRevision ? { revision: c.revision } : {}),
          reason: reasonAction.input.value,
          ...payload(),
        });
        if (current()) await refresh(success);
      } catch (e) {
        error(e);
      } finally {
        busy = false;
        buttons.forEach((b, i) => {
          b.disabled = previous[i]!;
        });
      }
    });
    actions.append(button);
  }
  const url = `/api/admin/crm/contacts/${c.id}`;
  action(
    data.registered ? "Activate trial" : "Reserve trial",
    url + "/access",
    () => {
      if (!days.input.reportValidity() || !days.input.value)
        throw new Error("Enter a duration from 1 to 365 days.");
      return { action: "trial", days: Number(days.input.value) };
    },
    data.registered
      ? "Trial activated."
      : "Trial reserved. Registration and email verification are pending.",
    true,
    "Apply this trial? Any existing complimentary grant will be replaced.",
  );
  action(
    data.registered
      ? "Grant complimentary access"
      : "Reserve complimentary access",
    url + "/access",
    () => ({ action: "complimentary" }),
    "Complimentary access updated.",
    true,
    "Grant complimentary access without an expiration? Any current trial grant will be replaced.",
  );
  action(
    "Revoke trial / complimentary access",
    url + "/access",
    () => ({ action: "revoke" }),
    "Trial and complimentary access revoked.",
    !!data.complimentary || data.reservation?.state === "reserved",
    "Revoke this grant? Access will depend on any remaining subscription or feedback pilot.",
  );
  if (data.registered) {
    action(
      data.suspended ? "Restore account" : "Suspend account",
      url + "/status",
      () => ({ suspended: !data.suspended }),
      "Account status updated.",
      true,
      data.suspended
        ? "Restore sign-in for this account?"
        : "Suspend this account and sign out all its sessions? Paid billing will continue.",
    );
    action(
      "Sign out all sessions",
      url + "/sessions",
      () => ({}),
      "All sessions signed out.",
      true,
      "Sign this user out on every device?",
    );
    action(
      "Send password reset",
      url + "/email-action",
      () => ({ purpose: "reset" }),
      "Password reset requested.",
      data.mail_enabled && !data.suspended,
    );
    action(
      "Send email verification",
      url + "/email-action",
      () => ({ purpose: "verify" }),
      "Email verification requested.",
      data.mail_enabled && !data.suspended,
    );
    const pilotUrl = `/api/admin/accounts/${encodeURIComponent(data.id!)}/feedback-pilot`;
    action(
      "Invite to feedback pilot",
      pilotUrl,
      () => ({}),
      "Feedback pilot invitation ready in the user's account.",
      !data.complimentary && data.pilot?.state === "none",
      "Invite this account to the three-month feedback pilot? The user must accept its terms and baseline survey.",
      "POST",
      false,
    );
    action(
      "Revoke feedback pilot",
      pilotUrl,
      () => ({}),
      "Feedback pilot revoked.",
      !!data.pilot &&
        !["none", "revoked", "expired"].includes(data.pilot.state),
      "Revoke this feedback pilot? Other paid or complimentary access will remain.",
      "DELETE",
      false,
    );
    if (!data.mail_enabled)
      section.append(
        el(
          "p",
          "Email delivery is not configured. Password reset and verification emails are unavailable.",
        ),
      );
  }
  section.append(actions);
  container.append(section);
}
