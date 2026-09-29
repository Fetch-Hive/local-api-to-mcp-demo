"""SQLite engine and per-request sessions."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./data/issues.db"


def resolve_database_url(database_url: str | None = None) -> str:
    if database_url is not None:
        return database_url
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def ensure_sqlite_parent(database_url: str) -> None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return
    location = database_url[len(prefix) :]
    if location in {":memory:", ""} or location.startswith("file:"):
        return
    parent = Path(location).expanduser().parent
    if parent != Path("."):
        parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(database_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()
