"""Owner-only cash reporting, explicit expense inputs and scenario forecasts.

Stripe access is GET-only. No card credentials, customer PII or invoice payloads
are persisted. A failed/incomplete refresh preserves the last complete snapshot.
"""

import csv
import hashlib
import io
import re
import time
import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Literal

from fastapi import HTTPException, Request
from pydantic import Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from landwolf import admin, auth, billing, crm_reporting
from landwolf.config import Settings
from landwolf.crm_core import Contact
from landwolf.db import Account
from landwolf.finance_models import FinanceAudit, FinanceExpense, FinanceSettings, FinanceSnapshot
from landwolf.schemas import Contract

Vendor = Literal["render", "spaceship", "openai", "other"]
VENDORS = {"render": "Render", "spaceship": "Spaceship", "openai": "OpenAI / ChatGPT"}
MAX_CENTS = 100_000_000


def money(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def month(value: date, offset: int = 0) -> str:
    index = value.year * 12 + value.month - 1 + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def valid_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Use a valid YYYY-MM-DD date") from error
    if not 2000 <= parsed.year <= 2100 or value != parsed.isoformat():
        raise ValueError("Use a date between 2000 and 2100")
    return value


class ExpenseInput(Contract):
    date: str = Field(max_length=10)
    vendor: Vendor
    amount_cents: int = Field(strict=True, ge=-MAX_CENTS, le=MAX_CENTS)
    allocation_percent: int = Field(strict=True, ge=0, le=100)
    # Optional disambiguator for genuine equal same-day charges; never a card number.
    reference: str = Field(default="", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,39}$|^$")

    @field_validator("date")
    @classmethod
    def check_date(cls, value: str) -> str:
        value = valid_date(value)
        if value > datetime.now(UTC).date().isoformat():
            raise ValueError("Actual expenses cannot have a future date; use forecast budgets")
        return value


class Budget(Contract):
    amount_cents: int | None = Field(default=None, strict=True, ge=0, le=MAX_CENTS)
    interval: Literal["month", "year"] = "month"
    renewal_date: str | None = Field(default=None, max_length=10)
    allocation_percent: int = Field(default=100, strict=True, ge=0, le=100)

    @field_validator("renewal_date")
    @classmethod
    def check_date(cls, value: str | None) -> str | None:
        return valid_date(value) if value is not None else None


class PlanInput(Contract):
    revision: int = Field(default=0, strict=True, ge=0)
    render: Budget = Field(default_factory=Budget)
    spaceship: Budget = Field(default_factory=lambda: Budget(interval="year"))
    openai: Budget = Field(default_factory=Budget)
    other: Budget = Field(default_factory=Budget)
    new_users_monthly: int = Field(default=0, strict=True, ge=0, le=100000)
    conversion_percent: int = Field(default=10, strict=True, ge=0, le=100)
    churn_percent: int = Field(default=5, strict=True, ge=0, le=100)
    monthly_price_cents: int = Field(default=2900, strict=True, ge=1, le=MAX_CENTS)
    processing_percent: int = Field(default=3, strict=True, ge=0, le=100)
    processing_fixed_cents: int = Field(default=30, strict=True, ge=0, le=10000)


class ImportInput(Contract):
    csv_text: str = Field(min_length=1, max_length=100000)
    allocation_percent: int = Field(strict=True, ge=0, le=100)
    confirm: bool = Field(default=False, strict=True)


def fingerprint(body: ExpenseInput) -> str:
    # Allocation is not identity: reimporting with a new allocation cannot double count.
    identity = f"{body.date}|{body.vendor}|{body.amount_cents}|{body.reference}"
    return hashlib.sha256(identity.encode()).hexdigest()


def expense_view(row: FinanceExpense) -> dict[str, Any]:
    return {
        "id": row.id,
        "date": row.date,
        "vendor": row.vendor,
        "amount_cents": row.amount_cents,
        "allocation_percent": row.allocation_percent,
        "business_cents": money(Decimal(row.amount_cents) * row.allocation_percent / 100),
        "source": row.source,
    }


def audit(session: Session, owner: Account, action: str, resource: str) -> None:
    session.add(
        FinanceAudit(
            id=str(uuid.uuid4()),
            owner_account_id=owner.id,
            action=action,
            resource_id=resource,
            created_at=int(time.time()),
        )
    )


def write_owner(request: Request, session: Session, settings: Settings) -> Account:
    owner = admin.require_owner(request, session, settings, write=True)
    session.execute(select(Account.id).where(Account.id == owner.id).with_for_update())
    auth.limit(session, f"finance-write:{owner.id}", 30, 60)
    return owner


def add_expense(
    request: Request, session: Session, settings: Settings, body: ExpenseInput
) -> dict[str, Any]:
    owner = write_owner(request, session, settings)
    if session.scalar(
        select(FinanceExpense.id).where(FinanceExpense.fingerprint == fingerprint(body))
    ):
        raise HTTPException(
            409, "Possible duplicate expense; use a reference for a distinct charge"
        )
    row = FinanceExpense(
        id=str(uuid.uuid4()),
        fingerprint=fingerprint(body),
        date=body.date,
        vendor=body.vendor,
        amount_cents=body.amount_cents,
        allocation_percent=body.allocation_percent,
        source="owner_entry",
        created_at=int(time.time()),
    )
    session.add(row)
    audit(session, owner, "finance_expense_added", row.id)
    session.commit()
    return expense_view(row)


def import_rows(body: ImportInput) -> tuple[list[ExpenseInput], int]:
    try:
        reader = csv.DictReader(io.StringIO(body.csv_text.lstrip("\ufeff")), strict=True)
        headers = reader.fieldnames or []
        if len(headers) > 40 or not {"Date", "Description", "Amount"}.issubset(headers):
            raise ValueError("CSV needs Date, Description and Amount columns")
        rows: list[ExpenseInput] = []
        skipped = 0
        for index, record in enumerate(reader):
            if index >= 500:
                raise ValueError("Import at most 500 rows per file")
            description = record.get("Description") or ""
            # Only recognized business vendors are selected. Never retain descriptions,
            # account columns, card numbers or unrelated personal transactions.
            vendor: Vendor
            if re.search(r"\brender(?:\.com)?\b", description, re.I):
                vendor = "render"
            elif re.search(r"\bspaceship(?:\.com)?\b", description, re.I):
                vendor = "spaceship"
            elif re.search(r"\b(?:openai|chatgpt)\b", description, re.I):
                vendor = "openai"
            else:
                skipped += 1
                continue
            raw_date = (record.get("Date") or "").strip()
            if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", raw_date):
                raw_date = datetime.strptime(raw_date, "%m/%d/%Y").date().isoformat()
            raw_amount = (record.get("Amount") or "").strip().replace(",", "").replace("$", "")
            if raw_amount.startswith("(") and raw_amount.endswith(")"):
                raw_amount = "-" + raw_amount[1:-1]
            if not re.fullmatch(r"-?\d{1,9}(?:\.\d{1,2})?", raw_amount):
                raise ValueError("Recognized vendor row has an invalid USD amount")
            rows.append(
                ExpenseInput(
                    date=raw_date,
                    vendor=vendor,
                    amount_cents=money(Decimal(raw_amount) * 100),
                    allocation_percent=body.allocation_percent,
                )
            )
        return rows, skipped
    except (ValueError, csv.Error, InvalidOperation) as error:
        raise HTTPException(
            422,
            "Invalid CSV: use Date, Description, Amount; USD debits positive, "
            "credits negative; at most 500 rows",
        ) from error


def import_expenses(
    request: Request, session: Session, settings: Settings, body: ImportInput
) -> dict[str, Any]:
    owner = write_owner(request, session, settings)
    rows, skipped = import_rows(body)
    selected: list[ExpenseInput] = []
    seen: set[str] = set()
    duplicates = 0
    for row in rows:
        key = fingerprint(row)
        if key in seen or session.scalar(
            select(FinanceExpense.id).where(FinanceExpense.fingerprint == key)
        ):
            duplicates += 1
            continue
        seen.add(key)
        selected.append(row)
    if body.confirm:
        for row in selected:
            session.add(
                FinanceExpense(
                    id=str(uuid.uuid4()),
                    fingerprint=fingerprint(row),
                    date=row.date,
                    vendor=row.vendor,
                    amount_cents=row.amount_cents,
                    allocation_percent=row.allocation_percent,
                    source="amex_csv",
                    created_at=int(time.time()),
                )
            )
        audit(session, owner, "finance_expenses_imported", str(len(selected)))
        session.commit()
    return {
        "confirmed": body.confirm,
        "selected": len(selected),
        "duplicates": duplicates,
        "skipped": skipped,
        "rows": [row.model_dump(exclude={"reference"}) for row in selected],
        "note": "Review vendor matches and business allocation. Equal same-day charges are "
        "flagged as duplicates; add genuine distinct charges manually with a reference. "
        "No unrelated rows or card details are retained.",
    }


def save_plan(
    request: Request, session: Session, settings: Settings, body: PlanInput
) -> dict[str, Any]:
    owner = write_owner(request, session, settings)
    row = session.get(FinanceSettings, "plan")
    revision = row.payload.get("revision", 0) if row else 0
    if body.revision != revision:
        raise HTTPException(409, "Forecast settings changed in another tab; reload before saving")
    payload = body.model_dump()
    payload["revision"] = revision + 1
    for vendor in (*VENDORS, "other"):
        budget = getattr(body, vendor)
        if (
            budget.interval == "year"
            and budget.amount_cents is not None
            and not budget.renewal_date
        ):
            raise HTTPException(422, "Annual budgets require an explicit renewal date")
    if row is None:
        row = FinanceSettings(id="plan", payload=payload, updated_at=int(time.time()))
        session.add(row)
    else:
        row.payload, row.updated_at = payload, int(time.time())
    audit(session, owner, "finance_plan_updated", "plan")
    session.commit()
    return payload


def stripe_list(
    api: billing.StripeAPI, path: str, fields: dict[str, str], deadline: float
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    params = {**fields, "limit": "100"}
    seen: set[str] = set()
    for _ in range(10):
        if time.monotonic() > deadline:
            raise billing.unavailable()
        response = api.call("GET", path, params)
        if time.monotonic() > deadline:
            raise billing.unavailable()
        data = response.get("data")
        if (
            not isinstance(data, list)
            or len(data) > 100
            or not isinstance(response.get("has_more"), bool)
        ):
            raise billing.unavailable()
        for item in data:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("id"), str)
                or item["id"] in seen
            ):
                raise billing.unavailable()
            seen.add(item["id"])
            rows.append(item)
        if not response["has_more"]:
            return rows
        if not data:
            raise billing.unavailable()
        params["starting_after"] = data[-1]["id"]
    raise HTTPException(
        503, "Finance history exceeds the safe pagination limit; last snapshot retained"
    )


