import test from "node:test";
import assert from "node:assert/strict";
import { viewportInsets } from "../web/mobile-keyboard.ts";

test("keyboard viewport accounts for iOS panning and Android layout resize", () => {
  assert.deepEqual(viewportInsets(950, 420, 60, 1), {
    height: 420,
    top: 60,
    bottom: 470,
  });
  assert.deepEqual(viewportInsets(420, 420, 0, 1), {
    height: 420,
    top: 0,
    bottom: 0,
  });
  assert.equal(viewportInsets(950, 950, 0, 1).bottom, 0);
  assert.equal(viewportInsets(950, 950, 60, 1).bottom, 0);
});
test("invalid geometry fails safely and pinch zoom is never treated as a keyboard", () => {
  for (const index of [0, 1, 2, 3])
    for (const invalid of [NaN, Infinity, -Infinity]) {
      const values = [950, 420, 0, 1];
      values[index] = invalid;
      assert.equal(viewportInsets(...values), null);
    }
  for (const values of [
    [0, 420, 0, 1],
    [950, 0, 0, 1],
    [950, 420, -1, 1],
    [950, 420, 0, 2],
    [950, 420, 0, 0.5],
  ])
    assert.equal(viewportInsets(...values), null);
});
