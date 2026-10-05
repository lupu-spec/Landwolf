/** Private, deterministic research. All untrusted content is rendered as text. */
type Api = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
const topics = {
  access: "Legal access",
  use: "Permitted use",
  title: "Title and sale terms",
  water: "Water",
  septic: "Wastewater",
  power: "Power",
  flood: "Flood and site conditions",
};
type Topic = keyof typeof topics;
type Goal = {
  intended_use: string;
  use_details: string;
  budget: number | null;
  requirements: Topic[];
  max_months: number | null;
};
type Evidence = {
  topic: Topic;
  status: string;
  note: string;
  source_ref: string;
  checked_on: string | null;
  scope: string;
  applicability_confirmed: boolean;
};
type Costs = {
  purchase_basis: string;
  purchase_price: number | null;
  known_costs: number | null;
  unresolved_low: number | null;
  unresolved_high: number | null;
  net_proceeds: number | null;
  target_return_pct: number;
  holding_months: number | null;
  monthly_holding: number | null;
  extra_cost: number;
  delay_months: number;
};
type CaseInput = {
  revision: number;
  hunt_id: string | null;
  goal: Goal;
  costs: Costs;
  evidence: Evidence[];
  authority: string;
  authority_confirmed: boolean;
  pause_reason: string;
  pause_note: string;
};
type Decision = {
  costs: {
    known_total: number | null;
    allowance: number | null;
    budget_allowance: number | null;
    return_allowance: number | null;
    favorable_total: number | null;
    adverse_total: number | null;
    adverse_return_pct: number | null;
    status: string;
    warnings: string[];
  };
  blockers: string[];
  questions: {
    topic: string;
    label: string;
    question: string;
    priority: string;
    reason: string;
  }[];
  pause_condition_met: boolean | null;
  summary: string;
  limitation: string;
};
type Case = {
  listing_id: string;
  revision: number;
  input: CaseInput;
  effective_goal: Goal;
  property: {
    title: string;
    state: string;
    county: string | null;
    parcel_number: string | null;
    tract: string;
    source_url: string;
    retrieved_at: string;
    price_kind: string;
  };
  available: boolean;
  decision: Decision;
  history: {
    kind: string;
    message: string;
    at: number;
    previous_allowance: number | null;
    allowance: number | null;
  }[];
};
type Brief = {
  authority: string;
  topic: string;
  intended_use: string;
  use_details: string;
  shared: boolean;
  properties: {
    listing_id: string;
    title: string;
    parcel_number: string | null;
    state: string;
    county: string | null;
    question: string;
    reason: string;
  }[];
};
type HuntResearch = {
  goal: Goal;
  revision: number;
  cases: Case[];
  brief: Brief[];
};

function node<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  text = "",
  css = "",
): HTMLElementTagNameMap[K] {
  const value = document.createElement(tag);
  value.textContent = text;
  value.className = css;
  return value;
}
const money = (n: number | null) =>
  n === null
    ? "Needs inputs"
    : n.toLocaleString("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
      });
const errorText = (e: unknown) =>
  e instanceof Error
    ? e.message
    : "Research is temporarily unavailable. Try again.";
function button(
  label: string,
  action: () => void,
  css = "button secondary small",
): HTMLButtonElement {
  const b = node("button", label, css);
  b.type = "button";
  b.addEventListener("click", action);
  return b;
}
function section(title: string, open = false): HTMLDetailsElement {
  const details = node("details", "", "decision-section");
  details.open = open;
  details.append(node("summary", title));
  return details;
}
function input(
  parent: HTMLElement,
  label: string,
  value: string | number | null,
  type = "text",
  max = 500,
): HTMLInputElement {
  const wrapper = node("label", label);
  const field = node("input");
  field.type = type;
  field.value = value === null ? "" : String(value);
  field.maxLength = max;
  if (type === "number") {
    field.min = "0";
    field.max = "1000000000";
    field.step = "0.01";
  }
  wrapper.append(field);
  parent.append(wrapper);
  return field;
}
function select(
  parent: HTMLElement,
  label: string,
  values: [string, string][],
  selected: string,
): HTMLSelectElement {
  const wrapper = node("label", label);
  const field = node("select");
  for (const [value, text] of values) {
    const option = node("option", text);
    option.value = value;
    field.append(option);
  }
  field.value = selected;
  wrapper.append(field);
  parent.append(wrapper);
  return field;
}
function check(
  parent: HTMLElement,
  label: string,
  checked: boolean,
): HTMLInputElement {
  const wrapper = node("label", "", "decision-check");
  const field = node("input");
  field.type = "checkbox";
  field.checked = checked;
  wrapper.append(field, node("span", label));
  parent.append(wrapper);
  return field;
}
const number = (field: HTMLInputElement) =>
  field.value.trim() === "" ? null : field.valueAsNumber;

function goalFields(
  parent: HTMLElement,
  goal: Goal,
): { read: () => Goal; fieldset: HTMLFieldSetElement } {
  const fieldset = node("fieldset", "", "decision-goal");
  fieldset.append(node("legend", "Your research goal"));
  const grid = node("div", "", "decision-grid");
  const use = select(
    grid,
    "Intended use",
    [
      ["home", "Home / cabin"],
      ["recreation", "Recreation"],
      ["agriculture", "Agriculture"],
      ["investment", "Investment"],
      ["other", "Other"],
    ],
    goal.intended_use,
  );
  const budget = input(
    grid,
    "Total project budget ($, optional)",
    goal.budget,
    "number",
  );
  budget.min = "0.01";
  const detail = input(
    grid,
    "Specific use (optional)",
    goal.use_details,
    "text",
    160,
  );
  const more = section("Requirements and timing");
  more.append(
    node(
      "p",
      "Mark your non-negotiable requirements. Unknown answers do not satisfy them.",
      "input-note",
    ),
  );
  const checks = (Object.entries(topics) as [Topic, string][]).map(
    ([key, label]) =>
      [key, check(more, label, goal.requirements.includes(key))] as const,
  );
  const months = input(
    more,
    "Maximum holding months (optional)",
    goal.max_months,
    "number",
  );
  months.max = "120";
  months.step = "1";
  fieldset.append(grid, more);
  parent.append(fieldset);
  return {
    fieldset,
    read: () => ({
      intended_use: use.value,
      use_details: detail.value.trim(),
      budget: number(budget),
      requirements: checks.filter(([, c]) => c.checked).map(([key]) => key),
      max_months: number(months),
    }),
  };
}

function decisionOutput(item: Case): HTMLElement {
  const result = node("section", "", "decision-output");
  result.append(
    node("h3", "What could change your decision"),
    node("p", item.decision.summary),
  );
  const metrics = node("dl", "", "decision-metrics");
  for (const [label, value] of [
    ["Remaining allowance", money(item.decision.costs.allowance)],
    ["Favorable total cost", money(item.decision.costs.favorable_total)],
    ["Adverse total with stress", money(item.decision.costs.adverse_total)],
    [
      "Adverse total-period return",
      item.decision.costs.adverse_return_pct === null
        ? "Needs inputs"
        : `${item.decision.costs.adverse_return_pct}%`,
    ],
  ])
    metrics.append(node("dt", label), node("dd", value));
  result.append(metrics);
  const states: Record<string, string> = {
    incomplete: "Enter the missing cost assumptions to assess your target.",
    within_assumptions: "Within the target across your entered cost range.",
    exceeds_target: "Even the favorable cost case exceeds your target.",
    sensitive:
      "The cost range crosses your target; quotes or timing could change the outcome.",
  };
  result.append(
    node("p", states[item.decision.costs.status] ?? "Review assumptions."),
  );
  if (
    item.decision.costs.allowance !== null &&
    item.decision.costs.allowance < 0
  )
    result.append(
      node(
        "p",
        "Negative allowance is a shortfall before unresolved work.",
        "source-state warn",
      ),
    );
  const list = node("ol", "", "decision-questions");
  for (const q of item.decision.questions) {
    const row = node("li");
    row.append(
      node("strong", `${q.priority}: ${q.label}`),
      node("p", q.question),
      node("p", q.reason, "input-note"),
    );
    list.append(row);
  }
  result.append(list);
  if (item.decision.blockers.length)
    result.append(
      node("p", item.decision.blockers.join(" · "), "source-state warn"),
    );
  if (item.input.pause_reason)
    result.append(
      node(
        "p",
        `Paused for ${item.input.pause_reason}${item.input.pause_note ? `: ${item.input.pause_note}` : ""}. ${item.decision.pause_condition_met === true ? "That condition is now met; review all remaining requirements." : "That condition is not yet confirmed as met."}`,
      ),
    );
  const notes = section("Calculation assumptions and limits");
  for (const warning of item.decision.costs.warnings)
    notes.append(node("p", warning));
  notes.append(node("p", item.decision.limitation));
  result.append(notes);
  if (item.history.length) {
    const history = section("Research changes");
    for (const event of item.history)
      history.append(
        node(
          "p",
          `${new Date(event.at * 1000).toLocaleString()} — ${event.message} Allowance: ${money(event.previous_allowance)} → ${money(event.allowance)}`,
        ),
      );
    result.append(history);
  }
  return result;
}

