"""Private finance storage; never copy bank credentials or full card statements."""

from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from landwolf.db import Base


class FinanceExpense(Base):
    __tablename__ = "lw2_finance_expenses"
    __table_args__ = (
        CheckConstraint("allocation_percent >= 0 AND allocation_percent <= 100"),
        CheckConstraint("amount_cents >= -100000000 AND amount_cents <= 100000000"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    vendor: Mapped[str] = mapped_column(String(32))
    amount_cents: Mapped[int] = mapped_column(Integer)
    allocation_percent: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[int] = mapped_column(Integer)


class FinanceSettings(Base):
    __tablename__ = "lw2_finance_settings"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[int] = mapped_column(Integer)


class FinanceSnapshot(Base):
    __tablename__ = "lw2_finance_snapshots"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[int] = mapped_column(Integer)


class FinanceAudit(Base):
    __tablename__ = "lw2_finance_audit"
    __table_args__ = (
        CheckConstraint(
            "action IN ('finance_expense_added','finance_expenses_imported',"
            "'finance_plan_updated','finance_stripe_snapshot_updated')"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[int] = mapped_column(Integer)


class LupuSpecFinanceEntry(Base):
    """Owner-entered, append-only cash ledger separate from LandWolf Stripe billing."""

    __tablename__ = "lw2_lupuspec_finance_entries"
    __table_args__ = (
        CheckConstraint("amount_cents != 0 AND amount_cents >= -100000000 AND amount_cents <= 100000000"),
        CheckConstraint("kind IN ('receipt','expense')"),
        CheckConstraint("capability IN ('studio','software','fabrication','supply')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    capability: Mapped[str] = mapped_column(String(20), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    amount_cents: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str] = mapped_column(String(40), default="")
    created_by: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"))
    created_at: Mapped[int] = mapped_column(Integer)
