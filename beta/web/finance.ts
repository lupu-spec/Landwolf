/** Private owner workspace; no bank credentials or finance records in browser storage. */
import type { Api } from "./crm";
import { renderChart } from "./finance-chart";

type Budget = {
  amount_cents: number | null;
  interval: "month" | "year";
  renewal_date: string | null;
  allocation_percent: number;
};
type Plan = {
  revision: number;
  render: Budget;
  spaceship: Budget;
  openai: Budget;
  other: Budget;
  new_users_monthly: number;
  conversion_percent: number;
  churn_percent: number;
  monthly_price_cents: number;
  processing_percent: number;
  processing_fixed_cents: number;
};
type Expense = {
  id: string;
  date: string;
  vendor: string;
  amount_cents: number;
  allocation_percent: number;
  business_cents: number;
  source: string;
};
type ImportResult = {
  selected: number;
  duplicates: number;
  skipped: number;
  note: string;
  rows: {
    date: string;
    vendor: string;
    amount_cents: number;
    allocation_percent: number;
  }[];
};
type Forecast = {
  scenario: string;
  month: string;
  revenue_cents: number | null;
  cost_cents: number;
  net_cents: number | null;
  expected_subscriptions: number;
  missing_costs: string[];
};
type Report = {
  subscription_collections_all_time_cents: number | null;
  as_of: number;
  stripe_available: boolean;
  stripe_stale: boolean;
  stripe: null | {
    as_of: number;
    plan_run_rate_cents: number;
    active_subscriptions: number;
    excluded_records: number;
    basis: string;
  };
  history: {
    month: string;
    receipts_cents: number | null;
    subscription_receipts_cents: number | null;
    refunds_cents: number | null;
    fees_cents: number | null;
    expenses_cents: number;
    net_cents: number | null;
    new_users: number;
    partial_month: boolean;
  }[];
  expenses: Expense[];
  plan: Plan;
  forecast: Forecast[];
  users: { total_users: number; memberships: Record<string, number> };
  recommendations: {
    title: string;
    basis: string;
    action: string;
    metric: string;
  }[];
  limits: string;
};
const vendors = {
  render: "Render",
  spaceship: "Spaceship",
  openai: "OpenAI / ChatGPT",
  other: "Other business expense",
};
const amount = (value: number | null) =>
  value === null
    ? "Unknown"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
      }).format(value / 100);
