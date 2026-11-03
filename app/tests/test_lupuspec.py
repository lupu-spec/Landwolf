"""LupuSpec intake, CRM linkage, idempotency and owner-only workflow tests."""

import uuid

import pytest
from sqlalchemy import func, select

from landwolf.crm_core import Contact, Project
from landwolf.lupuspec import ConceptEvent, ConceptRequest


def request_body(**overrides):
    return {
        "submission_id": str(uuid.uuid4()),
        "capability": "software",
        "title": "Linux inventory management application",
        "text": "Build a private Linux inventory application with role-based access.",
        "quantity": 1,
        "full_name": "Synthetic Buyer",
        "email": "lupuspec-buyer@example.com",
        "contact_permission": True,
        **overrides,
    }


def submit(client, data, headers=None):
    return client.post(
        "/api/lupuspec/requests",
        json=data,
        headers=headers
        if headers is not None
        else {"Origin": "http://testserver", "Content-Type": "application/json"},
    )


def test_crm_project_seeded_without_mixing_landwolf_accounts(client):
    with client.app.state.factory() as session:
        assert session.get(Project, "lupuspec").name == "LupuSpec"
        assert session.get(Project, "landwolf").name == "LandWolf"


@pytest.mark.parametrize("capability", ["studio", "software", "fabrication", "supply"])
def test_public_intake_creates_a_crm_contact_and_request(client, capability):
    payload = request_body(capability=capability)
    response = submit(client, payload)
    assert response.status_code == 201, response.text
    with client.app.state.factory() as session:
        contact = session.scalar(select(Contact).where(Contact.project_id == "lupuspec"))
        assert contact.email == payload["email"]
        assert contact.primary_use == "lupuspec_" + capability
        assert contact.marketing_opt_in is False
        assert contact.consent_version is None
        row = session.get(ConceptRequest, response.json()["request_id"])
        assert row.contact_id == contact.id
        assert row.capability == capability
        assert row.status == "received"
        assert row.quantity == 1
        assert session.scalar(select(func.count()).select_from(ConceptRequest)) == 1


def test_idempotent_submission_and_customer_reuse(client):
    payload = request_body()
    first = submit(client, payload)
    second = submit(client, payload)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    changed = submit(client, {**payload, "title": "Changed title"})
    assert changed.status_code == 409
    third = submit(
        client,
        request_body(
            email=payload["email"],
            title="Second project",
            text="Please build a new macOS desktop application for my workshop.",
        ),
    )
    assert third.status_code == 201, third.text
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(ConceptRequest)) == 2
        assert (
            session.scalar(
                select(func.count()).select_from(Contact).where(Contact.project_id == "lupuspec")
            )
            == 1
        )


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"capability": "unknown"}, 422),
        ({"title": "X"}, 422),
        ({"text": "too short"}, 422),
        ({"quantity": 0}, 422),
        ({"quantity": 10001}, 422),
        ({"quantity": 1.5}, 422),
        ({"contact_permission": False}, 422),
        ({"reference_url": "http://example.com/file.step"}, 422),
        ({"reference_url": "https://user:password@example.com/a"}, 422),
        ({"reference_url": "https://example.com:8443/a"}, 422),
        ({"email": "not-an-email"}, 422),
        ({"phone": "123"}, 422),
    ],
)
def test_invalid_intake_rejected_without_customer_or_request(client, change, expected):
    response = submit(client, request_body(**change))
    assert response.status_code == expected, response.text
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(ConceptRequest)) == 0
        assert (
            session.scalar(
                select(func.count()).select_from(Contact).where(Contact.project_id == "lupuspec")
            )
            == 0
        )


def test_same_origin_required_without_landwolf_login(client):
    payload = request_body()
    assert submit(client, payload, headers={}).status_code == 403
    assert (
        submit(client, payload, headers={"Origin": "https://attacker.example"}).status_code == 403
    )
    assert (
        submit(
            client, payload, headers={"Origin": "http://testserver", "Content-Type": "text/plain"}
        ).status_code
        == 415
    )
    assert submit(client, payload).status_code == 201


def test_request_queue_owner_only(client, signed_in, owner_signed_in):
    assert client.get("/api/admin/lupuspec/requests").status_code == 200
    # Owner fixture promotes the one signed-in account; simulate a nonowner by dropping it.
    client.app.state.settings.owner_account_id = str(uuid.uuid4())
    assert client.get("/api/admin/lupuspec/requests").status_code == 403
    assert (
        client.patch(
            "/api/admin/lupuspec/requests/" + str(uuid.uuid4()),
            json={"status": "quoted", "revision": 1},
            headers=signed_in,
        ).status_code
        == 403
    )


def test_status_requires_owner_csrf_and_revision(client, owner_signed_in):
    request = submit(client, request_body())
    item_id = request.json()["request_id"]
    route = "/api/admin/lupuspec/requests/" + item_id
    assert client.patch(route, json={"status": "reviewing", "revision": 1}).status_code == 403
    first = client.patch(
        route, json={"status": "reviewing", "revision": 1}, headers=owner_signed_in
    )
    assert first.status_code == 200, first.text
    assert first.json()["revision"] == 2
    assert first.json()["status"] == "reviewing"
    conflict = client.patch(
        route, json={"status": "quoted", "revision": 1}, headers=owner_signed_in
    )
    assert conflict.status_code == 409
    unchanged = client.patch(
        route, json={"status": "reviewing", "revision": 2}, headers=owner_signed_in
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["revision"] == 2
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(ConceptEvent)) == 1
        assert session.get(ConceptRequest, item_id).status == "reviewing"


def test_owner_queue_links_to_same_crm_contact(client, owner_signed_in):
    submit(client, request_body())
    response = client.get("/api/admin/lupuspec/requests")
    assert response.status_code == 200
    requests = response.json()["requests"]
    assert len(requests) == 1
    assert requests[0]["email"] == "lupuspec-buyer@example.com"
    contact = client.get("/api/admin/crm/contacts/" + requests[0]["contact_id"])
    assert contact.status_code == 200, contact.text
    assert contact.json()["contact"]["project_id"] == "lupuspec"
    report = client.get("/api/admin/crm/projects")
    assert any(p["id"] == "lupuspec" for p in report.json()["projects"])


def test_portal_uses_separate_public_route_and_discloses_no_secrets(client):
    from pathlib import Path

    portal = Path(__file__).parents[1] / "web" / "lupuspec.html"
    markup = portal.read_text()
    for capability in ("studio", "software", "fabrication", "supply"):
        assert 'value="' + capability + '"' in markup
    assert "LupuSpec" in markup
    assert "L91 LLC" in markup
    assert "lupuspec.js" in markup
    assert "LupuSpec" not in client.get("/api/health").text
