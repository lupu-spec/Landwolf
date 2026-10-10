"""Private finance invariants; all transactions are synthetic, no vendor writes."""

import time
from datetime import UTC, date, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from landwolf import billing, finance
from landwolf.finance_models import FinanceExpense, FinanceSnapshot


def expense(**changes):
    return {
        "date": date.today().isoformat(),
        "vendor": "render",
        "amount_cents": 701,
        "allocation_percent": 50,
        **changes,
    }


def test_owner_report_unknown_not_zero_and_no_customer_details(client, owner_signed_in):
    response = client.get("/api/admin/finance")
    assert response.status_code == 200
    report = response.json()
    assert report["stripe"] is None
    assert report["history"][-1]["receipts_cents"] is None
    assert report["users"]["total_users"] == 0
    assert len(report["forecast"]) == 9
    assert len(report["recommendations"]) == 4
    assert "investor@example.com" not in response.text
    assert "no-store" in response.headers["cache-control"]


@pytest.mark.parametrize("path", ["", "/refresh", "/expenses", "/import", "/plan"])
def test_finance_requires_owner(client, signed_in, path):
    method = "GET" if not path else "PUT" if path == "/plan" else "POST"
    body = (
        expense()
        if path == "/expenses"
        else {"csv_text": "x", "allocation_percent": 100}
        if path == "/import"
        else {}
    )
    response = client.request(
        method,
        "/api/admin/finance" + path,
        headers=signed_in,
        json=body if method != "GET" else None,
    )
    assert response.status_code == 403


def test_finance_requires_session(client):
    assert client.get("/api/admin/finance").status_code == 401


def test_expense_csrf_allocation_duplicates_and_audit(client, owner_signed_in):
    assert client.post("/api/admin/finance/expenses", json=expense()).status_code == 403
    result = client.post("/api/admin/finance/expenses", headers=owner_signed_in, json=expense())
    assert result.status_code == 201, result.text
    assert result.json()["business_cents"] == 351
    assert (
        client.post(
            "/api/admin/finance/expenses",
            headers=owner_signed_in,
            json=expense(allocation_percent=100),
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/admin/finance/expenses",
            headers=owner_signed_in,
            json=expense(reference="invoice-two"),
        ).status_code
        == 201
    )
    assert client.get("/api/admin/finance").json()["history"][-1]["expenses_cents"] == 702


@pytest.mark.parametrize(
    "changes",
    [
        {"amount_cents": True},
        {"amount_cents": 1.2},
        {"amount_cents": 100000001},
        {"allocation_percent": -1},
        {"allocation_percent": 101},
        {"vendor": "amex"},
        {"date": "2026-02-30"},
        {"date": "2100-01-01"},
        {"reference": "1234567890123456"},
    ],
)
def test_expense_invalid_inputs_do_not_write(client, owner_signed_in, changes):
    assert (
        client.post(
            "/api/admin/finance/expenses", headers=owner_signed_in, json=expense(**changes)
        ).status_code
        == 422
    )
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(FinanceExpense)) == 0


def test_csv_preview_confirmation_privacy_credits_and_reimport(client, owner_signed_in):
    body = {
        "csv_text": "Date,Description,Amount\n09/01/2026,RENDER.COM,7.00\n"
        "09/01/2026,Personal sensitive shopping,55\n09/02/2026,OPENAI CHATGPT,-2.00\n",
        "allocation_percent": 50,
    }
    result = client.post("/api/admin/finance/import", headers=owner_signed_in, json=body)
    assert result.status_code == 200, result.text
    assert result.json()["selected"] == 2 and result.json()["skipped"] == 1
    assert "sensitive" not in result.text
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(FinanceExpense)) == 0
    body["confirm"] = True
    assert (
        client.post("/api/admin/finance/import", headers=owner_signed_in, json=body).json()[
            "selected"
        ]
        == 2
    )
    result = client.post("/api/admin/finance/import", headers=owner_signed_in, json=body).json()
    assert result["duplicates"] == 2 and result["selected"] == 0
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(FinanceExpense)) == 2


