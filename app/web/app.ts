import { setupFocusVisibility } from "./focus-visibility";
import { setupSourceFilter, type SourceOption } from "./source-filter";
import { sourceLink } from "./source-links";
import { setupAppearance } from "./theme";
import { setupCoverage, type CoverageReport } from "./coverage";
import type { Source } from "./source-list";
import { byId, element, scrollBehavior } from "./dom";
import { setupCRM } from "./crm";
import { setupFinance } from "./finance";
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

setupFocusVisibility();

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
const finance = setupFinance(
  <T>(path: string, method?: string, body?: unknown) =>
    api<T>(path, method, body, 60000),
);
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
let mapViewportFrame = 0;
let notificationTimer: ReturnType<typeof setTimeout> | undefined;
let isOwner = false;
const sourceFilter = setupSourceFilter(
  byId<HTMLSelectElement>("state"),
  byId<HTMLSelectElement>("category"),
  byId<HTMLSelectElement>("source-filter"),
);
const coverage = setupCoverage(
  sourceLink,
  (state) => {
    form.reset();
    byId<HTMLSelectElement>("state").value = state;
    sourceFilter.update();
    void navigate("explore");
  },
  () => Boolean(csrf && isOwner && currentView === "sources"),
);
setupAppearance();
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
  seller_listing: "Seller & broker listing",
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
  sourceFilter.clear();
  isOwner = false;
  assistant.clear();
  decisions.clear();
  feedback.clear();
  crm.clear();
  finance.clear();
  byId("crm-nav").hidden = true;
  byId("finance-nav").hidden = true;
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
  coverage.clear();
  isOwner = false;
  byId("coverage-nav").hidden = true;
  byId("source-panel").hidden = true;
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
        finance.clear();
        byId("crm-nav").hidden = true;
        byId("finance-nav").hidden = true;
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

function photo(
  record: Pick<PropertyRecord, "image_url" | "tract">,
  css: string,
): HTMLElement {
  const src = safeImage(record.image_url);
  const img = element("img", css) as HTMLImageElement;
  const fallback = "/assets/no-photo-available.webp";
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
  const sourceChoices = await api<SourceOption[]>("/api/source-options");
  if (!csrf || csrf !== sessionToken) return;
  sourceFilter.load(sourceChoices);
  isOwner = current.is_owner === true;
  byId("coverage-nav").hidden = !isOwner;
  byId("crm-nav").hidden = !isOwner;
  byId("finance-nav").hidden = !isOwner;
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
  if (["sources", "crm", "finance"].includes(view) && !isOwner)
    view = "explore";
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
  if (view !== "finance") finance.clear();
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
  const managingFinance = view === "finance";
  byId("finance-panel").hidden = !managingFinance;
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
    managingContacts ||
    managingFinance;
  byId("workspace-title").textContent = managingFinance
    ? "LandWolf financial management"
    : managingContacts
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
                : "Explore land for sale";
  byId("workspace-description").textContent = managingFinance
    ? "Private revenue, business expenses, and evidence-based growth planning."
    : managingContacts
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
                : "Filter by location, acreage, price or sale type. Check each listing’s source and sale terms.";
  // A tab switch must expose its destination even from a long Research report.
  byId("workspace-title").focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "instant" });
  if (managingFinance) {
    await finance.open();
  } else if (managingContacts) {
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
      const result = await api<CoverageReport>("/api/sources");
      if (!csrf || csrf !== sessionToken || navigation !== navigationSequence)
        return;
      coverage.render(result);
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
  sourceFilter.update();
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
    new ResizeObserver(scheduleMapViewport).observe(byId("property-map"));
  }
  mapRecords = result.map_results;
  mapNeedsFit = true;
  const missing = result.total - result.map_total;
  byId("map-count").textContent =
    result.map_total > result.map_limit
      ? `First ${mapRecords.length} of ${result.map_total} mapped locations · narrow your filters`
      : `${result.map_total} mapped locations · ${missing} without coordinates`;
  renderMapMarkers();
  scheduleMapViewport();
}

