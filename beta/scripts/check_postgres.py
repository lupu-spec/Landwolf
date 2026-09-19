"""Check search and permanent Saved removal against disposable PostgreSQL."""

import os
import secrets
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from landwolf import auth
from landwolf.config import Settings
from landwolf.db import (
    SCHEMA_VERSION,
    Account,
    AccountAction,
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
        response = client.post("/api/auth/register", json=credentials, headers=headers)
        require(response.status_code == 201, "PostgreSQL registration failed")
        headers["X-CSRF-Token"] = response.json()["csrf"]

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
        require(
            len(client.get("/api/sources").json()["states"]) == 50, "Coverage aggregation failed"
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
    print(
        "Passed: PostgreSQL authentication, nationwide JSON filters, "
        "nulls, dates, pagination, permanent Saved deletion, retained accounts/sessions, "
        "trust snapshots, quarantine, parcel evidence and one-use password recovery"
    )


if __name__ == "__main__":
    main()
