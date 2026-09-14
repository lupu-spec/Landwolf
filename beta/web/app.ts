import L from "leaflet";

type PropertyRecord = {
  id: string;
  tract: string;
  title: string;
  county: string;
  state: string;
  acres: number;
  asking_price: number;
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
};
type Source = {
  name: string;
  url: string;
  status: string;
  last_success: number | null;
  record_count: number;
  message: string;
  stale: boolean;
  coverage_note: string;
};
type SearchResult = {
  results: PropertyRecord[];
  total: number;
  page: number;
  page_size: number;
  coverage_supported: boolean;
  source: Source;
};
type SessionInfo = { authenticated?: boolean; email: string; csrf: string };
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
let currentProperty: PropertyRecord | null = null;
let lastResult: SearchResult | null = null;
let map: L.Map | null = null;
let markers: L.LayerGroup | null = null;
let mapRecords: PropertyRecord[] = [];
let notificationTimer: ReturnType<typeof setTimeout> | undefined;

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
  requestSequence++;
  detailSequence++;
  currentProperty = null;
  lastResult = null;
  dialog.close();
  byId("detail-content").replaceChildren();
  byId("analysis-results").replaceChildren();
  byId<HTMLFormElement>("analysis-form").reset();
  byId("property-list").replaceChildren();
  byId("source-cards").replaceChildren();
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
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
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
      parsed.hostname === "cdn.glo.texas.gov" &&
      parsed.pathname.startsWith("/vlb/land/tract-images/")
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
    if (parsed.protocol === "https:" && parsed.hostname === "www.glo.texas.gov")
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
async function navigate(view: string): Promise<void> {
  document
    .querySelectorAll<HTMLButtonElement>("[data-nav]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.nav === view),
    );
  const sources = view === "sources";
  savedOnly = view === "saved";
  page = 1;
  byId("source-panel").hidden = !sources;
  byId("explore-panel").hidden = sources;
  byId("workspace-title").textContent = sources
    ? "Know the source. Know the limits."
    : savedOnly
      ? "Your opportunities, in one place."
      : "Find your next opportunity.";
  byId("workspace-description").textContent = sources
    ? "A transparent view of connected data and current gaps."
    : savedOnly
      ? "Your account's saved properties. Filters still apply."
      : "Real listings. Clear sources. A closer look at what matters.";
  if (sources) {
    try {
      const result = await api<{ sources: Source[] }>("/api/sources");
      renderSources(result.sources);
    } catch (error) {
      notify(errorText(error));
    }
  } else await search();
}
document.querySelectorAll<HTMLButtonElement>("[data-nav]").forEach((button) =>
  button.addEventListener("click", () => {
    void navigate(button.dataset.nav ?? "explore");
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
  byId<HTMLSelectElement>("state").value = "TX";
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
    "Texas GLO public-sale inventory · Asking prices are not appraisals";
  const source = result.source;
  byId("source-summary").textContent =
    source.status === "syncing"
      ? "Refreshing official inventory. Use Refresh results in a moment."
      : `${source.stale || source.status !== "ready" ? "Source needs attention" : "Official-source inventory"} · Last successful retrieval ${date(source.last_success)}`;
  byId("source-summary").parentElement?.classList.toggle(
    "stale",
    source.stale || source.status !== "ready",
  );
  const empty = result.results.length === 0;
  byId("empty-state").hidden = !empty;
  byId("results-layout").hidden = empty;
  if (empty) {
    byId("empty-title").textContent = !result.coverage_supported
      ? "This coverage is not connected yet."
      : source.record_count === 0
        ? "The official inventory is not ready yet."
        : savedOnly
          ? "No saved properties match these filters."
          : "No matching listings in this source.";
    byId("empty-description").textContent = !result.coverage_supported
      ? "The beta currently covers Texas GLO public-sale land. Other states, tax sales, foreclosures, and surplus feeds are not connected. This is a coverage gap, not proof that no opportunities exist."
      : source.record_count === 0
        ? source.message +
          " Try Refresh results shortly. We will not substitute sample listings."
        : "Try another county, a lower acreage minimum, or a higher price ceiling. These results only reflect the connected source.";
  }
  byId("property-list").replaceChildren(...result.results.map(propertyCard));
  const pages = Math.max(1, Math.ceil(total / result.page_size));
  byId("pagination").hidden = pages === 1;
  byId<HTMLButtonElement>("previous").disabled = page <= 1;
  byId<HTMLButtonElement>("next").disabled = page >= pages;
  byId("page-label").textContent = `Page ${page} of ${pages}`;
  if (!empty) drawMap(result.results);
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
function propertyCard(record: PropertyRecord): HTMLElement {
  const card = element("article", "property-card");
  const image = element("div", "property-image");
  image.append(photo(record, ""));
  image.append(
    element(
      "span",
      "category-label",
      record.active ? "GOVERNMENT LAND" : "NOT IN CURRENT INVENTORY",
    ),
  );
  const save = element("button", "save-button");
  save.setAttribute(
    "aria-label",
    `${record.saved ? "Unsave" : "Save"} tract ${record.tract}`,
  );
  save.setAttribute("aria-pressed", String(record.saved));
  save.append(bookmarkIcon());
  save.addEventListener("click", async () => {
    save.disabled = true;
    try {
      const result = await api<{ saved: boolean }>(
        `/api/saved/${encodeURIComponent(record.id)}`,
        record.saved ? "DELETE" : "PUT",
      );
      record.saved = result.saved;
      if (lastResult) renderResults(lastResult);
      notify(
        result.saved
          ? "Property saved to your account."
          : "Property removed from your saved list.",
      );
      if (savedOnly) void search();
    } catch (error) {
      notify(errorText(error));
      save.disabled = false;
    }
  });
  image.append(save);
  const body = element("div", "card-body");
  body.append(
    element("p", "card-location", `${record.county} County, ${record.state}`),
  );
  const heading = element("div", "card-heading");
  heading.append(
    element("h3", "", record.title),
    element(
      "span",
      "",
      `${record.acres.toLocaleString(undefined, { maximumFractionDigits: 4 })} acres`,
    ),
  );
  body.append(heading);
  body.append(
    element("p", "card-price", money(record.asking_price)),
    element(
      "p",
      "card-price-note",
      `Published sale price · ${money(record.asking_price / record.acres)}/acre`,
    ),
    element("div", "card-divider"),
  );
  const footer = element("div", "card-footer");
  footer.append(element("span", "card-source", "Texas GLO · Public sale"));
  const detail = element("button", "card-detail", "View property →");
  detail.setAttribute("aria-label", `View property ${record.tract}`);
  detail.addEventListener("click", () => {
    void openDetail(record.id);
  });
  footer.append(detail);
  body.append(footer);
  card.append(image, body);
  return card;
}

function drawMap(records: PropertyRecord[]): void {
  if (!map) {
    map = L.map("property-map", { scrollWheelZoom: false }).setView(
      [31.2, -99.3],
      6,
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
  else map.setView([31.2, -99.3], 6);
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
          source.status === "ready" && !source.stale
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
          `${source.record_count} records at last successful sync · ${date(source.last_success)}`,
        ),
        element("p", "", source.message),
        sourceLink(source.url, "Inspect the original inventory ↗"),
      );
      return card;
    }),
  );
}