function scheduleMapViewport(): void {
  if (mapViewportFrame) return;
  mapViewportFrame = requestAnimationFrame(() => {
    mapViewportFrame = 0;
    updateMapViewport();
  });
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
document
  .querySelectorAll<HTMLButtonElement>("button[data-view]")
  .forEach((button) =>
    button.addEventListener("click", () => {
      byId("results-layout").dataset.view = button.dataset.view;
      document
        .querySelectorAll<HTMLButtonElement>("button[data-view]")
        .forEach((other) => {
          if (other.tagName === "BUTTON")
            other.setAttribute("aria-pressed", String(other === button));
        });
      mapNeedsFit = true;
      scheduleMapViewport();
    }),
  );

function researchMode(): void {
  const address = byId<HTMLSelectElement>("research-mode").value === "address";
  byId("research-address-field").hidden = !address;
  const addressInput = byId<HTMLInputElement>("research-address");
  addressInput.required = address;
  // Hidden nonempty inputs still participate in native constraint validation.
  // Disable only the inactive mode; keep its values for switching back.
  addressInput.disabled = !address;
  byId("research-coordinate-fields").hidden = address;
  for (const id of ["research-latitude", "research-longitude"]) {
    const field = byId<HTMLInputElement>(id);
    field.required = !address;
    field.disabled = address;
  }
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
      byId("decision-workspace").scrollIntoView({ behavior: scrollBehavior() });
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
  if (
    matchMedia("(min-width: 1101px) and (any-pointer: fine)").matches &&
    !matchMedia("(any-pointer: coarse)").matches
  )
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
    .querySelectorAll<HTMLButtonElement>("button[data-view]")
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
        huntForm.scrollIntoView({ behavior: scrollBehavior() });
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
          "No saved Hun…2000 tokens truncated….css" />
    <script type="module" src="/assets/app.js"></script>
  </head>
  <body>
    <a class="skip-link" href="#main">Skip to content</a>
    <header class="site-header">
      <a href="/" class="brand" aria-label="LandWolf home"
        ><picture
          ><source srcset="/assets/landwolf-logo.webp" type="image/webp" />
          <img
            src="/assets/landwolf-logo.jpg"
            alt="LandWolf — Find distressed and acquisition opportunities"
            width="270"
            height="90" /></picture
      ></a>
      <div class="navigation-dock" role="group" aria-label="App dock">
        <button
          type="button"
          class="dock-arrow"
          data-dock-shift="-1"
          aria-label="Previous dock options"
          aria-controls="dock-track"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m14 6-6 6 6 6" />
          </svg>
        </button>
        <div
          id="dock-track"
          role="group"
          class="dock-track"
          aria-label="Swipe, drag or scroll to browse app tools"
        >
          <nav
            class="main-nav"
            aria-label="Main navigation"
            id="main-nav"
            hidden
          >
            <button
              type="button"
              class="nav-link dock-item active"
              data-nav="explore"
              data-dock="explore"
              aria-label="Explore properties"
              title="Explore properties"
            >
              <span class="dock-tile dock-explore"
                ><svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" />
                  <path d="m16 8-2.5 5.5L8 16l2.5-5.5Z" /></svg
              ></span>
              <span class="dock-label" aria-hidden="true">Explore</span
              ><span class="sr-only">Explore properties</span>
            </button>
            <button
              type="button"
              class="nav-link dock-item"
              data-nav="research"
              data-dock="research"
              aria-label="Property research"
              title="Property research"
            >
              <span class="dock-tile dock-research"
                ><svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M13 3H5v18h8M13 3v5h5V3Z M8 7h2M8 11h3" />
                  <circle cx="16" cy="15" r="4" />
                  <path d="m19 18 3 3" /></svg
              ></span>
              <span class="dock-label" aria-hidden="true">Research</span
              ><span class="sr-only">Property research</span>
            </button>
            <button
              type="button"
              class="nav-link dock-item"
              data-nav="hunt"
              data-dock="hunt"
              aria-label="Hunt"
              title="Hunt"
            >
              <span class="dock-tile dock-hunt"
                ><svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m3 11 2-7h4l1 7m4 0 1-7h4l2 7M10 14h4M10 10h4" />
                  <circle cx="6" cy="16" r="4" />
                  <circle cx="18" cy="16" r="4" /></svg
              ></span>
              <span class="dock-label" aria-hidden="true">Hunt</span
              ><span class="sr-only">Hunt</span>
            </button>
            <button
              type="button"
              class="nav-link dock-item"
              data-nav="sources"
              data-dock="sources"
              aria-label="Data coverage"
              title="Data coverage"
              id="coverage-nav"
              hidden
            >
              <span class="dock-tile dock-sources"
                ><svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="m12 3 10 6-10 6L2 9Zm-10 10 10 6 10-6M2 17l10 6 10-6"
                  /></svg
              ></span>
              <span class="dock-label" aria-hidden="true">Coverage</span
              ><span class="sr-only">Data coverage</span>
            </button>
            <button
              type="button"
              class="nav-link dock-item"
              data-nav="feedback"
              data-dock="feedback"
              aria-label="Feedback"
              title="Feedback"
            >
              <span class="dock-tile dock-feedback"
                ><svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M21 11a8 8 0 0 1-8 8H8l-5 3v-8a8 8 0 0 1 8-11h2a8 8 0 0 1 8 8Z"
                  />
                  <path d="M7 9h10M7 13h6" /></svg
              ></span>
              <span class="dock-label" aria-hidden="true">Feedback</span
              ><span class="sr-only">Feedback</span>
            </button>
            <button
              type="button"
              class="nav-link dock-item"
              data-nav="billing"
              data-dock="billing"
              aria-label="Membership"
              title="Membership"
            >
              <span class="dock-tile dock-billing"
                ><svg viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="2" y="4" width="20" height="16" rx="4" />
                  <path d="M2 9h20M6 15h4M15 15h3" /></svg
              ></span>
              <span class="dock-label" aria-hidden="true">Membership</span
              ><span class="sr-only">Membership</span>
            </button>
            <button
              id="crm-nav"
              type="button"
              class="nav-link dock-item"
              data-nav="crm"
              data-dock="crm"
              hidden
              aria-label="L91 LLC CRM"
              title="L91 LLC CRM"
            >
              <span class="dock-tile"
                ><svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.7"
                  aria-hidden="true"
                >
                  <rect x="3" y="3" width="18" height="18" rx="4" />
                  <circle cx="9" cy="9" r="2" />
                  <path
                    d="M5 17c0-4 8-4 8 0M15 8h3M15 12h3M16 16h2"
                  /></svg></span
              ><span class="dock-label">CRM</span>
            </button>
            <button
              id="finance-nav"
              type="button"
              class="nav-link dock-item"
              data-nav="finance"
              data-dock="finance"
              hidden
              aria-label="Owner finances"
              title="Owner finances"
            >
              <span class="dock-tile"
                ><svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.7"
                  aria-hidden="true"
                >
                  <path
                    d="M3 20h18M6 17V9h3v8M11 17V4h3v13M16 17v-6h3v6"
                  /></svg></span
              ><span class="dock-label">Finances</span>
            </button>
          </nav>

          <button
            type="button"
            class="wolf-chat-trigger dock-item"
            data-dock="chat"
            aria-label="AI Chat with Romulus and Remus"
            title="AI Chat with Romulus and Remus"
          >
            <span class="dock-tile dock-chat"
              ><img
                src="/assets/romulus.svg"
                alt=""
                width="28"
                height="28" /><img
                src="/assets/remus.svg"
                alt=""
                width="28"
                height="28"
            /></span>
            <span class="dock-label" aria-hidden="true">AI Chat</span
            ><span class="sr-only">AI Chat with Romulus and Remus</span>
          </button>
        </div>
        <button
          type="button"
          class="dock-arrow"
          data-dock-shift="1"
          aria-label="Next dock options"
          aria-controls="dock-track"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m10 6 6 6-6 6" />
          </svg>
        </button>
      </div>
      <div class="account-tools">
        <label class="theme-control">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="8" />
            <path
              d="M12 4v16a8 8 0 0 0 0-16Z"
              fill="currentColor"
              stroke="none"
            />
          </svg>
          <span class="sr-only">Appearance</span>
          <select id="appearance" aria-label="Appearance">
            <option value="system">Auto</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </label>
        <button id="signout" class="button quiet small" hidden>Sign out</button>
      </div>
    </header>
    <main id="main" tabindex="-1">
      <section id="auth-view" class="auth-layout">
        <div class="auth-story">
          <div class="story-shade"></div>
          <div class="story-copy">
            <p class="eyebrow light">PROPERTY INTELLIGENCE, WITH PERSPECTIVE</p>
            <h1>
              Find the land.<br /><span class="story-heading-line"
                >Understand</span
              >
              <em>the opportunity.</em>
            </h1>
            <p>
              Explore source-backed listings. Investigate the risks. Know your
              numbers before you make a move.
            </p>
            <div class="story-features">
              <span>Official-source records</span
              ><span>Transparent deal scenarios</span
              ><span>Source-backed research</span>
            </div>
          </div>
          <p class="photo-credit">
            Land photography: Texas General Land Office
          </p>
        </div>
        <div class="auth-panel">
          <div class="auth-content">
            <p class="eyebrow">WELCOME TO LANDWOLF</p>
            <h2 id="auth-title">
              Your next opportunity
              <span class="auth-heading-line">starts here.</span>
            </h2>
            <p class="muted">
              Sign in to search, research properties, and run deal scenarios.
              Build a clearer picture before you make a move.
            </p>
            <p class="muted">
              Standard memberships cost $29/month or $299/year. Invited pilots
              and owner-granted complimentary accounts have separate terms.
              Creating an account alone never starts billing.
            </p>
            <p id="facebook-trial-offer" class="muted" hidden>
              Thanks for considering our feedback trial. The survey requirements
              and billing protections are explained below.
            </p>
            <p class="muted" id="trial-signup-offer" hidden>
              Eligible new users can choose up to 90 days of free access after
              signup. Saving a payment method with Stripe does not start a
              charge. To keep the promotional access, complete brief, honest
              feedback check-ins on days 30, 60 and 90. Miss a check-in? We'll
              email you at least seven days before any potential $29/month
              billing, with the exact start date and a chance to complete
              feedback or cancel online. No retroactive trial charges. Complete
              all three surveys, and the trial ends without automatic billing.
              You can choose a paid plan separately.
              <a href="/trial-terms">Read full trial terms</a>.
            </p>
            <div
              class="segmented auth-tabs"
              role="group"
              aria-label="Account action"
            >
              <button id="login-tab" aria-pressed="true">Sign in</button
              ><button id="register-tab" aria-pressed="false">
                Create account
              </button>
            </div>
            <form id="auth-form">
              <label for="email">Email address</label
              ><input
                id="email"
                aria-describedby="auth-message"
                name="email"
                type="email"
                maxlength="254"
                autocomplete="username"
                placeholder="you@example.com"
                required
              />
              <label for="password">Password</label
              ><input
                id="password"
                aria-describedby="password-help auth-message"
                name="password"
                type="password"
                minlength="12"
                maxlength="128"
                autocomplete="current-password"
                placeholder="At least 12 characters"
                required
              />
              <p id="password-help" class="input-note">
                Use a unique password of 12–128 characters.
              </p>
              <fieldset
                id="registration-profile"
                class="registration-profile"
                hidden
                disabled
              >
                <legend>Tell us about yourself</legend>
                <label for="signup-name">Full name</label
                ><input
                  id="signup-name"
                  autocomplete="name"
                  maxlength="120"
                  required
                />
                <label for="signup-use">How will you use LandWolf?</label
                ><select id="signup-use" required>
                  <option value="">Choose your primary use</option>
                  <option value="investing">Find investment properties</option>
                  <option value="research">Research land or property</option>
                  <option value="deal_analysis">Evaluate deals</option>
                  <option value="client_work">Support clients</option>
                  <option value="development">
                    Plan development or construction
                  </option>
                  <option value="personal">Find land for personal use</option>
                  <option value="exploring">Explore the tool</option>
                  <option value="other">Other</option>
                </select>
                <div class="signup-grid">
                  <label
                    >Company (optional)<input
                      id="signup-company"
                      autocomplete="organization"
                      maxlength="160"
                  /></label>
                  <label
                    >Job title (optional)<input
                      id="signup-title"
                      autocomplete="organization-title"
                      maxlength="120"
                  /></label>
                  <label
                    >Phone (optional)<input
                      id="signup-phone"
                      type="tel"
                      autocomplete="tel"
                      maxlength="32"
                      placeholder="+1 555 010 1234"
                  /></label>
                  <div>
                    <label for="signup-industry">Industry (optional)</label
                    ><select id="signup-industry">
                      <option value="">Choose industry</option>
                      <option value="real_estate">Real estate</option>
                      <option value="construction">
                        Construction &amp; trades
                      </option>
                      <option value="woodworking">
                        Woodworking &amp; manufacturing
                      </option>
                      <option value="technology">Technology &amp; AI</option>
                      <option value="finance">Finance &amp; lending</option>
                      <option value="professional_services">
                        Professional services
                      </option>
                      <option value="personal">Personal use</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label for="signup-type"
                    >Which best describes you? (optional)</label
                  ><select id="signup-type">
                    <option value="">Choose role</option>
                    <option value="investor">Investor</option>
                    <option value="agent">Agent / broker</option>
                    <option value="developer">Developer / builder</option>
                    <option value="lender">Lender</option>
                    <option value="business_owner">Business owner</option>
                    <option value="individual">Individual</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <label
                  >Anything else about your goals? (optional)<textarea
                    id="signup-details"
                    maxlength="1000"
                    rows="2"
                  ></textarea>
                </label>
                <p class="input-note">
                  L91 LLC uses these details to manage your account, provide
                  support, and understand how you use LandWolf. Your profile is
                  private to the owner. Contact support.landwolf@gmail.com for
                  access, correction, deletion, or to withdraw email permission.
                </p>
                <label class="signup-consent"
                  ><input id="signup-marketing" type="checkbox" />Email me
                  LandWolf product news and offers. I can unsubscribe by
                  contacting support.</label
                >
                <p class="input-note">
                  Optional. Creating an account does not authorize marketing
                  calls or texts.
                </p>
              </fieldset>
              <button
                id="auth-submit"
                class="button primary full"
                type="submit"
              >
                Sign in to LandWolf <span aria-hidden="true">→</span>
              </button>
              <p id="auth-message" class="form-message" role="alert"></p>
            </form>
            <p class="auth-support">
              <button type="button" class="text-button" id="forgot-password">
                Forgot password?
              </button>
              Need help accessing your account?
              <a href="mailto:support.landwolf@gmail.com">Contact support</a>.
            </p>
            <div class="membership-note">
              <span class="membership-note-icon" aria-hidden="true">↗</span>
              <div>
                <strong>Research US land before you bid.</strong>
                <p>
                  Search all 50 states. Connected government sources provide
                  land, foreclosure and auction records; coverage varies by
                  source.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="workspace" class="workspace" hidden>
        <div class="workspace-heading">
          <div>
            <p class="eyebrow" id="workspace-eyebrow">LandWolf</p>
            <h2 id="workspace-title" tabindex="-1" aria-level="1">
              Explore land for sale
            </h2>
            <p class="muted" id="workspace-description">
              Filter by location, acreage, price or sale type. Check each
              listing’s source and sale terms.
            </p>
          </div>
          <div class="signed-in">
            <span class="account-avatar" aria-hidden="true">LW</span>
            <div>
              <span>YOUR WORKSPACE</span><strong id="account-email"></strong>
            </div>
          </div>
        </div>

        <section
          id="crm-panel"
          hidden
          aria-label="Customer relationship management"
        ></section>
        <section
          id="finance-panel"
          hidden
          aria-label="Owner financial dashboard"
        ></section>

        <div class="email-verification" aria-live="polite">
          <span id="email-status"></span>
          <button type="button" class="text-button" id="verify-email" hidden>
            Verify email
          </button>
        </div>

        <aside
          id="feedback-notice"
          class="feedback-notice"
          role="status"
          hidden
        >
          <span id="feedback-notice-text"></span>
          <button
            type="button"
            class="button secondary small"
            data-nav="feedback"
          >
            Review feedback pilot
          </button>
        </aside>
        <section
          id="billing-panel"
          class="source-panel"
          hidden
          aria-label="Membership and billing"
        >
          <div id="billing-content"></div>
        </section>
        <section
          id="feedback-panel"
          class="source-panel"
          hidden
          aria-label="Investor feedback"
        >
          <div id="feedback-content"></div>
          <section
            id="feedback-admin"
            hidden
            aria-label="Owner feedback administration"
          ></section>
        </section>
        <section
          id="source-panel"
          class="source-panel"
          hidden
          aria-labelledby="coverage-title"
        >
          <p class="eyebrow">KNOW WHAT YOU'RE SEARCHING</p>
          <h2 id="coverage-title">Data sources</h2>
          <p>
            Connected means LandWolf can retrieve listings from that source. A
            successful retrieval does not verify title, liens, market value, or
            continued availability.
          </p>
          <div class="coverage-filters">
            <div class="field">
              <label for="coverage-state">Coverage state</label
              ><select id="coverage-state">
                <option value="US">All 50 states</option>
              </select>
            </div>
            <div class="field">
              <label for="coverage-category">Sale type coverage</label
              ><select id="coverage-category">
                <option value="all">All sale types</option>
                <option value="government_land">
                  DNR &amp; government land
                </option>
                <option value="seller_listing">
                  Seller &amp; broker listings
                </option>
                <option value="tax_sale">Tax sales</option>
                <option value="foreclosure">Foreclosure / REO</option>
                <option value="pre_foreclosure">Pre-foreclosure notices</option>
                <option value="surplus">Public surplus</option>
                <option value="public_auction">Public auctions</option>
              </select>
            </div>
          </div>
          <p class="source-health-legend">
            Green: ≤24 hours · Yellow: &gt;24 to &lt;36 hours · Red: ≥36 hours
            or no successful update. Gray: directory only. Times use your
            device’s time zone. Select a source for details.
          </p>
          <div
            id="source-cards"
            role="region"
            aria-label="Source freshness"
          ></div>
          <details class="feature-roadmap">
            <summary>Development roadmap</summary>
            <div id="feature-roadmap"></div>
          </details>
          <div class="coverage-next">
            <h3>Public property research</h3>
            <p>
              Use Property research to look up a street address or coordinates.
              These reference databases do not add sale listings or establish
              market value. Live MLS is not connected: MLS providers require
              data-access authorization. No paid API subscriptions are enabled.
            </p>
            <div id="research-catalog"></div>
          </div>
          <div class="coverage-next">
            <h3>All 50 states. Explicit coverage limits.</h3>
            <p>
              Federal feeds accept all 50 states, but may have no current
              records in a state. State and county inventories are partial.
              Arkansas county tax-delinquent auctions are connected; tax-lien
              certificate and nationwide pre-foreclosure feeds are not
              connected. IRS tax-seizure auctions are a separate sale type. A
              default notice does not establish an offer to sell or an auction
              date.
            </p>
            <p>
              Directory links open official sites and do not add listings.
              Counts below include current records across all connected
              categories, exclude past auction dates and bid deadlines, and do
              not establish full market coverage.
            </p>
            <div
              id="state-coverage"
              class="table-scroll"
              role="region"
              aria-label="State coverage; scroll horizontally for all columns"
              tabindex="0"
            ></div>
            <details class="county-coverage">
              <summary>Inspect observed county coverage</summary>
              <div id="county-coverage"></div>
            </details>
          </div>
        </section>

        <section
          id="research-panel"
          class="source-panel research-panel"
          hidden
          aria-labelledby="research-title"
        >
          <p class="eyebrow">PUBLIC RECORDS • PROPERTY RESEARCH</p>
          <h2 id="research-title">A closer look at a location.</h2>
          <p>
            Look up geographic identifiers, flood mapping, elevation, soils and
            available parcel records. Coverage varies by source. This does not
            establish that a property is for sale.
          </p>
          <div
            id="research-property-context"
            class="research-property-context"
          ></div>
          <button
            id="research-new"
            type="button"
            class="button secondary research-new"
          >
            New research
          </button>
          <form
            id="research-form"
            class="research-form"
            aria-label="Public property research"
          >
            <div class="field">
              <label for="research-mode">Research by</label>
              <select id="research-mode">
                <option value="address">Street address</option>
                <option value="coordinates">Coordinates</option>
              </select>
            </div>
            <div id="research-address-field" class="field">
              <label for="research-address"
                >Street address, city, state and ZIP</label
              >
              <input
                id="research-address"
                aria-describedby="research-status"
                minlength="8"
                maxlength="240"
                autocomplete="off"
                placeholder="e.g. 1500 Marilla St, Dallas, TX 75201"
                required
              />
            </div>
            <div
              id="research-coordinate-fields"
              class="research-coordinates"
              hidden
            >
              <div class="field">
                <label for="research-latitude">Latitude</label
                ><input
                  id="research-latitude"
                  aria-describedby="research-status"
                  type="number"
                  min="-90"
                  max="90"
                  step="any"
                  placeholder="32.7767"
                />
              </div>
              <div class="field">
                <label for="research-longitude">Longitude</label
                ><input
                  id="research-longitude"
                  aria-describedby="research-status"
                  type="number"
                  min="-180"
                  max="180"
                  step="any"
                  placeholder="-96.7970"
                />
              </div>
            </div>
            <button id="research-submit" class="button primary" type="submit">
              Research location
            </button>
          </form>
          <p class="input-note">
            Addresses are sent to the U.S. Census Geocoder; resolved coordinates
            are sent to the public data sources. Census address points are
            approximate and may fall on a road or neighboring parcel. Use a
            verified point for parcel research.
          </p>
          <p id="research-status" role="status" aria-live="polite"></p>
          <div id="research-results"></div>
        </section>

        <section
          id="hunt-panel"
          class="source-panel"
          hidden
          aria-labelledby="hunt-title"
        >
          <h2 id="hunt-title">Create a saved Hunt</h2>
          <p class="muted">
            Choose where and how much land. Save your Hunt to see matches now
            and check again later. You can save up to three Hunts.
          </p>
          <div class="hunt-actions" role="group" aria-label="Quick starters">
            <button
              type="button"
              class="button secondary small"
              data-hunt-preset="acreage"
            >
              5–50 acres
            </button>
            <button
              type="button"
              class="button secondary small"
              data-hunt-preset="large"
            >
              Larger tracts
            </button>
            <button
              type="button"
              class="button secondary small"
              data-hunt-preset="auction"
            >
              Auction hunt
            </button>
          </div>
          <form id="hunt-form" class="hunt-form">
            <label
              >Where
              <select name="state" aria-describedby="hunt-coverage-note">
                <option value="">Anywhere in connected inventory</option>
              </select>
            </label>
            <label
              >How much land?
              <select name="size">
                <option value="5-50">5–50 acres</option>
                <option value="0.01-5">0.01–5 acres</option>
                <option value="50-500">50–500 acres</option>
                <option value="500-10000000">500+ acres</option>
                <option value="custom">Custom range</option>
              </select>
            </label>
            <label
              ><span id="hunt-budget-label">Budget ($, optional)</span>
              <input
                name="max_price"
                type="number"
                min="1"
                max="1000000000"
                step="any"
                placeholder="Maximum dollars"
                aria-describedby="hunt-budget-note"
              />
            </label>
            <p id="hunt-budget-note" class="input-note hunt-wide"></p>
            <details id="hunt-advanced" class="hunt-advanced">
              <summary>More options</summary>
              <div class="hunt-advanced-fields">
                <label
                  >Hunt name (optional)
                  <input
                    name="name"
                    maxlength="80"
                    placeholder="We'll name it for you"
                  />
                </label>
                <label
                  >Sale type
                  <select name="mode">
                    <option value="fixed">Published sale price</option>
                    <option value="auction">Auction opening bid</option>
                  </select>
                </label>
                <label
                  >County (choose a state first)
                  <input name="county" maxlength="100" />
                </label>
                <div id="hunt-custom-size" class="hunt-size-fields" hidden>
                  <label
                    >Minimum acres
                    <input
                      name="min_acres"
                      type="number"
                      min="0.0001"
                      max="10000000"
                      step="any"
                      value="5"
                  /></label>
                  <label
                    >Maximum acres
                    <input
                      name="max_acres"
                      type="number"
                      min="0.0001"
                      max="10000000"
                      step="any"
                      value="50"
                  /></label>
                </div>
                <label
                  >Radius center latitude
                  <input
                    name="center_lat"
                    type="number"
                    min="-90"
                    max="90"
                    step="any"
                  />
                </label>
                <label
                  >Radius center longitude
                  <input
                    name="center_lon"
                    type="number"
                    min="-180"
                    max="180"
                    step="any"
                  />
                </label>
                <label
                  >Radius miles (maximum 500)
                  <input
                    name="radius_miles"
                    type="number"
                    min="0.01"
                    max="500"
                    step="any"
                  />
                </label>
                <label
                  >Maximum asking price per acre ($, fixed-price only)
                  <input
                    name="max_price_per_acre"
                    type="number"
                    min="1"
                    max="1000000000"
                    step="any"
                  />
                </label>
              </div>
              <p class="input-note">
                For a radius search, choose Anywhere, leave county blank, and
                enter all three radius fields. The center is a search location,
                not a parcel boundary.
              </p>
            </details>
            <div class="hunt-actions hunt-wide">
              <button id="hunt-submit" class="button primary" type="submit">
                Save Hunt &amp; view matches
              </button>
              <button
                id="hunt-cancel"
                class="button secondary"
                type="button"
                hidden
              >
                Cancel edit
              </button>
            </div>
          </form>
          <p id="hunt-coverage-note" class="input-note">
            Searches only the connected public inventory; coverage varies by
            state.
          </p>
          <p class="input-note">
            Auction opening bids are not total purchase costs. No email delivery
            is configured for Hunt; check this page for updates.
          </p>
          <p id="hunt-status" role="status" aria-live="polite"></p>
          <h3 id="saved-hunts-title">Your saved Hunts</h3>
          <div id="hunt-list" class="hunt-list"></div>
          <div id="hunt-results"></div>
        </section>

        <section id="explore-panel">
          <form
            id="search-form"
            class="search-bar"
            aria-label="Property search"
          >
            <div class="field location-field">
              <label for="location">County, tract, or location</label
              ><input
                id="location"
                name="location"
                maxlength="100"
                placeholder="e.g. Eastland, 14968"
              />
            </div>
            <div class="field">
              <label for="state">State</label
              ><select id="state" name="state">
                <option value="US">All 50 states</option>
              </select>
            </div>
            <div class="field">
              <label for="min-acres">Min. acres</label
              ><input
                id="min-acres"
                name="min_acres"
                type="number"
                min="0"
                max="10000000"
                step="0.01"
                placeholder="Any size"
              />
            </div>
            <div class="field">
              <label for="max-price">Max. published price / bid</label
              ><input
                id="max-price"
                name="max_price"
                type="number"
                min="0"
                max="1000000000"
                step="1"
                placeholder="No maximum"
              />
            </div>
            <div class="field">
              <label for="category">Category</label
              ><select id="category" name="category">
                <option value="all">All sale types</option>
                <option value="government_land">
                  DNR &amp; government land
                </option>
                <option value="seller_listing">
                  Seller &amp; broker listings
                </option>
                <option value="tax_sale">Tax sales</option>
                <option value="foreclosure">Foreclosure / REO</option>
                <option value="pre_foreclosure">Pre-foreclosure notices</option>
                <option value="surplus">Public surplus</option>
                <option value="public_auction">Public auctions</option>
              </select>
            </div>
            <button
              class="button primary search-submit"
              id="search-submit"
              type="submit"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="10.5" cy="10.5" r="6.5" />
                <path d="m16 16 5 5" /></svg
              >Search
            </button>
          </form>
          <div class="source-filter-row">
            <label for="source-filter">Data source</label>
            <select id="source-filter" name="source" form="search-form">
              <option value="">All matching sources</option>
            </select>
            <span
              >Price and acreage filters exclude unknown values. Check bid type
              and dates in each listing.</span
            >
          </div>
          <details id="publisher-searches" hidden>
            <summary>Browse selected publisher</summary>
            <p id="publisher-search-note"></p>
            <ul id="publisher-search-links"></ul>
          </details>
          <div class="coverage-strip">
            <p id="source-summary">Loading listings…</p>
            <button id="refresh-results" class="text-button">
              Refresh results
            </button>
          </div>
          <p id="workspace-error" class="form-message" role="alert"></p>
          <button
            id="workspace-retry"
            type="button"
            class="button secondary"
            hidden
          >
            Retry loading properties
          </button>
          <div class="results-toolbar">
            <div>
              <h2 id="results-title">Property results</h2>
              <p
                id="results-subtitle"
                role="status"
                aria-live="polite"
                aria-atomic="true"
              >
                Search the connected inventory to begin.
              </p>
            </div>
            <div class="results-controls">
              <label for="sort" class="sr-only">Sort properties</label
              ><select id="sort">
                <option value="price_asc">Price: low to high</option>
                <option value="price_desc">Price: high to low</option>
                <option value="acres_desc">Largest acreage</option>
                <option value="county">County A–Z</option>
              </select>
              <div
                class="segmented view-tabs"
                role="group"
                aria-label="Results layout"
              >
                <button data-view="split" aria-pressed="true">Split</button
                ><button data-view="list" aria-pressed="false">List</button
                ><button data-view="map" aria-pressed="false">Map</button>
              </div>
            </div>
          </div>
          <div id="empty-state" class="empty-state" hidden>
            <span class="empty-mark" aria-hidden="true">⌕</span>
            <h3 id="empty-title"></h3>
            <p id="empty-description"></p>
            <button id="reset-filters" class="button secondary">
              Reset filters
            </button>
          </div>
          <div id="results-layout" class="results-layout" data-view="split">
            <div
              id="property-list"
              class="property-list"
              aria-live="polite"
            ></div>
            <div class="map-panel">
              <div class="map-label">
                <span>PROPERTY MAP</span><span id="map-count"></span>
              </div>
              <div
                id="property-map"
                role="region"
                aria-describedby="map-alternative"
                aria-label="Map of source-reported property locations"
              ></div>
              <div id="map-warning" class="map-warning" hidden></div>
              <div class="map-footer" id="map-alternative">
                Use the List button above for keyboard-accessible property
                details, including properties without map coordinates. Source
                locations across your filtered search, independent of list
                pages. Listings without coordinates remain in the list. Location
                points, not surveyed boundaries.
                <a
                  href="https://www.openstreetmap.org/fixthemap"
                  target="_blank"
                  rel="noopener noreferrer"
                  >Report a map issue</a
                >
              </div>
            </div>
          </div>
          <div class="pagination" id="pagination" hidden>
            <button id="previous" class="button secondary small">
              ← Previous
            </button>
            <p id="page-label"></p>
            <button id="next" class="button secondary small">Next →</button>
          </div>
        </section>
      </section>
    </main>
    <dialog
      id="account-dialog"
      class="account-dialog"
      aria-labelledby="account-action-title"
    >
      <button type="button" id="close-account-action" class="button quiet">
        Close
      </button>
      <button type="button" class="wolf-chat-trigger text-button">
        AI Chat with Romulus and Remus
      </button>
      <h2 id="account-action-title">Reset your password</h2>
      <form id="account-action-form">
        <label id="account-action-label" for="account-action-input"
          >Account email address</label
        >
        <input
          id="account-action-input"
          type="email"
          autocomplete="email"
          required
        />
        <button id="account-action-submit" type="submit" class="button primary">
          Request reset email
        </button>
        <p id="account-action-message" class="form-message" role="status"></p>
      </form>
      <p class="input-note">
        Links expire after 30 minutes. Password resets sign out all existing
        sessions.
      </p>
    </dialog>

    <dialog
      id="property-dialog"
      class="property-dialog"
      aria-labelledby="detail-title"
    >
      <div class="detail-topbar">
        <div id="detail-actions" class="detail-actions"></div>
        <button type="button" class="wolf-chat-trigger text-button">
          AI Chat with Romulus and Remus
        </button>
        <button
          id="close-detail"
          class="icon-button"
          aria-label="Close property details"
        >
          ×
        </button>
      </div>
      <div id="detail-content"></div>
      <section
        id="decision-workspace"
        class="decision-workspace"
        aria-label="Decision research workspace"
      ></section>
      <section class="analysis-section" aria-labelledby="analysis-title">
        <div class="analysis-intro">
          <p class="eyebrow">THE NUMBERS BEHIND THE OPPORTUNITY</p>
          <h2 id="analysis-title">Build your deal scenario.</h2>
          <p>
            A quick check of your purchase, sale and costs. Expand Advanced
            whenever you want more control.
          </p>
          <p id="scenario-property-context" class="input-note"></p>
        </div>
        <form id="analysis-form" novalidate>
          <fieldset class="analysis-basics">
            <legend>Start with four figures</legend>
            <div class="analysis-grid">
              <label
                >Purchase / bid price ($)<input
                  name="purchase_price"
                  type="number"
                  min="0"
                  max="1000000000"
                  step="0.01"
                  required
              /></label>
              <label
                >Expected sale price ($)<input
                  name="resale_likely"
                  step="0.01"
                  type="number"
                  min="0.01"
                  max="1000000000"
                  placeholder="Your base estimate"
                  required
              /></label>
              <label
                >Repairs / improvements ($)<input
                  name="repairs_likely"
                  value="0"
                  data-unestimated-cost
                  step="0.01"
                  type="number"
                  min="0"
                  max="1000000000"
                  required
                  placeholder="Your estimate"
              /></label>
              <label
                >Title &amp; closing costs ($)<input
                  name="closing_costs"
                  value="0"
                  data-unestimated-cost
                  step="0.01"
                  type="number"
                  min="0"
                  max="1000000000"
                  required
                  placeholder="Your estimate"
              /></label>
            </div>
            <p class="input-note">
              Enter your estimates, then calculate. Expected sale starts at the
              bid; the initial resale range is −5% / +20%. Repairs use your
              entered budget unless you adjust their range in Advanced.
            </p>
            <p id="scenario-basis" class="input-note" role="status"></p>
            <p id="scenario-assumptions" class="input-note"></p>
          </fieldset>
          <details id="analysis-advanced" class="analysis-advanced">
            <summary>Advanced</summary>
            <p class="input-note">
              Adjust ranges, fees, financing and investment targets. These
              values remain included when Advanced is closed.
            </p>
            <fieldset>
              <legend>Resale range</legend>
              <div class="analysis-grid">
                <label
                  >Resale — low ($)<input
                    name="resale_low"
                    step="0.01"
                    type="number"
                    min="0.01"
                    max="1000000000"
                    placeholder="Your conservative estimate"
                    required
                /></label>
                <label
                  >Resale — high ($)<input
                    name="resale_high"
                    step="0.01"
                    type="number"
                    min="0.01"
                    max="1000000000"
                    placeholder="Your upside estimate"
                    required
                /></label>
                <label
                  >Downside below expected sale (%)<input
                    name="downside_pct"
                    type="number"
                    min="0"
                    max="99.9"
                    step="0.1"
                    value="5"
                    required
                /></label>
                <label
                  >Upside above expected sale (%)<input
                    name="upside_pct"
                    type="number"
                    min="0"
                    max="1000"
                    step="0.1"
                    value="20"
                    required
                /></label>
              </div>
              <button id="reapply-bid-range" type="button" class="text-button">
                Reset expected sale and range to the bid
              </button>
            </fieldset>
            <fieldset>
              <legend>Repair uncertainty</legend>
              <div class="analysis-grid">
                <label
                  >Repairs — low ($)<input
                    name="repairs_low"
                    value="0"
                    data-unestimated-cost
                    step="0.01"
                    type="number"
                    min="0"
                    max="1000000000"
                    required
                    placeholder="Your estimate"
                /></label>
                <label
                  >Repairs — high ($)<input
                    name="repairs_high"
                    value="0"
                    data-unestimated-cost
                    step="0.01"
                    type="number"
                    min="0"
                    max="1000000000"
                    required
                    placeholder="Your estimate"
                /></label>
              </div>
              <p class="input-note">
                Low and high follow the repairs budget until you edit them here.
                Changing or closing Advanced never discards your edits.
              </p>
            </fieldset>
            <fieldset>
              <legend>Fees, holding costs &amp; financing</legend>
              <div class="analysis-grid">
                <label
                  >Liens / back-tax reserve ($)<input
                    name="lien_reserve"
                    value="0"
                    data-unestimated-cost
                    step="0.01"
                    type="number"
                    min="0"
                    max="1000000000"
                    required
                    placeholder="Not independently verified"
                /></label>
                <label
                  >Monthly holding cost ($)<input
                    name="monthly_holding"
                    value="0"
                    data-unestimated-cost
                    step="0.01"
                    type="number"
                    min="0"
                    max="1000000"
                    required
                    placeholder="Include property taxes"
                /></label>
                <label
                  >Holding period (months)<input
                    name="holding_months"
                    data-unestimated-cost
                    type="number"
                    min="0"
                    max="120"
                    value="0"
                    required
                /></label>
                <label
                  >Buyer auction fee (%)<input
                    name="buyer_premium_pct"
                    value="0"
                    data-unestimated-cost
                    type="number"
                    min="0"
                    max="50"
                    step="0.1"
                    required
                    placeholder="Check seller terms"
                /></label>
                <label
                  >Selling costs (%)<input
                    name="selling_cost_pct"
                    data-unestimated-cost
                    type="number"
                    min="0"
                    max="50"
                    step="0.1"
                    value="0"
                    required
                /></label>
                <label
                  >Financing APR (%)<input
                    name="annual_financing_pct"
                    value="0"
                    data-unestimated-cost
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    required
                    placeholder="0 for cash purchase"
                /></label>
              </div>
              <p class="input-note">
                Unestimated costs start at 0; these are placeholders, not
                verified zero costs. Add researched costs and reserves.
                Financing uses simple interest on the full bid. Include taxes,
                insurance and maintenance in monthly holding costs;
                source-reported taxes are not verified surviving liens or annual
                tax estimates.
              </p>
            </fieldset>
            <fieldset>
              <legend>Your investment targets</legend>
              <p class="input-note">
                Editable preferences, not estimates of this property.
              </p>
              <div class="analysis-grid">
                <label
                  >Target median ROI (%)<input
                    name="target_roi_pct"
                    type="number"
                    min="0"
                    max="200"
                    value="20"
                    step="0.1"
                    required
                /></label>
                <label
                  >Minimum median profit ($)<input
                    name="min_profit"
                    type="number"
                    min="0"
                    max="1000000000"
                    value="25000"
                    required
                /></label>
                <label
                  >Maximum loss probability (%)<input
                    name="max_loss_probability_pct"
                    type="number"
                    min="0"
                    max="50"
                    value="10"
                    step="0.1"
                    required
                /></label>
                <label
                  >Reproducibility seed<input
                    name="seed"
                    type="number"
                    min="0"
                    max="4294967295"
                    value="847291"
                    required
                /></label>
              </div>
            </fieldset>
          </details>
          <div id="zero-cost-warning" class="zero-cost-warning">
            <p>
              Zero-cost assumptions omit expenses and may overstate returns. A
              zero holding period also removes modeled holding and financing
              costs.
            </p>
            <label
              ><input
                id="zero-cost-ack"
                name="zero_cost_ack"
                type="checkbox"
                required
              />
              I understand that zero values exclude costs and may not reflect
              this property.</label
            >
          </div>
          <div class="analysis-actions">
            <button id="run-analysis" class="button primary" type="submit">
              Calculate deal <span aria-hidden="true">→</span></button
            ><span
              >10,000 illustrative scenarios · Assumptions are editable.</span
            >
          </div>
          <p id="analysis-error" class="form-message" role="alert"></p>
        </form>
        <div id="analysis-results" aria-live="polite" hidden></div>
      </section>
    </dialog>
    <div id="toast" class="toast" role="status" hidden></div>
    <footer class="site-footer">
      <span>
        © <span id="year"></span> L91 LLC · LandWolf<br />
        <a
          id="release-version"
          href="https://github.com/lupu-spec/Landwolf/blob/main/RELEASES.md"
          target="_blank"
          rel="noopener noreferrer"
          >Version history ↗</a
        >
      </span>
      <p>
        Research tools, not investment or legal advice. Verify records and sale
        terms with the original source.
      </p>
      <nav aria-label="Public resources">
        <a href="/land-investing">Land research checklist</a> ·
        <a href="/faq">FAQ</a> · <a href="/about">About LandWolf</a> ·
        <a href="/trial-terms">Trial terms</a> ·
        <a href="/accessibility">Accessibility</a> ·
        <a href="/lupuspec">LupuSpec</a> ·
        <a
          href="https://l91-audit-desk.secret-hen-4327.chatgpt.site"
          target="_blank"
          rel="noopener noreferrer"
          >Audit Desk ↗</a
        >
        ·
        <a
          href="https://lupu-retail-watch.secret-hen-4327.chatgpt.site"
          target="_blank"
          rel="noopener noreferrer"
          >Retail Watch</a
        >
      </nav>
      <a href="mailto:support.landwolf@gmail.com">Contact support ↗</a>
    </footer>
    <noscript
      ><p class="empty-state">
        LandWolf requires JavaScript for sign-in, interactive maps, and deal
        analysis.
      </p></noscript
    >
  </body>
</html>
