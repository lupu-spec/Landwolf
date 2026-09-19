import L from "leaflet";
import { bidRange, similarFilters } from "./property-context";

type SavedLocation = {
  address: string | null;
  latitude: number | null;
  longitude: number | null;
};
type SavedEntry = {
  id: string;
  listing_id: string | null;
  title: string;
  location: SavedLocation | null;
  location_origin: "source" | "user";
  revision: number;
  property?: PropertyRecord | null;
};
type SavedResult = {
  results: SavedEntry[];
  total: number;
  page: number;
  page_size: number;
};

type PropertyRecord = {
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
  saved: boolean;
  saved_record: SavedEntry | null;
  research_location: SavedLocation | null;
  location_origin: "source" | "user";
};
type Source = {
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
  total: number;
  page: number;
  page_size: number;
  coverage_supported: boolean;
  sources: Source[];
  coverage_note: string;
};
type SessionInfo = { authenticated?: boolean; email: string; csrf: string };
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
  maximum_bid: number | null;
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
let registerMode = false;
let page = 1;
let savedOnly = false;
let requestSequence = 0;
let detailSequence = 0;
let analysisSequence = 0;
let researchSequence = 0;
let navigationSequence = 0;
let researchListingId: string | null = null;
let currentProperty: PropertyRecord | null = null;
let pendingResearchProperty: PropertyRecord | null = null;
let lastResult: SearchResult | null = null;
let map: L.Map | null = null;
let markers: L.LayerGroup | null = null;
let mapRecords: PropertyRecord[] = [];
let notificationTimer: ReturnType<typeof setTimeout> | undefined;
let coverageSources: Source[] = [];
let coverageStates: StateCoverage[] = [];
const saving = new Set<string>();
const resaleNames = ["resale_low", "resale_likely", "resale_high"];
let resaleOverrides = new Set<string>();
const scenarioDrafts = new Map<
  string,
  { values: Record<string, string>; overrides: string[] }
>();
let filterView = "explore";
const filterDrafts = new Map<string, Record<string, string>>();
let researchProperty: PropertyRecord | null = null;
let researchSaved: SavedEntry | null = null;
let researchManualId = "";
let researchSaving = false;
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
  saving.clear();
  scenarioDrafts.clear();
  resaleOverrides.clear();
  filterDrafts.clear();
  filterView = "explore";
  form.reset();
  byId<HTMLSelectElement>("state").value = "US";
  requestSequence++;
  detailSequence++;
  navigationSequence++;
  resetResearch();
  currentProperty = null;
  pendingResearchProperty = null;
  lastResult = null;
  dialog.close();
  byId("detail-content").replaceChildren();
  byId("detail-actions").replaceChildren();
  byId("analysis-results").replaceChildren();
  byId<HTMLFormElement>("analysis-form").reset();
  byId("property-list").replaceChildren();
  byId("source-cards").replaceChildren();
  byId("state-coverage").replaceChildren();
  byId("research-catalog").replaceChildren();
  coverageSources = [];
  coverageStates = [];
  byId("account-email").textContent = "";
  markers?.clearLayers();
  mapRecords = [];
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
      const detail =
        result && typeof result === "object" && "detail" in result
          ? String(result.detail)
          : "Request failed";
      throw new Error(detail);
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
function photo(record: PropertyRecord, css: string): HTMLElement {
  const src = safeImage(record.image_url);
  if (!src)
    return element("div", css + " image-missing", "Source image unavailable");
  const img = element("img", css);
  img.src = src;
  img.alt = `Official source image for tract ${record.tract}`;
  img.loading = "lazy";
  img.addEventListener(
    "error",
    () =>
      img.replaceWith(
        element("div", css + " image-missing", "Source image unavailable"),
      ),
    { once: true },
  );
  return img;
}

