# Data sources and graphite interface

Release candidate: v0.14.0. Deployment evidence is recorded separately in RELEASES.md.

Sign in with the configured owner account and choose **Data coverage** in the dock.
The compact list contains **Source name**, **Health**, and **Last updated**. Select
any row, or focus it and press Enter/Space, to expand its details. Select again to
collapse it. State and sale-type filters continue to work. The state table still
opens searches; research-source links and county coverage remain available below.

| Circle | Meaning |
| --- | --- |
| Green | Last successful import was no more than 24 hours ago |
| Yellow | More than 24 hours, but less than 36 hours |
| Red | 36 hours or more; or missing/invalid/future successful-import timestamp |
| Gray | Directory link only; no imported data and no update timestamp |

Exactly 24 hours is green; exactly 36 hours is red. The timestamp includes date,
year, time and the device's time-zone abbreviation. Status uses the device clock.
Colors update once a minute while this view is visible, and when the browser tab
becomes visible again, without closing open rows or requesting another import.
An open page may therefore take up to one minute to cross a color boundary.

**Health here measures import age.** A failed latest attempt does not change the
last successful update or reset its age. A source can have a green circle and a
failed latest attempt. Expand the row to inspect retrieval status, failure reason,
record count, last attempted time, recent runs, reuse limits and the original link.
An empty successful import may also be green: it does not promise available listings.
The six-hour source refresh schedule and server stale/availability warnings are
separate; these colors do not change source scheduling or search eligibility.
A successful import does not prove publisher recency, complete coverage, title,
liens, valuation, sale availability or parcel-boundary accuracy.

No matching sources produces an explicit empty state. Listing data and source
history are retained under the existing server rules. The view remains owner-only;
ordinary accounts cannot retrieve `/api/sources` by changing the visible controls.

The shared interface uses graphite gradients, metallic silver controls, rounded
surfaces and a glass-style navigation dock inspired by the supplied lock screen.
Form/evidence panels remain light for readable text. The original LandWolf logo,
images, map, keyboard controls, investment inputs, Hunts, CRM and billing remain
part of the application. Print views retain white backgrounds and dark text.
Romulus and Remus include these instructions in the owner coverage help topic.
