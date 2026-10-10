"""Registration capture, project isolation, private CRM, and migration contracts."""

import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from landwolf import crm_core
from landwolf.db import Account, initialize

PROFILE = {
    "full_name": "Fixture Investor",
    "company": "Fixture Company",
    "phone": "+1 555 010 1234",
    "job_title": "Principal",
    "industry": "real_estate",
    "contact_type": "investor",
    "primary_use": "investing",
    "use_details": "Synthetic research goals",
    "marketing_opt_in": False,
}
HEADERS = {"Origin": "http://testserver", "X-LandWolf-Client": "web"}


def signup(client, **profile):
    return client.post(
        "/api/auth/register",
        headers=HEADERS,
        json={
            "email": "new-profile@example.com",
            "password": "Test-only passphrase 847!",
            "profile": {**PROFILE, **profile},
        },
    )


def test_registration_is_atomic_and_private(client):
    response = signup(client)
    assert response.status_code == 201
    assert "profile" not in response.json()
    assert client.get("/api/admin/crm/contacts").status_code == 403
    with client.app.state.factory() as db:
        row = db.scalar(select(crm_core.Contact))
        assert row.full_name == PROFILE["full_name"] and row.email == "new-profile@example.com"
        assert row.company == PROFILE["company"] and not row.marketing_opt_in
        assert row.consent_version == crm_core.CONSENT_VERSION
        client.app.state.settings.owner_account_id = db.scalar(select(Account.id))
    contacts = client.get("/api/admin/crm/contacts").json()
    assert contacts["total"] == 1
    assert not {"password", "password_hash", "token_hash"} & contacts["contacts"][0].keys()
    assert signup(client).status_code == 400
    with client.app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(crm_core.Contact)) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"full_name": " "},
        {"primary_use": ""},
        {"primary_use": "bad"},
        {"phone": "not a phone"},
        {"phone": "1" * 16},
        {"company": "x" * 161},
        {"job_title": "bad\nvalue"},
        {"marketing_opt_in": "false"},
    ],
)
def test_invalid_profiles_do_not_create_accounts(client, change):
    response = signup(client, **change)
    assert response.status_code == 422
    with client.app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Account)) == 0
        assert db.scalar(select(func.count()).select_from(crm_core.Contact)) == 0


def test_profile_required_and_failed_capture_rolls_back(client, monkeypatch):
    assert (
        client.post(
            "/api/auth/register",
            headers=HEADERS,
            json={"email": "missing@example.com", "password": "Test-only passphrase 847!"},
        ).status_code
        == 422
    )

    def fail(*args, **kwargs):
        raise IntegrityError("synthetic", {}, Exception("synthetic"))

    monkeypatch.setattr("landwolf.auth.capture", fail)
    assert signup(client).status_code == 400
    with client.app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Account)) == 0


@pytest.mark.parametrize("route", ["contacts", "contacts.csv", "projects", "contacts/unknown"])
def test_anonymous_crm_denied(client, route):
    assert client.get("/api/admin/crm/" + route).status_code == 401


def test_owner_filters_edits_notes_export_and_csrf(client, owner_signed_in):
    assert signup(client, full_name="=FORMULA", marketing_opt_in=True).status_code == 201
    # New customer cannot promote themself or alter owner records.
    assert (
        client.post(
            "/api/admin/crm/projects", headers=owner_signed_in, json={"id": "bad", "name": "Bad"}
        ).status_code
        == 403
    )
    response = client.post(
        "/api/auth/login",
        headers=HEADERS,
        json={"email": "investor@example.com", "password": "Test-only passphrase 847!"},
    )
    headers = {**HEADERS, "X-CSRF-Token": response.json()["csrf"]}
    rows = client.get(
        "/api/admin/crm/contacts?q=FORMULA&industry=real_estate&primary_use=investing"
    ).json()
    assert rows["total"] == 1
    contact = rows["contacts"][0]
    url = "/api/admin/crm/contacts/" + contact["id"]
    body = {
        "revision": contact["revision"],
        "lifecycle": "qualified",
        "tags": ["Priority"],
        "follow_up_on": "2026-12-01",
    }
    assert client.patch(url, json=body).status_code == 403
    assert client.patch(url, headers=headers, json=body).status_code == 200
    assert client.patch(url, headers=headers, json=body).status_code == 409
    assert (
        client.post(
            url + "/notes",
            headers=headers,
            json={"text": "<script>not executable</script>\nFollow-up notes can use paragraphs."},
        ).status_code
        == 201
    )
    detail = client.get(url).json()
    assert any(a["kind"] == "note" and "\nFollow-up" in a["text"] for a in detail["activities"])
    exported = client.get("/api/admin/crm/contacts.csv?industry=real_estate")
    assert exported.status_code == 200 and exported.headers["cache-control"] == "no-store"
    data = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert len(data) == 1 and data[0]["full_name"] == "'=FORMULA"
    assert client.post(url + "/unsubscribe", headers=headers, json={}).status_code == 200
    assert not client.get(url).json()["contact"]["marketing_opt_in"]
    assert client.get("/api/admin/crm/contacts?q=%25").json()["total"] == 0
    assert client.get("/api/admin/crm/contacts?page=0").status_code == 422


