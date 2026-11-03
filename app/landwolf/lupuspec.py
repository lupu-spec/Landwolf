"""LupuSpec customer concept intake and owner-managed work-order queue.

A request is not an approved production job. Dispatch, charges and fulfillment
remain explicit owner-controlled operations.
"""

import hashlib
import json
import time
import uuid
from collections.abc import Iterator
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import EmailStr, Field, field_validator
from sqlalchemy import CheckConstraint, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from landwolf import admin, auth
from landwolf.config import Settings
from landwolf.crm_core import Contact, Intake, capture
from landwolf.db import Base
from landwolf.schemas import Contract

Capability = Literal["studio", "software", "fabrication", "supply"]
Status = Literal[
    "received", "reviewing", "quoted", "approved", "in_progress", "delivered", "closed"
]
CAPABILITIES: dict[str, str] = {
    "studio": "Studio",
    "software": "Software",
    "fabrication": "Fabrication",
    "supply": "Supply",
}


class ConceptRequest(Base):
    __tablename__ = "lw2_lupuspec_requests"
    __table_args__ = (
        CheckConstraint("quantity >= 1 AND quantity <= 10000"),
        CheckConstraint(
            "status IN ('received','reviewing','quoted','approved',"
            "'in_progress','delivered','closed')"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submission_id: Mapped[str] = mapped_column(String(36), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    contact_id: Mapped[str] = mapped_column(String(36), index=True)
    capability: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(150))
    text: Mapped[str] = mapped_column(String(4000))
    reference_url: Mapped[str] = mapped_column(String(500), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(24), default="received")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[int] = mapped_column(Integer)


class ConceptEvent(Base):
    __tablename__ = "lw2_lupuspec_request_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    owner_id: Mapped[str] = mapped_column(String(36))
    from_status: Mapped[str] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[int] = mapped_column(Integer)


class RequestInput(Contract):
    submission_id: uuid.UUID
    capability: Capability
    title: str = Field(min_length=3, max_length=150)
    text: str = Field(min_length=20, max_length=4000)
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr = Field(max_length=254)
    company: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=32)
    reference_url: str = Field(default="", max_length=500)
    quantity: int = Field(default=1, ge=1, le=10000, strict=True)
    contact_permission: Literal[True]

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return (
            value
            if not value
            else Intake.model_validate(
                {
                    "external_id": "validation",
                    "email": "validation@example.com",
                    "full_name": "Validation",
                    "primary_use": "other",
                    "phone": value,
                }
            ).phone
        )

    @field_validator("reference_url")
    @classmethod
    def valid_reference(cls, value: str) -> str:
        if value:
            url = urlsplit(value)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.port is not None
                or len(url.hostname) > 253
            ):
                raise ValueError("Use an HTTPS link without credentials or a port")
        return value


class StatusInput(Contract):
    revision: int = Field(ge=1, strict=True)
    status: Status


