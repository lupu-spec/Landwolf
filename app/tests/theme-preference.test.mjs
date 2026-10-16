import test from "node:test";
import assert from "node:assert/strict";
import {
  appearancePreference,
  resolvedTheme,
} from "../web/theme-preference.ts";

test("only supported appearance values survive persisted input", () => {
  for (const value of [null, undefined, {}, 1, "", "DARK", "sepia", "system"])
    assert.equal(appearancePreference(value), "system");
  assert.equal(appearancePreference("light"), "light");
  assert.equal(appearancePreference("dark"), "dark");
});

test("explicit appearance wins and automatic appearance follows either system boundary", () => {
  for (const systemDark of [false, true]) {
    assert.equal(resolvedTheme("light", systemDark), "light");
    assert.equal(resolvedTheme("dark", systemDark), "dark");
    assert.equal(
      resolvedTheme("system", systemDark),
      systemDark ? "dark" : "light",
    );
  }
});
