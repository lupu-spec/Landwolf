# First-login property map repair

Candidate v0.10.2, October 10, 2026 UTC.

## Confirmed cause

A read-only query of the live v0.10.1 production inventory found 92 active,
current-sale search matches, 30 with source coordinates. Default price sorting
put 11 Michigan records and one USDA record without coordinates on the first
12-item page. The browser passed only that page to the map: zero map locations
despite 30 elsewhere in the filtered inventory. No source repair or invented
coordinates is appropriate for this failure.

## Repair

`/api/search` returns a compact, independently bounded map selection using the
identical active-sale and search predicates, before list pagination. The list
retains its 12-item pages and original sorting. Map records include only ID,
tract, price and source coordinates, capped at 1,000 with total and limit metadata.
The map displays the cap when reached, and otherwise shows mapped and unlocated
counts. Records without coordinates remain accessible in the list.

The browser clears old pins during search and frames results after the map has a
visible, nonzero size. A ResizeObserver handles the initial hidden mobile list
layout and later map/split transitions. Pins remain clickable, including grouped
locations. Sign-out clears map records. No migration, billing, access, credential,
dependency, source allowlist, snapshot or quarantine change is included.

Changes: `landwolf/main.py`, `web/app.ts`, map explanatory copy in `web/index.html`
and `web/help-guide.ts`; API/browser/PostgreSQL regressions; five version metadata
files. The regressions reproduce 12 unlocated first-page listings with located
records beyond that page, including Chromium/WebKit at 390, 820 and 1440 pixels,
first registration, fresh login, session reload, pagination and clickable markers.

## Verification status

Final release gates and deployments are pending. Local browser installation
failed because downloaded archives were empty/truncated; hosted CI will supply
the required browser and disposable PostgreSQL/restore checks. The Render SQL
connector cannot access the private database because its external allowlist is
empty; inventory was read through the existing authenticated Render service shell
without changing networking. An initial new test omitted the required JSON body
on logout; it was corrected to the established API contract.
