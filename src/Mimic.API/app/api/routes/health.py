"""Liveness and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import AppSettings, DbSession
from app.db.models import Collection, Environment, Mock, SavedRequest

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe including the database")
def readiness(db: DbSession, settings: AppSettings) -> dict[str, object]:
    """Verify the database is reachable and report what is stored."""
    try:
        counts = {
            "collections": db.scalar(select(func.count()).select_from(Collection)) or 0,
            "requests": db.scalar(select(func.count()).select_from(SavedRequest)) or 0,
            "environments": db.scalar(select(func.count()).select_from(Environment)) or 0,
            "mocks": db.scalar(select(func.count()).select_from(Mock)) or 0,
        }
    except Exception as exc:  # noqa: BLE001 - readiness must never raise
        return {"status": "degraded", "database": "unavailable", "detail": str(exc)}

    return {
        "status": "ok",
        "database": "ok",
        "version": settings.app_version,
        "counts": counts,
    }
