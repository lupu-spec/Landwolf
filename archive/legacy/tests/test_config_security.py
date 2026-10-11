import pytest
from pydantic import ValidationError

from app.core.config import Settings


BASE_PROD = {
    "app_env": "production",
    "secret_key": "x" * 48,
    "database_url": "postgresql+psycopg://user:password@db.example.com:5432/app",
    "cors_origins": "https://app.example.com",
    "cookie_secure": True,
    "cookie_httponly": True,
    "cookie_samesite": "strict",
    "stripe_secret_key": "sk_live_example",
    "stripe_monthly_price_id": "price_live_monthly_example",
    "stripe_annual_price_id": "price_live_annual_example",
    "stripe_webhook_secret": "whsec_example",
    "stripe_success_url": "https://app.example.com/?checkout=success",
    "stripe_cancel_url": "https://app.example.com/?checkout=cancel",
}


def make_settings(**overrides):
    values = dict(BASE_PROD)
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_valid_production_configuration_loads():
    settings = make_settings()
    assert settings.app_env == "production"
    assert settings.cookie_secure is True
    assert settings.cors_origin_list == ["https://app.example.com"]


def test_production_rejects_placeholder_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make_settings(secret_key="change-me")


def test_production_rejects_short_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make_settings(secret_key="too-short")


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        make_settings(cors_origins="*")


def test_production_rejects_http_cors():
    with pytest.raises(ValidationError, match="HTTPS"):
        make_settings(cors_origins="http://app.example.com")


def test_production_rejects_insecure_cookie():
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        make_settings(cookie_secure=False)


def test_production_requires_httponly_cookie():
    with pytest.raises(ValidationError, match="COOKIE_HTTPONLY"):
        make_settings(cookie_httponly=False)


def test_production_requires_stripe_webhook_secret():
    with pytest.raises(ValidationError, match="STRIPE_WEBHOOK_SECRET"):
        make_settings(stripe_webhook_secret="")


def test_production_requires_https_checkout_urls():
    with pytest.raises(ValidationError, match="STRIPE_SUCCESS_URL"):
        make_settings(stripe_success_url="http://app.example.com/success")


def test_secret_values_are_redacted_in_repr():
    settings = make_settings()
    rendered = repr(settings)
    assert "sk_live_example" not in rendered
    assert "whsec_example" not in rendered
    assert "password@db.example.com" not in rendered
