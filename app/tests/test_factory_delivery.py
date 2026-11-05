"""Release delivery preserves customer boundaries and checks downloaded bytes."""

import base64
import hashlib
import uuid

import pytest
from sqlalchemy import func, select
from test_customer_portal import join
from test_factory_bridge import BODY
from test_factory_bridge import approved as factory_approved

from landwolf import factory_bridge
from landwolf.factory_delivery import FactoryDelivery
from landwolf.portal_models import ProjectMessage, WorkItem


@pytest.fixture
def approved(client, monkeypatch):
    return factory_approved.__wrapped__(client, monkeypatch)


def delivered(client, approved):
    headers, path, jobs, calls, exchange = approved
    dispatch = client.post(path + "/factory", headers=headers, json=BODY).json()["dispatch"]
    source = b"PK-fixture-source"
    receipt = {
        "id": str(uuid.uuid4()),
        "version": "1.0.0",
        "state": "delivered",
        "target": "calculator-test",
        "production_url": "https://calculator-test.pages.dev",
        "has_source": True,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "artifact_sha256": "a" * 64,
        "report": {
            "schema": "l91.release-checks.v1",
            "passed": True,
            "operation": "publish",
            "artifact_sha256": "a" * 64,
        },
    }
    jobs[dispatch["id"]].update(state="completed", release=receipt)
    with client.app.state.factory() as session:
        item = session.get_one(WorkItem, path.split("/")[-1]).request_id
    return path, item, receipt, source, calls, exchange


def test_delivery_is_explicit_idempotent_and_customer_safe(client, approved):
    _, item, receipt, _, calls, _ = delivered(client, approved)
    receipt["state"] = "published"
    assert client.get("/api/portal/projects/" + item).json()["releases"] == []
    receipt["state"] = "delivered"
    first = client.get("/api/portal/projects/" + item).json()
    assert first["releases"][0]["checks"] == "PASSED"
    assert next(w for w in first["services"] if w["service"] == "software")["status"] == "delivered"
    assert first == client.get("/api/portal/projects/" + item).json()
    assert "report" not in str(first["releases"])
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(FactoryDelivery)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(ProjectMessage)
                .where(ProjectMessage.submission_id == receipt["id"])
            )
            == 1
        )
    join(client, "other-release@example.com")
    count = len(calls)
    assert client.get("/api/portal/projects/" + item).status_code == 404
    assert len(calls) == count


@pytest.mark.parametrize(
    "change",
    [
        {"production_url": "https://evil.example"},
        {"report": {"passed": False}},
        {"source_sha256": "bad"},
        {"has_source": False},
    ],
)
def test_bad_receipt_never_marks_delivered(client, approved, change):
    _, item, receipt, _, _, _ = delivered(client, approved)
    receipt.update(change)
    response = client.get("/api/portal/projects/" + item)
    assert response.status_code == 200
    assert not response.json()["releases"]
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(FactoryDelivery)) == 0


def test_download_checks_ownership_and_package_hash(client, approved, monkeypatch):
    _, item, _, source, calls, exchange = delivered(client, approved)

    def fetch(settings, method, route, payload=None):
        if route.endswith("/source"):
            calls.append((method, route, payload))
            return {"base64": base64.b64encode(source).decode()}
        return exchange(settings, method, route, payload)

    monkeypatch.setattr(factory_bridge, "exchange", fetch)
    release = client.get("/api/portal/projects/" + item).json()["releases"][0]
    response = client.get(release["source_url"])
    assert response.status_code == 200 and response.content == source
    assert "no-store" in response.headers["cache-control"]
    source = b"PK-tampered"
    assert client.get(release["source_url"]).status_code == 502
    join(client, "other-download@example.com")
    count = len(calls)
    assert client.get(release["source_url"]).status_code == 404
    assert len(calls) == count
    assert (
        client.get(release["source_url"].replace("/api/portal/", "/api/admin/portal/")).status_code
        == 403
    )
    client.cookies.clear()
    assert client.get(release["source_url"]).status_code == 401


