"""Saved-property contracts and source-location handoff without invented parcel points."""

import re
from typing import Any, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from sqlalchemy.orm import Session

from landwolf.db import Listing, SavedRecord
from landwolf.schemas import Contract, PropertyRecord


class SavedLocation(Contract):
    address: str | None = Field(default=None, min_length=8, max_length=240)
    latitude: float | None = Field(default=None, ge=-90, le=90, strict=True)
    longitude: float | None = Field(default=None, ge=-180, le=180, strict=True)

    @model_validator(mode="after")
    def one_location(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Supply both latitude and longitude")
        if (self.address is not None) == (self.latitude is not None):
            raise ValueError("Supply an address or coordinates")
        if self.address is not None:
            self.address = self.address.strip()
            if len(self.address) < 8 or any(ord(c) < 32 for c in self.address):
                raise ValueError("Supply a complete street address")
        return self


class SavedEdit(Contract):
    title: str = Field(min_length=1, max_length=300)
    location: SavedLocation

    @field_validator("title")
    @classmethod
    def valid_title(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError("Supply a property name")
        return value


class SavedCreate(SavedEdit):
    manual_id: UUID | None = None
    listing_id: str | None = Field(default=None, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")

    @model_validator(mode="after")
    def one_identity(self) -> Self:
        if (self.manual_id is None) == (self.listing_id is None):
            raise ValueError("Supply a manual ID or listing ID")
        return self


class SavedUpdate(SavedEdit):
    revision: int = Field(ge=1, strict=True)


def source_location(record: PropertyRecord) -> SavedLocation | None:
    if record.latitude is not None and record.longitude is not None:
        return SavedLocation(latitude=record.latitude, longitude=record.longitude)
    # Only full, street-shaped source location text can be an address candidate.
    # Tract IDs, legal descriptions, counties and regional labels are not geocoded.
    value = (record.location_description or "").strip()
    ending = re.search(r"\b([A-Z]{2})(?:,?\s+\d{5}(?:-\d{4})?)?$", value)
    if (
        8 <= len(value) <= 240
        and re.match(r"^\d+[A-Za-z-]*\s+\S", value)
        and ending
        and ending[1] == record.state
        and not any(ord(c) < 32 for c in value)
    ):
        return SavedLocation(address=value)
    return None


def saved_payload(session: Session, entry: SavedRecord) -> dict[str, Any]:
    item = session.get(Listing, entry.listing_id) if entry.listing_id else None
    record = PropertyRecord.model_validate(item.payload) if item else None
    location = (
        SavedLocation.model_validate(entry.research_location)
        if entry.research_location is not None
        else source_location(record)
        if record
        else None
    )
    return {
        "id": entry.id,
        "listing_id": entry.listing_id,
        "title": entry.title,
        "location": location.model_dump() if location else None,
        "location_origin": "user" if entry.research_location is not None else "source",
        "revision": entry.revision,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }
