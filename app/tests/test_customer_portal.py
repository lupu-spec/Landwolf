"""Two-customer isolation, public-to-private linkage and service cash invariants."""

import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from conftest import register as landwolf_register
from sqlalchemy import func, select
from test_lupuspec import request_body, submit

from landwolf.db import Account, initialize
from landwolf.finance_models import LupuSpecFinanceEntry
from landwolf.portal_models import (
    CashDimension,
    Customer,
    CustomerProject,
    ServiceAccount,
    WorkItem,
)

HEADERS = {"Origin": "http://testserver", "X-LandWolf-Client": "web"}
PASSWORD = "Synthetic customer passphrase 847!"


def join(client, email="portal-a@example.com"):
    response = client.post(
        "/api/portal/register",
        headers=HEADERS,
        json={"email": email, "password": PASSWORD, "full_name": "Synthetic Customer"},
    )
    assert response.status_code == 201, response.text
    return {**HEADERS, "X-CSRF-Token": response.json()["csrf"]}


def login(client, email):
    response = client.post(
        "/api/auth/login", headers=HEADERS, json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {**HEADERS, "X-CSRF-Token": response.json()["csrf"]}


def project(client, headers, **changes):
    body = request_body(
        email="portal-a@example.com", services=["software", "fabrication"], **changes
    )
    response = client.post("/api/portal/projects", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json(), body


def test_project_roundtrip_services_and_no_landwolf_enrollment(client):
    headers = join(client)
    created, body = project(client, headers)
    assert {w["service"] for w in created["services"]} == {"software", "fabrication"}
    assert client.get("/api/portal/projects").json()["projects"][0]["id"] == created["id"]
    retry = client.post("/api/portal/projects", headers=headers, json=body)
    assert retry.json() == created
    assert (
        client.post(
            "/api/portal/projects", headers=headers, json={**body, "services": ["software"]}
        ).status_code
        == 409
    )
    detail = client.get("/api/portal/projects/" + created["id"])
    assert detail.headers["cache-control"] == "no-store"
    assert detail.json()["text"] == body["text"]
    for private in ("contact_id", "email", "phone", "cost", "created_by", "csrf", "account_id"):
        assert private not in detail.json()
    from landwolf.crm_core import Contact

    with client.app.state.factory() as session:
        assert (
            session.scalar(
                select(func.count()).select_from(Contact).where(Contact.project_id == "landwolf")
            )
            == 0
        )
        assert session.scalar(select(func.count()).select_from(ServiceAccount)) == 2
        engine = session.bind
    initialize(engine)
    with client.app.state.factory() as session:
        assert (
            session.scalar(
                select(func.count()).select_from(Contact).where(Contact.project_id == "landwolf")
            )
            == 0
        )
        assert session.scalar(select(func.count()).select_from(CustomerProject)) == 1


def test_another_customer_cannot_read_write_link_or_dispatch(client):
    headers = join(client)
    first, _ = project(client, headers)
    other = join(client, "portal-b@example.com")
    route = "/api/portal/projects/" + first["id"]
    assert client.get("/api/portal/projects").json()["projects"] == []
    assert client.get(route).status_code == 404
    assert (
        client.post(
            route + "/messages",
            headers=other,
            json={"submission_id": str(uuid.uuid4()), "text": "Cross-customer attempt"},
        ).status_code
        == 404
    )
    assert client.get("/api/admin/portal/catalog").status_code == 403
    assert client.get("/api/admin/finance").status_code == 403
    assert client.get("/api/admin/crm/contacts").status_code == 403
    assert (
        client.post(
            "/api/admin/portal/work/" + first["services"][0]["id"] + "/handoff",
            headers=other,
            json={},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            "/api/admin/portal/work/" + first["services"][0]["id"],
            headers=other,
            json={"revision": 1, "status": "approved"},
        ).status_code
        == 403
    )
    client.cookies.clear()
    assert client.get(route).status_code == 401


def test_guest_email_match_or_submission_replay_never_claims_old_project(client):
    body = request_body(email="portal-a@example.com")
    guest = submit(client, body).json()["request_id"]
    headers = join(client)
    assert client.get("/api/portal/projects").json()["projects"] == []
    assert client.get("/api/portal/projects/" + guest).status_code == 404
    replay = client.post(
        "/api/portal/projects", headers=headers, json={**body, "services": ["software"]}
    )
    assert replay.status_code == 404
    own, _ = project(client, headers)
    assert own["id"] != guest
    assert len(client.get("/api/portal/projects").json()["projects"]) == 1


def test_existing_landwolf_account_is_reused_without_access_changes(client):
    headers = landwolf_register(client)
    response = client.post(
        "/api/portal/projects",
        headers=headers,
        json=request_body(email="investor@example.com", services=["software"]),
    )
    assert response.status_code == 201, response.text
    assert client.get("/api/portal/session").json()["authenticated"] is True
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(Account)) == 1
        assert session.scalar(select(func.count()).select_from(Customer)) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"customer_id": str(uuid.uuid4())},
        {"services": []},
        {"services": ["supply"]},
        {"services": ["software", "software"]},
        {"services": ["landwolf"]},
        {"email": "someone-else@example.com"},
        {"quantity": True},
    ],
)
def test_invalid_project_or_forged_customer_context_rejected(client, changes):
    headers = join(client)
    body = request_body(email="portal-a@example.com", services=["software"])
    response = client.post("/api/portal/projects", headers=headers, json={**body, **changes})
    assert response.status_code == 422, response.text
    assert client.get("/api/portal/projects").json()["projects"] == []


