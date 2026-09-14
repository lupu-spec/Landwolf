import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from landwolf import provider
from landwolf.db import Listing
from landwolf.provider import SourceUnavailable, parse_detail, parse_inventory, safe_source_url

FIXTURES = Path(__file__).parent / "fixtures"
INVENTORY = (FIXTURES / "inventory.html").read_text()
DETAIL = (FIXTURES / "detail.html").read_text()


def test_inventory_preserves_source_facts_and_unknowns() -> None:
    record = parse_inventory(INVENTORY, "2026-09-14T00:00:00+00:00")[0]
    assert record.id == "glo-14968"
    assert record.acres == 10.89
    assert record.asking_price == 196000
    assert record.price_kind == "Published sale price"
    assert record.latitude is None
    assert record.legal_description is None
    assert record.source_url.endswith("/tract/14968")


@pytest.mark.parametrize(
    "html",
    [
        "<html>Source unavailable</html>",
        INVENTORY.replace("$196,000", "NaN"),
        INVENTORY.replace("10.8900 acres", "-1 acres"),
        INVENTORY.replace("<strong>14968</strong>", "<strong>bad</strong>"),
        INVENTORY.replace("/veterans/land-sale/public/tract/14968", "https://evil.example.com/"),
        INVENTORY.replace("</tbody>", INVENTORY.split("<tbody>")[1]),
    ],
)
def test_incomplete_or_invalid_inventory_fails_closed(html: str) -> None:
    with pytest.raises(SourceUnavailable):
        parse_inventory(html, "2026-09-14T00:00:00+00:00")


def test_detail_only_maps_valid_source_coordinates() -> None:
    result = parse_detail(DETAIL)
    assert result["latitude"] == pytest.approx(32.484552777778)
    assert result["longitude"] == pytest.approx(-98.517502777778)
    assert "latitude" not in parse_detail(DETAIL.replace("32.484552777778", "0"))
    with pytest.raises(SourceUnavailable):
        parse_detail("<html>Login required</html>")


@pytest.mark.parametrize(
    "url",
    [
        "http://www.glo.texas.gov/veterans/land-sale/public",
        "http://169.254.169.254/",
        "https://www.glo.texas.gov.evil.example.com/veterans/land-sale/public",
        "https://www.glo.texas.gov/veterans/land-sale/public?redirect=evil",
        "https://www.glo.texas.gov/admin",
        "file:///etc/passwd",
    ],
)
def test_source_url_rejects_ssrf(url: str) -> None:
    assert not safe_source_url(url)


def test_sync_failure_retains_cache_and_complete_sync_deactivates_missing(
    client: TestClient, inventory: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def good_fetch(_: httpx.AsyncClient, url: str) -> str:
        return INVENTORY if url == provider.INVENTORY else DETAIL

    monkeypatch.setattr(provider, "fetch_text", good_fetch)
    source = client.app.state.provider
    assert asyncio.run(source.refresh())["status"] == "ready"
    with client.app.state.factory() as session:
        active = session.scalars(select(Listing).where(Listing.active.is_(True))).all()
        assert [record.id for record in active] == ["glo-14968"]
        assert active[0].payload["latitude"] == pytest.approx(32.484552777778)

    async def failure(_: httpx.AsyncClient, url: str) -> str:
        raise SourceUnavailable("Simulated upstream outage")

    monkeypatch.setattr(provider, "fetch_text", failure)
    status = asyncio.run(source.refresh())
    assert status["status"] == "unavailable"
    assert status["last_success"] is not None
    with client.app.state.factory() as session:
        assert session.get(Listing, "glo-14968").active


def test_failed_detail_retains_prior_detail_timestamp(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def initial(_: httpx.AsyncClient, url: str) -> str:
        return INVENTORY if url == provider.INVENTORY else DETAIL

    monkeypatch.setattr(provider, "fetch_text", initial)
    source = client.app.state.provider
    asyncio.run(source.refresh())
    with client.app.state.factory() as session:
        timestamp = session.get(Listing, "glo-14968").payload["detail_retrieved_at"]

    async def partial(_: httpx.AsyncClient, url: str) -> str:
        if url == provider.INVENTORY:
            return INVENTORY
        raise SourceUnavailable("Simulated detail outage")

    monkeypatch.setattr(provider, "fetch_text", partial)
    assert asyncio.run(source.refresh())["status"] == "ready"
    with client.app.state.factory() as session:
        assert session.get(Listing, "glo-14968").payload["detail_retrieved_at"] == timestamp


def test_http_redirect_content_type_and_size_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run(response: httpx.Response) -> None:
        transport = httpx.MockTransport(lambda _: response)
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(SourceUnavailable):
                await provider.fetch_text(client, provider.INVENTORY)

    asyncio.run(run(httpx.Response(302, headers={"location": "http://169.254.169.254"})))
    asyncio.run(run(httpx.Response(200, headers={"content-type": "application/json"})))
    monkeypatch.setattr(provider, "MAX_BYTES", 100)
    asyncio.run(run(httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * 101)))
