import { releaseCards, type Delivery } from "./releases";
/** Customer API only. Shared CRM, costs and factory credentials never enter this bundle. */
import { byId, element } from "./dom";

type Work = { id: string; service: string; status: string; revision: number };
type Project = {
  releases?: Delivery[];
  id: string;
  title: string;
  status: string;
  quantity: number;
  created_at: number;
  services: Work[];
  text?: string;
  reference_url?: string;
  messages?: { id: string; author: string; text: string; created_at: number }[];
  older_messages?: boolean;
};
type Session = {
  authenticated: boolean;
  csrf?: string;
  email?: string;
  name?: string;
  customer_id?: string;
};
let session: Session = { authenticated: false };
let generation = 0;
let selected = "";
let projects: Project[] = [];
let offset = 0;
let nextOffset: number | null = null;
let joining = false;
let submissionId = crypto.randomUUID();
const form = byId<HTMLFormElement>("concept-form");
const status = byId("portal-status");
const submissionStatus = byId("submission-status");
const submit = byId<HTMLButtonElement>("submit-request");
const signForm = byId<HTMLFormElement>("signin-form");
const title = (value: string) => value.replaceAll("_", " ").toUpperCase();
const errorText = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Unable to complete the request. Please try again.";
const field = (form: HTMLFormElement, name: string): HTMLInputElement =>
  form.elements.namedItem(name) as HTMLInputElement;

