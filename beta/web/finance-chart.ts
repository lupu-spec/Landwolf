/** Exact, accessible SVG charts with a zero baseline and an accompanying table. */
export type Series = {
  label: string;
  values: (number | null)[];
  color: string;
};
export function chartBounds(series: Series[]): { min: number; max: number } {
  const values = series
    .flatMap((s) => s.values)
    .filter((v): v is number => v !== null && Number.isFinite(v));
  return { min: Math.min(0, ...values), max: Math.max(1, ...values) };
}
export function renderChart(
  title: string,
  labels: string[],
  series: Series[],
  money = true,
): HTMLElement {
  const figure = document.createElement("figure");
  figure.className = "finance-chart";
  const caption = document.createElement("figcaption");
  caption.textContent = title;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 640 250");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `${title}. Exact values follow in a table.`);
  const { min, max } = chartBounds(series);
  const y = (v: number) => 205 - ((v - min) / (max - min)) * 175;
  const text = (x: number, at: number, value: string) => {
    const el = document.createElementNS(svg.namespaceURI, "text");
    el.setAttribute("x", String(x));
    el.setAttribute("y", String(at));
    el.textContent = value;
    svg.append(el);
  };
  const format = (value: number | null) =>
    value === null
      ? "Unknown"
      : money
        ? new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
          }).format(value / 100)
        : String(value);
  text(5, 20, format(max));
  text(5, 225, format(min));
  const axis = document.createElementNS(svg.namespaceURI, "line");
  for (const [key, value] of Object.entries({
    x1: 70,
    x2: 630,
    y1: y(0),
    y2: y(0),
  }))
    axis.setAttribute(key, String(value));
  axis.setAttribute("class", "finance-axis");
  svg.append(axis);
  const group = 550 / Math.max(1, labels.length);
  const width = Math.min(35, (group - 12) / Math.max(1, series.length));
  labels.forEach((label, index) => {
    text(75 + group * index, 247, label.slice(2));
    series.forEach((item, n) => {
      const value = item.values[index];
      if (value === null || value === undefined || !Number.isFinite(value))
        return;
      const rect = document.createElementNS(svg.namespaceURI, "rect");
      rect.setAttribute("x", String(75 + group * index + width * n));
      rect.setAttribute("y", String(Math.min(y(0), y(value))));
      rect.setAttribute("height", String(Math.abs(y(value) - y(0))));
      rect.setAttribute("width", String(width - 2));
      rect.setAttribute("class", `finance-bar ${item.color}`);
      const tip = document.createElementNS(svg.namespaceURI, "title");
      tip.textContent = `${label} ${item.label}: ${format(value)}`;
      rect.append(tip);
      svg.append(rect);
    });
  });
  figure.append(caption, svg);
  const table = document.createElement("table");
  table.className = "finance-table";
  const head = document.createElement("tr");
  for (const label of ["Month", ...series.map((s) => s.label)]) {
    const th = document.createElement("th");
    th.textContent = label;
    th.scope = "col";
    head.append(th);
  }
  const thead = document.createElement("thead");
  thead.append(head);
  table.append(thead);
  const tbody = document.createElement("tbody");
  labels.forEach((label, index) => {
    const tr = document.createElement("tr");
    for (const value of [
      label,
      ...series.map((s) => format(s.values[index] ?? null)),
    ]) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    }
    tbody.append(tr);
  });
  table.append(tbody);
  const wrap = document.createElement("div");
  wrap.className = "finance-table-wrap";
  wrap.append(table);
  figure.append(wrap);
  return figure;
}
