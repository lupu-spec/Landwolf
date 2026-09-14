"""Synthetic government-page shapes; these fixtures are never runtime inventory."""

import asyncio
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from landwolf import catalog, national
from landwolf.db import Listing
from landwolf.national import (
    PublicReader,
    approved_url,
    arkansas_catalog,
    checked,
    parse_alaska,
    parse_arkansas,
    parse_irs,
    parse_michigan,
    parse_treasury,
    parse_usda,
    parse_usda_detail,
    usda_states,
)
from landwolf.provider import SourceUnavailable
from landwolf.schemas import PropertyRecord, SearchQuery
from landwolf.sources import safe_link
from landwolf.states import STATES

TREASURY = """<table><tr><td>RURAL LAND: 1 Fixture Road, Test City, Colorado 80000
ONLINE AUCTION DATE: Friday, October 2, 2099 4.5 ± acres. Sale # 99-66-001.
<a href="fixture.shtml">For complete details click here</a></td></tr></table>"""
ALASKA = """<section class="js-parcel-card" data-auction="998" data-parcel="1001"
data-price="25000" data-acres="5.5" data-subd="Synthetic Creek" data-region="Northern"
data-program="AUC-RES" data-resident-requirement="yes">
<div class="badge-price">Minimum Bid: $25,000</div></section>"""
PROGRAM = """<p>The bidding period for Auction #998 is between June 10 and September 30, 2099.
The auction event will be held on October 21, 2099.</p>"""
MI = """<div id="ListView"><div class="card">
<a href="/LandSale/Parcels/Details?ParcelId=9900">Property Details</a><dl>
<dt>Parcel Status:</dt><dd>Available</dd><dt>Size:</dt><dd>2.50 acres</dd>
<dt>Minimum Accepted</dt><dd>$5,000.00</dd><dt>Parcel Number</dt>
<dd>9900 Fixture County, T1N</dd><dt>Description</dt><dd>Synthetic parcel.</dd>
</dl></div></div>"""
IRS_FILTERS = """<form id="views-exposed-form-auction-items-block-1">
<select name="field_asset_type_target_id"><option selected value="8">Real-Estate</option></select>
<select name="field_sale_type_target_id"><option selected value="1">Seized</option></select>
</form>"""
IRS = (
    IRS_FILTERS
    + """<article class="irs-ad" id="node-9900"><h3>
<a href="/ad/fixture-home">Synthetic tax-seizure home</a></h3><div class="usa-card__body">
<time>Sep 15, 2099 10:00 AM</time><address>Test City WA, 98000</address></div>
<div class="field--name-field-minimum-bid"><div class="field__item">150,000.00</div></div>
</article>"""
)
USDA = """<table id="propertySummariesTable"><thead><tr><th>Photo</th><th>Listing Type</th>
<th>Street Address</th><th>City</th><th>State</th><th>County</th><th>Zip</th><th>Price/Bid</th>
</tr></thead><tbody><tr><td>
<a href="/resales/public/SFHPropertyDetail?id=9900&amp;listingType=Foreclosure">Details</a></td>
<td>Foreclosure</td><td>1 Synthetic Lane<br><a>Map</a></td><td>Test Town</td>
<td>Georgia</td><td>Fixture County</td><td>30000</td><td>$123,000</td></tr></tbody></table>"""

ARKANSAS = """<table id="tableAllCertifications"><thead><tr><th>County</th><th>Sale #</th>
<th>Name</th><th>Legal Description</th><th>Interested Parties</th><th>Parcel #</th><th>Taxes</th>
<th>Actions</th></tr></thead><tbody><tr><td>CLAY</td><td>9900</td>
<td>Synthetic owner placeholder</td>
<td>Synthetic deed restrictions; inspect the original.</td><td>Do not import this column</td>
<td>000-00000-000</td><td>$123.45</td><td>Source link</td></tr></tbody></table>"""


