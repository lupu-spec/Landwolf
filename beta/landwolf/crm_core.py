"""Portable CRM storage and contracts. No LandWolf auth, billing, or network dependencies.

Copy this module into another Python service, initialize its metadata, and inject
its SQLAlchemy Session. The host owns authentication and transaction boundaries.
"""

import hashlib
import re
import secrets
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

INDUSTRIES = {
    "real_estate": "Real estate",
    "construction": "Construction & trades",
    "woodworking": "Woodworking & manufacturing",
    "technology": "Technology & AI",
    "finance": "Finance & lending",
    "professional_services": "Professional services",
    "personal": "Personal use",
    "other": "Other",
}
USES = {
    "investing": "Find investment properties",
    "research": "Research land or property",
    "deal_analysis": "Evaluate deals",
    "client_work": "Support clients",
    "development": "Plan development or construction",
    "personal": "Find land for personal use",
    "exploring": "Explore the tool",
    "other": "Other",
}
STAGES = {
    "registered": "Registered",
    "qualified": "Qualified",
    "contacted": "Contacted",
    "customer": "Customer",
    "inactive": "Inactive",
}
CONTACT_TYPES = {
    "investor": "Investor",
    "agent": "Agent / broker",
    "developer": "Developer / builder",
    "lender": "Lender",
    "business_owner": "Business owner",
    "individual": "Individual",
    "other": "Other",
}
CONSENT_TEXT = "Email me LandWolf product news and offers. I can unsubscribe by contacting support."
CONSENT_VERSION = "landwolf-email-v1"


class CRMBase(DeclarativeBase):
    pass


class Project(CRMBase):
    __tablename__ = "crm_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer)


class Contact(CRMBase):
    __tablename__ = "crm_contacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("crm_projects.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    company: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    job_title: Mapped[str] = mapped_column(String(120), default="")
    industry: Mapped[str] = mapped_column(String(40), default="")
    contact_type: Mapped[str] = mapped_column(String(40), default="")
    primary_use: Mapped[str] = mapped_column(String(40), default="")
    use_details: Mapped[str] = mapped_column(String(1000), default="")
    lifecycle: Mapped[str] = mapped_column(String(24), default="registered", index=True)
    source: Mapped[str] = mapped_column(String(80))
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    consent_recorded_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    follow_up_on: Mapped[str] = mapped_column(String(10), default="")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[int] = mapped_column(Integer, index=True)
    updated_at: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("project_id", "external_id", name="uq_crm_project_identity"),
        UniqueConstraint("project_id", "email", name="uq_crm_project_email"),
        Index("ix_crm_project_created", "project_id", "created_at"),
    )


class Activity(CRMBase):
    __tablename__ = "crm_activities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    contact_id: Mapped[str] = mapped_column(ForeignKey("crm_contacts.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[int] = mapped_column(Integer)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="after")
    @classmethod
    def no_controls(cls, value: Any) -> Any:
        if isinstance(value, str) and any(ord(c) < 32 for c in value):
            raise ValueError("Control characters are not allowed")
        return value


class Profile(Contract):
    full_name: str = Field(min_length=1, max_length=120)
    company: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=32)
    job_title: str = Field(default="", max_length=120)
    industry: str = Field(default="", max_length=40)
    contact_type: str = Field(default="", max_length=40)
    primary_use: str = Field(min_length=1, max_length=40)
    use_details: str = Field(default="", max_length=1000)
    marketing_opt_in: bool = Field(default=False, strict=True)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        if value and (
            not re.fullmatch(r"\+?[0-9 ().-]+", value)
            or not 7 <= sum(c.isdigit() for c in value) <= 15
        ):
            raise ValueError("Use 7–15 digits, with an optional country code")
        return value

    @field_validator("industry", "contact_type", "primary_use")
    @classmethod
    def category_code(cls, value: str) -> str:
        if value and not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", value):
            raise ValueError("Use a category code")
        return value


class Intake(Profile):
    external_id: str = Field(min_length=1, max_length=120)
    email: EmailStr = Field(max_length=254)
    consent_version: str | None = Field(default=None, max_length=80)


class NewProject(Contract):
    id: str = Field(min_length=2, max_length=40, pattern=r"^[a-z][a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=100)


class ContactUpdate(Contract):
    revision: int = Field(ge=1)
    lifecycle: Literal["registered", "qualified", "contacted", "customer", "inactive"]
    tags: list[str] = Field(default_factory=list, max_length=12)
    follow_up_on: str = Field(default="", max_length=10)

    @field_validator("tags")
    @classmethod
    def valid_tags(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(r"[\w -]{1,40}", value) for value in values):
            raise ValueError("Tags must be 1–40 letters, numbers, spaces or hyphens")
        return list(dict.fromkeys(values))

    @field_validator("follow_up_on")
    @classmethod
    def valid_date(cls, value: str) -> str:
        from datetime import date

        if value and date.fromisoformat(value).isoformat() != value:
            raise ValueError("Use YYYY-MM-DD")
        return value


class Note(Contract):
    text: str = Field(min_length=1, max_length=2000)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def record_activity(
    session: Session, contact_id: str, actor: str, kind: str, text: str = ""
) -> None:
    session.add(
        Activity(
            id=str(uuid.uuid4()),
            contact_id=contact_id,
            actor_id=actor,
            kind=kind,
            text=text,
            created_at=int(time.time()),
        )
    )


def capture(session: Session, project_id: str, body: Intake, *, source: str) -> Contact:
    """Idempotent registration ingestion; a retry never overwrites curated CRM data."""
    existing = session.scalar(
        select(Contact).where(
            Contact.project_id == project_id, Contact.external_id == body.external_id
        )
    )
    email = str(body.email).casefold()
    if existing:
        if existing.email != email:
            raise ValueError("Registration identity conflicts with an existing contact")
        return existing
    if session.scalar(
        select(Contact.id).where(Contact.project_id == project_id, Contact.email == email)
    ):
        raise ValueError("Registration identity conflicts with an existing contact")
    if body.marketing_opt_in and not body.consent_version:
        raise ValueError("Consent wording version is required for marketing opt-in")
    now = int(time.time())
    contact = Contact(
        id=str(uuid.uuid4()),
        project_id=project_id,
        external_id=body.external_id,
        email=email,
        source=source,
        created_at=now,
        updated_at=now,
        consent_recorded_at=now,
        **body.model_dump(exclude={"email", "external_id"}),
    )
    session.add(contact)
    session.flush()
    record_activity(session, contact.id, project_id, "registered")
    return contact


def serialize(contact: Contact) -> dict[str, Any]:
    # Explicit allowlist: never expose host credentials or project secrets.
    return {
        key: getattr(contact, key)
        for key in (
            "id",
            "project_id",
            "external_id",
            "email",
            "full_name",
            "company",
            "phone",
            "job_title",
            "industry",
            "contact_type",
            "primary_use",
            "use_details",
            "lifecycle",
            "source",
            "marketing_opt_in",
            "consent_version",
            "consent_recorded_at",
            "tags",
            "follow_up_on",
            "revision",
            "created_at",
            "updated_at",
        )
    }
