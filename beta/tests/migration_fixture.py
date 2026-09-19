"""Synthetic retired schema for SQLite/PostgreSQL migration tests only."""

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from landwolf.db import Account, Base, Listing, LoginSession, SchemaVersion, SourceState


def legacy_fixture(engine: Engine, version: int) -> None:
    # Materialize the actual pre-v4 tables, not the current schema disguised
    # by an old version marker. This catches missing additive migrations.
    names = {
        "lw2_schema_version",
        "lw2_accounts",
        "lw2_sessions",
        "lw2_rate_buckets",
        "lw2_listings",
        "lw2_sources",
    }
    Base.metadata.create_all(
        engine, tables=[t for t in Base.metadata.sorted_tables if t.name in names]
    )
    with Session(engine) as session, session.begin():
        session.add(SchemaVersion(version=version))
        session.add(
            Account(
                id="migration-fixture",
                email="migration@example.com",
                password_hash="synthetic-hash",
                created_at=123,
            )
        )
        session.add(
            Listing(
                id="migration-fixture",
                source="tx_glo_public",
                active=False,
                payload={"title": "Synthetic migration listing"},
            )
        )
        session.flush()
        session.add(
            LoginSession(
                token_hash="synthetic-session",
                account_id="migration-fixture",
                csrf="synthetic-csrf",
                expires_at=2000000000,
                last_seen=123,
            )
        )
        session.add(SourceState(id="tx_glo_public", status="ready", record_count=1))
    with engine.begin() as connection:
        if version == 3:
            return
        connection.execute(
            text("""
            CREATE TABLE lw2_saved_properties (
                account_id VARCHAR(36) REFERENCES lw2_accounts(id),
                listing_id VARCHAR(80) REFERENCES lw2_listings(id),
                created_at INTEGER NOT NULL,
                PRIMARY KEY (account_id, listing_id)
            )
        """)
        )
        connection.execute(
            text("""
            INSERT INTO lw2_saved_properties VALUES ('migration-fixture','migration-fixture',123)
        """)
        )
        if version == 2:
            connection.execute(
                text("""
                CREATE TABLE lw2_saved_records (
                    account_id VARCHAR(36) REFERENCES lw2_accounts(id),
                    id VARCHAR(80), listing_id VARCHAR(80) REFERENCES lw2_listings(id),
                    title VARCHAR(300) NOT NULL, research_location JSON,
                    revision INTEGER NOT NULL, created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (account_id,id), UNIQUE (account_id,listing_id)
                )
            """)
            )
            connection.execute(
                text("""
                INSERT INTO lw2_saved_records VALUES
                ('migration-fixture','migration-fixture','migration-fixture',
                 'Synthetic linked property',NULL,1,123,123),
                ('migration-fixture','manual-fixture',NULL,'Synthetic manual property',
                 :location,1,123,123)
            """),
                {"location": '{"address":"123 Fixture St, Test City, TX 75000"}'},
            )
