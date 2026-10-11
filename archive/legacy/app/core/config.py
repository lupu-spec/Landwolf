from functools import cached_property
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: SecretStr = SecretStr("change-me")
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://property:property@db:5432/property_intelligence"
    )
    cors_origins: str = "http://localhost:8000"
    jwt_expire_minutes: int = Field(default=60, ge=5, le=1440)

    auth_cookie_name: str = "upi_session"
    cookie_secure: bool = False
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None
    cookie_path: str = "/"

    stripe_secret_key: SecretStr = SecretStr("")
    stripe_monthly_price_id: str = ""
    stripe_annual_price_id: str = ""
    stripe_webhook_secret: SecretStr = SecretStr("")
    stripe_success_url: str = "http://localhost:8000/?checkout=success"
    stripe_cancel_url: str = "http://localhost:8000/?checkout=cancel"
    webhook_failure_injection_secret: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("app_env")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        value = value.strip().lower()
        allowed = {"development", "test", "staging", "production"}
        if value not in allowed:
            raise ValueError(f"APP_ENV must be one of {sorted(allowed)}")
        return value

    @field_validator("cookie_samesite")
    @classmethod
    def validate_samesite(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        return value

    @model_validator(mode="after")
    def validate_runtime_configuration(self):
        env = self.app_env
        secret = self.secret_key.get_secret_value()
        database = self.database_url.get_secret_value()
        stripe_secret = self.stripe_secret_key.get_secret_value()
        stripe_webhook = self.stripe_webhook_secret.get_secret_value()
        origins = self.cors_origin_list

        if env in {"staging", "production"}:
            errors: list[str] = []

            if not secret or secret == "change-me" or len(secret) < 32:
                errors.append("SECRET_KEY must be a unique random value of at least 32 characters")
            if not database:
                errors.append("DATABASE_URL is required")
            if not origins:
                errors.append("CORS_ORIGINS must contain at least one explicit HTTPS origin")
            if "*" in origins:
                errors.append("CORS_ORIGINS cannot contain '*' when credentials are enabled")
            if any(urlparse(origin).scheme != "https" for origin in origins):
                errors.append("All staging/production CORS origins must use HTTPS")
            if not self.cookie_secure:
                errors.append("COOKIE_SECURE must be true in staging/production")
            if not self.cookie_httponly:
                errors.append("COOKIE_HTTPONLY must remain true in staging/production")
            if self.cookie_samesite == "none" and not self.cookie_secure:
                errors.append("SameSite=None requires COOKIE_SECURE=true")

            if not stripe_secret:
                errors.append("STRIPE_SECRET_KEY is required in staging/production")
            if not self.stripe_monthly_price_id:
                errors.append("STRIPE_MONTHLY_PRICE_ID is required in staging/production")
            if not self.stripe_annual_price_id:
                errors.append("STRIPE_ANNUAL_PRICE_ID is required in staging/production")
            if not stripe_webhook:
                errors.append("STRIPE_WEBHOOK_SECRET is required in staging/production")
            for field_name, url in {
                "STRIPE_SUCCESS_URL": self.stripe_success_url,
                "STRIPE_CANCEL_URL": self.stripe_cancel_url,
            }.items():
                if urlparse(url).scheme != "https":
                    errors.append(f"{field_name} must use HTTPS in staging/production")

            if errors:
                raise ValueError("Invalid deployment configuration:\n- " + "\n- ".join(errors))

        return self

    @cached_property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production_like(self) -> bool:
        return self.app_env in {"staging", "production"}

    @property
    def database_dsn(self) -> str:
        return self.database_url.get_secret_value()

    @property
    def jwt_secret(self) -> str:
        return self.secret_key.get_secret_value()

    @property
    def stripe_api_secret(self) -> str:
        return self.stripe_secret_key.get_secret_value()

    @property
    def stripe_webhook_signing_secret(self) -> str:
        return self.stripe_webhook_secret.get_secret_value()


settings = Settings()
