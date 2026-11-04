"""Public inquiry to owner work: preserve identity, deny unverified ownership."""

import uuid

from sqlalchemy import func, select
from test_customer_portal import join
from test_lupuspec import request_body, submit

from landwolf.db import Account
from landwolf.lupuspec import ConceptRequest
from landwolf.portal_models import Customer, CustomerProject, WorkItem


def test_guest_prepare_is_idempotent_and_does_not_grant_email_access(client, owner_signed_in):
    body = request_body(capability="studio", email="guest@example.com")
    request_id = submit(client, body).json()["request_id"]
    path = "/api/admin/portal/projects/" + request_id
    payload = {"revision": 1, "service": "software", "confirmed": True}
    first = client.post(path + "/prepare", headers=owner_signed_in, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["services"][0]["service"] == "software"
    assert first.json()["services"][0]["status"] == "received"
    assert (
        client.post(path + "/prepare", headers=owner_signed_in, json=payload).json() == first.json()
    )
    with client.app.state.factory() as session:
        item = session.get(ConceptRequest, request_id)
        assert item.text == body["text"] and item.capability == "studio"
        assert session.scalar(select(func.count()).select_from(WorkItem)) == 1
        assert session.scalar(select(func.count()).select_from(CustomerProject)) == 1
        assert session.get(Customer, first.json()["customer_id"]).account_id is None
        assert session.scalar(select(func.count()).select_from(Account)) == 1
    assert client.get(path).json() == first.json()
    join(client, "guest@example.com")
    assert client.get("/api/portal/projects/" + request_id).status_code == 404
    assert client.get(path).status_code == 403
    assert client.post(path + "/prepare", headers=owner_signed_in, json=payload).status_code == 403


def test_guest_preparation_guards_and_add_service(client, owner_signed_in):
    request_id = submit(client, request_body()).json()["request_id"]
    path = "/api/admin/portal/projects/" + request_id + "/prepare"
    body = {"revision": 1, "service": "studio", "confirmed": True}
    assert client.post(path, json=body).status_code == 403
    for invalid in (
        {"service": "shell"},
        {"confirmed": False},
        {"revision": 0},
        {"revision": True},
        {"customer_id": str(uuid.uuid4())},
    ):
        assert (
            client.post(path, headers=owner_signed_in, json={**body, **invalid}).status_code == 422
        )
    assert (
        client.post(path, headers=owner_signed_in, json={**body, "revision": 2}).status_code == 409
    )
    first = client.post(path, headers=owner_signed_in, json=body).json()
    second = client.post(path, headers=owner_signed_in, json={**body, "service": "software"}).json()
    assert second["customer_id"] == first["customer_id"]
    assert {w["service"] for w in second["services"]} == {"studio", "software"}
    assert (
        client.post(
            path.replace(request_id, str(uuid.uuid4())), headers=owner_signed_in, json=body
        ).status_code
        == 404
    )


def test_v16_customer_migration_preserves_links(client):
    from test_customer_portal import project

    from landwolf.db import initialize

    headers = join(client)
    item, _ = project(client, headers)
    with client.app.state.factory() as session:
        engine = session.get_bind()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE old_customers (id VARCHAR(36) PRIMARY KEY, "
            "account_id VARCHAR(36) NOT NULL UNIQUE REFERENCES lw2_accounts(id), "
            "name VARCHAR(120) NOT NULL, created_at INTEGER NOT NULL)"
        )
        connection.exec_driver_sql("INSERT INTO old_customers SELECT * FROM lw2_customers")
        connection.exec_driver_sql("DROP TABLE lw2_customers")
        connection.exec_driver_sql("ALTER TABLE old_customers RENAME TO lw2_customers")
        connection.exec_driver_sql("UPDATE lw2_schema_version SET version=16")
    initialize(engine)
    initialize(engine)
    assert client.get("/api/portal/projects/" + item["id"]).status_code == 200
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_prepared_guest_can_be_explicitly_linked_without_moving_work(client, owner_signed_in):
    request_id = submit(client, request_body()).json()["request_id"]
    path = "/api/admin/portal/projects/" + request_id
    prepared = client.post(
        path + "/prepare",
        headers=owner_signed_in,
        json={"revision": 1, "service": "software", "confirmed": True},
    ).json()
    join(client, "verified-customer@example.com")
    customer_id = client.get("/api/portal/session").json()["customer_id"]
    assert client.get("/api/portal/projects/" + request_id).status_code == 404
    logged = client.post(
        "/api/auth/login",
        headers={"Origin": "http://testserver", "X-LandWolf-Client": "web"},
        json={"email": "investor@example.com", "password": "Test-only passphrase 847!"},
    )
    headers = {**owner_signed_in, "X-CSRF-Token": logged.json()["csrf"]}
    payload = {"customer_id": customer_id, "identity_confirmed": True}
    assert (
        client.post(
            path + "/link", headers=headers, json={**payload, "identity_confirmed": False}
        ).status_code
        == 422
    )
    assert client.post(path + "/link", headers=headers, json=payload).status_code == 200
    assert client.post(path + "/link", headers=headers, json=payload).status_code == 409
    from test_customer_portal import login

    login(client, "verified-customer@example.com")
    owned = client.get("/api/portal/projects/" + request_id).json()
    assert owned["services"] == prepared["services"]
    assert client.get("/api/portal/projects").json()["projects"][0]["id"] == request_id
    work_id = prepared["services"][0]["id"]
    assert client.get("/api/portal/work/" + work_id + "/factory").json() == {"state": "not_started"}
    join(client, "unrelated@example.com")
    assert client.get("/api/portal/work/" + work_id + "/factory").status_code == 404
