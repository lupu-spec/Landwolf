// Blocking external bundle runs before styles: no inline script/CSP exception.
import { applyAppearance, savedAppearance } from "./theme-preference";
applyAppearance(savedAppearance());
