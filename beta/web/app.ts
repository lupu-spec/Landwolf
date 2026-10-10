import { setupCRM } from "./crm";
import { setupNavigationDock } from "./navigation-dock";
import { dismissMobileKeyboard, setupMobileKeyboard } from "./mobile-keyboard";
import {
  setupBilling,
  billingDestination,
  type BillingStatus,
} from "./billing";
import L from "leaflet";
import { setupFeedback } from "./feedback";
import { setupWolfAssistant } from "./wolf-assistant";
import type { HelpView } from "./help-guide";
import { bidRange, similarFilters } from "./property-context";
import {
  propertyTrustCard,
  researchSummary,
  type PropertyTrust,
} from "./trust-ui";
import { setupAccountActions } from "./account-actions";
import { acreagePresets, acreageRange, huntName } from "./hunt-form";
import { setupDecisionWorkspace } from "./decision-workspace";

type ResearchLocation = {
  address: string | null;
  latitude: number | null;
  longitude: number | null;
};
type PropertyRecord = {
  trust?: PropertyTrust;
  id: string;
  source: string;
  tract: string;
  title: string;
  county: string | null;
  state: string;
  acres: number | null;
  asking_price: number | null;
  reported_taxes: number | null;
  source_appraised_value: number | null;
  price_kind: string;
  category: string;
  sale_type: string;
  sale_status: string;
  auction_date: string | null;
  auction_date_text: string | null;
  bidding_deadline: string | null;
  eligibility: string | null;
  source_url: string;
  source_name: string;
  image_url: string | null;
  latitude: number | null;
  longitude: number | null;
  legal_description: string | null;
  location_description: string | null;
  source_account: string | null;
  retrieved_at: string;
  detail_retrieved_at: string | null;
  data_completeness: number;
  risk_notes: string[];
  active: boolean;
  research_location: ResearchLocation | null;
};
type Source = {
  last_attempt?: number | null;
  reuse_note?: string;
  history?: {
    finished_at: number;
    status: string;
    record_count: number;
    message: string;
  }[];
  id: string;
  name: string;
  url: string;
  status: string;
  last_success: number | null;
  record_count: number;
  message: string;
  stale: boolean;
  coverage_note: string;
  states: string[];
  categories: string[];
  automated: boolean;
};
type StateCoverage = {
  state: string;
  name: string;
  record_count: number;
  directory_url: string;
  feed_ids: string[];
};
type SearchResult = {
  results: PropertyRecord[];
  map_results: MapRecord[];
  map_total: number;
  map_limit: number;
  total: number;
  page: number;
  page_size: number;
  coverage_supported: boolean;
  data_attention: boolean;
  sources: Source[];
  coverage_note: string;
};
type MapRecord = Pick<
  PropertyRecord,
  "id" | "tract" | "asking_price" | "latitude" | "longitude"
>;
type SessionInfo = {
  billing?: BillingStatus;
  payments_enabled?: boolean;
  is_owner?: boolean;
  version?: string;
  authenticated?: boolean;
  email: string;
  csrf: string;
  email_verified?: boolean;
  email_delivery_enabled?: boolean;
  feedback_trial_enabled?: boolean;
  environment?: string;
};
type ResearchCatalog = {
  id: string;
  name: string;
  url: string;
  coverage: string;
};
type ResearchReport = {
  status: string;
  message: string;
  cached: boolean;
  location: {
    latitude: number;
    longitude: number;
    label: string;
    basis: string;
    state: string;
  } | null;
  sources: {
    id: string;
    name: string;
    url: string;
    status: string;
    retrieved_at: string;
    summary: string;
    limitation: string;
    sections: { title: string; facts: { label: string; value: string }[] }[];
  }[];
};
type AnalysisResult = {
  model_version: string;
  iterations: number;
  seed: number;
  profit: Record<string, number>;
  acquisition_cost: Record<string, number>;
  median_roi_pct: number | null;
  loss_probability_pct: number;
  loss_probability_interval_pct: number[];
  feasible: boolean;
  current_bid_meets_targets: boolean;
  scenario_score: number | null;
  histogram: { low: number; high: number; count: number }[];
  limitations: string[];
};

function byId<T extends HTMLElement = HTMLElement>(id: string): T {
  const result = document.getElementById(id);
  if (!result) throw new Error(`Required interface element missing: ${id}`);
  return result as T;
}
function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  css = "",
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  node.className = css;
  if (text !== undefined) node.textContent = text;
  return node;
}
const money = (value: number | null | undefined) =>
  value == null
    ? "Not available"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(value);
const date = (value: string | number | null) =>
  value === null
    ? "Not yet retrieved"
    : new Date(typeof value === "number" ? value * 1000 : value).toLocaleString(
        [],
        { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" },
      );
const errorText = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
const form = byId<HTMLFormElement>("search-form");
const dialog = byId<HTMLDialogElement>("property-dialog");
let csrf = "";
const decisions = setupDecisionWorkspace(api, () => csrf, openDetail);
let currentView = "explore";
const billing = setupBilling(api, async (status) => {
  await feedback.refresh();
  if (status.allowed) await navigate("explore");
});
const feedback = setupFeedback(api, (status) => {
  if (billing.state?.enabled) {
    if (billing.state.allowed !== status.access_allowed)
      billing.set({ ...billing.state, allowed: status.access_allowed });
    void billing.refresh().catch((error: unknown) => notify(errorText(error)));
  }
  if (
    !status.access_allowed &&
    currentView !== "feedback" &&
    currentView !== "hunt" &&
    currentView !== "billing"
  ) {
    dialog.close();
    void navigate(
      billing.state?.enabled ? billingDestination(billing.state) : "feedback",
    );
  }
});
const crm = setupCRM(api);
const facebookTrial =
  new URLSearchParams(window.location.search).get("trial") ===
  "facebook-90-day-feedback";
let registerMode = false;
let page = 1;
let requestSequence = 0;
let detailSequence = 0;
let analysisSequence = 0;
let researchSequence = 0;
let navigationSequence = 0;
type HuntCriteria = {
  mode: "fixed" | "auction";
  states: string[];
  county: string | null;
  center_lat: number | null;
  center_lon: number | null;
  radius_miles: number | null;
  min_acres: number;
  max_acres: number;
  max_price: number | null;
  max_price_per_acre: number | null;
  preferred_min?: number | null;
  preferred_max?: number | null;
};
type HuntRow = {
  id: string;
  name: string;
  criteria: HuntCriteria;
  active: boolean;
  revision: number;
};
type HuntEntry = {
  listing_id: string;
  title: string;
  tract: string;
  image_url: string | null;
  state: string;
  county: string | null;
  acres: number | null;
  amount: number | null;
  price_kind: string;
  score: number | null;
  reasons: string[];
  components?: Record<string, number>;
};
let editingHunt: string | null = null;
let editingHuntCriteria: HuntCriteria | null = null;
let huntSaving = false;
let huntListSequence = 0;
let huntResultSequence = 0;
let researchListingId: string | null = null;
let currentProperty: PropertyRecord | null = null;
let pendingResearchProperty: PropertyRecord | null = null;
let map: L.Map | null = null;
let markers: L.LayerGroup | null = null;
let mapRecords: MapRecord[] = [];
let mapNeedsFit = false;
let notificationTimer: ReturnType<typeof setTimeout> | undefined;
let coverageSources: Source[] = [];
let isOwner = false;
let coverageStates: StateCoverage[] = [];
let coverageCounties: {
  state: string;
  county: string;
  source: string;
  record_count: number;
}[] = [];
setupNavigationDock();
setupMobileKeyboard();
const assistant = setupWolfAssistant({
  api,
  session: () => csrf,
  context: () => ({
    authenticated: Boolean(csrf),
    owner: isOwner,
    access: billing.state?.enabled
      ? billing.state.allowed
      : feedback.allowed("explore"),
    view: byId<HTMLDialogElement>("account-dialog").open
      ? "account"
      : dialog.open
        ? "property"
        : csrf
          ? (currentView as HelpView)
          : "auth",
  }),
  navigate: async (view) => {
    if (view === "auth")
      return !csrf && !byId<HTMLDialogElement>("account-dialog").open;
    if (view === "property") return Boolean(csrf && dialog.open);
    if (view === "account" || !csrf || (view === "sources" && !isOwner))
      return false;
    if (!byId<HTMLDialogElement>("account-dialog").open) {
      dialog.close();
      if (currentView !== view) await navigate(view);
      return currentView === view;
    }
    return false;
  },
});
const resaleNames = ["resale_low", "resale_likely", "resale_high"];
let resaleOverrides = new Set<string>();
let repairOverrides = new Set<string>();
const scenarioDrafts = new Map<
  string,
  {
    values: Record<string, string>;
    overrides: string[];
    repairOverrides: string[];
  }
>();
let researchProperty: PropertyRecord | null = null;
let researchContextSequence = 0;
const categoryNames: Record<string, string> = {
  government_land: "DNR & government land",
  tax_sale: "Tax sale",
  foreclosure: "Foreclosure / REO",
  pre_foreclosure: "Pre-foreclosure notice",
  surplus: "Public surplus",
  public_auction: "Public auction",
};
const area = (value: number | null) =>
  value === null
    ? "Acreage not published"
    : `${value.toLocaleString(undefined, { maximumFractionDigits: 4 })} acres`;
const perAcre = (record: PropertyRecord) =>
  record.asking_price !== null && record.acres !== null
    ? money(record.asking_price / record.acres)
    : "Not available";
const location = (record: PropertyRecord) =>
  `${record.county ? record.county + " County, " : ""}${record.state}`;
const saleDate = (value: string | null) =>
  value ? new Date(value + "T12:00:00").toLocaleDateString() : "Not published";

function notify(message: string): void {
  const box = byId("toast");
  box.textContent = message;
  box.hidden = false;
  clearTimeout(notificationTimer);
  notificationTimer = setTimeout(() => {
    box.hidden = true;
  }, 3500);
}

function clearSession(): void {
  csrf = "";
  isOwner = false;
  assistant.clear();
  decisions.clear();
  feedback.clear();
  crm.clear();
  byId("crm-nav").hidden = true;
  byId<HTMLFormElement>("auth-form").reset();
  billing.clear();
  currentView = "explore";
  scenarioDrafts.clear();
  resaleOverrides.clear();
  repairOverrides.clear();
  form.reset();
  byId<HTMLSelectElement>("state").value = "US";
  requestSequence++;
  detailSequence++;
  navigationSequence++;
  resetResearch();
  currentProperty = null;
  pendingResearchProperty = null;
  dialog.close();
  byId("detail-content").replaceChildren();
  byId("detail-actions").replaceChildren();
  byId("analysis-results").replaceChildren();
  byId<HTMLFormElement>("analysis-form").reset();
  byId("property-list").replaceChildren();
  byId("source-summary").textContent = "Loading listings…";
  byId("source-cards").replaceChildren();
  byId("state-coverage").replaceChildren();
  byId("research-catalog").replaceChildren();
  coverageSources = [];
  isOwner = false;
  byId("coverage-nav").hidden = true;
  byId("source-panel").hidden = true;
  coverageStates = [];
  coverageCounties = [];
  byId("county-coverage").replaceChildren();
  byId("account-email").textContent = "";
  byId("email-status").textContent = "";
  byId("feature-roadmap").replaceChildren();
  huntListSequence++;
  huntResultSequence++;
  byId("hunt-list").replaceChildren();
  byId("hunt-results").replaceChildren();
  byId("hunt-status").textContent = "";
  resetHuntForm();
  markers?.clearLayers();
  mapRecords = [];
  mapNeedsFit = false;
  map?.closePopup();
  byId("workspace").hidden = true;
  byId("auth-view").hidden = false;
  byId("main-nav").hidden = true;
  byId("signout").hidden = true;
}

async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  timeoutMs = 20000,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, {
      method,
      credentials: "same-origin",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-LandWolf-Client": "web",
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      },
      ...(method !== "GET" ? { body: JSON.stringify(body ?? {}) } : {}),
    });
    const result: unknown = await response.json();
    if (!response.ok) {
      if (response.status === 401 && csrf) clearSession();
      if (response.status === 403 && path.startsWith("/api/account/"))
        clearSession();
      if (response.status === 403 && path.startsWith("/api/admin/")) {
        crm.clear();
        byId("crm-nav").hidden = true;
      }
      const detail =
        result && typeof result === "object" && "detail" in result
          ? result.detail
          : "Request failed";
      if (
        response.status === 403 &&
        !path.startsWith("/api/feedback") &&
        !path.startsWith("/api/admin")
      )
        void feedback.refresh();
      if (response.status === 402 && !path.startsWith("/api/billing")) {
        dialog.close();
        void billing
          .refresh()
          .then(() => navigate(billingDestination(billing.state)))
          .catch((error: unknown) => notify(errorText(error)));
      }
      const description =
        detail && typeof detail === "object" && "message" in detail
          ? String(detail.message)
          : String(detail);
      throw new Error(description);
    }
    // The same-origin API enforces response records through its Pydantic contract.
    return result as T;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError")
      throw new Error("Request timed out. Please try again.", { cause: error });
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function safeImage(url: string | null): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" &&
      !parsed.username &&
      !parsed.password &&
      !parsed.port &&
      ((parsed.hostname === "cdn.glo.texas.gov" &&
        parsed.pathname.startsWith("/vlb/land/tract-images/")) ||
        (parsed.hostname === "dnr.alaska.gov" &&
          parsed.pathname.startsWith("/mlw/cdn/img/landsales/")))
      ? url
      : null;
  } catch {
    return null;
  }
}
function sourceLink(url: string, label: string): HTMLAnchorElement {
  const a = element("a", "", label);
  try {
    const parsed = new URL(url);
    if (
      parsed.protocol === "https:" &&
      !parsed.username &&
      !parsed.password &&
      !parsed.port &&
      [
        "www.glo.texas.gov",
        "www.resales.usda.gov",
        "www.irsauctions.gov",
        "www.treasury.gov",
        "dnr.alaska.gov",
        "www.dnr.state.mi.us",
        "www.michigan.gov",
        "www.hudhomestore.gov",
        "disposal.gsa.gov",
        "www.usa.gov",
        "cosl.org",
        "geocoding.geo.census.gov",
        "www.fema.gov",
        "epqs.nationalmap.gov",
        "sdmdataaccess.nrcs.usda.gov",
        "www.nconemap.gov",
        "www.dot.state.mn.us",
        "edocs-public.dot.state.mn.us",
        "www.dnr.state.mn.us",
        "land.az.gov",
      ].includes(parsed.hostname)
    )
      a.href = url;
  } catch {
    /* A malformed source is displayed without an actionable URL. */
  }
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  return a;
}
function photo(
  record: Pick<PropertyRecord, "image_url" | "tract">,
  css: string,
): HTMLElement {
  const src = safeImage(record.image_url);
  const img = element("img", css) as HTMLImageElement;
  const fallback = "/assets/no-photo-available.png";
  img.src = src ?? fallback;
  img.alt = src
    ? `Official source image for tract ${record.tract}`
    : "LandWolf — No photo available";
  img.loading = "lazy";
  if (!src) img.classList.add("image-missing");
  else
    img.addEventListener(
      "error",
      () => {
        img.src = fallback;
        img.alt = "LandWolf — No photo available";
        img.classList.add("image-missing");
      },
      { once: true },
    );
  return img;
}

