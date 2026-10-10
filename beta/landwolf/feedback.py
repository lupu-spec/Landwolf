"""Invite-only investor feedback pilot with a fixed calendar-month entitlement."""

import calendar
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, Self

from fastapi import HTTPException, Request
from pydantic import ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from landwolf import admin
from landwolf.config import Settings
from landwolf.db import Account, FeedbackAudit, FeedbackEnrollment, FeedbackResponse, TrialResponse
from landwolf.schemas import Contract

TERMS_VERSION = "investor-pilot-v1"
SURVEY_VERSION = 1
DAY_SECONDS = 86400
GRACE_SECONDS = 7 * DAY_SECONDS
SURVEYS = (("day14", 14), ("day30", 30), ("day60", 60), ("day85", 85))
SurveyKey = Literal["day14", "day30", "day60", "day85"]


def _now() -> int:
    return int(time.time())


class StrictContract(Contract):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class Answers(StrictContract):
    usage: Literal["used", "not_used"]
    last_attempted_task: str = Field(min_length=1, max_length=1500)
    blocker: str = Field(min_length=1, max_length=1500)
    feature_request: str = Field(max_length=1500)
    feature_reason: str = Field(max_length=1500)
    priority: Literal["low", "medium", "high"] | None = None
    value_rating: int | None = Field(default=None, ge=1, le=5)
    no_changes: bool

    @field_validator("last_attempted_task", "blocker", "feature_request", "feature_reason")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def valid_answers(self) -> Self:
        if not self.last_attempted_task or not self.blocker:
            raise ValueError("Task and blocker cannot be blank; not used is a valid answer")
        if not self.no_changes and (not self.feature_request or not self.feature_reason):
            raise ValueError("Describe the feature and why, or select no changes")
        if self.no_changes:
            self.feature_request = self.feature_request or "No changes requested"
            self.feature_reason = self.feature_reason or "No changes requested"
        if self.usage == "used" and self.value_rating is None:
            raise ValueError("Rate the value from 1 to 5 when you have used LandWolf")
        return self


class AcceptInput(StrictContract):
    terms_version: Literal["investor-pilot-v1"]
    accepted_terms: Literal[True]
    baseline: Answers

    @field_validator("accepted_terms", mode="before")
    @classmethod
    def explicit_consent(cls, value: Any) -> Any:
        if value is not True:
            raise ValueError("Explicit agreement is required")
        return value


class SurveyInput(StrictContract):
    survey_key: SurveyKey
    survey_version: Literal[1]
    answers: Answers

    @field_validator("survey_version", mode="before")
    @classmethod
    def explicit_version(cls, value: Any) -> Any:
        if type(value) is not int or value != SURVEY_VERSION:
            raise ValueError("Unsupported survey version")
        return value


class InviteInput(StrictContract):
    reason: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Reason cannot be blank")
        return normalized


class RevokeInput(InviteInput):
    pass


def three_months_after(timestamp: int) -> int:
    """Preserve UTC clock time; clamp day to the destination month's final day."""
    start = datetime.fromtimestamp(timestamp, UTC)
    month_index = start.year * 12 + start.month - 1 + 3
    year, month = divmod(month_index, 12)
    month += 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return int(start.replace(year=year, month=month, day=day).timestamp())


def _responses(session: Session, account_id: str) -> list[FeedbackResponse]:
    return list(
        session.scalars(select(FeedbackResponse).where(FeedbackResponse.account_id == account_id))
    )


