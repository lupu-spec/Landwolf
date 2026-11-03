"""Customer boundaries and service dimensions. Existing v14 records stay intact."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from landwolf.db import Base


class Customer(Base):
    __tablename__ = "lw2_customers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[int] = mapped_column(Integer)


class ServiceAccount(Base):
    __tablename__ = "lw2_customer_services"
    __table_args__ = (
        UniqueConstraint("customer_id", "service"),
        UniqueConstraint("id", "customer_id", "service"),
        CheckConstraint("service IN ('studio','software','fabrication','supply','landwolf')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("lw2_customers.id"), index=True)
    service: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[int] = mapped_column(Integer)


class CustomerProject(Base):
    __tablename__ = "lw2_customer_projects"
    __table_args__ = (UniqueConstraint("request_id", "customer_id"),)
    request_id: Mapped[str] = mapped_column(
        ForeignKey("lw2_lupuspec_requests.id"), primary_key=True
    )
    customer_id: Mapped[str] = mapped_column(ForeignKey("lw2_customers.id"), index=True)
    linked_by: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"))
    link_basis: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[int] = mapped_column(Integer)


class WorkItem(Base):
    __tablename__ = "lw2_service_work"
    __table_args__ = (
        ForeignKeyConstraint(
            ["request_id", "customer_id"],
            ["lw2_customer_projects.request_id", "lw2_customer_projects.customer_id"],
        ),
        ForeignKeyConstraint(
            ["service_account_id", "customer_id", "service"],
            [
                "lw2_customer_services.id",
                "lw2_customer_services.customer_id",
                "lw2_customer_services.service",
            ],
        ),
        UniqueConstraint("request_id", "service"),
        CheckConstraint(
            "status IN ('received','reviewing','quoted','approved',"
            "'in_progress','delivered','closed')"
        ),
        CheckConstraint("revision >= 1"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    service_account_id: Mapped[str] = mapped_column(String(36))
    service: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(24), default="received")
    revision: Mapped[int] = mapped_column(Integer, default=1)


class ProjectMessage(Base):
    __tablename__ = "lw2_customer_messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["request_id", "customer_id"],
            ["lw2_customer_projects.request_id", "lw2_customer_projects.customer_id"],
        ),
        UniqueConstraint("actor_id", "submission_id"),
        CheckConstraint("author IN ('customer','team')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"))
    submission_id: Mapped[str] = mapped_column(String(36))
    author: Mapped[str] = mapped_column(String(12))
    text: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[int] = mapped_column(Integer)


class PortalAudit(Base):
    __tablename__ = "lw2_portal_audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("lw2_accounts.id"))
    action: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[int] = mapped_column(Integer)


class CashDimension(Base):
    """One classification of one cash row, never a second financial transaction."""

    __tablename__ = "lw2_cash_dimensions"
    __table_args__ = (CheckConstraint("currency = 'USD'"),)
    entry_id: Mapped[str] = mapped_column(
        ForeignKey("lw2_lupuspec_finance_entries.id"), primary_key=True
    )
    work_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("lw2_service_work.id"), nullable=True, index=True
    )
    stream: Mapped[str] = mapped_column(String(40), index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    source_reference: Mapped[str] = mapped_column(String(80), unique=True)
    reversal_of: Mapped[str | None] = mapped_column(
        ForeignKey("lw2_lupuspec_finance_entries.id"), nullable=True, unique=True
    )