function setAuthMode(register: boolean): void {
  registerMode = register;
  byId<HTMLFieldSetElement>("registration-profile").hidden = !register;
  byId<HTMLFieldSetElement>("registration-profile").disabled = !register;
  byId("login-tab").setAttribute("aria-pressed", String(!register));
  byId("register-tab").setAttribute("aria-pressed", String(register));
  byId("auth-submit").textContent = register
    ? "Create your account →"
    : "Sign in to LandWolf →";
  byId<HTMLInputElement>("password").autocomplete = register
    ? "new-password"
    : "current-password";
  byId("auth-message").textContent = "";
}
byId("login-tab").addEventListener("click", () => setAuthMode(false));
byId("register-tab").addEventListener("click", () => setAuthMode(true));
if (facebookTrial) {
  byId("facebook-trial-offer").hidden = false;
  setAuthMode(true);
}
byId<HTMLFormElement>("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = byId<HTMLButtonElement>("auth-submit");
  button.disabled = true;
  byId("auth-message").textContent = "";
  try {
    const info = await api<SessionInfo>(
      `/api/auth/${registerMode ? "register" : "login"}`,
      "POST",
      {
        email: byId<HTMLInputElement>("email").value,
        password: byId<HTMLInputElement>("password").value,
        ...(registerMode
          ? {
              campaign: facebookTrial ? "facebook-90-day-feedback" : undefined,
              profile: {
                full_name: byId<HTMLInputElement>("signup-name").value,
                company: byId<HTMLInputElement>("signup-company").value,
                phone: byId<HTMLInputElement>("signup-phone").value,
                job_title: byId<HTMLInputElement>("signup-title").value,
                industry: byId<HTMLSelectElement>("signup-industry").value,
                contact_type: byId<HTMLSelectElement>("signup-type").value,
                primary_use: byId<HTMLSelectElement>("signup-use").value,
                use_details: byId<HTMLTextAreaElement>("signup-details").value,
                marketing_opt_in:
                  byId<HTMLInputElement>("signup-marketing").checked,
              },
            }
          : {}),
      },
    );
    byId<HTMLInputElement>("password").value = "";
    byId<HTMLFormElement>("auth-form").reset();
    await enterWorkspace(info);
  } catch (error) {
    byId("auth-message").textContent = errorText(error);
  } finally {
    button.disabled = false;
  }
});
byId("signout").addEventListener("click", async () => {
  try {
    await api("/api/auth/logout", "POST");
    clearSession();
    notify("You have signed out.");
  } catch (error) {
    notify(errorText(error));
  }
});

