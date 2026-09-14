"""Contracts reject unknown keys, non-finite values, and unbounded workloads."""

import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Credentials(Contract):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128, repr=False)


class PropertyRecord(Contract):
    id: str
    source: Literal["tx_glo_public"] = "tx_glo_public"
    source_name: str = "Texas General Land Office"
    source_url: str
    tract: str
    title: str
    state: Literal["TX"] = "TX"
    county: str
    acres: float = Field(gt=0, le=10_000_000)
    asking_price: float = Field(ge=0, le=1_000_000_000)
    price_kind: Literal["Published sale price"] = "Published sale price"
    category: Literal["government_land"] = "government_land"
    image_url: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    legal_description: str | None = None
    location_description: str | None = None
    source_account: str | None = None
    retrieved_at: str
    detail_retrieved_at: str | None = None
    data_completeness: int = Field(default=60, ge=0, le=100)
    active: bool = True
    risk_notes: list[str] = Field(
        default_factory=lambda: [
            "Title, surviving liens, access, utilities and occupancy "
            "have not been independently verified.",
            "A published listing is not a guarantee of availability or a clear title.",
            "Map points are source-reported locations, not surveyed parcel boundaries.",
        ]
    )


class SearchQuery(Contract):
    state: str = Field(default="TX", min_length=2, max_length=2)
    location: str = Field(default="", max_length=100)
    category: Literal["all", "government_land", "tax_sale", "foreclosure", "surplus"] = "all"
    min_acres: float = Field(default=0, ge=0, le=10_000_000)
    max_price: float | None = Field(default=None, ge=0, le=1_000_000_000)
    sort: Literal["price_asc", "price_desc", "acres_desc", "county"] = "price_asc"
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=12, ge=1, le=100)
    saved_only: bool = False

    @field_validator("state")
    @classmethod
    def state_code(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z]{2}", value):
            raise ValueError("Use a two-letter state code")
        return value.upper()


class Range(Contract):
    low: float = Field(ge=0, le=1_000_000_000)
    likely: float = Field(ge=0, le=1_000_000_000)
    high: float = Field(ge=0, le=1_000_000_000)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if not self.low <= self.likely <= self.high:
            raise ValueError("Range must satisfy low <= likely <= high")
        return self


class AnalysisInput(Contract):
    purchase_price: float = Field(ge=0, le=1_000_000_000)
    resale: Range
    repairs: Range
    lien_reserve: float = Field(ge=0, le=1_000_000_000)
    closing_costs: float = Field(ge=0, le=1_000_000_000)
    holding_months: int = Field(ge=0, le=120)
    monthly_holding: float = Field(ge=0, le=1_000_000)
    buyer_premium_pct: float = Field(ge=0, le=50)
    selling_cost_pct: float = Field(ge=0, le=50)
    annual_financing_pct: float = Field(ge=0, le=100)
    target_roi_pct: float = Field(ge=0, le=200)
    min_profit: float = Field(ge=0, le=1_000_000_000)
    max_loss_probability_pct: float = Field(ge=0, le=50)
    iterations: int = Field(default=10000, ge=1000, le=25000)
    seed: int = Field(default=847291, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def positive_resale(self) -> Self:
        if self.resale.low <= 0:
            raise ValueError("Resale estimates must be positive")
        return self
