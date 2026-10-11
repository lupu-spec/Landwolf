"""Session-scoped CRM self-service; no caller-selected identity or deletion route."""

import time
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from landwolf import auth, recovery
from landwolf import crm_core as core
from landwolf.config import Settings
from landwolf.db import Account


class ProfileEdit(core.Profile):
    revision: int = Field(ge=1, strict=True)


def own_contact(session: Session, account: Account) -> core.Contact:
    row = session.scalar(
        select(core.Contact).where(
            core.Contact.project_id == "landwolf", core.Contact.external_id == account.id
        )
    )
    if row is None or row.email != account.email:
        raise HTTPException(409, "Your profile needs an account correction. Contact support.")
    return row


def profile_values(row: core.Contact) -> dict[str, Any]:
    # Never serialize the owner's CRM fields, notes, tags, IDs or access controls.
    return {
        "email": row.email,
        "revision": row.revision,
        **{field: getattr(row, field) for field in core.Profile.model_fields},
    }


def register(app: FastAPI, settings: Settings, factory: sessionmaker[Session]) -> None:
    def db() -> Iterator[Session]:
        with factory() as session:
            try:
                yield session
            except SQLAlchemyError as exc:
                session.rollback()
                raise HTTPException(
                    503, "Account help is temporarily unavailable. Please retry."
                ) from exc

    DB = Annotated[Session, Depends(db)]

    @app.get("/api/account/profile")
    def get_profile(request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings)
        return {
            "profile": profile_values(own_contact(session, account)),
            "categories": {
                "industry": core.INDUSTRIES,
                "contact_type": core.CONTACT_TYPES,
                "primary_use": core.USES,
            },
            "consent_text": core.CONSENT_TEXT,
            "mail_enabled": app.state.mailer.enabled,
        }

    @app.patch("/api/account/profile")
    def update_profile(body: ProfileEdit, request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, "self-profile:" + account.id, 20)
        row = own_contact(session, account)
        values = body.model_dump(exclude={"revision"})
        for field, choices in (
            ("industry", core.INDUSTRIES),
            ("contact_type", core.CONTACT_TYPES),
            ("primary_use", core.USES),
        ):
            value = values[field]
            if value and value not in choices and value != getattr(row, field):
                raise HTTPException(422, "Choose a listed profile category.")
        changed = sorted(field for field, value in values.items() if getattr(row, field) != value)
        now = int(time.time())
        if "marketing_opt_in" in changed:
            values.update(consent_recorded_at=now, consent_version=core.CONSENT_VERSION)
        key = session.scalar(
            update(core.Contact)
            .where(
                core.Contact.id == row.id,
                core.Contact.external_id == account.id,
                core.Contact.email == account.email,
                core.Contact.revision == body.revision,
            )
            .values(**values, revision=body.revision + 1, updated_at=now)
            .returning(core.Contact.id)
        )
        if key is None:
            raise HTTPException(409, "Your profile changed. Reopen it and review before saving.")
        core.record_activity(
            session,
            row.id,
            account.id,
            "profile_self_updated",
            "User reviewed and saved profile fields: " + (", ".join(changed) or "no changes"),
        )
        session.commit()
        return {"profile": profile_values(row), "message": "Your profile is saved in L91 LLC CRM."}

    @app.post("/api/account/password-reset", status_code=202)
    def password_reset(
        body: core.Contract, request: Request, session: DB, tasks: BackgroundTasks
    ) -> dict[str, str]:
        account = auth.authenticate(request, session, settings, write=True)
        # The stored address is authoritative; chat cannot redirect the reset mail.
        return recovery.request_action(
            account.email, "reset", request, session, settings, app.state.mailer, factory, tasks
        )
