/** Aggregate-only owner CRM view; records and access decisions stay on the server. */
export type Statistics = {
  as_of: number;
  total_users: number;
  categories: Record<string, number>;
  memberships: Record<string, number>;
  billing_records_older_than_day: number;
  oldest_billing_sync: number | null;
  basis: string;
};

export function renderStatistics(
  container: HTMLElement,
  stats: Statistics,
  labels: Record<string, string>,
  choose: (category: string, membership: string) => void,
) {
  container.replaceChildren();
  const heading = document.createElement("h3");
  heading.textContent = "User statistics";
  container.append(heading);
  const cards = document.createElement("div");
  cards.className = "crm-statistics-grid";
  const add = (
    label: string,
    count: number,
    category: string,
    membership = "",
  ) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "crm-statistic button secondary";
    button.setAttribute("aria-label", `Show ${label.toLowerCase()}: ${count}`);
    const value = document.createElement("strong");
    value.textContent = String(count);
    const caption = document.createElement("span");
    caption.textContent = label;
    button.append(value, caption);
    button.addEventListener("click", () => choose(category, membership));
    cards.append(button);
  };
  add("Users", stats.total_users, "user");
  add("Trial users", stats.memberships.trial || 0, "user", "trial");
  add("Paid users", stats.memberships.paid || 0, "user", "paid");
  container.append(cards);
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Other categories and counting rules";
  details.append(summary);
  const breakdown = document.createElement("div");
  breakdown.className = "crm-actions";
  for (const [key, count] of Object.entries(stats.memberships)) {
    if (key === "trial" || key === "paid") continue;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "button secondary";
    button.textContent = `${labels[key] || key}: ${count}`;
    button.addEventListener("click", () => choose("user", key));
    breakdown.append(button);
  }
  for (const [key, label] of [
    ["owner", "Owners"],
    ["smoke_test", "Smoke tests"],
    ["contact", "Contacts / external projects"],
  ] as const) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "button secondary";
    button.textContent = `${label}: ${stats.categories[key] || 0}`;
    button.addEventListener("click", () => choose(key, ""));
    breakdown.append(button);
  }
  const note = document.createElement("p");
  note.textContent = `${stats.basis} Counts follow project, search and profile filters, before account category or membership filters. Updated ${new Date(stats.as_of * 1000).toLocaleString()}.`;
  details.append(breakdown, note);
  if (stats.billing_records_older_than_day) {
    const warning = document.createElement("p");
    warning.textContent = `${stats.billing_records_older_than_day} billing record(s) were last synchronized more than 24 hours ago. Counts may lag Stripe changes.`;
    details.append(warning);
  }
  container.append(details);
}