function setAuthMode(register: boolean): void {
  registerMode = register;
  byId("login-tab").setAttribute("aria-pressed", String(!register));
  byId("register-tab").setAttribute("aria-pressed", String(register));
  byId("auth-submit").textContent = register
    ? "Create your free account →"
    : "Sign in to LandWolf →";
  byId<HTMLInputElement>("password").autocomplete = register
    ? "new-password"
    : "current-password";
  byId("auth-message").textContent = "";
}
byId("login-tab").addEventListener("click", () => setAuthMode(false));
byId("register-tab").addEventListener("click", () => setAuthMode(true));
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
      },
    );
    byId<HTMLInputElement>("password").value = "";
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
  csrf = info.csrf;
  byId("account-email").textContent = info.email;
  byId("auth-view").hidden = true;
  byId("workspace").hidden = false;
  byId("main-nav").hidden = false;
  byId("signout").hidden = false;
  savedOnly = false;
  page = 1;
  await navigate("explore");
}
async function navigate(
  view: string,
  preset?: Record<string, string>,
): Promise<void> {
  if (view === "explore" || view === "saved") {
    if (view !== filterView) {
      filterDrafts.set(filterView, formValues(form));
      form.reset();
      byId<HTMLSelectElement>("state").value = "US";
      fillForm(form, filterDrafts.get(view) ?? {});
      filterView = view;
    }
    if (preset) fillForm(form, preset);
  }
  const navigation = ++navigationSequence;
  const sessionToken = csrf;
  requestSequence++;
  document
    .querySelectorAll<HTMLButtonElement>("[data-nav]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.nav === view),
    );
  const sources = view === "sources";
  const researching = view === "research";
  savedOnly = view === "saved";
  if (view === "explore")
    byId("results-layout").dataset.view =
      document.querySelector<HTMLButtonElement>(
        '[data-view][aria-pressed="true"]',
      )?.dataset.view ?? "split";
  page = 1;
  byId("source-panel").hidden = !sources;
  byId("research-panel").hidden = !researching;
  byId("explore-panel").hidden = sources || researching;
  form.hidden = savedOnly;
  byId("saved-toolbar").hidden = !savedOnly;
  document
    .querySelectorAll<HTMLElement>(
      ".source-filter-row, .coverage-strip, .results-controls",
    )
    .forEach((node) => {
      node.hidden = savedOnly;
    });
  byId("workspace-title").textContent = sources
    ? "Know the source. Know the limits."
    : researching
      ? "Understand the location."
      : savedOnly
        ? "Your opportunities, in one place."
        : "Find your next opportunity.";
  byId("workspace-description").textContent = sources
    ? "A transparent view of connected data and current gaps."
    : researching
      ? "Public records, with their source and uncertainty in view."
      : savedOnly
        ? "Saved to your account. Open Research to continue with the saved address or coordinates."
        : "Real listings. Clear sources. A closer look at what matters.";
  if (sources) {
    try {
      const result = await api<{
        sources: Source[];
        states: StateCoverage[];
        research_sources: ResearchCatalog[];
      }>("/api/sources");
      if (!csrf || csrf !== sessionToken || navigation !== navigationSequence)
        return;
      coverageSources = result.sources;
      coverageStates = result.states;
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
    } catch (error) {
      notify(errorText(error));
    }
  } else if (!researching) await search();
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
    saved_only: savedOnly,
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
  if (!lastResult) {
    byId("property-list").replaceChildren(
      ...Array.from({ length: 4 }, () => element("div", "loading-card")),
    );
  }
  try {
    if (savedOnly) {
      const result = await api<SavedResult>(
        `/api/saved?page=${page}&page_size=12`,
      );
      if (sequence !== requestSequence || !csrf) return;
      if (result.results.length === 0 && page > 1) {
        page--;
        void search();
        return;
      }
      renderSaved(result);
      return;
    }
    const result = await api<SearchResult>("/api/search", "POST", query());
    if (sequence !== requestSequence || !csrf) return;
    lastResult = result;
    renderResults(result);
  } catch (error) {
    if (sequence === requestSequence) {
      byId("workspace-error").textContent = errorText(error);
      if (!lastResult) byId("property-list").replaceChildren();
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
    `${total} ${savedOnly ? "saved " : ""}${total === 1 ? "property" : "properties"}`;
  byId("results-subtitle").textContent =
    "Connected sale inventories · Published prices and bids are not appraisals";
  const feeds = result.sources.filter((source) => source.automated);
  const ready = feeds.filter(
    (source) => source.status === "ready" && !source.stale,
  );
  const attention = feeds.some(
    (source) => source.status !== "ready" || source.stale,
  );
  byId("source-summary").textContent =
    `${ready.length} of ${feeds.length} matching feeds refreshed${attention ? " · Some feeds need attention" : ""} · Partial coverage; inspect Data coverage`;
  byId("source-summary").parentElement?.classList.toggle("stale", attention);
  const empty = result.results.length === 0;
  byId("empty-state").hidden = !empty;
  byId("results-layout").hidden = empty;
  if (empty) {
    byId("empty-title").textContent = !result.coverage_supported
      ? "This coverage is not connected yet."
      : savedOnly
        ? "No saved properties match these filters."
        : "No matching listings in connected sources.";
    byId("empty-description").textContent = !result.coverage_supported
      ? "An automated feed for this selection is not connected. Open Data coverage for official source links and current gaps. A pre-foreclosure notice is not a confirmed sale."
      : result.coverage_note +
        " Try a different state or filter, or inspect Data coverage.";
  }
  byId("property-list").replaceChildren(...result.results.map(propertyCard));
  const pages = Math.max(1, Math.ceil(total / result.page_size));
  byId("pagination").hidden = pages === 1;
  byId<HTMLButtonElement>("previous").disabled = page <= 1;
  byId<HTMLButtonElement>("next").disabled = page >= pages;
  byId("page-label").textContent = `Page ${page} of ${pages}`;
  if (!empty) drawMap(result.results);
}

function renderSaved(result: SavedResult): void {
  const linked = result.results.flatMap((entry) =>
    entry.property ? [entry.property] : [],
  );
  // Reuse the same result shell, while keeping manual records out of the source map.
  renderResults({
    ...result,
    results: linked,
    sources: [],
    coverage_supported: true,
    coverage_note: "",
  });
  byId("results-title").textContent =
    `${result.total} saved ${result.total === 1 ? "property" : "properties"}`;
  byId("results-subtitle").textContent =
    "Most recently saved or updated first · Includes properties you added";
  byId("empty-state").hidden = result.total > 0;
  byId("results-layout").hidden = result.total === 0;
  byId("results-layout").dataset.view = "list";
  byId("empty-title").textContent = "No saved properties yet.";
  byId("empty-description").textContent =
    "Use Save property on a listing, or Add a property to save an address or coordinates.";
  byId("property-list").replaceChildren(
    ...result.results.map((entry) =>
      entry.property ? propertyCard(entry.property) : manualCard(entry),
    ),
  );
}

function locationLabel(value: SavedLocation | null): string {
  if (!value)
    return "Location needed — add an address or coordinates in Research.";
  return value.address ?? `${value.latitude}, ${value.longitude}`;
}

function manualCard(entry: SavedEntry): HTMLElement {
  const card = element("article", "property-card manual-property");
  const body = element("div", "card-body");
  body.append(
    element("p", "eyebrow", "PROPERTY YOU ADDED"),
    element("h3", "", entry.title),
    element("p", "saved-location", locationLabel(entry.location)),
    element(
      "p",
      "input-note",
      "User-entered research location. Sale status and parcel boundaries are not verified.",
    ),
  );
  const actions = element("div", "property-actions");
  const research = element("button", "button primary", "Research property");
  research.type = "button";
  research.addEventListener("click", () => {
    void openSaved(entry.id);
  });
  const remove = element("button", "button secondary", "Remove from Saved");
  remove.type = "button";
  remove.addEventListener("click", async () => {
    const token = csrf;
    remove.disabled = true;
    try {
      await api(`/api/saved/${encodeURIComponent(entry.id)}`, "DELETE");
      if (token !== csrf) return;
      if (researchSaved?.id === entry.id) resetResearch();
      notify("Removed from Saved properties.");
      if (savedOnly) await search();
    } catch (error) {
      if (token === csrf) notify(errorText(error));
    } finally {
      remove.disabled = false;
    }
  });
  actions.append(research, remove);
  body.append(actions);
  card.append(body);
  return card;
}

function bookmarkIcon(): SVGSVGElement {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M6 3h12v18l-6-4-6 4z");
  svg.append(path);
  return svg;
}
function saveControl(
  record: PropertyRecord,
  compact = false,
): HTMLButtonElement {
  const button = element(
    "button",
    compact ? "button secondary save-button" : "button primary property-save",
  );
  button.type = "button";
  button.dataset.saveId = record.id;
  button.dataset.tract = record.tract;
  button.dataset.compact = String(compact);
  paintSave(button, record.saved, saving.has(record.id));
  button.addEventListener("click", () => {
    void toggleSave(record);
  });
  return button;
}
function paintSave(
  button: HTMLButtonElement,
  saved: boolean,
  busy: boolean,
): void {
  button.disabled = busy;
  button.setAttribute("aria-pressed", String(saved));
  button.setAttribute(
    "aria-label",
    `${saved ? "Remove saved property" : "Save property"} ${button.dataset.tract ?? ""}`,
  );
  button.title = saved
    ? "Remove from Saved properties"
    : "Save to your account";
  button.replaceChildren(
    bookmarkIcon(),
    document.createTextNode(
      busy ? "Updating…" : saved ? "Saved ✓" : "Save property",
    ),
  );
}
function syncSaveControls(record: PropertyRecord): void {
  document
    .querySelectorAll<HTMLButtonElement>("[data-save-id]")
    .forEach((button) => {
      if (button.dataset.saveId === record.id)
        paintSave(button, record.saved, saving.has(record.id));
    });
}
async function toggleSave(record: PropertyRecord): Promise<void> {
  if (!csrf || saving.has(record.id)) return;
  const sessionToken = csrf;
  saving.add(record.id);
  syncSaveControls(record);
  const report = (message: string) => {
    if (dialog.open && currentProperty?.id === record.id)
      byId("detail-save-status").textContent = message;
    else notify(message);
  };
  try {
    const result = await api<{ saved: boolean }>(
      `/api/saved/${encodeURIComponent(record.id)}`,
      record.saved ? "DELETE" : "PUT",
    );
    if (csrf !== sessionToken) return;
    record.saved = result.saved;
    for (const item of lastResult?.results ?? [])
      if (item.id === record.id) item.saved = result.saved;
    if (currentProperty?.id === record.id) currentProperty.saved = result.saved;
    if (researchProperty?.id === record.id)
      researchProperty.saved = result.saved;
    if (!result.saved) {
      record.saved_record = null;
      if (currentProperty?.id === record.id)
        currentProperty.saved_record = null;
      if (researchSaved?.id === record.id) researchSaved = null;
    }
    report(
      result.saved
        ? "Saved to your account. Find it in Saved properties."
        : "Removed from Saved properties.",
    );
    if (savedOnly) void search();
  } catch (error) {
    if (csrf === sessionToken)
      report(`Save change failed: ${errorText(error)} Try again.`);
  } finally {
    if (csrf === sessionToken) {
      saving.delete(record.id);
      syncSaveControls(record);
    }
  }
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
  actions.prepend(saveControl(record, true));
  body.append(
    footer,
    element("p", "saved-location", locationLabel(record.research_location)),
    actions,
  );
  card.append(image, body);
  return card;
}

function drawMap(records: PropertyRecord[]): void {
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
  }
  mapRecords = records;
  const points: L.LatLngTuple[] = [];
  for (const record of records) {
    if (record.latitude === null || record.longitude === null) continue;
    points.push([record.latitude, record.longitude]);
  }
  byId("map-count").textContent =
    `${points.length} of ${records.length} locations · this page`;
  if (points.length)
    map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 12 });
  else map.setView([39, -98], 4);
  renderMapMarkers();
  setTimeout(() => map?.invalidateSize(), 50);
}

