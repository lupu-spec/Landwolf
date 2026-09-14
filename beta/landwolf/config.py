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
    additional_origins: tuple[str, ...] = Field(default=(), max_length=4)
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
        raise ValueError("Payments must remain disabled for free access")

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
        if self.environment == "production" and not self.database_url.startswith(
            "postgresql+psycopg://"
        ):
            raise ValueError("Production requires a separate PostgreSQL database")
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
        if self.environment == "production":
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