def test_arkansas_tax_catalog_excludes_cancellations_and_owner_columns() -> None:
    url = "https://cosl.org/Home/CatalogViewBySaleDate?saledate=9%2F15%2F2099%2010%3A00%3A00%20AM"
    html = f'<h1>Public Auction Catalog</h1><p>Sale Date</p><a href="{url}">Catalog</a>'
    assert arkansas_catalog(html, date(2099, 9, 14)) == [(url, date(2099, 9, 15))]
    assert arkansas_catalog(html, date(2099, 9, 16)) == []
    record = parse_arkansas(ARKANSAS, url, date(2099, 9, 15))[0]
    assert record.asking_price is None and record.price_kind == "Not published"
    assert record.reported_taxes == 123.45
    assert record.category == "tax_sale" and record.state == "AR"
    assert "owner placeholder" not in record.model_dump_json()
    assert "Do not import" not in record.model_dump_json()
    assert "restrictions" in record.legal_description
    canceled = ARKANSAS.replace("Synthetic owner placeholder", "ENTRY CANCELLED")
    assert parse_arkansas(canceled, url, date(2099, 9, 15)) == []
    with pytest.raises(SourceUnavailable):
        parse_arkansas(ARKANSAS.replace("$123.45", "-500"), url, date(2099, 9, 15))


def sample(**updates: object) -> PropertyRecord:
    return PropertyRecord.model_validate(
        {
            "id": "irs-9900",
            "source": "irs_auctions",
            "tract": "9900",
            "title": "Synthetic listing",
            "state": "WA",
            "category": "tax_sale",
            "source_url": "https://www.irsauctions.gov/ad/fixture-home",
            "retrieved_at": "2099-01-01T00:00:00Z",
            **updates,
        }
    )


def test_sale_types_preserve_unknowns_and_source_bid_semantics() -> None:
    treasury = parse_treasury(TREASURY)[0]
    assert treasury.state == "CO" and treasury.category == "public_auction"
    assert treasury.asking_price is None and treasury.price_kind == "Not published"
    assert treasury.acres == 4.5 and treasury.latitude is None
    assert treasury.auction_date == date(2099, 10, 2)
    alaska = parse_alaska(ALASKA, PROGRAM)[0]
    assert alaska.bidding_deadline == date(2099, 9, 30)
    assert alaska.auction_date == date(2099, 10, 21)
    assert alaska.eligibility == "Alaska residents only"
    assert alaska.price_kind == "Minimum bid"
    michigan = parse_michigan(MI)[0]
    assert michigan.acres == 2.5 and michigan.state == "MI"
    assert parse_michigan(MI.replace("Available", "Pending Bid Opening")) == []
    irs, more = parse_irs(IRS)
    assert irs[0].category == "tax_sale" and not more
    assert irs[0].sale_type == "Federal tax-seizure auction"
    assert parse_irs(IRS.replace("Synthetic tax-seizure home", "AUCTION CANCELED"))[0] == []
    usda = parse_usda(USDA, "SFH")[0]
    assert usda.title == "1 Synthetic Lane" and usda.acres is None
    assert usda.price_kind == "Government bid" and usda.auction_date is None
    assert parse_usda(USDA.replace("$123,000", "$0"), "SFH")[0].asking_price is None
    assert usda_states(
        '<select id="stateCode"><option value=""></option>'
        '<option value="13">Georgia (1)</option></select>'
    ) == ["13"]


@pytest.mark.parametrize(
    "parser,html",
    [
        (parse_treasury, "No table"),
        (parse_treasury, TREASURY.replace("fixture.shtml", "https://evil.example/")),
        (parse_michigan, MI.replace("Available", "Unknown future status")),
        (parse_michigan, MI.replace("2.50 acres", "-5 acres")),
        (parse_irs, IRS.replace('value="8"', 'value="9"')),
        (parse_irs, IRS.replace("/ad/fixture-home", "http://169.254.169.254/")),
        (lambda html: parse_alaska(ALASKA, html), "Missing bid deadline"),
        (lambda html: parse_usda(html, "SFH"), USDA.replace("Georgia", "Unknown state")),
        (lambda html: parse_usda(html, "SFH"), USDA.replace("$123,000", "$NaN")),
    ],
)
def test_source_layout_and_untrusted_field_failures(parser: object, html: str) -> None:
    with pytest.raises((SourceUnavailable, ValueError)):
        parser(html)


