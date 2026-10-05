# Private Seller Listings integration

Status: implementation candidate, not deployed. No collector or scheduled job is
running. No upstream website-specific scraper has been verified. This change
provides the normalized ingestion side and public collection, not a working
website extraction adapter. The live target denied the inspection browser.

## User-facing behavior

A new Private Seller Listings category and source filter accepts listings in all
50 states. This is private-market inventory, including owners, agents and brokers;
it is not an assertion that every listing is for sale by owner. Individual listing
details preserve representative name, brokerage, public business phone and the
original seller/agent listing link. Unknown seller type remains unknown.

Acquisition URL, provider key, external identifier and access reference live only
in `lw2_private_listing_origins`. They are never joined into public API responses.
Public IDs are opaque hashes. Feed endpoints are configured through the job's
private environment, not committed source. Required attribution remains visible.
A factual address/area heading and existing default thumbnail are used. Marketing
descriptions and upstream photos are not imported by this candidate.

## Scheduling and feed contract

`render.private-listings.yaml` describes an unprovisioned 12-hour job:
`0 0,12 * * *` (00:00 and 12:00 UTC; local display changes with daylight saving).
The command is `python -m landwolf.cli sync-private`. This scheduled process is
separate from the existing six-hour public-agency refresh. No ChatGPT reminder
is used to claim an ingestion job is running.

Supply `LANDWOLF_PRIVATE_FEEDS` as a JSON array in the job environment. At most 50
configurations are accepted. Each contains:

- `key`: internal stable provider key, lowercase letters/digits/underscores.
- `url`: normalized JSON feed endpoint, HTTPS, no credentials or custom port.
- `feed_hosts`: exact reviewed acquisition/feed domains.
- `original_hosts`: reviewed seller/agent domains, distinct from acquisition domains.
- `access_reference`: internal record of the access basis; never public.
- `required_attribution`: optional public attribution required by the provider.

Each page contains `snapshot_id`, `total`, `complete`, `next_url`, `listings`.
`total` and `snapshot_id` must remain constant across a complete snapshot.
`complete` is true only for the terminal page; then `next_url` must be null.
Each listing contains required `external_id`, `acquisition_url`,
`original_listing_url`, and two-letter `state`. Optional fields are `county`,
`address`, `acres`, `asking_price`, `parcel_number`, paired `latitude`/`longitude`,
`seller_type` (owner/agent/broker/unknown), `listing_agent`, `listing_brokerage`,
`seller_phone`, `source_effective_date`, and `active`.

Only published business contact details belong in the feed. Coordinates must be
source-reported; never infer a parcel point from a locality. Asking prices remain
asking prices, not appraisals. Original links must omit query/tracking parameters.
A record without a verified direct original link must be resolved before import;
do not substitute the acquisition portal link or invent a destination.

Limits: 1,000 listings and 8 MiB per page, 10,000 pages, 1,000,000 records per
snapshot, 30-second requests, and a 30-minute feed deadline. Pages are paced.
Redirects, 401/403 responses, unbounded rate limits, malformed pages, changing snapshots, duplicate IDs,
and repeated pagination stop the run. Transient 5xx failures receive up to two
retries with backoff; 429 is retried only with an explicit numeric Retry-After
no longer than 60 seconds. Randomized pacing spreads request load; one HTTP client
retains the session. No bypass, rotating proxy or CAPTCHA
handling is implemented. Actual nationwide throughput has not been established.

Each provider snapshot commits atomically. Failures preserve that provider's
last complete inventory. Other providers can succeed independently; overall
status cannot be marked fully refreshed after a partial run. A database lock
serializes import processes. Memory use is bounded by a page rather than total
inventory; bulk writes replace the old 5,000-record snapshot limit for this path.
Abrupt removals are rejected for investigation; there is no automatic override.
Repeated provider/external IDs update the same listing. Cross-provider entity
resolution is not implemented: records are not merged on guessed address/acreage.
A failed run restarts that provider's snapshot; resumable crawl checkpoints are
not implemented in this candidate.

## Database and release sequence

Schema v9 adds one internal provenance table. No existing account, entitlement,
payment, pilot or listing tables are dropped beyond the existing retired-Saved
migration behavior. No Stripe implementation changes are included.

Before deployment: complete a site-specific collector or connect a normalized
feed; establish actual pagination/full inventory coverage; test retrieval and
seller-link resolution; run all release gates and a staging import against its
separate database. The code does not infer rights from a site's public visibility.

Promote a versioned compatible web build before migrating/provisioning the cron
against the same production database. The job must never migrate a live v8 web
service's database to v9 while that older code is serving. Cron configuration
alone is not evidence that any job exists or data has been imported. Observe
first-run completion, exact row counts, source status and a second scheduled run.

Rollback is a v9-compatible fix-forward build or a coordinated tested backup
restore. Do not run a v8 application against the v9 schema. Keep the provenance
table internal under existing database access controls; no public read route is
provided. Removing a feed configuration does not delete its prior inventory;
explicit retirement is a separate operation.