function renderMapMarkers(): void {
  if (!map || !markers) return;
  markers.clearLayers();
  // Screen-space groups keep overlapping labels and identical coordinates reachable.
  // The cluster anchor is a real source point; individual coordinates never change.
  const groups: {
    position: L.LatLngTuple;
    pixel: L.Point;
    records: PropertyRecord[];
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
    setTimeout(() => map?.invalidateSize(), 50);
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
  researchSaved = null;
  researchManualId = "";
  researchSaving = false;
  byId<HTMLInputElement>("research-name").value = "";
  byId("research-save-status").textContent = "";
  byId<HTMLButtonElement>("research-save").disabled = false;
  byId("research-save").textContent = "Save property";
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
  actions.append(research, similar);
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
    await showResearchProperty(fresh, fresh.saved_record);
  } catch (error) {
    if (token === csrf) notify(errorText(error));
  }
}

async function openSaved(id: string): Promise<void> {
  const sequence = ++researchContextSequence;
  const token = csrf;
  try {
    const entry = await api<SavedEntry>(`/api/saved/${encodeURIComponent(id)}`);
    if (sequence !== researchContextSequence || token !== csrf) return;
    await showResearchProperty(entry.property ?? null, entry);
  } catch (error) {
    if (token === csrf) notify(errorText(error));
  }
}

