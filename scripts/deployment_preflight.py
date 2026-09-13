#!/usr/bin/env python3
"""
Fail-closed deployment preflight.

Usage:
  python scripts/deployment_preflight.py --environment staging
  python scripts/deployment_preflight.py --environment production
  python scripts/deployment_preflight.py --compare-env-files .env.staging .env.production

The script never prints secret values.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ENVIRONMENTS = {"staging", "production"}

REQUIRED_COMMON = {
    "APP_ENV",
    "SECRET_KEY",
    "DATABASE_URL",
    "CORS_ORIGINS",
    "JWT_EXPIRE_MINUTES",
    "COOKIE_SECURE",
    "COOKIE_HTTPONLY",
    "COOKIE_SAMESITE",
}

REQUIRED_BILLING = {
    "STRIPE_SECRET_KEY",
    "STRIPE_MONTHLY_PRICE_ID",
    "STRIPE_ANNUAL_PRICE_ID",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_SUCCESS_URL",
    "STRIPE_CANCEL_URL",
}

PLACEHOLDER_PATTERNS = (
    r"^replace[-_ ]?me",
    r"^changeme$",
    r"^change[-_ ]?me",
    r"^secret$",
    r"^password$",
    r"^example",
    r"^test$",
    r"^dummy",
    r"^your[-_ ]",
)

SENSITIVE_KEYS = {
    "SECRET_KEY",
    "DATABASE_URL",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
}

def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}

def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(path)
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values

def entropy_bits(value: str) -> float:
    if not value:
        return 0.0
    alphabet = 0
    if re.search(r"[a-z]", value): alphabet += 26
    if re.search(r"[A-Z]", value): alphabet += 26
    if re.search(r"\d", value): alphabet += 10
    if re.search(r"[^A-Za-z0-9]", value): alphabet += 32
    if alphabet == 0:
        return 0.0
    return len(value) * math.log2(alphabet)

def is_placeholder(value: str) -> bool:
    v = value.strip().lower()
    return any(re.search(p, v) for p in PLACEHOLDER_PATTERNS)

def validate_secret(name: str, value: str, errors: list[str]) -> None:
    if not value:
        errors.append(f"{name} is missing or empty.")
        return
    if is_placeholder(value):
        errors.append(f"{name} appears to contain a placeholder/default value.")
    # DATABASE_URL is validated structurally rather than with generic entropy.
    if name == "DATABASE_URL":
        parsed = urlparse(value.replace("postgresql+psycopg://", "postgresql://", 1))
        if not parsed.scheme.startswith("postgresql"):
            errors.append("DATABASE_URL must use PostgreSQL/PostGIS in staging/production.")
        if not parsed.hostname:
            errors.append("DATABASE_URL must include a database host.")
        if not parsed.username:
            errors.append("DATABASE_URL must include a database username.")
        if parsed.password and (len(parsed.password) < 16 or is_placeholder(parsed.password)):
            errors.append("DATABASE_URL contains a weak/default database password.")
        return
    if name == "SECRET_KEY":
        if len(value) < 32:
            errors.append("SECRET_KEY must be at least 32 characters.")
        if entropy_bits(value) < 160:
            errors.append("SECRET_KEY has insufficient estimated entropy; use a cryptographically random value.")
    elif name == "STRIPE_WEBHOOK_SECRET":
        if not value.startswith("whsec_") or len(value) < 20:
            errors.append("STRIPE_WEBHOOK_SECRET does not look like a valid Stripe webhook signing secret.")
    elif name == "STRIPE_SECRET_KEY":
        if not (value.startswith("sk_test_") or value.startswith("sk_live_")):
            errors.append("STRIPE_SECRET_KEY must be a Stripe secret key.")
        if len(value) < 20:
            errors.append("STRIPE_SECRET_KEY appears too short.")

def validate(env: dict[str, str], target: str) -> list[str]:
    errors: list[str] = []

    if target not in ENVIRONMENTS:
        return [f"Unsupported environment: {target}"]

    required = REQUIRED_COMMON | REQUIRED_BILLING
    for key in sorted(required):
        if not env.get(key, "").strip():
            errors.append(f"Required variable {key} is missing.")

    app_env = env.get("APP_ENV", "").strip().lower()
    if app_env != target:
        errors.append(f"APP_ENV must be '{target}' for a {target} release.")

    for key in SENSITIVE_KEYS:
        validate_secret(key, env.get(key, ""), errors)

    origins = [x.strip() for x in env.get("CORS_ORIGINS", "").split(",") if x.strip()]
    if not origins:
        errors.append("CORS_ORIGINS must contain at least one explicit origin.")
    for origin in origins:
        if origin == "*" or "*" in origin:
            errors.append("CORS_ORIGINS must not contain wildcards.")
        if not origin.startswith("https://"):
            errors.append(f"CORS origin must use HTTPS in {target}: {origin!r}")
        if "localhost" in origin or "127.0.0.1" in origin:
            errors.append(f"Localhost CORS origin is forbidden in {target}.")

    if not parse_bool(env.get("COOKIE_SECURE", "")):
        errors.append("COOKIE_SECURE must be true.")
    if not parse_bool(env.get("COOKIE_HTTPONLY", "")):
        errors.append("COOKIE_HTTPONLY must be true.")
    same_site = env.get("COOKIE_SAMESITE", "").strip().lower()
    if same_site not in {"lax", "strict", "none"}:
        errors.append("COOKIE_SAMESITE must be lax, strict, or none.")
    if same_site == "none" and not parse_bool(env.get("COOKIE_SECURE", "")):
        errors.append("SameSite=None requires COOKIE_SECURE=true.")

    for key in ("STRIPE_SUCCESS_URL", "STRIPE_CANCEL_URL"):
        value = env.get(key, "")
        if value and not value.startswith("https://"):
            errors.append(f"{key} must use HTTPS in {target}.")

    stripe_key = env.get("STRIPE_SECRET_KEY", "")
    if target == "production" and stripe_key.startswith("sk_test_"):
        errors.append("Production must not use a Stripe test secret key.")
    if target == "staging" and stripe_key.startswith("sk_live_"):
        errors.append("Staging must not use a Stripe live secret key.")


    try:
        minutes = int(env.get("JWT_EXPIRE_MINUTES", "0"))
        if minutes <= 0 or minutes > 1440:
            errors.append("JWT_EXPIRE_MINUTES must be between 1 and 1440.")
    except ValueError:
        errors.append("JWT_EXPIRE_MINUTES must be an integer.")

    return errors

def compare_envs(staging: dict[str, str], production: dict[str, str]) -> list[str]:
    errors: list[str] = []

    # Secret reuse across environments is forbidden.
    for key in SENSITIVE_KEYS:
        s = staging.get(key, "").strip()
        p = production.get(key, "").strip()
        if s and p and s == p:
            errors.append(f"{key} is reused between staging and production.")

    # Public endpoints/origins should also not accidentally point at the same environment.
    for key in ("CORS_ORIGINS", "STRIPE_SUCCESS_URL", "STRIPE_CANCEL_URL"):
        s = staging.get(key, "").strip()
        p = production.get(key, "").strip()
        if s and p and s == p:
            errors.append(f"{key} is identical in staging and production; verify environment isolation.")

    if staging.get("APP_ENV", "").lower() != "staging":
        errors.append("Staging file APP_ENV must equal staging.")
    if production.get("APP_ENV", "").lower() != "production":
        errors.append("Production file APP_ENV must equal production.")

    return errors

def load_current_environment() -> dict[str, str]:
    return dict(os.environ)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=sorted(ENVIRONMENTS))
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--compare-env-files", nargs=2, metavar=("STAGING_FILE", "PRODUCTION_FILE"))
    args = parser.parse_args()

    errors: list[str] = []

    if args.compare_env_files:
        s_path, p_path = map(Path, args.compare_env_files)
        staging = parse_env_file(s_path)
        production = parse_env_file(p_path)
        errors += validate(staging, "staging")
        errors += validate(production, "production")
        errors += compare_envs(staging, production)
    else:
        if not args.environment:
            parser.error("--environment is required unless --compare-env-files is used")
        env = parse_env_file(args.env_file) if args.env_file else load_current_environment()
        errors += validate(env, args.environment)

    if errors:
        print("DEPLOYMENT PREFLIGHT FAILED", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print("DEPLOYMENT PREFLIGHT PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
