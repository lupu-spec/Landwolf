"""Explicit environment boundaries. Opaque sessions need no JWT signing key."""

import os
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_public_origin() -> str:
    # Render assigns this service's URL before its container starts. Never derive
    # the security boundary from a request Host or forwarding header.
    if os.environ.get("RENDER") != "true":
        return "http://127.0.0.1:8000"
    origin = os.environ.get("RENDER_EXTERNAL_URL", "")
    url = urlsplit(origin)
    if (
        url.scheme != "https"
        or not url.hostname
        or not url.hostname.endswith(".onrender.com")
        or url.hostname == ".onrender.com"
        or url.port is not None
    ):
        raise ValueError("Render must supply its assigned public HTTPS origin")
    return origin


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LANDWOLF_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = Field(default="sqlite:///./landwolf-beta.db", repr=False)
    public_origin: str = Field(default_factory=default_public_origin)
    additional_origins: tuple[str, ...] = Field(default=(), max_length=4)
    auto_sync: bool = True
    owner_account_id: str | None = Field(default=None, pattern=r"^[0-9a-fA-F-]{36}$")
    payments_enabled: bool = False
    stripe_secret_key: SecretStr | None = Field(default=None, repr=False)
    stripe_webhook_secret: SecretStr | None = Field(default=None, repr=False)
    stripe_account_id: str | None = Field(default=None, pattern=r"^acct_[A-Za-z0-9]+$")
    stripe_monthly_price_id: str | None = Field(default=None, pattern=r"^price_[A-Za-z0-9]+$")
    stripe_annual_price_id: str | None = Field(default=None, pattern=r"^price_[A-Za-z0-9]+$")
    stripe_portal_configuration_id: str | None = Field(default=None, pattern=r"^bpc_[A-Za-z0-9]+$")
    pilot_invite_emails: tuple[EmailStr, ...] = Field(default=(), max_length=500, repr=False)
    session_hours: int = Field(default=8, ge=1, le=24)
    idle_minutes: int = Field(default=30, ge=5, le=120)
    auth_limit: int = Field(default=12, ge=1, le=100)
    mail_provider: Literal["disabled", "resend"] = "disabled"
    mail_from: EmailStr | None = None
    mail_api_key: SecretStr | None = Field(default=None, repr=False)

    @field_validator("payments_enabled", mode="before")
    @classmethod
    def explicit_payment_flag(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.casefold() in {"true", "false"}:
            return value.casefold() == "true"
        raise ValueError("Payments flag must be true or false")

    @field_validator("pilot_invite_emails")
    @classmethod
    def normalize_pilot_emails(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        # Private deployment configuration, never a public client-side allowlist.
        return tuple(dict.fromkeys(email.casefold() for email in value))

    @model_validator(mode="after")
    def validate_deployment(self) -> Self:
        # Render supplies the standard PostgreSQL scheme; select our pinned driver.
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
        self.public_origin = self.validate_origin(self.public_origin)
        self.additional_origins = tuple(self.validate_origin(o) for o in self.additional_origins)
        if len(set(self.trusted_origins)) != len(self.trusted_origins):
            raise ValueError("Configured origins must be unique")
        if len({urlsplit(o).scheme for o in self.trusted_origins}) != 1:
            raise ValueError("Configured origins must use the same scheme")
        if self.mail_provider == "resend" and (
            not self.mail_from or not self.mail_api_key or not self.mail_api_key.get_secret_value()
        ):
            raise ValueError("Resend requires a verified sender and an API key")
        if self.environment in {"staging", "production"} and not self.database_url.startswith(
            "postgresql+psycopg://"
        ):
            raise ValueError("Production requires a separate PostgreSQL database")
        if self.payments_enabled:
            key = self.stripe_secret_key.get_secret_value() if self.stripe_secret_key else ""
            webhook = (
                self.stripe_webhook_secret.get_secret_value() if self.stripe_webhook_secret else ""
            )
            if not key.startswith(("sk_live_", "rk_live_")) or len(key) < 24:
                raise ValueError("Payments require a live Stripe server key; sandbox is forbidden")
            if not webhook.startswith("whsec_") or len(webhook) < 24:
                raise ValueError("Payments require the live webhook signing secret")
            if not all(
                (
                    self.stripe_account_id,
                    self.stripe_monthly_price_id,
                    self.stripe_annual_price_id,
                    self.stripe_portal_configuration_id,
                    self.owner_account_id,
                )
            ):
                raise ValueError(
                    "Payments require account, prices, portal configuration and owner ID"
                )
            if self.stripe_monthly_price_id == self.stripe_annual_price_id:
                raise ValueError("Monthly and annual prices must be distinct")
        return self

    def validate_origin(self, origin: str) -> str:
        url = urlsplit(origin)
        if (
            not url.hostname
            or url.username is not None
            or url.password is not None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in origin)
            or "*" in origin
            or "\\" in origin
        ):
            raise ValueError("Configured origins must be plain HTTP(S) origins")
        if self.environment in {"staging", "production"}:
            if (
                url.scheme != "https"
                or url.hostname in {"localhost", "127.0.0.1", "::1", "testserver"}
                or url.port is not None
            ):
                raise ValueError("Production requires a public HTTPS origin")
        elif url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "testserver"}
        ):
            raise ValueError("HTTP is allowed only for local development")
        return f"{url.scheme}://{url.netloc.lower()}"

    @property
    def trusted_origins(self) -> tuple[str, ...]:
        return (self.public_origin, *self.additional_origins)

    @property
    def secure_cookies(self) -> bool:
        return self.public_origin.startswith("https://")
