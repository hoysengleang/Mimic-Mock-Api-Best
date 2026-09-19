"""CRUD for environments and their variables."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from app.api.deps import DbSession
from app.db.models import Environment
from app.schemas.environment import (
    EnvironmentCreate,
    EnvironmentOut,
    EnvironmentUpdate,
)

router = APIRouter(prefix="/environments", tags=["environments"])


def _get(db: DbSession, environment_id: str) -> Environment:
    environment = db.get(Environment, environment_id)
    if environment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Environment not found")
    return environment


def _deactivate_others(db: DbSession, keep_id: str) -> None:
    db.execute(
        update(Environment)
        .where(Environment.id != keep_id)
        .values(is_active=False)
    )


@router.get("", response_model=list[EnvironmentOut])
def list_environments(db: DbSession) -> list[Environment]:
    return list(db.scalars(select(Environment).order_by(Environment.created_at)))


@router.post("", response_model=EnvironmentOut, status_code=status.HTTP_201_CREATED)
def create_environment(payload: EnvironmentCreate, db: DbSession) -> Environment:
    environment = Environment(
        name=payload.name,
        is_active=payload.is_active,
        variables=[v.model_dump(mode="json") for v in payload.variables],
    )
    db.add(environment)
    db.flush()
    if payload.is_active:
        _deactivate_others(db, environment.id)
    db.commit()
    db.refresh(environment)
    return environment


@router.get("/{environment_id}", response_model=EnvironmentOut)
def get_environment(environment_id: str, db: DbSession) -> Environment:
    return _get(db, environment_id)


@router.patch("/{environment_id}", response_model=EnvironmentOut)
def update_environment(
    environment_id: str, payload: EnvironmentUpdate, db: DbSession
) -> Environment:
    environment = _get(db, environment_id)
    data = payload.model_dump(exclude_unset=True, mode="json")

    for field, value in data.items():
        setattr(environment, field, value)

    if data.get("is_active"):
        _deactivate_others(db, environment.id)

    db.commit()
    db.refresh(environment)
    return environment


@router.post("/{environment_id}/activate", response_model=EnvironmentOut)
def activate_environment(environment_id: str, db: DbSession) -> Environment:
    """Make this the one active environment."""
    environment = _get(db, environment_id)
    environment.is_active = True
    _deactivate_others(db, environment.id)
    db.commit()
    db.refresh(environment)
    return environment


@router.post("/deactivate-all", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_all(db: DbSession) -> None:
    db.execute(update(Environment).values(is_active=False))
    db.commit()


@router.delete("/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_environment(environment_id: str, db: DbSession) -> None:
    db.delete(_get(db, environment_id))
    db.commit()
