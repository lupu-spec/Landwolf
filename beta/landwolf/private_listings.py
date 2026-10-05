"""Bounded imports of configured, paginated seller feeds with private provenance.

This consumes the documented normalized feed contract. It does not scrape an
unconfigured website or assert rights to another publisher's descriptions/images.
"""

import asyncio
import hashlib
import ipaddress
import json
import random
import time
from datetime import UTC, date, datetime
from typing import Any, Literal, Self
from urllib.parse import urlsplit

import httpx
from pydantic import Field, model_validator
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from landwolf.db import Listing, PrivateListingOrigin, SourceState
from landwolf.schemas import Contract, PropertyRecord
from landwolf.states import STATES
from landwolf.trust import log_run

SOURCE = "private_seller_listings"
LABEL = "Private Seller Listings"
INTERVAL_SECONDS = 12 * 3600
MAX_PAGE_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 1_000_000
MAX_PAGES = 10_000


def public_url(value: str, hosts: list[str]) -> bool:
    """Exact operator-reviewed domains; no credentials, fragments, ports or IPs."""
    try:
        parts = urlsplit(value)
        host = parts.hostname or ""
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        return bool(
            len(value) <= 1000
            and parts.scheme == "https"
            and host in hosts
            and "." in host
            and not host.endswith((".local", ".localhost", ".internal"))
            and not parts.username
            and not parts.password
            and not parts.port
            and not parts.fragment
        )
    except ValueError:
        return False


class FeedConfig(Contract):
    key: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    url: str = Field(max_length=1000, repr=False)
    feed_hosts: list[str] = Field(min_length=1, max_length=10, repr=False)
    original_hosts: list[str] = Field(min_length=1, max_length=2000, repr=False)
    access_reference: str = Field(min_length=1, max_length=300, repr=False)
    required_attribution: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_urls(self) -> Self:
        if not public_url(self.url, self.feed_hosts):
            raise ValueError("Feed endpoint must use a reviewed public HTTPS host")
        if set(self.feed_hosts) & set(self.original_hosts):
            raise ValueError("Acquisition hosts must not be exposed as original seller hosts")
        return self


