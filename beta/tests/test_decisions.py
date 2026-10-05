"""Behavioral contracts for costs, evidence, private persistence and Hunt research."""

import copy
from datetime import date, timedelta

import pytest
from conftest import register
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import delete, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from test_hunt import criteria, record

from landwolf.db import (
    Account,
    Base,
    Listing,
    ResearchCase,
    ResearchGoal,
    SchemaVersion,
    database,
    initialize,
)
from landwolf.decisions import CaseInput, Costs, Evidence, Goal, economics, evaluate


def body(**changes):
    value = CaseInput(
        goal=Goal(budget=130000),
        costs=Costs(known_costs=25000, unresolved_low=18000, unresolved_high=18000),
        pause_reason="budget",
    ).model_dump(mode="json")
    return {**value, **changes}


def make_hunt(client, headers, name="Research Hunt"):
    result = client.post("/api/hunts", json={"name": name, "criteria": criteria()}, headers=headers)
    assert result.status_code == 201, result.text
    return result.json()["id"]


def test_return_allowance_and_stress_are_explicit():
    item = record(asking_price=100000)
    costs = Costs(
        known_costs=25000,
        net_proceeds=160000,
        unresolved_low=18000,
        unresolved_high=18000,
        monthly_holding=500,
        delay_months=2,
        extra_cost=1000,
    )
    result = economics(costs, Goal(), item)
    assert result["allowance"] == 8333.33
    assert result["adverse_total"] == 145000
    assert result["adverse_return_pct"] == 10.34
    assert result["status"] == "exceeds_target"
    assert economics(costs, Goal(budget=120000), item)["allowance"] == -5000
    assert economics(Costs(), Goal(budget=120000), item)["allowance"] is None
    assert (
        economics(
            Costs(
                known_costs=0,
                purchase_basis="entered",
                purchase_price=0,
                unresolved_low=0,
                unresolved_high=0,
                net_proceeds=100,
            ),
            Goal(),
            item,
        )["adverse_return_pct"]
        is None
    )


@given(st.integers(0, 10000000), st.integers(0, 10000000), st.integers(0, 10000000))
def test_allowance_monotonic_and_exact(purchase, known, increase):
    item = record(asking_price=purchase)
    a = economics(Costs(known_costs=known), Goal(budget=90000000), item)
    b = economics(Costs(known_costs=known + increase), Goal(budget=90000000), item)
    assert b["allowance"] == a["allowance"] - increase
    assert a["known_total"] == purchase + known


@pytest.mark.parametrize(
    "invalid",
    [
        {"unresolved_low": 1},
        {"unresolved_low": 2, "unresolved_high": 1},
        {"known_costs": -1},
        {"known_costs": float("nan")},
        {"known_costs": float("inf")},
        {"delay_months": 2},
        {"purchase_basis": "entered"},
        {"purchase_price": 100},
        {"delay_months": 121},
        {"extra": 1},
    ],
)
def test_invalid_costs_rejected(invalid):
    with pytest.raises(ValueError):
        Costs(**invalid)


def test_evidence_and_requirements_do_not_infer_clearance():
    with pytest.raises(ValueError):
        Evidence(topic="access", status="confirmed")
    with pytest.raises(ValueError):
        Evidence(topic="use", checked_on=date.today() + timedelta(days=2))
    fact = {
        "topic": "use",
        "status": "confirmed",
        "note": "Fixture rule applies",
        "source_ref": "Fixture ordinance section 1",
        "checked_on": "2026-01-01",
        "scope": "general_rule",
    }
    with pytest.raises(ValueError):
        Evidence(**fact)
    accepted = Evidence(**fact, applicability_confirmed=True)
    with pytest.raises(ValueError):
        Evidence(**{**fact, "topic": "access"}, applicability_confirmed=True)
    goal = Goal(budget=200000)
    spec = CaseInput(
        goal=goal,
        costs=Costs(known_costs=0, unresolved_low=0, unresolved_high=0),
        evidence=[accepted],
    )
    result = evaluate(spec, goal, record(), available=True)
    assert result["questions"][0]["topic"] == "access"
    assert result["costs"]["status"] == "within_assumptions"
    assert len(result["blockers"]) == 2
    assert "not independently" in result["limitation"]
    assert len(evaluate(spec, goal, record(), available=False)["blockers"]) == 3


