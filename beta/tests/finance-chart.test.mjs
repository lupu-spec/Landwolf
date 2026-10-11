import test from "node:test";
import assert from "node:assert/strict";
import { chartBounds } from "../web/finance-chart.ts";

test("finance charts include zero and negative cash without clipping", () => {
  assert.deepEqual(chartBounds([{ values: [-3200, 2900, null] }]), {
    min: -3200,
    max: 2900,
  });
  assert.deepEqual(chartBounds([{ values: [2900] }]), { min: 0, max: 2900 });
});

test("unknown and nonfinite finance values never fabricate chart receipts", () => {
  for (const values of [[], [null], [0, 0], [NaN, Infinity, -Infinity]])
    assert.deepEqual(chartBounds([{ values }]), { min: 0, max: 1 });
});
