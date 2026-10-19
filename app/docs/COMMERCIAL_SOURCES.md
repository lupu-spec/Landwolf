# Seller and broker listings

The source adapters add Zillow and Compass Texas land-search pages and 50
state-specific Craigslist sources to the existing authenticated catalog. The main
screen uses the same source definitions as the backend. Choose a state and
**Seller & broker listings**, then a source; results, map points, price/acreage
filters, property details and research handoffs use the existing flow. Selecting
a single-state source selects its state. Switching states while Craigslist is
selected switches to that state's source. Reset restores all matching sources.

## Scope and interpretation

- Zillow: first Texas land-search page. Only publisher-tagged LOT/LAND records
  explicitly marked FOR_SALE in Texas qualify. Asking price, published lot area,
  coordinates and original links are retained. Square feet convert to acres with
  a calculated label. Asking prices are not appraisals or comparable sales.
- Craigslist: the public regional directory retrieved October 19, 2026 UTC maps
  all 50 states to 412 unique regional markets. Each state refresh samples the
  first land-keyword result page of every listed regional market. Locations must
  unambiguously match a structured publisher address in that state. Cross-border
  results are excluded; duplicate canonical URLs within a state are collapsed.
  Common house, rental and financing-promotion titles are excluded conservatively.
  Keywords do not establish vacant-land status or owner/broker identity.
- Compass: first Texas land-filtered page; active USD offers must match a Texas
  address/location record by canonical URL. Generic residential schema labels can
  still occur in this land search. Vacant-land classification remains unverified;
  unpublished acreage stays unknown.

These are sampled pages, not complete inventories or proof of statewide/nationwide
availability. Source health describes retrieval. Zero supported records is not
proof that no land is offered in a state. State matching follows publisher
addresses, not a city search's assumed boundaries. Published map pins are not
parcel outlines. No cross-provider parcel deduplication uses approximate points.

New records use **Publisher listing — verify availability** and carry visible
limitations. Hunts put seller/broker records in Needs review rather than treating
unverified availability/classification as established eligibility. Property research
uses supplied source coordinates; scenario assumptions and user overrides retain
their existing behavior. Missing prices/acreage remain unknown and are excluded
when a corresponding numeric filter is applied.

## Retrieval and security

All requests use fixed, reviewed HTTPS hosts and page paths; no private endpoints,
credentials, proxies, browser evasion, arbitrary user URLs or redirects are used.
Robots policy is checked before each source refresh; blocks and unexpected content
fail closed. Requests stay within existing timeouts and eight-MB response limits.
Craigslist region requests are sequential, at least one second apart, and respect
supported crawl delays. Each state has its own bounded refresh and atomic snapshot.
Existing last-good data and quarantine gates remain in effect if any region fails.
The scheduler refreshes the original government sources before commercial sources.
All sources retain the established six-hour refresh cycle after a pass completes.

Only listing facts and original links are imported. No publisher photos, seller
contacts or full listing descriptions are copied; the existing missing-photo image
is used. Public reachability and robots policy do not establish redistribution
rights. Publisher terms must be reviewed before expanding reuse, image delivery or
bulk redistribution. No paid service or Apify account is required by these adapters.

`GET /api/source-options` requires authentication and returns only static source
IDs, names, states and categories. Owner-only coverage diagnostics, operational
counts/history, customer/CRM data, billing entitlements, CSRF and research access
boundaries retain their existing checks. No migration or database reset is needed.

## Verification

Synthetic fixtures cover all 50 state mappings, identity/state isolation, unknown
fields, conversion, duplicate rejection, invalid coordinates/numbers, malicious
URLs, robots/access failures, last-good snapshots, search/detail/map integration,
Hunt review and location handoff. Browser tests cover phone/desktop Chromium and
WebKit, linked state/source controls, original links, reset and Light/Dark/Auto.

Explicit read-only live verification:

```sh
.venv/bin/python scripts/check_commercial_sources.py --sample-regions
.venv/bin/python scripts/check_commercial_sources.py
LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-v17-source-verification.db .venv/bin/python -m landwolf.cli sync
```

The sample flag checks one region per state and is never represented as a full
regional test. The normal runtime refresh uses the complete reviewed regional
roster. Live checker output contains aggregate counts/status only, never seller
contacts or complete records. Final observed results, failures and deployment
identities are recorded in [VERIFICATION.md](VERIFICATION.md) and the release ledger.
