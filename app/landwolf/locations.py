"""Source-location handoff without invented parcel points."""

import re
from typing import Self

from pydantic import Field, model_validator

from landwolf.schemas import Contract, PropertyRecord


class ResearchLocation(Contract):
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


def source_location(record: PropertyRecord) -> ResearchLocation | None:
    if record.latitude is not None and record.longitude is not None:
        return ResearchLocation(latitude=record.latitude, longitude=record.longitude)
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
        return ResearchLocation(address=value)
    return None