function packet(item: Case): HTMLElement {
  const root = node("article");
  root.append(
    node("h2", item.property.title),
    node(
      "p",
      `${item.property.county ?? "County unconfirmed"}, ${item.property.state} · Parcel ${item.property.parcel_number ?? "not verified"} · Listing ${item.listing_id}`,
    ),
    node(
      "p",
      `Intended use: ${item.effective_goal.intended_use} ${item.effective_goal.use_details}`,
    ),
    node("p", `Source: ${item.property.source_url}`),
    node("p", `Source retrieved: ${item.property.retrieved_at}`),
    decisionOutput(item),
  );
  root.append(node("h3", "Recorded answers — supplied by the customer"));
  for (const fact of item.input.evidence)
    root.append(
      node(
        "p",
        `${topics[fact.topic]}: ${fact.status}. ${fact.note} Source/reference: ${fact.source_ref || "not supplied"}. Checked: ${fact.checked_on ?? "not supplied"}. Scope: ${fact.scope}.`,
      ),
    );
  return root;
}
function briefContent(groups: Brief[]): HTMLElement {
  const root = node("div");
  root.append(
    node(
      "p",
      "Verify the responsible authority and each parcel. Answers remain property-specific; general rules require confirmed applicability. No requests are sent automatically.",
    ),
  );
  for (const group of groups) {
    root.append(
      node("h4", `${group.authority} — ${group.topic}`),
      node(
        "p",
        `Use: ${group.intended_use} ${group.use_details} · ${group.properties.length} propert${group.properties.length === 1 ? "y" : "ies"}`,
      ),
    );
    for (const p of group.properties)
      root.append(
        node(
          "p",
          `${p.title} (${p.state}, ${p.county ?? "county unconfirmed"}; parcel ${p.parcel_number ?? "unconfirmed"}; listing ${p.listing_id}): ${p.question} ${p.reason}`,
        ),
      );
  }
  return root;
}
function printContent(content: HTMLElement): void {
  for (const details of content.querySelectorAll("details"))
    details.open = true;
  document.getElementById("decision-print")?.remove();
  const root = node("section");
  root.id = "decision-print";
  root.append(
    node("h1", "LandWolf research packet"),
    node(
      "p",
      `Prepared ${new Date().toLocaleString()}. Private customer research; no certification of title, value or buildability.`,
    ),
    content,
  );
  // A modal dialog's top layer must not obscure the print-only packet.
  const host =
    document.querySelector<HTMLDialogElement>("dialog[open]") ?? document.body;
  host.append(root);
  document.body.classList.add("printing-research");
  const cleanup = () => {
    document.body.classList.remove("printing-research");
    root.remove();
  };
  window.addEventListener("afterprint", cleanup, { once: true });
  try {
    window.print();
  } finally {
    cleanup();
  }
}

