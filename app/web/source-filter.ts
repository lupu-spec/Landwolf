/** Main-screen source choices share the server's source/state/category definitions. */
import { byId, element } from "./dom";
import { sourceLink } from "./source-links";

export type SourceOption = {
  id: string;
  name: string;
  states: string[];
  categories: string[];
  external_searches: string[];
  import_enabled: boolean;
};

export function matchingSources(
  options: SourceOption[],
  state: string,
  category: string,
): SourceOption[] {
  return options.filter(
    (option) =>
      (state === "US" || option.states.includes(state)) &&
      (category === "all" || option.categories.includes(category)),
  );
}

export function setupSourceFilter(
  state: HTMLSelectElement,
  category: HTMLSelectElement,
  source: HTMLSelectElement,
) {
  let options: SourceOption[] = [];
  function update(remapState = false): void {
    let previous = source.value;
    if (
      remapState &&
      previous.startsWith("craigslist_") &&
      state.value !== "US"
    ) {
      previous = `craigslist_${state.value.toLowerCase()}`;
    }
    const choices = matchingSources(options, state.value, category.value);
    const all = element("option", "", "All matching sources");
    all.value = "";
    source.replaceChildren(
      all,
      ...choices.map((choice) => {
        const option = element("option", "", choice.name);
        option.value = choice.id;
        return option;
      }),
    );
    source.value = choices.some((choice) => choice.id === previous)
      ? previous
      : "";
    const selected = choices.find((choice) => choice.id === source.value);
    const links = selected?.external_searches ?? [];
    const panel = byId<HTMLDetailsElement>("publisher-searches");
    panel.hidden = links.length === 0;
    if (!links.length) panel.open = false;
    byId("publisher-search-note").textContent = selected?.import_enabled
      ? "Open the publisher to confirm details. Apply price and acreage filters on its site."
      : "Search on the publisher’s site. Automatic import is not enabled. Apply price and acreage filters there.";
    byId("publisher-search-links").replaceChildren(
      ...links.map((url) => {
        const row = element("li");
        const region =
          new URL(url).pathname.split("/").filter(Boolean).at(-1) ?? "Search";
        row.append(
          sourceLink(url, `${selected?.name ?? "Publisher"} — ${region}`),
        );
        return row;
      }),
    );
  }
  state.addEventListener("change", () => update(true));
  category.addEventListener("change", () => update());
  source.addEventListener("change", () => {
    const choice = options.find((option) => option.id === source.value);
    if (choice?.states.length === 1) state.value = choice.states[0] ?? "US";
    update();
  });
  return {
    load(value: SourceOption[]): void {
      options = value;
      update();
    },
    update,
    clear(): void {
      options = [];
      update();
    },
  };
}
