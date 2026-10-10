"""Real reset routes and message composition; only Google's transport is synthetic."""

import asyncio
import smtplib
import ssl
import threading

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import select

from landwolf import auth
from landwolf.config import Settings
from landwolf.db import AccountAction
from landwolf.recovery import Mailer

SENDER = "support.landwolf@gmail.com"
TEST_PASSWORD = "abcdefghijklmnop"  # Synthetic, never a mailbox credential.


def settings(**changes):
    values = {
        "environment": "test",
        "public_origin": "https://landwolf.ai",
        "mail_provider": "gmail",
        "mail_from": SENDER,
        "gmail_app_password": SecretStr(TEST_PASSWORD),
    }
    return Settings(**(values | changes))


@pytest.fixture
def smtp(monkeypatch):
    calls = {"messages": []}

    class Transport:
        def __init__(self, host, port, *, timeout, context):
            assert (host, port, timeout) == ("smtp.gmail.com", 465, 10)
            assert context.verify_mode == ssl.CERT_REQUIRED
            assert context.check_hostname
            calls["thread"] = threading.get_ident()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            calls["closed"] = True

        def login(self, username, password):
            assert username == SENDER and password == TEST_PASSWORD
            if calls.get("failure"):
                raise calls["failure"]

        def send_message(self, message, *, from_addr, to_addrs):
            calls["messages"].append((message, from_addr, to_addrs))
            return {to_addrs[0]: (550, b"Synthetic refusal")} if calls.get("refused") else {}

    monkeypatch.setattr("landwolf.recovery.smtplib.SMTP_SSL", Transport)
    return calls


@pytest.mark.parametrize("purpose", ["reset", "verify"])
def test_gmail_sender_recipient_tls_and_event_loop(smtp, purpose):
    caller_thread = threading.get_ident()
    asyncio.run(Mailer(settings()).send("recipient@example.com", purpose, "a" * 43))
    message, sender, recipients = smtp["messages"][0]
    assert sender == SENDER and recipients == ["recipient@example.com"]
    assert str(message["From"]) == f"LandWolf Support <{SENDER}>"
    assert str(message["Reply-To"]) == SENDER
    assert str(message["To"]) == "recipient@example.com"
    assert message["Cc"] is None and message["Bcc"] is None
    body = message.get_content()
    assert f"https://landwolf.ai/#action={purpose}&token=" + "a" * 43 in body
    assert "30 minutes" in body and "used once" in body
    assert smtp["closed"] and smtp["thread"] != caller_thread


@pytest.mark.parametrize("route", ["/api/auth/recovery", "/api/account/password-reset"])
def test_login_and_chat_routes_send_through_same_support_mailbox(client, signed_in, smtp, route):
    client.app.state.mailer = Mailer(settings())
    body = {"email": "investor@example.com"} if route.endswith("recovery") else {}
    response = client.post(route, json=body, headers=signed_in)
    assert response.status_code == 202
    message, sender, recipients = smtp["messages"][0]
    assert sender == SENDER and recipients == ["investor@example.com"]
    token = message.get_content().split("token=", 1)[1].split()[0]
    assert token not in response.text
    with client.app.state.factory() as session:
        assert session.scalar(select(AccountAction)).token_hash == auth.digest(token)
    reset_body = {"token": token, "password": "New synthetic passphrase 941!"}
    assert (
        client.post("/api/auth/reset-password", json=reset_body, headers=signed_in).status_code
        == 200
    )
    assert (
        client.post("/api/auth/reset-password", json=reset_body, headers=signed_in).status_code
        == 400
    )
    assert not client.get("/api/session").json()["authenticated"]


@pytest.mark.parametrize(
    "failure",
    [
        smtplib.SMTPAuthenticationError(535, b"Synthetic authentication failure"),
        smtplib.SMTPServerDisconnected("Synthetic disconnect"),
        TimeoutError("Synthetic timeout"),
        ssl.SSLError("Synthetic TLS failure"),
    ],
)
def test_smtp_failure_invalidates_token_without_leaking_details(
    client, signed_in, smtp, caplog, failure
):
    client.app.state.mailer = Mailer(settings())
    smtp["failure"] = failure
    result = client.post("/api/account/password-reset", json={}, headers=signed_in)
    assert result.status_code == 202
    with client.app.state.factory() as session:
        assert session.scalar(select(AccountAction)) is None
    assert "issued token invalidated" in caplog.text
    assert TEST_PASSWORD not in caplog.text and "Synthetic" not in caplog.text
    assert not smtp["messages"] and smtp["closed"]


def test_refused_recipient_invalidates_token(client, signed_in, smtp):
    client.app.state.mailer = Mailer(settings())
    smtp["refused"] = True
    assert client.post("/api/account/password-reset", json={}, headers=signed_in).status_code == 202
    with client.app.state.factory() as session:
        assert session.scalar(select(AccountAction)) is None


@pytest.mark.parametrize("password", [None, "", "short", "a" * 17, "a" * 15 + "\n", "é" * 16])
def test_gmail_rejects_missing_or_invalid_credential(password):
    with pytest.raises(ValidationError, match="16-letter app password") as error:
        settings(gmail_app_password=password)
    assert "input_value" not in str(error.value)


def test_gmail_requires_support_sender_and_accepts_grouped_password():
    with pytest.raises(ValidationError, match="support sender"):
        settings(mail_from="other@gmail.com")
    configured = settings(gmail_app_password="abcd efgh ijkl mnop")
    assert configured.gmail_app_password.get_secret_value() == TEST_PASSWORD
    assert TEST_PASSWORD not in repr(configured)
    assert not Mailer(Settings()).enabled