def _content_hash(body: RequestInput) -> str:
    payload = body.model_dump(mode="json", exclude={"submission_id"})
    payload["email"] = str(body.email).casefold()
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _origin_guard(request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin", "")
    if (
        origin not in settings.trusted_origins
        or urlsplit(origin).netloc.lower() != request.headers.get("host", "").lower()
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise HTTPException(403, "Use the LupuSpec portal on its own origin")
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        raise HTTPException(415, "Use application/json")


def _owner_view(row: ConceptRequest, contact: Contact) -> dict[str, Any]:
    return {
        "id": row.id,
        "contact_id": contact.id,
        "full_name": contact.full_name,
        "email": contact.email,
        "company": contact.company,
        "phone": contact.phone,
        "capability": row.capability,
        "title": row.title,
        "text": row.text,
        "quantity": row.quantity,
        "reference_url": row.reference_url,
        "status": row.status,
        "revision": row.revision,
        "created_at": row.created_at,
    }


def store_request(body: RequestInput, session: Session) -> ConceptRequest:
    """Write intake in the caller transaction; this grants no customer access."""
    contact = capture(
        session,
        "lupuspec",
        Intake(
            external_id="lupuspec:"
            + hashlib.sha256(str(body.email).casefold().encode()).hexdigest(),
            email=str(body.email).casefold(),
            full_name=body.full_name,
            company=body.company,
            phone=body.phone,
            primary_use="lupuspec_" + body.capability,
            use_details=body.title[:1000],
            marketing_opt_in=False,
        ),
        source="lupuspec_portal",
    )
    now = int(time.time())
    item = ConceptRequest(
        id=str(uuid.uuid4()),
        submission_id=str(body.submission_id),
        content_hash=_content_hash(body),
        contact_id=contact.id,
        capability=body.capability,
        title=body.title,
        text=body.text,
        reference_url=body.reference_url,
        quantity=body.quantity,
        status="received",
        revision=1,
        created_at=now,
        updated_at=now,
    )
    session.add(item)
    session.flush()
    return item


def register(app: FastAPI, settings: Settings, factory: sessionmaker[Session]) -> None:
    def db() -> Iterator[Session]:
        with factory() as session:
            yield session

    DB = Annotated[Session, Depends(db)]

    @app.post("/api/lupuspec/requests", status_code=201)
    def receive(body: RequestInput, request: Request, session: DB) -> dict[str, str]:
        _origin_guard(request, settings)
        ip = request.client.host if request.client else "unknown"
        auth.limit(session, f"lupuspec-intake-ip:{ip}", 12, 3600)
        auth.limit(
            session,
            f"lupuspec-intake-email:{hashlib.sha256(str(body.email).casefold().encode()).hexdigest()}",
            8,
            3600,
        )
        submission_id = str(body.submission_id)
        digest = _content_hash(body)
        existing = session.scalar(
            select(ConceptRequest).where(ConceptRequest.submission_id == submission_id)
        )
        if existing:
            if existing.content_hash != digest:
                raise HTTPException(409, "Submission ID was already used for different details")
            return {"request_id": existing.id, "status": existing.status}
        try:
            item = store_request(body, session)
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(409, "Contact identity conflict; contact support") from exc
        except IntegrityError as exc:
            session.rollback()
            previous = session.scalar(
                select(ConceptRequest).where(ConceptRequest.submission_id == submission_id)
            )
            if previous is not None and previous.content_hash == digest:
                return {"request_id": previous.id, "status": previous.status}
            raise HTTPException(409, "Request changed concurrently; retry with a new ID") from exc
        return {"request_id": item.id, "status": item.status}

    @app.get("/api/admin/lupuspec/requests")
    def list_requests(request: Request, session: DB) -> dict[str, Any]:
        admin.require_owner(request, session, settings, write=False)
        records = session.execute(
            select(ConceptRequest, Contact)
            .join(Contact, Contact.id == ConceptRequest.contact_id)
            .where(Contact.project_id == "lupuspec")
            .order_by(ConceptRequest.created_at.desc(), ConceptRequest.id.desc())
            .limit(200)
        ).all()
        return {"requests": [_owner_view(item, contact) for item, contact in records]}

    @app.patch("/api/admin/lupuspec/requests/{request_id}")
    def change_status(
        request_id: str, body: StatusInput, request: Request, session: DB
    ) -> dict[str, Any]:
        owner = admin.require_owner(request, session, settings, write=True)
        auth.limit(session, f"lupuspec-admin:{owner.id}", 30, 60)
        row = session.scalar(
            select(ConceptRequest).where(ConceptRequest.id == request_id).with_for_update()
        )
        if row is None:
            raise HTTPException(404, "Request not found")
        if row.revision != body.revision:
            raise HTTPException(409, "Request changed; refresh and retry")
        if row.status != body.status:
            session.add(
                ConceptEvent(
                    id=str(uuid.uuid4()),
                    request_id=row.id,
                    owner_id=owner.id,
                    from_status=row.status,
                    to_status=body.status,
                    created_at=int(time.time()),
                )
            )
            row.status = body.status
            row.revision += 1
            row.updated_at = int(time.time())
            session.commit()
        contact = session.get(Contact, row.contact_id)
        if contact is None or contact.project_id != "lupuspec":
            raise HTTPException(409, "LupuSpec contact is not available")
        return _owner_view(row, contact)
