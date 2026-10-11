from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import Property, SearchEvent
from app.schemas import SearchRequest


def run_search(db: Session, user_id: str, request: SearchRequest):
    q = select(Property)

    if request.state:
        q = q.where(Property.state == request.state.upper())
    if request.city:
        q = q.where(Property.city.ilike(request.city))
    if request.county:
        q = q.where(Property.county.ilike(request.county))
    if request.min_acres is not None:
        q = q.where(Property.acreage >= request.min_acres)
    if request.max_price is not None:
        q = q.where(Property.estimated_value <= request.max_price)
    if request.distress_type:
        q = q.where(Property.distress_type == request.distress_type)
    if request.min_data_quality is not None:
        q = q.where(Property.data_quality >= request.min_data_quality)

    q = q.order_by(Property.data_quality.desc(), Property.estimated_value.asc()).limit(request.limit)
    rows = list(db.scalars(q))

    event = SearchEvent(
        user_id=user_id,
        query_json=request.model_dump(),
        result_count=len(rows),
    )
    db.add(event)
    return rows
