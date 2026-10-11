"""Owner-issued access reservations and account status, without browser credentials."""

import time
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from landwolf.config import Settings
from landwolf.crm_core import Contact, Reservation, record_activity
from landwolf.db import (
    Account,
    AccountAdminAudit,
    AccountRestriction,
    AdminAuditLog,
    BillingExemption,
    LoginSession,
)


def ensure_enabled(session: Session, account: Account, settings: Settings) -> None:
    restriction = session.get(AccountRestriction, account.id)
    if account.id != settings.owner_account_id and restriction and restriction.suspended:
        raise HTTPException(403, "This account is suspended. Contact support.")


def account_for(session: Session, contact: Contact) -> Account | None:
    if contact.project_id != "landwolf":
        return None
    account = session.get(Account, contact.external_id)
    if account and account.email != contact.email:
        raise HTTPException(409, "Account and contact identity differ. Contact support.")
    return account


def audit(
    session: Session,
    contact: Contact,
    actor: str,
    action: str,
    reason: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    account = account_for(session, contact)
    session.add(
        AccountAdminAudit(
            id=str(uuid.uuid4()),
            actor_account_id=actor,
            target_account_id=account.id if account else None,
            action="crm_" + action,
            contact_id=contact.id,
            reason=reason,
            previous_state=before,
            new_state=after,
            created_at=int(time.time()),
        )
    )
    record_activity(session, contact.id, actor, action, reason)


def revoke_grants(session: Session, account: Account, owner: str, reason: str) -> None:
    now = int(time.time())
    for row in session.scalars(
        select(BillingExemption).where(
            BillingExemption.account_id == account.id,
            BillingExemption.status == "active",
        )
    ):
        row.status = "revoked"
        row.revoked_at = now
        row.revoked_by_account_id = owner
        row.revocation_reason = reason
        row.updated_at = now
        session.add(
            AdminAuditLog(
                id=str(uuid.uuid4()),
                actor_account_id=owner,
                target_account_id=account.id,
                action="billing_exemption_revoked",
                resource_type="billing_exemption",
                resource_id=row.id,
                reason=reason,
                previous_state={"billing_exempt": True, "expires_at": row.expires_at},
                new_state={"billing_exempt": False},
                created_at=now,
            )
        )


def apply_grant(
    session: Session,
    account: Account,
    owner: str,
    reason: str,
    days: int | None,
) -> int | None:
    # Caller locks the account and owns the transaction. Retire expired rows too,
    # since the database permits only one row marked active per account.
    revoke_grants(session, account, owner, reason)
    session.flush()
    now = int(time.time())
    expires = now + days * 86400 if days is not None else None
    grant_id = str(uuid.uuid4())
    session.add(
        BillingExemption(
            id=grant_id,
            account_id=account.id,
            status="active",
            reason=reason,
            granted_by_account_id=owner,
            granted_at=now,
            expires_at=expires,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        AdminAuditLog(
            id=str(uuid.uuid4()),
            actor_account_id=owner,
            target_account_id=account.id,
            action="billing_exemption_granted",
            resource_type="billing_exemption",
            resource_id=grant_id,
            reason=reason,
            previous_state={"billing_exempt": False},
            new_state={"billing_exempt": True, "expires_at": expires},
            created_at=now,
        )
    )
    return expires


def activate_reserved(session: Session, account: Account, settings: Settings) -> None:
    """Claim only after mailbox verification; an email string is not ownership proof."""
    from landwolf.db import AccountEmail

    verified = session.get(AccountEmail, account.id)
    if not verified or not verified.verified_at or account.id == settings.owner_account_id:
        return
    contact = session.scalar(
        select(Contact).where(
            Contact.project_id == "landwolf",
            Contact.external_id == account.id,
        )
    )
    if contact is None:
        return
    # Lock order matches owner writes: contact, then account, then reservation.
    session.execute(select(Contact.id).where(Contact.id == contact.id).with_for_update())
    session.execute(select(Account.id).where(Account.id == account.id).with_for_update())
    row = session.scalar(
        select(Reservation)
        .where(
            Reservation.contact_id == contact.id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None or row.state != "reserved" or row.owner_id != settings.owner_account_id:
        return
    existing = session.scalar(
        select(BillingExemption.id).where(
            BillingExemption.account_id == account.id,
            BillingExemption.status == "active",
            (
                BillingExemption.expires_at.is_(None)
                | (BillingExemption.expires_at > int(time.time()))
            ),
        )
    )
    if existing is not None:
        return
    expires = apply_grant(session, account, row.owner_id, row.reason, row.days)
    row.state = "activated"
    row.activated_at = int(time.time())
    row.expires_at = expires
    contact.revision += 1
    contact.updated_at = int(time.time())
    audit(
        session,
        contact,
        row.owner_id,
        "reserved_access_activated",
        row.reason,
        {"state": "reserved"},
        {"state": "active", "expires_at": expires},
    )
    session.commit()


def sign_out_all(session: Session, account: Account) -> int:
    tokens = session.scalars(
        delete(LoginSession)
        .where(
            LoginSession.account_id == account.id,
        )
        .returning(LoginSession.token_hash)
    ).all()
    return len(tokens)