def test_origin_csrf_limits_and_revoked_session(client):
    headers = join(client)
    payload = request_body(email="portal-a@example.com", services=["software"])
    for bad in (
        {},
        {**headers, "Origin": "https://evil.example"},
        {**headers, "X-CSRF-Token": "wrong"},
    ):
        assert client.post("/api/portal/projects", headers=bad, json=payload).status_code == 403
    assert (
        client.post("/api/portal/projects", headers=headers, content=b"x" * 17000).status_code
        == 413
    )
    assert client.get("/api/portal/projects?offset=-1").status_code == 422
    assert client.get("/api/portal/projects?offset=10001").status_code == 422
    assert client.post("/api/auth/logout", headers=headers, json={}).status_code == 200
    assert client.get("/api/portal/projects").status_code == 401


def test_customer_messages_owner_publication_and_work_revision(client):
    headers = join(client)
    item, _ = project(client, headers)
    path = "/api/portal/projects/" + item["id"]
    msg = {
        "submission_id": str(uuid.uuid4()),
        "text": "Please use stainless steel. <script>not HTML</script>",
    }
    assert client.post(path + "/messages", headers=headers, json=msg).status_code == 201
    assert client.post(path + "/messages", headers=headers, json=msg).status_code == 201
    assert (
        client.post(
            path + "/messages", headers=headers, json={**msg, "text": "Changed"}
        ).status_code
        == 409
    )
    assert len(client.get(path).json()["messages"]) == 1
    with client.app.state.factory() as session:
        client.app.state.settings.owner_account_id = session.scalar(select(Account.id))
    owner_path = "/api/admin/portal/projects/" + item["id"]
    assert (
        client.post(
            owner_path + "/messages",
            headers=headers,
            json={"submission_id": str(uuid.uuid4()), "text": "Your materials are ready."},
        ).status_code
        == 201
    )
    assert client.get(path).json()["messages"][-1]["author"] in {"customer", "team"}
    work = next(w for w in item["services"] if w["service"] == "software")
    endpoint = "/api/admin/portal/work/" + work["id"]
    assert client.post(endpoint + "/handoff", headers=headers, json={}).status_code == 409
    assert (
        client.patch(
            endpoint, headers=headers, json={"revision": 1, "status": "approved"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            endpoint, headers=headers, json={"revision": 1, "status": "closed"}
        ).status_code
        == 409
    )
    brief = client.post(endpoint + "/handoff", headers=headers, json={}).json()
    assert brief["dispatch"] == "manual_owner_review"
    assert set(brief) == {"work_item_id", "project_id", "title", "goal", "dispatch", "factory_url"}
    assert client.get(path).json()["services"] != item["services"]


def test_only_explicit_owner_link_exposes_legacy_guest_request(client):
    guest = submit(client, request_body()).json()["request_id"]
    headers = join(client)
    customer = client.get("/api/portal/session").json()["customer_id"]
    path = "/api/admin/portal/projects/" + guest + "/link"
    body = {"customer_id": customer, "identity_confirmed": True}
    assert client.post(path, headers=headers, json=body).status_code == 403
    with client.app.state.factory() as session:
        client.app.state.settings.owner_account_id = session.scalar(select(Account.id))
    assert (
        client.post(path, headers=headers, json={**body, "identity_confirmed": False}).status_code
        == 422
    )
    assert client.post(path, headers=headers, json=body).status_code == 200
    assert client.post(path, headers=headers, json=body).status_code == 409
    assert client.get("/api/portal/projects/" + guest).status_code == 200


def test_classified_cash_customer_streams_and_reversals(client):
    headers = join(client)
    item, _ = project(client, headers)
    work = next(w for w in item["services"] if w["service"] == "software")
    with client.app.state.factory() as session:
        client.app.state.settings.owner_account_id = session.scalar(select(Account.id))
    endpoint = "/api/admin/finance/lupuspec/entries"
    body = {
        "date": datetime.now(UTC).date().isoformat(),
        "capability": "software",
        "kind": "receipt",
        "amount_cents": 12345,
        "stream": "software.build",
        "work_item_id": work["id"],
        "source_reference": "manual.receipt-001",
    }
    first = client.post(endpoint, headers=headers, json=body)
    assert first.status_code == 201, first.text
    assert client.post(endpoint, headers=headers, json=body).status_code == 409
    for changes in (
        {"stream": "fabrication.print"},
        {"work_item_id": item["services"][0]["id"]},
        {"work_item_id": None},
        {"amount_cents": -1},
    ):
        assert (
            client.post(
                endpoint,
                headers=headers,
                json={**body, "source_reference": "manual.invalid", **changes},
            ).status_code
            == 422
        )
    cost = {
        **body,
        "source_reference": "manual.cost-001",
        "kind": "expense",
        "amount_cents": 1000,
        "stream": "software.compute",
    }
    assert client.post(endpoint, headers=headers, json=cost).status_code == 201
    report = client.get("/api/admin/finance").json()["lupuspec"]
    assert report["totals"] == {"receipts_cents": 12345, "expenses_cents": 1000, "net_cents": 11345}
    assert sum(r["net_cents"] for r in report["breakdown"]["rows"]) == 11345
    assert {r["project_id"] for r in report["breakdown"]["rows"]} == {item["id"]}
    reversal = {
        **body,
        "amount_cents": -12345,
        "source_reference": "manual.reversal-001",
        "reversal_of": first.json()["id"],
    }
    assert (
        client.post(endpoint, headers=headers, json={**reversal, "amount_cents": -1}).status_code
        == 422
    )
    assert client.post(endpoint, headers=headers, json=reversal).status_code == 201
    assert (
        client.post(
            endpoint, headers=headers, json={**reversal, "source_reference": "manual.reversal-002"}
        ).status_code
        == 409
    )
    assert client.get("/api/admin/finance").json()["lupuspec"]["totals"]["receipts_cents"] == 0
    # Costs do not leak through the customer projection, including after classification.
    detail = client.get("/api/portal/projects/" + item["id"]).json()
    assert "stream" not in str(detail) and "amount_cents" not in str(detail)
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(LupuSpecFinanceEntry)) == 3
        assert session.scalar(select(func.count()).select_from(CashDimension)) == 3


