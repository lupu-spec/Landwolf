import test from "node:test";
import assert from "node:assert/strict";
import { sourceHealth, sourceTimestamp } from "../web/source-health.ts";
const now = 1_800_000_000;
const hour = 3600;
test("successful-import freshness includes exact 24 and 36 hour boundaries", () => {
  for (const [age, color] of [
    [0, "green"],
    [24 * hour - 1, "green"],
    [24 * hour, "green"],
    [24 * hour + 1, "yellow"],
    [36 * hour - 1, "yellow"],
    [36 * hour, "red"],
    [100 * hour, "red"],
  ])
    assert.equal(sourceHealth(true, now - age, now).color, color);
});
test("missing, malformed and future timestamps cannot advertise a healthy import", () => {
  for (const timestamp of [null, NaN, Infinity, -1, 0, now + 1])
    assert.equal(sourceHealth(true, timestamp, now).color, "red");
  assert.equal(sourceHealth(true, now, NaN).color, "red");
});
test("directory entries never claim an import, regardless of timestamp", () => {
  for (const timestamp of [null, now, now - 40 * hour])
    assert.equal(sourceHealth(false, timestamp, now).color, "neutral");
});
test("timestamp presentation contains a date, year and time, with explicit missing and invalid states", () => {
  assert.equal(sourceTimestamp(null), "Not yet retrieved");
  for (const value of [NaN, Infinity, -1, 0, 1e99])
    assert.equal(sourceTimestamp(value), "Invalid timestamp");
  const shown = sourceTimestamp(now);
  assert.match(shown, /2027/);
  assert.match(shown, /\d{1,2}:\d{2}/);
});
