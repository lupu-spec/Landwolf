"""Account-scoped research persistence, on-open decisions and shared Hunt briefs."""

import hashlib
import json
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from landwolf import auth, billing
from landwolf.config import Settings
from landwolf.db import Account, Hunt, Listing, ResearchCase, ResearchGoal
from landwolf.decisions import (
    MAX_CASES,
    MAX_HISTORY,
    CaseInput,
    CompareInput,
    Goal,
    GoalInput,
    comparison,
    evaluate,
)
from landwolf.schemas import PropertyRecord


def owned_hunt(session: Session, account_id: str, hunt_id: str) -> Hunt:
    row = session.get(Hunt, hunt_id)
    if row is None or row.account_id != account_id:
        raise HTTPException(404, "Hunt not found")
    return row


def goal_for_hunt(session: Session, hunt: Hunt) -> tuple[Goal, int]:
    row = session.get(ResearchGoal, hunt.id)
    return (Goal.model_validate(row.payload), row.revision) if row else (Goal(), 0)


def record_for_case(session: Session, row: ResearchCase) -> tuple[PropertyRecord, bool]:
    listing = session.get(Listing, row.listing_id)
    record = PropertyRecord.model_validate(listing.payload if listing else row.source_snapshot)
    today = datetime.now(UTC).date()
    available = bool(listing and listing.active and record.active)
    available = available and all(
        d is None or d >= today for d in (record.auction_date, record.bidding_deadline)
    )
    return record, available


def snapshot(record: PropertyRecord) -> dict[str, Any]:
    """Keep only bounded source facts needed after inventory removal."""
    return record.model_dump(
        mode="json",
        include={
            "id",
            "source",
            "source_name",
            "source_url",
            "tract",
            "title",
            "state",
            "county",
            "acres",
            "asking_price",
            "price_kind",
            "parcel_number",
            "retrieved_at",
            "active",
            "auction_date",
            "bidding_deadline",
            "category",
            "sale_status",
        },
    )


def case_payload(session: Session, row: ResearchCase, *, persist: bool = True) -> dict[str, Any]:
    spec = CaseInput.model_validate(row.payload)
    record, available = record_for_case(session, row)
    goal = spec.goal
    if row.hunt_id:
        goal, _ = goal_for_hunt(session, owned_hunt(session, row.account_id, row.hunt_id))
    decision = evaluate(spec, goal, record, available=available)
    inputs = {
        "goal": goal.model_dump(),
        "spec": spec.model_dump(mode="json", exclude={"revision"}),
        "price": record.asking_price,
        "price_kind": record.price_kind,
        "available": available,
        "parcel_number": record.parcel_number,
        "state": record.state,
        "county": record.county,
    }
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    history = list(row.history)
    if fingerprint != row.fingerprint and row.fingerprint:
        before = row.evaluation.get("pause_condition_met")
        after = decision["pause_condition_met"]
        if spec.pause_reason and before is not True and after is True:
            message = (
                "The condition behind your pause is now met under the recorded "
                "evidence and assumptions."
            )
            if decision["blockers"]:
                message += " Other requirements still need attention."
            kind = "reconsider"
        elif spec.pause_reason and before is True and after is not True:
            message = (
                "The condition behind your pause is no longer confirmed as met. "
                "Review the changed evidence."
            )
            kind = "review"
        else:
            message = (
                "Decision inputs changed. Review the updated costs, requirements and evidence."
            )
            kind = "updated"
        history = [
            {
                "kind": kind,
                "message": message,
                "at": int(time.time()),
                "previous_allowance": row.evaluation.get("costs", {}).get("allowance"),
                "allowance": decision["costs"]["allowance"],
            },
            *history,
        ][:MAX_HISTORY]
    if persist and fingerprint != row.fingerprint:
        # Serialize account operations on PostgreSQL; CAS also protects SQLite edits.
        session.execute(
            update(ResearchCase)
            .where(
                ResearchCase.account_id == row.account_id,
                ResearchCase.listing_id == row.listing_id,
                ResearchCase.revision == row.revision,
                ResearchCase.fingerprint == row.fingerprint,
            )
            .values(
                fingerprint=fingerprint,
                evaluation=decision,
                history=history,
                source_snapshot=snapshot(record),
            ),
            execution_options={"synchronize_session": False},
        )
    return {
        "listing_id": row.listing_id,
        "revision": row.revision,
        "hunt_id": row.hunt_id,
        "input": {**spec.model_dump(mode="json"), "revision": row.revision},
        "effective_goal": goal.model_dump(),
        "property": snapshot(record),
        "available": available,
        "decision": decision,
        "history": history,
        "updated_at": row.updated_at,
    }