async function enterWorkspace(info: SessionInfo): Promise<void> {
  assistant.clear();
  csrf = info.csrf;
  const sessionToken = csrf;
  byId("account-email").textContent = info.email;
  const current = await api<SessionInfo>("/api/session");
  if (!csrf || csrf !== sessionToken) return;
  isOwner = current.is_owner === true;
  byId("coverage-nav").hidden = !isOwner;
  byId("crm-nav").hidden = !isOwner;
  byId("email-status").textContent = current.email_verified
    ? "Email verified"
    : current.email_delivery_enabled
      ? "Email not yet verified"
      : "Email delivery is not configured. Contact support for account help.";
  byId("verify-email").hidden =
    Boolean(current.email_verified) || !current.email_delivery_enabled;
  if (current.billing) billing.set(current.billing);
  const paymentReturn = new URLSearchParams(window.location.search).get(
    "billing",
  );
  if (paymentReturn) {
    window.history.replaceState(null, "", window.location.pathname);
    if (paymentReturn === "return" && current.billing?.enabled) {
      try {
        billing.set(await api<BillingStatus>("/api/billing/refresh", "POST"));
      } catch (error) {
        notify(errorText(error));
      }
    }
  }
  page = 1;
  await feedback.start(Boolean(current.is_owner));
  if (!csrf || csrf !== sessionToken) return;
  // Expose navigation only after startup has selected the permitted initial view.
  // Otherwise its delayed response can overwrite a user's first tab selection.
  byId("auth-view").hidden = true;
  byId("workspace").hidden = false;
  byId("main-nav").hidden = false;
  byId("signout").hidden = false;
  if (current.billing?.enabled) await billing.refresh();
  await navigate(
    billing.state?.enabled && !billing.state.allowed
      ? billingDestination(billing.state)
      : feedback.state?.state === "invited" || !feedback.allowed("explore")
        ? "feedback"
        : "explore",
  );
}
async function navigate(
  view: string,
  preset?: Record<string, string>,
): Promise<void> {
  dismissMobileKeyboard();
  if (["sources", "crm"].includes(view) && !isOwner) view = "explore";
  if (view !== "billing" && !feedback.allowed(view)) {
    view = billing.state?.enabled
      ? billingDestination(billing.state)
      : "feedback";
  }
  if (
    billing.state?.enabled &&
    !billing.state.allowed &&
    !["billing", "feedback", "hunt"].includes(view)
  )
    view = billingDestination(billing.state);
  if (view !== "crm") crm.clear();
  currentView = view;
  assistant.update();
  if (view === "explore" && preset) fillForm(form, preset);
  const navigation = ++navigationSequence;
  const sessionToken = csrf;
  requestSequence++;
  document
    .querySelectorAll<HTMLButtonElement>("#main-nav [data-nav]")
    .forEach((button) => {
      const active = button.dataset.nav === view;
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
  const sources = view === "sources";
  const researching = view === "research";
  const hunting = view === "hunt";
  const givingFeedback = view === "feedback";
  const subscribing = view === "billing";
  const managingContacts = view === "crm";
  byId("crm-panel").hidden = !managingContacts;
  byId("billing-panel").hidden = !subscribing;
  byId("feedback-panel").hidden = !givingFeedback;
  if (view === "explore")
    byId("results-layout").dataset.view =
      document.querySelector<HTMLButtonElement>(
        '[data-view][aria-pressed="true"]',
      )?.dataset.view ?? "split";
  page = 1;
  byId("source-panel").hidden = !sources;
  byId("research-panel").hidden = !researching;
  byId("hunt-panel").hidden = !hunting;
  byId("explore-panel").hidden =
    sources ||
    researching ||
    hunting ||
    givingFeedback ||
    subscribing ||
    managingContacts;
  byId("workspace-title").textContent = managingContacts
    ? "L91 LLC CRM"
    : subscribing
      ? "LandWolf membership."
      : givingFeedback
        ? "Help shape LandWolf."
        : sources
          ? "Know the source. Know the limits."
          : researching
            ? "Understand the location."
            : hunting
              ? "Find the land that fits."
              : "Find your next opportunity.";
  byId("workspace-description").textContent = managingContacts
    ? "Contacts, follow-ups, and registrations across your projects."
    : subscribing
      ? "Secure payments. Clear terms. Your account stays in control."
      : givingFeedback
        ? "Your experience, your priorities, and your feedback pilot status."
        : sources
          ? "A transparent view of connected data and current gaps."
          : researching
            ? "Public records, with their source and uncertainty in view."
            : hunting
              ? "Set your criteria once. Review source-backed matches and changes."
              : "Real listings. Clear sources. A closer look at what matters.";
  // A tab switch must expose its destination even from a long Research report.
  byId("workspace-title").focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "instant" });
  if (managingContacts) {
    await crm.open();
  } else if (subscribing) {
    try {
      await billing.refresh();
    } catch (error) {
      notify(errorText(error));
    }
  } else if (givingFeedback) {
    await feedback.open();
  } else if (sources) {
    try {
      const result = await api<{
        sources: Source[];
        states: StateCoverage[];
        research_sources: ResearchCatalog[];
        counties: typeof coverageCounties;
      }>("/api/sources");
      if (!csrf || csrf !== sessionToken || navigation !== navigationSequence)
        return;
      coverageSources = result.sources;
      coverageStates = result.states;
      coverageCounties = result.counties;
      renderCoverage();
      byId("research-catalog").replaceChildren(
        ...result.research_sources.map((source) => {
          const card = element("article", "source-card");
          card.append(
            element("h4", "", source.name),
            element("p", "", source.coverage),
            sourceLink(source.url, "View public source ↗"),
          );
          return card;
        }),
      );
      const framework = await api<{
        priorities: {
          priority: number;
          name: string;
          status: string;
          description: string;
        }[];
      }>("/api/capabilities");
      if (!csrf || csrf !== sessionToken || navigation !== navigationSequence)
        return;
      byId("feature-roadmap").replaceChildren(
        ...framework.priorities.map((item) => {
          const row = element("article", "roadmap-item");
          row.append(
            element(
              "h4",
              "",
              `${item.priority}. ${item.name} · ${item.status}`,
            ),
            element("p", "", item.description),
          );
          return row;
        }),
      );
    } catch (error) {
      notify(errorText(error));
    }
  } else if (hunting) await loadHunts();
  else if (!researching) await search();
}
document.querySelectorAll<HTMLButtonElement>("[data-nav]").forEach((button) =>
  button.addEventListener("click", () => {
    const view = button.dataset.nav ?? "explore";
    if (view === "research" && pendingResearchProperty)
      void researchPropertyLocation(pendingResearchProperty);
    else void navigate(view);
  }),
);

function query(): Record<string, unknown> {
  const data = new FormData(form);
  const maximum = String(data.get("max_price") ?? "");
  return {
    state: data.get("state"),
    location: data.get("location"),
    min_acres: Number(data.get("min_acres") || 0),
    max_price: maximum ? Number(maximum) : null,
    category: data.get("category"),
    source: data.get("source") || null,
    sort: byId<HTMLSelectElement>("sort").value,
    page,
    page_size: 12,
  };
}
function setLoading(loading: boolean): void {
  byId<HTMLButtonElement>("search-submit").disabled = loading;
  byId("property-list").setAttribute("aria-busy", String(loading));
}
async function search(): Promise<void> {
  const sequence = ++requestSequence;
  setLoading(true);
  byId("workspace-error").textContent = "";
  byId("workspace-retry").hidden = true;
  byId("empty-state").hidden = true;
  byId("pagination").hidden = true;
  byId("results-layout").hidden = false;
  byId("results-title").textContent = "Loading properties…";
  byId("results-subtitle").textContent = "";
  // Do not present prior search results while loading a new selection.
  byId("property-list").replaceChildren(
    ...Array.from({ length: 4 }, () => element("div", "loading-card")),
  );
  mapRecords = [];
  markers?.clearLayers();
  byId("map-count").textContent = "Loading locations…";
  try {
    const result = await api<SearchResult>("/api/search", "POST", query());
    if (sequence !== requestSequence || !csrf) return;
    renderResults(result);
  } catch (error) {
    if (sequence === requestSequence) {
      byId("workspace-error").textContent = errorText(error);
      byId("property-list").replaceChildren();
      byId("results-layout").hidden = true;
      byId("results-title").textContent = "Properties could not load.";
      byId("workspace-retry").hidden = false;
    }
  } finally {
    if (sequence === requestSequence) setLoading(false);
  }
}
form.addEventListener("submit", (event) => {
  event.preventDefault();
  page = 1;
  void search();
});
byId("sort").addEventListener("change", () => {
  page = 1;
  void search();
});
byId("refresh-results").addEventListener("click", () => {
  void search();
});
byId("workspace-retry").addEventListener("click", () => {
  void search();
});
byId("reset-filters").addEventListener("click", () => {
  form.reset();
  byId<HTMLSelectElement>("state").value = "US";
  page = 1;
  void search();
});
byId("previous").addEventListener("click", () => {
  page = Math.max(1, page - 1);
  void search();
});
byId("next").addEventListener("click", () => {
  page++;
  void search();
});

function renderResults(result: SearchResult): void {
  const total = result.total;
  byId("results-title").textContent =
    `${total} ${total === 1 ? "property" : "properties"}`;
  byId("results-subtitle").textContent =
    "Connected sale inventories · Published prices and bids are not appraisals";
  const feeds = result.sources.filter((source) => source.automated);
  const ready = feeds.filter(
    (source) => source.status === "ready" && !source.stale,
  );
  const attention = result.data_attention;
  byId("source-summary").textContent = isOwner
    ? `${ready.length} of ${feeds.length} matching feeds refreshed${attention ? " · Some feeds need attention" : ""} · Partial coverage; inspect Data coverage`
    : attention
      ? "Some listing data could not be refreshed. Confirm availability with the original listing."
      : "Confirm availability and sale terms with the original listing.";
  byId("source-summary").parentElement?.classList.toggle("stale", attention);
  const empty = result.results.length === 0;
  byId("empty-state").hidden = !empty;
  byId("results-layout").hidden = empty;
  if (empty) {
    byId("empty-title").textContent = !result.coverage_supported
      ? "This coverage is not connected yet."
      : attention
        ? "Results are incomplete while sources need attention."
        : "No matching listings in connected sources.";
    byId("empty-description").textContent = !result.coverage_supported
      ? isOwner
        ? "An automated feed for this selection is not connected. Open Data coverage for official source links and current gaps. A pre-foreclosure notice is not a confirmed sale."
        : "No listings are currently available for this selection. Try a different state or filter. A pre-foreclosure notice is not a confirmed sale."
      : result.coverage_note +
        (isOwner
          ? " Try a different state or filter, or inspect Data coverage."
          : " Try a different state or filter.");
  }
  byId("property-list").replaceChildren(...result.results.map(propertyCard));
  const pages = Math.max(1, Math.ceil(total / result.page_size));
  byId("pagination").hidden = pages === 1;
  byId<HTMLButtonElement>("previous").disabled = page <= 1;
  byId<HTMLButtonElement>("next").disabled = page >= pages;
  byId("page-label").textContent = `Page ${page} of ${pages}`;
  drawMap(result);
}

function locationLabel(value: ResearchLocation | null): string {
  if (!value)
    return "Location needed — enter an address or coordinates in Research.";
  return value.address ?? `${value.latitude}, ${value.longitude}`;
}
function propertyCard(record: PropertyRecord): HTMLElement {
  const card = element("article", "property-card");
  const image = element("div", "property-image");
  image.append(photo(record, ""));
  image.append(
    element(
      "span",
      "category-label",
      record.active
        ? (categoryNames[record.category] ?? record.category).toUpperCase()
        : "NOT IN CURRENT INVENTORY",
    ),
  );
  const body = element("div", "card-body");
  body.append(element("p", "card-location", location(record)));
  const heading = element("div", "card-heading");
  heading.append(
    element("h3", "", record.title),
    element("span", "", area(record.acres)),
  );
  body.append(heading);
  if (record.trust)
    body.append(
      element(
        "p",
        "evidence-badge",
        record.trust.identity.id
          ? "Publisher parcel ID available"
          : "Parcel match needs review",
      ),
    );
  body.append(
    element("p", "card-price", money(record.asking_price)),
    element(
      "p",
      "card-price-note",
      `${record.price_kind}${record.asking_price !== null && record.acres !== null ? " · " + perAcre(record) + "/acre" : ""}`,
    ),
    element(
      "p",
      "card-sale-status",
      `${record.sale_status}${record.auction_date ? " · " + saleDate(record.auction_date) : ""}`,
    ),
    element("div", "card-divider"),
  );
  const footer = element("div", "card-footer");
  footer.append(element("span", "card-source", record.source_name));
  const detail = element("button", "card-detail", "View property →");
  detail.setAttribute("aria-label", `View property ${record.tract}`);
  detail.addEventListener("click", () => {
    void openDetail(record.id);
  });
  footer.append(detail);
  const actions = propertyActions(record);
  body.append(
    footer,
    element("p", "research-location", locationLabel(record.research_location)),
    actions,
  );
  card.append(image, body);
  return card;
}