def status(
    session: Session, account: Account, now: int | None = None, *, settings: Settings | None = None
) -> dict[str, Any]:
    current = _now() if now is None else now
    row = session.get(FeedbackEnrollment, account.id)
    result: dict[str, Any] = {
        "state": "none",
        "enrolled": row is not None,
        "accepted_at": row.accepted_at if row else None,
        "expires_at": row.expires_at if row else None,
        "terms_version": TERMS_VERSION,
        "survey_version": SURVEY_VERSION,
        "due_survey": None,
        "next_due_at": None,
        "completed_surveys": [],
        "access_allowed": True,
        "access_override": admin.entitlement(session, account, settings) if settings else None,
    }
    if row is None:
        return result
    completed = {response.survey_key for response in _responses(session, account.id)}
    result["completed_surveys"] = [
        key for key in ("baseline", *(item[0] for item in SURVEYS)) if key in completed
    ]
    if row.state == "revoked":
        result.update(state="revoked", access_allowed=row.accepted_at is None)
    elif row.accepted_at is None:
        result["state"] = "invited"
    elif row.expires_at is None or current >= row.expires_at:
        result.update(state="expired", access_allowed=False)
    else:
        result["state"] = "active"
        for key, offset in SURVEYS:
            if key in completed:
                continue
            due_at = row.accepted_at + offset * DAY_SECONDS
            result["next_due_at"] = due_at
            if current >= due_at:
                result["due_survey"] = {
                    "key": key,
                    "due_at": due_at,
                    "grace_until": min(due_at + GRACE_SECONDS, row.expires_at),
                }
                if current >= due_at + GRACE_SECONDS:
                    result.update(state="feedback_required", access_allowed=False)
            break
    if result["access_override"] is not None:
        result["access_allowed"] = True
    return result


def require_access(session: Session, account: Account, settings: Settings) -> None:
    current = status(session, account, settings=settings)
    if current["access_allowed"]:
        return
    code, message = {
        "feedback_required": ("FEEDBACK_REQUIRED", "Complete your due feedback to resume access"),
        "expired": ("PILOT_EXPIRED", "Your three-month investor pilot has ended"),
        "revoked": ("PILOT_REVOKED", "Your investor pilot access has been revoked"),
    }[current["state"]]
    raise HTTPException(403, {"code": code, "message": message})


def _audit(
    session: Session,
    actor: str,
    target: str,
    action: str,
    now: int,
    *,
    survey_key: str | None = None,
    reason: str | None = None,
) -> None:
    session.add(
        FeedbackAudit(
            id=str(uuid.uuid4()),
            actor_account_id=actor,
            target_account_id=target,
            action=action,
            survey_key=survey_key,
            reason=reason,
            created_at=now,
        )
    )


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Feedback changed concurrently; reload and retry") from exc


def _locked(session: Session, account: Account) -> FeedbackEnrollment:
    # A real write serializes SQLite and PostgreSQL mutations. Refresh after locking
    # so a concurrent acceptance/revocation cannot be overwritten by stale state.
    session.execute(
        update(FeedbackEnrollment)
        .where(FeedbackEnrollment.account_id == account.id)
        .values(revision=FeedbackEnrollment.revision + 1)
    )
    row = session.get(FeedbackEnrollment, account.id, populate_existing=True)
    if row is None:
        raise HTTPException(403, "An owner invitation is required")
    return row


def invite(
    request: Request, session: Session, settings: Settings, account_id: str, body: InviteInput
) -> dict[str, Any]:
    owner = admin.require_owner(request, session, settings, write=True)
    target = session.get(Account, account_id)
    if target is None:
        raise HTTPException(404, "Account not found")
    if admin.entitlement(session, target, settings) is not None:
        raise HTTPException(409, "Owner or independently complimentary accounts cannot enroll")
    existing = session.get(FeedbackEnrollment, target.id)
    if existing is not None:
        if existing.state == "invited":
            return status(session, target, settings=settings)
        raise HTTPException(409, "This account already has a pilot history; it cannot restart")
    now = _now()
    session.add(
        FeedbackEnrollment(
            account_id=target.id,
            invited_by_account_id=owner.id,
            invited_at=now,
            state="invited",
            terms_version=TERMS_VERSION,
        )
    )
    _audit(session, owner.id, target.id, "invite", now, reason=body.reason)
    _commit(session)
    return status(session, target, now, settings=settings)


def accept(session: Session, account: Account, body: AcceptInput) -> dict[str, Any]:
    row = _locked(session, account)
    baseline = session.get(FeedbackResponse, (account.id, "baseline"))
    answers = body.baseline.model_dump()
    if row.state == "revoked":
        raise HTTPException(409, "This invitation has been revoked")
    if row.accepted_at is not None:
        if baseline is not None and baseline.answers == answers:
            _commit(session)
            return status(session, account)
        raise HTTPException(409, "Pilot terms were already accepted; baseline is immutable")
    now = _now()
    row.accepted_at = now
    row.expires_at = three_months_after(now)
    row.state = "active"
    session.add(
        FeedbackResponse(
            account_id=account.id,
            survey_key="baseline",
            survey_version=SURVEY_VERSION,
            answers=answers,
            submitted_at=now,
        )
    )
    _audit(session, account.id, account.id, "accept", now, survey_key="baseline")
    _commit(session)
    return status(session, account, now)


