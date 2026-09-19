"""CRUD for mock endpoint definitions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, update

from app.api.deps import DbSession
from app.db.models import Mock
from app.schemas.mock import MockCreate, MockOut, MockUpdate
from app.services.mock_registry import registry

router = APIRouter(prefix="/mocks", tags=["mocks"])


def _sync_hits(db: DbSession) -> None:
    """Write buffered hit counts so reads report current numbers."""
    registry.flush_hits(db)


def _get(db: DbSession, mock_id: str) -> Mock:
    mock = db.get(Mock, mock_id)
    if mock is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mock not found")
    return mock


def _assert_unique(
    db: DbSession, path: str, method: str, *, exclude_id: str | None = None
) -> None:
    """Reject an exact duplicate of path+method, which is always a mistake."""
    statement = select(Mock).where(Mock.path == path, Mock.method == method)
    if exclude_id:
        statement = statement.where(Mock.id != exclude_id)
    if db.scalars(statement).first() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A mock for {method} {path} already exists. "
            "Edit that one, or give this a different path.",
        )


@router.get("", response_model=list[MockOut])
def list_mocks(
    db: DbSession,
    enabled_only: bool = Query(False, description="Return only enabled mocks."),
    search: str = Query("", max_length=200),
) -> list[Mock]:
    _sync_hits(db)
    statement = select(Mock).order_by(Mock.priority.desc(), Mock.path)
    if enabled_only:
        statement = statement.where(Mock.is_enabled.is_(True))
    if search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(Mock.path.ilike(pattern) | Mock.name.ilike(pattern))
    return list(db.scalars(statement))


@router.post("", response_model=MockOut, status_code=status.HTTP_201_CREATED)
def create_mock(payload: MockCreate, db: DbSession) -> Mock:
    _assert_unique(db, payload.path, payload.method)
    mock = Mock(**payload.model_dump())
    db.add(mock)
    db.commit()
    db.refresh(mock)
    registry.invalidate()
    return mock


@router.get("/{mock_id}", response_model=MockOut)
def get_mock(mock_id: str, db: DbSession) -> Mock:
    _sync_hits(db)
    return _get(db, mock_id)


@router.patch("/{mock_id}", response_model=MockOut)
@router.put("/{mock_id}", response_model=MockOut)
def update_mock(mock_id: str, payload: MockUpdate, db: DbSession) -> Mock:
    mock = _get(db, mock_id)
    data = payload.model_dump(exclude_unset=True)

    new_path = data.get("path", mock.path)
    new_method = data.get("method", mock.method)
    if new_path != mock.path or new_method != mock.method:
        _assert_unique(db, new_path, new_method, exclude_id=mock_id)

    for field, value in data.items():
        setattr(mock, field, value)
    db.commit()
    db.refresh(mock)
    registry.invalidate()
    return mock


@router.delete("/{mock_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mock(mock_id: str, db: DbSession) -> None:
    db.delete(_get(db, mock_id))
    db.commit()
    registry.invalidate()


@router.post("/{mock_id}/toggle", response_model=MockOut)
def toggle_mock(mock_id: str, db: DbSession) -> Mock:
    mock = _get(db, mock_id)
    mock.is_enabled = not mock.is_enabled
    db.commit()
    db.refresh(mock)
    registry.invalidate()
    return mock


@router.post("/reset-hits", status_code=status.HTTP_204_NO_CONTENT)
def reset_hit_counts(db: DbSession) -> None:
    # Drop anything buffered too, or it would be written back after the reset.
    registry.reset()
    db.execute(update(Mock).values(hit_count=0, last_hit_at=None))
    db.commit()
