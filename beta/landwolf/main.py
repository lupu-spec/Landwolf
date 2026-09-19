"""Same-origin FastAPI beta. Every property and analysis route requires a session."""

import asyncio
import contextlib
import time
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from landwolf import auth
from landwolf.analysis import analyze
from landwolf.catalog import Catalog, current_sale_conditions
from landwolf.config import Settings
from landwolf.db import (
    SCHEMA_VERSION,
    Account,
    Listing,
    LoginSession,
    SavedProperty,
    SavedRecord,
    SchemaVersion,
    database,
    initialize,
)
from landwolf.research import (
    RESEARCH_SOURCES,
    ResearchBusy,
    ResearchPoint,
    ResearchQuery,
    ResearchReport,
    ResearchService,
)
from landwolf.saved import SavedCreate, SavedUpdate, saved_payload, source_location
from landwolf.schemas import AnalysisInput, Credentials, PropertyRecord, SearchQuery
from landwolf.sources import SOURCE_BY_ID


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
    provider = Catalog(factory)
    research = ResearchService()

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.environment != "production":
            initialize(engine)
        with factory() as session:
            if session.scalars(select(SchemaVersion.version)).all() != [SCHEMA_VERSION]:
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
        title="LandWolf",
        version="0.2.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.factory, app.state.provider, app.state.settings = factory, provider, settings
    app.state.research = research
    app.add_middleware(BodyLimit)
    hosts = []
    for origin in settings.trusted_origins:
        host = urlsplit(origin).hostname
        if host is None:
            raise ValueError("A public origin hostname is required")
        hosts.append(host)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts, www_redirect=False)

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
                    "https://dnr.alaska.gov https://tile.openstreetmap.org; "
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
            if version != [SCHEMA_VERSION]:
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
        return {
            "sources": provider.statuses(),
            "states": provider.coverage(),
            "research_sources": list(RESEARCH_SOURCES),
            "payments_enabled": False,
        }

    @app.post("/api/research")
    async def research_location(
        query: ResearchQuery, request: Request, session: DB
    ) -> ResearchReport:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"research:{account.id}", 12)
        auth.limit(session, "research:shared", 40)
        point = None
        if query.listing_id:
            item = session.get(Listing, query.listing_id)
            if item is None:
                raise HTTPException(404, "Property not found")
            record = PropertyRecord.model_validate(item.payload)
            if record.latitude is None or record.longitude is None:
                raise HTTPException(
                    422, "No published point is available. Use an address or verified coordinates."
                )
            point = ResearchPoint(
                latitude=record.latitude,
                longitude=record.longitude,
                label=record.title,
                basis="Source-published coordinate",
                state=record.state,
            )
        # Release the database connection before bounded upstream I/O.
        session.close()
        try:
            return await research.lookup(query, point)
        except ResearchBusy as exc:
            raise HTTPException(
                503,
                "Property research is busy. Please try again shortly.",
                headers={"Retry-After": "5"},
            ) from exc

    def record_payload(item: Listing, session: Session, account: Account) -> dict[str, Any]:
        record = PropertyRecord.model_validate(item.payload)
        value = record.model_dump(mode="json")
        entry = session.get(SavedRecord, (account.id, item.id))
        saved = saved_payload(session, entry) if entry else None
        location = source_location(record)
        value.update(
            active=item.active,
            saved=entry is not None,
            saved_record=saved,
            research_location=saved["location"]
            if saved
            else location.model_dump()
            if location
            else None,
            location_origin=saved["location_origin"] if saved else "source",
        )
        today = datetime.now(UTC).date().isoformat()
        if any(
            value.get(key) and value[key] < today for key in ("auction_date", "bidding_deadline")
        ):
            value.update(active=False, sale_status="Date passed — verify outcome")
        return value

    @app.post("/api/search")
    def search(query: SearchQuery, request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"search:{account.id}", 60)
        if query.source is not None and query.source not in SOURCE_BY_ID:
            raise HTTPException(422, "Select a known source")
        sources = provider.statuses(query.state, query.category, query.source)
        supported = any(source["automated"] for source in sources)
        stmt = select(Listing)
        if query.saved_only:
            stmt = stmt.where(
                Listing.id.in_(
                    select(SavedRecord.listing_id).where(SavedRecord.account_id == account.id)
                )
            )
        else:
            stmt = stmt.where(
                Listing.active.is_(True),
                *current_sale_conditions(datetime.now(UTC).date().isoformat()),
            )
        if query.state != "US":
            stmt = stmt.where(Listing.payload["state"].as_string() == query.state)
        if query.category != "all":
            stmt = stmt.where(Listing.payload["category"].as_string() == query.category)
        if query.source:
            stmt = stmt.where(Listing.source == query.source)
        if query.location.strip():
            location = func.lower(
                func.coalesce(Listing.payload["county"].as_string(), "")
                + " "
                + func.coalesce(Listing.payload["tract"].as_string(), "")
                + " "
                + func.coalesce(Listing.payload["title"].as_string(), "")
                + " "
                + func.coalesce(Listing.payload["location_description"].as_string(), "")
            )
            stmt = stmt.where(location.contains(query.location.strip().lower(), autoescape=True))
        acreage = Listing.payload["acres"].as_float()
        price = Listing.payload["asking_price"].as_float()
        if query.min_acres > 0:
            stmt = stmt.where(acreage >= query.min_acres)
        if query.max_price is not None:
            stmt = stmt.where(price <= query.max_price)
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        key = (
            Listing.payload["county"].as_string()
            if query.sort == "county"
            else (acreage if query.sort == "acres_desc" else price)
        )
        order = key.desc() if query.sort in {"price_desc", "acres_desc"} else key.asc()
        stmt = (
            stmt.order_by(order.nullslast(), Listing.id)
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        rows = [record_payload(item, session, account) for item in session.scalars(stmt)]
        return {
            "results": rows,
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "coverage_supported": supported,
            "sources": sources,
            "coverage_note": (
                "Partial source coverage in all 50 states. Counts reflect connected "
                "inventories, not all properties or county sales. Unknown price/acreage is "
                "excluded when that numeric filter is applied."
            ),
        }

    @app.get("/api/properties/{listing_id}")
    def detail(listing_id: str, request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings)
        item = session.get(Listing, listing_id)
        if item is None:
            raise HTTPException(404, "Property not found")
        return record_payload(item, session, account)

    def entry_payload(entry: SavedRecord, session: Session, account: Account) -> dict[str, Any]:
        value = saved_payload(session, entry)
        item = session.get(Listing, entry.listing_id) if entry.listing_id else None
        value["property"] = record_payload(item, session, account) if item else None
        return value

    @app.get("/api/saved")
    def saved_list(
        request: Request,
        session: DB,
        page: int = Query(default=1, ge=1, le=10000),
        page_size: int = Query(default=12, ge=1, le=100),
    ) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings)
        stmt = select(SavedRecord).where(SavedRecord.account_id == account.id)
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = session.scalars(
            stmt.order_by(SavedRecord.updated_at.desc(), SavedRecord.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return {
            "results": [entry_payload(row, session, account) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @app.get("/api/saved/{saved_id}")
    def saved_detail(saved_id: str, request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings)
        entry = session.get(SavedRecord, (account.id, saved_id))
        if entry is None:
            raise HTTPException(404, "Saved property not found")
        return entry_payload(entry, session, account)

    def insert_saved(session: Session, values: dict[str, Any]) -> None:
        insert = sqlite_insert if engine.dialect.name == "sqlite" else pg_insert
        session.execute(insert(SavedRecord).values(**values).on_conflict_do_nothing())

    @app.post("/api/saved")
    def create_saved(spec: SavedCreate, request: Request, session: DB) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"save:{account.id}", 60)
        if spec.listing_id and session.get(Listing, spec.listing_id) is None:
            raise HTTPException(404, "Property not found")
        saved_id = spec.listing_id or f"manual-{spec.manual_id}"
        location = spec.location.model_dump()
        insert_saved(
            session,
            {
                "account_id": account.id,
                "id": saved_id,
                "listing_id": spec.listing_id,
                "title": spec.title,
                "research_location": location,
            },
        )
        entry = session.get(SavedRecord, (account.id, saved_id))
        if entry is None:
            raise HTTPException(409, "Save changed. Reopen the property and try again.")
        if entry.title != spec.title or entry.research_location != location:
            raise HTTPException(409, "Already saved. Reopen from Saved properties before editing.")
        session.commit()
        return entry_payload(entry, session, account)

    @app.patch("/api/saved/{saved_id}")
    def update_saved(
        saved_id: str, spec: SavedUpdate, request: Request, session: DB
    ) -> dict[str, Any]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"save:{account.id}", 60)
        if session.get(SavedRecord, (account.id, saved_id)) is None:
            raise HTTPException(404, "Saved property not found")
        changed = session.execute(
            update(SavedRecord)
            .where(
                SavedRecord.account_id == account.id,
                SavedRecord.id == saved_id,
                SavedRecord.revision == spec.revision,
            )
            .values(
                title=spec.title,
                research_location=spec.location.model_dump(),
                revision=SavedRecord.revision + 1,
                updated_at=int(time.time()),
            )
            .returning(SavedRecord.id)
        ).scalar_one_or_none()
        if changed is None:
            raise HTTPException(
                409, "Changed in another tab. Reopen from Saved properties before editing."
            )
        session.commit()
        entry = session.get(SavedRecord, (account.id, saved_id))
        if entry is None:
            raise HTTPException(404, "Saved property not found")
        return entry_payload(entry, session, account)

    @app.put("/api/saved/{listing_id}")
    def save(listing_id: str, request: Request, session: DB) -> dict[str, bool]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"save:{account.id}", 60)
        item = session.get(Listing, listing_id)
        if item is None:
            raise HTTPException(404, "Property not found")
        # Repeated bookmarks must not overwrite a user's edited research location.
        insert_saved(
            session,
            {
                "account_id": account.id,
                "id": listing_id,
                "listing_id": listing_id,
                "title": PropertyRecord.model_validate(item.payload).title,
            },
        )
        session.commit()
        return {"saved": True}

    @app.delete("/api/saved/{listing_id}")
    def unsave(listing_id: str, request: Request, session: DB) -> dict[str, bool]:
        account = auth.authenticate(request, session, settings, write=True)
        auth.limit(session, f"save:{account.id}", 60)
        session.execute(
            delete(SavedRecord).where(
                SavedRecord.account_id == account.id, SavedRecord.id == listing_id
            )
        )
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