def submit(session: Session, account: Account, body: SurveyInput) -> dict[str, Any]:
    row = _locked(session, account)
    answers = body.answers.model_dump()
    previous = session.get(FeedbackResponse, (account.id, body.survey_key))
    if previous is not None:
        if previous.answers != answers:
            raise HTTPException(409, "This survey was already submitted; responses are immutable")
        _commit(session)
        return status(session, account)
    now = _now()
    current = status(session, account, now)
    if row.state != "active" or current["state"] == "expired":
        raise HTTPException(409, "An active accepted pilot is required")
    due = current["due_survey"]
    if due is None or due["key"] != body.survey_key:
        raise HTTPException(409, "Only the earliest due survey can be submitted")
    session.add(
        FeedbackResponse(
            account_id=account.id,
            survey_key=body.survey_key,
            survey_version=SURVEY_VERSION,
            answers=answers,
            submitted_at=now,
        )
    )
    _audit(session, account.id, account.id, "submit", now, survey_key=body.survey_key)
    _commit(session)
    return status(session, account, now)


def revoke(
    request: Request, session: Session, settings: Settings, account_id: str, body: RevokeInput
) -> dict[str, Any]:
    owner = admin.require_owner(request, session, settings, write=True)
    target = session.get(Account, account_id)
    if target is None:
        raise HTTPException(404, "Account not found")
    row = _locked(session, target)
    if row.state != "revoked":
        now = _now()
        row.state = "revoked"
        row.revoked_at = now
        _audit(session, owner.id, target.id, "revoke", now, reason=body.reason)
    _commit(session)
    return status(session, target, settings=settings)


def cohort(request: Request, session: Session, settings: Settings) -> dict[str, Any]:
    admin.require_owner(request, session, settings, write=False)
    rows = session.scalars(
        select(Account)
        .join(FeedbackEnrollment, FeedbackEnrollment.account_id == Account.id)
        .order_by(FeedbackEnrollment.invited_at.desc(), Account.id)
        .limit(500)
    ).all()
    now = _now()
    return {
        "enrollments": [
            {
                "account_id": row.id,
                "email": row.email,
                **status(session, row, now, settings=settings),
            }
            for row in rows
        ]
    }


def report(request: Request, session: Session, settings: Settings) -> dict[str, Any]:
    admin.require_owner(request, session, settings, write=False)
    responses = session.execute(
        select(FeedbackResponse, Account.email)
        .join(Account, FeedbackResponse.account_id == Account.id)
        .order_by(FeedbackResponse.submitted_at.desc(), FeedbackResponse.account_id)
        .limit(500)
    ).all()
    events = session.scalars(
        select(FeedbackAudit).order_by(FeedbackAudit.created_at.desc(), FeedbackAudit.id).limit(200)
    ).all()
    trial_responses = session.execute(
        select(TrialResponse, Account.email)
        .join(Account, TrialResponse.account_id == Account.id)
        .order_by(TrialResponse.submitted_at.desc(), TrialResponse.account_id)
        .limit(500)
    ).all()
    combined: list[dict[str, Any]] = [
        {
            "account_id": row.account_id,
            "email": email,
            "survey_key": row.survey_key,
            "survey_version": row.survey_version,
            "answers": row.answers,
            "submitted_at": row.submitted_at,
        }
        for row, email in responses
    ] + [
        {
            "account_id": row.account_id,
            "email": email,
            "survey_key": f"self-service-day{row.day}",
            "survey_version": 1,
            "answers": row.answers,
            "submitted_at": row.submitted_at,
        }
        for row, email in trial_responses
    ]
    combined.sort(key=lambda value: (-value["submitted_at"], value["account_id"]))
    return {
        "responses": combined[:500],
        "events": [
            {
                "id": row.id,
                "actor_account_id": row.actor_account_id,
                "target_account_id": row.target_account_id,
                "action": row.action,
                "survey_key": row.survey_key,
                "reason": row.reason,
                "created_at": row.created_at,
            }
            for row in events
        ],
    }