async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    cache: "no-store",
    signal: AbortSignal.timeout(30000),
    headers: {
      "Content-Type": "application/json",
      "X-LandWolf-Client": "web",
      ...(session.csrf ? { "X-CSRF-Token": session.csrf } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/auth/login") {
      clearPrivate();
      session = { authenticated: false };
      showSession();
    }
    throw new Error(
      data &&
        typeof data === "object" &&
        "detail" in data &&
        typeof data.detail === "string"
        ? data.detail
        : "Request failed. Please try again.",
    );
  }
  return data as T;
}
function clearPrivate() {
  generation++;
  selected = "";
  projects = [];
  byId("project-list").replaceChildren();
  byId("project-detail").replaceChildren();
  submissionStatus.textContent = "";
  form.reset();
  submissionId = crypto.randomUUID();
}
function panel(name: "intake" | "workspace" | "signin") {
  for (const id of ["intake", "workspace", "signin"])
    byId(id + "-panel").hidden = id !== name;
  for (const [id, target] of [
    ["new-project-nav", "intake"],
    ["my-projects-nav", "workspace"],
    ["signin-nav", "signin"],
  ] as const) {
    byId(id).removeAttribute("aria-current");
    if (target === name) byId(id).setAttribute("aria-current", "page");
  }
  status.textContent = "";
}
function showSession() {
  byId("signin-nav").hidden = session.authenticated;
  byId("signout-nav").hidden = !session.authenticated;
  byId("additional-services").hidden = !session.authenticated;
  byId("guest-note").hidden = session.authenticated;
  byId("account-state").textContent = session.authenticated
    ? "SIGNED IN · " + session.email
    : "GUEST · REQUEST A PROJECT OR SIGN IN";
  field(form, "email").readOnly = session.authenticated;
  if (session.authenticated) {
    field(form, "email").value = session.email || "";
    if (!field(form, "full_name").value)
      field(form, "full_name").value =
        session.name === "Customer" ? "" : session.name || "";
  }
}
async function refreshSession() {
  const stamp = generation;
  const value = await api<Session>("/api/portal/session");
  if (stamp !== generation) return;
  session = value;
  showSession();
}
function button(label: string, action: () => void): HTMLButtonElement {
  const b = element("button", "", label);
  b.type = "button";
  b.addEventListener("click", action);
  return b;
}
function renderList() {
  const list = byId("project-list");
  list.replaceChildren();
  const filter = byId<HTMLSelectElement>("service-filter").value;
  const visible = projects.filter(
    (p) => !filter || p.services.some((w) => w.service === filter),
  );
  for (const p of visible) {
    const card = button("", () => {
      void detail(p.id).catch((e) => {
        status.textContent = errorText(e);
      });
    });
    card.className = "project-card";
    card.setAttribute("aria-label", p.title);
    card.setAttribute("aria-pressed", String(selected === p.id));
    card.append(
      element(
        "span",
        "eyebrow",
        p.services.map((w) => title(w.service)).join(" / "),
      ),
      element("strong", "", p.title),
      element("span", "status-tag", title(p.status)),
      element(
        "span",
        "note",
        new Date(p.created_at * 1000).toLocaleDateString(),
      ),
    );
    list.append(card);
  }
  if (!visible.length)
    list.append(
      element(
        "p",
        "empty-state",
        projects.length
          ? "NO MATCHING PROJECTS ON THIS PAGE"
          : "NO PROJECTS YET",
      ),
    );
  byId("previous-projects").hidden = offset === 0;
  byId("next-projects").hidden = nextOffset === null;
}
async function loadProjects(pageOffset = 0) {
  if (!session.authenticated) {
    panel("signin");
    return;
  }
  const stamp = ++generation;
  panel("workspace");
  selected = "";
  byId("project-detail").replaceChildren();
  byId("project-list").replaceChildren(
    element("p", "note", "LOADING PROJECTS…"),
  );
  const result = await api<{ projects: Project[]; next_offset: number | null }>(
    "/api/portal/projects?offset=" + pageOffset,
  );
  if (stamp !== generation) return;
  projects = result.projects;
  offset = pageOffset;
  nextOffset = result.next_offset;
  renderList();
  byId("project-detail").append(
    element("h2", "", "PROJECT DETAILS"),
    element(
      "p",
      "note",
      projects.length
        ? "SELECT A PROJECT"
        : "SUBMIT A NEW PROJECT TO GET STARTED",
    ),
  );
}
async function detail(id: string) {
  selected = id;
  renderList();
  const stamp = ++generation;
  const view = byId("project-detail");
  view.replaceChildren(element("p", "note", "LOADING PROJECT…"));
  const p = await api<Project>(
    "/api/portal/projects/" + encodeURIComponent(id),
  );
  if (stamp !== generation || selected !== id) return;
  view.replaceChildren(
    element("p", "eyebrow", "PROJECT / " + p.id.slice(0, 8).toUpperCase()),
    element("h2", "project-title", p.title),
    element("span", "status-tag", title(p.status)),
  );
  const work = element("div", "work-list");
  for (const item of p.services) {
    const row = element("div", "work-row");
    row.append(
      element("strong", "", title(item.service)),
      element("span", "status-tag", title(item.status)),
    );
    if (item.service === "software") {
      const progress = element("span", "note", "FACTORY · LOADING");
      row.append(progress);
      const refresh = element("button", "", "REFRESH PROGRESS");
      refresh.type = "button";
      const update = async () => {
        refresh.disabled = true;
        try {
          const state = await api<{ state: string }>(
            "/api/portal/work/" + item.id + "/factory",
          );
          if (stamp === generation && selected === id)
            progress.textContent = "FACTORY · " + title(state.state);
        } catch {
          if (stamp === generation && selected === id)
            progress.textContent = "FACTORY · STATUS UNAVAILABLE";
        } finally {
          refresh.disabled = false;
        }
      };
      refresh.addEventListener("click", () => void update());
      row.append(refresh);
      void update();
    }
    work.append(row);
  }
  view.append(
    work,
    element("h3", "", "REQUIREMENTS"),
    element("p", "preserve-lines", p.text),
    element("p", "note", "QUANTITY · " + p.quantity),
  );
  if (p.reference_url) {
    const link = element("a", "", "REFERENCE FILE");
    link.href = p.reference_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    view.append(link);
  }
  view.append(releaseCards(p.releases || []));
  view.append(element("h3", "", "UPDATES"));
  if (!p.messages?.length) view.append(element("p", "note", "NO UPDATES YET"));
  if (p.older_messages)
    view.append(element("p", "note", "SHOWING THE MOST RECENT 100 UPDATES"));
  for (const message of p.messages || []) {
    const card = element("article", "message");
    card.append(
      element(
        "p",
        "eyebrow",
        (message.author === "team" ? "LUPUSPEC" : "YOU") +
          " · " +
          new Date(message.created_at * 1000).toLocaleString(),
      ),
      element("p", "preserve-lines", message.text),
    );
    view.append(card);
  }
  const reply = element("form", "reply-form");
  const label = element("label", "", "ADD A MESSAGE");
  const input = element("textarea");
  input.required = true;
  input.maxLength = 2000;
  input.rows = 4;
  label.append(input);
  const send = element("button", "", "SEND MESSAGE");
  send.type = "submit";
  const result = element("p", "note");
  result.setAttribute("role", "status");
  const messageId = crypto.randomUUID();
  reply.append(label, send, result);
  reply.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!reply.reportValidity()) return;
    send.disabled = true;
    try {
      await api(
        "/api/portal/projects/" + encodeURIComponent(id) + "/messages",
        "POST",
        { submission_id: messageId, text: input.value.trim() },
      );
      if (stamp === generation && selected === id) await detail(id);
    } catch (e) {
      if (stamp === generation) result.textContent = errorText(e);
    } finally {
      send.disabled = false;
    }
  });
  view.append(reply);
}
byId("new-project-nav").addEventListener("click", () => {
  generation++;
  panel("intake");
});
byId("signin-nav").addEventListener("click", () => panel("signin"));
for (const id of ["my-projects-nav", "refresh-projects"])
  byId(id).addEventListener("click", () => {
    void loadProjects().catch((e) => {
      status.textContent = errorText(e);
    });
  });
