"""Private approval boundary and replay-safe remote delivery using real local SQL."""

import uuid

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import func, select
from test_customer_portal import join, project

from landwolf import factory_bridge as bridge
from landwolf.db import Account, SchemaVersion, initialize
from landwolf.portal_models import PortalAudit, WorkItem

BODY = {
    "revision": 2,
    "project_key": "new",
    "runtime": "python",
    "acceptance": "Return a helper",
    "confirmed": True,
}


@pytest.fixture
def approved(client, monkeypatch):
    headers = join(client)
    item, _ = project(client, headers)
    work = next(w for w in item["services"] if w["service"] == "software")
    with client.app.state.factory() as session:
        client.app.state.settings.owner_account_id = session.scalar(select(Account.id))
    path = "/api/admin/portal/work/" + work["id"]
    assert (
        client.patch(path, headers=headers, json={"revision": 1, "status": "approved"}).status_code
        == 200
    )
    client.app.state.settings.factory_token = SecretStr("test-only-factory-connection")
    jobs = {}
    calls = []

    def exchange(settings, method, route, payload=None):
        calls.append((method, route, payload))
        if route == "/portal/targets":
            return {
                "runners": [
                    {
                        "name": "Fixture",
                        "connected": True,
                        "ready": True,
                        "projects": [
                            {
                                "id": "new",
                                "name": "New project",
                                "runtimes": ["python"],
                                "checks": "syntax",
                            }
                        ],
                    }
                ]
            }
        key = route.split("/")[3]
        if method == "PUT":
            jobs.setdefault(key, {"id": key, "task_id": str(uuid.uuid4()), "state": "queued"})
        if key not in jobs:
            raise HTTPException(404, "not received")
        if route.endswith("/cancel"):
            jobs[key]["state"] = "cancelled"
        return jobs[key]

    monkeypatch.setattr(bridge, "exchange", exchange)
    return headers, path, jobs, calls, exchange


def test_approval_creates_one_durable_job_with_no_contact_or_financial_data(client, approved):
    headers, path, jobs, calls, _ = approved
    first = client.post(path + "/factory", headers=headers, json=BODY)
    assert first.status_code == 201, first.text
    again = client.post(path + "/factory", headers=headers, json=BODY)
    assert again.json() == first.json()
    assert len(jobs) == 1
    payload = next(c[2] for c in calls if c[0] == "PUT")
    assert set(payload) == {"title", "goal", "runtime", "project_key", "acceptance"}
    assert "email" not in str(payload) and "cost" not in str(payload)
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(bridge.FactoryDispatch)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(PortalAudit)
                .where(PortalAudit.action == "factory_run_approved")
            )
            == 1
        )
    assert (
        client.post(
            path + "/factory", headers=headers, json={**BODY, "acceptance": "Changed"}
        ).status_code
        == 409
    )
    assert len(jobs) == 1
    assert (
        client.post(path + "/factory/cancel", headers=headers, json={}).json()["dispatch"]["state"]
        == "cancelled"
    )
    assert client.get(path + "/factory").json()["dispatch"]["state"] == "cancelled"


def test_lost_acknowledgement_reuses_frozen_identity(client, approved, monkeypatch):
    headers, path, jobs, _, exchange = approved
    first = True

    def lost(settings, method, route, payload=None):
        nonlocal first
        result = exchange(settings, method, route, payload)
        if method == "PUT" and first:
            first = False
            raise HTTPException(503, "Acknowledgement lost")
        return result

    monkeypatch.setattr(bridge, "exchange", lost)
    assert client.post(path + "/factory", headers=headers, json=BODY).status_code == 503
    assert len(jobs) == 1
    seen = client.get(path + "/factory").json()["dispatch"]
    replay = client.post(path + "/factory", headers=headers, json=BODY).json()["dispatch"]
    assert seen == replay
    assert len(jobs) == 1


def test_offline_connection_retains_pending_request(client, approved, monkeypatch):
    headers, path, jobs, _, exchange = approved

    def offline(settings, method, route, payload=None):
        if route != "/portal/targets":
            raise HTTPException(503, "offline")
        return exchange(settings, method, route, payload)

    monkeypatch.setattr(bridge, "exchange", offline)
    assert client.post(path + "/factory", headers=headers, json=BODY).status_code == 503
    pending = client.get(path + "/factory").json()["dispatch"]
    assert pending["state"] == "pending"
    monkeypatch.setattr(bridge, "exchange", exchange)
    replay = client.post(path + "/factory", headers=headers, json=BODY).json()["dispatch"]
    assert replay["id"] == pending["id"] and len(jobs) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"confirmed": False},
        {"runtime": "bash"},
        {"project_key": "../../etc"},
        {"goal": "Injected"},
        {"acceptance": "x" * 4001},
    ],
)
def test_invalid_approvals_never_dispatch(client, approved, change):
    headers, path, jobs, _, _ = approved
    assert (
        client.post(path + "/factory", headers=headers, json={**BODY, **change}).status_code == 422
    )
    assert not jobs


