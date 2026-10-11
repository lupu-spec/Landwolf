from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.search import router as search_router
from app.core.config import settings
from app.db.session import Base, engine

app = FastAPI(
    title="US Property Intelligence",
    version="0.1.0",
    description="Property intelligence and acquisition analysis platform.",
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Stripe-Signature"],
)

app.include_router(auth_router)
app.include_router(search_router)
app.include_router(billing_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "environment": settings.app_env}


@app.on_event("startup")
def startup():
    # Settings are instantiated at import time, so invalid staging/production
    # configuration fails before the server starts accepting traffic.
    if settings.app_env in {"development", "test"}:
        Base.metadata.create_all(bind=engine)


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
