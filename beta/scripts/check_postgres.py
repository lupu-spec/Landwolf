"""Check search and permanent Saved removal against disposable PostgreSQL."""

import os
import secrets
import sys
import time
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from sqlalchemy import delete, inspect, select

from landwolf import auth, feedback
from landwolf.config import Settings
from landwolf.db import (
    SCHEMA_VERSION,
    Account,
    AccountAction,
    Hunt,
    Listing,
    LoginSession,
    SchemaVersion,
    SourceRun,
    database,
    initialize,
)
from landwolf.main import create_app
from landwolf.schemas import PropertyRecord
from landwolf.trust import publish_snapshot


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def check_research(client: TestClient, headers: dict[str, str], hunt_id: str, suffix: str) -> None:
    """Exercise actual PostgreSQL JSON persistence, CAS updates and Hunt ownership."""
    goal = {"goal": {"budget": 200}}
    path = f"/api/hunts/{hunt_id}/research-goal"
    require(client.put(path, headers=headers, json=goal).status_code == 200, "Research goal failed")
    require(client.put(path, headers=headers, json=goal).status_code == 409, "Goal CAS failed")
    data = {
        "hunt_id": hunt_id,
        "costs": {"known_costs": 25, "unresolved_low": 200, "unresolved_high": 200},
        "pause_reason": "budget",
    }
    path = f"/api/decision-cases/pg-{suffix}-known"
    first = client.put(path, headers=headers, json=data)
    require(first.status_code == 200, "PostgreSQL research save failed")
    require(client.get(path).json()["revision"] == 1, "Research did not persist")
    require(client.put(path, headers=headers, json=data).status_code == 409, "Research CAS failed")
    data["revision"] = 1
    data["costs"] = {"known_costs": 25, "unresolved_low": 50, "unresolved_high": 50}
    second = client.put(path, headers=headers, json=data)
    require(second.status_code == 200, "Research update failed")
    require(second.json()["history"][0]["kind"] == "reconsider", "Research reconsideration failed")
    require(
        client.get(path).json()["history"] == second.json()["history"], "Research notices repeat"
    )
    data["revision"] = 0
    require(
        client.put(f"/api/decision-cases/pg-{suffix}-other", headers=headers, json=data).status_code
        == 200,
        "Second comparison case failed",
    )
    compared = client.post(
        f"/api/hunts/{hunt_id}/research-compare",
        headers=headers,
        json={"listing_ids": [f"pg-{suffix}-known", f"pg-{suffix}-other"]},
    )
    require(
        compared.status_code == 200 and compared.json()["cost_difference"] == 100,
        "PostgreSQL research comparison failed",
    )
    require(
        len(client.get(f"/api/hunts/{hunt_id}/research").json()["cases"]) == 2,
        "Hunt research membership failed",
    )


