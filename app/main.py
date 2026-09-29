"""Local Issue Tracker application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api import router
from app.database import (
    create_db_engine,
    create_session_factory,
    ensure_sqlite_parent,
    resolve_database_url,
)
from app.models import Base
from app.openapi_docs import apply_field_descriptions
from app.seed import seed_if_empty

STATIC_DIR = Path(__file__).resolve().parent / "static"
LOCAL_SERVER = "http://127.0.0.1:8000"


def create_app(database_url: str | None = None) -> FastAPI:
    url = resolve_database_url(database_url)
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ensure_sqlite_parent(url)
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            seed_if_empty(session)
        yield
        engine.dispose()

    app = FastAPI(
        title="Local Issue Tracker",
        summary="Localhost CRUD API for issues.",
        description=(
            "Local issue tracker. The process binds to 127.0.0.1 and stores issues in SQLite. "
            "GET /api/issues returns every issue, newest first. "
            "POST /api/issues creates an issue. "
            "PATCH /api/issues/{issue_id} changes only the fields present in the body. "
            "DELETE /api/issues/{issue_id} returns 204 when the row is removed."
        ),
        version="1.0.0",
        license_info={"name": "MIT"},
        servers=[
            {
                "url": LOCAL_SERVER,
                "description": "This application on localhost. It is not reachable from other machines.",
            }
        ],
        openapi_tags=[
            {
                "name": "issues",
                "description": "Create, read, update, and delete issues in the local SQLite database.",
            }
        ],
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    _install_openapi(app)

    @app.middleware("http")
    async def no_store(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith("/api/") or path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


def _install_openapi(app: FastAPI) -> None:
    def openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
            license_info=app.license_info,
        )
        apply_field_descriptions(schema)
        app.openapi_schema = schema
        return schema

    app.openapi = openapi  # type: ignore[method-assign]


app = create_app()