function drawMap(result: SearchResult): void {
  if (!map) {
    map = L.map("property-map", { scrollWheelZoom: false }).setView(
      [39, -98],
      4,
    );
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    })
      .on("tileerror", () => {
        byId("map-warning").textContent =
          "Base-map tiles are unavailable. Property coordinates and list details remain available.";
        byId("map-warning").hidden = false;
      })
      .addTo(map);
    markers = L.layerGroup().addTo(map);
    map.on("zoomend", renderMapMarkers);
    new ResizeObserver(() => updateMapViewport()).observe(byId("property-map"));
  }
  mapRecords = result.map_results;
  mapNeedsFit = true;
  const missing = result.total - result.map_total;
  byId("map-count").textContent =
    result.map_total > result.map_limit
      ? `First ${mapRecords.length} of ${result.map_total} mapped locations · narrow your filters`
      : `${result.map_total} mapped locations · ${missing} without coordinates`;
  renderMapMarkers();
  requestAnimationFrame(updateMapViewport);
}

function updateMapViewport(): void {
  const container = byId("property-map");
  if (!map || !container.clientWidth || !container.clientHeight) return;
  map.invalidateSize({ pan: false });
  if (!mapNeedsFit) return;
  mapNeedsFit = false;
  const points: L.LatLngTuple[] = mapRecords.flatMap((record) =>
    record.latitude === null || record.longitude === null
      ? []
      : [[record.latitude, record.longitude] as L.LatLngTuple],
  );
  if (points.length)
    map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 12 });
  else map.setView([39, -98], 4);
  renderMapMarkers();
}

function renderMapMarkers(): void {
  if (!map || !markers) return;
  markers.clearLayers();
  // Screen-space groups keep overlapping labels and identical coordinates reachable.
  // The cluster anchor is a real source point; individual coordinates never change.
  const groups: {
    position: L.LatLngTuple;
    pixel: L.Point;
    records: MapRecord[];
  }[] = [];
  for (const record of mapRecords) {
    if (record.latitude === null || record.longitude === null) continue;
    const position: L.LatLngTuple = [record.latitude, record.longitude];
    const pixel = map.project(position);
    const group = groups.find(
      (candidate) =>
        Math.abs(candidate.pixel.x - pixel.x) < 110 &&
        Math.abs(candidate.pixel.y - pixel.y) < 45,
    );
    if (group) group.records.push(record);
    else groups.push({ position, pixel, records: [record] });
  }
  for (const group of groups) {
    const record = group.records[0];
    if (!record) continue;
    const clustered = group.records.length > 1;
    const label = element(
      "span",
      "",
      clustered
        ? `${group.records.length} properties`
        : money(record.asking_price),
    );
    const marker = L.marker(group.position, {
      icon: L.divIcon({
        className: "map-pin",
        html: label,
        iconAnchor: [30, 15],
      }),
      title: clustered
        ? `${group.records.length} properties at or near this location`
        : `Tract ${record.tract}: ${money(record.asking_price)}`,
      alt: `Open tract ${record.tract}`,
    });
    if (clustered) {
      const choices = element("div", "map-property-choices");
      choices.append(element("strong", "", "Choose a property"));
      for (const item of group.records) {
        const choice = element(
          "button",
          "map-property-choice",
          `Tract ${item.tract} · ${money(item.asking_price)}`,
        );
        choice.addEventListener("click", () => {
          map?.closePopup();
          void openDetail(item.id);
        });
        choices.append(choice);
      }
      marker.bindPopup(choices, { maxWidth: 300 });
    } else {
      marker.on("click", () => {
        void openDetail(record.id);
      });
    }
    markers.addLayer(marker);
  }
}
document.querySelectorAll<HTMLButtonElement>("[data-view]").forEach((button) =>
  button.addEventListener("click", () => {
    byId("results-layout").dataset.view = button.dataset.view;
    document
      .querySelectorAll<HTMLButtonElement>("[data-view]")
      .forEach((other) => {
        if (other.tagName === "BUTTON")
          other.setAttribute("aria-pressed", String(other === button));
      });
    mapNeedsFit = true;
    requestAnimationFrame(updateMapViewport);
  }),
);

function renderSources(sources: Source[]): void {
  byId("source-cards").replaceChildren(
    ...sources.map((source) => {
      const card = element("article", "source-card");
      card.append(
        element(
          "span",
          `source-state ${source.stale || source.status !== "ready" ? "warn" : ""}`,
          !source.automated
            ? "Official source link · not imported"
            : source.status === "ready" && !source.stale
              ? "Retrieval current"
              : source.status,
        ),
      );
      card.append(
        element("h3", "", source.name),
        element("p", "", source.coverage_note),
        element(
          "p",
          "",
          source.automated
            ? `${source.record_count} source records at last successful sync · ${date(source.last_success)}`
            : "Directory entry; excluded from property counts",
        ),
        element("p", "", source.message),
        sourceLink(source.url, "Inspect the original inventory ↗"),
      );
      if (source.automated) {
        card.append(
          element(
            "p",
            "input-note",
            `Last attempted: ${date(source.last_attempt ?? null)} · Scheduled every 6 hours. Retrieval does not establish publisher freshness.`,
          ),
        );
        const history = element("details", "source-history");
        history.append(
          element("summary", "", "Recent refreshes and reuse limits"),
        );
        history.append(
          element(
            "p",
            "",
            source.reuse_note ?? "Review source terms before redistribution.",
          ),
        );
        for (const run of source.history ?? [])
          history.append(
            element(
              "p",
              "",
              `${date(run.finished_at)} · ${run.status} · ${run.record_count} candidate records. ${run.message}`,
            ),
          );
        if (!source.history?.length)
          history.append(
            element(
              "p",
              "",
              "No refresh history recorded for this source yet.",
            ),
          );
        card.append(history);
      }
      return card;
    }),
  );
}

function renderCoverage(): void {
  const state = byId<HTMLSelectElement>("coverage-state").value;
  const category = byId<HTMLSelectElement>("coverage-category").value;
  renderSources(
    coverageSources.filter(
      (source) =>
        (state === "US" || source.states.includes(state)) &&
        (category === "all" || source.categories.includes(category)),
    ),
  );
  const rows = coverageStates.filter(
    (item) => state === "US" || item.state === state,
  );
  const table = element("table", "coverage-table");
  const head = element("thead");
  const header = element("tr");
  for (const label of [
    "State",
    "Current records · all categories",
    "Official state agencies",
  ])
    header.append(element("th", "", label));
  head.append(header);
  const body = element("tbody");
  for (const item of rows) {
    const row = element("tr");
    const stateCell = element("td");
    const button = element("button", "text-button", item.name);
    button.addEventListener("click", () => {
      form.reset();
      byId<HTMLSelectElement>("state").value = item.state;
      void navigate("explore");
    });
    stateCell.append(button);
    const link = element("td");
    link.append(
      sourceLink(item.directory_url, "Find state / local agencies ↗"),
    );
    row.append(stateCell, element("td", "", String(item.record_count)), link);
    body.append(row);
  }
  table.append(head, body);
  byId("state-coverage").replaceChildren(table);
  const countyList = element("ul", "county-list");
  const counties = coverageCounties.filter(
    (item) =>
      (state === "US" || item.state === state) &&
      coverageSources.some(
        (source) =>
          source.id === item.source &&
          (category === "all" || source.categories.includes(category)),
      ),
  );
  for (const item of counties.slice(0, 40))
    countyList.append(
      element(
        "li",
        "",
        `${item.county}, ${item.state}: ${item.record_count} records · ${coverageSources.find((source) => source.id === item.source)?.name ?? item.source} · partial coverage`,
      ),
    );
  byId("county-coverage").replaceChildren(
    element(
      "p",
      "",
      counties.length
        ? `Observed county coverage (${Math.min(40, counties.length)} of ${counties.length} source/county groups). Select a state to narrow the view.`
        : "No county records available for this selection. This does not establish that no properties are for sale.",
    ),
    countyList,
  );
}
byId("coverage-state").addEventListener("change", renderCoverage);
byId("coverage-category").addEventListener("change", renderCoverage);

function researchMode(): void {
  const address = byId<HTMLSelectElement>("research-mode").value === "address";
  byId("research-address-field").hidden = !address;
  byId<HTMLInputElement>("research-address").required = address;
  byId("research-coordinate-fields").hidden = address;
  for (const id of ["research-latitude", "research-longitude"])
    byId<HTMLInputElement>(id).required = !address;
}
function invalidateResearch(): void {
  researchSequence++;
  researchListingId = null;
  byId("research-results").replaceChildren();
  byId("research-status").textContent = "";
  byId<HTMLButtonElement>("research-submit").disabled = false;
}
function resetResearch(): void {
  invalidateResearch();
  researchContextSequence++;
  researchProperty = null;
  byId("research-property-context").replaceChildren();
  byId<HTMLFormElement>("research-form").reset();
  researchMode();
}
function propertyActions(record: PropertyRecord): HTMLElement {
  const actions = element("div", "property-actions");
  const research = element("button", "button secondary", "Research property");
  research.type = "button";
  research.addEventListener("click", () => {
    void researchPropertyLocation(record);
  });
  const similar = element("button", "text-button", "Find similar properties");
  similar.type = "button";
  similar.addEventListener("click", () => {
    rememberScenario();
    dialog.close();
    detailSequence++;
    void navigate("explore", similarFilters(record));
  });
  const decision = element("button", "button secondary", "Decision research");
  decision.type = "button";
  decision.addEventListener("click", () => {
    void (async () => {
      if (!dialog.open || currentProperty?.id !== record.id)
        await openDetail(record.id);
      byId("decision-workspace").scrollIntoView({ behavior: "smooth" });
    })();
  });
  actions.append(research, decision, similar);
  return actions;
}
async function researchPropertyLocation(record: PropertyRecord): Promise<void> {
  const sequence = ++researchContextSequence;
  const token = csrf;
  try {
    const fresh = await api<PropertyRecord>(
      `/api/properties/${encodeURIComponent(record.id)}`,
    );
    if (sequence !== researchContextSequence || token !== csrf) return;
    await showResearchProperty(fresh);
  } catch (error) {
    if (token === csrf) notify(errorText(error));
  }
}

