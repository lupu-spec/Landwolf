"""Read-only, bounded official Texas GLO public-sale adapter with provenance."""

import asyncio
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from landwolf.db import Listing, SourceState
from landwolf.schemas import PropertyRecord

LOGGER = logging.getLogger(__name__)
SOURCE = "tx_glo_public"
ORIGIN = "https://www.glo.texas.gov"
INVENTORY = ORIGIN + "/veterans/land-sale/public"
MAX_RECORDS = 500
MAX_BYTES = 6_000_000
REFRESH_SECONDS = 6 * 3600


class SourceUnavailable(Exception):
    """No complete, trustworthy inventory was obtained."""


def stamp() -> str:
    return datetime.now(UTC).isoformat()


def safe_source_url(url: str) -> bool:
    parts = urlsplit(url)
    return bool(
        parts.scheme == "https"
        and parts.netloc == "www.glo.texas.gov"
        and not parts.query
        and not parts.fragment
        and (
            parts.path == "/veterans/land-sale/public"
            or re.fullmatch(r"/veterans/land-sale/public/tract/\d{1,12}", parts.path)
        )
    )


def parse_inventory(html: str, retrieved_at: str) -> list[PropertyRecord]:
    soup = BeautifulSoup(html, "html.parser")
    table = next(
        (
            t
            for t in soup.find_all("table")
            if "Tract Number" in t.get_text() and "Sale Price" in t.get_text()
        ),
        None,
    )
    if table is None:
        raise SourceUnavailable("Inventory layout changed; cached records retained")
    rows = table.select("tbody tr")
    if not rows or len(rows) > MAX_RECORDS:
        raise SourceUnavailable("Unexpected inventory size; manual source review required")
    records: list[PropertyRecord] = []
    seen: set[str] = set()
    for row in rows:
        cells = row.find_all("td")
        if len(cells) != 6:
            raise SourceUnavailable("Unexpected inventory row")
        tract = cells[1].get_text(strip=True)
        if not re.fullmatch(r"\d{1,12}", tract) or tract in seen:
            raise SourceUnavailable("Invalid or duplicate tract identifier")
        seen.add(tract)
        link = cells[5].find("a", href=True)
        url = urljoin(ORIGIN, str(link["href"])) if link else ""
        if not safe_source_url(url) or not url.endswith("/tract/" + tract):
            raise SourceUnavailable("Unexpected source link")
        img = cells[0].find("img", src=True)
        image = str(img["src"]) if img else None
        if image and not re.fullmatch(
            r"https://cdn\.glo\.texas\.gov/vlb/land/tract-images/[0-9]+/[A-Za-z0-9_.-]+", image
        ):
            image = None
        try:
            acres = float(cells[3].get_text(strip=True).replace("acres", "").replace(",", ""))
            price = float(cells[4].get_text(strip=True).replace("$", "").replace(",", ""))
            county = cells[2].get_text(" ", strip=True)
            if not county or len(county) > 80:
                raise ValueError("Invalid county")
            records.append(
                PropertyRecord(
                    id=f"glo-{tract}",
                    tract=tract,
                    title=f"Tract {tract}",
                    county=county,
                    acres=acres,
                    asking_price=price,
                    source_url=url,
                    image_url=image,
                    retrieved_at=retrieved_at,
                )
            )
        except ValueError as exc:
            raise SourceUnavailable("Invalid source field; inventory was not replaced") from exc
    return records


