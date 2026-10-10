"""Deployment-only billing statuses: fixed labels, never secret fragments or hashes."""

from collections.abc import Mapping
from typing import Literal

MAX_INSPECTED_LENGTH = 4096
BILLING_NAMES = (
    "LANDWOLF_STRIPE_SECRET_KEY",
    "LANDWOLF_STRIPE_WEBHOOK_SECRET",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "LANDWOLF_OWNER_ACCOUNT_ID",
    "LANDWOLF_STRIPE_ACCOUNT_ID",
    "LANDWOLF_STRIPE_MONTHLY_PRICE_ID",
    "LANDWOLF_STRIPE_ANNUAL_PRICE_ID",
    "LANDWOLF_STRIPE_PORTAL_CONFIGURATION_ID",
    "LANDWOLF_PILOT_INVITE_EMAILS",
)


def secret_status(value: str | None, kind: Literal["server", "webhook"]) -> str:
    """Describe a value's format without outputting any part of that value."""
    if value is None:
        return "missing"
    if not value:
        return "empty"
    if len(value) > MAX_INSPECTED_LENGTH:
        return "oversized"
    if value != value.strip():
        return "surrounding_whitespace"
    if value[0] in "\"'" or value[-1] in "\"'":
        return "surrounding_quotes"
    if any(char.isspace() for char in value):
        return "embedded_whitespace"
    if any(marker in value for marker in ("***", "...", "\u2026")):
        return "masked_or_truncated_display"
    if value.startswith(("pk_live_", "pk_test_")):
        return "publishable_key_not_server_secret"
    if value.startswith(("sk_test_", "rk_test_")):
        return "sandbox_server_key"
    if kind == "webhook":
        if not value.startswith("whsec_"):
            return "wrong_webhook_secret_prefix"
        return "format_ok_not_authenticated" if len(value) >= 24 else "too_short"
    if not value.startswith(("sk_live_", "rk_live_")):
        return "wrong_live_server_key_prefix"
    return "format_ok_not_authenticated" if len(value) >= 24 else "too_short"


def environment_status(environment: Mapping[str, str]) -> dict[str, str]:
    """Inspect only known names; raw process env is not proof of effective settings.

    Case-insensitive lookup matches Settings. Ambiguous differently cased entries
    are reported, not resolved. Non-secret configuration is presence-only, including
    the private invitation list. Legacy names are diagnostic, never key fallbacks.
    """
    report: dict[str, str] = {}
    for name in BILLING_NAMES:
        matches = [value for key, value in environment.items() if key.casefold() == name.casefold()]
        if len(matches) > 1:
            report[name] = "ambiguous_case_variants"
            continue
        value = matches[0] if matches else None
        if name.endswith("STRIPE_SECRET_KEY"):
            report[name] = secret_status(value, "server")
        elif name.endswith("STRIPE_WEBHOOK_SECRET"):
            report[name] = secret_status(value, "webhook")
        else:
            report[name] = "missing" if value is None else "present" if value else "empty"
    return report
