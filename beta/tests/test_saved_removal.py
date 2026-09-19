"""Saved retirement, permanent storage deletion and retained account boundaries."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from migration_fixture import legacy_fixture
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from landwolf.db import (
    Account,
    Listing,
    LoginSession,
    SchemaVersion,
    SourceState,
    database,
    initialize,
)
from landwolf.locations import source_location
from landwolf.schemas import PropertyRecord


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/saved"),
        ("POST", "/api/saved"),
        ("GET", "/api/saved/glo-99001"),
        ("PUT", "/api/saved/glo-99001"),
        ("PATCH", "/api/saved/glo-99001"),
        ("DELETE", "/api/saved/glo-99001"),
    ],
)
@pytest.mark.parametrize("authenticated", [False, True])
def test_retired_routes_are_absent(
    client: TestClient, method: str, path: str, authenticated: bool
) -> None:
    from conftest import register

    headers = register(client) if authenticated else {}
    assert client.request(method, path, json={}, headers=headers).status_code == 404


@pytest.mark.parametrize("value", [True, False])
def test_retired_search_contract_rejected(
    client: TestClient, signed_in: dict[str, str], value: bool
) -> None:
    response = client.post("/api/search", json={"saved_only": value}, headers=signed_in)
    assert response.status_code == 422


def test_property_responses_have_no_saved_state(
    client: TestClient, signed_in: dict[str, str], inventory: None
) -> None:
    records = client.post("/api/search", json={}, headers=signed_in).json()["results"]
    records.append(client.get("/api/properties/glo-99001").json())
    for record in records:
        assert not {"saved", "saved_record", "location_origin"}.intersection(record)
        assert record["research_location"]["latitude"] == 32.48455
    with client.app.state.factory() as session:
        tables = inspect(session.get_bind()).get_table_names()
        assert "lw2_saved_records" not in tables and "lw2_saved_properties" not in tables


@pytest.mark.parametrize("version", [1, 2])
def test_migration_permanently_drops_saves_preserves_other_data(
    tmp_path: Path, version: int
) -> None:
    engine, _ = database(f"sqlite:///{tmp_path / 'migration.db'}")
    legacy_fixture(engine, version)
    initialize(engine)
    initialize(engine)
    assert "lw2_saved_records" not in inspect(engine).get_table_names()
    assert "lw2_saved_properties" not in inspect(engine).get_table_names()
    with Session(engine) as session:
        assert session.scalars(select(SchemaVersion.version)).all() == [3]
        account = session.get(Account, "migration-fixture")
        assert account.password_hash == "synthetic-hash" and account.created_at == 123
        assert session.get(LoginSession, "synthetic-session").csrf == "synthetic-csrf"
        assert session.get(Listing, "migration-fixture").payload == {
            "title": "Synthetic migration listing"
        }
        assert session.get(SourceState, "tx_glo_public").record_count == 1
    engine.dispose()


def test_migration_failure_rolls_back_deletion(tmp_path: Path, monkeypatch) -> None:
    engine, _ = database(f"sqlite:///{tmp_path / 'rollback.db'}")
    legacy_fixture(engine, 2)
    execute = Connection.execute

    def fail_second_drop(self, statement, *args, **kwargs):
        if str(statement) == "DROP TABLE IF EXISTS lw2_saved_properties":
            raise RuntimeError("Synthetic migration failure")
        return execute(self, statement, *args, **kwargs)

    monkeypatch.setattr(Connection, "execute", fail_second_drop)
    with pytest.raises(RuntimeError, match="Synthetic migration failure"):
        initialize(engine)
    with engine.connect() as connection:
        assert connection.scalar(select(SchemaVersion.version)) == 2
        assert connection.scalar(text("SELECT count(*) FROM lw2_saved_records")) == 2
        assert connection.scalar(text("SELECT count(*) FROM lw2_saved_properties")) == 1
    engine.dispose()


def test_unknown_schema_fails_before_deleting_data(tmp_path: Path) -> None:
    engine, _ = database(f"sqlite:///{tmp_path / 'unknown.db'}")
    legacy_fixture(engine, 2)
    with engine.begin() as connection:
        connection.execute(text("UPDATE lw2_schema_version SET version=999"))
    with pytest.raises(RuntimeError, match="Unsupported"):
        initialize(engine)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM lw2_saved_records")) == 2
    engine.dispose()


@pytest.mark.parametrize(
    "source", ["usda_resales", "irs_auctions", "us_treasury", "tx_glo_public", "ak_dnr"]
)
def test_source_address_handoff_remains(source: str) -> None:
    record = PropertyRecord(
        id="fixture",
        tract="fixture",
        title="Fixture",
        source=source,
        source_url="https://www.glo.texas.gov",
        retrieved_at="2099-01-01",
        location_description="123 Fixture St, Test City, TX 75000",
    )
    point = source_location(record)
    assert point and point.address == record.location_description and point.latitude is None
    for value in [None, "tract 123", "123 county parcel", "123 Test St, City, CA 75000", "x" * 301]:
        record.location_description = value
        assert source_location(record) is None
