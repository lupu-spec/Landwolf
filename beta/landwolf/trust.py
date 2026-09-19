"""Conservative parcel identity, field provenance and atomic inventory review gates."""

import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from landwolf.db import Listing, ParcelIdentity, SaleEvent, SourceRun, SourceState
from landwolf.framework import Evidence
from landwolf.schemas import PropertyRecord

FRESHNESS_SECONDS = 6 * 3600
HISTORY_LIMIT = 40


def parcel_key(record: PropertyRecord) -> str | None:
    # Never merge parcels from coordinates, street names, tract IDs or agency account IDs.
    # Preserve APN punctuation and leading zeros; jurisdiction-specific rules differ.
    if not record.county or not record.parcel_number:
        return None
    key = [record.state, " ".join(record.county.casefold().split()), record.parcel_number.strip()]
    return hashlib.sha256(json.dumps(key).encode()).hexdigest()


def fingerprint(records: list[PropertyRecord]) -> str:
    stable = [
        record.model_dump(mode="json", exclude={"retrieved_at", "detail_retrieved_at"})
        for record in sorted(records, key=lambda item: item.id)
    ]
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()


def log_run(
    session: Session,
    source: str,
    status: str,
    count: int,
    message: str,
    *,
    checksum: str = "",
    removed: int = 0,
) -> None:
    session.add(
        SourceRun(
            source=source,
            finished_at=int(time.time()),
            status=status,
            record_count=count,
            removed_count=removed,
            fingerprint=checksum,
            message=message,
        )
    )
    session.flush()
    older = list(
        session.scalars(
            select(SourceRun.id)
            .where(SourceRun.source == source)
            .order_by(SourceRun.finished_at.desc(), SourceRun.id.desc())
            .offset(HISTORY_LIMIT)
        )
    )
    if older:
        session.execute(delete(SourceRun).where(SourceRun.id.in_(older)))


def publish_snapshot(session: Session, source: str, records: list[PropertyRecord]) -> bool:
    """Caller owns the transaction. Quarantine anomalies without replacing good data."""
    if len(records) > 5000 or len({item.id for item in records}) != len(records):
        raise ValueError("Duplicate identifiers or oversized inventory")
    if any(item.source != source for item in records):
        raise ValueError("Source identifier namespace mismatch")
    now = int(time.time())
    today = datetime.now(UTC).date()
    previous = list(session.scalars(select(Listing).where(Listing.source == source)))
    current = {item.id: item for item in records}
    still_current = []
    for item in previous:
        old = PropertyRecord.model_validate(item.payload)
        if item.active and all(
            day is None or day >= today for day in (old.auction_date, old.bidding_deadline)
        ):
            still_current.append(old)
    missing = sum(item.id not in current or not current[item.id].active for item in still_current)
    price_changes = sum(
        item.asking_price is not None
        and item.asking_price > 0
        and item.id in current
        and current[item.id].asking_price is not None
        and abs(float(current[item.id].asking_price or 0) / item.asking_price - 1) > 0.5
        for item in still_current
    )
    checksum = fingerprint(records)
    approved = session.scalar(
        select(SourceRun.id)
        .where(
            SourceRun.source == source,
            SourceRun.fingerprint == checksum,
            SourceRun.approved.is_(True),
            SourceRun.finished_at >= now - 86400,
        )
        .limit(1)
    )
    suspicious = (
        (len(still_current) >= 2 and not records)
        or (len(still_current) >= 10 and missing > len(still_current) / 2)
        or price_changes >= 3
    )
    state = session.get(SourceState, source) or SourceState(id=source)
    state.last_attempt = now
    session.add(state)
    if suspicious and not approved:
        state.status = "review_required"
        state.message = "Unusual inventory change held for review; previous records retained."
        log_run(
            session,
            source,
            "review_required",
            len(records),
            state.message,
            checksum=checksum,
            removed=missing,
        )
        return False
    session.execute(update(Listing).where(Listing.source == source).values(active=False))
    session.execute(update(SaleEvent).where(SaleEvent.source == source).values(active=False))
    for record in records:
        item = session.get(Listing, record.id) or Listing(id=record.id, source=source)
        if item.source != source:
            raise ValueError("Source identifier namespace collision")
        item.payload, item.active = record.model_dump(mode="json"), record.active
        session.add(item)
        identity = parcel_key(record)
        if identity and session.get(ParcelIdentity, identity) is None:
            session.add(
                ParcelIdentity(
                    id=identity,
                    state=record.state,
                    county=record.county,
                    parcel_number=record.parcel_number,
                )
            )
            session.flush()
        event_id = hashlib.sha256(
            f"{source}:{record.id}:{record.auction_date or 'direct'}".encode()
        ).hexdigest()
        event = session.get(SaleEvent, event_id) or SaleEvent(
            id=event_id,
            listing_id=record.id,
            source=source,
            first_seen=now,
        )
        event.parcel_id, event.last_seen, event.active = identity, now, record.active
        event.payload = {
            "source_url": record.source_url,
            "auction_date": str(record.auction_date or ""),
            "price_kind": record.price_kind,
            "asking_price": record.asking_price,
        }
        session.add(event)
    state.last_success, state.record_count = now, len(records)
    state.status = "ready"
    state.message = (
        "Complete official inventory retrieved; confirm availability and sale terms at source."
    )
    log_run(
        session, source, "ready", len(records), state.message, checksum=checksum, removed=missing
    )
    # Sale event metadata is retained for one year; account research is never persisted here.
    session.execute(
        delete(SaleEvent).where(
            SaleEvent.active.is_(False), SaleEvent.last_seen < now - 365 * 86400
        )
    )
    return True


