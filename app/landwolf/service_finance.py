"""Classify existing cash rows without duplicating them in consolidated totals."""

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from landwolf.finance_models import LupuSpecFinanceEntry
from landwolf.portal_models import CashDimension, WorkItem

# Stable codes, separate from display labels. LandWolf billing remains its own source.
STREAMS: dict[str, dict[str, str]] = {
    "studio.design": {"service": "studio", "kind": "receipt", "label": "DESIGN FEES"},
    "software.build": {"service": "software", "kind": "receipt", "label": "SOFTWARE BUILDS"},
    "software.support": {"service": "software", "kind": "receipt", "label": "SOFTWARE SUPPORT"},
    "fabrication.print": {"service": "fabrication", "kind": "receipt", "label": "3D PRINTING"},
    "fabrication.cnc": {"service": "fabrication", "kind": "receipt", "label": "CNC / CUSTOM PARTS"},
    "supply.parts": {"service": "supply", "kind": "receipt", "label": "PARTS SALES"},
    "supply.sourcing": {"service": "supply", "kind": "receipt", "label": "SOURCING FEES"},
    **{
        f"{service}.{cost}": {"service": service, "kind": "expense", "label": label}
        for service, costs in {
            "studio": [("labor", "DESIGN LABOR"), ("tools", "DESIGN TOOLS")],
            "software": [
                ("labor", "DEVELOPMENT LABOR"),
                ("compute", "COMPUTE / HOSTING"),
                ("tools", "SOFTWARE TOOLS"),
            ],
            "fabrication": [
                ("materials", "MATERIALS"),
                ("machine", "MACHINE TIME"),
                ("vendor", "OUTSIDE FABRICATION"),
            ],
            "supply": [
                ("purchased_parts", "PURCHASED PARTS"),
                ("shipping", "SHIPPING"),
                ("vendor", "SUPPLIER FEES"),
            ],
        }.items()
        for cost, label in costs
    },
}


def prepare_dimension(
    session: Session,
    *,
    capability: str,
    kind: str,
    amount: int,
    stream: str,
    work_item_id: uuid.UUID | None,
    source_reference: str,
    reversal_of: uuid.UUID | None,
) -> CashDimension | None:
    if not stream and not source_reference and work_item_id is None and reversal_of is None:
        return None  # Preserve v14 API callers; report these explicitly as unclassified.
    definition = STREAMS.get(stream)
    if (
        not definition
        or definition["service"] != capability
        or definition["kind"] != kind
        or not source_reference
    ):
        raise HTTPException(
            422, "Choose a matching service, entry type, stream and source reference"
        )
    if kind == "receipt" and work_item_id is None:
        raise HTTPException(422, "Link customer receipts to a service work item")
    if work_item_id:
        work = session.get(WorkItem, str(work_item_id))
        if work is None or work.service != capability:
            raise HTTPException(422, "Work item does not belong to this service")
    if session.scalar(
        select(CashDimension.entry_id).where(CashDimension.source_reference == source_reference)
    ):
        raise HTTPException(409, "Source reference already recorded")
    if (amount < 0) != (reversal_of is not None):
        raise HTTPException(422, "A negative amount must reverse an existing classified entry")
    if reversal_of:
        original = session.get(LupuSpecFinanceEntry, str(reversal_of))
        dimensions = session.get(CashDimension, str(reversal_of))
        if (
            original is None
            or dimensions is None
            or original.amount_cents <= 0
            or amount != -original.amount_cents
            or original.kind != kind
            or original.capability != capability
            or dimensions.stream != stream
            or dimensions.work_item_id != (str(work_item_id) if work_item_id else None)
        ):
            raise HTTPException(422, "Reverse the exact original amount, stream and work item")
        if session.scalar(
            select(CashDimension.entry_id).where(CashDimension.reversal_of == str(reversal_of))
        ):
            raise HTTPException(409, "Entry was already reversed")
    return CashDimension(
        stream=stream,
        work_item_id=str(work_item_id) if work_item_id else None,
        source_reference=source_reference,
        reversal_of=str(reversal_of) if reversal_of else None,
        currency="USD",
    )


def breakdown(session: Session, entries: list[LupuSpecFinanceEntry]) -> dict[str, Any]:
    """The same period/rows as the shared finance board; unknown allocation stays unknown."""
    ids = [row.id for row in entries]
    dimensions = {
        row.entry_id: row
        for row in session.scalars(
            select(CashDimension).where(CashDimension.entry_id.in_(ids))
        ).all()
    }
    works = {
        row.id: row
        for row in session.scalars(
            select(WorkItem).where(
                WorkItem.id.in_([d.work_item_id for d in dimensions.values() if d.work_item_id])
            )
        ).all()
    }
    groups: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in entries:
        dim = dimensions.get(row.id)
        work = works.get(dim.work_item_id) if dim and dim.work_item_id else None
        key = (
            row.capability,
            dim.stream if dim else "unclassified",
            work.customer_id if work else "",
            work.request_id if work else "",
        )
        target = groups.setdefault(
            key,
            {
                "service": key[0],
                "stream": key[1],
                "customer_id": key[2] or None,
                "project_id": key[3] or None,
                "currency": "USD",
                "receipts_cents": 0,
                "expenses_cents": 0,
                "net_cents": 0,
            },
        )
        target["receipts_cents" if row.kind == "receipt" else "expenses_cents"] += row.amount_cents
        target["net_cents"] = target["receipts_cents"] - target["expenses_cents"]
    return {
        "rows": list(groups.values()),
        "unclassified_entries": len(entries) - len(dimensions),
        "basis": "USD cash, same six-month period as the shared board. Not recognized revenue. "
        "Unassigned expenses stay overhead; missing classification is not inferred.",
    }
