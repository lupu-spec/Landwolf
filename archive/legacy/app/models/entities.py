import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    free_searches_used: Mapped[int] = mapped_column(Integer, default=0)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    subscription_status: Mapped[str] = mapped_column(String(50), default="none")
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    last_stripe_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_stripe_event_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_stripe_event_created: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_parcel_id: Mapped[str | None] = mapped_column(String(255), index=True)
    address: Mapped[str | None] = mapped_column(String(500), index=True)
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(2), index=True)
    county: Mapped[str | None] = mapped_column(String(120), index=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), index=True)
    acreage: Mapped[float | None] = mapped_column(Float)
    estimated_value: Mapped[float | None] = mapped_column(Float)
    annual_taxes: Mapped[float | None] = mapped_column(Float)
    property_type: Mapped[str | None] = mapped_column(String(80))
    distress_type: Mapped[str | None] = mapped_column(String(80), index=True)
    data_quality: Mapped[float] = mapped_column(Float, default=0)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)


class SearchEvent(Base):
    __tablename__ = "search_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    query_json: Mapped[dict] = mapped_column(JSON)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stripe_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120))
    stripe_created: Mapped[int] = mapped_column(BigInteger, index=True)
    customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    processing_result: Mapped[str] = mapped_column(String(50), default="applied")
    payload: Mapped[dict] = mapped_column(JSON)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