def source_history(session: Session, source: str) -> list[dict[str, Any]]:
    return [
        {
            "finished_at": row.finished_at,
            "status": row.status,
            "record_count": row.record_count,
            "removed_count": row.removed_count,
            "message": row.message,
        }
        for row in session.scalars(
            select(SourceRun)
            .where(SourceRun.source == source)
            .order_by(SourceRun.finished_at.desc(), SourceRun.id.desc())
            .limit(5)
        )
    ]


def property_evidence(record: PropertyRecord, state: SourceState | None) -> dict[str, Any]:
    identity = parcel_key(record)
    fields = [
        ("parcel_number", "County parcel number", record.parcel_number),
        ("county", "County", record.county),
        ("acres", "Published acreage", record.acres),
        ("asking_price", record.price_kind, record.asking_price),
        ("reported_taxes", "Published tax balance", record.reported_taxes),
        (
            "source_appraised_value",
            "Source appraisal (not market value)",
            record.source_appraised_value,
        ),
        ("auction_date", "Auction date", str(record.auction_date) if record.auction_date else None),
        (
            "bidding_deadline",
            "Bid deadline",
            str(record.bidding_deadline) if record.bidding_deadline else None,
        ),
        ("latitude", "Published latitude", record.latitude),
        ("longitude", "Published longitude", record.longitude),
    ]
    evidence = []
    for name, label, value in fields:
        detail = record.source == "tx_glo_public" and name in {"latitude", "longitude"}
        evidence.append(
            Evidence(
                field=name,
                label=label,
                value=value,
                basis=(record.acreage_basis if name == "acres" else "reported")
                if value is not None
                else "unknown",
                source_url=record.source_url,
                retrieved_at=(record.detail_retrieved_at if detail else record.retrieved_at),
                effective_date=(
                    record.source_effective_date.isoformat()
                    if record.source_effective_date
                    else None
                ),
                limitation="Retrieval is not a publisher update date. Check the original record.",
            ).model_dump()
        )
    fresh = bool(
        state
        and state.status == "ready"
        and state.last_success
        and time.time() - state.last_success <= FRESHNESS_SECONDS
    )
    return {
        "identity": {
            "id": identity,
            "status": "publisher_parcel_id" if identity else "unresolved",
            "message": "Publisher parcel ID is county-scoped; boundary not independently verified."
            if identity
            else "Parcel identity unresolved. Tract numbers and points do not confirm a parcel.",
        },
        "freshness": "current_retrieval" if fresh else "needs_attention",
        "evidence": evidence,
        "next_steps": [
            "Confirm current availability, eligibility and deadlines with the selling agency.",
            "Match the county parcel and legal description before relying on location research.",
            "Verify title, liens, legal access and intended use with qualified professionals.",
            "Obtain comparable sales and costs before treating a scenario as underwriting.",
        ],
    }
