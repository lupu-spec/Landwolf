"""Synthetic seller feeds: complete snapshots, isolation and public provenance."""

import asyncio
import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from landwolf.db import Listing, PrivateListingOrigin
from landwolf.private_listings import (
    FeedConfig,
    SellerListing,
    finish_status,
    import_feed,
    load_configs,
    public_url,
)


def config(key: str = "fixture_feed") -> FeedConfig:
    return FeedConfig(
        key=key,
        url="https://inventory.example.test/feed",
        feed_hosts=["inventory.example.test"],
        original_hosts=["agent.example.test"],
        access_reference="Synthetic fixture; no real listings",
    )


def listing(identifier: int = 1) -> dict[str, Any]:
    return {
        "external_id": str(identifier),
        "acquisition_url": f"https://inventory.example.test/property/{identifier}",
        "original_listing_url": f"https://agent.example.test/listing/{identifier}",
        "state": "TX",
        "county": "Fixture",
        "acres": 10,
        "asking_price": 12345,
        "seller_type": "broker",
        "listing_agent": "Synthetic Agent",
        "listing_brokerage": "Synthetic Brokerage",
    }


def page(items: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    return {
        "snapshot_id": "fixture-snapshot",
        "total": len(items),
        "complete": True,
        "next_url": None,
        "listings": items,
        **overrides,
    }


def run_feed(client: TestClient, pages: list[Any], cfg: FeedConfig | None = None) -> int:
    iterator = iter(pages)

    def handle(request: httpx.Request) -> httpx.Response:
        item = next(iterator, pages[-1])
        if isinstance(item, int):
            return httpx.Response(item)
        return httpx.Response(200, json=item)

    async def run() -> int:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as transport:
            return await import_feed(client.app.state.factory, cfg or config(), transport)

    return asyncio.run(run())


def records(client: TestClient) -> list[dict[str, Any]]:
    with client.app.state.factory() as session:
        return [
            row.payload for row in session.scalars(select(Listing).where(Listing.active.is_(True)))
        ]


def test_import_updates_idempotently_and_preserves_broker(client: TestClient) -> None:
    for price in (12345, 10000, 10000):
        run_feed(client, [page([{**listing(), "asking_price": price}])])
    rows = records(client)
    assert len(rows) == 1
    assert rows[0]["asking_price"] == 10000
    assert rows[0]["category"] == "private_seller"
    assert rows[0]["seller_type"] == "broker"
    assert rows[0]["listing_agent"] == "Synthetic Agent"
    assert rows[0]["source_name"] == "Private Seller Listings"
    assert "inventory.example.test" not in json.dumps(rows)
    with client.app.state.factory() as session:
        origin = session.scalar(select(PrivateListingOrigin))
        assert origin.acquisition_url == listing()["acquisition_url"]


@pytest.mark.parametrize("failure", [403, 429, 500, "short", "duplicate", "changed", "loop"])
def test_failed_or_incomplete_refresh_preserves_snapshot(client: TestClient, failure: Any) -> None:
    run_feed(client, [page([listing()])])
    before = records(client)
    first = page(
        [listing(2)], total=3, complete=False, next_url="https://inventory.example.test/page2"
    )
    last = page([listing(3)], total=3)
    if isinstance(failure, int):
        last = failure
    elif failure == "duplicate":
        last = page([listing(2), listing(3)], total=3)
    elif failure == "changed":
        last = page([listing(3), listing(4)], total=3, snapshot_id="changed")
    elif failure == "loop":
        last = page(
            [listing(3)], total=3, complete=False, next_url="https://inventory.example.test/page2"
        )
    with pytest.raises((ValueError, httpx.HTTPError)):
        run_feed(client, [first, last])
    assert records(client) == before


def test_removal_does_not_change_other_provider(client: TestClient) -> None:
    run_feed(client, [page([listing(1), listing(2)])])
    run_feed(client, [page([listing(3)])], config("another_fixture"))
    run_feed(client, [page([listing(2)])])
    assert len(records(client)) == 2
    with pytest.raises(ValueError, match="removal"):
        run_feed(client, [page([])])
    assert len(records(client)) == 2


def test_inventory_larger_than_old_5000_limit(client: TestClient) -> None:
    pages = []
    for number in range(6):
        items = [listing(n) for n in range(number * 1000, (number + 1) * 1000)]
        pages.append(
            page(
                items,
                total=6000,
                complete=number == 5,
                next_url=None
                if number == 5
                else f"https://inventory.example.test/page{number + 2}",
            )
        )
    assert run_feed(client, pages) == 6000
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(Listing)) == 6000


def test_generic_authenticated_api_and_direct_link(
    client: TestClient, signed_in: dict[str, str]
) -> None:
    run_feed(client, [page([listing()])])
    finish_status(client.app.state.factory, 1, True)
    response = client.post("/api/search", json={"category": "private_seller"}, headers=signed_in)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert "inventory.example.test" not in response.text
    record = response.json()["results"][0]
    assert record["source_url"] == listing()["original_listing_url"]
    sources = client.get("/api/sources")
    assert "inventory.example.test" not in sources.text
    client.cookies.clear()
    assert client.get("/api/sources").status_code == 401


@pytest.mark.parametrize(
    "url",
    [
        "http://agent.example.test/x",
        "https://127.0.0.1/x",
        "https://agent.example.test@evil.test/x",
        "https://agent.example.test:444/x",
        "https://evil.test/x",
        "javascript:alert(1)",
    ],
)
def test_rejects_unapproved_links(url: str) -> None:
    assert not public_url(url, config().original_hosts)
    with pytest.raises(ValueError):
        SellerListing(**{**listing(), "original_listing_url": url}).record(config(), "2099-01-01")


def test_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        load_configs("{}")
    with pytest.raises(ValueError):
        load_configs(json.dumps([config().model_dump(), config().model_dump()]))
    with pytest.raises(ValueError):
        SellerListing(**{**listing(), "latitude": 32}).record(config(), "2099-01-01")
    with pytest.raises(ValueError):
        SellerListing(**{**listing(), "asking_price": float("nan")})
    with pytest.raises(ValueError):
        SellerListing(
            **{**listing(), "original_listing_url": "https://inventory.example.test/x"}
        ).record(config(), "2099-01-01")


@pytest.mark.parametrize(
    "status_code, retry_after, expected_calls",
    [(403, None, 1), (429, None, 1), (429, "120", 1), (429, "0", 3), (503, None, 3)],
)
def test_retry_budget_stops_at_access_denial(
    status_code: int, retry_after: str | None, expected_calls: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    from landwolf.private_listings import fetch_page

    calls = 0

    async def immediate_sleep(seconds: float) -> None:
        assert seconds >= 0

    monkeypatch.setattr(asyncio, "sleep", immediate_sleep)

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status_code, headers={"Retry-After": retry_after} if retry_after else {}
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as transport:
            with pytest.raises(httpx.HTTPStatusError):
                await fetch_page(transport, config().url, config())

    asyncio.run(run())
    assert calls == expected_calls
