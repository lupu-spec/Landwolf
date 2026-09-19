import assert from "node:assert/strict";
import test from "node:test";
import {
  bidRange,
  sourceAddress,
  similarFilters,
} from "../web/property-context.ts";

test("bid anchor uses -5% / +20%, with editable percentages and cents", () => {
  assert.deepEqual(bidRange(100000), {
    low: 95000,
    likely: 100000,
    high: 120000,
  });
  assert.deepEqual(bidRange(100000, 10, 30), {
    low: 90000,
    likely: 100000,
    high: 130000,
  });
  assert.deepEqual(bidRange(101.25), {
    low: 96.19,
    likely: 101.25,
    high: 121.5,
  });
  assert.deepEqual(bidRange(100, 0, 0), { low: 100, likely: 100, high: 100 });
});
test("invalid or unrepresentable ranges do not yield plausible defaults", () => {
  for (const bid of [NaN, Infinity, -1, 0, 0.001, 1e9, 1e9 + 1])
    assert.equal(bidRange(bid), null);
  for (const down of [NaN, Infinity, -1, 100])
    assert.equal(bidRange(100, down), null);
  for (const up of [NaN, Infinity, -1, 1001])
    assert.equal(bidRange(100, 5, up), null);
});
test("default ranges are finite, positive, ordered and proportional across bid sizes", () => {
  for (const bid of [0.01, 1, 1.03, 1000, 100000, 800000000]) {
    const range = bidRange(bid);
    assert.ok(
      range &&
        range.low > 0 &&
        range.low <= range.likely &&
        range.likely <= range.high,
    );
    assert.ok(Math.abs(range.low - bid * 0.95) <= 0.0051);
    assert.ok(Math.abs(range.high - bid * 1.2) <= 0.0051);
  }
});
test("only source-identified full addresses prefill public research", () => {
  const record = {
    source: "usda_resales",
    state: "TX",
    location_description: "123 Fixture St, Test City, TX 75000",
  };
  assert.equal(sourceAddress(record), record.location_description);
  assert.equal(
    sourceAddress({ ...record, source: "irs_auctions" }),
    record.location_description,
  );
  for (const source of ["tx_glo_public", "ak_dnr", "unknown"])
    assert.equal(sourceAddress({ ...record, source }), "");
  for (const location_description of [
    null,
    "tract 123",
    "123 county parcel",
    "123 Test St, City, CA 75000",
    "x".repeat(301),
  ])
    assert.equal(sourceAddress({ ...record, location_description }), "");
});
test("similar filters carry county, state, category and minimum area, not stale price/source", () => {
  assert.deepEqual(
    similarFilters({
      state: "TX",
      county: "Test",
      category: "tax_sale",
      acres: 10.123,
    }),
    {
      state: "TX",
      location: "Test",
      category: "tax_sale",
      min_acres: "10.12",
      max_price: "",
      source: "",
    },
  );
  const unknown = similarFilters({
    state: "AK",
    county: null,
    category: "government_land",
    acres: null,
  });
  assert.equal(unknown.location, "");
  assert.equal(unknown.min_acres, "");
});
