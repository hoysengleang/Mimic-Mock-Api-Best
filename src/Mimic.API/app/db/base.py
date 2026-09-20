from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _is_memory(url: str) -> bool:
    if not _is_sqlite(url):
        return False
    if ":memory:" in url or "mode=memory" in url:
        return True
    _, _, path = url.partition("///")
    return path == "" or url in ("sqlite://", "sqlite+pysqlite://")


@event.listens_for(Engine, "connect")
def _configure_sqlite(dbapi_connection: Any, connection_record: Any) -> None:
    if type(dbapi_connection).__module__.split(".")[0] != "sqlite3":
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def build_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    url = settings.sqlalchemy_url

    kwargs: dict[str, Any] = {"echo": settings.debug, "future": True}
    if _is_sqlite(url):
        kwargs["connect_args"] = {"check_same_thread": False}
        if _is_memory(url):
            kwargs["poolclass"] = StaticPool
        else:
            settings.data_dir.mkdir(parents=True, exist_ok=True)

    return create_engine(url, **kwargs)


_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = build_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False
        )
    return _SessionFactory


def init_db(engine: Engine | None = None) -> None:
    """Create every table. Safe to call repeatedly."""
    from app.db import models  # noqa: F401  (import registers the models)

    Base.metadata.create_all(bind=engine or get_engine())


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope for use outside the request cycle."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Drop cached engine/session factory. Used by tests."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None
