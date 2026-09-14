"""Version-one beta schema; never touches legacy account/property tables."""

import time
from collections.abc import Iterator
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, create_engine, select
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


def database(url: str) -> tuple[Engine, sessionmaker[Session]]:
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 15}
    engine = create_engine(url, **kwargs)
    return engine, sessionmaker(engine, expire_on_commit=False)


def initialize(engine: Engine) -> None:
    """Explicit initial bootstrap. Schema upgrades require a future migration."""
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        versions = session.scalars(select(SchemaVersion.version)).all()
        if not versions:
            session.add(SchemaVersion(version=1))
        elif versions != [1]:
            raise RuntimeError("Unsupported beta schema version; migration required")


def session_dependency(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