def test_usda_detail_date_and_empty_date_are_distinct() -> None:
    html = '<h1>Property Detail</h1><div class="col-md-4">Sale Date:</div><div>10/21/2099</div>'
    assert parse_usda_detail(html)["auction_date"] == date(2099, 10, 21)
    assert "auction_date" not in parse_usda_detail(html.replace("10/21/2099", ""))
    unknown = parse_usda_detail(html.replace("10/21/2099", "22 08 17"))
    assert unknown["active"] is False and unknown["sale_status"] == "Date needs review"
    assert unknown["auction_date_text"] == "22 08 17"
    assert parse_usda_detail(html.replace("10/21/2099", "5-26-23"))["auction_date"] == date(
        2023, 5, 26
    )
    fsa = USDA.replace("Price/Bid", "Value/Bid").replace("Foreclosure", "REO Property")
    fsa = fsa.replace("SFHPropertyDetail", "FSAPropertyDetail")
    assert parse_usda(fsa, "FSA")[0].asking_price is None
    detail = (
        '<h1>Property Detail</h1><div class="col-md-4">Appraised Value:</div><div>$330,000</div>'
    )
    assert parse_usda_detail(detail)["source_appraised_value"] == 330000


@pytest.mark.parametrize(
    "url",
    [
        "http://www.irsauctions.gov/ad/fixture",
        "https://www.irsauctions.gov.evil.example/ad/fixture",
        "https://" + ":".join(("test-user", "test-password")) + "@www.irsauctions.gov/ad/fixture",
        "https://www.irsauctions.gov:443/ad/fixture",
        "https://www.irsauctions.gov/ad/fixture?url=http://localhost",
        "https://www.irsauctions.gov/../admin",
        "https://169.254.169.254/",
        "file:///etc/passwd",
        "https://www.irsauctions.gov/ad/fixture#x",
    ],
)
def test_outbound_requests_reject_ssrf(url: str) -> None:
    assert not approved_url("irs_auctions", url)


def test_reader_blocks_redirects_size_content_type_and_bounds_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run(response: httpx.Response, expected: type[Exception]) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return response

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            reader = PublicReader("irs_auctions", client)
            with pytest.raises(expected):
                await reader.read("https://www.irsauctions.gov/ad/fixture")
            assert calls <= 2

    asyncio.run(
        run(httpx.Response(302, headers={"location": "http://localhost"}), httpx.HTTPStatusError)
    )
    asyncio.run(
        run(httpx.Response(200, headers={"content-type": "application/json"}), SourceUnavailable)
    )
    monkeypatch.setattr(national, "MAX_RESPONSE_BYTES", 20)
    asyncio.run(
        run(
            httpx.Response(200, text="x" * 21, headers={"content-type": "text/html"}),
            SourceUnavailable,
        )
    )
    asyncio.run(run(httpx.Response(503), httpx.HTTPStatusError))


def test_invalid_contracts_do_not_turn_unknowns_into_zero() -> None:
    assert sample().asking_price is None and sample().acres is None
    assert sample(asking_price=0).asking_price == 0
    assert SearchQuery(state="ak").state == "AK"
    for fields in [
        {"state": "ZZ"},
        {"latitude": 50},
        {"sale_status": "Auction scheduled"},
        {"category": "pre_foreclosure"},
        {"asking_price": float("inf")},
    ]:
        with pytest.raises(ValueError):
            sample(**fields)
    assert (
        sample(category="pre_foreclosure", sale_status="Pre-foreclosure notice").auction_date
        is None
    )
    with pytest.raises(SourceUnavailable):
        checked([sample(), sample()])
    assert not safe_link("https://www.usa.gov.evil.example/states/alaska")


