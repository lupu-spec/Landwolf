/** Owner coverage view; data lifetime, filtering and disclosure rendering stay local. */
import { byId, element } from "./dom";
import {
  renderSourceList,
  refreshSourceHealth,
  type Source,
} from "./source-list";
type StateCoverage = {
  state: string;
  name: string;
  record_count: number;
  directory_url: string;
  feed_ids: string[];
};
type ResearchCatalog = {
  id: string;
  name: string;
  url: string;
  coverage: string;
};

export type CoverageReport = {
  sources: Source[];
  states: StateCoverage[];
  research_sources: ResearchCatalog[];
  counties: {
    state: string;
    county: string;
    source: string;
    record_count: number;
  }[];
};
export function setupCoverage(
  sourceLink: (url: string, label: string) => HTMLAnchorElement,
  selectState: (state: string) => void,
  isActive: () => boolean,
) {
  let coverageSources: Source[] = [];
  let coverageStates: StateCoverage[] = [];
  let coverageCounties: CoverageReport["counties"] = [];
  function renderCoverage(): void {
    const state = byId<HTMLSelectElement>("coverage-state").value;
    const category = byId<HTMLSelectElement>("coverage-category").value;
    renderSourceList(
      byId("source-cards"),
      coverageSources.filter(
        (source) =>
          (state === "US" || source.states.includes(state)) &&
          (category === "all" || source.categories.includes(category)),
      ),
      sourceLink,
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
        selectState(item.state);
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

  // One page-lifetime timer; never refetch, reopen rows, or retain data after sign-out.
  function refreshHealth(): void {
    if (isActive() && !document.hidden)
      refreshSourceHealth(byId("source-cards"));
  }
  window.setInterval(refreshHealth, 60_000);
  document.addEventListener("visibilitychange", refreshHealth);
  return {
    clear(): void {
      coverageSources = [];
      coverageStates = [];
      coverageCounties = [];
      for (const id of [
        "source-cards",
        "state-coverage",
        "county-coverage",
        "research-catalog",
      ])
        byId(id).replaceChildren();
    },
    render(report: CoverageReport): void {
      coverageSources = report.sources;
      coverageStates = report.states;
      coverageCounties = report.counties;
      renderCoverage();
      byId("research-catalog").replaceChildren(
        ...report.research_sources.map((source) => {
          const card = element("article", "source-card");
          card.append(
            element("h4", "", source.name),
            element("p", "", source.coverage),
            sourceLink(source.url, "View public source ↗"),
          );
          return card;
        }),
      );
    },
  };
}
