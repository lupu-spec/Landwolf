from scripts.deployment_preflight import validate, compare_envs

def good_env(target="production"):
    live = target == "production"
    return {
        "APP_ENV": target,
        "SECRET_KEY": "A9!z" * 20,
        "DATABASE_URL": f"postgresql+psycopg://property:VeryLongDbPassword!12345@{target}-db.internal:5432/property_intelligence",
        "CORS_ORIGINS": f"https://{target}.example.com",
        "JWT_EXPIRE_MINUTES": "60",
        "COOKIE_SECURE": "true",
        "COOKIE_HTTPONLY": "true",
        "COOKIE_SAMESITE": "lax",
        "STRIPE_SECRET_KEY": ("sk_live_" if live else "sk_test_") + "x" * 32,
        "STRIPE_MONTHLY_PRICE_ID": "price_" + "m" * 24,
        "STRIPE_ANNUAL_PRICE_ID": "price_" + "a" * 24,
        "STRIPE_WEBHOOK_SECRET": "whsec_" + "x" * 32,
        "STRIPE_SUCCESS_URL": f"https://{target}.example.com/?checkout=success",
        "STRIPE_CANCEL_URL": f"https://{target}.example.com/?checkout=cancel",
    }

def test_valid_production():
    assert validate(good_env("production"), "production") == []

def test_valid_staging():
    assert validate(good_env("staging"), "staging") == []

def test_missing_required_fails():
    e = good_env()
    e["SECRET_KEY"] = ""
    assert any("SECRET_KEY" in x for x in validate(e, "production"))

def test_weak_secret_fails():
    e = good_env()
    e["SECRET_KEY"] = "changeme"
    assert validate(e, "production")

def test_wildcard_cors_fails():
    e = good_env()
    e["CORS_ORIGINS"] = "*"
    assert validate(e, "production")

def test_http_cors_fails():
    e = good_env()
    e["CORS_ORIGINS"] = "http://prod.example.com"
    assert validate(e, "production")

def test_insecure_cookie_fails():
    e = good_env()
    e["COOKIE_SECURE"] = "false"
    assert validate(e, "production")

def test_production_test_stripe_key_fails():
    e = good_env()
    e["STRIPE_SECRET_KEY"] = "sk_test_" + "x" * 32
    assert validate(e, "production")

def test_staging_live_stripe_key_fails():
    e = good_env("staging")
    e["STRIPE_SECRET_KEY"] = "sk_live_" + "x" * 32
    assert validate(e, "staging")

def test_secret_reuse_between_environments_fails():
    s, p = good_env("staging"), good_env("production")
    p["SECRET_KEY"] = s["SECRET_KEY"]
    assert any("SECRET_KEY is reused" in x for x in compare_envs(s, p))

def test_database_secret_reuse_fails():
    s, p = good_env("staging"), good_env("production")
    p["DATABASE_URL"] = s["DATABASE_URL"]
    assert any("DATABASE_URL is reused" in x for x in compare_envs(s, p))
