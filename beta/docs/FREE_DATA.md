# Free public property data

Access and response shapes checked September 14, 2026. No API keys, provider
accounts, trials, billing credentials or subscriptions were created for these
connections. Public service availability and geographic completeness can vary.

| Connected source | API | Meaning and coverage |
| --- | --- | --- |
| U.S. Census Geocoder | [Geographies API](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html) | Address matching or coordinate lookup; state, county and tract identifiers. The beta accepts all 50 states. Address coordinates are interpolated along address ranges, not surveyed parcel points. |
| FEMA NFHL | [Public map service](https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer) | Layer 0 checks digital coverage; layer 28 returns intersecting effective flood-zone attributes. Missing coverage or zones mean unknown. This point screen is not a whole-parcel analysis or an insurance determination. |
| USGS EPQS | [API documentation](https://epqs.nationalmap.gov/v1/docs) | Terrain elevation in meters/feet, source resolution and acquisition date where published. Not a building elevation certificate. [National Map reuse guidance](https://www.usgs.gov/faqs/what-are-terms-uselicensing-map-services-and-data-national-map). |
| USDA NRCS Soil Data Access | [Service documentation](https://sdmdataaccess.nrcs.usda.gov/WebServiceHelp.aspx) | SSURGO map-unit and component attributes at a point: drainage, hydrologic group, slope and farmland class where surveyed. Components describe a map unit, not exact conditions at every location. Credit: [Soil Survey Staff, USDA NRCS](https://sdmdataaccess.nrcs.usda.gov/Citation.htm). |
| North Carolina OneMap | [Parcel polygon service](https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1) | Point-intersecting county parcels: identifiers, GIS acreage, reported assessment values, use and source dates. Service metadata covers 100 NC counties and the Eastern Band of Cherokee Indians. County completeness and update dates vary. [NC OneMap](https://www.nconemap.gov/) provides data and APIs for applications. |

NC parcel values retain their published type; they are not asking prices or an
independent market valuation. Multiple intersecting candidates are retained.
Approximate address points may identify the wrong parcel, especially along roads.
Users must confirm identity and boundaries with county records. Owner names,
mailing addresses and contact fields are not requested, stored or displayed.
Nationwide assessor, deed, title, lien, permit and zoning databases are not connected.

## MLS and account-based alternatives

**Live MLS is not connected.** RESO defines interoperability standards; it does
not grant production listing rights. Its reference developer server uses prior-year
Austin/UnlockMLS data for testing and development. It is unsuitable as live beta
inventory. Production access requires permission and licensing from the MLS/data
provider, including applicable display and media conditions.
[RESO API FAQ](https://www.reso.org/knowledge-base/reso-web-api-faq/),
[data FAQ](https://www.reso.org/knowledge-base/data-topics-faq/).

[RentCast](https://www.rentcast.io/api) advertises 50 free calls per month, with
paid per-request overages. It requires an account/key and an
[API license](https://www.rentcast.io/terms-api). It is not connected and no account
was opened. Any future integration must establish applicable data rights and an
enforced usage ceiling before activation; a free allowance is not unlimited free use.

## Request and failure contract

Authenticated `POST /api/research` accepts exactly one of:

```json
{"address":"1500 Marilla St, Dallas, TX 75201"}
```

```json
{"latitude":35.7804,"longitude":-78.6391}
```

```json
{"listing_id":"glo-99001"}
```

The listing example is a test ID, not real inventory. Listing lookups use only
stored source coordinates. An absent point requires explicit user location input.
An ambiguous/unmatched address stops downstream research. Census state conflicts
with a published listing also fail closed. DC and territories are outside this
beta's selected scope.

All requests require a valid server session, trusted origin and CSRF token.
Database-backed limits allow 12 research requests per account/minute and 40 total
per minute. Four lookups can execute concurrently per worker; the existing beta
runs one worker. Connections are released before upstream I/O. Each lookup allows
at most 14 outbound attempts, one retry for selected transient errors, a 2 MB JSON
response limit, and no redirects or user-selected endpoints. Census has a 25-second
overall deadline; parallel source lookups each have 30 seconds. The UI allows 60
seconds and discards results after input changes or logout.

The USDA API accepts SQL rather than bind parameters. Only validated finite numeric
coordinates, formatted as numeric literals, enter a fixed read-only query. No user
address, parcel ID, SQL or URL is interpolated. ArcGIS requests name explicit fields
and request at most 21 records; more than 20 or a transfer-limit flag fails closed.
No incomplete page is represented as complete research.

Failures produce per-source unknown/unavailable states without hiding successful
sources. A bounded 128-entry memory cache retains ready reports for six hours and
other statuses for 60 seconds. Original retrieval timestamps survive cache hits;
they are distinct from acquisition, revision or transformation dates. No public
reference result changes listing coordinates, asking prices, accounts
or scenario assumptions. Public providers receive the address or resolved point
necessary for their queries; those inputs are not added to application logs.
