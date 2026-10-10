"""Owner-only complimentary billing access with append-only audit events."""

import time
import uuid
from typing import Any

from fastapi import HTTPException, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from landwolf import auth
from landwolf.config import Settings
from landwolf.db import Account, AdminAuditLog, BillingExemption
from landwolf.schemas import Contract


class ExemptionGrant(Contract):
    reason: str | None = Field(default=None, max_length=500)
    expires_at: int | None = Field(default=None, gt=0)


class ExemptionRevoke(Contract):
    reason: str | None = Field(default=None, max_length=500)


def require_owner(
    request: Request, session: Session, settings: Settings, *, write: bool
) -> Account:
    account = auth.authenticate(request, session, settings, write=write)
    if settings.owner_account_id is None or account.id != settings.owner_account_id:
        raise HTTPException(403, "Owner authorization required")
    return account


def active_exemption(
    session: Session, account_id: str, *, now: int | None = None
) -> BillingExemption | None:
    current = int(time.time()) if now is None else now
    return session.scalar(
        select(BillingExemption).where(
            BillingExemption.account_id == account_id,
            BillingExemption.status == "active",
            (BillingExemption.expires_at.is_(None) | (BillingExemption.expires_at > current)),
        )
    )


def entitlement(session: Session, account: Account, settings: Settings) -> str | None:
    if settings.owner_account_id is not None and account.id == settings.owner_account_id:
        return "owner"
    if active_exemption(session, account.id) is not None:
        return "complimentary"
    return None


def _target(session: Session, account_id: str) -> Account:
    target = session.get(Account, account_id)
    if target is None:
        raise HTTPException(404, "Account not found")
    return target


def grant(
    request: Request,
    session: Session,
    settings: Settings,
    account_id: str,
    body: ExemptionGrant,
) -> dict[str, Any]:
    owner = require_owner(request, session, settings, write=True)
    if account_id == owner.id:
        raise HTTPException(409, "Owner access is immutable")
    target = _target(session, account_id)
    session.execute(select(Account.id).where(Account.id == target.id).with_for_update())
    if active_exemption(session, target.id) is not None:
        raise HTTPException(409, "Complimentary access is already active")
    now = int(time.time())
    if body.expires_at is not None and body.expires_at <= now:
        raise HTTPException(422, "Expiration must be in the future")
    row = BillingExemption(
        id=str(uuid.uuid4()),
        account_id=target.id,
        status="active",
        reason=body.reason,
        granted_by_account_id=owner.id,
        granted_at=now,
        expires_at=body.expires_at,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.add(
        AdminAuditLog(
            id=str(uuid.uuid4()),
            actor_account_id=owner.id,
            target_account_id=target.id,
            action="billing_exemption_granted",
            resource_type="billing_exemption",
            resource_id=row.id,
            reason=body.reason,
            previous_state={"billing_exempt": False},
            new_state={"billing_exempt": True, "expires_at": body.expires_at},
            request_id=request.headers.get("x-request-id", "")[:100] or None,
            created_at=now,
        )
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Complimentary access changed concurrently; reload") from exc
    return {
        "account_id": target.id,
        "email": target.email,
        "billing_exempt": True,
        "expires_at": body.expires_at,
    }


def revoke(
    request: Request,
    session: Session,
    settings: Settings,
    account_id: str,
    body: ExemptionRevoke,
) -> dict[str, Any]:
    owner = require_owner(request, session, settings, write=True)
    if account_id == owner.id:
        raise HTTPException(409, "Owner access is immutable")
    target = _target(session, account_id)
    session.execute(select(Account.id).where(Account.id == target.id).with_for_update())
    row = active_exemption(session, target.id)
    if row is None:
        raise HTTPException(404, "No active complimentary access")
    now = int(time.time())
    row.status = "revoked"
    row.revoked_at = now
    row.revoked_by_account_id = owner.id
    row.revocation_reason = body.reason
    row.updated_at = now
    session.add(
        AdminAuditLog(
            id=str(uuid.uuid4()),
            actor_account_id=owner.id,
            target_account_id=target.id,
            action="billing_exemption_revoked",
            resource_type="billing_exemption",
            resource_id=row.id,
            reason=body.reason,
            previous_state={"billing_exempt": True, "expires_at": row.expires_at},
            new_state={"billing_exempt": False},
            request_id=request.headers.get("x-request-id", "")[:100] or None,
            created_at=now,
        )
    )
    session.commit()
    return {"account_id": target.id, "email": target.email, "billing_exempt": False}


def accounts(request: Request, session: Session, settings: Settings) -> dict[str, Any]:
    require_owner(request, session, settings, write=False)
    now = int(time.time())
    rows = session.scalars(select(Account).order_by(Account.email).limit(500)).all()
    exemptions = {
        item.account_id: item
        for item in session.scalars(
            select(BillingExemption).where(
                BillingExemption.status == "active",
                (BillingExemption.expires_at.is_(None) | (BillingExemption.expires_at > now)),
            )
        )
    }
    return {
        "accounts": [
            {
                "id": row.id,
                "email": row.email,
                "owner": settings.owner_account_id == row.id,
                "billing_exempt": row.id in exemptions,
                "expires_at": exemptions[row.id].expires_at if row.id in exemptions else None,
            }
            for row in rows
        ]
    }


def audit(request: Request, session: Session, settings: Settings) -> dict[str, Any]:
    require_owner(request, session, settings, write=False)
    rows = session.scalars(
        select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(200)
    ).all()
    return {
        "events": [
            {
                "id": row.id,
                "actor_account_id": row.actor_account_id,
                "target_account_id": row.target_account_id,
                "action": row.action,
                "resource_id": row.resource_id,
                "reason": row.reason,
                "previous_state": row.previous_state,
                "new_state": row.new_state,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }
