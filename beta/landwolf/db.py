"""Versioned beta migrations; never touches legacy application tables."""

import time
from collections.abc import Iterator
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
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


class ParcelIdentity(Base):
    """A publisher's county-scoped parcel identifier, not a surveyed boundary."""

    __tablename__ = "lw2_parcel_identities"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    state: Mapped[str] = mapped_column(String(2), index=True)
    county: Mapped[str] = mapped_column(String(100))
    parcel_number: Mapped[str] = mapped_column(String(100))


class SaleEvent(Base):
    __tablename__ = "lw2_sale_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    listing_id: Mapped[str] = mapped_column(String(80), index=True)
    parcel_id: Mapped[str | None] = mapped_column(ForeignKey("lw2_parcel_identities.id"))
    source: Mapped[str] = mapped_column(String(40), index=True)
    first_seen: Mapped[int] = mapped_column(Integer)
    last_seen: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class SourceRun(Base):
    """Bounded operational history. No account or raw publisher contact data."""

    __tablename__ = "lw2_source_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    finished_at: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(32))
    record_count: Mapped[int] = mapped_column(Integer)
    removed_count: Mapped[int] = mapped_column(Integer, default=0)
    fingerprint: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(300))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)


class AccountEmail(Base):
    __tablename__ = "lw2_account_email"
    account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), primary_key=True)
    verified_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AccountAction(Base):
    __tablename__ = "lw2_account_actions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class BillingExemption(Base):
    __tablename__ = "lw2_billing_exemptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    granted_by_account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"))
    granted_at: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revoked_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revoked_by_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("lw2_accounts.id"), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint("status IN ('active','revoked','expired')", name="ck_lw2_exemption_status"),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > granted_at", name="ck_lw2_exemption_expiration"
        ),
        Index(
            "ux_lw2_exemption_active_account",
            "account_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index("ix_lw2_exemption_expiry", "expires_at"),
    )


class AdminAuditLog(Base):
    __tablename__ = "lw2_admin_audit_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), index=True)
    target_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("lw2_accounts.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    previous_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, index=True)
    __table_args__ = (
        CheckConstraint(
            "action IN ('billing_exemption_granted','billing_exemption_revoked',"
            "'billing_exemption_expired')",
            name="ck_lw2_admin_audit_action",
        ),
        Index("ix_lw2_admin_audit_actor_created", "actor_account_id", "created_at"),
        Index("ix_lw2_admin_audit_target_created", "target_account_id", "created_at"),
        Index("ix_lw2_admin_audit_action_created", "action", "created_at"),
    )


class FeedbackEnrollment(Base):
    """One lifetime invitation per account; accepting fixes the pilot end date."""

    __tablename__ = "lw2_feedback_enrollments"
    account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), primary_key=True)
    invited_by_account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"))
    invited_at: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16), default="invited")
    terms_version: Mapped[str] = mapped_column(String(40))
    accepted_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    revoked_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint("state IN ('invited','active','revoked')", name="ck_lw2_feedback_state"),
        CheckConstraint(
            "(accepted_at IS NULL AND expires_at IS NULL) OR "
            "(accepted_at IS NOT NULL AND expires_at > accepted_at)",
            name="ck_lw2_feedback_dates",
        ),
    )


class FeedbackResponse(Base):
    __tablename__ = "lw2_feedback_responses"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("lw2_feedback_enrollments.account_id"), primary_key=True
    )
    survey_key: Mapped[str] = mapped_column(String(16), primary_key=True)
    survey_version: Mapped[int] = mapped_column(Integer)
    answers: Mapped[dict[str, Any]] = mapped_column(JSON)
    submitted_at: Mapped[int] = mapped_column(Integer, index=True)
    __table_args__ = (
        CheckConstraint(
            "survey_key IN ('baseline','day14','day30','day60','day85')",
            name="ck_lw2_feedback_survey_key",
        ),
        CheckConstraint("survey_version = 1", name="ck_lw2_feedback_survey_version"),
    )


class FeedbackAudit(Base):
    """Append-only pilot events, separate from the billing audit action contract."""

    __tablename__ = "lw2_feedback_audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"))
    target_account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), index=True)
    action: Mapped[str] = mapped_column(String(16))
    survey_key: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, index=True)
    __table_args__ = (
        CheckConstraint(
            "action IN ('invite','accept','submit','revoke')", name="ck_lw2_feedback_audit"
        ),
    )


class Hunt(Base):
    __tablename__ = "lw2_hunts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    criteria: Mapped[dict[str, Any]] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[int] = mapped_column(Integer)


class HuntMatch(Base):
    __tablename__ = "lw2_hunt_matches"
    hunt_id: Mapped[str] = mapped_column(ForeignKey("lw2_hunts.id"), primary_key=True)
    listing_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[int] = mapped_column(Integer)


class HuntEvent(Base):
    __tablename__ = "lw2_hunt_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hunt_id: Mapped[str] = mapped_column(ForeignKey("lw2_hunts.id"), index=True)
    listing_id: Mapped[str] = mapped_column(String(80))
    revision: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(24))
    message: Mapped[str] = mapped_column(String(240))
    created_at: Mapped[int] = mapped_column(Integer, index=True)


SCHEMA_VERSION = 7


def database(url: str) -> tuple[Engine, sessionmaker[Session]]:
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 15}
    engine = create_engine(url, **kwargs)
    return engine, sessionmaker(engine, expire_on_commit=False)


def initialize(engine: Engine) -> None:
    """Add feedback pilot storage in v7; preserve existing user data."""
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
        if versions not in ([], [1], [2], [3], [4], [5], [6], [SCHEMA_VERSION]):
            raise RuntimeError("Unsupported beta schema version; migration required")
        Base.metadata.create_all(connection)
        # Intentionally irreversible. Do not archive or copy retired Saved data.
        # No CASCADE: unexpected dependents must fail the transaction for review.
        connection.execute(text("DROP TABLE IF EXISTS lw2_saved_records"))
        connection.execute(text("DROP TABLE IF EXISTS lw2_saved_properties"))
        if not versions:
            connection.execute(insert(SchemaVersion).values(version=SCHEMA_VERSION))
        elif versions != [SCHEMA_VERSION]:
            connection.execute(update(SchemaVersion).values(version=SCHEMA_VERSION))


def session_dependency(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
