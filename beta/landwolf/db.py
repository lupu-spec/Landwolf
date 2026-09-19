"""Versioned, additive beta migrations; never touches legacy application tables."""

import time
from collections.abc import Iterator
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    insert,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class SchemaVersion(Base):
    __tablename__ = "lw2_schema_version"
    version: Mapped[int] = mapped_column(primary_key=True)


class Account(Base):
    __tablename__ = "lw2_accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[int] = mapped_column(default=lambda: int(time.time()))


class LoginSession(Base):
    __tablename__ = "lw2_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)
    last_seen: Mapped[int] = mapped_column(Integer)


class RateBucket(Base):
    __tablename__ = "lw2_rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class Listing(Base):
    __tablename__ = "lw2_listings"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class SourceState(Base):
    __tablename__ = "lw2_sources"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    last_success: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_attempt: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="not_synced")
    message: Mapped[str] = mapped_column(String(300), default="Awaiting first source sync")
    record_count: Mapped[int] = mapped_column(Integer, default=0)


class SavedProperty(Base):
    __tablename__ = "lw2_saved_properties"
    account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), primary_key=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("lw2_listings.id"), primary_key=True)
    created_at: Mapped[int] = mapped_column(default=lambda: int(time.time()))


class SavedRecord(Base):
    """Account-owned research context. Never published into the source inventory."""

    __tablename__ = "lw2_saved_records"
    __table_args__ = (UniqueConstraint("account_id", "listing_id"),)
    account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    listing_id: Mapped[str | None] = mapped_column(ForeignKey("lw2_listings.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    research_location: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()))
    updated_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()))


SCHEMA_VERSION = 2


def database(url: str) -> tuple[Engine, sessionmaker[Session]]:
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 15}
    engine = create_engine(url, **kwargs)
    return engine, sessionmaker(engine, expire_on_commit=False)


def initialize(engine: Engine) -> None:
    """Bootstrap or migrate v1 → v2 atomically; retain all old bookmark rows."""
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            # sqlite's legacy driver does not start a transaction for DDL.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            connection.execute(text("SELECT pg_advisory_xact_lock(1947202602)"))
        versions = (
            connection.scalars(select(SchemaVersion.version)).all()
            if inspect(connection).has_table(SchemaVersion.__tablename__)
            else []
        )
        if versions not in ([], [1], [SCHEMA_VERSION]):
            raise RuntimeError("Unsupported beta schema version; migration required")
        Base.metadata.create_all(connection)
        if not versions:
            connection.execute(insert(SchemaVersion).values(version=SCHEMA_VERSION))
        elif versions == [1]:
            connection.execute(
                insert(SavedRecord).from_select(
                    [
                        "account_id",
                        "id",
                        "listing_id",
                        "title",
                        "created_at",
                        "updated_at",
                        "revision",
                    ],
                    select(
                        SavedProperty.account_id,
                        SavedProperty.listing_id,
                        SavedProperty.listing_id,
                        Listing.payload["title"].as_string(),
                        SavedProperty.created_at,
                        SavedProperty.created_at,
                        text("1"),
                    ).join(Listing, Listing.id == SavedProperty.listing_id),
                )
            )
            connection.execute(update(SchemaVersion).values(version=SCHEMA_VERSION))


def session_dependency(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