def parse_detail(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    fields: dict[str, str] = {}
    for heading in soup.find_all("h3"):
        label = heading.get_text(" ", strip=True)
        paragraph = heading.find_next_sibling("p")
        if paragraph is not None:
            fields[label] = paragraph.get_text(" ", strip=True)[:4000]
    result: dict[str, Any] = {
        "legal_description": fields.get("Legal Description"),
        "location_description": fields.get("Location"),
        "source_account": fields.get("Account Number"),
    }
    if not result["legal_description"] or not result["location_description"]:
        raise SourceUnavailable("Property detail layout changed")
    for anchor in soup.find_all("a", href=True):
        parts = urlsplit(str(anchor["href"]))
        if parts.scheme != "https" or parts.netloc != "maps.google.com":
            continue
        value = parse_qs(parts.query).get("q", [""])[0]
        match = re.fullmatch(r"(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)", value)
        if match:
            lat, lng = float(match[1]), float(match[2])
            # Never map a generic geocoder result or a point outside Texas as this tract.
            if 25 <= lat <= 37 and -107 <= lng <= -93:
                result.update(latitude=lat, longitude=lng)
            break
    result["detail_retrieved_at"] = stamp()
    result["data_completeness"] = 100 if "latitude" in result else 80
    return result


async def fetch_text(client: httpx.AsyncClient, url: str) -> str:
    if not safe_source_url(url):
        raise SourceUnavailable("Unapproved source URL")
    try:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            if "text/html" not in response.headers.get("content-type", ""):
                raise SourceUnavailable("Unexpected source content type")
            content = bytearray()
            async for part in response.aiter_bytes():
                content.extend(part)
                if len(content) > MAX_BYTES:
                    raise SourceUnavailable("Source response exceeded the size limit")
            return content.decode("utf-8")
    except (httpx.HTTPError, UnicodeError) as exc:
        raise SourceUnavailable(
            "Official source could not be reached; cached records retained"
        ) from exc


class GLOProvider:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory
        self.lock = asyncio.Lock()

    def status(self) -> dict[str, Any]:
        with self.factory() as session:
            state = session.get(SourceState, SOURCE)
            last = state.last_success if state else None
            return {
                "id": SOURCE,
                "name": "Texas General Land Office · Public land sales",
                "url": INVENTORY,
                "state": "TX",
                "category": "government_land",
                "status": state.status if state else "not_synced",
                "last_success": last,
                "record_count": state.record_count if state else 0,
                "message": state.message if state else "Awaiting first source sync",
                "stale": last is None or time.time() - last > REFRESH_SECONDS,
                "coverage_note": (
                    "Texas GLO public-sale tracts only. Not all Texas properties, tax sales, "
                    "or foreclosures. Other states are not connected yet."
                ),
            }

    async def refresh(self) -> dict[str, Any]:
        if self.lock.locked():
            return self.status()
        async with self.lock:
            with self.factory() as session:
                initial_state = session.get(SourceState, SOURCE) or SourceState(id=SOURCE)
                initial_state.status, initial_state.message, initial_state.last_attempt = (
                    "syncing",
                    "Refreshing official inventory",
                    int(time.time()),
                )
                session.add(initial_state)
                session.commit()
                previous = {
                    x.id: x.payload
                    for x in session.scalars(select(Listing).where(Listing.source == SOURCE))
                }
            try:
                async with (
                    asyncio.timeout(180),
                    httpx.AsyncClient(
                        timeout=httpx.Timeout(15, connect=5),
                        follow_redirects=False,
                        headers={
                            "User-Agent": (
                                "LandWolfBeta/0.2 (+https://github.com/lupu-spec/Landwolf; "
                                "support.landwolf@gmail.com)"
                            ),
                            "Accept": "text/html",
                        },
                    ) as client,
                ):
                    records = parse_inventory(await fetch_text(client, INVENTORY), stamp())
                    # Low-volume official inventory; sequential detail requests protect the source.
                    for record in records:
                        try:
                            record = record.model_copy(
                                update=parse_detail(await fetch_text(client, record.source_url))
                            )
                        except SourceUnavailable:
                            cached = previous.get(record.id, {})
                            for key in (
                                "latitude",
                                "longitude",
                                "legal_description",
                                "location_description",
                                "source_account",
                                "detail_retrieved_at",
                                "data_completeness",
                            ):
                                if key in cached:
                                    setattr(record, key, cached[key])
                        previous[record.id] = PropertyRecord.model_validate(
                            record.model_dump()
                        ).model_dump()
                        await asyncio.sleep(0.1)
                with self.factory() as session, session.begin():
                    # Only a complete inventory can deactivate missing listings.
                    session.execute(
                        update(Listing).where(Listing.source == SOURCE).values(active=False)
                    )
                    for record in records:
                        item = session.get(Listing, record.id) or Listing(
                            id=record.id, source=SOURCE
                        )
                        item.payload, item.active = previous[record.id], True
                        session.add(item)
                    state = session.get(SourceState, SOURCE)
                    if state is None:
                        raise SourceUnavailable("Source state missing")
                    state.last_success = int(time.time())
                    state.record_count = len(records)
                    state.status, state.message = (
                        "ready",
                        "Official inventory refreshed; verify availability with seller",
                    )
            except (SourceUnavailable, TimeoutError) as exc:
                with self.factory() as session, session.begin():
                    state = session.get(SourceState, SOURCE)
                    if state is not None:
                        state.status = "unavailable"
                        state.message = (
                            "Source temporarily unavailable. Last successful records retained; "
                            "availability must be rechecked."
                        )
                LOGGER.warning("Source refresh failed: %s", type(exc).__name__)
            return self.status()

    async def run(self) -> None:
        while True:
            if self.status()["stale"]:
                await self.refresh()
            await asyncio.sleep(REFRESH_SECONDS)