export function setupDecisionWorkspace(
  api: Api,
  session: () => string,
  openProperty: (id: string) => Promise<void>,
) {
  let generation = 0;
  let propertySequence = 0;
  function clear() {
    generation++;
    propertySequence++;
    document.getElementById("decision-workspace")?.replaceChildren();
    document.getElementById("decision-print")?.remove();
    document.body.classList.remove("printing-research");
  }

  async function property(
    listingId: string,
    preferredHunt?: string,
  ): Promise<void> {
    const host = document.getElementById("decision-workspace");
    if (!host) return;
    const epoch = generation,
      sequence = ++propertySequence,
      token = session();
    const current = () =>
      Boolean(
        token &&
        session() === token &&
        generation === epoch &&
        sequence === propertySequence,
      );
    host.replaceChildren(node("p", "Loading decision research…"));
    try {
      const [initial, huntList] = await Promise.all([
        api<Case>(`/api/decision-cases/${encodeURIComponent(listingId)}`),
        api<{ hunts: { id: string; name: string }[] }>("/api/hunts"),
      ]);
      if (!current()) return;
      let saved = initial;
      let displayed = initial;
      const form = node("form", "", "decision-form");
      form.setAttribute("aria-label", "Decision research");
      const status = node("p");
      status.setAttribute("role", "status");
      const output = node("div");
      output.append(decisionOutput(initial));
      host.replaceChildren(
        node("h2", "Research your decision"),
        node(
          "p",
          "Record what matters, test your cost assumptions, and prepare the next questions. Research stays private to your account.",
        ),
        form,
        status,
        output,
      );
      const hunt = select(
        form,
        "Research within a Hunt (optional)",
        [
          ["", "This property only"],
          ...huntList.hunts.map((h) => [h.id, h.name] as [string, string]),
        ],
        initial.input.hunt_id ?? preferredHunt ?? "",
      );
      const goalHost = node("div");
      form.append(goalHost);
      let goal = goalFields(goalHost, initial.effective_goal);
      const goalNote = node("p", "", "input-note");
      form.append(goalNote);
      let goalLoading = false;
      let goalRequest = 0;
      async function loadGoal() {
        const request = ++goalRequest;
        goal.fieldset.disabled = Boolean(hunt.value);
        goalNote.textContent = hunt.value
          ? "Uses this Hunt's research goal. Edit it in the Hunt research panel."
          : "This goal applies to this property.";
        if (!hunt.value) {
          goalLoading = false;
          return;
        }
        goalLoading = true;
        try {
          const value = await api<{ goal: Goal }>(
            `/api/hunts/${encodeURIComponent(hunt.value)}/research-goal`,
          );
          if (!current() || request !== goalRequest) return;
          goalHost.replaceChildren();
          goal = goalFields(goalHost, value.goal);
          goal.fieldset.disabled = true;
          goalLoading = false;
        } catch (error) {
          if (current() && request === goalRequest)
            status.textContent = errorText(error);
        }
      }
      hunt.addEventListener("change", () => void loadGoal());
      const costs = section("Costs and stress test", true);
      costs.append(
        node(
          "p",
          "Additional known costs include closing, base holding and financing, but exclude unresolved work. All entries are your assumptions; blank is unknown.",
          "input-note",
        ),
      );
      const costGrid = node("div", "", "decision-grid");
      const c = initial.input.costs;
      const basis = select(
        costGrid,
        "Acquisition basis",
        [
          ["published", `Current ${initial.property.price_kind.toLowerCase()}`],
          ["entered", "My acquisition assumption"],
        ],
        c.purchase_basis,
      );
      const purchase = input(
        costGrid,
        "Acquisition assumption ($)",
        c.purchase_price,
        "number",
      );
      const basisChanged = () => {
        purchase.disabled = basis.value === "published";
        purchase.required = !purchase.disabled;
      };
      basis.addEventListener("change", basisChanged);
      basisChanged();
      const known = input(
        costGrid,
        "Known additional costs ($)",
        c.known_costs,
        "number",
      );
      const low = input(
        costGrid,
        "Unresolved work — low ($)",
        c.unresolved_low,
        "number",
      );
      const high = input(
        costGrid,
        "Unresolved work — high ($)",
        c.unresolved_high,
        "number",
      );
      costs.append(costGrid);
      const stress = section("Investment assumptions and stress controls");
      const stressGrid = node("div", "", "decision-grid");
      const proceeds = input(
        stressGrid,
        "Net exit proceeds after selling costs ($, optional)",
        c.net_proceeds,
        "number",
      );
      proceeds.min = "0.01";
      const target = input(
        stressGrid,
        "Target total-period return (%)",
        c.target_return_pct,
        "number",
      );
      target.max = "1000";
      const holding = input(
        stressGrid,
        "Base holding months",
        c.holding_months,
        "number",
      );
      holding.max = "120";
      holding.step = "1";
      const monthly = input(
        stressGrid,
        "Monthly carrying cost for added delay ($)",
        c.monthly_holding,
        "number",
      );
      monthly.max = "1000000";
      const extra = input(
        stressGrid,
        "Additional cost stress ($)",
        c.extra_cost,
        "number",
      );
      const delay = input(
        stressGrid,
        "Additional delay months",
        c.delay_months,
        "number",
      );
      delay.max = "120";
      delay.step = "1";
      stress.append(stressGrid);
      costs.append(stress);
      form.append(costs);
      const answers = section("Record evidence and answers");
      answers.append(
        node(
          "p",
          "Confirmed means you have recorded supporting evidence. LandWolf does not independently certify these answers. Date, note and source reference are required for an answered question.",
          "input-note",
        ),
      );
      const readers: (() => Evidence)[] = [];
      for (const [key, label] of Object.entries(topics) as [Topic, string][]) {
        const e = initial.input.evidence.find((e) => e.topic === key);
        const part = section(label);
        const state = select(
          part,
          `${label} answer`,
          [
            ["unknown", "Not yet verified"],
            ["confirmed", "Requirement supported"],
            ["failed", "Requirement not met"],
            ["not_applicable", "Not applicable"],
          ],
          e?.status ?? "unknown",
        );
        const note = input(part, `${label} — evidence note`, e?.note ?? "");
        const source = input(
          part,
          `${label} — source or document reference`,
          e?.source_ref ?? "",
        );
        const checked = input(
          part,
          `${label} — date checked`,
          e?.checked_on ?? "",
          "date",
        );
        checked.max = new Date().toISOString().slice(0, 10);
        const scope = select(
          part,
          `${label} — evidence scope`,
          [
            ["this_property", "This property"],
            ...(key === "use"
              ? [
                  ["general_rule", "General rule, applicability checked"] as [
                    string,
                    string,
                  ],
                ]
              : []),
          ],
          e?.scope ?? "this_property",
        );
        const applies = check(
          part,
          "I confirmed this rule applies to this specific property",
          e?.applicability_confirmed ?? false,
        );
        applies.parentElement!.hidden = key !== "use";
        const required = () => {
          for (const field of [note, source, checked])
            field.required = state.value !== "unknown";
        };
        state.addEventListener("change", required);
        required();
        readers.push(() => ({
          topic: key,
          status: state.value,
          note: note.value.trim(),
          source_ref: source.value.trim(),
          checked_on: checked.value || null,
          scope: scope.value,
          applicability_confirmed: applies.checked,
        }));
        answers.append(part);
      }
      const authority = input(
        answers,
        "Planning authority for shared questions",
        initial.input.authority,
        "text",
        160,
      );
      const authorityConfirmed = check(
        answers,
        "I confirmed this planning authority has jurisdiction",
        initial.input.authority_confirmed,
      );
      form.append(answers);
      const pause = section("Pause this property and remember why");
      const reason = select(
        pause,
        "Reason to pause",
        [
          ["", "Actively researching"],
          ["budget", "Budget / return target"],
          ["access", "Legal access"],
          ["use", "Permitted use"],
          ["power", "Power service"],
          ["timeline", "Holding timeline"],
          ["other", "Other — manual review"],
        ],
        initial.input.pause_reason,
      );
      const pauseNote = input(
        pause,
        "Pause note",
        initial.input.pause_note,
        "text",
        400,
      );
      pause.append(
        node(
          "p",
          "Opening this research or its Hunt checks current recorded inputs. A notice explains whether your condition changed. No email or background report reruns.",
          "input-note",
        ),
      );
      form.append(pause);
      const read = (): CaseInput => ({
        revision: saved.revision,
        hunt_id: hunt.value || null,
        goal: goal.read(),
        costs: {
          purchase_basis: basis.value,
          purchase_price: basis.value === "entered" ? number(purchase) : null,
          known_costs: number(known),
          unresolved_low: number(low),
          unresolved_high: number(high),
          net_proceeds: number(proceeds),
          target_return_pct: number(target) ?? 20,
          holding_months: number(holding),
          monthly_holding: number(monthly),
          extra_cost: number(extra) ?? 0,
          delay_months: number(delay) ?? 0,
        },
        evidence: readers.map((read) => read()),
        authority: authority.value.trim(),
        authority_confirmed: authorityConfirmed.checked,
        pause_reason: reason.value,
        pause_note: pauseNote.value.trim(),
      });
      const actions = node("div", "", "hunt-actions");
      let busy = false;
      async function submit(save: boolean) {
        if (busy || !current()) return;
        if (goalLoading) {
          status.textContent =
            "Wait for the Hunt goal, or reselect it to retry.";
          return;
        }
        // Expand invalid nested controls so native validation can focus them.
        for (const invalid of form.querySelectorAll(":invalid")) {
          let parent = invalid.parentElement;
          while (parent && parent !== form) {
            if (parent instanceof HTMLDetailsElement) parent.open = true;
            parent = parent.parentElement;
          }
        }
        if (!form.reportValidity()) return;
        busy = true;
        for (const b of actions.querySelectorAll("button")) b.disabled = true;
        try {
          const value = await api<Case>(
            `/api/${save ? "decision-cases" : "decision-preview"}/${encodeURIComponent(listingId)}`,
            save ? "PUT" : "POST",
            read(),
          );
          if (!current()) return;
          displayed = value;
          if (save) saved = value;
          output.replaceChildren(decisionOutput(value));
          status.textContent = save
            ? "Research recorded. It will be here when you return."
            : "Preview updated. Record research to retain these edits.";
        } catch (error) {
          if (current())
            status.textContent = `${errorText(error)} Your edits remain in the form.`;
        } finally {
          busy = false;
          for (const b of actions.querySelectorAll("button"))
            b.disabled = false;
        }
      }
      actions.append(
        button("Calculate preview", () => void submit(false)),
        button("Record research", () => void submit(true), "button primary"),
        button("Print displayed research", () =>
          printContent(packet(displayed)),
        ),
      );
      actions.append(
        button("Remove research record", () => {
          if (
            !window.confirm(
              "Remove this property's research, answers and history?",
            )
          )
            return;
          void (async () => {
            try {
              await api(
                `/api/decision-cases/${encodeURIComponent(listingId)}`,
                "DELETE",
              );
              if (current()) await property(listingId);
            } catch (error) {
              if (current()) status.textContent = errorText(error);
            }
          })();
        }),
      );
      form.append(actions);
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        void submit(true);
      });
      await loadGoal();
    } catch (error) {
      if (current())
        host.replaceChildren(
          node("p", errorText(error)),
          button(
            "Retry decision research",
            () => void property(listingId, preferredHunt),
          ),
        );
    }
  }

  async function hunt(host: HTMLElement, huntId: string): Promise<void> {
    const epoch = generation,
      token = session();
    const current = () =>
      Boolean(
        token &&
        session() === token &&
        generation === epoch &&
        host.isConnected,
      );
    host.replaceChildren(node("p", "Loading Hunt research…"));
    try {
      const data = await api<HuntResearch>(
        `/api/hunts/${encodeURIComponent(huntId)}/research`,
      );
      if (!current()) return;
      host.replaceChildren(node("h3", "Research this Hunt"));
      const status = node("p");
      status.setAttribute("role", "status");
      const form = node("form", "", "decision-form");
      const goal = goalFields(form, data.goal);
      const save = button("Update Hunt research goal", () => {
        if (!form.reportValidity()) return;
        save.disabled = true;
        void (async () => {
          try {
            await api(
              `/api/hunts/${encodeURIComponent(huntId)}/research-goal`,
              "PUT",
              { revision: data.revision, goal: goal.read() },
            );
            if (current()) await hunt(host, huntId);
          } catch (error) {
            if (current()) status.textContent = errorText(error);
          } finally {
            save.disabled = false;
          }
        })();
      });
      form.append(save);
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        save.click();
      });
      const setup = section("Set the goal for this Hunt", !data.cases.length);
      setup.append(form);
      host.append(setup, status);
      if (!data.cases.length) {
        host.append(
          node(
            "p",
            "Open a property, choose this Hunt in Research your decision, and record your research to compare candidates and prepare shared questions.",
          ),
        );
        return;
      }
      const cases = node("div", "", "decision-cases");
      for (const item of data.cases) {
        const card = node("article", "", "source-card");
        card.append(
          node("h4", item.property.title),
          node(
            "p",
            `Remaining allowance: ${money(item.decision.costs.allowance)}`,
          ),
          node("p", item.decision.summary),
        );
        if (item.input.pause_reason)
          card.append(
            node(
              "p",
              `Paused for ${item.input.pause_reason}. ${item.decision.pause_condition_met === true ? "Condition now met — review this candidate." : "Condition still needs review."}`,
            ),
          );
        if (item.history[0]) card.append(node("p", item.history[0].message));
        card.append(
          button("Open decision research", () => {
            void (async () => {
              await openProperty(item.listing_id);
              if (current()) {
                await property(item.listing_id, huntId);
                document.getElementById("decision-workspace")?.scrollIntoView();
              }
            })().catch((error) => {
              if (current()) status.textContent = errorText(error);
            });
          }),
        );
        cases.append(card);
      }
      host.append(cases);
      if (data.cases.length > 1) {
        const compare = section("Compare two properties", true);
        const options = data.cases.map(
          (item) => [item.listing_id, item.property.title] as [string, string],
        );
        const a = select(compare, "Property A", options, options[0]![0]);
        const b = select(compare, "Property B", options, options[1]![0]);
        const output = node("div");
        const run = button("Explain the trade-off", () => {
          run.disabled = true;
          void (async () => {
            try {
              const result = await api<{
                a: Case;
                b: Case;
                same_goal: boolean;
                explanation: string;
                range_result: string | null;
                limitation: string;
              }>(
                `/api/hunts/${encodeURIComponent(huntId)}/research-compare`,
                "POST",
                { listing_ids: [a.value, b.value] },
              );
              if (!current()) return;
              output.replaceChildren(
                node(
                  "p",
                  `A: ${result.a.property.title}. B: ${result.b.property.title}.`,
                ),
                node("p", result.explanation),
                node(
                  "p",
                  result.range_result ??
                    "Complete both cost ranges to compare their overlap.",
                ),
                node("p", result.limitation),
              );
              for (const [label, item] of [
                ["A", result.a],
                ["B", result.b],
              ] as const)
                output.append(
                  node(
                    "p",
                    `${label} unresolved requirements: ${item.decision.blockers.join("; ") || "none recorded"}`,
                  ),
                );
            } catch (error) {
              if (current()) output.textContent = errorText(error);
            } finally {
              run.disabled = false;
            }
          })();
        });
        compare.append(run, output);
        host.append(compare);
      }
      const brief = section("Shared research questions");
      const content = briefContent(data.brief);
      brief.append(
        button("Print shared research brief", () =>
          printContent(briefContent(data.brief)),
        ),
        button("Copy shared research brief", () => {
          void navigator.clipboard
            .writeText(content.innerText)
            .then(() => {
              if (current())
                status.textContent =
                  "Research brief copied. No messages were sent.";
            })
            .catch(() => {
              if (current())
                status.textContent =
                  "Copy unavailable. Use Print shared research brief.";
            });
        }),
        content,
      );
      host.append(brief);
    } catch (error) {
      if (current())
        host.replaceChildren(
          node("p", errorText(error)),
          button("Retry Hunt research", () => void hunt(host, huntId)),
        );
    }
  }
  return { clear, property, hunt };
}