class SellerListing(Contract):
    external_id: str = Field(min_length=1, max_length=160)
    acquisition_url: str = Field(max_length=1000, repr=False)
    original_listing_url: str = Field(max_length=1000)
    state: str = Field(min_length=2, max_length=2)
    county: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    acres: float | None = Field(default=None, gt=0, le=10_000_000)
    asking_price: float | None = Field(default=None, ge=0, le=1_000_000_000)
    parcel_number: str | None = Field(default=None, min_length=1, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    seller_type: Literal["owner", "agent", "broker", "unknown"] = "unknown"
    listing_agent: str | None = Field(default=None, max_length=160)
    listing_brokerage: str | None = Field(default=None, max_length=160)
    seller_phone: str | None = Field(default=None, max_length=40)
    source_effective_date: date | None = None
    active: bool = True

    def record(self, config: FeedConfig, retrieved_at: str) -> PropertyRecord:
        if not public_url(self.original_listing_url, config.original_hosts):
            raise ValueError("Original listing link is not approved for public display")
        if urlsplit(self.original_listing_url).query:
            raise ValueError("Original listing links must omit tracking/query parameters")
        if not public_url(self.acquisition_url, config.feed_hosts):
            raise ValueError("Acquisition URL is outside configured provenance hosts")
        identifier = (
            "ps-" + hashlib.sha256((config.key + "\0" + self.external_id).encode()).hexdigest()
        )
        facts = self.model_dump(
            exclude={"external_id", "acquisition_url", "original_listing_url", "address"}
        )
        # A factual heading avoids republishing marketing copy. Photos retain the
        # application's default artwork until image-display rights are integrated.
        return PropertyRecord(
            **facts,
            id=identifier,
            tract=identifier[3:15],
            title=self.address or f"Land listing in {self.county or self.state}",
            location_description=self.address,
            source=SOURCE,
            source_name=LABEL,
            source_url=self.original_listing_url,
            category="private_seller",
            sale_type="Private market listing",
            attribution=config.required_attribution,
            retrieved_at=retrieved_at,
        )


class FeedPage(Contract):
    snapshot_id: str = Field(min_length=1, max_length=160)
    total: int = Field(ge=0, le=MAX_RECORDS)
    complete: bool
    next_url: str | None = Field(default=None, max_length=1000, repr=False)
    listings: list[SellerListing] = Field(max_length=1000)

    @model_validator(mode="after")
    def pagination(self) -> Self:
        if self.complete != (self.next_url is None):
            raise ValueError("Only the terminal page may declare a complete snapshot")
        if not self.complete and not self.listings:
            raise ValueError("An intermediate page must advance the inventory")
        return self


def load_configs(raw: str) -> list[FeedConfig]:
    if len(raw) > 1_000_000:
        raise ValueError("Feed configuration exceeds the supported size")
    values = json.loads(raw)
    if not isinstance(values, list) or len(values) > 50:
        raise ValueError("Expected at most 50 feed configurations")
    configs = [FeedConfig.model_validate(value) for value in values]
    if len({config.key for config in configs}) != len(configs):
        raise ValueError("Feed keys must be unique")
    return configs


async def fetch_page(client: httpx.AsyncClient, url: str, config: FeedConfig) -> FeedPage:
    if not public_url(url, config.feed_hosts):
        raise ValueError("Pagination left the reviewed feed hosts")
    # A 401/403 or an interactive block is terminal. Only transient server
    # failures and explicit short Retry-After rate limits receive bounded retries.
    for attempt in range(3):
        async with client.stream("GET", url, follow_redirects=False) as response:
            retry_after = response.headers.get("retry-after", "")
            rate_delay = (
                int(retry_after) if retry_after.isdigit() and len(retry_after) < 5 else None
            )
            retryable = response.status_code in {500, 502, 503, 504} or (
                response.status_code == 429 and rate_delay is not None and rate_delay <= 60
            )
            if retryable and attempt < 2:
                delay = rate_delay if response.status_code == 429 else 2**attempt
            else:
                response.raise_for_status()
                if response.headers.get("content-type", "").split(";")[0] != "application/json":
                    raise ValueError("Expected a normalized JSON listing feed")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_PAGE_BYTES:
                        raise ValueError("Feed page exceeded the response limit")
                return FeedPage.model_validate_json(body)
        # Jitter spreads load; it does not impersonate user interaction.
        await asyncio.sleep(float(delay or 0) + random.uniform(0, 0.25))  # nosec B311
    raise ValueError("Feed retry budget exhausted")


def upsert(session: Session, model: Any, rows: list[dict[str, Any]], key: str) -> None:
    if not rows:
        return
    dialect = session.get_bind().dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        raise ValueError("Unsupported ingestion database")
    insert = pg_insert if dialect == "postgresql" else sqlite_insert
    # Keep SQL parameters below SQLite's bound even with a 1,000-record feed page.
    for offset in range(0, len(rows), 100):
        statement = insert(model).values(rows[offset : offset + 100])
        session.execute(
            statement.on_conflict_do_update(
                index_elements=[key],
                set_={name: getattr(statement.excluded, name) for name in rows[0] if name != key},
            )
        )


async def import_feed(
    factory: sessionmaker[Session], config: FeedConfig, client: httpx.AsyncClient
) -> int:
    """Publish only a complete validated snapshot; any error rolls back all changes.

    The database transaction lock also serializes separate scheduler processes.
    Other feeds' rows and billing/account data are never replaced by this operation.
    """
    retrieved_at = datetime.now(UTC).isoformat()
    with factory() as session, session.begin():
        if session.get_bind().dialect.name == "postgresql":
            acquired = session.scalar(text("SELECT pg_try_advisory_xact_lock(1947202609)"))
            if not acquired:
                raise ValueError("Another private listing import is already running")
        else:
            session.execute(text("BEGIN IMMEDIATE"))
        owned = select(PrivateListingOrigin.listing_id).where(
            PrivateListingOrigin.provider_key == config.key
        )
        previous = int(
            session.scalar(
                select(func.count())
                .select_from(Listing)
                .where(Listing.id.in_(owned), Listing.active.is_(True))
            )
            or 0
        )
        session.execute(update(Listing).where(Listing.id.in_(owned)).values(active=False))
        seen_urls: set[str] = set()
        snapshot: str | None = None
        total: int | None = None
        count = 0
        url = config.url
        async with asyncio.timeout(1800):
            for _ in range(MAX_PAGES):
                if url in seen_urls:
                    raise ValueError("Feed pagination repeated a page")
                seen_urls.add(url)
                page = await fetch_page(client, url, config)
                if snapshot is None:
                    snapshot, total = page.snapshot_id, page.total
                    # Replaying an already committed snapshot is idempotent. The
                    # seen-ID guard below still validates the full feed on retries.
                    session.execute(
                        update(PrivateListingOrigin)
                        .where(PrivateListingOrigin.provider_key == config.key)
                        .values(snapshot_id="")
                    )
                if page.snapshot_id != snapshot or page.total != total:
                    raise ValueError("Feed changed snapshot during pagination")
                records = [item.record(config, retrieved_at) for item in page.listings]
                identifiers = [record.id for record in records]
                if len(set(identifiers)) != len(identifiers) or session.scalar(
                    select(PrivateListingOrigin.listing_id)
                    .where(
                        PrivateListingOrigin.listing_id.in_(identifiers),
                        PrivateListingOrigin.snapshot_id == snapshot,
                    )
                    .limit(1)
                ):
                    raise ValueError("Duplicate feed identifiers")
                upsert(
                    session,
                    Listing,
                    [
                        {
                            "id": record.id,
                            "source": SOURCE,
                            "active": record.active,
                            "payload": record.model_dump(mode="json"),
                        }
                        for record in records
                    ],
                    "id",
                )
                upsert(
                    session,
                    PrivateListingOrigin,
                    [
                        {
                            "listing_id": record.id,
                            "provider_key": config.key,
                            "external_id": item.external_id,
                            "acquisition_url": item.acquisition_url,
                            "access_reference": config.access_reference,
                            "snapshot_id": snapshot,
                        }
                        for record, item in zip(records, page.listings, strict=True)
                    ],
                    "listing_id",
                )
                count += len(records)
                if count > page.total:
                    raise ValueError("Feed exceeded its declared total")
                if page.complete:
                    if count != page.total:
                        raise ValueError("Feed ended before its declared total")
                    remaining = int(
                        session.scalar(
                            select(func.count())
                            .select_from(Listing)
                            .where(Listing.id.in_(owned), Listing.active.is_(True))
                        )
                        or 0
                    )
                    if previous and remaining < previous / 2:
                        raise ValueError("Large inventory removal requires source review")
                    break
                if not page.next_url:
                    raise ValueError("Feed pagination did not terminate correctly")
                url = page.next_url
                await asyncio.sleep(random.uniform(0.25, 0.5))  # nosec B311
            else:
                raise ValueError("Feed exceeded the bounded page budget")
    return count


async def sync(factory: sessionmaker[Session], raw: str) -> int:
    configs = load_configs(raw)
    if not configs:
        raise ValueError("No configured private listing feeds configured")
    count = 0
    now = int(time.time())
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30, connect=8),
            follow_redirects=False,
            headers={
                "User-Agent": "LandWolf/1.0 (+https://landwolf.ai)",
                "Accept": "application/json",
            },
        ) as client:
            for config in configs:
                count += await import_feed(factory, config, client)
    except (ValueError, TimeoutError, httpx.HTTPError):
        finish_status(factory, now, False)
        raise
    finish_status(factory, now, True)
    return count


