"""Exercise nationwide JSON queries and saves against a disposable PostgreSQL database."""

import os
import uuid
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from landwolf.config import Settings
from landwolf.db import (
    Account,
    Base,
    Listing,
    SavedProperty,
    SavedRecord,
    SchemaVersion,
    database,
    initialize,
)
from landwolf.main import create_app
from landwolf.schemas import PropertyRecord


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    url = os.environ.get("LANDWOLF_TEST_POSTGRES_URL", "")
    if not url or not urlsplit(url).path.endswith("/landwolf_ci"):
        raise SystemExit("A disposable landwolf_ci PostgreSQL database is required")
    settings = Settings(
        environment="test", database_url=url, public_origin="http://testserver", auto_sync=False
    )
    suffix = uuid.uuid4().hex[:12]
    engine, factory = database(url)
    if not inspect(engine).has_table(SchemaVersion.__tablename__):
        Base.metadata.create_all(
            engine,
            tables=[
                table
                for table in Base.metadata.sorted_tables
                if table.name != SavedRecord.__tablename__
            ],
        )
        with factory() as session, session.begin():
            session.add(SchemaVersion(version=1))
            session.add(
                Account(
                    id="migration-fixture",
                    email="migration@example.com",
                    password_hash="synthetic-hash",
                )
            )
            session.add(
                Listing(
                    id="migration-fixture",
                    source="tx_glo_public",
                    active=False,
                    payload={"title": "Synthetic migration fixture"},
                )
            )
            session.flush()
            session.add(
                SavedProperty(
                    account_id="migration-fixture", listing_id="migration-fixture", created_at=123
                )
            )
    initialize(engine)
    initialize(engine)
    with factory() as session:
        require(
            session.scalars(select(SchemaVersion.version)).all() == [2], "Migration version failed"
        )
        migrated = session.get(SavedRecord, ("migration-fixture", "migration-fixture"))
        require(
            migrated is not None and migrated.created_at == 123,
            "PostgreSQL bookmark migration failed",
        )
        require(
            session.get(SavedProperty, ("migration-fixture", "migration-fixture")) is not None,
            "Old bookmark removed",
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
        listing_id = f"pg-{suffix}-known"
        for _ in range(2):
            require(
                client.put(f"/api/saved/{listing_id}", json={}, headers=headers).status_code == 200,
                "Save failed",
            )
        require(search(saved_only=True)["total"] == 1, "Saved search duplicated or lost property")
        saved = client.get(f"/api/saved/{listing_id}").json()
        edited = client.patch(
            f"/api/saved/{listing_id}",
            json={
                "title": "CI saved location",
                "location": {"latitude": 35.7804, "longitude": -78.6391},
                "revision": saved["revision"],
            },
            headers=headers,
        )
        require(
            edited.status_code == 200 and edited.json()["revision"] == 2, "Location update failed"
        )
        manual = {
            "manual_id": str(uuid.uuid4()),
            "title": "CI manual property",
            "location": {"address": "123 Fixture St, Test City, TX 75000"},
        }
        for _ in range(2):
            require(
                client.post("/api/saved", json=manual, headers=headers).status_code == 200,
                "Manual save failed",
            )
        require(
            client.get("/api/saved").json()["total"] == 2,
            "Manual save retry duplicated or lost property",
        )
        require(
            len(client.get("/api/sources").json()["states"]) == 50, "Coverage aggregation failed"
        )
        require(
            client.request(
                "DELETE", f"/api/saved/{listing_id}", json={}, headers=headers
            ).status_code
            == 200,
            "Unsave failed",
        )
        require(
            client.post("/api/auth/logout", json={}, headers=headers).status_code == 200,
            "Logout failed",
        )
        require(
            client.get("/api/sources").status_code == 401, "Source endpoint leaked after logout"
        )
    print(
        "Passed: PostgreSQL authentication, nationwide JSON filters, "
        "nulls, dates, pagination, v1 migration, manual saves and persistent research locations"
    )


if __name__ == "__main__":
    main()
