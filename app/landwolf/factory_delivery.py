"""Materialize explicit factory delivery decisions into the scoped customer portal."""

import base64
import hashlib
import re
import time
import uuid
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, Response
from sqlalchemy import Boolean, ForeignKey, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from landwolf.config import Settings
from landwolf.db import Base
from landwolf.lupuspec import ConceptRequest
from landwolf.portal_models import PortalAudit, ProjectMessage, WorkItem


class FactoryDelivery(Base):
    __tablename__ = "lw2_factory_deliveries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dispatch_id: Mapped[str] = mapped_column(ForeignKey("lw2_factory_dispatches.id"))
    work_id: Mapped[str] = mapped_column(ForeignKey("lw2_service_work.id"), index=True)
    version: Mapped[str] = mapped_column(String(40))
    url: Mapped[str] = mapped_column(String(300))
    source_sha256: Mapped[str] = mapped_column(String(64))
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[int] = mapped_column(Integer)


def validated_release(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict) or value.get("state") != "delivered":
        return None
    try:
        release_id = str(uuid.UUID(value["id"]))
        version = value["version"]
        target = value["target"]
        address = value["production_url"]
        parsed = urlparse(address)
        report = value["report"]
        if (
            not isinstance(version, str)
            or not re.fullmatch(r"\d{1,4}\.\d{1,4}\.\d{1,4}", version)
            or not isinstance(target, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", target)
            or parsed.scheme != "https"
            or parsed.netloc != target + ".pages.dev"
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or value.get("has_source") is not True
            or report.get("schema") != "l91.release-checks.v1"
            or report.get("passed") is not True
            or report.get("operation") != "publish"
            or report.get("artifact_sha256") != value["artifact_sha256"]
            or not re.fullmatch(r"[a-f0-9]{64}", value["artifact_sha256"])
            or not re.fullmatch(r"[a-f0-9]{64}", value["source_sha256"])
        ):
            raise ValueError("Invalid receipt")
        return {
            "id": release_id,
            "version": version,
            "url": "https://" + parsed.netloc,
            "artifact_sha256": value["artifact_sha256"],
            "source_sha256": value["source_sha256"],
        }
    except (KeyError, ValueError, TypeError, AttributeError):
        raise HTTPException(502, "Invalid factory delivery receipt") from None


def delivery_history(remote: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, str] | None]]:
    """Validate the bounded delivery projection before changing any local record."""
    values = remote.get("releases")
    if values is None:  # Compatibility with the previous bridge during rollout.
        values = [remote.get("release")]
    if not isinstance(values, list) or len(values) > 30:
        raise HTTPException(502, "Invalid factory delivery history")
    result = []
    seen = set()
    for value in values:
        if value is None:
            continue
        if not isinstance(value, dict):
            raise HTTPException(502, "Invalid factory delivery history")
        if value.get("state") not in {"delivered", "rolled_back"}:
            continue
        try:
            release_id = str(uuid.UUID(value["id"]))
        except (KeyError, ValueError, TypeError, AttributeError):
            raise HTTPException(502, "Invalid factory delivery identity") from None
        if release_id in seen:
            raise HTTPException(502, "Duplicate factory delivery identity")
        seen.add(release_id)
        result.append((value, validated_release(value)))
    return result


