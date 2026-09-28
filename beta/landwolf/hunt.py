"""Deterministic, source-backed Hunt matching. No paid enrichment or model calls."""

import hashlib
import json
import math
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import Field, model_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from landwolf.db import Hunt, HuntEvent, HuntMatch, Listing, SourceState
from landwolf.schemas import Contract, PropertyRecord
from landwolf.states import state_code

MAX_HUNTS = 3
MAX_CANDIDATES = 20000
FRESH_SECONDS = 12 * 3600


class Criteria(Contract):
    mode: Literal["fixed", "auction"]
    states: list[str] = Field(default_factory=list, max_length=50)
    county: str | None = Field(default=None, max_length=100)
    center_lat: float | None = Field(default=None, ge=-90, le=90)
    center_lon: float | None = Field(default=None, ge=-180, le=180)
    radius_miles: float | None = Field(default=None, gt=0, le=500)
    min_acres: float = Field(gt=0, le=10_000_000)
    max_acres: float = Field(gt=0, le=10_000_000)
    preferred_min: float | None = Field(default=None, gt=0, le=10_000_000)
    preferred_max: float | None = Field(default=None, gt=0, le=10_000_000)
    max_price: float | None = Field(default=None, gt=0, le=1_000_000_000)
    max_price_per_acre: float | None = Field(default=None, gt=0, le=1_000_000_000)

    @model_validator(mode="after")
    def valid(self) -> Self:
        if self.max_acres < self.min_acres:
            raise ValueError("Maximum acreage must be at least minimum acreage")
        if len(set(self.states)) != len(self.states):
            raise ValueError("States must be unique")
        self.states = [state_code(s) for s in self.states]
        if self.county and len(self.states) != 1:
            raise ValueError("County requires exactly one state")
        if any(v is not None for v in (self.center_lat, self.center_lon, self.radius_miles)):
            if any(v is None for v in (self.center_lat, self.center_lon, self.radius_miles)):
                raise ValueError("Radius requires center latitude, longitude and miles")
            if self.county or self.states:
                raise ValueError("Choose radius or states/counties")
        low = self.preferred_min if self.preferred_min is not None else self.min_acres
        high = self.preferred_max if self.preferred_max is not None else self.max_acres
        if not self.min_acres <= low <= high <= self.max_acres:
            raise ValueError("Preferred acreage must lie within the allowed range")
        if self.mode == "auction" and self.max_price_per_acre is not None:
            raise ValueError("Auction opening bids cannot be ranked by price per acre")
        return self


class HuntInput(Contract):
    name: str = Field(min_length=1, max_length=80)
    criteria: Criteria


class HuntUpdate(Contract):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    criteria: Criteria | None = None
    active: bool | None = None


def distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a, b = math.radians(lat1), math.radians(lat2)
    dlat, dlon = b - a, math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlon / 2) ** 2
    return 3958.7613 * 2 * math.asin(min(1, math.sqrt(h)))


def evaluate(
    record: PropertyRecord,
    criteria: Criteria,
    source: SourceState | None,
    *,
    now: int | None = None,
) -> dict[str, Any]:
    """Three-valued eligibility: known failures exclude; missing evidence goes to review."""
    now = int(time.time()) if now is None else now
    failures: list[str] = []
    missing: list[str] = []
    if not record.active or record.sale_status == "Pre-foreclosure notice":
        failures.append("Not an active land sale")
    if criteria.states and record.state not in criteria.states:
        failures.append("Outside selected states")
    if criteria.county and (record.county or "").casefold() != criteria.county.casefold():
        (missing if not record.county else failures).append("County")
    if record.acres is None:
        missing.append("Acreage")
    elif not criteria.min_acres <= record.acres <= criteria.max_acres:
        failures.append("Acreage outside range")
    price_kind = "Published sale price" if criteria.mode == "fixed" else "Minimum bid"
    if record.price_kind != price_kind or record.asking_price is None:
        missing.append("Required price basis")
    elif criteria.max_price is not None and record.asking_price > criteria.max_price:
        failures.append("Price exceeds limit")
    if (
        criteria.max_price_per_acre is not None
        and record.acres is not None
        and record.asking_price is not None
        and record.price_kind == price_kind
        and record.asking_price / record.acres > criteria.max_price_per_acre
    ):
        failures.append("Price per acre exceeds limit")
    distance = None
    if criteria.radius_miles is not None:
        if record.latitude is None or record.longitude is None:
            missing.append("Source location")
        else:
            if criteria.center_lat is None or criteria.center_lon is None:
                raise ValueError("Validated Hunt center is missing")
            distance = distance_miles(
                criteria.center_lat, criteria.center_lon, record.latitude, record.longitude
            )
            if distance > criteria.radius_miles:
                failures.append("Outside radius")
    if record.category in {"foreclosure", "pre_foreclosure"}:
        missing.append("Unimproved land classification")
    if (
        source is None
        or source.status == "unavailable"
        or source.last_success is None
        or now - source.last_success > FRESH_SECONDS
    ):
        missing.append("Recent source confirmation")
    if (
        record.auction_date
        and record.auction_date.isoformat() < datetime.fromtimestamp(now, UTC).date().isoformat()
    ):
        failures.append("Auction date passed")
    if (
        record.bidding_deadline
        and record.bidding_deadline.isoformat()
        < datetime.fromtimestamp(now, UTC).date().isoformat()
    ):
        failures.append("Bid deadline passed")
    if failures:
        return {"eligibility": "excluded", "reasons": failures, "score": None}
    if missing:
        return {"eligibility": "needs_review", "reasons": missing, "score": None}
    if record.acres is None or record.asking_price is None:
        raise ValueError("Eligible listing lacks required facts")
    low = criteria.preferred_min or criteria.min_acres
    high = criteria.preferred_max or criteria.max_acres
    if low <= record.acres <= high:
        acreage = 100.0
    elif record.acres < low:
        acreage = 50 + 50 * (record.acres - criteria.min_acres) / (low - criteria.min_acres)
    else:
        acreage = 50 + 50 * (criteria.max_acres - record.acres) / (criteria.max_acres - high)
    parts: dict[str, tuple[int, float]] = {
        "acreage": (60 if criteria.mode == "auction" else 25, acreage)
    }
    if distance is not None and criteria.radius_miles is not None:
        parts["proximity"] = (
            40 if criteria.mode == "auction" else 15,
            100 - 50 * distance / criteria.radius_miles,
        )
    if criteria.mode == "fixed":
        if criteria.max_price is not None:
            parts["asking_price"] = (25, 100 - 50 * record.asking_price / criteria.max_price)
        if criteria.max_price_per_acre is not None:
            parts["price_per_acre"] = (
                35,
                100 - 50 * (record.asking_price / record.acres) / criteria.max_price_per_acre,
            )
    # Half-up for nonnegative scores; Python round uses ties-to-even.
    score = math.floor(
        sum(w * v for w, v in parts.values()) / sum(w for w, _ in parts.values()) + 0.5
    )
    return {
        "eligibility": "eligible",
        "score": score,
        "components": {key: round(value, 2) for key, (_, value) in parts.items()},
        "reasons": ["Fits confirmed criteria"],
        "distance_miles": distance,
    }


