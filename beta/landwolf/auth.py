"""Revocable, hashed opaque sessions; no browser token storage or billing gates."""

import hashlib
import secrets
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from threading import BoundedSemaphore
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request, Response
from sqlalchemy import case, delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from landwolf.config import Settings
from landwolf.crm_access import ensure_enabled
from landwolf.crm_core import CONSENT_TEXT, CONSENT_VERSION, Intake, capture, record_activity
from landwolf.db import Account, LoginSession, RateBucket
from landwolf.schemas import Credentials, Registration

COOKIE = "landwolf_session"
PASSWORDS = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
PASSWORD_WORK = BoundedSemaphore(2)


@contextmanager
def password_work() -> Iterator[None]:
    """Bound concurrent Argon2 memory use, including across different client IPs."""
    if not PASSWORD_WORK.acquire(blocking=False):
        raise HTTPException(
            503, "Sign-in is busy. Please try again shortly.", headers={"Retry-After": "2"}
        )
    try:
        yield
    finally:
        PASSWORD_WORK.release()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def limit(session: Session, key: str, maximum: int, seconds: int = 60) -> None:
    """Atomic shared-database buckets; never trust client-supplied forwarding headers."""
    now = int(time.time())
    bucket = digest(f"{key}:{now // seconds}")
    insert = (
        sqlite_insert
        if session.bind is not None and session.bind.dialect.name == "sqlite"
        else pg_insert
    )
    stmt = insert(RateBucket).values(key=bucket, count=1, expires_at=now + seconds * 2)
    upsert = stmt.on_conflict_do_update(
        index_elements=[RateBucket.key], set_={"count": RateBucket.count + 1}
    ).returning(RateBucket.count)
    count = session.scalar(upsert)
    session.execute(delete(RateBucket).where(RateBucket.expires_at < now))
    session.commit()
    if count is None or count > maximum:
        raise HTTPException(
            429, "Too many requests. Please try again later.", headers={"Retry-After": str(seconds)}
        )


def origin_guard(request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin", "")
    # Each configured origin may write only to its own host, even during a cutover.
    if origin not in settings.trusted_origins or request.headers.get("host", "").lower() != (
        urlsplit(origin).netloc
    ):
        raise HTTPException(403, "Request origin is not allowed")
    if request.headers.get("x-landwolf-client") != "web":
        raise HTTPException(403, "Client header is required")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site request rejected")
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        raise HTTPException(415, "Use application/json")


def authenticate(
    request: Request,
    session: Session,
    settings: Settings,
    *,
    write: bool = False,
    touch: bool = True,
    response: Response | None = None,
) -> Account:
    token = request.cookies.get(COOKIE, "")
    if len(token) != 43:
        raise HTTPException(401, "Sign in to access LandWolf")
    login = session.get(LoginSession, digest(token))
    now = int(time.time())
    if login is None or login.expires_at <= now:
        if login is not None:
            session.delete(login)
            session.commit()
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    account = session.get(Account, login.account_id)
    if account is None:
        raise HTTPException(401, "Sign in to access LandWolf")
    ensure_enabled(session, account, settings)
    if write:
        origin_guard(request, settings)
        supplied_csrf = request.headers.get("x-csrf-token", "")
        if (
            len(supplied_csrf) != 43
            or not supplied_csrf.isascii()
            or not secrets.compare_digest(supplied_csrf, login.csrf)
        ):
            raise HTTPException(403, "Invalid security token; reload the page")
    if touch:
        # Update only an existing, valid row: concurrent logout/reset must never
        # resurrect a revoked session. /api/session renews both database and cookie.
        deadline = now + settings.session_days * 86400
        renewed = session.scalar(
            update(LoginSession)
            .where(LoginSession.token_hash == login.token_hash, LoginSession.expires_at > now)
            .values(
                last_seen=now,
                expires_at=(
                    case(
                        (LoginSession.expires_at < deadline, deadline),
                        else_=LoginSession.expires_at,
                    )
                    if response is not None
                    else LoginSession.expires_at
                ),
            )
            .returning(LoginSession.expires_at)
        )
        session.commit()
        if renewed is None:
            raise HTTPException(401, "Sign in to access LandWolf")
        if response is not None:
            set_session_cookie(response, token, settings, now)
    request.state.login = login
    return account


def set_session_cookie(response: Response, token: str, settings: Settings, now: int) -> None:
    """Keep credentials in a persistent HttpOnly cookie, never browser script storage."""
    lifetime = settings.session_days * 86400
    response.set_cookie(
        COOKIE,
        token,
        max_age=lifetime,
        expires=datetime.fromtimestamp(now + lifetime, UTC),
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )


def establish(
    account: Account, request: Request, response: Response, session: Session, settings: Settings
) -> dict[str, str]:
    old = request.cookies.get(COOKIE)
    if old:
        session.execute(delete(LoginSession).where(LoginSession.token_hash == digest(old)))
    now = int(time.time())
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    session.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
    session.add(
        LoginSession(
            token_hash=digest(token),
            account_id=account.id,
            csrf=csrf,
            expires_at=now + settings.session_days * 86400,
            last_seen=now,
        )
    )
    session.commit()
    set_session_cookie(response, token, settings, now)
    return {"email": account.email, "csrf": csrf}


def sign_in(
    credentials: Credentials,
    request: Request,
    response: Response,
    session: Session,
    settings: Settings,
    *,
    register: bool,
) -> dict[str, str]:
    origin_guard(request, settings)
    email = str(credentials.email).casefold()
    ip = request.client.host if request.client else "unknown"
    limit(session, f"auth:ip:{ip}", settings.auth_limit, 600)
    limit(session, f"auth:account:{email}", settings.auth_limit, 600)
    account = session.scalar(select(Account).where(Account.email == email))
    if register:
        # Perform the expensive hash even for duplicate emails, then use a generic error.
        with password_work():
            hashed = PASSWORDS.hash(credentials.password)
        if account:
            raise HTTPException(400, "Unable to create account. Try signing in or contact support.")
        account = Account(id=str(uuid.uuid4()), email=email, password_hash=hashed)
        session.add(account)
        try:
            if not isinstance(credentials, Registration):
                raise HTTPException(422, "Registration profile is required")
            session.flush()
            contact = capture(
                session,
                "landwolf",
                Intake(
                    external_id=account.id,
                    email=email,
                    consent_version=CONSENT_VERSION,
                    **credentials.profile.model_dump(),
                ),
                source="registration",
            )
            record_activity(
                session,
                contact.id,
                account.id,
                "consent_recorded",
                ("Opted in: " if credentials.profile.marketing_opt_in else "Not opted in: ")
                + CONSENT_TEXT,
            )
            session.commit()
        except (IntegrityError, ValueError) as exc:
            session.rollback()
            raise HTTPException(
                400, "Unable to create account. Try signing in or contact support."
            ) from exc
    else:
        try:
            with password_work():
                PASSWORDS.verify(
                    account.password_hash if account else DUMMY_HASH, credentials.password
                )
        except (VerificationError, InvalidHashError) as exc:
            raise HTTPException(401, "Email or password is incorrect") from exc
        if account is None:
            raise HTTPException(401, "Email or password is incorrect")
        if PASSWORDS.check_needs_rehash(account.password_hash):
            with password_work():
                account.password_hash = PASSWORDS.hash(credentials.password)
    ensure_enabled(session, account, settings)
    return establish(account, request, response, session, settings)
