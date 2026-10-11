from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas import CheckoutRequest, CheckoutResponse
from app.services.auth import current_user
from app.services.billing import checkout_for_user, process_webhook

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(body: CheckoutRequest, user=Depends(current_user), db: Session = Depends(get_db)):
    return CheckoutResponse(checkout_url=checkout_for_user(db, user, body.plan))


@router.post("/webhook")
async def webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_failure_injection: str | None = Header(
        default=None, alias="X-Webhook-Failure-Injection"
    ),
):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    process_webhook(
        db, payload, signature,
        failure_injection=x_webhook_failure_injection,
    )
    return {"received": True}
