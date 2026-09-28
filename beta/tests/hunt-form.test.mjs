import assert from "node:assert/strict";
import test from "node:test";
import {
  acreagePresets,
  acreageRange,
  huntName,
  matchLabel,
} from "../web/hunt-form.ts";

test("acreage presets and exact custom boundaries retain their meaning", () => {
  for (const [key, range] of Object.entries(acreagePresets))
    assert.deepEqual(acreageRange(key, "", ""), range);
  assert.deepEqual(acreageRange("custom", "10", "10"), [10, 10]);
  assert.deepEqual(
    acreageRange("custom", "0.0001", "10000000"),
    [0.0001, 10000000],
  );
});

test("invalid acreage cannot silently become a search", () => {
  for (const [low, high] of [
    ["", "50"],
    ["5", ""],
    ["20", "5"],
    ["0", "5"],
    ["-1", "5"],
    ["NaN", "5"],
    ["5", "Infinity"],
    ["5", "10000001"],
  ])
    assert.throws(
      () => acreageRange("custom", low, high),
      /valid acreage range/,
    );
  assert.throws(
    () => acreageRange("unknown", "5", "50"),
    /valid acreage range/,
  );
});

test("automatic names and match labels avoid price or value claims", () => {
  assert.equal(huntName("TX", 5, 50, false), "TX · 5–50 acres");
  assert.equal(
    huntName("Anywhere", 500, 10000000, true),
    "Anywhere · 500+ acres · Auctions",
  );
  assert.ok(huntName("A".repeat(100), 5, 50, false).length <= 80);
  assert.equal(matchLabel(null), "Needs review");
  assert.equal(matchLabel(79), "Matches your filters");
  assert.equal(matchLabel(80), "Strong match");
});
