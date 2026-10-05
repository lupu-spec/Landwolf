"""Owner-authorized, bounded account CSV without credentials or survey answers."""

import csv
import io
from datetime import UTC, datetime

from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from landwolf import admin
from landwolf.config import Settings
from landwolf.db import Account, FeedbackEnrollment

MAX_EXPORT_USERS = 10_000


def spreadsheet_text(value: str) -> str:
    """Keep untrusted text from becoming a spreadsheet formula or control prefix."""
    if value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _date(value: int | None) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat().replace("+00:00", "Z") if value else ""


def users_csv(request: Request, session: Session, settings: Settings) -> Response:
    try:
        admin.require_owner(request, session, settings, write=False)
        rows = session.execute(
            select(
                Account.email,
                Account.id,
                FeedbackEnrollment.invited_at,
                FeedbackEnrollment.accepted_at,
                FeedbackEnrollment.expires_at,
                FeedbackEnrollment.revoked_at,
            )
            .outerjoin(FeedbackEnrollment, FeedbackEnrollment.account_id == Account.id)
            .order_by(Account.email, Account.id)
            .limit(MAX_EXPORT_USERS + 1)
        ).all()
    except SQLAlchemyError as exc:
        raise HTTPException(503, "User export is temporarily unavailable. Please retry.") from exc
    if len(rows) > MAX_EXPORT_USERS:
        raise HTTPException(
            409, "User export exceeds 10,000 accounts. No partial file was created."
        )
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Email",
            "Account role",
            "Pilot invited (UTC)",
            "Pilot accepted (UTC)",
            "Pilot ends (UTC)",
            "Pilot revoked (UTC)",
        ]
    )
    for email, account_id, invited, accepted, expires, revoked in rows:
        writer.writerow(
            [
                spreadsheet_text(email),
                "Owner" if account_id == settings.owner_account_id else "User",
                *(_date(value) for value in (invited, accepted, expires, revoked)),
            ]
        )
    filename = f"landwolf-users-{datetime.now(UTC):%Y-%m-%d}.csv"
    return Response(
        content=("\ufeff" + output.getvalue()).encode("utf-8"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
