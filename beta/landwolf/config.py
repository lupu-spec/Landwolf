"""Explicit environment boundaries. Opaque sessions need no JWT signing key."""

import os
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
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

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = Field(default="sqlite:///./landwolf-beta.db", repr=False)
    public_origin: str = Field(default_factory=default_public_origin)
    auto_sync: bool = True
    payments_enabled: Literal[False] = False
    session_hours: int = Field(default=8, ge=1, le=24)
    idle_minutes: int = Field(default=30, ge=5, le=120)
    auth_limit: int = Field(default=12, ge=1, le=100)

    @field_validator("payments_enabled", mode="before")
    @classmethod
    def keep_payments_disabled(cls, value: object) -> Literal[False]:
        # Environment variables are strings; accept only an explicit false value.
        if value is False or (isinstance(value, str) and value.casefold() == "false"):
            return False
        raise ValueError("Payments must remain disabled for the free beta")

    @model_validator(mode="after")
    def validate_deployment(self) -> Self:
        # Render supplies the standard PostgreSQL scheme; select our pinned driver.
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
        url = urlsplit(self.public_origin)
        if (
            not url.hostname
            or url.username
            or url.password
            or url.path not in ("", "/")
            or url.query
            or url.fragment
        ):
            raise ValueError("PUBLIC_ORIGIN must be a plain origin")
        if self.environment == "production":
            if url.scheme != "https" or url.hostname in {"localhost", "127.0.0.1"}:
                raise ValueError("Production requires a public HTTPS origin")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires a separate PostgreSQL beta database")
        elif url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "testserver"}
        ):
            raise ValueError("HTTP is allowed only for local development")
        self.public_origin = self.public_origin.rstrip("/")
        return self

    @property
    def secure_cookies(self) -> bool:
        return self.public_origin.startswith("https://")
