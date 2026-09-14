"""Independent source snapshots and bounded scheduling for the nationwide catalog."""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from landwolf.db import Listing, SourceState
from landwolf.national import PublicReader, retrieve
from landwolf.provider import REFRESH_SECONDS, GLOProvider, SourceUnavailable
from landwolf.sources import SOURCES, SourceDefinition, matches, safe_link
from landwolf.states import STATES

LOGGER = logging.getLogger(__name__)


class InventoryProvider:
    def __init__(self, factory: sessionmaker[Session], definition: SourceDefinition) -> None:
        self.factory, self.definition = factory, definition
        self.lock = asyncio.Lock()

    def status(self) -> dict[str, Any]:
        d = self.definition
        with self.factory() as session:
            state = session.get(SourceState, d.id)
            last = state.last_success if state else None
            return {
                "id": d.id,
                "name": d.name,
                "url": d.url,
                "states": list(d.states),
                "categories": list(d.categories),
                "automated": True,
                "status": state.status if state else "not_synced",
                "last_success": last,
                "record_count": state.record_count if state else 0,
                "message": state.message if state else "Awaiting first source refresh",
                "stale": last is None or time.time() - last > REFRESH_SECONDS,
                "coverage_note": d.coverage_note,
            }

    async def refresh(self) -> dict[str, Any]:
        if self.lock.locked():
            return self.status()
        async with self.lock:
            source = self.definition.id
            with self.factory() as session, session.begin():
                initial = session.get(SourceState, source) or SourceState(id=source)
                initial.status, initial.message, initial.last_attempt = (
                    "syncing",
                    "Refreshing official inventory",
                    int(time.time()),
                )
                session.add(initial)
            try:
                async with (
                    asyncio.timeout(300),
                    httpx.AsyncClient(
                        timeout=httpx.Timeout(30, connect=8),
                        follow_redirects=False,
                        headers={
                            "User-Agent": "LandWolfBeta/0.2 (+https://github.com/lupu-spec/Landwolf)",
                            "Accept": "text/html",
                        },
                    ) as client,
                ):
                    records = await retrieve(source, PublicReader(source, client))
                if any(r.source != source or not safe_link(r.source_url) for r in records):
                    raise SourceUnavailable("Source provenance failed validation")
                with self.factory() as session, session.begin():
                    # Never replace or deactivate another source's snapshot.
                    session.execute(
                        update(Listing).where(Listing.source == source).values(active=False)
                    )
                    for record in records:
                        item = session.get(Listing, record.id) or Listing(
                            id=record.id, source=source
                        )
                        if item.source != source:
                            raise SourceUnavailable("Source identifier namespace collision")
                        item.payload, item.active = record.model_dump(mode="json"), record.active
                        session.add(item)
                    state = session.get(SourceState, source)
                    if state is None:
                        raise SourceUnavailable("Source state missing")
                    state.status, state.message = (
                        "ready",
                        "Complete official inventory retrieved; confirm sale terms at source",
                    )
                    state.last_success, state.record_count = int(time.time()), len(records)
            except (
                SourceUnavailable,
                TimeoutError,
                httpx.HTTPError,
                ValueError,
                UnicodeError,
            ) as exc:
                with self.factory() as session, session.begin():
                    state = session.get(SourceState, source)
                    if state is not None:
                        state.status = "unavailable"
                        state.message = (
                            "Refresh failed. The last complete snapshot is retained; "
                            "confirm availability at source."
                        )
                LOGGER.warning("Source %s refresh failed: %s", source, type(exc).__name__)
            return self.status()


class Catalog:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory
        self.providers = {
            d.id: GLOProvider(factory) if d.id == "tx_glo_public" else InventoryProvider(factory, d)
            for d in SOURCES
            if d.automated
        }

    def statuses(
        self, state: str = "US", category: str = "all", source_id: str | None = None
    ) -> list[dict[str, Any]]:
        result = []
        for d in SOURCES:
            if not matches(d, state, category, source_id):
                continue
            if d.automated:
                status = self.providers[d.id].status()
                status.update(
                    states=list(d.states),
                    categories=list(d.categories),
                    automated=True,
                    coverage_note=d.coverage_note,
                )
            else:
                status = {
                    "id": d.id,
                    "name": d.name,
                    "url": d.url,
                    "states": list(d.states),
                    "categories": list(d.categories),
                    "automated": False,
                    "status": "directory",
                    "record_count": 0,
                    "last_success": None,
                    "stale": False,
                    "message": "Source link only; no records imported",
                    "coverage_note": d.coverage_note,
                }
            result.append(status)
        return result

    def coverage(self) -> list[dict[str, Any]]:
        today = datetime.now(UTC).date().isoformat()
        with self.factory() as session:
            state_field = Listing.payload["state"].as_string()
            counts = {
                str(code): int(count)
                for code, count in session.execute(
                    select(state_field, func.count())
                    .where(Listing.active.is_(True), *current_sale_conditions(today))
                    .group_by(state_field)
                ).all()
            }
        return [
            {
                "state": code,
                "name": name,
                "record_count": counts.get(code, 0),
                "directory_url": "https://www.usa.gov/states/" + name.lower().replace(" ", "-"),
                "feed_ids": [d.id for d in SOURCES if d.automated and code in d.states],
            }
            for code, name in STATES.items()
        ]

    async def refresh(self) -> list[dict[str, Any]]:
        slots = asyncio.Semaphore(2)

        async def one(source: str) -> None:
            async with slots:
                try:
                    await self.providers[source].refresh()
                except SQLAlchemyError as exc:
                    LOGGER.error(
                        "Source %s database refresh failed: %s", source, type(exc).__name__
                    )

        await asyncio.gather(*(one(source) for source in self.providers))
        return self.statuses()

    async def run(self) -> None:
        while True:
            await self.refresh()
            await asyncio.sleep(REFRESH_SECONDS)


def current_sale_conditions(today: str) -> list[Any]:
    """A published bid deadline takes effect even before the auction event date."""
    return [
        (Listing.payload[key].as_string().is_(None)) | (Listing.payload[key].as_string() >= today)
        for key in ("auction_date", "bidding_deadline")
    ]
