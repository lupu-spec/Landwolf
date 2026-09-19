"""Public-behavior regression gates for provenance, identity and snapshot integrity."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from landwolf.db import Listing, ParcelIdentity, SaleEvent, SourceRun, SourceState
from landwolf.framework import PartnerConsent, SourceReadiness
from landwolf.schemas import PropertyRecord
from landwolf.trust import fingerprint, parcel_key, publish_snapshot


def item(number: int, **changes) -> PropertyRecord:
    return PropertyRecord.model_validate(
        {
            "id": f"trust-{number}",
            "tract": str(number),
            "title": "Synthetic trust fixture",
            "county": "Fixture County",
            "state": "TX",
            "parcel_number": f"00-{number}",
            "source_url": "https://www.glo.texas.gov/veterans/land-sale/public",
            "asking_price": 100,
            "retrieved_at": "2099-01-01T00:00:00Z",
            **changes,
        }
    )


def test_identity_is_county_scoped_and_never_inferred_from_point():
    first = item(1)
    assert parcel_key(first) == parcel_key(item(9, parcel_number="00-1"))
    for change in [{"county": "Other"}, {"state": "AZ"}, {"parcel_number": "1"}]:
        assert parcel_key(first) != parcel_key(item(1, **change))
    assert parcel_key(item(1, parcel_number=None, latitude=30, longitude=-100)) is None
    assert parcel_key(item(1, county=None)) is None


def test_fingerprint_ignores_retrieval_time_but_not_price():
    assert fingerprint([item(1)]) == fingerprint([item(1, retrieved_at="2099-02-01")])
    assert fingerprint([item(1)]) != fingerprint([item(1, asking_price=101)])


def test_sales_share_identity_without_overwriting_events(client: TestClient):
    with client.app.state.factory() as session, session.begin():
        assert publish_snapshot(session, "tx_glo_public", [item(1)])
    with client.app.state.factory() as session, session.begin():
        assert publish_snapshot(session, "tx_glo_public", [item(2, parcel_number="00-1")])
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(ParcelIdentity)) == 1
        assert session.scalar(select(func.count()).select_from(SaleEvent)) == 2
        assert not session.get(Listing, "trust-1").active
        assert session.get(Listing, "trust-2").active


@pytest.mark.parametrize("change", ["empty", "missing", "prices"])
def test_suspicious_refresh_preserves_good_snapshot(client: TestClient, change: str):
    records = [item(n) for n in range(12)]
    with client.app.state.factory() as session, session.begin():
        publish_snapshot(session, "tx_glo_public", records)
    candidate = (
        []
        if change == "empty"
        else records[:2]
        if change == "missing"
        else [item(n, asking_price=10000) for n in range(12)]
    )
    with client.app.state.factory() as session, session.begin():
        assert not publish_snapshot(session, "tx_glo_public", candidate)
    with client.app.state.factory() as session:
        state = session.get(SourceState, "tx_glo_public")
        assert state.status == "review_required" and state.record_count == 12
        assert session.scalar(select(func.count()).select_from(Listing).where(Listing.active)) == 12
        assert session.get(Listing, "trust-0").payload["asking_price"] == 100


def test_review_approval_matches_exact_candidate(client: TestClient):
    with client.app.state.factory() as session, session.begin():
        publish_snapshot(session, "tx_glo_public", [item(n) for n in range(12)])
        assert not publish_snapshot(session, "tx_glo_public", [])
        review = session.scalar(select(SourceRun).where(SourceRun.status == "review_required"))
        review.approved = True
    with client.app.state.factory() as session, session.begin():
        assert not publish_snapshot(session, "tx_glo_public", [item(1)])
        assert publish_snapshot(session, "tx_glo_public", [])
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(Listing).where(Listing.active)) == 0


def test_expired_sales_can_leave_inventory_without_quarantine(client: TestClient):
    old = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    with client.app.state.factory() as session, session.begin():
        publish_snapshot(session, "tx_glo_public", [item(n, auction_date=old) for n in range(12)])
        assert publish_snapshot(session, "tx_glo_public", [])


@pytest.mark.parametrize("records", [[item(1), item(1)], [item(2, source="ar_cosl")]])
def test_invalid_source_snapshot_cannot_publish(client: TestClient, records):
    with client.app.state.factory() as session, pytest.raises(ValueError), session.begin():
        publish_snapshot(session, "tx_glo_public", records)
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(Listing)) == 0


def test_authenticated_evidence_and_coverage(client, signed_in, inventory):
    detail = client.get("/api/properties/glo-99001").json()
    assert detail["trust"]["identity"]["status"] == "unresolved"
    assert detail["trust"]["freshness"] == "needs_attention"
    facts = {fact["field"]: fact for fact in detail["trust"]["evidence"]}
    assert facts["parcel_number"]["basis"] == "unknown"
    assert facts["asking_price"]["basis"] == "reported"
    assert facts["asking_price"]["effective_date"] is None
    sources = client.get("/api/sources").json()
    assert len(sources["states"]) == 50
    assert all(row["coverage"] == "partial" for row in sources["counties"])
    capabilities = client.get("/api/capabilities").json()["priorities"]
    assert [row["priority"] for row in capabilities] == [1, 2, 3, 4]
    assert all(row["status"] == "framework" for row in capabilities[1:])


def test_framework_does_not_expose_unimplemented_services(client):
    assert client.get("/api/capabilities").status_code == 401
    assert client.post("/api/partners/inquiries", json={}).status_code == 404
    assert not SourceReadiness(source_id="fixture").eligible
    with pytest.raises(ValueError):
        PartnerConsent(
            recipient_ids=["fixture"],
            shared_fields=["email"],
            disclosure_version="v1",
            consent=False,
        )
