from pathlib import Path

def test_smoke_script_covers_release_contract():
    text = Path("scripts/post_deploy_smoke.py").read_text().lower()
    for token in ["api/health","access-control-allow-origin","access-control-allow-credentials","api/auth/register","api/auth/login","httponly","secure","samesite=","api/auth/me","api/search/preview","unauthenticated search","unsubscribed first search","subscription_required","expected 402"]:
        assert token in text

def test_smoke_script_does_not_print_sensitive_values():
    text = Path("scripts/post_deploy_smoke.py").read_text().lower()
    for forbidden in ["print(auth_cookie)", "print(password)", "print(token)"]:
        assert forbidden not in text