def finish_status(factory: sessionmaker[Session], attempted_at: int, success: bool) -> None:
    with factory() as session, session.begin():
        state = session.get(SourceState, SOURCE) or SourceState(id=SOURCE)
        state.last_attempt = attempted_at
        if success:
            state.last_success = int(time.time())
        state.status = "ready" if success else "unavailable"
        state.record_count = int(
            session.scalar(
                select(func.count())
                .select_from(Listing)
                .where(Listing.source == SOURCE, Listing.active.is_(True))
            )
            or 0
        )
        state.message = (
            "Private market feeds refreshed; confirm availability with the listing representative."
            if success
            else "A private market feed did not complete. Its last complete inventory is retained."
        )
        session.add(state)
        log_run(session, SOURCE, state.status, state.record_count, state.message)


def status(factory: sessionmaker[Session]) -> dict[str, Any]:
    with factory() as session:
        row = session.get(SourceState, SOURCE)
        last = row.last_success if row else None
        return {
            "id": SOURCE,
            "name": LABEL,
            "url": "",
            "states": list(STATES),
            "categories": ["private_seller"],
            "automated": True,
            "status": row.status if row else "not_connected",
            "last_success": last,
            "last_attempt": row.last_attempt if row else None,
            "record_count": row.record_count if row else 0,
            "stale": last is None or time.time() - last > INTERVAL_SECONDS,
            "refresh_interval_hours": 12,
            "full_county_coverage": False,
            "message": row.message if row else "No private seller feed is connected yet.",
            "coverage_note": (
                "Owner, agent and broker listings across supported feeds; "
                "coverage varies by location."
            ),
            "reuse_note": "Listing representative and required attribution are preserved.",
        }