def test_other_service_not_delivered_by_software_release(client, approved):
    _, item, _, _, _, _ = delivered(client, approved)
    data = client.get("/api/portal/projects/" + item).json()
    assert data["status"] != "delivered"
    assert {row["service"]: row["status"] for row in data["services"]} == {
        "software": "delivered",
        "fabrication": "received",
    }


def test_rollback_withdraws_release_download(client, approved):
    _, item, receipt, _, _, _ = delivered(client, approved)
    release = client.get("/api/portal/projects/" + item).json()["releases"][0]
    receipt["state"] = "rolled_back"
    assert client.get("/api/portal/projects/" + item).json()["releases"] == []
    assert client.get(release["source_url"]).status_code == 404


def history_remote(approved, receipts):
    jobs = approved[2]
    remote = next(iter(jobs.values()))
    remote["releases"] = receipts
    remote["release"] = {"id": str(uuid.uuid4()), "state": "queued"}
    return remote


def test_newer_queued_attempt_does_not_hide_delivered_history(client, approved):
    _, item, receipt, _, _, _ = delivered(client, approved)
    second = {**receipt, "id": str(uuid.uuid4()), "version": "1.0.1"}
    history_remote(approved, [receipt, second])
    first = client.get("/api/portal/projects/" + item).json()
    assert {r["version"] for r in first["releases"]} == {"1.0.0", "1.0.1"}
    assert next(w for w in first["services"] if w["service"] == "software")["status"] == "delivered"
    assert first == client.get("/api/portal/projects/" + item).json()
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(FactoryDelivery)) == 2
        assert session.scalar(select(func.count()).select_from(ProjectMessage)) == 2


def test_rollback_is_not_hidden_by_new_attempt_or_later_delivery(client, approved):
    _, item, receipt, _, _, _ = delivered(client, approved)
    old = client.get("/api/portal/projects/" + item).json()["releases"][0]
    receipt["state"] = "rolled_back"
    remote = history_remote(approved, [receipt])
    data = client.get("/api/portal/projects/" + item).json()
    assert not data["releases"]
    assert (
        next(w for w in data["services"] if w["service"] == "software")["status"] == "in_progress"
    )
    assert client.get(old["source_url"]).status_code == 404
    second = {**receipt, "id": str(uuid.uuid4()), "state": "delivered", "version": "1.0.1"}
    remote["releases"].append(second)
    data = client.get("/api/portal/projects/" + item).json()
    assert [r["version"] for r in data["releases"]] == ["1.0.1"]
    assert next(w for w in data["services"] if w["service"] == "software")["status"] == "delivered"
    assert data == client.get("/api/portal/projects/" + item).json()


def test_rollback_and_later_delivery_sync_together(client, approved):
    _, item, receipt, _, _, _ = delivered(client, approved)
    client.get("/api/portal/projects/" + item)
    receipt["state"] = "rolled_back"
    second = {**receipt, "id": str(uuid.uuid4()), "state": "delivered", "version": "1.0.1"}
    history_remote(approved, [receipt, second])
    data = client.get("/api/portal/projects/" + item).json()
    assert [r["version"] for r in data["releases"]] == ["1.0.1"]
    assert next(w for w in data["services"] if w["service"] == "software")["status"] == "delivered"


@pytest.mark.parametrize("invalid", ["duplicate", "oversized", "bad_receipt"])
def test_invalid_history_does_not_partially_materialize_delivery(client, approved, invalid):
    _, item, receipt, _, _, _ = delivered(client, approved)
    history = [receipt]
    if invalid == "duplicate":
        history.append(receipt)
    elif invalid == "oversized":
        history *= 31
    else:
        history.append({**receipt, "id": str(uuid.uuid4()), "source_sha256": "invalid"})
    history_remote(approved, history)
    assert not client.get("/api/portal/projects/" + item).json()["releases"]
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(FactoryDelivery)) == 0