def test_equal_amounts_on_distinct_work_and_unclassified_old_rows_remain_separate(client):
    headers = join(client)
    first, _ = project(client, headers)
    second, _ = project(client, headers)
    with client.app.state.factory() as session:
        client.app.state.settings.owner_account_id = session.scalar(select(Account.id))
    endpoint = "/api/admin/finance/lupuspec/entries"
    base = {
        "date": datetime.now(UTC).date().isoformat(),
        "capability": "software",
        "kind": "receipt",
        "amount_cents": 200,
        "stream": "software.build",
    }
    for index, item in enumerate([first, second]):
        w = next(w for w in item["services"] if w["service"] == "software")
        assert (
            client.post(
                endpoint,
                headers=headers,
                json={
                    **base,
                    "work_item_id": w["id"],
                    "source_reference": "manual.equal-" + str(index),
                },
            ).status_code
            == 201
        )
    legacy = {k: v for k, v in base.items() if k != "stream"}
    assert client.post(endpoint, headers=headers, json=legacy).status_code == 201
    report = client.get("/api/admin/finance").json()["lupuspec"]
    assert report["totals"]["receipts_cents"] == 600
    assert report["breakdown"]["unclassified_entries"] == 1
    assert len(report["breakdown"]["rows"]) == 3


@pytest.mark.parametrize("name", ["   ", "Synthetic\u0001Name", "Synthetic\nName"])
def test_invalid_customer_name_does_not_create_account(client, name):
    response = client.post(
        "/api/portal/register",
        headers={"Origin": "http://testserver", "X-LandWolf-Client": "web"},
        json={
            "email": "invalid-name@example.com",
            "password": "Synthetic customer passphrase 847!",
            "full_name": name,
        },
    )
    assert response.status_code == 422
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(Account)) == 0


