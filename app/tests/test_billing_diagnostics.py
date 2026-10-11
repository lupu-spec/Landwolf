"""Secret-safe deployment diagnostics with generated, deliberately synthetic values."""

import json

import pytest

from landwolf.billing_diagnostics import BILLING_NAMES, environment_status, secret_status


def synthetic(prefix: str) -> str:
    return prefix + "not-a-real-key" * 3


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "missing"),
        ("", "empty"),
        (" " + synthetic("sk_live_"), "surrounding_whitespace"),
        (synthetic("sk_live_") + "\n", "surrounding_whitespace"),
        ('"' + synthetic("sk_live_") + '"', "surrounding_quotes"),
        (synthetic("sk_live_") + " '", "surrounding_quotes"),
        ("sk_live_abc defghi", "embedded_whitespace"),
        ("sk_live_***", "masked_or_truncated_display"),
        ("sk_live_abc\u2026", "masked_or_truncated_display"),
        (synthetic("pk_live_"), "publishable_key_not_server_secret"),
        (synthetic("pk_test_"), "publishable_key_not_server_secret"),
        (synthetic("sk_test_"), "sandbox_server_key"),
        (synthetic("rk_test_"), "sandbox_server_key"),
        (synthetic("whsec_"), "wrong_live_server_key_prefix"),
        ("sk_live_" + "x" * 15, "too_short"),
        ("sk_live_" + "x" * 16, "format_ok_not_authenticated"),
        (synthetic("rk_live_"), "format_ok_not_authenticated"),
        ("x" * 4097, "oversized"),
    ],
)
def test_server_classification_never_exposes_value(value: str | None, expected: str) -> None:
    result = secret_status(value, "server")
    assert result == expected
    if value:
        assert value not in result
    assert "not-a-real-key" not in result


def test_webhook_shape_is_not_authentication() -> None:
    assert secret_status(synthetic("whsec_"), "webhook") == "format_ok_not_authenticated"
    assert secret_status(synthetic("sk_live_"), "webhook") == "wrong_webhook_secret_prefix"
    assert secret_status("whsec_" + "x" * 17, "webhook") == "too_short"
    assert secret_status("whsec_" + "x" * 18, "webhook") == "format_ok_not_authenticated"


def test_fixed_names_only_and_no_legacy_fallback() -> None:
    environment = {
        "STRIPE_SECRET_KEY": synthetic("sk_live_"),
        "LANDWOLF_PILOT_INVITE_EMAILS": '["private-person@example.com"]',
        "UNRELATED_PRIVATE_VALUE": "must-not-leak",
    }
    before = dict(environment)
    report = environment_status(environment)
    assert set(report) == set(BILLING_NAMES)
    assert report["LANDWOLF_STRIPE_SECRET_KEY"] == "missing"
    assert report["STRIPE_SECRET_KEY"] == "format_ok_not_authenticated"
    assert report["LANDWOLF_PILOT_INVITE_EMAILS"] == "present"
    serialized = json.dumps(report)
    assert "private-person" not in serialized
    assert "not-a-real-key" not in serialized
    assert "UNRELATED_PRIVATE_VALUE" not in serialized
    assert "must-not-leak" not in serialized
    assert environment == before


def test_case_insensitivity_and_duplicate_detection() -> None:
    environment = {"landwolf_stripe_secret_key": synthetic("sk_live_")}
    assert environment_status(environment)["LANDWOLF_STRIPE_SECRET_KEY"] == (
        "format_ok_not_authenticated"
    )
    environment["LANDWOLF_STRIPE_SECRET_KEY"] = synthetic("sk_test_")
    assert environment_status(environment)["LANDWOLF_STRIPE_SECRET_KEY"] == (
        "ambiguous_case_variants"
    )


def test_empty_nonsecret_setting_is_distinct_from_missing() -> None:
    report = environment_status({"LANDWOLF_OWNER_ACCOUNT_ID": ""})
    assert report["LANDWOLF_OWNER_ACCOUNT_ID"] == "empty"
    assert report["LANDWOLF_STRIPE_ACCOUNT_ID"] == "missing"
