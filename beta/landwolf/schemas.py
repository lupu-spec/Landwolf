"""Contracts reject unknown keys, non-finite values, and unbounded workloads."""

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from landwolf.states import state_code

Category = Literal[
    "government_land", "tax_sale", "foreclosure", "pre_foreclosure", "surplus", "public_auction"
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Credentials(Contract):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128, repr=False)


class PropertyRecord(Contract):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    source: str = Field(default="tx_glo_public", max_length=40, pattern=r"^[a-z0-9_]+$")
    source_name: str = Field(default="Texas General Land Office", max_length=160)
    source_url: str = Field(max_length=1000)
    tract: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    state: str = "TX"
    county: str | None = Field(default=None, max_length=100)
    acres: float | None = Field(default=None, gt=0, le=10_000_000)
    asking_price: float | None = Field(default=None, ge=0, le=1_000_000_000)
    reported_taxes: float | None = Field(default=None, ge=0, le=1_000_000_000)
    source_appraised_value: float | None = Field(default=None, ge=0, le=1_000_000_000)
    price_kind: Literal[
        "Published sale price", "Minimum bid", "Government bid", "Not published"
    ] = "Published sale price"
    category: Category = "government_land"
    sale_type: str = Field(default="Public land sale", max_length=100)
    sale_status: Literal[
        "Available",
        "Auction scheduled",
        "Date not announced",
        "Date needs review",
        "Pre-foreclosure notice",
    ] = "Available"
    auction_date: date | None = None
    auction_date_text: str | None = Field(default=None, max_length=80)
    bidding_deadline: date | None = None
    notice_date: date | None = None
    eligibility: str | None = Field(default=None, max_length=500)
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

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str) -> str:
        return state_code(value)

    @model_validator(mode="after")
    def consistent_sale(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Coordinates must be supplied as a pair")
        if self.asking_price is None:
            self.price_kind = "Not published"
        elif self.price_kind == "Not published":
            raise ValueError("A published price requires its price kind")
        if self.sale_status == "Auction scheduled" and self.auction_date is None:
            raise ValueError("Scheduled auctions require a source-published date")
        if (
            self.bidding_deadline
            and self.auction_date
            and self.bidding_deadline > self.auction_date
        ):
            raise ValueError("Bid deadline cannot follow the auction")
        if self.category == "pre_foreclosure" and (
            self.sale_status != "Pre-foreclosure notice" or self.auction_date is not None
        ):
            raise ValueError("A pre-foreclosure notice is not a scheduled sale")
        self.data_completeness = 20 * sum(
            [
                True,
                self.asking_price is not None,
                self.acres is not None,
                bool(self.legal_description or self.location_description),
                self.latitude is not None and self.longitude is not None,
            ]
        )
        return self


class SearchQuery(Contract):
    state: str = Field(default="US", min_length=2, max_length=2)
    location: str = Field(default="", max_length=100)
    category: Literal["all"] | Category = "all"
    source: str | None = Field(default=None, max_length=40, pattern=r"^[a-z0-9_]+$")
    min_acres: float = Field(default=0, ge=0, le=10_000_000)
    max_price: float | None = Field(default=None, ge=0, le=1_000_000_000)
    sort: Literal["price_asc", "price_desc", "acres_desc", "county"] = "price_asc"
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=12, ge=1, le=100)
    saved_only: bool = False

    @field_validator("state")
    @classmethod
    def state_code(cls, value: str) -> str:
        return state_code(value, nationwide=True)


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
    resale_basis: Literal["user_estimate", "bid_scenario", "custom_scenario"] = "user_estimate"
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