async function showResearchProperty(record: PropertyRecord): Promise<void> {
  rememberScenario();
  dialog.close();
  detailSequence++;
  resetResearch();
  researchProperty = record;
  pendingResearchProperty = null;
  const contextSequence = researchContextSequence;
  const point = record.research_location;
  const hasPoint = point?.latitude != null && point.longitude !== null;
  const address = point?.address;
  if (hasPoint) {
    byId<HTMLSelectElement>("research-mode").value = "coordinates";
    byId<HTMLInputElement>("research-latitude").value = String(point.latitude);
    byId<HTMLInputElement>("research-longitude").value = String(
      point.longitude,
    );
    researchListingId = record.id;
  } else if (address)
    byId<HTMLInputElement>("research-address").value = address;
  researchMode();
  const context = byId("research-property-context");
  context.append(
    element("h3", "", record.title),
    element("p", "", `${location(record)} · ${area(record.acres)}`),
    element(
      "p",
      "input-note",
      "Source-reported location. Coordinates and address results are not surveyed parcel boundaries.",
    ),
  );
  const analyze = element("button", "button quiet", "Open deal scenario");
  analyze.addEventListener("click", () => {
    if (researchProperty) void openDetail(researchProperty.id);
  });
  context.append(analyze, propertyActions(record));
  await navigate("research");
  if (contextSequence !== researchContextSequence || !csrf) return;
  if (hasPoint) await runResearch();
  else
    byId("research-status").textContent = address
      ? "Address prefilled. Review it, then select Research location."
      : "This listing has no usable published address or point. Enter an address or coordinates. County and tract identifiers cannot locate a parcel.";
}

function newResearchProperty(): void {
  rememberScenario();
  dialog.close();
  currentProperty = null;
  pendingResearchProperty = null;
  resetResearch();
  void navigate("research");
  // Let phone users read the screen before deliberately opening the keyboard.
  if (matchMedia("(min-width: 1101px) and (any-pointer: fine)").matches)
    byId<HTMLInputElement>("research-address").focus();
}
byId("research-new").addEventListener("click", newResearchProperty);
function renderResearch(report: ResearchReport): void {
  const container = byId("research-results");
  container.replaceChildren();
  container.append(researchSummary(report));
  if (report.location) {
    const point = report.location;
    const context = element("div", "research-context");
    context.append(
      element("h3", "", point.label),
      element(
        "p",
        "",
        `${point.basis} · ${point.latitude.toFixed(6)}, ${point.longitude.toFixed(6)} · ${point.state}`,
      ),
    );
    if (point.basis === "Census address approximation")
      context.append(
        element(
          "p",
          "source-state warn",
          "Approximate address point. Parcel, flood and soil results may describe a road or neighboring land. Confirm the location before relying on them.",
        ),
      );
    if (report.cached)
      context.append(
        element(
          "p",
          "input-note",
          "Cached public response. Original retrieval times are shown below; successful results may be reused for up to 6 hours.",
        ),
      );
    container.append(context);
  }
  for (const source of report.sources) {
    const card = element("article", "source-card research-source");
    const status =
      {
        ready: "Data returned",
        unavailable: "Temporarily unavailable",
        no_data: "No data returned · unknown",
        not_applicable: "Outside this source's coverage",
      }[source.status] ?? "Unknown";
    card.append(
      element(
        "span",
        `source-state ${source.status === "ready" ? "" : "warn"}`,
        status,
      ),
      element("h3", "", source.name),
      element("p", "", source.summary),
    );
    const evidence = element("details", "research-evidence");
    evidence.append(element("summary", "", "Inspect source evidence"));
    for (const section of source.sections) {
      const group = element("section", "research-section");
      const facts = element("dl", "research-facts");
      group.append(element("h4", "", section.title));
      for (const fact of section.facts)
        facts.append(
          element("dt", "", fact.label),
          element("dd", "", fact.value),
        );
      group.append(facts);
      evidence.append(group);
    }
    card.append(evidence);
    card.append(
      element("p", "input-note", source.limitation),
      element(
        "p",
        "input-note",
        `${source.status === "not_applicable" ? "Coverage checked" : "Request completed"} ${new Date(source.retrieved_at).toLocaleString()}. Retrieval time is not the source record's update date.`,
      ),
      sourceLink(source.url, "View public source & limitations ↗"),
    );
    container.append(card);
  }
}
async function runResearch(): Promise<void> {
  const researchForm = byId<HTMLFormElement>("research-form");
  if (!csrf || !researchForm.reportValidity()) return;
  dismissMobileKeyboard();
  const sequence = ++researchSequence;
  const sessionToken = csrf;
  const body = researchListingId
    ? { listing_id: researchListingId }
    : byId<HTMLSelectElement>("research-mode").value === "address"
      ? { address: byId<HTMLInputElement>("research-address").value.trim() }
      : {
          latitude: Number(byId<HTMLInputElement>("research-latitude").value),
          longitude: Number(byId<HTMLInputElement>("research-longitude").value),
        };
  const button = byId<HTMLButtonElement>("research-submit");
  button.disabled = true;
  byId("research-results").replaceChildren();
  byId("research-status").textContent =
    "Checking public sources… this can take up to a minute.";
  try {
    const report = await api<ResearchReport>(
      "/api/research",
      "POST",
      body,
      60000,
    );
    if (!csrf || csrf !== sessionToken || sequence !== researchSequence) return;
    byId("research-status").textContent = report.message;
    renderResearch(report);
  } catch (error) {
    if (csrf === sessionToken && sequence === researchSequence)
      byId("research-status").textContent = errorText(error);
  } finally {
    if (sequence === researchSequence) button.disabled = false;
  }
}
byId("research-mode").addEventListener("change", researchMode);
byId("research-form").addEventListener("input", () => {
  invalidateResearch();
  const note = byId("research-property-context").querySelector(".input-note");
  if (researchProperty && note)
    note.textContent =
      "Location edited: research may describe a different property. Open deal scenario still refers to the original listing; research results will not overwrite its scenario inputs.";
});
byId("research-form").addEventListener("submit", (event) => {
  event.preventDefault();
  void runResearch();
});

async function openDetail(id: string, preferredHunt?: string): Promise<void> {
  const sequence = ++detailSequence;
  try {
    const record = await api<PropertyRecord>(
      `/api/properties/${encodeURIComponent(id)}`,
    );
    if (!csrf || sequence !== detailSequence) return;
    currentProperty = record;
    pendingResearchProperty = record;
    renderDetail(record);
    void decisions.property(record.id, preferredHunt);
    const analysisForm = byId<HTMLFormElement>("analysis-form");
    analysisForm.reset();
    byId<HTMLDetailsElement>("analysis-advanced").open = false;
    resaleOverrides = new Set<string>();
    repairOverrides = new Set<string>();
    const draft = scenarioDrafts.get(record.id);
    if (draft) {
      fillForm(analysisForm, draft.values);
      resaleOverrides = new Set(draft.overrides);
      repairOverrides = new Set(draft.repairOverrides);
    } else {
      analysisInput("purchase_price").value =
        record.asking_price === null ? "" : String(record.asking_price);
      applyBidRange();
    }
    renderScenarioBasis();
    byId("scenario-property-context").textContent =
      `${record.title} · ${location(record)} · ${record.price_kind}. The published price/bid is a hypothetical scenario anchor, not estimated market value.`;
    updateZeroCostWarning();
    byId("analysis-results").hidden = true;
    byId("analysis-results").replaceChildren();
    byId("analysis-error").textContent = "";
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
  } catch (error) {
    notify(errorText(error));
  }
}
function renderDetail(record: PropertyRecord): void {
  byId("detail-actions").replaceChildren(propertyActions(record));
  const hero = element("div", "detail-hero");
  hero.append(photo(record, "detail-photo"));
  const overview = element("div", "detail-overview");
  overview.append(
    element(
      "p",
      "eyebrow",
      record.active
        ? record.sale_type.toUpperCase()
        : "NO LONGER IN CURRENT INVENTORY",
    ),
  );
  const heading = element("h2", "", record.title);
  heading.id = "detail-title";
  overview.append(
    heading,
    element("p", "detail-location", location(record)),
    element("p", "detail-price", money(record.asking_price)),
    element(
      "p",
      "input-note",
      `${record.price_kind} · Not a market-value estimate`,
    ),
    element("p", "", record.sale_status),
    element(
      "p",
      "",
      `Auction: ${saleDate(record.auction_date)} · Bid deadline: ${saleDate(record.bidding_deadline)}`,
    ),
  );
  if (record.eligibility)
    overview.append(element("p", "source-state warn", record.eligibility));
  if (record.reported_taxes !== null)
    overview.append(
      element(
        "p",
        "input-note",
        `Source-reported taxes: ${money(record.reported_taxes)} · Not a sale price, minimum bid or verified lien balance`,
      ),
    );
  if (record.auction_date_text && !record.auction_date)
    overview.append(
      element(
        "p",
        "input-note",
        `Source date text: ${record.auction_date_text}`,
      ),
    );
  if (record.source_appraised_value !== null)
    overview.append(
      element(
        "p",
        "input-note",
        `Source-reported appraisal: ${money(record.source_appraised_value)} · Date and current market value not independently verified; not an asking price`,
      ),
    );
  overview.append(
    sourceLink(record.source_url, "View official listing & sale terms ↗"),
  );
  const facts = element("div", "detail-facts");
  for (const [label, value] of [
    ["LAND AREA", area(record.acres)],
    ["PRICE / ACRE", perAcre(record)],
    ["SOURCE FIELDS", `${record.data_completeness}%`],
  ]) {
    const fact = element("div");
    fact.append(element("span", "", label), element("strong", "", value));
    facts.append(fact);
  }
  overview.append(facts);
  overview.append(
    element(
      "p",
      "input-note",
      "Research property opens the source address or coordinates. Scenario edits remain in this page session only.",
    ),
  );
  hero.append(overview);
  const research = element("div", "detail-research");
  const description = element("div");
  description.append(
    element("h3", "", "Legal description"),
    element(
      "p",
      "",
      record.legal_description ?? "Not provided in retrieved source details.",
    ),
    element("h3", "", "Source-reported location"),
    element(
      "p",
      "",
      record.location_description ??
        "Not provided. This property is not shown as a precise map point.",
    ),
  );
  if (record.source_account)
    description.append(
      element(
        "p",
        "detail-source",
        `GLO account ${record.source_account} · This is not a verified county parcel ID.`,
      ),
    );
  description.append(
    element(
      "p",
      "detail-source",
      `Inventory retrieved ${date(record.retrieved_at)}. Details retrieved ${date(record.detail_retrieved_at)}. Source-field completeness is not a title or investment confidence score.`,
    ),
  );
  const risks = element("aside", "risk-box");
  risks.append(element("h3", "", "Due diligence is still required"));
  const list = element("ul");
  record.risk_notes.forEach((note) => list.append(element("li", "", note)));
  risks.append(list);
  risks.append(
    element(
      "p",
      "detail-source",
      "Source-field completeness: inventory identity, acreage, price, detail text, and location. Ownership, liens, taxes, flood status, and valuations are not independently verified.",
    ),
  );
  research.append(description, risks);
  byId("detail-content").replaceChildren(hero, research);
  if (record.trust)
    byId("detail-content").append(propertyTrustCard(record.trust, sourceLink));
}
byId("close-detail").addEventListener("click", () => {
  rememberScenario();
  detailSequence++;
  dialog.close();
});
dialog.addEventListener("cancel", () => {
  rememberScenario();
  detailSequence++;
});