const node = <K extends keyof HTMLElementTagNameMap>(
  tag: K,
  text = "",
  className = "",
) => {
  const el = document.createElement(tag);
  el.textContent = text;
  el.className = className;
  return el;
};
function field(label: string, value: string, type = "number") {
  const wrap = node("label", label);
  const input = node("input");
  input.type = type;
  input.value = value;
  input.id = `finance-${crypto.randomUUID()}`;
  if (type === "number") input.step = "any";
  wrap.htmlFor = input.id;
  wrap.append(input);
  return { wrap, input };
}
function select(label: string, options: Record<string, string>, value: string) {
  const wrap = node("label", label);
  const input = node("select");
  input.id = `finance-${crypto.randomUUID()}`;
  wrap.htmlFor = input.id;
  for (const [key, text] of Object.entries(options)) {
    const option = node("option", text);
    option.value = key;
    input.append(option);
  }
  input.value = value;
  wrap.append(input);
  return { wrap, input };
}
function button(label: string, handler: () => void) {
  const el = node("button", label, "button secondary");
  el.type = "button";
  el.addEventListener("click", handler);
  return el;
}
function dollars(input: HTMLInputElement): number | null {
  if (input.value.trim() === "") return null;
  const value = Number(input.value);
  if (
    !Number.isFinite(value) ||
    Math.abs(value) > 1_000_000 ||
    Math.abs(value * 100 - Math.round(value * 100)) > 0.000001
  )
    throw new Error("Enter dollars with at most two decimal places.");
  return Math.round(value * 100);
}
export function setupFinance(api: Api) {
  const panel = document.getElementById("finance-panel")!;
  let generation = 0;
  let active = false;
  function clear() {
    generation++;
    active = false;
    panel.replaceChildren();
    panel.oninput = null;
    panel.hidden = true;
  }
  async function open() {
    active = true;
    const token = ++generation;
    panel.replaceChildren(node("p", "Loading owner financial dashboard…"));
    try {
      const report = await api<Report>("/api/admin/finance");
      if (active && token === generation) render(report);
    } catch (error) {
      if (active && token === generation)
        panel.replaceChildren(
          node(
            "p",
            error instanceof Error ? error.message : "Unable to load finance.",
          ),
          button("Retry financial dashboard", () => void open()),
        );
    }
  }
  function render(report: Report) {
    const token = generation;
    panel.replaceChildren();
    const status = node("p", "", "finance-status");
    status.setAttribute("role", "status");
    const error = (reason: unknown) => {
      if (active && token === generation) {
        status.textContent =
          reason instanceof Error ? reason.message : "Please retry.";
        status.scrollIntoView({ block: "nearest" });
      }
    };
    let dirty = false;
    panel.oninput = () => {
      dirty = true;
    };
    const current = report.history.at(-1)!;
    const header = node("div", "", "finance-toolbar");
    const refresh = button("Refresh Stripe", () => {
      if (dirty) {
        error(
          new Error(
            "Save your entered expense or forecast settings before refreshing Stripe.",
          ),
        );
        return;
      }
      refresh.disabled = true;
      status.textContent = "Reading Stripe; existing billing is unchanged…";
      void api("/api/admin/finance/refresh", "POST")
        .then(() => {
          if (active && token === generation) return open();
        })
        .catch(error)
        .finally(() => {
          refresh.disabled = false;
        });
    });
    refresh.disabled = !report.stripe_available;
    header.append(
      node(
        "p",
        report.stripe
          ? `Stripe last verified ${new Date(report.stripe.as_of * 1000).toLocaleString()}${report.stripe_stale ? " · Stale: refresh before decisions" : ""}`
          : "Stripe has not been verified here. Unknown is not zero.",
      ),
      refresh,
    );
    panel.append(
      header,
      status,
      node(
        "p",
        "Owner only · USD · UTC calendar months · Current month is partial. Expenses are recorded business allocations, not a complete bank feed.",
        "muted",
      ),
    );
    const cards = node("div", "", "finance-cards");
    for (const [label, value] of [
      [
        "Subscription collections this month",
        amount(current.subscription_receipts_cents),
      ],
      ["Recorded business expenses", amount(current.expenses_cents)],
      [
        "Active plan run-rate (not cash)",
        amount(report.stripe?.plan_run_rate_cents ?? null),
      ],
      ["Real users", String(report.users.total_users)],
      [
        "All-time subscription collections",
        amount(report.subscription_collections_all_time_cents),
      ],
    ]) {
      const card = node("div", "", "finance-card");
      card.append(node("span", label), node("strong", value));
      cards.append(card);
    }
    panel.append(cards);
    panel.append(
      node(
        "p",
        report.stripe?.basis ??
          "Connect the existing live Stripe configuration before revenue refresh. No sandbox receipts are used.",
      ),
    );
    if (report.stripe?.excluded_records)
      panel.append(
        node(
          "p",
          `${report.stripe.excluded_records} non-USD/unsupported or non-subscription invoice records excluded. This is not a complete account reconciliation.`,
          "finance-warning",
        ),
      );
    const charts = node("div", "", "finance-charts");
    charts.append(
      renderChart(
        "Cash receipts and recorded costs · six months",
        report.history.map((x) => x.month),
        [
          {
            label: "Stripe account receipts",
            values: report.history.map((x) => x.receipts_cents),
            color: "navy",
          },
          {
            label: "Fees + recorded expenses",
            values: report.history.map((x) =>
              x.fees_cents === null ? null : x.fees_cents + x.expenses_cents,
            ),
            color: "orange",
          },
          {
            label: "Net before missing costs / tax",
            values: report.history.map((x) => x.net_cents),
            color: "teal",
          },
        ],
      ),
      renderChart(
        "New real users · owners and smoke tests excluded",
        report.history.map((x) => x.month),
        [
          {
            label: "Registered users",
            values: report.history.map((x) => x.new_users),
            color: "navy",
          },
        ],
        false,
      ),
    );
    panel.append(charts);
    const forecastSection = node("section", "", "finance-section");
    forecastSection.append(
      node("h2", "Next three months · scenario planning"),
      node(
        "p",
        "These are editable what-if scenarios—not statistical predictions or guaranteed cash. Annual subscription run-rate is spread monthly, not the actual renewal schedule. Complimentary pilots are not assumed to convert automatically.",
      ),
    );
    const choice = select(
      "Forecast scenario",
      {
        conservative: "Conservative",
        base: "Base assumptions",
        growth: "Growth experiment",
      },
      "base",
    );
    const forecastChart = node("div");
    const draw = () => {
      const rows = report.forecast.filter(
        (x) => x.scenario === choice.input.value,
      );
      forecastChart.replaceChildren(
        renderChart(
          "Projected monthly run-rate and costs",
          rows.map((x) => x.month),
          [
            {
              label: "Normalized receipts hypothesis",
              values: rows.map((x) => x.revenue_cents),
              color: "navy",
            },
            {
              label: "Budget + fee hypothesis",
              values: rows.map((x) => x.cost_cents),
              color: "orange",
            },
            {
              label: "Net before missing costs",
              values: rows.map((x) => x.net_cents),
              color: "teal",
            },
          ],
        ),
      );
      const missing = [...new Set(rows.flatMap((x) => x.missing_costs))];
      if (missing.length)
        forecastChart.prepend(
          node(
            "p",
            `Incomplete costs: ${missing.join(", ")}. Net excludes these costs—do not treat it as profit.`,
            "finance-warning",
          ),
        );
    };
    choice.input.addEventListener("change", draw);
    draw();
    forecastSection.append(choice.wrap, forecastChart);
    panel.append(forecastSection);
    const settings = node("details", "", "finance-section");
    settings.append(
      node("summary", "Edit cost budgets and growth assumptions"),
    );
    const planForm = node("form");
    const planFields = node("div", "", "finance-form-grid");
    const budgets = Object.entries(vendors).map(([key, label]) => {
      const budget = report.plan[key as keyof typeof vendors];
      const section = node("fieldset");
      section.append(node("legend", label));
      const cost = field(
        "Budget dollars (blank = unknown)",
        budget.amount_cents === null ? "" : String(budget.amount_cents / 100),
      );
      const interval = select(
        "Budget frequency",
        { month: "Monthly", year: "Annual cash renewal" },
        budget.interval,
      );
      const renewal = field(
        "Annual renewal date",
        budget.renewal_date ?? "",
        "date",
      );
      const allocation = field(
        "Business allocation %",
        String(budget.allocation_percent),
      );
      allocation.input.min = "0";
      allocation.input.max = "100";
      section.append(cost.wrap, interval.wrap, renewal.wrap, allocation.wrap);
      planFields.append(section);
      return { key, cost, interval, renewal, allocation };
    });
    const assumptions = (
      [
        ["new_users_monthly", "New real users per month", 1],
        ["conversion_percent", "Voluntary paid conversion %", 1],
        ["churn_percent", "Monthly churn %", 1],
        ["monthly_price_cents", "New monthly plan price dollars", 100],
        ["processing_percent", "Processing fee % hypothesis", 1],
        [
          "processing_fixed_cents",
          "Processing fee dollars per payment hypothesis",
          100,
        ],
      ] as const
    ).map(([key, label, scale]) => {
      const input = field(label, String(report.plan[key] / scale));
      planFields.append(input.wrap);
      return { key, input, scale };
    });
    const save = node("button", "Save forecast assumptions", "button");
    save.type = "submit";
    planForm.append(
      node(
        "p",
        "Use actual invoices for budgets. ChatGPT membership is separate from API usage; add API spend as an Other business expense if applicable. No fee or conversion rate here is a verified vendor quote.",
      ),
      planFields,
      save,
    );
    planForm.addEventListener("submit", (event) => {
      event.preventDefault();
      try {
        const updated: Plan = { ...report.plan };
        for (const b of budgets)
          updated[b.key as keyof typeof vendors] = {
            amount_cents: dollars(b.cost.input),
            interval: b.interval.input.value as "month" | "year",
            renewal_date: b.renewal.input.value || null,
            allocation_percent: Number(b.allocation.input.value),
          };
        for (const a of assumptions)
          updated[a.key] =
            a.scale === 100
              ? (dollars(a.input.input) ?? 0)
              : Number(a.input.input.value);
        save.disabled = true;
        void api("/api/admin/finance/plan", "PUT", updated)
          .then(() => {
            if (active && token === generation) return open();
          })
          .catch(error)
          .finally(() => {
            save.disabled = false;
          });
      } catch (reason) {
        error(reason);
      }
    });
    settings.append(planForm);
    panel.append(settings);
    const expenses = node("section", "", "finance-section");
    expenses.append(
      node("h2", "Business expenses"),
      node(
        "p",
        "Enter verified USD expenses, or preview a business-only Amex CSV. Positive = expense; negative = vendor credit. Stripe fees are already counted separately—do not add them twice.",
      ),
    );
    const expenseForm = node("form");
    const expenseGrid = node("div", "", "finance-form-grid");
    const when = field(
      "Expense date",
      new Date().toISOString().slice(0, 10),
      "date",
    );
    const vendor = select("Expense vendor", vendors, "render");
    const value = field("Expense amount dollars", "");
    value.input.required = true;
    const allocation = field("Expense business allocation %", "100");
    allocation.input.min = "0";
    allocation.input.max = "100";
    const reference = field(
      "Distinct charge reference (optional, no card details)",
      "",
      "text",
    );
    reference.input.maxLength = 40;
    expenseGrid.append(
      when.wrap,
      vendor.wrap,
      value.wrap,
      allocation.wrap,
      reference.wrap,
    );
    const add = node("button", "Record business expense", "button");
    add.type = "submit";
    expenseForm.append(expenseGrid, add);
    expenseForm.addEventListener("submit", (event) => {
      event.preventDefault();
      try {
        const cents = dollars(value.input);
        if (cents === null) throw new Error("Enter an expense amount.");
        add.disabled = true;
        void api("/api/admin/finance/expenses", "POST", {
          date: when.input.value,
          vendor: vendor.input.value,
          amount_cents: cents,
          allocation_percent: Number(allocation.input.value),
          reference: reference.input.value,
        })
          .then(() => {
            if (active && token === generation) return open();
          })
          .catch(error)
          .finally(() => {
            add.disabled = false;
          });
      } catch (reason) {
        error(reason);
      }
    });
    expenses.append(expenseForm);
    const importBox = node("details");
    importBox.append(
      node("summary", "Preview an Amex CSV import"),
      node(
        "p",
        "Export Date, Description, Amount in USD; at most 500 rows / 100 KB. Only Render, Spaceship and OpenAI/ChatGPT matches are selected. Other personal rows and card details are not stored. Review matches, duplicate warnings and allocation before confirming. No live card connection is active.",
      ),
    );
    const file = field("Amex CSV file", "", "file");
    file.input.accept = ".csv,text/csv";
    const percent = field("CSV business allocation %", "100");
    let pending: string | null = null;
    let importGeneration = 0;
    const preview = node("div");
    const confirm = button("Confirm business expense import", () => {
      if (pending === null) return;
      confirm.disabled = true;
      void api<ImportResult>("/api/admin/finance/import", "POST", {
        csv_text: pending,
        allocation_percent: Number(percent.input.value),
        confirm: true,
      })
        .then(() => {
          if (active && token === generation) return open();
        })
        .catch(error)
        .finally(() => {
          confirm.disabled = false;
        });
    });
    confirm.hidden = true;
    const resetPreview = () => {
      importGeneration++;
      pending = null;
      confirm.hidden = true;
      preview.replaceChildren();
    };
    file.input.addEventListener("change", resetPreview);
    percent.input.addEventListener("input", resetPreview);
    const inspect = button("Preview selected expenses", () => {
      const selected = file.input.files?.[0];
      if (!selected || selected.size > 100000) {
        error(new Error("Choose a CSV no larger than 100 KB."));
        return;
      }
      inspect.disabled = true;
      resetPreview();
      const importToken = importGeneration;
      const importAllocation = Number(percent.input.value);
      void selected
        .text()
        .then((text) => {
          if (
            !active ||
            token !== generation ||
            importToken !== importGeneration
          )
            return;
          return api<ImportResult>("/api/admin/finance/import", "POST", {
            csv_text: text,
            allocation_percent: importAllocation,
            confirm: false,
          }).then((result) => {
            if (
              !active ||
              token !== generation ||
              importToken !== importGeneration
            )
              return;
            pending = text;
            preview.replaceChildren(
              node(
                "p",
                `${result.selected} selected · ${result.duplicates} possible duplicates · ${result.skipped} unrelated rows skipped. ${result.note}`,
              ),
            );
            for (const row of result.rows)
              preview.append(
                node(
                  "p",
                  `${row.date} · ${row.vendor} · ${amount(row.amount_cents)} · ${row.allocation_percent}% business`,
                ),
              );
            confirm.hidden = result.selected === 0;
          });
        })
        .catch(error)
        .finally(() => {
          inspect.disabled = false;
        });
    });
    importBox.append(file.wrap, percent.wrap, inspect, preview, confirm);
    expenses.append(importBox);
    const records = node("details");
    records.append(
      node(
        "summary",
        `Recorded expenses (${report.expenses.length}) · current six-month period`,
      ),
    );
    for (const row of report.expenses)
      records.append(
        node(
          "p",
          `${row.date} · ${row.vendor} · ${amount(row.amount_cents)} × ${row.allocation_percent}% = ${amount(row.business_cents)} · ${row.source}`,
        ),
      );
    expenses.append(records);
    panel.append(expenses);
    const actions = node("section", "", "finance-section");
    actions.append(node("h2", "Growth playbook · actions tied to evidence"));
    for (const rec of report.recommendations) {
      const article = node("article", "", "finance-recommendation");
      article.append(
        node("h3", rec.title),
        node("p", rec.basis, "muted"),
        node("p", rec.action),
        node("p", rec.metric),
      );
      actions.append(article);
    }
    panel.append(actions, node("p", report.limits, "finance-warning"));
  }
  return { open, clear };
}