async function showResearchProperty(
  record: PropertyRecord | null,
  entry: SavedEntry | null,
): Promise<void> {
  rememberScenario();
  dialog.close();
  detailSequence++;
  resetResearch();
  researchProperty = record;
  pendingResearchProperty = null;
  researchSaved = entry;
  const contextSequence = researchContextSequence;
  const point = entry?.location ?? record?.research_location ?? null;
  const origin = entry?.location_origin ?? record?.location_origin;
  const hasPoint = point?.latitude != null && point.longitude !== null;
  const address = point?.address;
  byId<HTMLInputElement>("research-name").value =
    entry?.title ?? record?.title ?? "";
  byId("research-save").textContent = entry ? "Save changes" : "Save property";
  if (hasPoint) {
    byId<HTMLSelectElement>("research-mode").value = "coordinates";
    byId<HTMLInputElement>("research-latitude").value = String(point.latitude);
    byId<HTMLInputElement>("research-longitude").value = String(
      point.longitude,
    );
    if (origin === "source" && record) researchListingId = record.id;
  } else if (address)
    byId<HTMLInputElement>("research-address").value = address;
  researchMode();
  const context = byId("research-property-context");
  context.append(
    element("h3", "", entry?.title ?? record?.title ?? "Your property"),
    element(
      "p",
      "",
      record
        ? `${location(record)} · ${area(record.acres)}`
        : "Property you added",
    ),
    element(
      "p",
      "input-note",
      `${origin === "user" ? "Your saved location" : "Source-reported location"}. Review the fields before researching. Save changes to keep edits in your account. Coordinates and address results are not surveyed parcel boundaries.`,
    ),
  );
  const analyze = element("button", "button quiet", "Open deal scenario");
  analyze.addEventListener("click", () => {
    if (researchProperty) void openDetail(researchProperty.id);
  });
  if (record) context.append(analyze, propertyActions(record));
  await navigate("research");
  if (contextSequence !== researchContextSequence || !csrf) return;
  if (hasPoint && origin === "source") await runResearch();
  else
    byId("research-status").textContent = address
      ? "Address prefilled. Review it, then select Research location."
      : hasPoint
        ? "Saved coordinates prefilled. Review them, then select Research location."
        : "This listing has no usable published address or point. Enter an address or coordinates, then Save changes to keep this research location. County and tract identifiers cannot locate a parcel.";
}

