"""CSV privacy, fidelity, spreadsheet safety and bounded-failure contracts."""

import csv
import io

import pytest
from conftest import register
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from test_admin_billing import owner_and_user
from test_feedback import ACCEPT, enroll

from landwolf import feedback_export
from landwolf.db import Account

PATH = "/api/admin/feedback/users.csv"
PRIVATE_PATHS = (
    PATH,
    "/api/admin/accounts",
    "/api/admin/feedback",
    "/api/admin/feedback/responses",
)


def rows(response):
    return list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"), newline="")))


def test_owner_export_round_trip_headers_and_no_sensitive_fields(client):
    owner, user, headers = owner_and_user(client)
    assert (
        client.post(
            f"/api/admin/accounts/{user.id}/feedback-pilot", headers=headers, json={}
        ).status_code
        == 201
    )
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="landwolf-users-'
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    exported = rows(response)
    assert [row["Email"] for row in exported] == [user.email, owner.email]
    assert exported[0]["Pilot invited (UTC)"].endswith("Z")
    assert exported[0]["Pilot accepted (UTC)"] == ""
    assert exported[1]["Account role"] == "Owner"
    assert set(exported[0]) == {
        "Email",
        "Account role",
        "Pilot invited (UTC)",
        "Pilot accepted (UTC)",
        "Pilot ends (UTC)",
        "Pilot revoked (UTC)",
    }
    assert "password" not in response.text and owner.id not in response.text
    with client.app.state.factory() as session:
        account = session.get(Account, user.id)
        account.email = '"fixture,é\nline"@example.com'
        session.commit()
    assert rows(client.get(PATH))[0]["Email"] == '"fixture,é\nline"@example.com'


@pytest.mark.parametrize("payments_enabled", [False, True])
def test_private_lists_reject_guests_customers_and_revoked_owner(client, payments_enabled):
    client.app.state.settings.payments_enabled = payments_enabled
    for path in PRIVATE_PATHS:
        response = client.get(path)
        assert response.status_code == 401
        assert "Content-Disposition" not in response.headers
    headers = register(client)
    for path in PRIVATE_PATHS:
        assert client.get(path).status_code == 403
    client.post("/api/auth/logout", headers=headers, json={})
    owner, _, _ = owner_and_user(client)
    assert client.get(PATH).status_code == 200
    client.app.state.settings.owner_account_id = None
    for path in PRIVATE_PATHS:
        response = client.get(path)
        assert response.status_code == 403
        assert owner.email not in response.text


def test_pilot_and_complimentary_access_do_not_grant_export(client):
    user, headers = enroll(client)
    assert client.post("/api/feedback/accept", headers=headers, json=ACCEPT).status_code == 200
    for path in PRIVATE_PATHS:
        assert client.get(path).status_code == 403
    from landwolf.db import BillingExemption

    with client.app.state.factory() as session:
        session.add(
            BillingExemption(
                id="fixture-exemption",
                account_id=user.id,
                status="active",
                granted_by_account_id=client.app.state.settings.owner_account_id,
                granted_at=1,
                created_at=1,
                updated_at=1,
            )
        )
        session.commit()
    assert client.get("/api/feedback").json()["access_override"] == "complimentary"
    for path in PRIVATE_PATHS:
        assert client.get(path).status_code == 403


def test_export_bound_is_complete_or_explicitly_rejected(client, monkeypatch):
    owner_and_user(client)
    monkeypatch.setattr(feedback_export, "MAX_EXPORT_USERS", 2)
    assert len(rows(client.get(PATH))) == 2
    monkeypatch.setattr(feedback_export, "MAX_EXPORT_USERS", 1)
    response = client.get(PATH)
    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/json")
    assert "partial" in response.json()["detail"]
    assert "Content-Disposition" not in response.headers


def test_export_database_failure_is_retryable_without_personal_data(client):
    owner_and_user(client)
    with client.app.state.factory() as session:
        engine = session.get_bind()

    def fail_export(connection, cursor, statement, parameters, context, many):
        if "LEFT OUTER JOIN lw2_feedback_enrollments" in statement:
            raise OperationalError("fixture database failure", {}, Exception("private detail"))

    event.listen(engine, "before_cursor_execute", fail_export)
    try:
        response = client.get(PATH)
        assert response.status_code == 503
        assert "private detail" not in response.text
        assert "Content-Disposition" not in response.headers
    finally:
        event.remove(engine, "before_cursor_execute", fail_export)
    assert client.get(PATH).status_code == 200


@pytest.mark.parametrize(
    "text", ["=1+1", "+SUM(1)", "-1", "@SUM(1)", "  =1", "\tfixture", "\nfixture", "\rfixture"]
)
def test_formula_and_control_prefixes_are_text(text):
    assert feedback_export.spreadsheet_text(text) == "'" + text


@given(st.text(max_size=254))
def test_spreadsheet_safety_and_csv_round_trip(value):
    safe = feedback_export.spreadsheet_text(value)
    assert not safe.lstrip().startswith(("=", "+", "-", "@"))
    assert not safe.startswith(("\t", "\r", "\n"))
    assert safe == value or safe == "'" + value
    output = io.StringIO(newline="")
    csv.writer(output).writerow([safe])
    assert next(csv.reader(io.StringIO(output.getvalue(), newline=""))) == [safe]


def test_export_includes_users_beyond_the_display_limit(client):
    owner_and_user(client)
    with client.app.state.factory() as session:
        session.add_all(
            [
                Account(
                    id=f"fixture-{index}",
                    email=f"fixture-{index:04d}@example.com",
                    password_hash="fixture-disabled",
                )
                for index in range(501)
            ]
        )
        session.commit()
    assert len(client.get("/api/admin/accounts").json()["accounts"]) == 500
    exported = rows(client.get(PATH))
    assert len(exported) == 503
    assert len({row["Email"] for row in exported}) == 503
