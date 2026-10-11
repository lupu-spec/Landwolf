from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import SearchRequest, SearchResponse, SearchPreviewResponse, PropertyOut
from app.services.auth import current_user
from app.services.quota import require_subscription
from app.services.search import run_search

router = APIRouter(prefix="/api/search", tags=["search"])

def _band(values, formatter):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    low, high = vals[0], vals[-1]
    return formatter(low) if low == high else f"{formatter(low)}–{formatter(high)}"

@router.post("/preview", response_model=SearchPreviewResponse)
def preview(request: SearchRequest, user=Depends(current_user), db: Session = Depends(get_db)):
    # Login required; subscription intentionally not required.
    # No address, parcel ID, owner information, coordinates, or individual valuation is returned.
    rows = run_search(db, user.id, request)
    count = len(rows)
    signal = (
        "No strong matches found" if count == 0 else
        "A few potential matches" if count <= 2 else
        "Several potential opportunities" if count <= 5 else
        "Strong opportunity set"
    )
    categories = Counter((row.distress_type or "market").replace("_", " ").title() for row in rows)
    return SearchPreviewResponse(
        match_count=count,
        opportunity_signal=signal,
        category_summary=[f"{name}: {qty}" for name, qty in categories.most_common(3)],
        acreage_band=_band([row.acreage for row in rows], lambda v: f"{float(v):,.1f} acres"),
        value_band=_band([row.estimated_value for row in rows], lambda v: f"${float(v):,.0f}"),
        message=(
            "Your search shows signals worth investigating. Subscribe to move from market-level signals "
            "to property-level intelligence, including due-diligence data, risk context, valuation support, "
            "and acquisition analysis."
            if count else
            "This search does not currently show a strong opportunity signal. Adjust the criteria to explore a broader market or category."
        ),
        requires_subscription=True,
    )

@router.post("", response_model=SearchResponse)
def search(request: SearchRequest, user=Depends(current_user), db: Session = Depends(get_db)):
    require_subscription(user)
    rows = run_search(db, user.id, request)
    db.commit()
    return SearchResponse(
        results=[PropertyOut.model_validate(row, from_attributes=True) for row in rows],
        result_count=len(rows),
        subscription_status=user.subscription_status,
    )
