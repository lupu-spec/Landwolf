from typing import Literal
from pydantic import BaseModel, EmailStr, Field
from typing import Any


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SearchRequest(BaseModel):
    city: str | None = None
    state: str | None = Field(default=None, min_length=2, max_length=2)
    county: str | None = None
    min_acres: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    distress_type: str | None = None
    min_data_quality: float | None = Field(default=None, ge=0, le=100)
    limit: int = Field(default=50, ge=1, le=100)


class PropertyOut(BaseModel):
    id: str
    address: str | None
    city: str | None
    state: str
    county: str | None
    zip_code: str | None
    acreage: float | None
    estimated_value: float | None
    annual_taxes: float | None
    property_type: str | None
    distress_type: str | None
    data_quality: float
    latitude: float | None
    longitude: float | None


class SearchPreviewResponse(BaseModel):
    match_count: int
    opportunity_signal: str
    category_summary: list[str]
    acreage_band: str | None = None
    value_band: str | None = None
    message: str
    requires_subscription: bool = True


class SearchResponse(BaseModel):
    results: list[PropertyOut]
    result_count: int
    subscription_status: str


class MeResponse(BaseModel):
    id: str
    email: str
    subscription_status: str


class CheckoutRequest(BaseModel):
    plan: Literal["monthly", "annual"] = "monthly"


class CheckoutResponse(BaseModel):
    checkout_url: str
