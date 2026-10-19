/** Main-screen source choices share the server's source/state/category definitions. */
import { element } from "./dom";

export type SourceOption = {
  id: string;
  name: string;
  states: string[];
  categories: string[];
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
