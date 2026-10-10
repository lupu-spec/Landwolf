import test from "node:test";
import assert from "node:assert/strict";
import { cycleOffset, dockScale } from "../web/dock-motion.ts";

test("dock magnification is symmetric, bounded and strongest beneath the pointer", () => {
  assert.equal(dockScale(0), 1.42);
  assert.equal(dockScale(115), 1);
  for (let distance = 0; distance <= 500; distance++) {
    assert.equal(dockScale(distance), dockScale(-distance));
    assert.ok(dockScale(distance) >= 1 && dockScale(distance) <= 1.42);
    assert.ok(dockScale(distance) >= dockScale(distance + 1));
  }
  for (const invalid of [NaN, Infinity, -Infinity])
    assert.equal(dockScale(invalid), 1);
});
test("cycling wraps at both ends and never creates an invalid scroll target", () => {
  assert.equal(cycleOffset(0, 200, 1), 76);
  assert.equal(cycleOffset(0, 200, -1), 200);
  assert.equal(cycleOffset(200, 200, 1), 0);
  assert.equal(cycleOffset(200, 200, -1), 124);
  assert.equal(cycleOffset(50, 200, 0), 50);
  assert.equal(cycleOffset(0, 0, 1), 0);
  for (let maximum = 0; maximum < 500; maximum += 7)
    for (const current of [-100, 0, 3, maximum / 2, maximum, 900])
      for (const direction of [-1, 0, 1]) {
        const target = cycleOffset(current, maximum, direction);
        assert.ok(Number.isFinite(target) && target >= 0 && target <= maximum);
      }
  for (const invalid of [NaN, Infinity, -Infinity]) {
    assert.equal(cycleOffset(invalid, 100, 1), 0);
    assert.equal(cycleOffset(0, invalid, 1), 0);
    assert.equal(cycleOffset(0, 100, invalid), 0);
  }
});
