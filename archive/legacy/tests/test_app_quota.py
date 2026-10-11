from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.quota import require_subscription

def test_active_subscription_allows_search():
    require_subscription(SimpleNamespace(subscription_status="active"))

def test_trialing_subscription_allows_search():
    require_subscription(SimpleNamespace(subscription_status="trialing"))

def test_unsubscribed_user_is_blocked_immediately():
    with pytest.raises(HTTPException) as exc:
        require_subscription(SimpleNamespace(subscription_status="none"))
    assert exc.value.status_code == 402
    assert exc.value.detail["code"] == "SUBSCRIPTION_REQUIRED"
