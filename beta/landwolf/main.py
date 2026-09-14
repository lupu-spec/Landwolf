"""Same-origin FastAPI beta. Every property and analysis route requires a session."""

import asyncio
import contextlib
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from landwolf import auth
from landwolf.analysis import analyze
from landwolf.config import Settings
from landwolf.db import (
    Account,
    Listing,
    LoginSession,
    SavedProperty,
    SchemaVersion,
    database,
    initialize,
)
from landwolf.provider import MAX_RECORDS, GLOProvider
from landwolf.schemas import AnalysisInput, Credentials, PropertyRecord, SearchQuery


class BodyLimit:
    """Bound even chunked request bodies before JSON parsing; do not log their contents."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD"}:
            await self.app(scope, receive, send)
            return
        body = bytearray()
        try:
            async with asyncio.timeout(10):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > 16384:
                        await JSONResponse({"detail": "Request is too large"}, 413)(
                            scope, receive, send
                        )
                        return
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse({"detail": "Request timed out"}, 408)(scope, receive, send)
            return
        consumed = False

        async def bounded_receive() -> Message:
            nonlocal consumed
            if consumed:
                return await receive()
            consumed = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, bounded_receive, send)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine, factory = database(settings.database_url)
    provider = GLOProvider(factory)

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.environment != "production":
            initialize(engine)
        with factory() as session:
            if session.scalars(select(SchemaVersion.version)).all() != [1]:
                raise RuntimeError("Run the explicit beta schema initialization before serving")
        task = asyncio.create_task(provider.run()) if settings.auto_sync else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            engine.dispose()

    app = FastAPI(
        title="LandWolf Beta",
        version="0.2.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.factory, app.state.provider, app.state.settings = factory, provider, settings
    app.add_middleware(BodyLimit)
    host = urlsplit(settings.public_origin).hostname
    if host is None:
        raise ValueError("A public origin hostname is required")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[host])

    @app.middleware("http")
    async def headers(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
                # Leaflet needs dynamic inline positioning styles; scripts stay self-only.
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https://cdn.glo.texas.gov "
                    "https://tile.openstreetmap.org; "
                    "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; "
                    "frame-ancestors 'none'; form-action 'self'"
                ),
            }
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if settings.secure_cookies:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's default errors include submitted inputs, potentially passwords.
        fields = [".".join(str(p) for p in err["loc"][1:]) for err in exc.errors()]
        return JSONResponse(
            {"detail": "Check the values in: " + ", ".join(fields)}, status_code=422
        )

    def db() -> Iterator[Session]:
        with factory() as session:
            yield session

    DB = Annotated[Session, Depends(db)]

    @app.get("/api/health")
    def health(session: DB) -> dict[str, Any]:
        try:
            session.execute(text("SELECT 1"))
            version = session.scalars(select(SchemaVersion.version)).all()
            if version != [1]:
                raise HTTPException(503, "Schema is not ready")
        except SQLAlchemyError as exc:
            raise HTTPException(503, "Database is not ready") from exc
        return {"status": "ok", "version": "0.2.0", "payments_enabled": False}

    @app.get("/api/session")
    def current(request: Request, session: DB) -> dict[str, Any]:
        try:
            account = auth.authenticate(request, session, settings)
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
            return {"authenticated": False}
        return {"authenticated": True, "email": account.email, "csrf": request.state.login.csrf}

    @app.post("/api/auth/register", status_code=201)
    def register(
        credentials: Credentials, request: Request, response: Response, session: DB
    ) -> dict[str, str]:
        return auth.sign_in(credentials, request, response, session, settings, register=True)

    @app.post("/api/auth/login")
    def login(
        credentials: Credentials, request: Request, response: Response, session: DB
    ) -> dict[str, str]:
        return auth.sign_in(credentials, request, response, session, settings, register=False)

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response, session: DB) -> dict[str, bool]:
        auth.authenticate(request, session, settings, write=True)
        session.execute(
            delete(LoginSession).where(LoginSession.token_hash == request.state.login.token_hash)
        )
        session.commit()
        response.delete_cookie(
            auth.COOKIE, path="/", secure=settings.secure_cookies, httponly=True, samesite="strict"
        )
        return {"ok": True}

    @app.get("/api/sources")
    def sources(request: Request, session: DB) -> dict[str, Any]:
        auth.authenticate(request, session, settings)
        return {"sources": [provider.status()], "payments_enabled": False}

    def record_payload(item: Listing, saved: set[str]) -> dict[str, Any]:
        value = PropertyRecord.model_validate(item.payload).model_dump()
        value.update(active=item.active, saved=item.id in saved)
        return value

    def saved_ids(session: Session, account: Account) -> set[str]:
        return set(
            session.scalars(
                select(SavedProperty.listing_id).where(SavedProperty.account_id == account.id)
            )
        )

    @app.post("/api/search")
    def search(query: SearchQuery, request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"search:{account.id}", 60)
        supported = query.state == "TX" and query.category in {"all", "government_land"}
        saved = saved_ids(session, account)
        rows: list[dict[str, Any]] = []
        if supported:
            stmt = select(Listing).order_by(Listing.id).limit(MAX_RECORDS)
            if not query.saved_only:
                stmt = stmt.where(Listing.active.is_(True))
            for item in session.scalars(stmt):
                value = record_payload(item, saved)
                location = " ".join(
                    str(value.get(k) or "") for k in ("county", "tract", "location_description")
                ).casefold()
                if query.location.strip().casefold() not in location:
                    continue
                if value["acres"] < query.min_acres or (
                    query.max_price is not None and value["asking_price"] > query.max_price
                ):
                    continue
                if query.saved_only and item.id not in saved:
                    continue
                rows.append(value)
        key = (
            "county"
            if query.sort == "county"
            else "acres"
            if query.sort == "acres_desc"
            else "asking_price"
        )
        rows.sort(
            key=lambda row: (row[key], row["id"]),
            reverse=query.sort in {"price_desc", "acres_desc"},
        )
        start = (query.page - 1) * query.page_size
        return {
            "results": rows[start : start + query.page_size],
            "total": len(rows),
            "page": query.page,
            "page_size": query.page_size,
            "coverage_supported": supported,
            "source": provider.status(),
        }

    @app.get("/api/properties/{listing_id}")
    def detail(listing_id: str, request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings)
        item = session.get(Listing, listing_id)
        if item is None:
            raise HTTPException(404, "Property not found")
        return record_payload(item, saved_ids(session, account))

    @app.put("/api/saved/{listing_id}")
    def save(listing_id: str, request: Request, session: DB) -> dict[str, bool]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"save:{account.id}", 60)
        if session.get(Listing, listing_id) is None:
            raise HTTPException(404, "Property not found")
        # Per-user idempotent upsert handles double-clicks and concurrent requests.
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        insert = sqlite_insert if engine.dialect.name == "sqlite" else pg_insert
        session.execute(
            insert(SavedProperty)
            .values(account_id=account.id, listing_id=listing_id, created_at=int(time.time()))
            .on_conflict_do_nothing()
        )
        session.commit()
        return {"saved": True}

    @app.delete("/api/saved/{listing_id}")
    def unsave(listing_id: str, request: Request, session: DB) -> dict[str, bool]:
        account = auth.authenticate(request, session, settings, write=True)
        session.execute(
            delete(SavedProperty).where(
                SavedProperty.account_id == account.id, SavedProperty.listing_id == listing_id
            )
        )
        session.commit()
        return {"saved": False}

    @app.post("/api/analysis")
    def analysis(spec: AnalysisInput, request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"analysis:{account.id}", 10)
        return analyze(spec)

    static = Path(__file__).resolve().parent / "static"
    if static.is_dir():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(static / "index.html")

        @app.get("/favicon.svg", include_in_schema=False)
        def favicon() -> FileResponse:
            return FileResponse(static / "favicon.svg")

    return app
