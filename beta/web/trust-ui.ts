/** Render evidence as text. No generated valuation, risk score or HTML from sources. */
export type Evidence = {
  label: string;
  value: string | number | null;
  basis: "reported" | "calculated" | "estimated" | "unknown";
  retrieved_at: string | null;
  effective_date: string | null;
};
export type PropertyTrust = {
  identity: { id: string | null; status: string; message: string };
  freshness: string;
  evidence: Evidence[];
  next_steps: string[];
};
export type ResearchEvidence = {
  location: { basis: string } | null;
  sources: { id: string; name: string; status: string; summary: string }[];
};

function node<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  text: string,
  css = "",
): HTMLElementTagNameMap[K] {
  const result = document.createElement(tag);
  result.textContent = text;
  result.className = css;
  return result;
}

export function propertyTrustCard(trust: PropertyTrust): HTMLElement {
  const card = node("section", "", "trust-panel");
  card.append(node("h3", "Evidence and next steps"));
  card.append(node("p", trust.identity.message));
  card.append(
    node(
      "p",
      trust.freshness === "current_retrieval"
        ? "Source retrieval is current. Confirm availability before acting."
        : "Source freshness needs attention. Check the original listing.",
      "source-state warn",
    ),
  );
  const details = node("details", "", "evidence-details");
  details.append(node("summary", "Inspect field evidence"));
  const list = node("dl", "", "evidence-list");
  for (const fact of trust.evidence) {
    const value = node("dd", "");
    value.append(
      node("strong", fact.value === null ? "Unknown" : String(fact.value)),
    );
    value.append(
      node(
        "span",
        ` ${fact.basis} · Checked ${fact.retrieved_at ? new Date(fact.retrieved_at).toLocaleString() : "unknown"}`,
      ),
    );
    value.append(
      node("span", `Publisher date: ${fact.effective_date ?? "not supplied"}`),
    );
    list.append(node("dt", fact.label), value);
  }
  details.append(
    list,
    node(
      "p",
      "A retrieval date is not a publisher update date. Open the official listing to verify these fields.",
    ),
  );
  const steps = node("ol", "");
  for (const step of trust.next_steps) steps.append(node("li", step));
  card.append(details, steps);
  return card;
}

export function researchSummary(report: ResearchEvidence): HTMLElement {
  const card = node("section", "", "trust-panel research-summary");
  card.setAttribute("aria-label", "Research summary");
  card.append(node("h3", "Research summary"));
  const available = report.sources.filter(
    (source) => source.status === "ready",
  );
  const missing = report.sources.filter(
    (source) => source.status !== "ready" && source.status !== "not_applicable",
  );
  card.append(
    node(
      "p",
      `${available.length} sources returned evidence. ${missing.length} sources have missing or unavailable evidence.`,
    ),
  );
  const grid = node("div", "", "summary-grid");
  const location = node("div", "");
  location.append(
    node("h4", "Confirm the location"),
    node(
      "p",
      report.location?.basis === "Census address approximation"
        ? "The address is an approximate Census point. Confirm the parcel before relying on nearby records."
        : "These checks describe a point. Parcel boundaries, legal access and whole-property conditions still need verification.",
    ),
  );
  const risk = node("div", "");
  const flood = report.sources.find((source) => source.id === "fema");
  risk.append(
    node("h4", "Flood evidence"),
    node(
      "p",
      flood?.status === "ready"
        ? "Flood mapping returned for this point. Review the FEMA evidence below; it does not clear the whole parcel of flood risk."
        : "Flood risk remains unknown. Missing or unavailable mapping does not establish low risk.",
    ),
  );
  const decision = node("div", "");
  decision.append(
    node("h4", "Before a purchase decision"),
    node(
      "p",
      "Confirm parcel identity, title, liens, permitted use and sale terms. Comparable-sale value and acquisition costs are not established by this report.",
    ),
  );
  grid.append(location, risk, decision);
  card.append(grid);
  return card;
}
