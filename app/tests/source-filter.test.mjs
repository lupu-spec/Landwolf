import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({
  entryPoints: ["web/source-filter.ts"],
  bundle: true,
  platform: "node",
  format: "esm",
  write: false,
});
const { matchingSources } = await import(
  `data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`
);
const options = [
  { id: "craigslist_tx", states: ["TX"], categories: ["seller_listing"] },
  { id: "craigslist_ca", states: ["CA"], categories: ["seller_listing"] },
  { id: "tx_glo_public", states: ["TX"], categories: ["government_land"] },
];

test("state and sale category intersect without silently mixing another state", () => {
  assert.deepEqual(
    matchingSources(options, "TX", "seller_listing").map((row) => row.id),
    ["craigslist_tx"],
  );
  assert.deepEqual(matchingSources(options, "CA", "government_land"), []);
  assert.equal(matchingSources(options, "US", "seller_listing").length, 2);
  assert.equal(matchingSources(options, "US", "all").length, 3);
  assert.equal(options.length, 3);
});
