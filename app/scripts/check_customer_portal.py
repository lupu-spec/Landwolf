"""Exercise customer ownership and cash classification on the disposable CI database."""

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from landwolf.config import Settings
from landwolf.db import Account
from landwolf.portal_models import CashDimension, CustomerProject, WorkItem


def check(client: TestClient, settings: Settings, suffix: str) -> None:
    headers = {"Origin": "http://testserver", "X-LandWolf-Client": "web"}
    email = f"portal-pg-{suffix}@example.com"
    joined = client.post(
        "/api/portal/register",
        headers=headers,
        json={
            "email": email,
            "password": "Synthetic PostgreSQL passphrase 847!",
            "full_name": "PostgreSQL fixture",
        },
    )
    if joined.status_code != 201:
        raise RuntimeError("PostgreSQL portal registration failed")
    headers["X-CSRF-Token"] = joined.json()["csrf"]
    body = {
        "submission_id": str(uuid.uuid4()),
        "capability": "software",
        "services": ["software", "fabrication"],
        "title": "Synthetic PostgreSQL project",
        "text": "Create a Linux controller and printed enclosure for integration verification.",
        "full_name": "PostgreSQL fixture",
        "email": email,
        "contact_permission": True,
    }
    created = client.post("/api/portal/projects", headers=headers, json=body)
    if created.status_code != 201:
        raise RuntimeError("PostgreSQL customer/service/project transaction failed")
    project = created.json()
    if client.post("/api/portal/projects", headers=headers, json=body).json() != project:
        raise RuntimeError("PostgreSQL portal submission replay changed its identity")
    path = "/api/portal/projects/" + project["id"]
    message = {
        "submission_id": str(uuid.uuid4()),
        "text": "Synthetic customer update for restore verification.",
    }
    if client.post(path + "/messages", headers=headers, json=message).status_code != 201:
        raise RuntimeError("PostgreSQL customer message transaction failed")
    factory = client.app.state.factory
    original_owner = settings.owner_account_id
    try:
        with factory() as session:
            settings.owner_account_id = session.scalar(
                select(Account.id).where(Account.email == email)
            )
        work = next(row for row in project["services"] if row["service"] == "software")
        endpoint = "/api/admin/portal/work/" + work["id"]
        if (
            client.patch(
                endpoint, headers=headers, json={"revision": 1, "status": "approved"}
            ).status_code
            != 200
            or client.patch(
                endpoint, headers=headers, json={"revision": 1, "status": "closed"}
            ).status_code
            != 409
        ):
            raise RuntimeError("PostgreSQL work-item revision guard failed")
        entry = client.post(
            "/api/admin/finance/lupuspec/entries",
            headers=headers,
            json={
                "date": datetime.now(UTC).date().isoformat(),
                "capability": "software",
                "kind": "receipt",
                "amount_cents": 12345,
                "stream": "software.build",
                "work_item_id": work["id"],
                "source_reference": "pg-fixture-" + suffix,
            },
        )
        if entry.status_code != 201:
            raise RuntimeError("PostgreSQL dimensional cash transaction failed")
        with factory() as session:
            if (
                session.get(CustomerProject, project["id"]) is None
                or session.get(WorkItem, work["id"]).revision != 2
                or session.get(CashDimension, entry.json()["id"]).work_item_id != work["id"]
            ):
                raise RuntimeError("PostgreSQL customer dimensions did not persist")
        second = client.post(
            "/api/portal/register",
            headers={k: v for k, v in headers.items() if k != "X-CSRF-Token"},
            json={
                "email": f"portal-other-{suffix}@example.com",
                "password": "Synthetic other passphrase 847!",
                "full_name": "Other customer",
            },
        )
        if (
            second.status_code != 201
            or client.get(path).status_code != 404
            or client.get("/api/admin/finance").status_code != 403
        ):
            raise RuntimeError("PostgreSQL cross-customer boundary failed")
    finally:
        settings.owner_account_id = original_owner
    print(
        "Passed: PostgreSQL customer isolation, service work, revision guards and cash dimensions"
    )