@pytest.mark.parametrize(
    "csv",
    [
        "Date,Amount\n2026-09-01,7",
        "Date,Description,Amount\n2026-09-01,Render,7\n2026-09-02,Render,NaN",
    ],
)
def test_invalid_csv_atomic(client, owner_signed_in, csv):
    response = client.post(
        "/api/admin/finance/import",
        headers=owner_signed_in,
        json={"csv_text": csv, "allocation_percent": 100, "confirm": True},
    )
    assert response.status_code == 422
    assert client.get("/api/admin/finance").json()["expenses"] == []


def test_plan_optimistic_revision_and_annual_validation(client, owner_signed_in):
    plan = finance.PlanInput().model_dump()
    plan["other"] = {"amount_cents": 100, "interval": "year"}
    assert (
        client.put("/api/admin/finance/plan", headers=owner_signed_in, json=plan).status_code == 422
    )
    plan["other"]["renewal_date"] = "2027-01-01"
    assert (
        client.put("/api/admin/finance/plan", headers=owner_signed_in, json=plan).json()["revision"]
        == 1
    )
    assert (
        client.put("/api/admin/finance/plan", headers=owner_signed_in, json=plan).status_code == 409
    )
    assert client.get("/api/admin/finance").json()["plan"]["revision"] == 1


def test_forecast_year_rollover_annual_cost_and_unknown_revenue():
    plan = finance.PlanInput(
        render=finance.Budget(amount_cents=700),
        spaceship=finance.Budget(amount_cents=1200, interval="year", renewal_date="2026-01-01"),
        processing_percent=0,
        processing_fixed_cents=0,
        churn_percent=0,
        new_users_monthly=10,
        conversion_percent=10,
    )
    rows = finance.forecasts(
        plan, {"active_subscriptions": 1, "plan_run_rate_cents": 2900}, date(2026, 12, 15)
    )
    base = [row for row in rows if row["scenario"] == "base"]
    assert [row["month"] for row in base] == ["2027-01", "2027-02", "2027-03"]
    assert [row["revenue_cents"] for row in base] == [5800, 8700, 11600]
    assert [row["cost_cents"] for row in base] == [1900, 700, 700]
    assert base[0]["missing_costs"] == ["openai"]
    assert all(row["revenue_cents"] is None for row in finance.forecasts(plan, None, date.today()))


def test_failed_refresh_preserves_complete_snapshot(client, owner_signed_in, monkeypatch):
    payload = {
        "history": {},
        "as_of": 1,
        "active_subscriptions": 0,
        "plan_run_rate_cents": 0,
        "scheduled_cancellations": 0,
    }
    with client.app.state.factory() as session, session.begin():
        session.add(FinanceSnapshot(id="stripe", payload=payload, updated_at=1))

    def fail(settings):
        raise HTTPException(503, "Synthetic upstream failure")

    monkeypatch.setattr(finance, "stripe_snapshot", fail)
    assert (
        client.post("/api/admin/finance/refresh", headers=owner_signed_in, json={}).status_code
        == 503
    )
    assert client.get("/api/admin/finance").json()["stripe"] == payload