def integer(row: dict[str, Any], key: str, *, signed: bool = False) -> int:
    value = row.get(key)
    if type(value) is not int or abs(value) > 10**12 or (not signed and value < 0):
        raise billing.unavailable()
    return value


def object_field(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise billing.unavailable()
    return value


def stripe_snapshot(settings: Settings) -> dict[str, Any]:
    """All-time USD Stripe account cash; payouts are transfers, never revenue twice."""
    api = billing.StripeAPI(settings)
    account = api.call("GET", "/account")
    if account.get("id") != settings.stripe_account_id:
        raise billing.unavailable()
    deadline = time.monotonic() + 45
    invoices = stripe_list(api, "/invoices", {"status": "paid"}, deadline)
    balances = stripe_list(api, "/balance_transactions", {}, deadline)
    subscriptions = stripe_list(api, "/subscriptions", {"status": "all"}, deadline)
    history: dict[str, dict[str, int]] = {}
    excluded = 0

    def bucket(timestamp: int) -> dict[str, int]:
        try:
            key = datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m")
        except (ValueError, OverflowError, OSError) as error:
            raise billing.unavailable() from error
        return history.setdefault(
            key, {"receipts": 0, "refunds": 0, "fees": 0, "subscription_receipts": 0}
        )

    for row in balances:
        if row.get("currency") != "usd":
            excluded += 1
            continue
        values = bucket(integer(row, "created"))
        amount = integer(row, "amount", signed=True)
        fee = integer(row, "fee", signed=True)
        kind = row.get("type")
        # Payouts, reserves, transfers, adjustments and topups are not sales.
        if kind in {"charge", "payment"} and amount >= 0:
            values["receipts"] += amount
            values["fees"] += fee
        elif kind in {"refund", "payment_refund"} and amount <= 0:
            values["refunds"] -= amount
            values["fees"] += fee
        elif kind in {"stripe_fee", "stripe_fx_fee"}:
            values["fees"] -= amount
        elif kind not in {"payout", "payout_cancel", "payout_failure", "reserve_transaction"}:
            excluded += 1
    for row in invoices:
        if row.get("livemode") is not True:
            raise billing.unavailable()
        parent = object_field(row, "parent")
        subscription = row.get("subscription") or object_field(parent, "subscription_details").get(
            "subscription"
        )
        if not subscription or row.get("paid_out_of_band") or row.get("currency") != "usd":
            excluded += 1
            continue
        paid = object_field(row, "status_transitions").get("paid_at")
        if type(paid) is not int:
            raise billing.unavailable()
        bucket(paid)["subscription_receipts"] += integer(row, "amount_paid")
    mrr = Decimal(0)
    active = 0
    cancellations = 0
    for row in subscriptions:
        if row.get("livemode") is not True:
            raise billing.unavailable()
        if row.get("status") != "active":
            continue
        items = object_field(row, "items")
        if items.get("has_more") or not isinstance(items.get("data"), list):
            raise billing.unavailable()
        supported = False
        for item in items["data"]:
            if not isinstance(item, dict):
                raise billing.unavailable()
            price = object_field(item, "price")
            recurrence = object_field(price, "recurring")
            if price.get("currency") != "usd" or recurrence.get("interval") not in {
                "month",
                "year",
            }:
                excluded += 1
                continue
            count = integer(recurrence, "interval_count")
            if not count:
                raise billing.unavailable()
            months = count * (12 if recurrence["interval"] == "year" else 1)
            quantity = integer(item, "quantity")
            if not quantity:
                raise billing.unavailable()
            mrr += Decimal(integer(price, "unit_amount") * quantity) / months
            supported = True
        if supported:
            active += 1
            cancellations += int(row.get("cancel_at_period_end") is True)
    return {
        "history": history,
        "plan_run_rate_cents": money(mrr),
        "active_subscriptions": active,
        "scheduled_cancellations": cancellations,
        "excluded_records": excluded,
        "as_of": int(time.time()),
        "basis": "USD Stripe account cash receipts/refunds/fees by transaction creation month; "
        "subscription paid-invoice collections shown separately (paid date). Tax may be included "
        "in cash. Payouts are transfers, not sales. Plan run-rate normalizes active monthly/annual "
        "list prices before discounts/tax; not recognized revenue or a cash-billing schedule.",
    }


def refresh(request: Request, session: Session, settings: Settings) -> dict[str, Any]:
    owner = admin.require_owner(request, session, settings, write=True)
    session.execute(select(Account.id).where(Account.id == owner.id).with_for_update())
    auth.limit(session, f"finance-refresh:{owner.id}", 4, 60)
    payload = stripe_snapshot(settings)
    row = session.get(FinanceSnapshot, "stripe")
    if row is None:
        session.add(FinanceSnapshot(id="stripe", payload=payload, updated_at=payload["as_of"]))
    else:
        row.payload, row.updated_at = payload, payload["as_of"]
    audit(session, owner, "finance_stripe_snapshot_updated", "stripe")
    session.commit()
    return {"as_of": payload["as_of"], "ok": True}


def forecasts(
    plan: PlanInput, snapshot: dict[str, Any] | None, today: date
) -> list[dict[str, Any]]:
    results = []
    for scenario, growth_factor, churn_factor in [
        ("conservative", Decimal("0.5"), Decimal("1.5")),
        ("base", Decimal(1), Decimal(1)),
        ("growth", Decimal("1.5"), Decimal("0.5")),
    ]:
        users = Decimal(snapshot["active_subscriptions"]) if snapshot else Decimal(0)
        run_rate = Decimal(snapshot["plan_run_rate_cents"]) if snapshot else Decimal(0)
        for offset in (1, 2, 3):
            label = month(today, offset)
            addition = (
                Decimal(plan.new_users_monthly) * plan.conversion_percent / 100 * growth_factor
            )
            retention = max(Decimal(0), 1 - Decimal(plan.churn_percent) / 100 * churn_factor)
            users = users * retention + addition
            run_rate = run_rate * retention + addition * plan.monthly_price_cents
            costs = 0
            missing = []
            for vendor in (*VENDORS, "other"):
                budget = getattr(plan, vendor)
                if budget.amount_cents is None:
                    if vendor != "other":
                        missing.append(vendor)
                    continue
                applies = budget.interval == "month"
                if budget.interval == "year" and budget.renewal_date:
                    renewal = date.fromisoformat(budget.renewal_date)
                    applies = (
                        label.endswith(f"-{renewal.month:02d}") and int(label[:4]) >= renewal.year
                    )
                if applies:
                    costs += money(Decimal(budget.amount_cents) * budget.allocation_percent / 100)
            fees = money(
                run_rate * plan.processing_percent / 100 + users * plan.processing_fixed_cents
            )
            revenue = money(run_rate) if snapshot else None
            results.append(
                {
                    "scenario": scenario,
                    "month": label,
                    "expected_subscriptions": float(users.quantize(Decimal("0.01"))),
                    "revenue_cents": revenue,
                    "cost_cents": costs + fees,
                    "net_cents": revenue - costs - fees if revenue is not None else None,
                    "missing_costs": missing,
                }
            )
    return results


def report(session: Session, settings: Settings) -> dict[str, Any]:
    now = int(time.time())
    today = datetime.fromtimestamp(now, UTC).date()
    stored = session.get(FinanceSnapshot, "stripe")
    snapshot = stored.payload if stored else None
    configuration = session.get(FinanceSettings, "plan")
    plan = PlanInput.model_validate(configuration.payload) if configuration else PlanInput()
    stats = crm_reporting.report(session, settings)
    rows = crm_reporting.segments(settings, now)
    signups = (
        session.execute(
            select(Account.created_at)
            .join(Contact, Contact.external_id == Account.id)
            .join(rows, rows.c.contact_id == Contact.id)
            .where(rows.c.account_category == "user")
        )
        .scalars()
        .all()
    )
    start = month(today, -5)
    expenses = session.scalars(
        select(FinanceExpense)
        .where(FinanceExpense.date >= start)
        .order_by(FinanceExpense.date.desc(), FinanceExpense.id)
        .limit(501)
    ).all()
    if len(expenses) > 500:
        raise HTTPException(
            503, "Expense history exceeds the current report limit; narrow the accounting period"
        )
    history = []
    for offset in range(-5, 1):
        label = month(today, offset)
        actual = snapshot["history"].get(label, {}) if snapshot else {}
        cost = sum(
            expense_view(row)["business_cents"] for row in expenses if row.date.startswith(label)
        )
        receipts = actual.get("receipts", 0) if snapshot else None
        refunds, fees = actual.get("refunds", 0), actual.get("fees", 0)
        history.append(
            {
                "month": label,
                "receipts_cents": receipts,
                "subscription_receipts_cents": actual.get("subscription_receipts", 0)
                if snapshot
                else None,
                "refunds_cents": refunds if snapshot else None,
                "fees_cents": fees if snapshot else None,
                "expenses_cents": cost,
                "net_cents": receipts - refunds - fees - cost if receipts is not None else None,
                "new_users": sum(
                    datetime.fromtimestamp(value, UTC).strftime("%Y-%m") == label
                    for value in signups
                ),
                "partial_month": offset == 0,
            }
        )
    membership = stats["memberships"]
    recommendations = [
        {
            "title": "Make the first research task succeed",
            "basis": f"{stats['total_users']} real registered users; owners/smoke tests excluded.",
            "action": "Run a 14-day onboarding experiment: one property research task, one deal "
            "scenario and one saved Hunt. Ask consenting users where they get stuck.",
            "metric": "Measure first-task completion, 7-day return rate and paid conversions; "
            "targets are owner hypotheses, not causal predictions.",
        },
        {
            "title": "Learn from pilots before expanding acquisition",
            "basis": f"{membership['trial']} trial users; {membership['registered']} "
            "registered users without an active plan.",
            "action": "Review day-30/60/90 feedback and help users reach a useful result. Offer "
            "clear membership choices without changing pilot terms or inventing missed feedback.",
            "metric": "Track voluntary trial-to-paid conversions and cancellation reasons. "
            "This dashboard does not send marketing or trigger charges.",
        },
        {
            "title": "Test a focused investor channel",
            "basis": "LandWolf supports research, deal scenarios and saved Hunts; "
            "no attributable acquisition-event history is connected.",
            "action": "Test one consenting Texas property-investor cohort with a research "
            "walkthrough and a tagged referral link. Compare conversion before buying ads.",
            "metric": "Log leads, activated users, paid subscribers and spend per channel for "
            "14 days; then calculate CAC. No CAC or LTV estimate is claimed without data.",
        },
        {
            "title": "Complete costs before judging profitability",
            "basis": "Vendor costs must be verified with actual invoices and business allocations.",
            "action": "Reconcile business-only card transactions and actual invoices. Separate "
            "annual renewals from monthly bills; avoid counting Stripe fees twice.",
            "metric": "Monitor complete operating net, renewal cash needs and contribution per "
            "subscriber; forecasts are scenarios, not financial guarantees.",
        },
    ]
    if snapshot and snapshot["scheduled_cancellations"]:
        recommendations.insert(
            0,
            {
                "title": "Investigate scheduled cancellations",
                "basis": f"{snapshot['scheduled_cancellations']} active subscriptions "
                "scheduled to end.",
                "action": "Review voluntary feedback and reliability issues. Offer help through "
                "permitted channels; preserve cancellation rights.",
                "metric": "Track reasons and voluntary retention; never obstruct cancellation.",
            },
        )
    return {
        "as_of": now,
        "subscription_collections_all_time_cents": (
            sum(row.get("subscription_receipts", 0) for row in snapshot["history"].values())
            if snapshot
            else None
        ),
        "stripe": snapshot,
        "stripe_available": settings.payments_enabled,
        "stripe_stale": bool(stored and stored.updated_at < now - 86400),
        "history": history,
        "expenses": [expense_view(row) for row in expenses],
        "plan": plan.model_dump(),
        "forecast": forecasts(plan, snapshot, today),
        "users": stats,
        "recommendations": recommendations,
        "limits": "Management view, not audited accounts or tax advice. USD only. Recorded "
        "expenses may be incomplete. Revenue is cash receipts, not GAAP profit; plan run-rate "
        "is not cash. Three next-calendar-month scenarios assume normalized monthly receipts, "
        "not actual annual renewal timing. Churn/conversion/fees are editable hypotheses. "
        "No auto-conversion of complimentary pilots is assumed. ChatGPT plan fees and API spend "
        "must be entered separately if both apply; no bank connection is active.",
    }


def dashboard(request: Request, session: Session, settings: Settings) -> dict[str, Any]:
    admin.require_owner(request, session, settings, write=False)
    return report(session, settings)