function researchLocationInput(): SavedLocation {
  if (byId<HTMLSelectElement>("research-mode").value === "address")
    return {
      address: byId<HTMLInputElement>("research-address").value.trim(),
      latitude: null,
      longitude: null,
    };
  return {
    address: null,
    latitude: Number(byId<HTMLInputElement>("research-latitude").value),
    longitude: Number(byId<HTMLInputElement>("research-longitude").value),
  };
}

async function saveResearchProperty(): Promise<void> {
  if (
    !csrf ||
    researchSaving ||
    !byId<HTMLFormElement>("research-form").reportValidity()
  )
    return;
  const selectedLocation = researchLocationInput();
  const title =
    byId<HTMLInputElement>("research-name").value.trim() ||
    researchProperty?.title ||
    locationLabel(selectedLocation);
  if (!byId<HTMLInputElement>("research-name").reportValidity()) return;
  const token = csrf;
  const sequence = researchContextSequence;
  const originalEntry = researchSaved;
  if (!researchManualId) researchManualId = crypto.randomUUID();
  researchSaving = true;
  const button = byId<HTMLButtonElement>("research-save");
  button.disabled = true;
  byId("research-save-status").textContent =
    "Saving property and research location…";
  try {
    const body = originalEntry
      ? { title, location: selectedLocation, revision: originalEntry.revision }
      : {
          title,
          location: selectedLocation,
          ...(researchProperty
            ? { listing_id: researchProperty.id }
            : { manual_id: researchManualId }),
        };
    const result = await api<SavedEntry>(
      originalEntry
        ? `/api/saved/${encodeURIComponent(originalEntry.id)}`
        : "/api/saved",
      originalEntry ? "PATCH" : "POST",
      body,
    );
    if (token !== csrf || sequence !== researchContextSequence) return;
    researchSaved = result;
    if (researchProperty) {
      researchProperty.saved = true;
      researchProperty.saved_record = result;
      researchProperty.research_location = result.location;
      researchProperty.location_origin = result.location_origin;
      syncSaveControls(researchProperty);
    }
    button.textContent = "Save changes";
    const edited =
      JSON.stringify(researchLocationInput()) !==
        JSON.stringify(selectedLocation) ||
      (byId<HTMLInputElement>("research-name").value.trim() ||
        researchProperty?.title ||
        locationLabel(researchLocationInput())) !== title;
    byId("research-save-status").textContent = edited
      ? "The submitted property was saved. Your newer edits are not saved yet."
      : "Saved to your account with this research location. Open it from Saved properties on any device.";
  } catch (error) {
    if (token === csrf && sequence === researchContextSequence)
      byId("research-save-status").textContent =
        `Save failed: ${errorText(error)}`;
  } finally {
    if (token === csrf && sequence === researchContextSequence) {
      researchSaving = false;
      button.disabled = false;
    }
  }
}

