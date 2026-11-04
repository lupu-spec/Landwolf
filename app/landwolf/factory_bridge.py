"""Owner-approved, durable handoffs to the existing outbound-only local runner."""

import json
import time
import uuid
from collections.abc import Iterator
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import Field
from sqlalchemy import JSON, ForeignKey, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from landwolf import admin, auth
from landwolf.config import Settings
from landwolf.db import Base
from landwolf.lupuspec import ConceptRequest
from landwolf.portal_models import PortalAudit, WorkItem
from landwolf.schemas import Contract

ORIGIN = "https://l91-production-api.l91-lupu.workers.dev"


class FactoryDispatch(Base):
    """One immutable request per service work item; retries cannot create another job."""

    __tablename__ = "lw2_factory_dispatches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("lw2_service_work.id"), unique=True)
    approved_by: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"))
    work_revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer)


class RunInput(Contract):
    revision: int = Field(ge=1)
    project_key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*$")
    runtime: Literal["python", "node", "rust"]
    acceptance: str = Field(default="", max_length=4000)
    confirmed: Literal[True]


def exchange(settings: Settings, method: str, path: str, payload: Any = None) -> dict[str, Any]:
    """Fixed destination and bounded response. Never forward cookies or raw transport errors."""
    if settings.factory_token is None:
        raise HTTPException(503, "Factory connection is not configured")
    try:
        with (
            httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client,
            client.stream(
                method,
                ORIGIN + path,
                headers={"Authorization": "Bearer " + settings.factory_token.get_secret_value()},
                **({"json": payload} if payload is not None else {}),
            ) as response,
        ):
            if response.status_code == 404:
                raise HTTPException(404, "Factory has not received this request")
            if response.status_code == 409:
                raise HTTPException(409, "Factory task changed or target is unavailable; refresh")
            if response.status_code not in {200, 201}:
                raise HTTPException(503, "Factory unavailable; retry this request")
            content = bytearray()
            for chunk in response.iter_bytes(16384):
                content.extend(chunk)
                if len(content) > 900_000:
                    raise HTTPException(502, "Factory response exceeds the size limit")
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("Expected object")
            return data
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Factory unavailable; retry this request") from None


def visible(dispatch: FactoryDispatch, remote: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": dispatch.id,
        "work_id": dispatch.work_id,
        "state": "pending",
        "title": dispatch.payload["title"],
        "goal": dispatch.payload["goal"],
        "runtime": dispatch.payload["runtime"],
        "project_key": dispatch.payload["project_key"],
        "acceptance": dispatch.payload["acceptance"],
        "factory_url": "https://l91.landwolf.ai/",
    }
    if remote is not None:
        if remote.get("id") != dispatch.id or remote.get("state") not in {
            "queued",
            "running",
            "completed",
            "failed",
            "cancelled",
        }:
            raise HTTPException(502, "Invalid factory response")
        try:
            task_id = str(uuid.UUID(remote["task_id"]))
        except (KeyError, ValueError, TypeError, AttributeError):
            raise HTTPException(502, "Invalid factory response") from None
        result.update(
            task_id=task_id,
            state=remote["state"],
            stage=str(remote.get("stage", ""))[:100],
            message=str(remote.get("message", ""))[:500],
            result=remote.get("result"),
        )
        output = remote.get("result")
        report = output.get("report") if isinstance(output, dict) else None
        if (
            result["state"] == "completed"
            and isinstance(report, dict)
            and report.get("status") == "FAILED_OR_BLOCKED"
        ):
            result["state"] = "failed"
            result["message"] = "FACTORY CHECKS FAILED. REVIEW THE REPORT. CODE WAS NOT APPLIED."
    return result