byId("next-projects").addEventListener("click", () => {
  if (nextOffset !== null)
    void loadProjects(nextOffset).catch((e) => {
      status.textContent = errorText(e);
    });
});
byId("previous-projects").addEventListener("click", () => {
  void loadProjects(Math.max(0, offset - 20)).catch((e) => {
    status.textContent = errorText(e);
  });
});
byId("service-filter").addEventListener("change", renderList);
byId("auth-toggle").addEventListener("click", () => {
  joining = !joining;
  byId("signin-title").textContent = joining ? "CREATE ACCOUNT" : "SIGN IN";
  byId("auth-submit").textContent = joining ? "CREATE ACCOUNT" : "SIGN IN";
  byId("auth-toggle").textContent = joining
    ? "USE EXISTING ACCOUNT"
    : "CREATE ACCOUNT";
  byId("join-name-wrap").hidden = !joining;
  field(signForm, "full_name").required = joining;
  field(signForm, "password").autocomplete = joining
    ? "new-password"
    : "current-password";
});
signForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!signForm.reportValidity()) return;
  const b = byId<HTMLButtonElement>("auth-submit");
  b.disabled = true;
  status.textContent = "SIGNING IN…";
  try {
    const result = await api<{ csrf: string }>(
      joining ? "/api/portal/register" : "/api/auth/login",
      "POST",
      {
        email: field(signForm, "email").value.trim(),
        password: field(signForm, "password").value,
        ...(joining
          ? { full_name: field(signForm, "full_name").value.trim() }
          : {}),
      },
    );
    clearPrivate();
    session.csrf = result.csrf;
    signForm.reset();
    await refreshSession();
    panel("intake");
  } catch (e) {
    status.textContent = errorText(e);
  } finally {
    b.disabled = false;
  }
});
byId("recover-account").addEventListener("click", () => {
  const email = field(signForm, "email");
  if (!email.reportValidity()) return;
  void api<{ message: string }>("/api/auth/recovery", "POST", {
    email: email.value.trim(),
  })
    .then((result) => {
      status.textContent =
        result.message ||
        "If recovery is available, instructions will be emailed to you.";
    })
    .catch((e) => {
      status.textContent = errorText(e);
    });
});
byId("signout-nav").addEventListener("click", async () => {
  clearPrivate();
  panel("signin");
  try {
    await api("/api/auth/logout", "POST", {});
    session = { authenticated: false };
    showSession();
  } catch (e) {
    status.textContent = "Sign-out did not finish. " + errorText(e);
  }
});
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  submit.disabled = true;
  submissionStatus.textContent = "SENDING REQUEST…";
  const stamp = generation;
  try {
    const capability = form.querySelector<HTMLInputElement>(
      'input[name="capability"]:checked',
    )?.value;
    const permission = field(form, "contact_permission").checked;
    const quantity = Number(field(form, "quantity").value);
    if (!capability || !permission || !Number.isSafeInteger(quantity))
      throw new Error("Complete all required fields.");
    const services = [
      ...new Set([
        capability,
        ...Array.from(
          form.querySelectorAll<HTMLInputElement>(
            'input[name="extra"]:checked',
          ),
        ).map((i) => i.value),
      ]),
    ];
    const result = await api<{ id?: string; request_id?: string }>(
      session.authenticated ? "/api/portal/projects" : "/api/lupuspec/requests",
      "POST",
      {
        submission_id: submissionId,
        capability,
        title: field(form, "title").value.trim(),
        text: field(form, "text").value.trim(),
        quantity,
        reference_url: field(form, "reference_url").value.trim(),
        full_name: field(form, "full_name").value.trim(),
        email: field(form, "email").value.trim(),
        company: field(form, "company").value.trim(),
        phone: field(form, "phone").value.trim(),
        contact_permission: permission,
        ...(session.authenticated ? { services } : {}),
      },
    );
    if (stamp !== generation) return;
    form.reset();
    submissionId = crypto.randomUUID();
    showSession();
    submissionStatus.textContent =
      "Request received. Reference: " +
      (result.id || result.request_id) +
      ". WAITING FOR OWNER REVIEW. NO FACTORY RUN YET.";
    if (session.authenticated && result.id) {
      const customerEmail = session.email;
      try {
        await loadProjects();
        await detail(result.id);
        status.textContent = "PROJECT RECEIVED";
      } catch (e) {
        if (session.authenticated && session.email === customerEmail)
          status.textContent = "PROJECT SAVED. " + errorText(e);
      }
    }
  } catch (e) {
    if (stamp === generation) submissionStatus.textContent = errorText(e);
  } finally {
    submit.disabled = false;
  }
});
window.addEventListener("pagehide", clearPrivate);
window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    panel("intake");
    void refreshSession().catch((e) => {
      status.textContent = errorText(e);
    });
  }
});
void refreshSession().catch((e) => {
  byId("account-state").textContent = "SIGN-IN UNAVAILABLE";
  status.textContent = errorText(e);
});
