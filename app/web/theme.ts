import {
  APPEARANCE_KEY,
  appearancePreference,
  applyAppearance,
  savedAppearance,
} from "./theme-preference";

export function setupAppearance(): void {
  const select = document.querySelector<HTMLSelectElement>("#appearance");
  if (!select) return;
  let preference = savedAppearance();
  const render = () => {
    select.value = preference;
    applyAppearance(preference);
  };
  render();
  select.addEventListener("change", () => {
    preference = appearancePreference(select.value);
    try {
      localStorage.setItem(APPEARANCE_KEY, preference);
    } catch {
      // Storage can be blocked; the current page still changes appearance.
    }
    render();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
  window.addEventListener("storage", (event) => {
    if (event.key === APPEARANCE_KEY || event.key === null) {
      preference = savedAppearance();
      render();
    }
  });
}
