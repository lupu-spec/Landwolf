# Nationwide source coverage

For connected Census, FEMA, USGS, USDA NRCS and NC parcel reference APIs, see
[FREE_DATA.md](FREE_DATA.md). Reference research is separate from the sale inventory
below. Live MLS and nationwide assessor/deed databases are not connected.

Reviewed on 2026-09-14. This is a source inventory, not certification of completeness,
sale availability, clear title or current value. All property and coverage endpoints
require a signed-in session. Refresh timestamps describe our retrieval, not the
publisher's last update. Source records can refer to the same property more than once.

| Adapter | Primary source | Included | Important limits |
| --- | --- | --- | --- |
| `ar_cosl` | [Arkansas COSL catalog](https://cosl.org/Home/Contents) | Future/current auction catalogs by sale date, across participating counties | Excludes canceled entries, past events, owner names and interested-party columns. The Taxes column is a tax balance, never an asking price or minimum bid. The source catalog retains full legal and environmental restrictions. Online post-auction inventory is separate and not imported. |
| `tx_glo_public` | [Texas GLO public sales](https://www.glo.texas.gov/veterans/land-sale/public) | Complete public-sale tract table and individual details | Only source-published Texas coordinates; source points are not surveyed boundaries. |
| `usda_resales` | [USDA RD/FSA resales](https://www.resales.usda.gov/resales/public/home) | Single-family, multifamily, farm/ranch inventories for all 50 states with published records | Compares result counts with advertised state counts before replacement. Old sale dates are excluded; ambiguous dates are withheld. A Government Bid is distinct from an asking price. FSA's Value/Bid column can be an appraisal, so it does not populate an REO asking price. Source appraisals never prefill the deal model. |
| `us_treasury` | [Treasury upcoming real-property auctions](https://www.treasury.gov/auctions/treasury/rp/realprop.shtml) | Federal forfeiture auction announcements in the 50 states | Excludes explicitly canceled/postponed announcements and past dated events. Coming-soon announcements remain labeled without a confirmed date. Deposit amounts are not prices. Puerto Rico entries are outside this 50-state contract. |
| `irs_auctions` | [IRS auctions](https://www.irsauctions.gov/auction/items) | Real-Estate asset type 8 and Seized sale type 1, through all returned pages | Verifies the filters were applied. These are federal tax-seizure auctions, not county tax-deed or tax-lien certificate sales. Excludes canceled/postponed titles. Minimum bids are identified explicitly. |
| `ak_dnr` | [Alaska DNR available parcels](https://dnr.alaska.gov/mlw/landsales/parcels) and [program dates](https://dnr.alaska.gov/mlw/landsales/) | State DNR parcels with published acreage, price/bid and residency restrictions | Validates auction and bidding-deadline dates against the program page. Bidding closes before the auction event; the earlier deadline governs current search. No subdivision midpoint is substituted for a parcel coordinate. |
| `mi_dnr` | [Michigan DNR BuyNow](https://www.dnr.state.mi.us/landsale) | General-public search results explicitly marked Available | Uses the site's public read-only search form. Pending bid openings, pending sales, sold and withdrawn parcels are excluded. Government and conservancy offers are not imported. |

The [Michigan DNR program page](https://www.michigan.gov/dnr/managing-resources/real-estate/auctions-sales)
said summer 2026 auctions had concluded and unsold auction parcels would be relisted
on October 1. Those auction entries must not be promoted as currently open sales.

## Directory entries and missing feeds

- [HUD Home Store](https://www.hudhomestore.gov/) is an official foreclosure/REO
  directory link. Its robots policy disallows crawling; no HUD data is imported.
- [GSA real property disposition](https://disposal.gsa.gov/s/) is an official surplus
  property directory link. No GSA listing feed is integrated.
- [Michigan Treasury](https://www.michigan.gov/taxes/property/forfeiture-foreclosure)
  provides county tax-foreclosure information; it is not counted as an ingested feed.
- All 50 state directory links come from [USAGov's state directory](https://www.usa.gov/state-governments).
  They help locate public agencies and do not establish parcel-level data coverage.
- Nationwide pre-foreclosure records are **not connected**. A default notice is not
  a sale offer or an auction date. An approved county feed or licensed provider is
  needed before these records can populate search. For example, [ATTOM documents
  nationwide foreclosure data](https://www.attomdata.com/data/foreclosure-data/), but
  no ATTOM subscription, API credentials or redistribution rights have been supplied.
  No paid subscription was created and no credentials were requested in chat.
- County tax-deed and tax-lien feeds outside the connected Arkansas catalog need
  additional adapters and source-access review. The IRS connector does not fill this gap.

## Data and operation contracts

- No fabricated runtime data, geocoded approximations, or silent zero substitutions.
- A source snapshot is replaced atomically only after the full bounded retrieval
  succeeds. Failures retain last-good data with an unavailable/stale warning.
- Upstream HTML never reaches `innerHTML`. UI text uses text nodes; outbound request
  paths and browser source/image links use separate allowlists. No URL supplied by
  a search request can select an upstream host.
- Published dates are date-level information. Search excludes dates before today's
  UTC date, but same-day closing times and last-minute cancellations still require
  confirmation with the seller. No claim of real-time minute-level availability.
- Field completeness counts five supplied field groups, at 20% each: identity,
  published price/bid, acreage, descriptive text, and coordinates. It is not a
  confidence, valuation, title or investment-quality score.
- Unit/browser fixtures are synthetic. Live retrieval verification uses the CLI;
  fixture success alone never establishes upstream availability.

The generic listing JSON schema remains in existing `lw2_` tables; no account reset,
schema replacement, legacy database edit, billing integration or paid resource
addition is required for this expansion.
