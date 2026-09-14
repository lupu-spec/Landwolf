"""Isolated test databases and explicit synthetic fixtures; never runtime inventory."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from landwolf.config import Settings
from landwolf.db import Listing
from landwolf.main import create_app
from landwolf.schemas import AnalysisInput, PropertyRecord


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        public_origin="http://testserver",
        auto_sync=False,
    )
    with TestClient(create_app(settings)) as browser:
        yield browser


def register(client: TestClient, email: str = "investor@example.com") -> dict[str, str]:
    headers = {"Origin": "http://testserver", "X-LandWolf-Client": "web"}
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Test-only passphrase 847!"},
        headers=headers,
    )
    assert response.status_code == 201, response.status_code
    return {**headers, "X-CSRF-Token": response.json()["csrf"]}


@pytest.fixture
def signed_in(client: TestClient) -> dict[str, str]:
    return register(client)


def seed(factory: Any) -> None:
    with factory() as session, session.begin():
        for tract, county, price, acres, active in [
            ("99001", "Fixture Eastland", 100000, 10, True),
            ("99002", "Fixture Travis", 200000, 20, True),
            ("99003", "Fixture Hays", 50000, 5, False),
        ]:
            record = PropertyRecord(
                id=f"glo-{tract}",
                tract=tract,
                title=f"Test fixture {tract}",
                source_url=f"https://www.glo.texas.gov/veterans/land-sale/public/tract/{tract}",
                county=county,
                acres=acres,
                asking_price=price,
                latitude=32.48455,
                longitude=-98.5175,
                legal_description="Synthetic test description; not a real listing.",
                location_description="Synthetic test location.",
                retrieved_at="2026-09-14T00:00:00+00:00",
            )
            session.add(
                Listing(
                    id=record.id, source=record.source, active=active, payload=record.model_dump()
                )
            )


@pytest.fixture
def inventory(client: TestClient) -> None:
    seed(client.app.state.factory)


@pytest.fixture
def scenario() -> AnalysisInput:
    return AnalysisInput(
        purchase_price=100000,
        resale={"low": 200000, "likely": 200000, "high": 200000},
        repairs={"low": 10000, "likely": 10000, "high": 10000},
        lien_reserve=5000,
        closing_costs=5000,
        holding_months=12,
        monthly_holding=500,
        buyer_premium_pct=10,
        selling_cost_pct=6,
        annual_financing_pct=12,
        target_roi_pct=20,
        min_profit=25000,
        max_loss_probability_pct=10,
        iterations=1000,
        seed=42,
    )