byId("research-save").addEventListener("click", () => {
  void saveResearchProperty();
});
byId("research-name").addEventListener("input", () => {
  byId("research-save-status").textContent = "Unsaved name changes.";
});
byId("research-view-saved").addEventListener("click", () => {
  void navigate("saved");
});
function newResearchProperty(): void {
  rememberScenario();
  dialog.close();
  currentProperty = null;
  pendingResearchProperty = null;
  resetResearch();
  void navigate("research");
  byId<HTMLInputElement>("research-address").focus();
}
byId("research-new").addEventListener("click", newResearchProperty);
byId("saved-add").addEventListener("click", newResearchProperty);
function renderResearch(report: ResearchReport): void {
  const container = byId("research-results");
  container.replaceChildren();
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
      card.append(group);
    }
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
  byId("research-save-status").textContent =
    "Unsaved location changes. Select Save changes to keep them.";
  const note = byId("research-property-context").querySelector(".input-note");
  if (researchProperty && note)
    note.textContent =
      "Location edited: research may describe a different property. Open deal scenario still refers to the original listing; research results will not overwrite its scenario inputs.";
});
byId("research-form").addEventListener("submit", (event) => {
  event.preventDefault();
  void runResearch();
});

async function openDetail(id: string): Promise<void> {
  const sequence = ++detailSequence;
  try {
    const record = await api<PropertyRecord>(
      `/api/properties/${encodeURIComponent(id)}`,
    );
    if (!csrf || sequence !== detailSequence) return;
    currentProperty = record;
    pendingResearchProperty = record;
    renderDetail(record);
    const analysisForm = byId<HTMLFormElement>("analysis-form");
    analysisForm.reset();
    resaleOverrides = new Set<string>();
    const draft = scenarioDrafts.get(record.id);
    if (draft) {
      fillForm(analysisForm, draft.values);
      resaleOverrides = new Set(draft.overrides);
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
  byId("detail-actions").replaceChildren(
    saveControl(record),
    propertyActions(record),
  );
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
  const saveStatus = element("p", "input-note");
  saveStatus.id = "detail-save-status";
  saveStatus.setAttribute("role", "status");
  overview.append(
    saveStatus,
    element(
      "p",
      "input-note",
      "Save property keeps this listing in your account. Research property opens its saved address or coordinates. Save changes in Research to retain location edits. Scenario edits remain in this page session only.",
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
    const data = new FormData(byId<HTMLFormElement>("analysis-form"));
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
      "MODEL MAXIMUM BID",
      result.maximum_bid === null
        ? "No feasible bid"
        : money(result.maximum_bid),
      "Within your entered risk & return targets",
      "primary-metric",
    ],
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
  if (
    currentProperty &&
    currentProperty.asking_price !== null &&
    result.maximum_bid !== null &&
    result.maximum_bid < currentProperty.asking_price
  )
    container.append(
      element(
        "p",
        "model-meta",
        "Your model maximum is below the published price or bid. Confirm the seller's terms before making an offer.",
      ),
    );
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
  });
  // Bounded session memory, cleared on sign-out. Never use shared local storage.
  if (scenarioDrafts.size > 50) {
    const oldest = scenarioDrafts.keys().next().value;
    if (oldest) scenarioDrafts.delete(oldest);
  }
}
function applyBidRange(): void {
  const range = bidRange(
    analysisInput("purchase_price").valueAsNumber,
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
    ? "Custom resale assumptions. Your edited fields will not change when the bid or percentages change; untouched fields still follow the bid. Reapply the range to replace your resale overrides."
    : "Hypothetical bid-based resale range: low = bid × (1 − downside %); likely = bid; high = bid × (1 + upside %). These are scenario bounds, not statistical confidence limits or an appraisal. A positive bid and valid percentages are required.";
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
  if (
    ["purchase_price", "downside_pct", "upside_pct"].includes(event.target.name)
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
}
byId("year").textContent = String(new Date().getFullYear());
void (async () => {
  try {
    const info = await api<SessionInfo>("/api/session");
    if (info.authenticated) await enterWorkspace(info);
  } catch {
    byId("auth-message").textContent =
      "Unable to reach LandWolf. Check your connection and try again.";
  }
})();