def test_preview_persistence_conflict_and_delete(client, signed_in, inventory):
    path = "/api/decision-cases/glo-99001"
    assert client.get(path).json()["revision"] == 0
    preview = client.post("/api/decision-preview/glo-99001", json=body(), headers=signed_in)
    assert preview.status_code == 200, preview.text
    assert client.get(path).json()["revision"] == 0
    saved = client.put(path, json=body(), headers=signed_in)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    assert client.get(path).json()["input"]["costs"]["known_costs"] == 25000
    assert client.put(path, json=body(), headers=signed_in).status_code == 409
    assert (
        client.put(path, json=body(revision=1), headers={"Origin": "http://testserver"}).status_code
        == 403
    )
    assert client.request("DELETE", path, json={}, headers=signed_in).json() == {"deleted": True}
    assert client.get(path).json()["revision"] == 0


def test_price_reconsideration_and_no_timestamp_noise(client, signed_in, inventory):
    path = "/api/decision-cases/glo-99001"
    assert client.put(path, json=body(), headers=signed_in).status_code == 200
    with client.app.state.factory() as session, session.begin():
        row = session.get(Listing, "glo-99001")
        row.payload = {**row.payload, "retrieved_at": "2026-10-01T00:00:00Z"}
    assert client.get(path).json()["history"] == []
    with client.app.state.factory() as session, session.begin():
        row = session.get(Listing, "glo-99001")
        row.payload = {**row.payload, "asking_price": 80000}
    value = client.get(path).json()
    assert value["decision"]["pause_condition_met"] is True
    assert value["history"][0]["kind"] == "reconsider"
    assert "Other requirements" in value["history"][0]["message"]
    assert client.get(path).json()["history"] == value["history"]
    with client.app.state.factory() as session, session.begin():
        session.execute(delete(Listing).where(Listing.id == "glo-99001"))
    missing = client.get(path).json()
    assert missing["available"] is False
    assert missing["decision"]["pause_condition_met"] is None
    assert missing["property"]["asking_price"] == 80000
    assert missing["history"][0]["kind"] == "review"
    retained = client.get("/api/properties/glo-99001")
    assert retained.status_code == 200 and retained.json()["active"] is False


def test_hunt_goal_comparison_shared_brief_and_cleanup(client, signed_in, inventory):
    hunt_id = make_hunt(client, signed_in)
    goal_path = f"/api/hunts/{hunt_id}/research-goal"
    value = {"goal": Goal(budget=300000, use_details="One cabin").model_dump()}
    assert client.put(goal_path, json=value, headers=signed_in).status_code == 200
    assert client.get(goal_path).json()["goal"]["budget"] == 300000
    assert client.put(goal_path, json=value, headers=signed_in).status_code == 409
    for listing_id in ["glo-99001", "glo-99002"]:
        value = body(hunt_id=hunt_id, authority="Fixture planning office", authority_confirmed=True)
        assert (
            client.put(
                f"/api/decision-cases/{listing_id}", json=value, headers=signed_in
            ).status_code
            == 200
        )
    view = client.get(f"/api/hunts/{hunt_id}/research").json()
    assert len(view["cases"]) == 2
    assert all(case["effective_goal"]["budget"] == 300000 for case in view["cases"])
    shared = [group for group in view["brief"] if len(group["properties"]) == 2]
    assert len(shared) == 1 and shared[0]["topic"] == "Permitted use"
    comparison = client.post(
        f"/api/hunts/{hunt_id}/research-compare",
        json={"listing_ids": ["glo-99001", "glo-99002"]},
        headers=signed_in,
    )
    assert comparison.status_code == 200
    assert comparison.json()["cost_difference"] == 100000
    assert comparison.json()["range_result"] == "A costs less across the entered ranges."
    assert comparison.json()["a"]["decision"]["blockers"]
    assert (
        client.post(
            f"/api/hunts/{hunt_id}/research-compare",
            json={"listing_ids": ["glo-99001", "glo-99001"]},
            headers=signed_in,
        ).status_code
        == 422
    )
    assert (
        client.request("DELETE", f"/api/hunts/{hunt_id}", json={}, headers=signed_in).status_code
        == 200
    )
    with client.app.state.factory() as session:
        assert session.scalars(select(ResearchCase)).all() == []
        assert session.scalars(select(ResearchGoal)).all() == []