def register(app: FastAPI, settings: Settings, factory: sessionmaker[Session]) -> None:
    def db() -> Iterator[Session]:
        with factory() as session:
            yield session

    DB = Annotated[Session, Depends(db)]

    @app.get("/api/portal/work/{work_id}/factory")
    def customer_status(work_id: str, request: Request, session: DB) -> dict[str, str]:
        from landwolf.customer_portal import scoped_project

        account = auth.authenticate(request, session, settings)
        auth.limit(session, f"customer-factory-status:{account.id}", 60, 60)
        work = session.get(WorkItem, work_id)
        if work is None:
            raise HTTPException(404, "Work not found")
        scoped_project(session, account, work.request_id)
        dispatch = session.scalar(select(FactoryDispatch).where(FactoryDispatch.work_id == work_id))
        if dispatch is None:
            return {"state": "not_started"}
        try:
            remote = visible(dispatch, exchange(settings, "GET", "/portal/jobs/" + dispatch.id))
        except HTTPException as error:
            if error.status_code not in {404, 502, 503}:
                raise
            return {"state": "status_unavailable"}
        # No code, report, local paths, job IDs, errors or contact data cross this boundary.
        return {"state": "awaiting_review" if remote["state"] == "completed" else remote["state"]}

    @app.get("/api/admin/portal/factory/targets")
    def targets(request: Request, session: DB) -> dict[str, Any]:
        owner = admin.require_owner(request, session, settings, write=False)
        auth.limit(session, f"factory-targets:{owner.id}", 20, 60)
        return exchange(settings, "GET", "/portal/targets")

    @app.get("/api/admin/portal/work/{work_id}/factory")
    def status(work_id: str, request: Request, session: DB) -> dict[str, Any]:
        owner = admin.require_owner(request, session, settings, write=False)
        auth.limit(session, f"factory-status:{owner.id}", 60, 60)
        dispatch = session.scalar(select(FactoryDispatch).where(FactoryDispatch.work_id == work_id))
        if dispatch is None:
            return {"dispatch": None}
        try:
            remote = exchange(settings, "GET", "/portal/jobs/" + dispatch.id)
            return {"dispatch": visible(dispatch, remote)}
        except HTTPException as error:
            if error.status_code not in {404, 503}:
                raise
            return {
                "dispatch": {
                    **visible(dispatch),
                    "message": "STATUS UNAVAILABLE. RETRY THE SAME REQUEST.",
                }
            }

    @app.post("/api/admin/portal/work/{work_id}/factory", status_code=201)
    def run(work_id: str, body: RunInput, request: Request, session: DB) -> dict[str, Any]:
        owner = admin.require_owner(request, session, settings, write=True)
        auth.limit(session, f"factory-dispatch:{owner.id}", 10, 60)
        if settings.factory_token is None:
            raise HTTPException(503, "Factory connection is not configured")
        # A database lock serializes competing approvals with work status updates.
        work = session.scalar(select(WorkItem).where(WorkItem.id == work_id).with_for_update())
        if work is None or work.service != "software" or work.status != "approved":
            raise HTTPException(409, "Approve the software work before running it")
        if work.revision != body.revision:
            raise HTTPException(409, "Work changed; refresh and review before running")
        item = session.get_one(ConceptRequest, work.request_id)
        payload = {
            "title": item.title[:120],
            "goal": item.text,
            "runtime": body.runtime,
            "project_key": body.project_key,
            "acceptance": body.acceptance.strip(),
        }
        dispatch = session.scalar(select(FactoryDispatch).where(FactoryDispatch.work_id == work_id))
        if dispatch is None:
            targets = exchange(settings, "GET", "/portal/targets")
            allowed = any(
                project.get("id") == body.project_key
                and body.runtime in project.get("runtimes", [])
                for runner in targets.get("runners", [])
                for project in runner.get("projects", [])
            )
            if not allowed:
                raise HTTPException(409, "Choose an available factory project and runtime")
            dispatch = FactoryDispatch(
                id=str(uuid.uuid4()),
                work_id=work.id,
                approved_by=owner.id,
                work_revision=work.revision,
                payload=payload,
                created_at=int(time.time()),
            )
            session.add(dispatch)
            session.add(
                PortalAudit(
                    id=str(uuid.uuid4()),
                    actor_id=owner.id,
                    action="factory_run_approved",
                    resource_id=work.id,
                    created_at=int(time.time()),
                )
            )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                dispatch = session.scalar(
                    select(FactoryDispatch).where(FactoryDispatch.work_id == work_id)
                )
                if dispatch is None:
                    raise HTTPException(409, "Work changed; refresh and retry") from None
        else:
            session.commit()
        if dispatch.payload != payload or dispatch.work_revision != body.revision:
            raise HTTPException(
                409, "This work already has a factory request; open its existing run"
            )
        # Durable identity is committed BEFORE network I/O. Ambiguous timeouts use
        # the same ID and immutable snapshot; the factory enforces idempotency too.
        remote = exchange(settings, "PUT", "/portal/jobs/" + dispatch.id, dispatch.payload)
        return {"dispatch": visible(dispatch, remote)}

    @app.post("/api/admin/portal/work/{work_id}/factory/cancel")
    def cancel(work_id: str, request: Request, session: DB) -> dict[str, Any]:
        owner = admin.require_owner(request, session, settings, write=True)
        auth.limit(session, f"factory-cancel:{owner.id}", 10, 60)
        dispatch = session.scalar(select(FactoryDispatch).where(FactoryDispatch.work_id == work_id))
        if dispatch is None:
            raise HTTPException(404, "Factory request not found")
        remote = exchange(settings, "POST", "/portal/jobs/" + dispatch.id + "/cancel", {})
        session.add(
            PortalAudit(
                id=str(uuid.uuid4()),
                actor_id=owner.id,
                action="factory_cancel_requested",
                resource_id=work_id,
                created_at=int(time.time()),
            )
        )
        session.commit()
        return {"dispatch": visible(dispatch, remote)}
