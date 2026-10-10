/** Owner-only CRM. Personal records live in the server, never local browser storage. */
import { addContactForm, renderAccountAdmin } from "./crm-admin";
import { renderStatistics, type Statistics } from "./crm-reporting";

export type Api = <T>(
  path: string,
  method?: string,
  body?: unknown,
) => Promise<T>;
export type Contact = {
  id: string;
  project_id: string;
  email: string;
  full_name: string;
  company: string;
  phone: string;
  job_title: string;
  industry: string;
  contact_type: string;
  primary_use: string;
  use_details: string;
  lifecycle: string;
  source: string;
  marketing_opt_in: boolean;
  consent_version: string | null;
  consent_recorded_at: number | null;
  tags: string[];
  follow_up_on: string;
  revision: number;
  created_at: number;
  account_category: string;
  membership: string;
  billing_synced_at: number | null;
};
type Project = { id: string; name: string; connected: boolean };
export type Catalog = {
  projects: Project[];
  categories: Record<
    | "industries"
    | "uses"
    | "stages"
    | "contact_types"
    | "account_categories"
    | "memberships",
    Record<string, string>
  >;
};
const node = <K extends keyof HTMLElementTagNameMap>(tag: K, text = "") => {
  const el = document.createElement(tag);
  el.textContent = text;
  return el;
};
function selectField(
  label: string,
  choices: Record<string, string>,
  value = "",
) {
  const wrap = node("div");
  wrap.className = "crm-field";
  const caption = node("label", label);
  const select = node("select");
  select.id = `crm-${crypto.randomUUID()}`;
  caption.htmlFor = select.id;
  for (const [key, text] of Object.entries(choices)) {
    const option = node("option", text);
    option.value = key;
    select.append(option);
  }
  select.value = value;
  wrap.append(caption, select);
  return { wrap, input: select };
}
function inputField(label: string, value = "", type = "text") {
  const wrap = node("label", label);
  const input = node("input");
  input.type = type;
  input.value = value;
  wrap.append(input);
  return { wrap, input };
}
export function setupCRM(api: Api) {
  const panel = document.getElementById("crm-panel")!;
  let sequence = 0;
  let active = false;
  let downloadController: AbortController | undefined;
  let catalog: Catalog;
  let page = 1;
  let selected = "";
  let contactOpener: HTMLButtonElement | undefined;
  let filters = {
    project_id: "",
    q: "",
    lifecycle: "",
    industry: "",
    primary_use: "",
    account_category: "people",
    membership: "",
  };
  const status = node("p");
  status.setAttribute("role", "status");
  const list = node("div");
  list.className = "crm-list";
  const detail = node("section");
  detail.className = "crm-detail";
  const controls = node("div");
  const statistics = node("section");
  statistics.className = "crm-statistics";
  function clear() {
    downloadController?.abort();
    downloadController = undefined;
    active = false;
    sequence++;
    panel.replaceChildren();
    list.replaceChildren();
    detail.replaceChildren();
    controls.replaceChildren();
    statistics.replaceChildren();
    selected = "";
    contactOpener = undefined;
    page = 1;
    filters = {
      project_id: "",
      q: "",
      lifecycle: "",
      industry: "",
      primary_use: "",
      account_category: "people",
      membership: "",
    };
  }
  function message(error: unknown) {
    if (active)
      status.textContent =
        error instanceof Error
          ? error.message
          : "Unable to load CRM. Please retry.";
  }
  function button(text: string, action: () => Promise<void> | void) {
    const button = node("button", text);
    button.type = "button";
    button.className = "button secondary";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        await action();
      } catch (error) {
        message(error);
      } finally {
        button.disabled = false;
      }
    });
    return button;
  }
  function focusDetail(heading: HTMLElement) {
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
    heading.scrollIntoView({ block: "start", behavior: "instant" });
  }
  function backToContacts() {
    selected = "";
    detail.replaceChildren();
    const target = contactOpener?.isConnected
      ? contactOpener
      : list.querySelector("button");
    target?.focus({ preventScroll: true });
    target?.scrollIntoView({ block: "center", behavior: "instant" });
  }
  async function showContact(id: string) {
    selected = id;
    detail.replaceChildren();
    const stamp = sequence;
    const heading = node("h3", "Loading contact…");
    detail.append(heading, button("Back to contacts", backToContacts));
    focusDetail(heading);
    let data: {
      contact: Contact;
      activities: { kind: string; text: string; created_at: number }[];
    };
    try {
      data = await api<typeof data>(
        `/api/admin/crm/contacts/${encodeURIComponent(id)}`,
      );
    } catch (error) {
      if (!active || stamp !== sequence || selected !== id) return;
      heading.textContent = "Unable to open contact";
      detail.append(
        node("p", "Please retry or return to the contact list."),
        button("Retry opening contact", () => showContact(id)),
      );
      message(error);
      return;
    }
    if (!active || stamp !== sequence || selected !== id) return;
    const c = data.contact;
    heading.textContent = c.full_name || c.email;
    detail.append(node("p", c.email));
    const fields = node("dl");
    fields.className = "crm-facts";
    for (const [label, value] of Object.entries({
      Project:
        catalog.projects.find((p) => p.id === c.project_id)?.name ||
        c.project_id,
      Company: c.company,
      Phone: c.phone,
      "Job title": c.job_title,
      Industry: catalog.categories.industries[c.industry] || c.industry,
      "Contact type":
        catalog.categories.contact_types[c.contact_type] || c.contact_type,
      "Primary use": catalog.categories.uses[c.primary_use] || c.primary_use,
      "Use details": c.use_details,
      Source: c.source,
      "Account category":
        catalog.categories.account_categories[c.account_category] ||
        c.account_category,
      Membership: catalog.categories.memberships[c.membership] || c.membership,
      "Added to CRM": new Date(c.created_at * 1000).toLocaleDateString(),
      "Email marketing": c.marketing_opt_in ? "Opted in" : "Not opted in",
      "Consent wording": c.consent_version || "Not collected",
    })) {
      fields.append(node("dt", label), node("dd", value || "Not provided"));
    }
    const administration = node("div");
    detail.append(administration, fields);
    void renderAccountAdmin(
      administration,
      c,
      catalog,
      api,
      async (text) => {
        if (!active || stamp !== sequence || selected !== c.id) return;
        await load();
        if (!active) return;
        await showContact(c.id);
        status.textContent = text;
      },
      message,
      () => active && stamp === sequence && selected === c.id,
    ).catch(message);
    const form = node("form");
    form.className = "crm-fields";
    const stage = selectField(
      "Lifecycle stage",
      catalog.categories.stages,
      c.lifecycle,
    );
    const tags = inputField("Tags (comma separated)", c.tags.join(", "));
    tags.input.maxLength = 490;
    const due = inputField("Follow-up date", c.follow_up_on, "date");
    const save = node("button", "Save contact");
    save.type = "submit";
    save.className = "button primary";
    form.append(stage.wrap, tags.wrap, due.wrap, save);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      save.disabled = true;
      try {
        await api(`/api/admin/crm/contacts/${c.id}`, "PATCH", {
          revision: c.revision,
          lifecycle: stage.input.value,
          tags: tags.input.value
            .split(",")
            .map((v) => v.trim())
            .filter(Boolean),
          follow_up_on: due.input.value,
        });
        if (active && sequence === stamp && selected === c.id) {
          await load();
          if (!active) return;
          await showContact(c.id);
          status.textContent = "Contact saved.";
        }
      } catch (e) {
        message(e);
      } finally {
        save.disabled = false;
      }
    });
    detail.append(form);
    if (c.marketing_opt_in)
      detail.append(
        button("Mark email unsubscribed", async () => {
          await api(`/api/admin/crm/contacts/${c.id}/unsubscribe`, "POST");
          if (active && sequence === stamp) await showContact(c.id);
        }),
      );
    const notes = node("form");
    const label = node("label", "Add a follow-up note");
    const text = node("textarea");
    text.maxLength = 2000;
    text.required = true;
    label.append(text);
    const add = node("button", "Add note");
    add.type = "submit";
    add.className = "button secondary";
    notes.append(label, add);
    notes.addEventListener("submit", async (e) => {
      e.preventDefault();
      add.disabled = true;
      try {
        await api(`/api/admin/crm/contacts/${c.id}/notes`, "POST", {
          text: text.value,
        });
        if (active && stamp === sequence) await showContact(c.id);
      } catch (e) {
        message(e);
      } finally {
        add.disabled = false;
      }
    });
    detail.append(notes, node("h4", "Recent activity"));
    for (const a of data.activities)
      detail.append(
        node(
          "p",
          `${new Date(a.created_at * 1000).toLocaleString()} · ${a.kind.replaceAll("_", " ")}${a.text ? `: ${a.text}` : ""}`,
        ),
      );
    focusDetail(heading);
  }
  async function load() {
    const stamp = ++sequence;
    selected = "";
    detail.replaceChildren();
    list.replaceChildren();
    statistics.replaceChildren();
    status.textContent = "Loading contacts…";
    const params = new URLSearchParams({ ...filters, page: String(page) });
    const result = await api<{
      contacts: Contact[];
      total: number;
      statistics: Statistics;
    }>(`/api/admin/crm/contacts?${params}`);
    if (!active || stamp !== sequence) return;
    renderStatistics(
      statistics,
      result.statistics,
      catalog.categories.memberships,
      (category, membership) => {
        filters.account_category = category;
        filters.membership = membership;
        page = 1;
        renderControls();
        void load().catch(message);
      },
    );
    status.textContent = `${result.total} contacts · Page ${page} of ${Math.max(1, Math.ceil(result.total / 50))}`;
    if (!result.contacts.length)
      list.append(node("p", "No contacts match these filters."));
    for (const c of result.contacts) {
      const card = node("article");
      card.className = "crm-contact";
      const openContact = button("Open contact", () => {
        contactOpener = openContact;
        return showContact(c.id);
      });
      card.append(
        node("h3", c.full_name || "Profile not yet provided"),
        node("p", c.email),
        node(
          "p",
          `${catalog.categories.account_categories[c.account_category] || c.account_category} · ${catalog.categories.memberships[c.membership] || c.membership}`,
        ),
        node("p", [c.company, c.job_title].filter(Boolean).join(" · ")),
        node(
          "p",
          `${catalog.projects.find((p) => p.id === c.project_id)?.name || c.project_id} · ${catalog.categories.stages[c.lifecycle] || c.lifecycle}`,
        ),
        openContact,
      );
      list.append(card);
    }
    const pages = node("div");
    pages.className = "crm-actions";
    if (page > 1)
      pages.append(
        button("Previous page", async () => {
          page--;
          await load();
        }),
      );
    if (page * 50 < result.total)
      pages.append(
        button("Next page", async () => {
          page++;
          await load();
        }),
      );
    list.append(pages);
  }
  async function download() {
    const stamp = sequence;
    downloadController?.abort();
    const controller = new AbortController();
    downloadController = controller;
    const timer = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(
        `/api/admin/crm/contacts.csv?${new URLSearchParams(filters)}`,
        {
          credentials: "same-origin",
          signal: controller.signal,
        },
      );
      if (!response.ok) {
        if ([401, 403].includes(response.status)) clear();
        throw new Error("Unable to export contacts. Please refresh and retry.");
      }
      const blob = await response.blob();
      if (!active || stamp !== sequence) return;
      const url = URL.createObjectURL(blob);
      const a = node("a");
      a.href = url;
      a.download = "l91-llc-crm-contacts.csv";
      a.hidden = true;
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status.textContent = "CSV download started.";
    } finally {
      clearTimeout(timer);
      if (downloadController === controller) downloadController = undefined;
    }
  }
  function renderControls() {
    controls.replaceChildren();
    const filter = node("form");
    filter.className = "crm-fields";
    const search = inputField("Search name, email or company", filters.q);
    search.input.maxLength = 120;
    const projects = selectField(
      "Project",
      {
        "": "All projects",
        ...Object.fromEntries(catalog.projects.map((p) => [p.id, p.name])),
      },
      filters.project_id,
    );
    const stages = selectField(
      "Stage",
      { "": "All stages", ...catalog.categories.stages },
      filters.lifecycle,
    );
    const accountCategory = selectField(
      "Account category",
      {
        people: "People (hide smoke tests)",
        ...catalog.categories.account_categories,
        all: "All records, including smoke tests",
      },
      filters.account_category,
    );
    const membership = selectField(
      "Membership",
      { "": "All memberships", ...catalog.categories.memberships },
      filters.membership,
    );
    const industries = selectField(
      "Industry",
      { "": "All industries", ...catalog.categories.industries },
      filters.industry,
    );
    const uses = selectField(
      "Primary use",
      { "": "All uses", ...catalog.categories.uses },
      filters.primary_use,
    );
    const submit = node("button", "Filter contacts");
    submit.type = "submit";
    submit.className = "button primary";
    filter.append(
      search.wrap,
      projects.wrap,
      accountCategory.wrap,
      membership.wrap,
      stages.wrap,
      industries.wrap,
      uses.wrap,
      submit,
    );
    filter.addEventListener("submit", async (e) => {
      e.preventDefault();
      filters = {
        q: search.input.value,
        project_id: projects.input.value,
        lifecycle: stages.input.value,
        industry: industries.input.value,
        primary_use: uses.input.value,
        account_category: accountCategory.input.value,
        membership: membership.input.value,
      };
      page = 1;
      try {
        await load();
      } catch (e) {
        message(e);
      }
    });
    controls.append(filter, button("Export contacts CSV", download));
    controls.append(
      addContactForm(
        catalog,
        api,
        async (id) => {
          if (!active) return;
          filters.q = "";
          page = 1;
          renderControls();
          await load();
          if (active) await showContact(id);
        },
        message,
      ),
    );
    const integrations = node("details");
    integrations.append(node("summary", "Connect another project"));
    integrations.append(
      node(
        "p",
        "Create a project and use its private key on that project's server to capture registrations. Each project's contacts stay separate.",
      ),
    );
    const keyBox = node("div");
    keyBox.className = "crm-key";
    const reveal = (result: { id: string; token: string }) => {
      keyBox.replaceChildren(
        node(
          "p",
          "Save this key in your project's server secrets. It is shown only now.",
        ),
      );
      const label = node("label", "Project API key");
      const value = node("input");
      value.readOnly = true;
      value.value = result.token;
      label.append(value);
      keyBox.append(
        label,
        node(
          "p",
          `POST ${window.location.origin}/api/crm/v1/projects/${result.id}/registrations`,
        ),
        node("p", "Authorization: Bearer <project key>"),
        button("Hide key", () => keyBox.replaceChildren()),
      );
    };
    const form = node("form");
    form.className = "crm-fields";
    const id = inputField("Project ID");
    id.input.pattern = "[a-z][a-z0-9_-]+";
    id.input.maxLength = 40;
    id.input.minLength = 2;
    id.input.required = true;
    const name = inputField("Project name");
    name.input.required = true;
    name.input.maxLength = 100;
    const create = node("button", "Create project");
    create.type = "submit";
    create.className = "button primary";
    form.append(id.wrap, name.wrap, create);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      create.disabled = true;
      const stamp = sequence;
      try {
        const result = await api<{ id: string; token: string }>(
          "/api/admin/crm/projects",
          "POST",
          { id: id.input.value, name: name.input.value },
        );
        if (!active || sequence !== stamp) return;
        catalog.projects.push({
          id: result.id,
          name: name.input.value,
          connected: true,
        });
        reveal(result);
        form.reset();
        const option = node("option", catalog.projects.at(-1)!.name);
        option.value = result.id;
        projects.input.append(option);
        renderKeys();
      } catch (e) {
        message(e);
      } finally {
        create.disabled = false;
      }
    });
    const keys = node("div");
    function renderKeys() {
      keys.replaceChildren();
      for (const p of catalog.projects.filter((p) => p.id !== "landwolf")) {
        const row = node("div");
        row.className = "crm-actions";
        row.append(
          node("strong", p.name),
          button("Rotate key", async () => {
            const stamp = sequence;
            const result = await api<{ id: string; token: string }>(
              `/api/admin/crm/projects/${p.id}/rotate-key`,
              "POST",
            );
            if (active && stamp === sequence) reveal(result);
          }),
          button("Revoke key", async () => {
            await api(`/api/admin/crm/projects/${p.id}/key`, "DELETE");
            keyBox.replaceChildren();
            if (active) status.textContent = `${p.name} connector key revoked.`;
          }),
        );
        keys.append(row);
      }
    }
    renderKeys();
    integrations.append(form, keyBox, keys);
    controls.append(integrations);
  }
  async function open() {
    clear();
    active = true;
    const stamp = sequence;
    panel.append(statistics, controls, status, list, detail);
    status.textContent = "Loading CRM…";
    try {
      catalog = await api<Catalog>("/api/admin/crm/projects");
      if (!active || sequence !== stamp) return;
      renderControls();
      await load();
    } catch (e) {
      message(e);
    }
  }
  return { open, clear };
}