def test_account_isolation_and_billing(client, signed_in, inventory):
    path = "/api/decision-cases/glo-99001"
    hunt_id = make_hunt(client, signed_in)
    assert (
        client.put(
            path, json=body(hunt_id=hunt_id, pause_note="Private fixture note"), headers=signed_in
        ).status_code
        == 200
    )
    second = register(client, "other-research@example.com")
    assert client.get(path).json()["revision"] == 0
    assert client.get(f"/api/hunts/{hunt_id}/research").status_code == 404
    assert client.put(path, json=body(hunt_id=hunt_id), headers=second).status_code == 404
    assert (
        client.post(
            f"/api/hunts/{hunt_id}/research-compare",
            json={"listing_ids": ["glo-99001", "glo-99002"]},
            headers=second,
        ).status_code
        == 404
    )
    assert client.get("/api/sources").status_code == 403
    client.app.state.settings.payments_enabled = True
    assert client.get(path).status_code == 402
    assert client.put(path, json=body(), headers=second).status_code == 402
    client.post("/api/auth/logout", json={}, headers=second)
    assert client.get(path).status_code == 401


def test_failed_write_rolls_back_without_claiming_success(
    client, signed_in, inventory, monkeypatch
):
    from landwolf import research_workspace

    original = research_workspace.case_payload

    def fail(*args, **kwargs):
        raise SQLAlchemyError("Synthetic database fault")

    monkeypatch.setattr(research_workspace, "case_payload", fail)
    assert (
        client.put("/api/decision-cases/glo-99001", json=body(), headers=signed_in).status_code
        == 503
    )
    monkeypatch.setattr(research_workspace, "case_payload", original)
    assert client.get("/api/decision-cases/glo-99001").json()["revision"] == 0


def test_evidence_scope_persists_without_neighbor_propagation(client, signed_in, inventory):
    value = body(
        evidence=[
            {
                "topic": "access",
                "status": "confirmed",
                "note": "Fixture deed",
                "source_ref": "Fixture book 1",
                "checked_on": "2026-01-01",
            }
        ]
    )
    result = client.put("/api/decision-cases/glo-99001", json=value, headers=signed_in)
    assert result.status_code == 200
    assert client.get("/api/decision-cases/glo-99002").json()["input"]["evidence"] == []
    invalid = copy.deepcopy(value)
    invalid["evidence"] *= 2
    assert (
        client.put("/api/decision-cases/glo-99002", json=invalid, headers=signed_in).status_code
        == 422
    )


def test_real_v8_migration_is_additive_and_idempotent(tmp_path):
    engine, factory = database(f"sqlite:///{tmp_path / 'schema8.db'}")
    Base.metadata.create_all(
        engine,
        tables=[
            t
            for t in Base.metadata.sorted_tables
            if t.name not in {"lw2_research_cases", "lw2_research_goals"}
        ],
    )
    with factory() as session, session.begin():
        session.add(SchemaVersion(version=8))
        session.add(Account(id="retained", email="schema@example.com", password_hash="fixture"))
    assert not inspect(engine).has_table("lw2_research_cases")
    initialize(engine)
    initialize(engine)
    with factory() as session:
        assert session.get(Account, "retained").password_hash == "fixture"
        assert session.scalars(select(SchemaVersion.version)).all() == [9]
    assert inspect(engine).has_table("lw2_research_cases")
    assert inspect(engine).has_table("lw2_research_goals")
    engine.dispose()


def test_bounded_records_and_history(client, signed_in, inventory):
    path = "/api/decision-cases/glo-99001"
    saved = client.put(path, json=body(), headers=signed_in).json()
    for revision in range(1, 24):
        saved = client.put(
            path, json=body(revision=revision, pause_note=f"Revision {revision}"), headers=signed_in
        ).json()
    assert saved["revision"] == 24 and len(saved["history"]) == 20
    with client.app.state.factory() as session, session.begin():
        account = session.scalar(select(Account.id))
        template = session.get(ResearchCase, (account, "glo-99001"))
        for index in range(49):
            session.add(
                ResearchCase(
                    account_id=account,
                    listing_id=f"bounded-{index}",
                    hunt_id=None,
                    payload=template.payload,
                    source_snapshot=template.source_snapshot,
                    revision=1,
                    fingerprint="",
                    evaluation={},
                    history=[],
                    updated_at=1,
                )
            )
    assert (
        client.put("/api/decision-cases/glo-99002", json=body(), headers=signed_in).status_code
        == 409
    )


def test_timeline_unknown_and_boundary():
    goal = Goal(max_months=12)
    spec = CaseInput(pause_reason="timeline")
    assert evaluate(spec, goal, record(), available=True)["pause_condition_met"] is None
    spec.costs = Costs(holding_months=10, delay_months=2, monthly_holding=500)
    assert evaluate(spec, goal, record(), available=True)["pause_condition_met"] is True
    spec.costs.delay_months = 3
    assert evaluate(spec, goal, record(), available=True)["pause_condition_met"] is False
