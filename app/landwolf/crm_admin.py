"""Owner-only contact corrections, account administration, and access reservations."""

import time
import uuid
from collections.abc import Iterator
from typing import Annotated, Any, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from pydantic import EmailStr, Field, model_validator
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from landwolf import admin, auth, crm_access, feedback, recovery
from landwolf.config import Settings
from landwolf.crm_core import (
    Contact,
    Contract,
    Intake,
    Profile,
    Project,
    Reservation,
    capture,
    serialize,
)
from landwolf.db import (
    Account,
    AccountAction,
    AccountEmail,
    AccountRestriction,
    BillingCustomer,
    LoginSession,
)


class Change(Contract):
    revision: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=500)


class NewContact(Profile):
    email: EmailStr = Field(max_length=254)
    project_id: str = Field(default="landwolf", pattern=r"^[a-z][a-z0-9_-]{0,39}$")


class ProfileEdit(Profile):
    email: EmailStr = Field(max_length=254)
    revision: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=500)


class AccessChange(Change):
    action: Literal["trial", "complimentary", "revoke"]
    days: int | None = Field(default=None, ge=1, le=365, strict=True)

    @model_validator(mode="after")
    def valid_duration(self) -> "AccessChange":
        if self.action == "trial" and self.days is None:
            raise ValueError("Trial duration is required")
        if self.action == "revoke" and self.days is not None:
            raise ValueError("Revocation does not accept a duration")
        return self


class StatusChange(Change):
    suspended: bool = Field(strict=True)


class EmailAction(Change):
    purpose: Literal["reset", "verify"]