def test_stripe_cash_refunds_fees_subscription_collections_and_annual_run_rate(client, monkeypatch):
    settings = client.app.state.settings
    settings.payments_enabled = True
    settings.stripe_account_id = "acct_fixture"
    timestamp = int(time.time())
    calls = []
    records = {
        "/account": {"id": "acct_fixture"},
        "/invoices": {
            "data": [
                {
                    "id": "in_1",
                    "livemode": True,
                    "currency": "usd",
                    "amount_paid": 2900,
                    "parent": {"subscription_details": {"subscription": "sub_1"}},
                    "status_transitions": {"paid_at": timestamp},
                }
            ],
            "has_more": False,
        },
        "/balance_transactions": {
            "data": [
                {
                    "id": "txn_1",
                    "currency": "usd",
                    "created": timestamp,
                    "type": "charge",
                    "amount": 2900,
                    "fee": 100,
                },
                {
                    "id": "txn_2",
                    "currency": "usd",
                    "created": timestamp,
                    "type": "refund",
                    "amount": -500,
                    "fee": 0,
                },
                {
                    "id": "txn_3",
                    "currency": "usd",
                    "created": timestamp,
                    "type": "payout",
                    "amount": -2300,
                    "fee": 0,
                },
            ],
            "has_more": False,
        },
        "/subscriptions": {
            "data": [
                {
                    "id": "sub_1",
                    "livemode": True,
                    "status": "active",
                    "cancel_at_period_end": True,
                    "items": {
                        "has_more": False,
                        "data": [
                            {
                                "quantity": 1,
                                "price": {
                                    "currency": "usd",
                                    "unit_amount": 34800,
                                    "recurring": {"interval": "year", "interval_count": 1},
                                },
                            }
                        ],
                    },
                }
            ],
            "has_more": False,
        },
    }

    def call(self, method, path, fields=None):
        calls.append(method)
        return records[path]

    monkeypatch.setattr(billing.StripeAPI, "call", call)
    result = finance.stripe_snapshot(settings)
    values = result["history"][datetime.now(UTC).strftime("%Y-%m")]
    assert values == {"receipts": 2900, "refunds": 500, "fees": 100, "subscription_receipts": 2900}
    assert result["plan_run_rate_cents"] == 2900 and result["active_subscriptions"] == 1
    assert result["scheduled_cancellations"] == 1
    assert calls == ["GET"] * 4


def test_pagination_repeated_cursor_fails_closed():
    class Fake:
        def call(self, method, path, fields=None):
            return {"data": [{"id": "same"}], "has_more": True}

    with pytest.raises(HTTPException):
        finance.stripe_list(Fake(), "/invoices", {}, time.monotonic() + 20)


@pytest.mark.parametrize("value", [[], "invalid", 4, True])
def test_invalid_nested_stripe_objects_fail_closed(value):
    with pytest.raises(HTTPException) as error:
        finance.object_field({"parent": value}, "parent")
    assert error.value.status_code == 503


def test_csv_large_preview_uses_bounded_import_body_limit(client, owner_signed_in):
    text = (
        "Date,Description,Amount\n" + "2026-09-01,Unrelated personal row not retained,1.00\n" * 400
    )
    assert len(text) > 16384
    result = client.post(
        "/api/admin/finance/import",
        headers=owner_signed_in,
        json={"csv_text": text, "allocation_percent": 100},
    )
    assert result.status_code == 200, result.text
    assert result.json()["skipped"] == 400 and result.json()["rows"] == []


def test_credit_offset_is_allocated_and_all_time_unknown_stays_unknown(client, owner_signed_in):
    result = client.post(
        "/api/admin/finance/expenses", headers=owner_signed_in, json=expense(amount_cents=-701)
    )
    assert result.status_code == 201 and result.json()["business_cents"] == -351
    report = client.get("/api/admin/finance").json()
    assert report["history"][-1]["expenses_cents"] == -351
    assert report["subscription_collections_all_time_cents"] is None


@pytest.mark.parametrize(
    "csv",
    [
        "Date,Description,Amount\n2026-09-01,Render,$1,200.00",
        'Date,Description,Amount\n2026-09-01,Render,"12,34.00"',
        "Date,Description,Amount,Amount\n2026-09-01,Render,1.00,200.00",
    ],
)
def test_ambiguous_csv_never_silently_changes_amounts(csv):
    with pytest.raises(HTTPException) as error:
        finance.import_rows(finance.ImportInput(csv_text=csv, allocation_percent=100))
    assert error.value.status_code == 422


def test_quoted_grouped_currency_and_parenthesized_credit_are_exact():
    rows, skipped = finance.import_rows(
        finance.ImportInput(
            csv_text='Date,Description,Amount\n2026-09-01,Render,"$1,200.50"\n'
            '2026-09-02,OpenAI,"($12.50)"',
            allocation_percent=100,
        )
    )
    assert skipped == 0 and [row.amount_cents for row in rows] == [120050, -1250]
