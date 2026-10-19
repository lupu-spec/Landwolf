"""Synthetic commercial pages and state isolation; never fabricated runtime listings."""

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from landwolf import commercial
from landwolf.catalog import InventoryProvider
from landwolf.craigslist_regions import REGIONS
from landwolf.db import Listing
from landwolf.provider import SourceUnavailable
from landwolf.sources import SOURCE_BY_ID, SOURCES
from landwolf.states import STATES
from landwolf.trust import publish_snapshot


def script(value, kind="application/json"):
    return f'<script type="{kind}">{json.dumps(value)}</script>'


def zillow(**updates):
    row = {
        "zpid": "9900",
        "detailUrl": "https://www.zillow.com/homedetails/Synthetic-TX/9900_zpid/",
        "address": "Synthetic tract, TX",
        "unformattedPrice": 120000,
        "latLong": {"latitude": 32.5, "longitude": -97.5},
        "hdpData": {
            "homeInfo": {
                "state": "TX",
                "homeType": "LOT",
                "homeStatus": "FOR_SALE",
                "lotAreaValue": 87120,
                "lotAreaUnit": "sqft",
            }
        },
        **updates,
    }
    return script({"listResults": [row, row]})


def craigslist(state="TX", title="Synthetic 2.5 acres land", duplicate=False):
    place = {
        "name": title,
        "latitude": 32.5,
        "longitude": -97.5,
        "address": {"addressRegion": state, "addressLocality": "Fixture Town"},
    }
    item = {"@type": "ListItem", "item": place}
    data = {"@type": "ItemList", "itemListElement": [item, item] if duplicate else [item]}
    return (
        script(data, "application/ld+json")
        + f'''<li class="cl-static-search-result" title="{title}">
    <a href="https://www.craigslist.org/view/d/synthetic-land/FixtureListing123">
    <div class="price">$25,000</div></a></li>'''
    )


def compass(**updates):
    url = "https://www.compass.com/homedetails/Synthetic-TX/fixture_pid/"
    return "<title>Land for Sale in Texas | Compass</title>" + script(
        [
            {
                "@type": "Product",
                "url": url,
                "name": "Synthetic land listing",
                "offers": {
                    "priceCurrency": "USD",
                    "availability": "https://schema.org/InStock",
                    "price": "50000",
                    **updates,
                },
            },
            {
                "@type": "SingleFamilyResidence",
                "url": url,
                "address": {"addressRegion": "TX", "addressLocality": "Fixture Town"},
                "geo": {"latitude": "32.5", "longitude": "-97.5"},
            },
        ],
        "application/ld+json",
    )


def test_zillow_deduplicates_converts_area_and_preserves_asking_price():
    rows = commercial.parse("zillow_tx", zillow())
    assert len(rows) == 1
    item = rows[0]
    assert item.acres == 2 and item.acreage_basis == "calculated"
    assert item.asking_price == 120000 and item.price_kind == "Published sale price"
    assert item.category == "seller_listing" and item.image_url is None
    assert item.latitude == 32.5 and "not independently verified" in item.eligibility


@pytest.mark.parametrize("state", list(STATES))
def test_craigslist_all_50_state_definitions_and_published_state_filter(state):
    source = f"craigslist_{state.lower()}"
    definition = SOURCE_BY_ID[source]
    assert definition.states == (state,) and definition.automated
    assert 0 < len(REGIONS[state]) <= 40
    rows = commercial.parse(source, craigslist(state))
    assert rows[0].state == state and rows[0].source == source
    assert rows[0].acres == 2.5 and rows[0].asking_price == 25000
    other = "OK" if state != "OK" else "TX"
    assert commercial.parse(source, craigslist(other), allow_empty=True) == []


@pytest.mark.parametrize(
    "title", ["Home and land 2 acres", "Land rent monthly", "Zero down land", "Apartment sale"]
)
def test_craigslist_rejects_residential_rental_and_financing_promotions(title):
    assert commercial.parse("craigslist_tx", craigslist(title=title), allow_empty=True) == []


def test_craigslist_ambiguous_location_never_assigns_coordinates():
    assert commercial.parse("craigslist_tx", craigslist(duplicate=True), allow_empty=True) == []


def test_compass_matches_offer_location_and_preserves_unknown_acreage():
    item = commercial.parse("compass_tx", compass())[0]
    assert item.asking_price == 50000 and item.acres is None
    assert item.state == "TX" and item.longitude == -97.5
    with pytest.raises(SourceUnavailable):
        commercial.parse("compass_tx", compass().replace("Land for Sale in Texas", "Homes"))
    assert (
        commercial.compass(commercial.BeautifulSoup(compass(availability="SoldOut"), "html.parser"))
        == []
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://www.zillow.com/homedetails/Test/9900_zpid/",
        "https://evil.example/homedetails/Test/9900_zpid/",
        "https://www.zillow.com/homedetails/Test/9900_zpid/?next=x",
        "https://fixture-user@www.zillow.com/homedetails/Test/9900_zpid/",
        "https://www.zillow.com:444/homedetails/Test/9900_zpid/",
    ],
)
def test_listing_display_urls_reject_untrusted_components(url):
    with pytest.raises(SourceUnavailable):
        commercial.parse("zillow_tx", zillow(detailUrl=url))


@pytest.mark.parametrize(
    "html",
    [
        "<html>Access denied</html>",
        '<script type="application/json">{bad}</script>',
        zillow(unformattedPrice=float("nan")),
        zillow(unformattedPrice=True),
        zillow(latLong={"latitude": 100, "longitude": -97}),
    ],
)
def test_malformed_or_invalid_listing_page_fails_closed(html):
    with pytest.raises((SourceUnavailable, ValueError)):
        commercial.parse("zillow_tx", html)