def test_stale_unapproved_unavailable_target_and_missing_configuration(client, approved):
    headers, path, jobs, _, _ = approved
    assert (
        client.post(path + "/factory", headers=headers, json={**BODY, "revision": 1}).status_code
        == 409
    )
    assert (
        client.post(
            path + "/factory", headers=headers, json={**BODY, "project_key": "unknown"}
        ).status_code
        == 409
    )
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(bridge.FactoryDispatch)) == 0
    client.app.state.settings.factory_token = None
    assert client.post(path + "/factory", headers=headers, json=BODY).status_code == 503
    client.app.state.settings.factory_token = SecretStr("synthetic")
    assert (
        client.patch(path, headers=headers, json={"revision": 2, "status": "reviewing"}).status_code
        == 200
    )
    assert (
        client.post(path + "/factory", headers=headers, json={**BODY, "revision": 3}).status_code
        == 409
    )
    assert not jobs


def test_customer_and_csrf_cannot_dispatch_read_or_cancel(client, approved):
    headers, path, jobs, _, _ = approved
    assert (
        client.post(
            path + "/factory",
            headers={"Origin": "http://testserver", "X-LandWolf-Client": "web"},
            json=BODY,
        ).status_code
        == 403
    )
    other = join(client, "other-customer@example.com")
    assert client.post(path + "/factory", headers=other, json=BODY).status_code == 403
    assert client.get(path + "/factory").status_code == 403
    assert client.get("/api/admin/portal/factory/targets").status_code == 403
    assert client.post(path + "/factory/cancel", headers=other, json={}).status_code == 403
    assert not jobs


def test_v15_migration_preserves_accounts_work_and_dispatch(client, approved):
    headers, path, _, _, _ = approved
    first = client.post(path + "/factory", headers=headers, json=BODY).json()
    with client.app.state.factory() as session:
        account_count = session.scalar(select(func.count()).select_from(Account))
        work_count = session.scalar(select(func.count()).select_from(WorkItem))
        session.query(SchemaVersion).delete()
        session.add(SchemaVersion(version=15))
        session.commit()
        engine = session.get_bind()
    initialize(engine)
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(Account)) == account_count
        assert session.scalar(select(func.count()).select_from(WorkItem)) == work_count
        assert session.scalar(select(SchemaVersion.version)) == 17
    assert client.get(path + "/factory").json() == first


@pytest.mark.parametrize("status", [302, 401, 500])
def test_transport_never_follows_redirects_or_leaks_errors(client, monkeypatch, status):
    settings = client.app.state.settings
    settings.factory_token = SecretStr("synthetic-private-value")
    original = httpx.Client

    def transport(request):
        assert request.url.host == "l91-production-api.l91-lupu.workers.dev"
        assert "cookie" not in request.headers
        return httpx.Response(
            status,
            headers={"location": "https://untrusted.example"},
            text="private upstream detail",
        )

    def make_client(**kwargs):
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        return original(transport=httpx.MockTransport(transport), **kwargs)

    monkeypatch.setattr(bridge.httpx, "Client", make_client)
    with pytest.raises(HTTPException) as error:
        bridge.exchange(settings, "GET", "/portal/targets")
    assert error.value.status_code == 503
    assert "private" not in error.value.detail


def test_customer_progress_is_allowlisted_and_results_stay_private(client, approved):
    headers, path, jobs, _, _ = approved
    result = client.post(path + "/factory", headers=headers, json=BODY).json()["dispatch"]
    jobs[result["id"]].update(
        state="completed", result={"patch": "private code", "report": {"private": "local paths"}}
    )
    public_path = path.replace("/api/admin/portal/", "/api/portal/") + "/factory"
    assert client.get(public_path).json() == {"state": "awaiting_review"}
    join(client, "other-progress@example.com")
    assert client.get(public_path).status_code == 404
    client.cookies.clear()
    assert client.get(public_path).status_code == 401


@pytest.mark.parametrize(
    "status, expected", [("FAILED_OR_BLOCKED", "failed"), ("VERIFIED_SANDBOX", "completed")]
)
def test_finished_job_preserves_acceptance_outcome(client, approved, status, expected):
    headers, path, jobs, _, _ = approved
    dispatch = client.post(path + "/factory", headers=headers, json=BODY).json()["dispatch"]
    jobs[dispatch["id"]].update(
        state="completed", result={"patch": "private code", "report": {"status": status}}
    )
    result = client.get(path + "/factory").json()["dispatch"]
    assert result["state"] == expected
    assert result["result"]["report"]["status"] == status
    if expected == "failed":
        assert "CHECKS FAILED" in result["message"]
    public_path = path.replace("/api/admin/portal/", "/api/portal/") + "/factory"
    assert client.get(public_path).json() == {
        "state": "awaiting_review" if expected == "completed" else "failed"
    }


@pytest.mark.parametrize("status", ["delivered", "closed"])
def test_customer_delivery_supersedes_factory_review_without_losing_scope(client, approved, status):
    headers, path, jobs, calls, _ = approved
    dispatch = client.post(path + "/factory", headers=headers, json=BODY).json()["dispatch"]
    jobs[dispatch["id"]].update(
        state="completed",
        result={"patch": "private code", "report": {"status": "VERIFIED_SANDBOX"}},
    )
    assert (
        client.patch(path, headers=headers, json={"revision": 2, "status": status}).status_code
        == 200
    )
    public_path = path.replace("/api/admin/portal/", "/api/portal/") + "/factory"
    previous_calls = len(calls)
    assert client.get(public_path).json() == {"state": status}
    assert len(calls) == previous_calls
    join(client, "other-delivery@example.com")
    assert client.get(public_path).status_code == 404
    client.cookies.clear()
    assert client.get(public_path).status_code == 401