def register(app: FastAPI, settings: Settings, factory: sessionmaker[Session]) -> None:
    def db() -> Iterator[Session]:
        with factory() as session:
            try:
                yield session
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(
                    409, "Email or record already exists. Refresh and retry."
                ) from exc
            except SQLAlchemyError as exc:
                session.rollback()
                raise HTTPException(
                    503, "Account administration is temporarily unavailable."
                ) from exc

    DB = Annotated[Session, Depends(db)]

    def owner(request: Request, session: Session, write: bool = True) -> Account:
        actor = admin.require_owner(request, session, settings, write=write)
        if write:
            auth.limit(session, "crm-admin:" + actor.id, 40)
        return actor

    def get_contact(session: Session, contact_id: str) -> Contact:
        row = session.get(Contact, contact_id)
        if row is None:
            raise HTTPException(404, "Contact not found")
        return row

    def changed(session: Session, contact_id: str, revision: int) -> Contact:
        key = session.scalar(
            update(Contact)
            .where(
                Contact.id == contact_id,
                Contact.revision == revision,
            )
            .values(revision=revision + 1, updated_at=int(time.time()))
            .returning(Contact.id)
        )
        if key is None:
            raise HTTPException(409, "Contact changed. Reopen it and retry.")
        return get_contact(session, contact_id)

    def target(session: Session, contact: Contact, *, required: bool = True) -> Account | None:
        if contact.project_id != "landwolf":
            raise HTTPException(409, "Manage this account in its connected project.")
        account = crm_access.account_for(session, contact)
        if account and account.id == settings.owner_account_id:
            raise HTTPException(
                409, "Owner login and access are protected from administrative changes."
            )
        if account:
            session.execute(select(Account.id).where(Account.id == account.id).with_for_update())
        if required and account is None:
            raise HTTPException(409, "Account registration is pending.")
        return account

    @app.post("/api/admin/crm/contacts", status_code=201)
    def create(body: NewContact, request: Request, session: DB) -> dict[str, Any]:
        actor = owner(request, session)
        if body.marketing_opt_in:
            raise HTTPException(422, "Marketing consent must be supplied by the contact.")
        if session.get(Project, body.project_id) is None:
            raise HTTPException(404, "Project not found")
        if session.scalar(
            select(Contact.id).where(
                Contact.project_id == body.project_id,
                Contact.email == str(body.email).casefold(),
            )
        ):
            raise HTTPException(409, "This email already has a contact in this project.")
        existing_account = (
            session.scalar(select(Account).where(Account.email == str(body.email).casefold()))
            if body.project_id == "landwolf"
            else None
        )
        row = capture(
            session,
            body.project_id,
            Intake(
                external_id=existing_account.id
                if existing_account
                else "manual:" + str(uuid.uuid4()),
                **body.model_dump(exclude={"project_id"}),
            ),
            source="owner_manual",
        )
        row.consent_recorded_at = None
        crm_access.audit(session, row, actor.id, "contact_created", "Owner added contact", {}, {})
        session.commit()
        return serialize(row)

    @app.patch("/api/admin/crm/contacts/{contact_id}/profile")
    def profile(
        contact_id: str, body: ProfileEdit, request: Request, session: DB
    ) -> dict[str, Any]:
        actor = owner(request, session)
        if body.marketing_opt_in:
            raise HTTPException(422, "Marketing consent must be supplied by the contact.")
        row = changed(session, contact_id, body.revision)
        account = crm_access.account_for(session, row)
        email = str(body.email).casefold()
        email_changed = row.email != email
        if email_changed and account:
            target(session, row)
            if session.scalar(select(Account.id).where(Account.email == email)):
                raise HTTPException(409, "That email already belongs to another account.")
            account.email = email
            session.execute(delete(AccountEmail).where(AccountEmail.account_id == account.id))
            session.execute(delete(AccountAction).where(AccountAction.account_id == account.id))
            crm_access.sign_out_all(session, account)
        for field, value in body.model_dump(
            exclude={
                "email",
                "revision",
                "reason",
                "marketing_opt_in",
            }
        ).items():
            setattr(row, field, value)
        row.email = email
        if email_changed:
            row.marketing_opt_in = False
            row.consent_version = None
            row.consent_recorded_at = None
        crm_access.audit(
            session,
            row,
            actor.id,
            "profile_updated",
            body.reason,
            {},
            {"email_changed": email_changed},
        )
        session.commit()
        return serialize(row)

    @app.get("/api/admin/crm/contacts/{contact_id}/account")
    def account_details(contact_id: str, request: Request, session: DB) -> dict[str, Any]:
        owner(request, session, False)
        row = get_contact(session, contact_id)
        account = crm_access.account_for(session, row)
        reservation = session.get(Reservation, row.id)
        result: dict[str, Any] = {
            "supported": row.project_id == "landwolf",
            "registered": account is not None,
            "mail_enabled": app.state.mailer.enabled,
            "reservation": (
                {
                    "kind": reservation.kind,
                    "state": reservation.state,
                    "days": reservation.days,
                    "expires_at": reservation.expires_at,
                }
                if reservation
                else None
            ),
        }
        if account is None:
            return result
        restriction = session.get(AccountRestriction, account.id)
        exemption = admin.active_exemption(session, account.id)
        customer = session.get(BillingCustomer, account.id)
        sessions = select(LoginSession).where(
            LoginSession.account_id == account.id,
            LoginSession.expires_at > int(time.time()),
        )
        result.update(
            {
                "id": account.id,
                "owner": account.id == settings.owner_account_id,
                "created_at": account.created_at,
                "verified": recovery.verified(session, account.id),
                "suspended": bool(restriction and restriction.suspended),
                "active_sessions": session.scalar(
                    select(func.count()).select_from(sessions.subquery())
                ),
                "last_seen": session.scalar(
                    select(func.max(LoginSession.last_seen)).where(
                        LoginSession.account_id == account.id
                    )
                ),
                "complimentary": bool(exemption),
                "expires_at": exemption.expires_at if exemption else None,
                "subscription_status": customer.subscription_status if customer else "none",
                "paid_until": customer.paid_until if customer else None,
                "cancel_at_period_end": bool(customer and customer.cancel_at_period_end),
                "billing_synced_at": customer.synced_at if customer else None,
                "pilot": feedback.status(session, account, settings=settings),
            }
        )
        return result

    @app.post("/api/admin/crm/contacts/{contact_id}/access")
    def access(
        contact_id: str, body: AccessChange, request: Request, session: DB
    ) -> dict[str, Any]:
        actor = owner(request, session)
        row = changed(session, contact_id, body.revision)
        account = target(session, row, required=False)
        reservation = session.get(Reservation, row.id)
        if body.action == "revoke":
            if reservation:
                reservation.state = "revoked"
            if account:
                crm_access.revoke_grants(session, account, actor.id, body.reason)
            row.tags = [tag for tag in row.tags if tag not in {"trial_user", "complimentary"}]
            state, expires = "revoked", None
        else:
            if account:
                expires = crm_access.apply_grant(session, account, actor.id, body.reason, body.days)
                state = "activated"
            else:
                expires, state = None, "reserved"
            if reservation is None:
                reservation = Reservation(contact_id=row.id)
                session.add(reservation)
            reservation.kind = body.action
            reservation.days = body.days
            reservation.state = state
            reservation.owner_id = actor.id
            reservation.reason = body.reason
            reservation.created_at = int(time.time())
            reservation.activated_at = int(time.time()) if account else None
            reservation.expires_at = expires
            tags = [tag for tag in row.tags if tag not in {"trial_user", "complimentary"}]
            if len(tags) < 12:
                row.tags = tags + (["trial_user"] if body.action == "trial" else ["complimentary"])
        crm_access.audit(
            session,
            row,
            actor.id,
            "access_" + body.action,
            body.reason,
            {},
            {"state": state, "expires_at": expires},
        )
        session.commit()
        return {"state": state, "expires_at": expires}

    @app.post("/api/admin/crm/contacts/{contact_id}/status")
    def status(
        contact_id: str, body: StatusChange, request: Request, session: DB
    ) -> dict[str, bool]:
        actor = owner(request, session)
        row = changed(session, contact_id, body.revision)
        account = target(session, row)
        if account is None:
            raise HTTPException(409, "Account registration is pending.")
        restriction = session.get(AccountRestriction, account.id)
        if restriction is None:
            restriction = AccountRestriction(account_id=account.id)
            session.add(restriction)
        restriction.suspended = body.suspended
        restriction.reason = body.reason
        restriction.updated_by = actor.id
        restriction.updated_at = int(time.time())
        if body.suspended:
            crm_access.sign_out_all(session, account)
            session.execute(delete(AccountAction).where(AccountAction.account_id == account.id))
        crm_access.audit(
            session,
            row,
            actor.id,
            "suspended" if body.suspended else "restored",
            body.reason,
            {},
            {"suspended": body.suspended},
        )
        session.commit()
        return {"suspended": body.suspended}

    @app.post("/api/admin/crm/contacts/{contact_id}/sessions")
    def sessions(contact_id: str, body: Change, request: Request, session: DB) -> dict[str, int]:
        actor = owner(request, session)
        row = changed(session, contact_id, body.revision)
        account = target(session, row)
        if account is None:
            raise HTTPException(409, "Account registration is pending.")
        count = crm_access.sign_out_all(session, account)
        crm_access.audit(session, row, actor.id, "sessions_revoked", body.reason, {}, {})
        session.commit()
        return {"revoked": count}

    @app.post("/api/admin/crm/contacts/{contact_id}/email-action", status_code=202)
    def email_action(
        contact_id: str,
        body: EmailAction,
        request: Request,
        session: DB,
        tasks: BackgroundTasks,
    ) -> dict[str, str]:
        actor = owner(request, session)
        row = get_contact(session, contact_id)
        if row.revision != body.revision:
            raise HTTPException(409, "Contact changed. Reopen it and retry.")
        account = target(session, row)
        if account is None:
            raise HTTPException(409, "Account registration is pending.")
        crm_access.ensure_enabled(session, account, settings)
        result = recovery.request_action(
            account.email,
            body.purpose,
            request,
            session,
            settings,
            app.state.mailer,
            factory,
            tasks,
        )
        crm_access.audit(
            session, row, actor.id, "email_" + body.purpose + "_requested", body.reason, {}, {}
        )
        session.commit()
        return result
