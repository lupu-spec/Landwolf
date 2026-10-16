/** Owner source disclosures. All provider text is rendered through textContent. */
import { element as node } from "./dom";
import { sourceHealth, sourceTimestamp } from "./source-health";

export type Source = {
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

function healthIndicator(source: Source, now: number): HTMLElement {
  const result = node("span", "source-health");
  result.dataset.automated = String(source.automated);
  result.dataset.lastSuccess =
    source.last_success === null ? "" : String(source.last_success);
  updateIndicator(result, now);
  return result;
}
function updateIndicator(indicator: HTMLElement, now: number): void {
  const health = sourceHealth(
    indicator.dataset.automated === "true",
    indicator.dataset.lastSuccess === ""
      ? null
      : Number(indicator.dataset.lastSuccess),
    now,
  );
  indicator.dataset.health = health.color;
  indicator.title = health.label;
  indicator.setAttribute("aria-label", health.label);
  indicator.setAttribute("role", "img");
}
export function refreshSourceHealth(
  container: HTMLElement,
  now = Date.now() / 1000,
): void {
  container
    .querySelectorAll<HTMLElement>(".source-health")
    .forEach((indicator) => updateIndicator(indicator, now));
}

export function renderSourceList(
  container: HTMLElement,
  sources: Source[],
  link: (url: string, label: string) => HTMLAnchorElement,
  now = Date.now() / 1000,
): void {
  const header = node("div", "source-list-heading");
  header.setAttribute("aria-hidden", "true");
  for (const label of ["Source name", "Health", "Last updated"])
    header.append(node("span", "", label));
  container.replaceChildren(header);
  if (!sources.length) {
    container.append(
      node("p", "source-list-empty", "No sources match these filters."),
    );
    return;
  }
  for (const source of sources) {
    const row = node("details", "source-card source-row");
    const summary = node("summary", "source-row-summary");
    summary.append(
      node("span", "source-row-name", source.name),
      healthIndicator(source, now),
    );
    const timestamp = node(
      "span",
      "source-updated",
      source.automated ? sourceTimestamp(source.last_success) : "Not imported",
    );
    timestamp.setAttribute(
      "aria-label",
      `Last updated: ${timestamp.textContent}`,
    );
    summary.append(timestamp);
    const detail = node("div", "source-row-detail");
    detail.append(
      node("p", "", source.coverage_note),
      node(
        "p",
        "",
        source.automated
          ? `${source.record_count} source records at last successful sync · ${sourceTimestamp(source.last_success)}`
          : "Directory entry; excluded from property counts",
      ),
      node("p", "", `Retrieval status: ${source.status}. ${source.message}`),
      link(source.url, "Inspect the original inventory ↗"),
    );
    if (source.automated) {
      detail.append(
        node(
          "p",
          "input-note",
          `Last attempted: ${sourceTimestamp(source.last_attempt ?? null)} · Scheduled every 6 hours. Retrieval does not establish publisher freshness.`,
        ),
      );
      const history = node("details", "source-history");
      history.append(
        node("summary", "", "Recent refreshes and reuse limits"),
        node(
          "p",
          "",
          source.reuse_note ?? "Review source terms before redistribution.",
        ),
      );
      for (const run of source.history ?? [])
        history.append(
          node(
            "p",
            "",
            `${sourceTimestamp(run.finished_at)} · ${run.status} · ${run.record_count} candidate records. ${run.message}`,
          ),
        );
      if (!source.history?.length)
        history.append(
          node("p", "", "No refresh history recorded for this source yet."),
        );
      detail.append(history);
    }
    row.append(summary, detail);
    container.append(row);
  }
}