async function openDetail(id: string): Promise<void> {
  const sequence = ++detailSequence;
  try {
    const record = await api<PropertyRecord>(
      `/api/properties/${encodeURIComponent(id)}`,
    );
    if (!csrf || sequence !== detailSequence) return;
    currentProperty = record;
    renderDetail(record);
    byId<HTMLFormElement>("analysis-form").reset();
    const input =
      byId<HTMLFormElement>("analysis-form").elements.namedItem(
        "purchase_price",
      );
    if (input instanceof HTMLInputElement)
      input.value = String(record.asking_price);
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
  const hero = element("div", "detail-hero");
  hero.append(photo(record, "detail-photo"));
  const overview = element("div", "detail-overview");
  overview.append(
    element(
      "p",
      "eyebrow",
      record.active
        ? "GOVERNMENT LAND · PUBLIC SALE"
        : "NO LONGER IN CURRENT INVENTORY",
    ),
  );
  const heading = element("h2", "", record.title);
  heading.id = "detail-title";
  overview.append(
    heading,
    element("p", "detail-location", `${record.county} County, Texas`),
    element("p", "detail-price", money(record.asking_price)),
    element(
      "p",
      "input-note",
      "Published sale price · Not a market-value estimate",
    ),
  );
  overview.append(
    sourceLink(record.source_url, "View official listing & sale terms ↗"),
  );
  const facts = element("div", "detail-facts");
  for (const [label, value] of [
    ["LAND AREA", `${record.acres} acres`],
    ["PRICE / ACRE", money(record.asking_price / record.acres)],
    ["SOURCE FIELDS", `${record.data_completeness}%`],
  ]) {
    const fact = element("div");
    fact.append(element("span", "", label), element("strong", "", value));
    facts.append(fact);
  }
  overview.append(facts);
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
  detailSequence++;
  dialog.close();
});
dialog.addEventListener("cancel", () => {
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
    result.maximum_bid !== null &&
    result.maximum_bid < currentProperty.asking_price
  )
    container.append(
      element(
        "p",
        "model-meta",
        "Your model maximum is below the published sale price. The seller may not accept an offer at that level.",
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

// Changes to assumptions immediately invalidate the displayed prior analysis.
byId("analysis-form").addEventListener("input", () => {
  analysisSequence++;
  byId("analysis-results").hidden = true;
});
const states =
  "AL:Alabama|AK:Alaska|AZ:Arizona|AR:Arkansas|CA:California|CO:Colorado|CT:Connecticut|DE:Delaware|FL:Florida|GA:Georgia|HI:Hawaii|ID:Idaho|IL:Illinois|IN:Indiana|IA:Iowa|KS:Kansas|KY:Kentucky|LA:Louisiana|ME:Maine|MD:Maryland|MA:Massachusetts|MI:Michigan|MN:Minnesota|MS:Mississippi|MO:Missouri|MT:Montana|NE:Nebraska|NV:Nevada|NH:New Hampshire|NJ:New Jersey|NM:New Mexico|NY:New York|NC:North Carolina|ND:North Dakota|OH:Ohio|OK:Oklahoma|OR:Oregon|PA:Pennsylvania|RI:Rhode Island|SC:South Carolina|SD:South Dakota|TN:Tennessee|TX:Texas|UT:Utah|VT:Vermont|VA:Virginia|WA:Washington|WV:West Virginia|WI:Wisconsin|WY:Wyoming";
for (const state of states.split("|")) {
  const [code, name] = state.split(":");
  const option = element(
    "option",
    "",
    `${name}${code === "TX" ? "" : " · not connected"}`,
  );
  option.value = code ?? "";
  option.defaultSelected = code === "TX";
  byId<HTMLSelectElement>("state").append(option);
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
