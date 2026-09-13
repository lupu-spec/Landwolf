from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.entities import User

bearer = HTTPBearer(auto_error=False)


def register(db: Session, email: str, password: str) -> User:
    normalized = email.lower().strip()
    if db.scalar(select(User).where(User.email == normalized)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=normalized, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials else session_cookie
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        user_id = decode_access_token(token)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid account")
    return user
