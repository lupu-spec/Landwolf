/** Appearance is a device preference, never account or billing state. */
export type Appearance = "system" | "light" | "dark";
export const APPEARANCE_KEY = "landwolf.appearance";

export function appearancePreference(value: unknown): Appearance {
  return value === "light" || value === "dark" ? value : "system";
}

export function resolvedTheme(
  preference: Appearance,
  systemDark: boolean,
): "light" | "dark" {
  return preference === "system" ? (systemDark ? "dark" : "light") : preference;
}

export function savedAppearance(): Appearance {
  try {
    return appearancePreference(localStorage.getItem(APPEARANCE_KEY));
  } catch {
    return "system";
  }
}

export function applyAppearance(preference: Appearance): void {
  const theme = resolvedTheme(
    preference,
    matchMedia("(prefers-color-scheme: dark)").matches,
  );
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", theme === "dark" ? "#17181d" : "#e8e9ee");
}
