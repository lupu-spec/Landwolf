from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.services.auth import authenticate, current_user, register

router = APIRouter(prefix="/api/auth", tags=["auth"])


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
    )


@router.post("/register", response_model=TokenResponse)
def register_user(request: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    user = register(db, request.email, request.password)
    token = create_access_token(user.id)
    set_auth_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate(db, request.email, request.password)
    token = create_access_token(user.id)
    set_auth_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(
        key=settings.auth_cookie_name,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
        secure=settings.cookie_secure,
        httponly=settings.cookie_httponly,
        samesite=settings.cookie_samesite,
    )


@router.get("/me", response_model=MeResponse)
def me(user=Depends(current_user)):
    return MeResponse(
        id=user.id,
        email=user.email,
        subscription_status=user.subscription_status,
    )