def test_project_keys_are_write_only_scoped_rotatable_and_retry_safe(client, owner_signed_in):
    def project(project_id):
        result = client.post(
            "/api/admin/crm/projects",
            headers=owner_signed_in,
            json={"id": project_id, "name": "Fixture project"},
        )
        assert result.status_code == 201
        return result.json()["token"]

    key1, key2 = project("project-one"), project("project-two")
    assert key1 not in client.get("/api/admin/crm/projects").text
    with client.app.state.factory() as db:
        assert db.get(crm_core.Project, "project-one").token_hash != key1
    payload = {**PROFILE, "external_id": "external-1", "email": "external@example.com"}
    url = "/api/crm/v1/projects/project-one/registrations"
    with TestClient(client.app) as connector:
        h = {"Authorization": "Bearer " + key1}
        assert connector.get("/api/admin/crm/contacts", headers=h).status_code == 401
        assert (
            connector.post(
                url, headers={"Authorization": "Bearer " + key2}, json=payload
            ).status_code
            == 401
        )
        assert (
            connector.post(
                url, headers={**h, "Origin": "http://testserver"}, json=payload
            ).status_code
            == 403
        )
        first = connector.post(url, headers=h, json=payload)
        assert first.status_code == 200
        assert (
            connector.post(url, headers=h, json={**payload, "full_name": "Do not overwrite"}).json()
            == first.json()
        )
        assert (
            connector.post(url, headers=h, json={**payload, "external_id": "other-id"}).status_code
            == 409
        )
        assert (
            connector.post(
                url, headers=h, json={**payload, "email": "changed@example.com"}
            ).status_code
            == 409
        )
        assert (
            connector.post(
                "/api/crm/v1/projects/project-two/registrations",
                headers={"Authorization": "Bearer " + key2},
                json=payload,
            ).status_code
            == 200
        )
        assert client.get("/api/admin/crm/contacts?project_id=project-one").json()["total"] == 1
        rotated = client.post(
            "/api/admin/crm/projects/project-one/rotate-key", headers=owner_signed_in, json={}
        )
        assert rotated.status_code == 200
        assert connector.post(url, headers=h, json=payload).status_code == 401
        h = {"Authorization": "Bearer " + rotated.json()["token"]}
        assert connector.post(url, headers=h, json=payload).status_code == 200
        assert (
            client.request(
                "DELETE",
                "/api/admin/crm/projects/project-one/key",
                headers=owner_signed_in,
                json={},
            ).status_code
            == 200
        )
        assert connector.post(url, headers=h, json=payload).status_code == 401


def test_migration_backfills_known_facts_only_and_is_idempotent(client):
    with client.app.state.factory() as db, db.begin():
        db.add(
            Account(
                id="legacy-fixture",
                email="legacy@example.com",
                password_hash="synthetic",
                created_at=1,
            )
        )
    engine = client.app.state.factory.kw["bind"]
    initialize(engine)
    initialize(engine)
    with client.app.state.factory() as db:
        rows = list(db.scalars(select(crm_core.Contact)))
        assert len(rows) == 1
        row = rows[0]
        assert row.email == "legacy@example.com" and row.full_name == ""
        assert row.source == "existing_account" and row.consent_recorded_at is None
        assert not row.marketing_opt_in


def test_registration_accepts_multiline_goals(client):
    assert signup(client, use_details="First goal.\nSecond goal.").status_code == 201
    with client.app.state.factory() as db:
        assert db.scalar(select(crm_core.Contact)).use_details == "First goal.\nSecond goal."