byId<HTMLFormElement>("analysis-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();
    const form = byId<HTMLFormElement>("analysis-form");
    const invalid = form.querySelector<HTMLInputElement>("input:invalid");
    if (invalid?.closest("#analysis-advanced"))
      byId<HTMLDetailsElement>("analysis-advanced").open = true;
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const number = (name: string) => Number(data.get(name));
    const payload = {
      purchase_price: number("purchase_price"),
      resale_basis: resaleOverrides.size ? "custom_scenario" : "bid_scenario",
      resale: {
        low: number("resale_low"),
        likely: number("resale_likely"),
        high: number("resale_high"),
      },
      repairs: {
        low: number("repairs_low"),
        likely: number("repairs_likely"),
        high: number("repairs_high"),
      },
      lien_reserve: number("lien_reserve"),
      closing_costs: number("closing_costs"),
      holding_months: number("holding_months"),
      monthly_holding: number("monthly_holding"),
      buyer_premium_pct: number("buyer_premium_pct"),
      selling_cost_pct: number("selling_cost_pct"),
      annual_financing_pct: number("annual_financing_pct"),
      target_roi_pct: number("target_roi_pct"),
      min_profit: number("min_profit"),
      max_loss_probability_pct: number("max_loss_probability_pct"),
      seed: number("seed"),
      iterations: 10000,
    };
    byId("analysis-error").textContent = "";
    if (
      payload.resale.low > payload.resale.likely ||
      payload.resale.likely > payload.resale.high ||
      payload.repairs.low > payload.repairs.likely ||
      payload.repairs.likely > payload.repairs.high
    ) {
      byId("analysis-error").textContent =
        "Each range must be ordered: low ≤ likely ≤ high.";
      byId<HTMLDetailsElement>("analysis-advanced").open = true;
      analysisInput(
        payload.resale.low > payload.resale.likely ||
          payload.resale.likely > payload.resale.high
          ? "resale_low"
          : "repairs_low",
      ).focus();
      return;
    }
    const sequence = detailSequence;
    const run = ++analysisSequence;
    const button = byId<HTMLButtonElement>("run-analysis");
    button.disabled = true;
    try {
      const result = await api<AnalysisResult>(
        "/api/analysis",
        "POST",
        payload,
      );
      if (
        csrf &&
        sequence === detailSequence &&
        run === analysisSequence &&
        dialog.open
      )
        renderAnalysis(result);
    } catch (error) {
      byId("analysis-error").textContent = errorText(error);
    } finally {
      button.disabled = false;
    }
  },
);

function renderAnalysis(result: AnalysisResult): void {
  const container = byId("analysis-results");
  container.replaceChildren();
  container.hidden = false;
  const heading = element("div", "analysis-result-heading");
  heading.append(
    element("h3", "", "Your scenario, in perspective."),
    element(
      "span",
      `target-badge ${result.current_bid_meets_targets ? "" : "miss"}`,
      result.current_bid_meets_targets
        ? "Entered bid meets model targets"
        : "Entered bid does not meet model targets",
    ),
  );
  container.append(heading);
  const costWarning = result.limitations.find((note) =>
    note.includes("zero placeholders"),
  );
  if (costWarning)
    container.append(element("p", "zero-cost-warning", costWarning));
  const metrics = element("div", "metrics");
  for (const [label, value, note, css] of [
    [
      "MEDIAN NET PROFIT",
      money(result.profit.p50),
      "After modeled acquisition & selling costs",
      "",
    ],
    [
      "PROBABILITY OF LOSS",
      `${result.loss_probability_pct}%`,
      "For the entered purchase price",
      "",
    ],
    [
      "MEDIAN ROI",
      result.median_roi_pct === null
        ? "Undefined"
        : `${result.median_roi_pct}%`,
      "Profit ÷ modeled total cash cost",
      "",
    ],
  ]) {
    const metric = element("div", `metric ${css}`);
    metric.append(
      element("span", "label", label),
      element("strong", "", value),
      element("small", "", note),
    );
    metrics.append(metric);
  }
  container.append(metrics);
  const chart = element("div", "histogram-panel");
  chart.append(
    element("h4", "", "Range of modeled net profit"),
    element(
      "p",
      "",
      `${result.iterations.toLocaleString()} scenarios · Scenario score ${result.scenario_score ?? "not defined"}/100 (model fit, not property quality)`,
    ),
  );
  const bars = element("div", "histogram");
  bars.setAttribute("role", "img");
  bars.setAttribute(
    "aria-label",
    `Net profit distribution: 10th percentile ${money(result.profit.p10)}, median ${money(result.profit.p50)}, 90th percentile ${money(result.profit.p90)}`,
  );
  const maximum = Math.max(1, ...result.histogram.map((bin) => bin.count));
  for (const bin of result.histogram) {
    const bar = element("div", `bar ${bin.high <= 0 ? "negative" : ""}`);
    bar.style.height = `${Math.max(2, (bin.count / maximum) * 100)}%`;
    bar.title = `${money(bin.low)} – ${money(bin.high)}: ${bin.count} scenarios`;
    bars.append(bar);
  }
  const scale = element("div", "histogram-scale");
  scale.append(
    element("span", "", money(result.histogram[0]?.low)),
    element("span", "", money(result.histogram.at(-1)?.high)),
  );
  chart.append(bars, scale);
  const percentiles = element("div", "percentile-row");
  percentiles.append(
    element("span", "", `Downside P10: ${money(result.profit.p10)}`),
    element("span", "", `Median P50: ${money(result.profit.p50)}`),
    element("span", "", `Upside P90: ${money(result.profit.p90)}`),
  );
  chart.append(percentiles);
  container.append(chart);
  container.append(
    element(
      "p",
      "model-meta",
      `Median acquisition cost: ${money(result.acquisition_cost.p50)} · Loss probability sampling interval: ${result.loss_probability_interval_pct.join("–")}% · ${result.model_version} · Seed ${result.seed}`,
    ),
  );
  const details = element("details", "model-notes");
  details.open = true;
  details.append(element("summary", "", "Model assumptions & limitations"));
  const list = element("ul");
  result.limitations.forEach((note) => list.append(element("li", "", note)));
  details.append(list);
  details.append(
    element(
      "p",
      "",
      "Scenario score = (1 − loss probability) × target-ROI attainment, capped at 100. It is not a forecast, verified property rating, or legal opinion.",
    ),
  );
  container.append(details);
  container.scrollIntoView({
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "auto"
      : "smooth",
    block: "start",
  });
}

