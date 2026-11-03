"""Same-origin customer intermediary. No customer route serializes CRM or finance rows."""

import time
import uuid
from collections.abc import Iterator
from typing import Annotated, Any, Literal, Self

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import Field, field_validator, model_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from landwolf import admin, auth
from landwolf.config import Settings
from landwolf.crm_core import Contract as TextContract
from landwolf.db import Account
from landwolf.lupuspec import (
    Capability,
    ConceptRequest,
    RequestInput,
    StatusInput,
    _content_hash,
)
from landwolf.portal_models import (
    Customer,
    CustomerProject,
    PortalAudit,
    ProjectMessage,
    ServiceAccount,
    WorkItem,
)
from landwolf.schemas import Credentials


class JoinInput(Credentials):
    full_name: str = Field(min_length=1, max_length=120)

    @field_validator("full_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(character) < 32 for character in value):
            raise ValueError("Enter a name without control characters")
        return value


class ProjectInput(RequestInput):
    services: list[Capability] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def selected_services(self) -> Self:
        if len(set(self.services)) != len(self.services) or self.capability not in self.services:
            raise ValueError("Choose each service once and include the primary service")
        return self


class MessageInput(TextContract):
    submission_id: uuid.UUID
    text: str = Field(min_length=1, max_length=2000)


class LinkInput(TextContract):
    customer_id: uuid.UUID
    identity_confirmed: Literal[True]


def audit(session: Session, actor: str, action: str, resource: str) -> None:
    session.add(
        PortalAudit(
            id=str(uuid.uuid4()),
            actor_id=actor,
            action=action,
            resource_id=resource,
            created_at=int(time.time()),
        )
    )


def customer_for(session: Session, account: Account, *, create: bool = False) -> Customer | None:
    customer = session.scalar(select(Customer).where(Customer.account_id == account.id))
    if customer is None and create:
        customer = Customer(
            id=str(uuid.uuid4()),
            account_id=account.id,
            name="Customer",
            created_at=int(time.time()),
        )
        session.add(customer)
        session.flush()
    return customer


def link_project(
    session: Session,
    item: ConceptRequest,
    customer: Customer,
    services: list[str],
    actor: str,
    basis: str,
) -> None:
    """Only new authenticated submissions or an explicit owner-verified link may call this."""
    session.add(
        CustomerProject(
            request_id=item.id,
            customer_id=customer.id,
            linked_by=actor,
            link_basis=basis,
            created_at=int(time.time()),
        )
    )
    session.flush()
    for service in services:
        account = session.scalar(
            select(ServiceAccount).where(
                ServiceAccount.customer_id == customer.id, ServiceAccount.service == service
            )
        )
        if account is None:
            account = ServiceAccount(
                id=str(uuid.uuid4()),
                customer_id=customer.id,
                service=service,
                created_at=int(time.time()),
            )
            session.add(account)
            session.flush()
        session.add(
            WorkItem(
                id=str(uuid.uuid4()),
                request_id=item.id,
                customer_id=customer.id,
                service_account_id=account.id,
                service=service,
                status="received",
                revision=1,
            )
        )
    audit(session, actor, "project_linked", item.id)


def scoped_project(
    session: Session, account: Account, request_id: str
) -> tuple[ConceptRequest, CustomerProject]:
    record = session.execute(
        select(ConceptRequest, CustomerProject)
        .join(CustomerProject, CustomerProject.request_id == ConceptRequest.id)
        .join(Customer, Customer.id == CustomerProject.customer_id)
        .where(Customer.account_id == account.id, ConceptRequest.id == request_id)
    ).first()
    if record is None:
        raise HTTPException(404, "Project not found")
    return record[0], record[1]


def project_view(
    session: Session, item: ConceptRequest, link: CustomerProject, *, detail: bool = False
) -> dict[str, Any]:
    """Allowlist public project facts; never expose contact, actor IDs, CRM notes or costs."""
    work = session.scalars(
        select(WorkItem)
        .where(WorkItem.request_id == item.id, WorkItem.customer_id == link.customer_id)
        .order_by(WorkItem.service)
    ).all()
    result: dict[str, Any] = {
        "id": item.id,
        "title": item.title,
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "quantity": item.quantity,
        "services": [
            {"id": row.id, "service": row.service, "status": row.status, "revision": row.revision}
            for row in work
        ],
    }
    if detail:
        messages = session.scalars(
            select(ProjectMessage)
            .where(
                ProjectMessage.request_id == item.id, ProjectMessage.customer_id == link.customer_id
            )
            .order_by(ProjectMessage.created_at.desc(), ProjectMessage.id.desc())
            .limit(101)
        ).all()
        result.update(
            text=item.text,
            reference_url=item.reference_url,
            messages=[
                {"id": row.id, "author": row.author, "text": row.text, "created_at": row.created_at}
                for row in reversed(messages[:100])
            ],
            older_messages=len(messages) > 100,
        )
    return result


def save_message(
    session: Session, account: Account, link: CustomerProject, body: MessageInput, author: str
) -> dict[str, str]:
    prior = session.scalar(
        select(ProjectMessage).where(
            ProjectMessage.actor_id == account.id,
            ProjectMessage.submission_id == str(body.submission_id),
        )
    )
    if prior:
        if prior.request_id != link.request_id or prior.text != body.text or prior.author != author:
            raise HTTPException(409, "Message reference already used")
        return {"id": prior.id}
    row = ProjectMessage(
        id=str(uuid.uuid4()),
        request_id=link.request_id,
        customer_id=link.customer_id,
        actor_id=account.id,
        submission_id=str(body.submission_id),
        author=author,
        text=body.text,
        created_at=int(time.time()),
    )
    session.add(row)
    audit(session, account.id, "message_published", row.id)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Message changed concurrently; retry") from exc
    return {"id": row.id}


def register(app: FastAPI, settings: Settings, factory: sessionmaker[Session]) -> None:
    def db() -> Iterator[Session]:
        with factory() as session:
            yield session

    DB = Annotated[Session, Depends(db)]

    @app.post("/api/portal/register", status_code=201)
    def join(body: JoinInput, request: Request, response: Response, session: DB) -> dict[str, str]:
        auth.origin_guard(request, settings)
        ip = request.client.host if request.client else "unknown"
        auth.limit(session, f"auth:ip:{ip}", settings.auth_limit, 600)
        auth.limit(session, f"auth:account:{str(body.email).casefold()}", settings.auth_limit, 600)
        # Reuse the existing password/session implementation, without enrolling in LandWolf.
        with auth.password_work():
            hashed = auth.PASSWORDS.hash(body.password)
        account = Account(
            id=str(uuid.uuid4()), email=str(body.email).casefold(), password_hash=hashed
        )
        session.add(account)
        try:
            session.flush()
            session.add(
                Customer(
                    id=str(uuid.uuid4()),
                    account_id=account.id,
                    name=body.full_name.strip(),
                    created_at=int(time.time()),
                )
            )
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                400, "Unable to create account. Try signing in or contact support."
            ) from exc
        return auth.establish(account, request, response, session, settings)

    @app.get("/api/portal/session")
    def current(request: Request, response: Response, session: DB) -> dict[str, Any]:
        try:
            account = auth.authenticate(request, session, settings, response=response)
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
            return {"authenticated": False}
        customer = customer_for(session, account)
        return {
            "authenticated": True,
            "csrf": request.state.login.csrf,
            "email": account.email,
            "customer_id": customer.id if customer else None,
            "name": customer.name if customer else "",
        }

    @app.get("/api/portal/projects")
    def projects(request: Request, session: DB, offset: int = 0) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings)
        if offset < 0 or offset > 10000:
            raise HTTPException(422, "Invalid page")
        rows = session.execute(
            select(ConceptRequest, CustomerProject)
            .join(CustomerProject, CustomerProject.request_id == ConceptRequest.id)
            .join(Customer, Customer.id == CustomerProject.customer_id)
            .where(Customer.account_id == account.id)
            .order_by(ConceptRequest.created_at.desc(), ConceptRequest.id)
            .offset(offset)
            .limit(21)
        ).all()
        return {
            "projects": [project_view(session, item, link) for item, link in rows[:20]],
            "next_offset": offset + 20 if len(rows) > 20 else None,
        }

    @app.get("/api/portal/projects/{request_id}")
    def project(request_id: str, request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings)
        item, link = scoped_project(session, account, request_id)
        return project_view(session, item, link, detail=True)

    @app.post("/api/portal/projects", status_code=201)
    def create(body: ProjectInput, request: Request, session: DB) -> dict[str, Any]:
        from landwolf.lupuspec import store_request

        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"portal-projects:{account.id}", 8, 3600)
        if str(body.email).casefold() != account.email:
            raise HTTPException(422, "Use the signed-in email for this request")
        raw = RequestInput.model_validate(body.model_dump(exclude={"services"}))
        prior = session.scalar(
            select(ConceptRequest).where(ConceptRequest.submission_id == str(body.submission_id))
        )
        if prior:
            item, link = scoped_project(session, account, prior.id)
            view = project_view(session, item, link)
            if prior.content_hash != _content_hash(raw) or set(body.services) != {
                row["service"] for row in view["services"]
            }:
                raise HTTPException(409, "Submission reference already used")
            return view
        try:
            customer = customer_for(session, account, create=True)
            if customer is None:
                raise HTTPException(409, "Customer record unavailable")
            item = store_request(raw, session)
            link_project(
                session, item, customer, list(body.services), account.id, "authenticated_submission"
            )
            session.commit()
        except (IntegrityError, ValueError) as exc:
            session.rollback()
            raise HTTPException(409, "Request changed concurrently; retry") from exc
        return project_view(session, item, session.get_one(CustomerProject, item.id))

    @app.post("/api/portal/projects/{request_id}/messages", status_code=201)
    def message(
        request_id: str, body: MessageInput, request: Request, session: DB
    ) -> dict[str, str]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"portal-messages:{account.id}", 20, 3600)
        _, link = scoped_project(session, account, request_id)
        return save_message(session, account, link, body, "customer")

    @app.get("/api/admin/portal/catalog")
    def catalog(request: Request, session: DB) -> dict[str, Any]:
        admin.require_owner(request, session, settings, write=False)
        from landwolf.service_finance import STREAMS

        rows = session.execute(
            select(WorkItem, ConceptRequest)
            .join(ConceptRequest, ConceptRequest.id == WorkItem.request_id)
            .order_by(ConceptRequest.created_at.desc())
            .limit(501)
        ).all()
        if len(rows) > 500:
            raise HTTPException(
                503, "Work catalog limit reached; narrow the report before recording entries"
            )
        customers = session.execute(
            select(Customer, Account)
            .join(Account, Account.id == Customer.account_id)
            .order_by(Customer.created_at.desc())
            .limit(200)
        ).all()
        return {
            "work": [
                {
                    "id": row.id,
                    "request_id": row.request_id,
                    "customer_id": row.customer_id,
                    "service": row.service,
                    "title": item.title,
                }
                for row, item in rows
            ],
            "customers": [
                {"id": row.id, "name": row.name, "email": account.email}
                for row, account in customers
            ],
            "streams": [{"id": key, **value} for key, value in STREAMS.items()],
        }

    @app.get("/api/admin/portal/projects/{request_id}")
    def owner_project(request_id: str, request: Request, session: DB) -> dict[str, Any]:
        admin.require_owner(request, session, settings, write=False)
        item, link = (
            session.get(ConceptRequest, request_id),
            session.get(CustomerProject, request_id),
        )
        if item is None or link is None:
            raise HTTPException(404, "Project has no customer workspace")
        return {**project_view(session, item, link, detail=True), "customer_id": link.customer_id}

    @app.post("/api/admin/portal/projects/{request_id}/link")
    def owner_link(
        request_id: str, body: LinkInput, request: Request, session: DB
    ) -> dict[str, bool]:
        owner = admin.require_owner(request, session, settings, write=True)
        auth.limit(session, f"portal-link:{owner.id}", 20, 60)
        item, customer = (
            session.get(ConceptRequest, request_id),
            session.get(Customer, str(body.customer_id)),
        )
        if item is None or customer is None:
            raise HTTPException(404, "Project or customer not found")
        if session.get(CustomerProject, request_id):
            raise HTTPException(
                409, "Project already linked; customer ownership cannot be reassigned here"
            )
        try:
            link_project(
                session, item, customer, [item.capability], owner.id, "owner_verified_identity"
            )
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(409, "Project linked concurrently; refresh") from exc
        return {"ok": True}

    @app.post("/api/admin/portal/projects/{request_id}/messages", status_code=201)
    def publish(
        request_id: str, body: MessageInput, request: Request, session: DB
    ) -> dict[str, str]:
        owner = admin.require_owner(request, session, settings, write=True)
        auth.limit(session, f"portal-publish:{owner.id}", 30, 60)
        link = session.get(CustomerProject, request_id)
        if link is None:
            raise HTTPException(404, "Project has no customer workspace")
        return save_message(session, owner, link, body, "team")

    @app.patch("/api/admin/portal/work/{work_id}")
    def work_status(
        work_id: str, body: StatusInput, request: Request, session: DB
    ) -> dict[str, bool]:
        owner = admin.require_owner(request, session, settings, write=True)
        auth.limit(session, f"portal-work:{owner.id}", 30, 60)
        changed = session.scalar(
            update(WorkItem)
            .where(WorkItem.id == work_id, WorkItem.revision == body.revision)
            .values(status=body.status, revision=WorkItem.revision + 1)
            .returning(WorkItem.id)
        )
        if changed is None:
            session.rollback()
            raise HTTPException(409, "Work changed; refresh and retry")
        audit(session, owner.id, "work_status_" + body.status, work_id)
        session.commit()
        return {"ok": True}

    @app.post("/api/admin/portal/work/{work_id}/handoff")
    def handoff(work_id: str, request: Request, session: DB) -> dict[str, Any]:
        owner = admin.require_owner(request, session, settings, write=True)
        auth.limit(session, f"portal-handoff:{owner.id}", 10, 60)
        work = session.get(WorkItem, work_id)
        if work is None or work.service != "software" or work.status != "approved":
            raise HTTPException(409, "Only approved software work can be prepared for the factory")
        item = session.get_one(ConceptRequest, work.request_id)
        audit(session, owner.id, "factory_brief_prepared", work_id)
        session.commit()
        # A reviewable brief, never a command or an unauthenticated execution trigger.
        return {
            "work_item_id": work.id,
            "project_id": work.request_id,
            "title": item.title,
            "goal": item.text,
            "dispatch": "manual_owner_review",
            "factory_url": "https://l91.landwolf.ai/",
        }
