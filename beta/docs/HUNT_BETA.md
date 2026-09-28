# LandWolf Hunt beta

Hunt is a deterministic filter and ranking tool for the app's connected public listing catalog. It is available only to signed-in accounts. It makes no model calls or paid enrichment requests. This beta is not an appraisal, investment recommendation, or complete national inventory.

## Customer flow

Open Hunt, name a search, choose fixed-price or auction opening-bid mode, and set acreage, geography and optional price limits. The form supports nationwide, one state/county, or a radius from a supplied center coordinate. Save up to three active Hunts. View matches and records needing review; open the original property detail, edit criteria, pause/resume, or delete. Editing criteria increments a revision and establishes a new baseline.

The API also supports multiple states and an optional preferred acreage band, though the first beta form exposes a single state and uses the full allowed acreage range as its preference. All 50 state codes are accepted; connected inventory varies by state.

## Ranking and evidence

Hard requirements have pass, fail, or unknown outcomes. A known failure excludes the record. Missing required facts, price basis, source confirmation, or location put it in Needs review with no score. Fixed-price scores use enabled asking price (25), asking price per acre (35), acreage preference (25), and radius proximity (15), with weights normalized once for the criteria. Auction fit uses acreage (60) and radius (40); opening bid is a filter only. Hunt Fit is rounded half-up and is not market value.

The beta accepts government land catalog classifications as land opportunities, but unimproved status is not independently verified. Legal access, flood overlap, parcel boundaries, title, fees, and seller eligibility require separate research. Displayed listings retain their source price meaning. Freshness requires a successful source confirmation within twelve hours and no unavailable status. Catalog coverage is partial, including in states where a nationwide source has no current records.

## Change checks and limits

Creation captures an initial baseline without a new-match event. Opening a Hunt re-evaluates up to 20,000 active catalog records against the current database snapshot and records new high-fit matches and qualifying published asking-price drops for in-app history. Repeating the check without changed facts does not create another event. Pausing suppresses evaluation. This beta has no scheduled Hunt reconciliation, email digest, or push alerts: users must open a Hunt to check changes. It does not import new records or refresh publishers on its own; the existing catalog refresh remains separate.

Results are currently limited by the 20,000-candidate guard and the interface displays the first 50 per group. A larger catalog returns an explicit error rather than a misleading partial ranking. Source licensing and inventory completeness need separate review before public claims of broad coverage. The beta does not claim parcel outlines or offer road/flood filters. Email is disabled in staging until sender, opt-in, outbox, and delivery checks exist.

## API

`GET/POST /api/hunts`, `PATCH/DELETE /api/hunts/{id}`, `GET /api/hunts/{id}/matches`, and `GET /api/hunts/{id}/events` use existing session authentication; mutations require origin and CSRF checks. The schema-v5 migration adds Hunt, match, and event tables to the rebuilt `lw2_` namespace and preserves existing accounts and listings. Production remains on v0.3.3/schema v4 until a separate promotion is reviewed.
