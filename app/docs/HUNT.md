# LandWolf Hunt

Hunt is a deterministic filter and ranking tool for the app's connected public listing catalog. It is available only to signed-in accounts. It makes no model calls or paid enrichment requests. This implementation is not an appraisal, investment recommendation, or complete national inventory.

## Customer flow

Open Hunt, choose a state (or anywhere in connected inventory), an acreage band and optionally a budget. The app supplies a name automatically. More options exposes a custom acreage range, name, auction opening-bid mode, county, price per acre and coordinate radius for precise searches and editing existing Hunts. A radius cannot be combined with a state or county. The budget applies to the published asking price in fixed mode or opening bid in auction mode; neither is a total purchase cost. Save up to three active Hunts. View matches and records needing review; open the original property detail, edit criteria, pause/resume, or delete. Editing criteria increments a revision and establishes a new baseline. The location picker uses states rather than city geocoding; it does not infer parcel locations.

Quick starters offer 5–50 acres, larger tracts or auctions without adding required inputs. Selecting Custom range reveals its inputs automatically. Saving opens results; failed saves keep the inputs for retry, and Cancel edit leaves the stored Hunt unchanged. Auction mode labels the budget as an opening-bid ceiling and disables asking-price-per-acre filtering.

The API also supports multiple states and an optional preferred acreage band. The form preserves existing multiple-state criteria until the user selects a different state, and preserves a preferred band while the allowed acreage range is unchanged. New simple searches use the full allowed acreage range as their preference. All 50 state codes are accepted; connected inventory varies by state. Individual result cards show the title, acreage, published price type, location and a source image where available. Missing, disallowed or failed image URLs display the LandWolf default image. Confirmed matches do not repeat fit labels or criteria reasons; records needing review show the specific missing facts.

## Ranking and evidence

Hard requirements have pass, fail, or unknown outcomes. A known failure excludes the record. Missing required facts, price basis, source confirmation, or location put it in Needs review with no score. Fixed-price scores use enabled asking price (25), asking price per acre (35), acreage preference (25), and radius proximity (15), with weights normalized once for the criteria. Auction fit uses acreage (60) and radius (40); opening bid is a filter only. The internal fit score is rounded half-up and is not market value.

The implementation accepts government land catalog classifications as land opportunities, but unimproved status is not independently verified. Legal access, flood overlap, parcel boundaries, title, fees, and seller eligibility require separate research. Displayed listings retain their source price meaning. Freshness requires a successful source confirmation within twelve hours and no unavailable status. Catalog coverage is partial, including in states where a nationwide source has no current records.

## Change checks and limits

Creation captures an initial baseline without a new-match event. Opening a Hunt re-evaluates up to 20,000 active catalog records against the current database snapshot and records new high-fit matches and qualifying published asking-price drops for in-app history. Repeating the check without changed facts does not create another event. Pausing suppresses evaluation. This implementation has no scheduled Hunt reconciliation, email digest, or push alerts: users must open a Hunt to check changes. It does not import new records or refresh publishers on its own; the existing catalog refresh remains separate.

Results are currently limited by the 20,000-candidate guard and the interface displays the first 50 per group. A larger catalog returns an explicit error rather than a misleading partial ranking. Source licensing and inventory completeness need separate review before public claims of broad coverage. The implementation does not claim parcel outlines or offer road/flood filters. Email is disabled in staging until sender, opt-in, outbox, and delivery checks exist.

## API

`GET/POST /api/hunts`, `PATCH/DELETE /api/hunts/{id}`, `GET /api/hunts/{id}/matches`, and `GET /api/hunts/{id}/events` use existing session authentication; mutations require origin and CSRF checks. The schema-v5 migration adds Hunt, match, and event tables to the rebuilt `lw2_` namespace and preserves existing accounts and listings. Hunt is included in production. New Hunts, matches and events require a current billing entitlement; existing saved-Hunt management remains available after access expires.
