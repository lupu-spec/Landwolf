from fastapi import HTTPException
from typing import Any

PAID_STATUSES = {"active", "trialing"}

def subscription_active(user: Any) -> bool:
    return user.subscription_status in PAID_STATUSES

def require_subscription(user: Any) -> None:
    if subscription_active(user):
        return
    raise HTTPException(
        status_code=402,
        detail={
            "code": "SUBSCRIPTION_REQUIRED",
            "message": "An active subscription is required to search properties.",
        },
    )
