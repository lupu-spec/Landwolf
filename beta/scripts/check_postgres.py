"""Exercise nationwide JSON queries and saves against a disposable PostgreSQL database."""

import os
import uuid
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from landwolf.config import Settings
from landwolf.db import Listing
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
    app = create_app(settings)
    suffix = uuid.uuid4().hex[:12]
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
        "nulls, dates, pagination and saves"
    )


if __name__ == "__main__":
    main()