def shared_brief(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Only confirmed planning authorities can combine permitted-use questions."""
    groups: dict[tuple[str, ...], dict[str, Any]] = {}
    for case in cases:
        record, spec, goal = case["property"], case["input"], case["effective_goal"]
        for question in case["decision"]["questions"]:
            shared = question["topic"] == "use" and spec["authority_confirmed"]
            authority = (
                spec["authority"].strip()
                if shared
                else "Confirm the responsible professional or agency"
            )
            key: tuple[str, ...] = (
                record["state"],
                authority.casefold(),
                goal["intended_use"],
                goal["use_details"].strip().casefold(),
                question["topic"],
            )
            if not shared:
                key = (*key, record["id"])
            if key not in groups:
                groups[key] = {
                    "authority": authority,
                    "topic": question["label"],
                    "intended_use": goal["intended_use"],
                    "use_details": goal["use_details"],
                    "shared": shared,
                    "properties": [],
                }
            groups[key]["properties"].append(
                {
                    "listing_id": record["id"],
                    "title": record["title"],
                    "parcel_number": record.get("parcel_number"),
                    "state": record["state"],
                    "county": record.get("county"),
                    "question": question["question"],
                    "reason": question["reason"],
                }
            )
    return sorted(
        groups.values(), key=lambda g: (-len(g["properties"]), g["authority"], g["topic"])
    )


def register(app: FastAPI, settings: Settings, factory: sessionmaker[Session]) -> None:
    """Register ordinary app routes, preserving existing route/security inspection."""
    routes = app

    def db() -> Iterator[Session]:
        with factory() as session:
            try:
                yield session
            except SQLAlchemyError as exc:
                session.rollback()
                raise HTTPException(
                    503, "Research storage is temporarily unavailable. Retry shortly."
                ) from exc

    DB = Annotated[Session, Depends(db)]

    def customer(request: Request, session: Session, *, write: bool = False) -> Account:
        account = auth.authenticate(request, session, settings, write=write)
        billing.require_access(session, account, settings)
        auth.limit(session, f"decision:{account.id}", 90)
        session.execute(select(Account.id).where(Account.id == account.id).with_for_update())
        return account

    @routes.get("/api/decision-cases/{listing_id}")
    def get_case(listing_id: str, request: Request, session: DB) -> dict[str, Any]:
        account = customer(request, session)
        row = session.get(ResearchCase, (account.id, listing_id))
        if row is None:
            listing = session.get(Listing, listing_id)
            if listing is None:
                raise HTTPException(404, "Property not found")
            record = PropertyRecord.model_validate(listing.payload)
            row = ResearchCase(
                account_id=account.id,
                listing_id=listing_id,
                hunt_id=None,
                payload=CaseInput().model_dump(mode="json"),
                source_snapshot=snapshot(record),
                revision=0,
                fingerprint="",
                evaluation={},
                history=[],
                updated_at=0,
            )
            return case_payload(session, row, persist=False)
        result = case_payload(session, row)
        session.commit()
        return result

    @routes.post("/api/decision-preview/{listing_id}")
    def preview(listing_id: str, body: CaseInput, request: Request, session: DB) -> dict[str, Any]:
        account = customer(request, session, write=True)
        if body.hunt_id:
            owned_hunt(session, account.id, body.hunt_id)
        listing = session.get(Listing, listing_id)
        existing = session.get(ResearchCase, (account.id, listing_id))
        if listing is None and existing is None:
            raise HTTPException(404, "Property not found")
        retained = listing.payload if listing else existing.source_snapshot if existing else {}
        row = ResearchCase(
            account_id=account.id,
            listing_id=listing_id,
            hunt_id=body.hunt_id,
            payload=body.model_dump(mode="json"),
            source_snapshot=retained,
            revision=body.revision,
            fingerprint="",
            evaluation={},
            history=[],
            updated_at=0,
        )
        return case_payload(session, row, persist=False)

    @routes.put("/api/decision-cases/{listing_id}")
    def put_case(listing_id: str, body: CaseInput, request: Request, session: DB) -> dict[str, Any]:
        account = customer(request, session, write=True)
        if body.hunt_id:
            owned_hunt(session, account.id, body.hunt_id)
        row = session.get(ResearchCase, (account.id, listing_id))
        listing = session.get(Listing, listing_id)
        if listing is None and row is None:
            raise HTTPException(404, "Property not found")
        if body.revision != (row.revision if row else 0):
            raise HTTPException(409, "Research changed in another tab. Reload before editing.")
        now = int(time.time())
        if row is None:
            if listing is None:
                raise HTTPException(404, "Property not found")
            count = (
                session.scalar(
                    select(func.count())
                    .select_from(ResearchCase)
                    .where(ResearchCase.account_id == account.id)
                )
                or 0
            )
            if count >= MAX_CASES:
                raise HTTPException(
                    409, "Remove an old research record before adding another (limit 50)."
                )
            row = ResearchCase(
                account_id=account.id,
                listing_id=listing_id,
                hunt_id=body.hunt_id,
                payload=body.model_dump(mode="json"),
                source_snapshot=snapshot(PropertyRecord.model_validate(listing.payload)),
                revision=1,
                fingerprint="",
                evaluation={},
                history=[],
                updated_at=now,
            )
            session.add(row)
            session.flush()
        else:
            changed = session.execute(
                update(ResearchCase)
                .where(
                    ResearchCase.account_id == account.id,
                    ResearchCase.listing_id == listing_id,
                    ResearchCase.revision == body.revision,
                )
                .values(
                    payload=body.model_dump(mode="json"),
                    hunt_id=body.hunt_id,
                    revision=body.revision + 1,
                    updated_at=now,
                )
                .returning(ResearchCase.revision)
            )
            if changed.scalar_one_or_none() is None:
                raise HTTPException(409, "Research changed in another tab. Reload before editing.")
            session.refresh(row)
        result = case_payload(session, row)
        session.commit()
        return result

    @routes.delete("/api/decision-cases/{listing_id}")
    def remove_case(listing_id: str, request: Request, session: DB) -> dict[str, bool]:
        account = customer(request, session, write=True)
        session.execute(
            delete(ResearchCase).where(
                ResearchCase.account_id == account.id, ResearchCase.listing_id == listing_id
            )
        )
        session.commit()
        return {"deleted": True}

    @routes.get("/api/hunts/{hunt_id}/research")
    def hunt_research(hunt_id: str, request: Request, session: DB) -> dict[str, Any]:
        account = customer(request, session)
        hunt = owned_hunt(session, account.id, hunt_id)
        goal, revision = goal_for_hunt(session, hunt)
        rows = session.scalars(
            select(ResearchCase)
            .where(ResearchCase.account_id == account.id, ResearchCase.hunt_id == hunt_id)
            .order_by(ResearchCase.updated_at.desc())
            .limit(MAX_CASES)
        ).all()
        cases = [case_payload(session, row) for row in rows]
        session.commit()
        return {
            "goal": goal.model_dump(),
            "revision": revision,
            "cases": cases,
            "brief": shared_brief(cases),
            "limit": MAX_CASES,
        }

    @routes.get("/api/hunts/{hunt_id}/research-goal")
    def get_goal(hunt_id: str, request: Request, session: DB) -> dict[str, Any]:
        account = customer(request, session)
        goal, revision = goal_for_hunt(session, owned_hunt(session, account.id, hunt_id))
        return {"goal": goal.model_dump(), "revision": revision}

    @routes.put("/api/hunts/{hunt_id}/research-goal")
    def put_goal(hunt_id: str, body: GoalInput, request: Request, session: DB) -> dict[str, Any]:
        account = customer(request, session, write=True)
        owned_hunt(session, account.id, hunt_id)
        row = session.get(ResearchGoal, hunt_id)
        if body.revision != (row.revision if row else 0):
            raise HTTPException(409, "Hunt goal changed in another tab. Reload before editing.")
        if row:
            changed = session.execute(
                update(ResearchGoal)
                .where(ResearchGoal.hunt_id == hunt_id, ResearchGoal.revision == body.revision)
                .values(
                    payload=body.goal.model_dump(),
                    revision=body.revision + 1,
                    updated_at=int(time.time()),
                )
                .returning(ResearchGoal.revision)
            )
            if changed.scalar_one_or_none() is None:
                raise HTTPException(409, "Hunt goal changed in another tab. Reload before editing.")
        else:
            session.add(
                ResearchGoal(
                    hunt_id=hunt_id,
                    payload=body.goal.model_dump(),
                    revision=1,
                    updated_at=int(time.time()),
                )
            )
        session.commit()
        return {"goal": body.goal.model_dump(), "revision": body.revision + 1}

    @routes.post("/api/hunts/{hunt_id}/research-compare")
    def compare(hunt_id: str, body: CompareInput, request: Request, session: DB) -> dict[str, Any]:
        account = customer(request, session, write=True)
        owned_hunt(session, account.id, hunt_id)
        cases = []
        for listing_id in body.listing_ids:
            row = session.get(ResearchCase, (account.id, listing_id))
            if row is None or row.hunt_id != hunt_id:
                raise HTTPException(404, "Research not found in this Hunt")
            cases.append(case_payload(session, row))
        session.commit()
        return comparison(cases[0], cases[1])
