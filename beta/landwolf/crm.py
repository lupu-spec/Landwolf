"""LandWolf authentication adapter for the portable, project-scoped CRM."""

import csv
import io
import secrets
import time
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from landwolf import admin, auth
from landwolf import crm_core as core
from landwolf.config import Settings
from landwolf.feedback_export import spreadsheet_text


def register(app: FastAPI, settings: Settings, factory: sessionmaker[Session]) -> None:
    def db() -> Iterator[Session]:
        with factory() as session:
            try:
                yield session
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(
                    409, "Record already exists or changed. Refresh and retry."
                ) from exc
            except SQLAlchemyError as exc:
                session.rollback()
                raise HTTPException(503, "CRM is temporarily unavailable. Please retry.") from exc

    DB = Annotated[Session, Depends(db)]

    def owned(request: Request, session: Session, *, write: bool = False) -> str:
        owner = admin.require_owner(request, session, settings, write=write)
        if write:
            auth.limit(session, f"crm-write:{owner.id}", 60)
        return owner.id

    def contact(session: Session, contact_id: str) -> core.Contact:
        row = session.get(core.Contact, contact_id)
        if row is None:
            raise HTTPException(404, "Contact not found")
        return row

    @app.get("/api/admin/crm/projects")
    def projects(request: Request, session: DB) -> dict[str, Any]:
        owned(request, session)
        return {
            "projects": [
                {"id": p.id, "name": p.name, "connected": p.token_hash is not None}
                for p in session.scalars(select(core.Project).order_by(core.Project.name))
            ],
            "categories": {
                "industries": core.INDUSTRIES,
                "uses": core.USES,
                "stages": core.STAGES,
                "contact_types": core.CONTACT_TYPES,
            },
        }

    @app.post("/api/admin/crm/projects", status_code=201)
    def create_project(body: core.NewProject, request: Request, session: DB) -> dict[str, str]:
        owned(request, session, write=True)
        if (session.scalar(select(func.count()).select_from(core.Project)) or 0) >= 100:
            raise HTTPException(409, "Project limit reached")
        token = core.new_token()
        session.add(
            core.Project(
                id=body.id,
                name=body.name,
                token_hash=core.token_digest(token),
                created_at=int(time.time()),
            )
        )
        session.commit()
        return {"id": body.id, "token": token}

    @app.post("/api/admin/crm/projects/{project_id}/rotate-key")
    def rotate_key(project_id: str, request: Request, session: DB) -> dict[str, str]:
        owned(request, session, write=True)
        row = session.get(core.Project, project_id)
        if row is None or project_id == "landwolf":
            raise HTTPException(404, "External project not found")
        token = core.new_token()
        row.token_hash = core.token_digest(token)
        session.commit()
        return {"id": row.id, "token": token}

    @app.delete("/api/admin/crm/projects/{project_id}/key")
    def revoke_key(project_id: str, request: Request, session: DB) -> dict[str, bool]:
        owned(request, session, write=True)
        row = session.get(core.Project, project_id)
        if row is None or project_id == "landwolf":
            raise HTTPException(404, "External project not found")
        row.token_hash = None
        session.commit()
        return {"revoked": True}

    @app.post("/api/crm/v1/projects/{project_id}/registrations")
    def intake(project_id: str, body: core.Intake, request: Request, session: DB) -> dict[str, str]:
        # Server-to-server only: project keys must never be embedded in a browser.
        if request.headers.get("origin"):
            raise HTTPException(403, "Use this connector from your project server")
        ip = request.client.host if request.client else "unknown"
        auth.limit(session, f"crm-intake-ip:{ip}", 120)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        row = session.get(core.Project, project_id)
        if (
            len(token) != 43
            or row is None
            or row.token_hash is None
            or project_id == "landwolf"
            or not secrets.compare_digest(core.token_digest(token), row.token_hash)
        ):
            raise HTTPException(401, "Invalid project credential")
        auth.limit(session, f"crm-intake:{row.id}", 120)
        try:
            record = core.capture(session, row.id, body, source="registration_api")
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        session.commit()
        return {"contact_id": record.id, "status": "captured"}

    def filtered(project_id: str, q: str, lifecycle: str, industry: str, primary_use: str) -> Any:
        stmt = select(core.Contact)
        for field, value in (
            (core.Contact.project_id, project_id),
            (core.Contact.lifecycle, lifecycle),
            (core.Contact.industry, industry),
            (core.Contact.primary_use, primary_use),
        ):
            if value:
                stmt = stmt.where(field == value)
        if q:
            term = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            stmt = stmt.where(
                or_(
                    *(
                        field.ilike(term, escape="\\")
                        for field in (
                            core.Contact.full_name,
                            core.Contact.email,
                            core.Contact.company,
                        )
                    )
                )
            )
        return stmt.order_by(core.Contact.created_at.desc(), core.Contact.id)

    @app.get("/api/admin/crm/contacts")
    def contacts(
        request: Request,
        session: DB,
        project_id: str = Query("", max_length=40),
        q: str = Query("", max_length=120),
        lifecycle: str = Query("", max_length=24),
        industry: str = Query("", max_length=40),
        primary_use: str = Query("", max_length=40),
        page: int = Query(1, ge=1, le=100000),
    ) -> dict[str, Any]:
        owned(request, session)
        stmt = filtered(project_id, q, lifecycle, industry, primary_use)
        total = (
            session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        )
        rows = session.scalars(stmt.limit(50).offset((page - 1) * 50))
        return {
            "contacts": [core.serialize(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": 50,
        }

    @app.get("/api/admin/crm/contacts.csv")
    def export(
        request: Request,
        session: DB,
        project_id: str = Query("", max_length=40),
        q: str = Query("", max_length=120),
        lifecycle: str = Query("", max_length=24),
        industry: str = Query("", max_length=40),
        primary_use: str = Query("", max_length=40),
    ) -> Response:
        owned(request, session)
        rows = list(
            session.scalars(filtered(project_id, q, lifecycle, industry, primary_use).limit(10001))
        )
        if len(rows) > 10000:
            raise HTTPException(409, "Export exceeds 10,000 contacts. Narrow the filters.")
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        keys = [
            "project_id",
            "full_name",
            "email",
            "company",
            "phone",
            "job_title",
            "industry",
            "contact_type",
            "primary_use",
            "use_details",
            "lifecycle",
            "source",
            "marketing_opt_in",
            "consent_version",
            "consent_recorded_at",
            "tags",
            "follow_up_on",
            "created_at",
        ]
        writer.writerow(keys)
        for row in rows:
            values = core.serialize(row)
            writer.writerow(
                [
                    spreadsheet_text(
                        ", ".join(values[k])
                        if isinstance(values[k], list)
                        else str(values[k])
                        if values[k] is not None
                        else ""
                    )
                    for k in keys
                ]
            )
        return Response(
            content=("\ufeff" + output.getvalue()).encode(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="l91-llc-crm-contacts.csv"'},
        )

    @app.get("/api/admin/crm/contacts/{contact_id}")
    def detail(contact_id: str, request: Request, session: DB) -> dict[str, Any]:
        owned(request, session)
        row = contact(session, contact_id)
        activities = session.scalars(
            select(core.Activity)
            .where(core.Activity.contact_id == row.id)
            .order_by(core.Activity.created_at.desc(), core.Activity.id)
            .limit(100)
        )
        return {
            "contact": core.serialize(row),
            "activities": [
                {"kind": a.kind, "text": a.text, "created_at": a.created_at} for a in activities
            ],
        }

    @app.patch("/api/admin/crm/contacts/{contact_id}")
    def edit(
        contact_id: str, body: core.ContactUpdate, request: Request, session: DB
    ) -> dict[str, Any]:
        actor = owned(request, session, write=True)
        contact(session, contact_id)
        changed = session.scalar(
            update(core.Contact)
            .where(core.Contact.id == contact_id, core.Contact.revision == body.revision)
            .values(
                **body.model_dump(exclude={"revision"}),
                revision=body.revision + 1,
                updated_at=int(time.time()),
            )
            .returning(core.Contact.id)
        )
        if changed is None:
            raise HTTPException(409, "Contact changed. Reopen it and retry.")
        core.record_activity(session, contact_id, actor, "updated", f"Stage: {body.lifecycle}")
        session.commit()
        return core.serialize(contact(session, contact_id))

    @app.post("/api/admin/crm/contacts/{contact_id}/notes", status_code=201)
    def add_note(
        contact_id: str, body: core.Note, request: Request, session: DB
    ) -> dict[str, bool]:
        actor = owned(request, session, write=True)
        contact(session, contact_id)
        core.record_activity(session, contact_id, actor, "note", body.text)
        session.commit()
        return {"saved": True}

    @app.post("/api/admin/crm/contacts/{contact_id}/unsubscribe")
    def unsubscribe(contact_id: str, request: Request, session: DB) -> dict[str, bool]:
        actor = owned(request, session, write=True)
        contact(session, contact_id)
        session.execute(
            update(core.Contact)
            .where(core.Contact.id == contact_id)
            .values(
                marketing_opt_in=False,
                consent_recorded_at=int(time.time()),
                revision=core.Contact.revision + 1,
                updated_at=int(time.time()),
            )
        )
        core.record_activity(session, contact_id, actor, "unsubscribed")
        session.commit()
        return {"unsubscribed": True}