function formValues(target: HTMLFormElement): Record<string, string> {
  return Object.fromEntries(
    [...new FormData(target)]
      .filter(([name]) => name !== "zero_cost_ack")
      .map(([key, value]) => [key, String(value)]),
  );
}
function fillForm(
  target: HTMLFormElement,
  values: Record<string, string>,
): void {
  for (const [name, value] of Object.entries(values)) {
    const input = target.elements.namedItem(name);
    if (input instanceof HTMLInputElement || input instanceof HTMLSelectElement)
      input.value = value;
  }
}
function analysisInput(name: string): HTMLInputElement {
  const input = byId<HTMLFormElement>("analysis-form").elements.namedItem(name);
  if (!(input instanceof HTMLInputElement))
    throw new Error(`Missing scenario input: ${name}`);
  return input;
}
function rememberScenario(): void {
  if (!csrf || !currentProperty) return;
  scenarioDrafts.delete(currentProperty.id);
  scenarioDrafts.set(currentProperty.id, {
    values: formValues(byId<HTMLFormElement>("analysis-form")),
    overrides: [...resaleOverrides],
    repairOverrides: [...repairOverrides],
  });
  // Bounded session memory, cleared on sign-out. Never use shared local storage.
  if (scenarioDrafts.size > 50) {
    const oldest = scenarioDrafts.keys().next().value;
    if (oldest) scenarioDrafts.delete(oldest);
  }
}
function applyBidRange(): void {
  const range = bidRange(
    analysisInput(
      resaleOverrides.has("resale_likely") ? "resale_likely" : "purchase_price",
    ).valueAsNumber,
    analysisInput("downside_pct").valueAsNumber,
    analysisInput("upside_pct").valueAsNumber,
  );
  for (const [name, key] of [
    ["resale_low", "low"],
    ["resale_likely", "likely"],
    ["resale_high", "high"],
  ] as const) {
    if (!resaleOverrides.has(name))
      analysisInput(name).value = range ? String(range[key]) : "";
  }
  renderScenarioBasis();
}
function renderScenarioBasis(): void {
  byId("scenario-basis").textContent = resaleOverrides.size
    ? "Your sale estimate is an assumption. Untouched resale bounds follow expected sale; bounds edited in Advanced stay fixed. Reset the range to return to the bid-based starting assumptions."
    : "Hypothetical resale defaults follow the bid, not verified market value. Edit expected sale or expand Advanced. These ranges are not statistical confidence limits or an appraisal.";
  const amount = (name: string) => {
    const value = analysisInput(name).valueAsNumber;
    return Number.isFinite(value) ? money(value) : "Needs estimate";
  };
  byId("scenario-assumptions").textContent =
    `Ranges in use: resale ${amount("resale_low")}–${amount("resale_high")}; repairs ${amount("repairs_low")}–${amount("repairs_high")}. Holding: ${analysisInput("holding_months").value || "Needs estimate"} months. Advanced costs, fees and targets remain included when closed.`;
}
function applyRepairRange(): void {
  const likely = analysisInput("repairs_likely").valueAsNumber;
  for (const name of ["repairs_low", "repairs_high"])
    if (!repairOverrides.has(name))
      analysisInput(name).value =
        Number.isFinite(likely) && likely >= 0 ? String(likely) : "";
}
function updateZeroCostWarning(): void {
  const zero = [
    ...document.querySelectorAll<HTMLInputElement>("[data-unestimated-cost]"),
  ].some((input) => input.valueAsNumber === 0);
  byId("zero-cost-warning").hidden = !zero;
  byId<HTMLInputElement>("zero-cost-ack").required = zero;
}
function invalidateScenario(): void {
  analysisSequence++;
  byId("analysis-results").hidden = true;
  byId("analysis-error").textContent = "";
  byId<HTMLInputElement>("zero-cost-ack").checked = false;
}
byId("reapply-bid-range").addEventListener("click", () => {
  resaleOverrides.clear();
  applyBidRange();
  invalidateScenario();
  rememberScenario();
});
// Edits invalidate any in-flight response and preserve explicit user overrides.
byId("analysis-form").addEventListener("input", (event) => {
  if (
    !(event.target instanceof HTMLInputElement) ||
    event.target.id === "zero-cost-ack"
  )
    return;
  if (resaleNames.includes(event.target.name))
    resaleOverrides.add(event.target.name);
  if (["repairs_low", "repairs_high"].includes(event.target.name))
    repairOverrides.add(event.target.name);
  if (event.target.name === "repairs_likely") applyRepairRange();
  if (
    ["purchase_price", "resale_likely", "downside_pct", "upside_pct"].includes(
      event.target.name,
    )
  )
    applyBidRange();
  renderScenarioBasis();
  invalidateScenario();
  updateZeroCostWarning();
  rememberScenario();
});
const states =
  "AL:Alabama|AK:Alaska|AZ:Arizona|AR:Arkansas|CA:California|CO:Colorado|CT:Connecticut|DE:Delaware|FL:Florida|GA:Georgia|HI:Hawaii|ID:Idaho|IL:Illinois|IN:Indiana|IA:Iowa|KS:Kansas|KY:Kentucky|LA:Louisiana|ME:Maine|MD:Maryland|MA:Massachusetts|MI:Michigan|MN:Minnesota|MS:Mississippi|MO:Missouri|MT:Montana|NE:Nebraska|NV:Nevada|NH:New Hampshire|NJ:New Jersey|NM:New Mexico|NY:New York|NC:North Carolina|ND:North Dakota|OH:Ohio|OK:Oklahoma|OR:Oregon|PA:Pennsylvania|RI:Rhode Island|SC:South Carolina|SD:South Dakota|TN:Tennessee|TX:Texas|UT:Utah|VT:Vermont|VA:Virginia|WA:Washington|WV:West Virginia|WI:Wisconsin|WY:Wyoming";
for (const state of states.split("|")) {
  const [code, name] = state.split(":");
  const option = element("option", "", name);
  option.value = code ?? "";
  byId<HTMLSelectElement>("state").append(option);
  byId<HTMLSelectElement>("coverage-state").append(option.cloneNode(true));
  byId<HTMLFormElement>("hunt-form")
    .querySelector<HTMLSelectElement>('[name="state"]')
    ?.append(option.cloneNode(true));
}
byId("year").textContent = String(new Date().getFullYear());
if (window.matchMedia("(max-width: 800px)").matches) {
  document
    .querySelectorAll<HTMLButtonElement>("[data-view]")
    .forEach((button) =>
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.view === "list"),
      ),
    );
}
const accountLinkOpen = setupAccountActions(api, clearSession);
void (async () => {
  try {
    const info = await api<SessionInfo>("/api/session");
    byId("trial-signup-offer").hidden = !info.feedback_trial_enabled;
    if (info.version) {
      byId("release-version").textContent =
        `v${info.version} · ${info.environment === "production" ? "Production" : "Preview"}`;
    }
    if (info.environment === "staging") {
      const badge = document.querySelector(".environment-tag");
      if (badge) badge.textContent = "STAGING";
    }
    if (info.authenticated && !accountLinkOpen) await enterWorkspace(info);
  } catch {
    byId("auth-message").textContent =
      "Unable to reach LandWolf. Check your connection and try again.";
  }
})();

