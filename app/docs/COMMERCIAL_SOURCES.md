# Publisher searches and optional licensed imports

The main screen offers Zillow and Compass Texas land searches and a Craigslist
choice for every US state. State, sale category and source choices stay linked.
Selecting a single-state source selects its state; switching states while
Craigslist is selected selects that state's source. Open **Browse selected
publisher** to see all reviewed regional search links for that state. Craigslist's
public directory maps 50 states to 412 unique regional markets (reviewed October
19, 2026 UTC). This is search coverage, not a complete inventory of land for sale.

Price, acreage and other numeric LandWolf filters apply to imported records.
Apply them separately on the publisher site: links do not transfer numeric filters
or import results. Changing filters makes no publisher requests. Reset and
sign-out clear the publisher disclosure and its links.

## Default operation and provider agreements

**Zillow, Craigslist and Compass automatic imports are disabled by default.**
Existing government feeds continue unchanged. No provider agreements were supplied.
Read-only technical trials established that some public pages could be parsed;
they did not establish collection/display rights or continuing availability.

The actual publisher terms have material restrictions:

- [Zillow terms](https://www.zillow.com/corporate/terms-of-use/) restrict automated
  queries, scraping and redisplay except as authorized.
- [Craigslist terms](https://www.craigslist.org/about/terms.of.use/en) require a
  separate agreement for software interacting with the service and restrict
  automated collection and redisplay.
- [Compass terms](https://www.compass.com/legal/terms-of-service/) restrict automated
  collection and commercial reuse absent permission.

Before activating a collector, obtain an agreement covering its collection and
LandWolf display. Configure only covered IDs through
`LANDWOLF_LICENSED_LISTING_SOURCES`, a JSON array such as `["zillow_tx"]`.
Recognized IDs are `zillow_tx`, `compass_tx`, and `craigslist_<state abbreviation>`.
Unknown or duplicate IDs reject configuration. This records an operator's scope
decision; it does not create a license or override terms. The setting is empty in
this release; no hosted environment change is required.

The live checker exits 2 without constructing an HTTP client when no agreement
scope is configured. For covered sources only, run:

```sh
.venv/bin/python scripts/check_commercial_sources.py --sample-regions
.venv/bin/python scripts/check_commercial_sources.py
```

The sample flag checks one region per configured state, not every regional market.
The CLI sync runs original government feeds plus explicitly configured licensed
sources. No Apify account, paid service or new infrastructure is created.

## Adapter contracts when licensed

- Zillow: first Texas land page; only Texas LOT/LAND records marked FOR_SALE.
  Published price, lot area, coordinates and original links retain provenance;
  square feet convert to acres with a calculated label.
- Craigslist: first land-keyword page of each reviewed regional market in the
  selected state. Structured publisher addresses must unambiguously match the
  state. Cross-border records and duplicate canonical URLs are excluded. Common
  house, rental and financing titles are excluded conservatively. Owner/broker
  identity, availability and vacant-land classification remain unverified.
- Compass: first Texas land-filtered page; active USD offers match Texas address
  records by canonical URL. Generic residential labels can occur; land status
  remains unverified. Unpublished acreage remains unknown.

These are partial samples. Zero supported records does not prove no land is
available. Published pins are not surveyed boundaries; asking prices are not
appraisals or comparable sales. No approximate cross-provider deduplication is
performed. Missing numbers stay unknown and do not pass numeric filters. Hunts
put publisher listings in Needs review. No photos, seller contacts or full listing
descriptions are copied.

Fixed HTTPS hosts/paths, robots checks, response limits, bounded timeouts,
sequential paced regional requests and atomic state snapshots remain enforced.
A failed region preserves last-good data with unavailable/stale diagnostics.
Robots permission and public reachability do not establish reuse rights.

Authenticated `GET /api/source-options` exposes IDs, names, states, categories,
fixed external URLs and whether import is enabled. It exposes no owner diagnostics,
operational counts/history, accounts or CRM data. Billing, CSRF, research ownership
and existing entitlements remain enforced. No migration or account reset is needed.

## Verification and recovery

Synthetic tests cover all 50 mappings, state isolation, malformed data, unknown
values, duplicate/URL rejection, robots failures, snapshots, authentication,
search/details, Hunt review, default-disabled configuration and no-request live
checks. Phone/desktop Chromium and WebKit cover keyboard disclosure, regional
links, state switching, reset and Light/Dark/Auto screenshots. Licensed-mode tests
use isolated synthetic fixtures; they do not represent provider agreements.

The new runtime reads v0.16 records. The old runtime cannot read the seller
category/status after future licensed ingestion or saved research. Recovery must
retain v0.17 contracts while disabling/reverting collectors; do not delete owned
research or blindly downgrade. Commands and observed results are recorded in
[VERIFICATION.md](VERIFICATION.md); deployment identities enter the release ledger
only after observed deployment.