def test_every_service_has_distinct_receipt_and_cost_codes():
    from landwolf.service_finance import STREAMS

    for service in ("studio", "software", "fabrication", "supply"):
        assert {row["kind"] for row in STREAMS.values() if row["service"] == service} == {
            "receipt",
            "expense",
        }
    assert STREAMS["supply.parts"]["kind"] == "receipt"
    assert STREAMS["supply.purchased_parts"]["kind"] == "expense"


def test_v14_cash_duplicate_key_stays_compatible(client, owner_signed_in):
    body = {
        "date": datetime.now(UTC).date().isoformat(),
        "capability": "software",
        "kind": "receipt",
        "amount_cents": 321,
        "reference": "LegacyReceipt",
    }
    endpoint = "/api/admin/finance/lupuspec/entries"
    created = client.post(endpoint, headers=owner_signed_in, json=body)
    assert created.status_code == 201
    legacy_key = hashlib.sha256(
        f"{body['date']}|software|receipt|321|LegacyReceipt".encode()
    ).hexdigest()
    with client.app.state.factory() as session:
        entry = session.get(LupuSpecFinanceEntry, created.json()["id"])
        assert entry.fingerprint == legacy_key
    assert client.post(endpoint, headers=owner_signed_in, json=body).status_code == 409
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(LupuSpecFinanceEntry)) == 1


def test_customer_creation_and_work_are_atomic_on_failure(client, monkeypatch):
    headers = join(client)

    def fail(*args, **kwargs):
        raise ValueError("Synthetic transaction failure")

    monkeypatch.setattr("landwolf.customer_portal.link_project", fail)
    body = request_body(email="portal-a@example.com", services=["software"])
    assert client.post("/api/portal/projects", headers=headers, json=body).status_code == 409
    from landwolf.lupuspec import ConceptRequest

    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(ConceptRequest)) == 0
    assert client.get("/api/portal/projects").json()["projects"] == []


def test_v14_migration_preserves_requests_finance_and_does_not_claim_them(client, owner_signed_in):
    from landwolf.db import SCHEMA_VERSION, SchemaVersion
    from landwolf.lupuspec import ConceptRequest
    from landwolf.portal_models import PortalAudit, ProjectMessage

    request_id = submit(client, request_body()).json()["request_id"]
    cash = client.post(
        "/api/admin/finance/lupuspec/entries",
        headers=owner_signed_in,
        json={
            "date": datetime.now(UTC).date().isoformat(),
            "capability": "software",
            "kind": "receipt",
            "amount_cents": 321,
            "reference": "LegacyReceipt",
        },
    )
    assert cash.status_code == 201
    with client.app.state.factory() as session:
        engine = session.bind
        session.query(SchemaVersion).update({"version": 14})
        session.commit()
    for model in (
        CashDimension,
        ProjectMessage,
        WorkItem,
        CustomerProject,
        ServiceAccount,
        PortalAudit,
        Customer,
    ):
        model.__table__.drop(engine)
    initialize(engine)
    initialize(engine)
    with client.app.state.factory() as session:
        assert session.scalar(select(SchemaVersion.version)) == SCHEMA_VERSION
        assert session.get(ConceptRequest, request_id).status == "received"
        assert session.get(LupuSpecFinanceEntry, cash.json()["id"]).amount_cents == 321
        assert session.scalar(select(func.count()).select_from(CustomerProject)) == 0
        assert session.scalar(select(func.count()).select_from(CashDimension)) == 0