def refresh(session: Session, hunt: Hunt, *, now: int | None = None) -> dict[str, Any]:
    """Evaluate a bounded catalog snapshot and publish idempotent in-app changes."""
    now = int(time.time()) if now is None else now
    criteria = Criteria.model_validate(hunt.criteria)
    rows = session.scalars(
        select(Listing)
        .where(Listing.active.is_(True))
        .order_by(Listing.id)
        .limit(MAX_CANDIDATES + 1)
    ).all()
    if len(rows) > MAX_CANDIDATES:
        raise ValueError("Catalog exceeds Hunt beta evaluation limit")
    sources = {s.id: s for s in session.scalars(select(SourceState))}
    previous = {
        m.listing_id: m
        for m in session.scalars(select(HuntMatch).where(HuntMatch.hunt_id == hunt.id))
    }
    matches: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for item in rows:
        record = PropertyRecord.model_validate(item.payload)
        result = evaluate(record, criteria, sources.get(item.source), now=now)
        if result["eligibility"] == "excluded":
            continue
        entry = {
            "listing_id": item.id,
            "title": record.title,
            "state": record.state,
            "county": record.county,
            "acres": record.acres,
            "amount": record.asking_price,
            "price_kind": record.price_kind,
            **result,
        }
        if result["eligibility"] == "needs_review":
            review.append(entry)
            continue
        matches.append(entry)
        cents = round(record.asking_price * 100) if record.asking_price is not None else None
        fingerprint = hashlib.sha256(
            json.dumps([hunt.revision, item.id, result["score"], cents]).encode()
        ).hexdigest()
        old = previous.pop(item.id, None)
        if old is None:
            session.add(
                HuntMatch(
                    hunt_id=hunt.id,
                    listing_id=item.id,
                    revision=hunt.revision,
                    score=result["score"],
                    price_cents=cents,
                    fingerprint=fingerprint,
                    updated_at=now,
                )
            )
            if now > hunt.created_at and result["score"] >= 80:
                session.add(
                    HuntEvent(
                        id=str(uuid.uuid4()),
                        hunt_id=hunt.id,
                        listing_id=item.id,
                        revision=hunt.revision,
                        kind="new_match",
                        message="New to your Hunt",
                        created_at=now,
                    )
                )
        else:
            if (
                criteria.mode == "fixed"
                and old.revision == hunt.revision
                and old.price_cents is not None
                and cents is not None
                and cents <= old.price_cents * 0.95
                and old.price_cents - cents >= 100000
                and result["score"] >= 80
            ):
                session.add(
                    HuntEvent(
                        id=str(uuid.uuid4()),
                        hunt_id=hunt.id,
                        listing_id=item.id,
                        revision=hunt.revision,
                        kind="price_drop",
                        message="Published asking price decreased at least 5% and $1,000",
                        created_at=now,
                    )
                )
            old.score, old.price_cents, old.fingerprint, old.updated_at = (
                result["score"],
                cents,
                fingerprint,
                now,
            )
    for old in previous.values():
        session.delete(old)
    matches.sort(key=lambda r: (-r["score"], r["listing_id"]))
    return {
        "matches": matches,
        "needs_review": review,
        "evaluated_at": now,
        "coverage_note": (
            "Connected public inventory only; source coverage is partial. "
            "No valuation or parcel-level access/flood conclusion."
        ),
    }


def remove_hunt(session: Session, hunt: Hunt) -> None:
    session.execute(delete(HuntEvent).where(HuntEvent.hunt_id == hunt.id))
    session.execute(delete(HuntMatch).where(HuntMatch.hunt_id == hunt.id))
    session.delete(hunt)
