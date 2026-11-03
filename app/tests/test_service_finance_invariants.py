"""Generated signed cash rows conserve every cent in service/stream reports."""

from hypothesis import given, settings
from hypothesis import strategies as st

from landwolf.db import database, initialize
from landwolf.finance_models import LupuSpecFinanceEntry
from landwolf.service_finance import breakdown


@given(
    st.lists(
        st.tuples(
            st.sampled_from(["studio", "software", "fabrication", "supply"]),
            st.sampled_from(["receipt", "expense"]),
            st.integers(-100000000, 100000000).filter(lambda x: x != 0),
        ),
        max_size=50,
    )
)
@settings(max_examples=30, deadline=None)
def test_breakdown_conserves_receipts_costs_and_signed_reversals(values):
    engine, factory = database("sqlite://")
    initialize(engine)
    entries = [
        LupuSpecFinanceEntry(id=str(i), capability=service, kind=kind, amount_cents=amount)
        for i, (service, kind, amount) in enumerate(values)
    ]
    with factory() as session:
        groups = breakdown(session, entries)["rows"]
    assert sum(row["receipts_cents"] for row in groups) == sum(
        amount for _, kind, amount in values if kind == "receipt"
    )
    assert sum(row["expenses_cents"] for row in groups) == sum(
        amount for _, kind, amount in values if kind == "expense"
    )
    assert sum(row["net_cents"] for row in groups) == sum(
        amount if kind == "receipt" else -amount for _, kind, amount in values
    )
    engine.dispose()
