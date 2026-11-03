"""LupuSpec cash ledger accounting and L91 consolidation invariants."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from landwolf.finance_models import FinanceExpense, LupuSpecFinanceEntry


def row(**updates):
    return {
        "date": datetime.now(UTC).date().isoformat(),
        "capability": "studio",
        "kind": "receipt",
        "amount_cents": 25000,
        "reference": "job_A",
        **updates,
    }


def record(client, credentials, **updates):
    return client.post(
        "/api/admin/finance/lupuspec/entries",
        headers=credentials,
        json=row(**updates),
    )


def test_only_owner_can_create_cash_entries(client, signed_in, owner_signed_in):
    assert client.post("/api/admin/finance/lupuspec/entries", json=row()).status_code == 403
    client.app.state.settings.owner_account_id = None
    assert record(client, signed_in).status_code == 403


def test_manual_cash_entries_and_four_capability_totals(client, owner_signed_in):
    entries = [
        ("studio", "receipt", 12000),
        ("studio", "expense", 2200),
        ("software", "receipt", 15000),
        ("software", "expense", 4000),
        ("fabrication", "receipt", 8000),
        ("fabrication", "expense", 3300),
        ("supply", "receipt", 3500),
        ("supply", "expense", 900),
    ]
    for i, (capability, kind, amount) in enumerate(entries):
        response = record(
            client,
            owner_signed_in,
            capability=capability,
            kind=kind,
            amount_cents=amount,
            reference="job_" + str(i),
        )
        assert response.status_code == 201, response.text
    report = client.get("/api/admin/finance").json()
    totals = report["lupuspec"]["totals"]
    assert totals == {
        "receipts_cents": 38500,
        "expenses_cents": 10400,
        "net_cents": 28100,
    }
    assert report["lupuspec"]["capabilities"]["studio"]["net_cents"] == 9800
    assert report["lupuspec"]["capabilities"]["software"]["net_cents"] == 11000
    assert report["lupuspec"]["capabilities"]["fabrication"]["net_cents"] == 4700
    assert report["lupuspec"]["capabilities"]["supply"]["net_cents"] == 2600
    assert report["history"][-1]["lupuspec_receipts_cents"] == 38500
    assert report["history"][-1]["lupuspec_expenses_cents"] == 10400
    assert report["history"][-1]["consolidated_receipts_cents"] is None
    assert report["history"][-1]["consolidated_net_cents"] is None
    assert report["stripe"] is None
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(FinanceExpense)) == 0
        assert session.scalar(select(func.count()).select_from(LupuSpecFinanceEntry)) == 8


def test_duplication_protection_and_credit_offset(client, owner_signed_in):
    first = record(client, owner_signed_in)
    assert first.status_code == 201, first.text
    assert record(client, owner_signed_in).status_code == 409
    offset = record(client, owner_signed_in, amount_cents=-25000, reference="reversal_A")
    assert offset.status_code == 201, offset.text
    report = client.get("/api/admin/finance").json()
    assert report["lupuspec"]["totals"]["net_cents"] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"amount_cents": 0},
        {"amount_cents": 100000001},
        {"amount_cents": 1.1},
        {"amount_cents": True},
        {"capability": "unallocated"},
        {"kind": "transfer"},
        {"reference": "1234567890123456"},
        {"date": "2099-01-01"},
        {"date": "2026-02-30"},
    ],
)
def test_invalid_financial_entry_never_writes(client, owner_signed_in, change):
    response = record(client, owner_signed_in, **change)
    assert response.status_code == 422, response.text
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(LupuSpecFinanceEntry)) == 0


def test_no_cross_product_double_count_for_original_landwolf_expenses(client, owner_signed_in):
    assert record(client, owner_signed_in, kind="expense").status_code == 201
    response = client.post(
        "/api/admin/finance/expenses",
        headers=owner_signed_in,
        json={
            "date": datetime.now(UTC).date().isoformat(),
            "vendor": "render",
            "amount_cents": 3000,
            "allocation_percent": 100,
        },
    )
    assert response.status_code == 201, response.text
    report = client.get("/api/admin/finance").json()
    month = report["history"][-1]
    assert month["expenses_cents"] == 3000
    assert month["lupuspec_expenses_cents"] == 25000
    assert month["consolidated_expenses_cents"] == 28000
    assert report["lupuspec"]["capabilities"]["studio"]["expenses_cents"] == 25000
    assert report["lupuspec"]["totals"]["receipts_cents"] == 0