def main() -> None:
    url = os.environ.get("LANDWOLF_TEST_POSTGRES_URL", "")
    if not url or not urlsplit(url).path.endswith("/landwolf_ci"):
        raise SystemExit("A disposable landwolf_ci PostgreSQL database is required")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from migration_fixture import legacy_fixture

    settings = Settings(
        environment="test", database_url=url, public_origin="http://testserver", auto_sync=False
    )
    suffix = uuid.uuid4().hex[:12]
    engine, factory = database(url)
    if not inspect(engine).has_table(SchemaVersion.__tablename__):
        legacy_fixture(engine, 2)
    initialize(engine)
    initialize(engine)
    with factory() as session:
        require(
            session.scalars(select(SchemaVersion.version)).all() == [SCHEMA_VERSION],
            "Migration version failed",
        )
        require(not inspect(engine).has_table("lw2_saved_records"), "Saved records table retained")
        require(not inspect(engine).has_table("lw2_saved_properties"), "Bookmark table retained")
        require(
            session.get(Account, "migration-fixture").password_hash == "synthetic-hash",
            "Existing account changed",
        )
        require(
            session.get(LoginSession, "synthetic-session").csrf == "synthetic-csrf",
            "Existing session changed",
        )
        require(
            session.get(Listing, "migration-fixture").active is False, "Existing listing changed"
        )
    engine.dispose()
    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.factory() as session, session.begin():
            for label, state, price, acres, deadline in [
                ("known", "AK", 100, 2, None),
                ("unknown", "AK", None, None, None),
                ("expired", "AK", 50, 2, "2000-01-01"),
                ("other", "HI", 200, 3, None),
            ]:
                item = PropertyRecord(
                    id=f"pg-{suffix}-{label}",
                    tract=suffix,
                    title="Synthetic CI listing",
                    state=state,
                    source="us_treasury",
                    source_url="https://www.treasury.gov/auctions/treasury/rp/realprop.shtml",
                    category="public_auction",
                    asking_price=price,
                    acres=acres,
                    latitude=20.0 if label == "other" else None,
                    longitude=-155.0 if label == "other" else None,
                    bidding_deadline=deadline,
                    retrieved_at="2099-01-01T00:00:00Z",
                )
                session.add(
                    Listing(
                        id=item.id,
                        source=item.source,
                        active=True,
                        payload=item.model_dump(mode="json"),
                    )
                )
        headers = {"Origin": "http://testserver", "X-LandWolf-Client": "web"}
        credentials = {"email": f"postgres-{suffix}@example.com", "password": uuid.uuid4().hex}
        require(
            client.post("/api/search", json={}).status_code == 401,
            "Search must require authentication",
        )
        response = client.post(
            "/api/auth/register",
            json={
                "profile": {"full_name": "Fixture User", "primary_use": "research"},
                **(credentials),
            },
            headers=headers,
        )
        require(response.status_code == 201, "PostgreSQL registration failed")
        headers["X-CSRF-Token"] = response.json()["csrf"]
        own_profile = client.get("/api/account/profile").json()["profile"]
        self_edit = {key: value for key, value in own_profile.items() if key != "email"}
        self_edit["company"] = "PostgreSQL profile fixture"
        require(
            client.patch("/api/account/profile", json=self_edit, headers=headers).status_code
            == 200,
            "PostgreSQL self-profile write failed",
        )
        require(
            client.patch("/api/account/profile", json=self_edit, headers=headers).status_code
            == 409,
            "PostgreSQL stale self-profile write accepted",
        )
        require(
            client.get("/api/account/profile").json()["profile"]["company"] == self_edit["company"],
            "PostgreSQL self-profile did not persist",
        )
        require(
            client.delete("/api/account/profile", headers=headers).status_code == 405,
            "Unexpected profile deletion route",
        )
        with app.state.factory() as session, session.begin():
            account = session.scalar(select(Account).where(Account.email == credentials["email"]))
            login = session.scalar(
                select(LoginSession).where(LoginSession.account_id == account.id)
            )
            login.last_seen = int(time.time()) - 180 * 86400
            login.expires_at = int(time.time()) + 60
        renewed = client.get("/api/session")
        require(renewed.json()["authenticated"], "Persistent PostgreSQL session did not renew")
        require("Max-Age=31536000" in renewed.headers["set-cookie"], "Cookie lifetime not renewed")
        with app.state.factory() as session:
            login = session.scalar(
                select(LoginSession).where(LoginSession.account_id == account.id)
            )
            require(login.expires_at > int(time.time()) + 364 * 86400, "Session expiry not renewed")

        def search(**query: object) -> dict:
            response = client.post(
                "/api/search", json={"location": suffix, **query}, headers=headers
            )
            require(response.status_code == 200, "PostgreSQL search failed")
            return response.json()

        require(search()["total"] == 3, "Expired bidding deadline must be excluded")
        require(search(state="AK")["total"] == 2, "State JSON filtering failed")
        require(search(state="HI")["total"] == 1, "Hawaii filtering failed")
        require(search(max_price=150)["total"] == 1, "Unknown price must not behave as zero")
        require(search(min_acres=1)["total"] == 2, "Unknown acreage filter failed")
        require(
            search(sort="price_desc")["results"][-1]["asking_price"] is None, "NULLS LAST failed"
        )
        require(search(page_size=1, page=2)["results"][0]["state"] == "HI", "Pagination failed")
        map_page = search(page_size=1)
        require(map_page["results"][0]["latitude"] is None, "Map fixture must start unlocated")
        require(map_page["map_total"] == 1, "Map count must exclude null coordinates")
        require(
            map_page["map_results"][0]["id"] == f"pg-{suffix}-other",
            "Map omitted a location beyond the list page",
        )
        require(
            map_page["map_results"] == search(page=2, page_size=1)["map_results"],
            "Map changed with list pagination",
        )
        require(search(state="AK")["map_results"] == [], "Map ignored search filters")
        for method, path in [
            ("GET", "/api/saved"),
            ("POST", "/api/saved"),
            ("GET", "/api/saved/old"),
            ("PUT", "/api/saved/old"),
            ("PATCH", "/api/saved/old"),
            ("DELETE", "/api/saved/old"),
        ]:
            require(
                client.request(method, path, json={}, headers=headers).status_code == 404,
                "Retired Saved route still exists",
            )
        require(
            client.post("/api/search", json={"saved_only": True}, headers=headers).status_code
            == 422,
            "Retired search filter still accepted",
        )
        require("saved" not in search()["results"][0], "Saved state still exposed")
        require(client.get("/api/sources").status_code == 403, "Coverage leaked to customer")
        require(search()["sources"] == [], "Source diagnostics leaked through search")
        with app.state.factory() as session:
            settings.owner_account_id = session.scalar(
                select(Account.id).where(Account.email == credentials["email"])
            )
        require(
            len(client.get("/api/sources").json()["states"]) == 50, "Coverage aggregation failed"
        )
        settings.owner_account_id = None
        # A failed matching transaction must not roll back the account's saved preferences.
        broken_id = f"hunt-invalid-{suffix}"
        with app.state.factory() as session, session.begin():
            session.add(
                Listing(id=broken_id, source="us_treasury", active=True, payload={"id": broken_id})
            )
        saved = client.post(
            "/api/hunts",
            headers=headers,
            json={
                "name": "PostgreSQL save durability",
                "criteria": {
                    "mode": "fixed",
                    "states": [],
                    "min_acres": 5,
                    "max_acres": 50,
                },
            },
        )
        require(saved.status_code == 201, "Matching failure discarded the Hunt")
        require(saved.json()["matching_status"] == "unavailable", "Match failure was hidden")
        hunt_id = saved.json()["id"]
        with app.state.factory() as session:
            require(session.get(Hunt, hunt_id) is not None, "Hunt was not committed to PostgreSQL")
        require(
            any(row["id"] == hunt_id for row in client.get("/api/hunts").json()["hunts"]),
            "Saved Hunt cannot be read back",
        )
        with app.state.factory() as session, session.begin():
            session.execute(delete(Listing).where(Listing.id == broken_id))
        require(
            client.get(f"/api/hunts/{hunt_id}/matches").status_code == 200,
            "Matching cannot retry after source repair",
        )
        check_research(client, headers, hunt_id, suffix)
        require(
            client.request("DELETE", f"/api/hunts/{hunt_id}", headers=headers, json={}).status_code
            == 200,
            "Disposable Hunt cleanup failed",
        )
        # Exercise the PostgreSQL identity/event upsert and snapshot quarantine.
        with app.state.factory() as session, session.begin():
            records = [
                PropertyRecord(
                    id=f"trust-pg-{suffix}-{n}",
                    tract=f"{suffix}-{n}",
                    title="Synthetic trust record",
                    state="MN",
                    county="Fixture",
                    parcel_number=f"CI-{n}",
                    source="mn_dot",
                    source_url="https://www.dot.state.mn.us/row/propsales.html",
                    retrieved_at="2099-01-01T00:00:00Z",
                )
                for n in range(3)
            ]
            require(publish_snapshot(session, "mn_dot", records), "Trust snapshot failed")
            require(not publish_snapshot(session, "mn_dot", []), "Missing-feed quarantine failed")
        with app.state.factory() as session:
            latest = session.scalar(select(SourceRun).order_by(SourceRun.id.desc()))
            require(latest.status == "review_required", "Run ordering failed")
        detail = client.get(f"/api/properties/{records[0].id}").json()
        require(
            detail["trust"]["identity"]["status"] == "publisher_parcel_id", "Parcel evidence failed"
        )
        # Exercise atomic DELETE RETURNING, one-use tokens and session revocation.
        token = secrets.token_urlsafe(32)
        with app.state.factory() as session, session.begin():
            account = session.scalar(select(Account).where(Account.email == credentials["email"]))
            session.add(
                AccountAction(
                    token_hash=auth.digest(token),
                    account_id=account.id,
                    purpose="reset",
                    expires_at=int(time.time()) + 300,
                )
            )
        body = {"token": token, "password": "Synthetic replacement passphrase 472!"}
        require(
            client.post("/api/auth/reset-password", json=body, headers=headers).status_code == 200,
            "PostgreSQL recovery failed",
        )
        require(client.get("/api/sources").status_code == 401, "Reset did not revoke session")
        require(
            client.post("/api/auth/reset-password", json=body, headers=headers).status_code == 400,
            "Recovery token was reusable",
        )
        credentials["password"] = body["password"]
        response = client.post("/api/auth/login", json=credentials, headers=headers)
        require(response.status_code == 200, "New password failed")
        headers["X-CSRF-Token"] = response.json()["csrf"]
        require(
            client.post("/api/auth/logout", json={}, headers=headers).status_code == 200,
            "Logout failed",
        )
        require(
            client.get("/api/sources").status_code == 401, "Source endpoint leaked after logout"
        )
        # Keep populated cohort tables for the following exact-content restore rehearsal.
        owner_credentials = {
            "email": f"feedback-owner-{suffix}@example.com",
            "password": secrets.token_urlsafe(32),
        }
        owner_login = client.post(
            "/api/auth/register",
            json={
                "profile": {"full_name": "Fixture User", "primary_use": "research"},
                **(owner_credentials),
            },
            headers=headers,
        )
        require(owner_login.status_code == 201, "Feedback test owner registration failed")
        owner_headers = {**headers, "X-CSRF-Token": owner_login.json()["csrf"]}
        with app.state.factory() as session:
            owner = session.scalar(
                select(Account).where(Account.email == owner_credentials["email"])
            )
            participant = session.scalar(
                select(Account).where(Account.email == credentials["email"])
            )
            settings.owner_account_id = owner.id
            participant_id = participant.id
        crm_rows = client.get("/api/admin/crm/contacts?q=" + credentials["email"])
        require(crm_rows.status_code == 200, "PostgreSQL owner CRM failed")
        require(crm_rows.json()["total"] == 1, "PostgreSQL registration CRM capture failed")
        crm_contact = crm_rows.json()["contacts"][0]
        require(crm_contact["full_name"] == "Fixture User", "CRM profile not retained")
        edited = client.patch(
            "/api/admin/crm/contacts/" + crm_contact["id"],
            headers=owner_headers,
            json={
                "revision": crm_contact["revision"],
                "lifecycle": "qualified",
                "tags": ["Postgres fixture"],
                "follow_up_on": "2026-12-01",
            },
        )
        require(edited.status_code == 200, "PostgreSQL CRM edit failed")
        require(
            client.get("/api/admin/crm/contacts.csv").status_code == 200, "PostgreSQL CSV failed"
        )
        manual = client.post(
            "/api/admin/crm/contacts",
            headers=owner_headers,
            json={
                "email": f"crm-admin-{suffix}@example.com",
                "full_name": "Postgres Admin Fixture",
                "primary_use": "exploring",
            },
        )
        require(manual.status_code == 201, "PostgreSQL manual contact creation failed")
        manual_row = manual.json()
        manual_url = "/api/admin/crm/contacts/" + manual_row["id"]
        reservation_body = {
            "revision": manual_row["revision"],
            "action": "trial",
            "days": 14,
            "reason": "Synthetic PostgreSQL trial",
        }
        reserved = client.post(manual_url + "/access", headers=owner_headers, json=reservation_body)
        require(
            reserved.status_code == 200 and reserved.json()["state"] == "reserved",
            "PostgreSQL trial reservation failed",
        )
        require(
            client.post(
                manual_url + "/access", headers=owner_headers, json=reservation_body
            ).status_code
            == 409,
            "PostgreSQL stale administration update accepted",
        )
        current_manual = client.get(manual_url).json()["contact"]
        require(
            client.post(
                manual_url + "/access",
                headers=owner_headers,
                json={
                    "revision": current_manual["revision"],
                    "action": "revoke",
                    "reason": "Synthetic PostgreSQL revocation",
                },
            ).status_code
            == 200,
            "PostgreSQL reservation revocation failed",
        )
        invited = client.post(
            f"/api/admin/accounts/{participant_id}/feedback-pilot",
            headers=owner_headers,
            json={},
        )
        require(invited.status_code == 201, "PostgreSQL cohort invitation failed")
        report = client.get("/api/admin/crm/statistics")
        require(report.status_code == 200, "PostgreSQL CRM statistics failed")
        counts = report.json()
        require(
            sum(counts["memberships"].values()) == counts["total_users"],
            "PostgreSQL customer categories do not partition users",
        )
        smoke = client.post(
            "/api/admin/crm/contacts",
            headers=owner_headers,
            json={
                "email": f"production-smoke-{suffix}@example.com",
                "full_name": "Synthetic smoke",
                "primary_use": "research",
            },
        )
        require(smoke.status_code == 201, "PostgreSQL QA contact fixture failed")
        hidden = client.get("/api/admin/crm/contacts?account_category=smoke_test")
        require(hidden.status_code == 200, "PostgreSQL smoke filter failed")
        require(
            any(c["id"] == smoke.json()["id"] for c in hidden.json()["contacts"]),
            "PostgreSQL QA contact not classified",
        )
        require(
            client.get("/api/admin/crm/statistics").json()["total_users"] == counts["total_users"],
            "PostgreSQL QA contact inflated customers",
        )
        require(
            client.post("/api/auth/logout", headers=owner_headers, json={}).status_code == 200,
            "Feedback owner logout failed",
        )
        participant_login = client.post("/api/auth/login", json=credentials, headers=headers)
        require(participant_login.status_code == 200, "Feedback participant login failed")
        headers["X-CSRF-Token"] = participant_login.json()["csrf"]
        answers = {
            "usage": "not_used",
            "last_attempted_task": "Synthetic PostgreSQL verification",
            "blocker": "No product use yet",
            "feature_request": "",
            "feature_reason": "",
            "no_changes": True,
        }
        consent = {
            "terms_version": feedback.TERMS_VERSION,
            "accepted_terms": True,
            "baseline": answers,
        }
        accepted = client.post("/api/feedback/accept", headers=headers, json=consent)
        require(accepted.status_code == 200, "PostgreSQL consent transaction failed")
        original = accepted.json()
        replay = client.post("/api/feedback/accept", headers=headers, json=consent)
        require(replay.status_code == 200, "PostgreSQL consent replay failed")
        require(replay.json() == original, "Replay changed cohort state or term")
        with patch("landwolf.feedback._now", return_value=original["accepted_at"] + 21 * 86400):
            require(
                client.get("/api/sources").status_code == 403,
                "PostgreSQL overdue cohort was not gated",
            )
            submitted = client.post(
                "/api/feedback/responses",
                headers=headers,
                json={"survey_key": "day14", "survey_version": 1, "answers": answers},
            )
            require(submitted.status_code == 200, "PostgreSQL survey transaction failed")
            require(submitted.json()["access_allowed"], "Survey did not restore access")
            require(
                submitted.json()["expires_at"] == original["expires_at"],
                "Survey extended fixed pilot expiry",
            )
        require(client.get("/api/admin/feedback").status_code == 403, "Owner report leaked")
        # Leave populated research tables for the exact-content restore rehearsal.
        retained = client.post(
            "/api/hunts",
            headers=headers,
            json={
                "name": "Research restore",
                "criteria": {"mode": "fixed", "states": [], "min_acres": 1, "max_acres": 50},
            },
        )
        require(retained.status_code == 201, "Research restore Hunt failed")
        check_research(client, headers, retained.json()["id"], suffix)
    print(
        "Passed: PostgreSQL authentication, nationwide JSON filters, "
        "nulls, dates, pagination, permanent Saved deletion, retained accounts/sessions, "
        "trust snapshots, quarantine, parcel evidence, durable Hunt saves "
        "one-use password recovery, cohort consent/replay, overdue gating and survey restoration; "
        "private research, optimistic edits, comparisons and reconsideration"
    )


if __name__ == "__main__":
    main()