def sync_deliveries(session: Session, settings: Settings, request_id: str) -> None:
    """Refresh authorized delivery history, independently of the newest build attempt."""
    from landwolf.factory_bridge import FactoryDispatch, exchange, visible

    if settings.factory_token is None:
        return
    rows = session.execute(
        select(FactoryDispatch, WorkItem)
        .join(WorkItem, WorkItem.id == FactoryDispatch.work_id)
        .where(WorkItem.request_id == request_id, WorkItem.service == "software")
    ).all()
    for dispatch, known_work in rows:
        try:
            remote = exchange(settings, "GET", "/portal/jobs/" + dispatch.id)
            visible(dispatch, remote)
            history = delivery_history(remote)
        except HTTPException as error:
            if error.status_code in {404, 502, 503}:
                continue
            raise
        work = session.scalar(
            select(WorkItem).where(WorkItem.id == known_work.id).with_for_update()
        )
        if work is None or not history:
            continue
        changed = False
        now = int(time.time())
        for release, receipt in history:
            prior = session.get(FactoryDelivery, str(release["id"]))
            if prior and (prior.dispatch_id != dispatch.id or prior.work_id != work.id):
                raise HTTPException(502, "Delivery identity changed")
            if receipt is None:
                if prior and prior.active:
                    prior.active = False
                    changed = True
                continue
            if prior:
                if any(
                    getattr(prior, key) != receipt[key]
                    for key in ("version", "url", "artifact_sha256", "source_sha256")
                ):
                    raise HTTPException(502, "Delivery identity changed")
                if not prior.active:
                    prior.active = True
                    changed = True
                continue
            session.add(
                FactoryDelivery(
                    **receipt,
                    dispatch_id=dispatch.id,
                    work_id=work.id,
                    active=True,
                    created_at=now,
                )
            )
            session.add(
                ProjectMessage(
                    id=str(uuid.uuid4()),
                    request_id=work.request_id,
                    customer_id=work.customer_id,
                    actor_id=dispatch.approved_by,
                    submission_id=receipt["id"],
                    author="team",
                    text=(
                        f"RELEASE {receipt['version']}\n{receipt['url']}\n"
                        "CHECKS PASSED. SOURCE DOWNLOAD AVAILABLE."
                    ),
                    created_at=now,
                )
            )
            session.add(
                PortalAudit(
                    id=str(uuid.uuid4()),
                    actor_id=dispatch.approved_by,
                    action="factory_release_delivered",
                    resource_id=receipt["id"],
                    created_at=now,
                )
            )
            changed = True
        if not changed:
            continue
        if work.status != "closed":
            work.status = "delivered" if history[-1][1] is not None else "in_progress"
            work.revision += 1
        try:
            session.flush()
            unfinished = session.scalar(
                select(WorkItem.id).where(
                    WorkItem.request_id == work.request_id,
                    WorkItem.status.not_in(["delivered", "closed"]),
                )
            )
            item = session.get_one(ConceptRequest, work.request_id)
            if unfinished is None and item.status != "closed":
                item.status = "delivered"
                item.updated_at = now
            elif unfinished is not None and item.status == "delivered":
                item.status = "in_progress"
                item.updated_at = now
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "Delivery changed; refresh") from None


def public_deliveries(session: Session, request_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(FactoryDelivery)
        .join(WorkItem, WorkItem.id == FactoryDelivery.work_id)
        .where(WorkItem.request_id == request_id, FactoryDelivery.active.is_(True))
        .order_by(FactoryDelivery.created_at.desc(), FactoryDelivery.id.desc())
        .limit(30)
    ).all()
    return [
        {
            "id": row.id,
            "version": row.version,
            "url": row.url,
            "source_url": f"/api/portal/work/{row.work_id}/releases/{row.id}/source",
            "source_sha256": row.source_sha256,
            "checks": "PASSED",
        }
        for row in rows
    ]


def download(session: Session, settings: Settings, work_id: str, release_id: str) -> Response:
    from landwolf.factory_bridge import exchange

    release = session.get(FactoryDelivery, release_id)
    if release is None or release.work_id != work_id or not release.active:
        raise HTTPException(404, "Delivered release not found")
    data = exchange(
        settings,
        "GET",
        f"/portal/jobs/{release.dispatch_id}/releases/{release.id}/source",
    )
    try:
        content = base64.b64decode(data["base64"], validate=True)
        if len(content) > 500_000 or not content.startswith(b"PK"):
            raise ValueError("Invalid package")
        if hashlib.sha256(content).hexdigest() != release.source_sha256:
            raise ValueError("Hash mismatch")
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, "Source package could not be verified") from None
    return Response(
        content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="source-{release.version}.zip"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
