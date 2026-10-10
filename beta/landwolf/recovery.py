"""One-use email tokens; fragments stay out of server request URLs and logs."""

import logging
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage
from typing import Literal

import httpx
from fastapi import BackgroundTasks, HTTPException, Request
from pydantic import EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from landwolf import auth
from landwolf.config import Settings
from landwolf.db import Account, AccountAction, AccountEmail, LoginSession
from landwolf.schemas import Contract

LOGGER = logging.getLogger(__name__)
Purpose = Literal["reset", "verify"]
TOKEN_LIFETIME = 30 * 60
GENERIC_MESSAGE = (
    "If the account is eligible, an email will arrive with the next step. "
    "Check your inbox and spam folder."
)


class EmailRequest(Contract):
    email: EmailStr = Field(max_length=254)


class TokenRequest(Contract):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$", repr=False)


class ResetRequest(TokenRequest):
    password: str = Field(min_length=12, max_length=128, repr=False)


class Mailer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return self.settings.mail_provider in {"resend", "gmail"}

    async def send(self, email: str, purpose: Purpose, token: str) -> None:
        settings = self.settings
        if not self.enabled or not settings.mail_from:
            raise RuntimeError("Email delivery is not configured")
        action = "Reset your password" if purpose == "reset" else "Verify your email address"
        # Fragments stay out of server access logs and Referrer headers. The client
        # immediately removes the fragment and sends the token only in a JSON body.
        link = f"{settings.public_origin}/#action={purpose}&token={token}"
        subject = f"LandWolf: {action}"
        text = (
            f"{action}:\n\n{link}\n\n"
            "This link expires in 30 minutes and can be used once. "
            "If you did not request this, ignore this email.\nLandWolf"
        )
        await self.send_text(email, subject, text, auth.digest(token))

    async def send_text(self, email: str, subject: str, text: str, message_id: str) -> None:
        """Transactional notices share the configured support sender and bounded transport."""
        settings = self.settings
        if not self.enabled or not settings.mail_from:
            raise RuntimeError("Email delivery is not configured")
        if settings.mail_provider == "gmail":
            # SMTP is blocking; keep it off the application event loop. No retry:
            # a lost acknowledgment must not generate duplicate reset messages.
            await run_in_threadpool(self._send_gmail, email, subject, text)
            return
        if not settings.mail_api_key:
            raise RuntimeError("Email delivery is not configured")
        async with (
            httpx.AsyncClient(timeout=10, follow_redirects=False) as client,
            client.stream(
                "POST",
                "https://api.resend.com/emails",
                headers={
                    "Authorization": "Bearer " + settings.mail_api_key.get_secret_value(),
                    "Idempotency-Key": message_id,
                },
                json={
                    "from": str(settings.mail_from),
                    "to": [email],
                    "subject": subject,
                    "text": text,
                },
            ) as response,
        ):
            response.raise_for_status()

    def _send_gmail(self, email: str, subject: str, text: str) -> None:
        settings = self.settings
        if not settings.gmail_app_password or not settings.mail_from:
            raise RuntimeError("Email delivery is not configured")
        sender = str(settings.mail_from)
        message = EmailMessage()
        message["From"] = f"LandWolf Support <{sender}>"
        message["Reply-To"] = sender
        message["To"] = email
        message["Subject"] = subject
        message.set_content(text)
        # Fixed Google endpoint, certificate verification and a bounded socket
        # timeout. Never enable SMTP debug logging: it exposes credentials/tokens.
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, timeout=10, context=ssl.create_default_context()
        ) as smtp:
            smtp.login(sender, settings.gmail_app_password.get_secret_value())
            refused = smtp.send_message(message, from_addr=sender, to_addrs=[email])
            if refused:
                raise RuntimeError("Email recipient was refused")


async def deliver(
    mailer: Mailer,
    factory: sessionmaker[Session],
    email: str,
    purpose: Purpose,
    token: str,
) -> None:
    try:
        await mailer.send(email, purpose, token)
    except (httpx.HTTPError, RuntimeError, smtplib.SMTPException, OSError):
        with factory() as session, session.begin():
            session.execute(
                delete(AccountAction).where(AccountAction.token_hash == auth.digest(token))
            )
        LOGGER.warning("Account email delivery failed; issued token invalidated")


def request_action(
    email: str,
    purpose: Purpose,
    request: Request,
    session: Session,
    settings: Settings,
    mailer: Mailer,
    factory: sessionmaker[Session],
    tasks: BackgroundTasks,
) -> dict[str, str]:
    auth.origin_guard(request, settings)
    ip = request.client.host if request.client else "unknown"
    normalized = email.casefold()
    auth.limit(session, f"recovery:ip:{ip}", 8, 600)
    auth.limit(session, f"recovery:account:{normalized}", 3, 1800)
    auth.limit(session, "recovery:global", 100, 3600)
    if not mailer.enabled:
        raise HTTPException(503, "Email recovery is not configured. Contact support.")
    account = session.scalar(select(Account).where(Account.email == normalized))
    now = int(time.time())
    session.execute(delete(AccountAction).where(AccountAction.expires_at <= now))
    if account is not None:
        token = secrets.token_urlsafe(32)
        # Existing unexpired links remain valid to prevent unauthenticated attackers
        # invalidating an inbox link. The rate limit bounds the number of live tokens.
        session.add(
            AccountAction(
                token_hash=auth.digest(token),
                account_id=account.id,
                purpose=purpose,
                expires_at=now + TOKEN_LIFETIME,
            )
        )
        tasks.add_task(deliver, mailer, factory, normalized, purpose, token)
    session.commit()
    return {"message": GENERIC_MESSAGE}


def verified(session: Session, account_id: str) -> bool:
    record = session.get(AccountEmail, account_id)
    return bool(record and record.verified_at)


def consume(session: Session, token: str, purpose: Purpose, password: str | None = None) -> None:
    # Hash before the transaction's one-use compare-and-delete to keep locks short.
    hashed = None
    if password is not None:
        with auth.password_work():
            hashed = auth.PASSWORDS.hash(password)
    account_id = session.scalar(
        delete(AccountAction)
        .where(
            AccountAction.token_hash == auth.digest(token),
            AccountAction.purpose == purpose,
            AccountAction.expires_at > int(time.time()),
        )
        .returning(AccountAction.account_id)
    )
    if account_id is None:
        session.rollback()
        raise HTTPException(400, "This link is invalid or expired. Request a new email.")
    account = session.get(Account, account_id)
    if account is None:
        session.rollback()
        raise HTTPException(400, "This link is invalid or expired. Request a new email.")
    if purpose == "reset":
        if hashed is None:
            session.rollback()
            raise ValueError("Password required for reset")
        account.password_hash = hashed
        session.execute(delete(LoginSession).where(LoginSession.account_id == account_id))
    else:
        status = session.get(AccountEmail, account_id) or AccountEmail(account_id=account_id)
        status.verified_at = int(time.time())
        session.add(status)
    session.execute(
        delete(AccountAction).where(
            AccountAction.account_id == account_id,
            AccountAction.purpose == purpose,
        )
    )
    session.commit()
