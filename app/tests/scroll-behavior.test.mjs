import test from "node:test";
import assert from "node:assert/strict";
import { scrollBehavior } from "../web/dom.ts";

test("scrolling follows live reduced-motion changes", (t) => {
  let reduced = true;
  const previous = globalThis.window;
  t.after(() => {
    if (previous === undefined) delete globalThis.window;
    else globalThis.window = previous;
  });
  globalThis.window = {
    matchMedia(query) {
      assert.equal(query, "(prefers-reduced-motion: reduce)");
      return { matches: reduced };
    },
  };
  assert.equal(scrollBehavior(), "instant");
  reduced = false;
  assert.equal(scrollBehavior(), "smooth");
  reduced = true;
  assert.equal(scrollBehavior(), "instant");
});