def test_oversized_and_unknown_source_requests_fail():
    with pytest.raises(SourceUnavailable):
        commercial.parse("unknown", "")
    with pytest.raises(SourceUnavailable):
        commercial.parse("zillow_tx", "x" * (commercial.MAX_BYTES + 1))
    with pytest.raises(SourceUnavailable):
        commercial.objects([[{}] * 50001])


@pytest.mark.parametrize(
    "status,policy", [(200, "User-agent: *\nDisallow: /"), (403, ""), (429, ""), (302, "")]
)
def test_policy_and_access_failures_do_not_fetch_listing_page(status, policy):
    seen = []

    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(status, text=policy, headers={"content-type": "text/plain"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await commercial.retrieve("zillow_tx", client)

    with pytest.raises(SourceUnavailable):
        asyncio.run(run())
    assert seen == ["https://www.zillow.com/robots.txt"]


def test_reader_uses_exact_fixed_pages_and_no_private_endpoints():
    seen = []

    def respond(request):
        seen.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, text="User-agent: *\nAllow: /", headers={"content-type": "text/plain"}
            )
        return httpx.Response(200, text=zillow(), headers={"content-type": "text/html"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await commercial.retrieve("zillow_tx", client)

    assert len(asyncio.run(run())) == 1
    assert seen == ["https://www.zillow.com/robots.txt", commercial.PAGES["zillow_tx"]]


def test_state_refresh_preserves_snapshot_when_a_region_fails(client, monkeypatch):
    item = commercial.parse("zillow_tx", zillow())[0]
    factory = client.app.state.factory
    with factory() as session, session.begin():
        publish_snapshot(session, item.source, [item], scope_note=commercial.SCOPE)

    async def failed(source, http):
        raise SourceUnavailable("Publisher returned HTTP 403; no bypass")

    monkeypatch.setattr(commercial, "retrieve", failed)
    status = asyncio.run(InventoryProvider(factory, SOURCE_BY_ID[item.source]).refresh())
    assert status["status"] == "unavailable" and status["record_count"] == 1
    with factory() as session:
        assert session.get(Listing, item.id).active


def test_catalog_options_search_and_detail_share_new_sources(client: TestClient, signed_in):
    options = client.get("/api/source-options").json()
    assert len([x for x in options if x["id"].startswith("craigslist_")]) == 50
    assert all(set(x) == {"id", "name", "states", "categories"} for x in options)
    records = [
        commercial.parse("zillow_tx", zillow())[0],
        commercial.parse("compass_tx", compass())[0],
        commercial.parse("craigslist_ca", craigslist("CA"))[0],
    ]
    with client.app.state.factory() as session, session.begin():
        for item in records:
            publish_snapshot(session, item.source, [item], scope_note=commercial.SCOPE)
    result = client.post(
        "/api/search",
        json={"state": "CA", "source": "craigslist_ca", "category": "seller_listing"},
        headers=signed_in,
    )
    assert result.status_code == 200
    assert result.json()["total"] == 1 and result.json()["map_total"] == 1
    detail = client.get("/api/properties/" + records[-1].id).json()
    assert detail["state"] == "CA" and detail["category"] == "seller_listing"
    assert "not independently verified" in detail["eligibility"]
    assert (
        client.post(
            "/api/search", json={"state": "TX", "source": "craigslist_ca"}, headers=signed_in
        ).json()["total"]
        == 0
    )
    assert len(SOURCES) == 66


def test_source_options_requires_authentication(client):
    assert client.get("/api/source-options").status_code == 401


def test_commercial_hunt_results_require_review_and_research_uses_source_point(client, signed_in):
    import time

    from landwolf.db import SourceState
    from landwolf.hunt import Criteria, evaluate
    from landwolf.locations import source_location

    item = commercial.parse("zillow_tx", zillow())[0]
    criteria = Criteria(mode="fixed", states=["TX"], min_acres=1, max_acres=10)
    result = evaluate(
        item, criteria, SourceState(id=item.source, status="ready", last_success=int(time.time()))
    )
    assert result["eligibility"] == "needs_review"
    point = source_location(item)
    assert point.latitude == 32.5 and point.longitude == -97.5
    assert item.asking_price == 120000


def test_state_refresh_is_atomic_across_multiple_regions(monkeypatch):
    pages = commercial.PAGE_GROUPS["craigslist_tx"]
    seen = []

    def respond(request):
        seen.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, text="User-agent: *\nAllow: /", headers={"content-type": "text/plain"}
            )
        if str(request.url) == pages[0]:
            return httpx.Response(200, text=craigslist(), headers={"content-type": "text/html"})
        return httpx.Response(403)

    async def immediate(_):
        return None

    monkeypatch.setattr(commercial.asyncio, "sleep", immediate)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await commercial.retrieve("craigslist_tx", client)

    with pytest.raises(SourceUnavailable, match="403"):
        asyncio.run(run())
    assert seen[1:] == list(pages[:2])


@pytest.mark.parametrize(
    "html",
    [
        zillow(hdpData=[]),
        zillow(detailUrl={"bad": "shape"}),
        zillow(latLong=[]),
        '<script type="application/json">' + "[" * 2000 + "]" * 2000 + "</script>",
    ],
)
def test_malformed_nested_publisher_shapes_do_not_escape_refresh_contract(html):
    with pytest.raises(SourceUnavailable):
        commercial.parse("zillow_tx", html)