const huntForm = byId<HTMLFormElement>("hunt-form");
const huntSize = huntForm.elements.namedItem("size") as HTMLSelectElement;
function updateHuntSize(): void {
  byId("hunt-custom-size").hidden = huntSize.value !== "custom";
  for (const name of ["min_acres", "max_acres"]) {
    const field = huntForm.elements.namedItem(name) as HTMLInputElement;
    field.disabled = huntSize.value !== "custom";
    field.required = huntSize.value === "custom";
  }
  if (huntSize.value === "custom")
    byId<HTMLDetailsElement>("hunt-advanced").open = true;
}
huntSize.addEventListener("change", updateHuntSize);
function updateHuntMode(): void {
  const auction =
    (huntForm.elements.namedItem("mode") as HTMLSelectElement).value ===
    "auction";
  byId("hunt-budget-label").textContent = auction
    ? "Maximum opening bid ($, optional)"
    : "Budget ($, optional)";
  byId("hunt-budget-note").textContent = auction
    ? "Auction opening bids can rise. Fees and total purchase costs are not included."
    : "Filters published sale prices. Taxes, fees and other costs are not included.";
  const perAcre = huntForm.elements.namedItem(
    "max_price_per_acre",
  ) as HTMLInputElement;
  perAcre.disabled = auction;
}
function resetHuntForm(): void {
  editingHunt = null;
  editingHuntCriteria = null;
  huntForm.reset();
  const retainedStates = huntForm.querySelector('option[value="retained"]');
  retainedStates?.remove();
  updateHuntSize();
  updateHuntMode();
  byId<HTMLDetailsElement>("hunt-advanced").open = false;
  byId("hunt-submit").textContent = "Save Hunt & view matches";
  byId("hunt-cancel").hidden = true;
}
byId("hunt-cancel").addEventListener("click", () => {
  resetHuntForm();
  byId("hunt-status").textContent = "Edit canceled. Your Hunt is unchanged.";
});
(huntForm.elements.namedItem("mode") as HTMLSelectElement).addEventListener(
  "change",
  updateHuntMode,
);
huntForm.addEventListener(
  "invalid",
  (event) => {
    byId<HTMLDetailsElement>("hunt-advanced").open = true;
    if (event.target instanceof HTMLInputElement)
      byId("hunt-status").textContent = event.target.validationMessage;
  },
  true,
);
for (const button of document.querySelectorAll<HTMLButtonElement>(
  "[data-hunt-preset]",
)) {
  button.addEventListener("click", () => {
    if (huntSaving) return;
    huntSize.value = button.dataset.huntPreset === "large" ? "50-500" : "5-50";
    (huntForm.elements.namedItem("mode") as HTMLSelectElement).value =
      button.dataset.huntPreset === "auction" ? "auction" : "fixed";
    updateHuntSize();
    updateHuntMode();
    byId("hunt-status").textContent =
      "Starter applied. Choose a state and optional budget, then find your land.";
  });
}
updateHuntSize();
updateHuntMode();
function huntCriteria(): HuntCriteria {
  const data = new FormData(huntForm);
  const value = (key: string) => String(data.get(key) ?? "").trim();
  const optional = (key: string) => (value(key) ? Number(value(key)) : null);
  const [minAcres, maxAcres] = acreageRange(
    value("size"),
    value("min_acres"),
    value("max_acres"),
  );
  const selectedStates =
    value("state") === "retained"
      ? editingHuntCriteria?.states || []
      : value("state")
        ? [value("state")]
        : [];
  const radius = optional("radius_miles");
  const hasRadius = ["center_lat", "center_lon", "radius_miles"].some((key) =>
    value(key),
  );
  if (hasRadius && (selectedStates.length || value("county")))
    throw new Error("Choose a state/county or a radius, not both.");
  if (
    hasRadius &&
    ["center_lat", "center_lon", "radius_miles"].some((key) => !value(key))
  )
    throw new Error(
      "For a radius search, enter latitude, longitude and miles.",
    );
  if (value("county") && selectedStates.length !== 1)
    throw new Error("Choose a state before entering a county.");
  return {
    mode: value("mode") as "fixed" | "auction",
    states: selectedStates,
    county: value("county") || null,
    center_lat: optional("center_lat"),
    center_lon: optional("center_lon"),
    radius_miles: radius,
    min_acres: minAcres,
    max_acres: maxAcres,
    max_price: optional("max_price"),
    max_price_per_acre: optional("max_price_per_acre"),
    ...(editingHuntCriteria?.min_acres === minAcres &&
    editingHuntCriteria.max_acres === maxAcres
      ? {
          preferred_min: editingHuntCriteria.preferred_min,
          preferred_max: editingHuntCriteria.preferred_max,
        }
      : {}),
  };
}
async function loadHunts(): Promise<HuntRow[] | null> {
  const token = csrf;
  const sequence = ++huntListSequence;
  try {
    const result = await api<{ hunts: HuntRow[] }>("/api/hunts");
    if (!csrf || csrf !== token || sequence !== huntListSequence) return null;
    const list = byId("hunt-list");
    list.replaceChildren();
    for (const hunt of result.hunts) {
      const card = element("article", "source-card");
      card.append(
        element("h3", "", hunt.name),
        element(
          "p",
          "",
          `${hunt.criteria.mode === "auction" ? "Auction" : "Fixed price"} · ${hunt.criteria.states.join(", ") || "Nationwide"}${hunt.criteria.county ? ` · ${hunt.criteria.county} County` : ""} · ${hunt.criteria.min_acres}–${hunt.criteria.max_acres} acres · ${hunt.active ? "Active" : "Paused"}`,
        ),
      );
      const actions = element("div", "hunt-actions");
      const button = (label: string, action: () => void) => {
        const control = element("button", "button secondary small", label);
        control.type = "button";
        control.addEventListener("click", action);
        actions.append(control);
      };
      button("View matches", () => void showHunt(hunt));
      button("Edit", () => {
        if (huntSaving) return;
        resetHuntForm();
        editingHunt = hunt.id;
        editingHuntCriteria = hunt.criteria;
        if (hunt.criteria.states.length > 1) {
          const option = element("option", "", hunt.criteria.states.join(", "));
          option.value = "retained";
          (huntForm.elements.namedItem("state") as HTMLSelectElement).append(
            option,
          );
        }
        const fields: Record<string, string> = {
          name: hunt.name,
          mode: hunt.criteria.mode,
          state:
            hunt.criteria.states.length > 1
              ? "retained"
              : hunt.criteria.states[0] || "",
          county: hunt.criteria.county || "",
          center_lat: String(hunt.criteria.center_lat ?? ""),
          center_lon: String(hunt.criteria.center_lon ?? ""),
          radius_miles: String(hunt.criteria.radius_miles ?? ""),
          min_acres: String(hunt.criteria.min_acres),
          max_acres: String(hunt.criteria.max_acres),
          max_price: String(hunt.criteria.max_price ?? ""),
          max_price_per_acre: String(hunt.criteria.max_price_per_acre ?? ""),
        };
        const range = `${hunt.criteria.min_acres}-${hunt.criteria.max_acres}`;
        fields.size = Object.hasOwn(acreagePresets, range) ? range : "custom";
        for (const [key, value] of Object.entries(fields)) {
          const field = huntForm.elements.namedItem(key);
          if (
            field instanceof HTMLInputElement ||
            field instanceof HTMLSelectElement
          )
            field.value = value;
        }
        updateHuntSize();
        updateHuntMode();
        byId<HTMLDetailsElement>("hunt-advanced").open = true;
        byId("hunt-submit").textContent = "Save changes to Hunt";
        byId("hunt-cancel").hidden = false;
        byId("hunt-status").textContent =
          `Editing ${hunt.name}. Submit the form to save a new criteria revision.`;
        huntForm.scrollIntoView({ behavior: "smooth" });
      });
      button(
        hunt.active ? "Pause" : "Resume",
        () =>
          void (async () => {
            try {
              await api(`/api/hunts/${hunt.id}`, "PATCH", {
                active: !hunt.active,
              });
              await loadHunts();
            } catch (error) {
              notify(errorText(error));
            }
          })(),
      );
      button(
        "Delete",
        () =>
          void (async () => {
            if (
              !window.confirm(
                `Delete Hunt “${hunt.name}” and its research records?`,
              )
            )
              return;
            try {
              await api(`/api/hunts/${hunt.id}`, "DELETE");
              if (editingHunt === hunt.id) resetHuntForm();
              huntResultSequence++;
              byId("hunt-results").replaceChildren();
              await loadHunts();
            } catch (error) {
              notify(errorText(error));
            }
          })(),
      );
      card.append(actions);
      list.append(card);
    }
    if (!result.hunts.length)
      list.append(
        element(
          "p",
          "muted",
          "No saved Hunts yet. Choose your land preferences above, then select Save Hunt & view matches.",
        ),
      );
    return result.hunts;
  } catch (error) {
    if (csrf && csrf === token && sequence === huntListSequence)
      byId("hunt-status").textContent = errorText(error);
    return null;
  }
}
async function showHunt(hunt: HuntRow, scroll = true): Promise<void> {
  const token = csrf;
  const sequence = ++huntResultSequence;
  const current = () =>
    Boolean(csrf && csrf === token && sequence === huntResultSequence);
  const target = byId("hunt-results");
  target.replaceChildren(
    element("p", "muted", "Checking connected inventory…"),
  );
  try {
    const result = await api<{
      paused: boolean;
      matches: HuntEntry[];
      needs_review: HuntEntry[];
      coverage_note: string;
      evaluated_at: number;
    }>(`/api/hunts/${hunt.id}/matches`);
    if (!current()) return;
    const history = await api<{
      events: { listing_id: string; kind: string; message: string }[];
    }>(`/api/hunts/${hunt.id}/events`);
    if (!current()) return;
    target.replaceChildren(element("h2", "", hunt.name));
    const workspace = element("section", "decision-workspace");
    target.append(workspace);
    void decisions.hunt(workspace, hunt.id);
    if (result.paused) {
      target.append(element("p", "muted", "Hunt is paused."));
      return;
    }
    target.append(
      element(
        "p",
        "muted",
        `${result.matches.length} matches · ${result.needs_review.length} to review. ${result.coverage_note}`,
      ),
    );
    if (history.events.length)
      target.append(
        element("h3", "", "Recent changes"),
        ...history.events
          .slice(0, 10)
          .map((event) =>
            element("p", "", `${event.message} · ${event.listing_id}`),
          ),
      );
    const group = (title: string, rows: HuntEntry[]) => {
      target.append(element("h3", "", title));
      if (!rows.length)
        target.append(
          element("p", "muted", "None in the connected inventory."),
        );
      for (const row of rows.slice(0, 50)) {
        const card = element("article", "source-card hunt-result-card");
        const image = element("div", "hunt-result-photo");
        image.append(photo(row, ""));
        const details = element("div", "hunt-result-details");
        details.append(
          element("h4", "", row.title),
          element(
            "p",
            "",
            `${row.acres ?? "Unknown"} acres · ${money(row.amount)} ${row.price_kind} · ${row.county ? `${row.county}, ` : ""}${row.state}`,
          ),
        );
        if (row.score === null && row.reasons.length)
          details.append(element("p", "muted", row.reasons.join("; ")));
        const link = element(
          "button",
          "button secondary small",
          "View property",
        );
        link.type = "button";
        link.addEventListener(
          "click",
          () =>
            void (async () => {
              try {
                await openDetail(row.listing_id, hunt.id);
              } catch (error) {
                notify(errorText(error));
              }
            })(),
        );
        details.append(link);
        card.append(image, details);
        target.append(card);
      }
      if (rows.length > 50)
        target.append(
          element(
            "p",
            "muted",
            "Showing first 50 results. Narrow the Hunt to review more.",
          ),
        );
    };
    group("Matches", result.matches);
    group("Needs review", result.needs_review);
    if (scroll) target.scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    if (!current()) return;
    const retry = element("button", "button secondary small", "Retry matches");
    retry.type = "button";
    retry.addEventListener("click", () => void showHunt(hunt));
    target.replaceChildren(
      element("p", "form-message", `Your Hunt is saved. ${errorText(error)}`),
      retry,
    );
  }
}
huntForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (huntSaving) return;
  const token = csrf;
  void (async () => {
    try {
      const data = new FormData(huntForm);
      const criteria = huntCriteria();
      const payload = {
        name:
          String(data.get("name") ?? "").trim() ||
          huntName(
            criteria.states.join(", ") ||
              (criteria.radius_miles
                ? `${criteria.radius_miles}-mile radius`
                : "Anywhere"),
            criteria.min_acres,
            criteria.max_acres,
            criteria.mode === "auction",
          ),
        criteria,
      };
      const id = editingHunt;
      huntSaving = true;
      huntForm.setAttribute("aria-busy", "true");
      byId<HTMLButtonElement>("hunt-submit").disabled = true;
      byId<HTMLButtonElement>("hunt-cancel").disabled = true;
      byId("hunt-submit").textContent = "Saving Hunt…";
      byId("hunt-status").textContent = "Saving your Hunt…";
      const saved = await api<HuntRow>(
        id ? `/api/hunts/${id}` : "/api/hunts",
        id ? "PATCH" : "POST",
        payload,
      );
      if (!csrf || csrf !== token) return;
      resetHuntForm();
      const rows = await loadHunts();
      if (!csrf || csrf !== token) return;
      if (!rows?.some((row) => row.id === saved.id)) {
        const message =
          "The server accepted your Hunt, but the saved list could not be verified. Reload the page before saving another copy.";
        byId("hunt-status").textContent = message;
        notify(message);
        return;
      }
      const message = id
        ? "Hunt saved. Your updated preferences are stored in your account."
        : "Hunt saved to your account. Find it in Your saved Hunts below.";
      byId("hunt-status").textContent = message;
      notify(message);
      byId("hunt-status").scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
      // A failed or slow match request is not a failed save. Keep its retry separate.
      await showHunt(saved, false);
    } catch (error) {
      if (!csrf || csrf !== token) return;
      const message = errorText(error);
      byId("hunt-status").textContent = message;
      notify(message);
    } finally {
      huntSaving = false;
      huntForm.setAttribute("aria-busy", "false");
      byId<HTMLButtonElement>("hunt-submit").disabled = false;
      byId<HTMLButtonElement>("hunt-cancel").disabled = false;
      byId("hunt-submit").textContent = editingHunt
        ? "Save changes to Hunt"
        : "Save Hunt & view matches";
    }
  })();
});