def test_failed_source_preserves_its_snapshot_and_other_sources(
    client: TestClient, inventory: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = client.app.state.provider.providers["irs_auctions"]

    async def good(*_: object) -> list[PropertyRecord]:
        return [sample()]

    monkeypatch.setattr(catalog, "retrieve", good)
    first = asyncio.run(provider.refresh())
    assert first["status"] == "ready" and first["record_count"] == 1

    async def failure(*_: object) -> list[PropertyRecord]:
        raise SourceUnavailable("Synthetic outage")

    monkeypatch.setattr(catalog, "retrieve", failure)
    failed = asyncio.run(provider.refresh())
    assert failed["status"] == "unavailable" and failed["last_success"] == first["last_success"]
    with client.app.state.factory() as session:
        assert session.get(Listing, "irs-9900").active
        assert session.get(Listing, "glo-99001").active

    async def empty(*_: object) -> list[PropertyRecord]:
        return []

    monkeypatch.setattr(catalog, "retrieve", empty)
    assert asyncio.run(provider.refresh())["status"] == "ready"
    with client.app.state.factory() as session:
        assert not session.get(Listing, "irs-9900").active
        assert session.get(Listing, "glo-99001").active


def test_all_50_states_and_directory_counts_are_independent_of_feed_completeness(
    client: TestClient, signed_in: dict[str, str]
) -> None:
    with client.app.state.factory() as session, session.begin():
        for code in STATES:
            item = sample(id="fixture-" + code, state=code)
            session.add(
                Listing(
                    id=item.id,
                    source=item.source,
                    active=True,
                    payload=item.model_dump(mode="json"),
                )
            )
    for code in STATES:
        data = client.post("/api/search", json={"state": code.lower()}, headers=signed_in).json()
        assert data["total"] == 1 and data["results"][0]["state"] == code
    all_states = client.post("/api/search", json={"page_size": 100}, headers=signed_in).json()
    assert all_states["total"] == 50
    coverage = client.get("/api/sources").json()
    assert {s["state"] for s in coverage["states"]} == set(STATES)
    assert sum(s["record_count"] for s in coverage["states"]) == 50
    assert all(s["record_count"] == 0 for s in coverage["sources"] if not s["automated"])


def test_nationwide_filters_unknowns_expiry_and_stable_pagination(
    client: TestClient, signed_in: dict[str, str]
) -> None:
    with client.app.state.factory() as session, session.begin():
        for item in [
            sample(id="irs-known", asking_price=100, acres=2),
            sample(id="irs-unknown"),
            sample(id="irs-past", auction_date="2000-01-01", sale_status="Auction scheduled"),
            sample(id="irs-deadline", auction_date="2099-01-01", bidding_deadline="2000-01-01"),
        ]:
            session.add(
                Listing(
                    id=item.id,
                    source=item.source,
                    active=True,
                    payload=item.model_dump(mode="json"),
                )
            )

    def search(**fields: object) -> dict:
        response = client.post("/api/search", json=fields, headers=signed_in)
        assert response.status_code == 200
        return response.json()

    assert search()["total"] == 2
    assert search(max_price=101)["total"] == 1
    assert search(min_acres=1)["total"] == 1
    assert search(category="foreclosure")["total"] == 0
    assert search(source="tx_glo_public")["total"] == 0
    assert search(sort="price_desc")["results"][-1]["id"] == "irs-unknown"
    assert search(page_size=1, page=2)["results"][0]["id"] == "irs-unknown"
    assert search(location="%")["total"] == 0
    assert client.get("/api/properties/irs-past").json()["active"] is False
    assert client.put("/api/saved/irs-past", json={}, headers=signed_in).status_code == 200
    assert search(saved_only=True)["results"][0]["id"] == "irs-past"
    for query in [{"state": "ZZ"}, {"source": "unknown"}]:
        assert client.post("/api/search", json=query, headers=signed_in).status_code == 422
