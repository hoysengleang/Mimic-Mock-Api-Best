"""CRUD for collections, folders and saved requests."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.db.models import Collection, Folder, SavedRequest
from app.schemas.collection import (
    CollectionCreate,
    CollectionDetail,
    CollectionOut,
    CollectionUpdate,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    SavedRequestCreate,
    SavedRequestOut,
    SavedRequestUpdate,
)

router = APIRouter(tags=["collections"])


def _dump(value: Any) -> Any:
    """Convert pydantic models inside a payload to plain JSON-safe data."""
    if isinstance(value, list):
        return [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _get_collection(db: DbSession, collection_id: str) -> Collection:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    return collection


def _get_request(db: DbSession, request_id: str) -> SavedRequest:
    saved = db.get(SavedRequest, request_id)
    if saved is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    return saved


def _next_position(db: DbSession, model: Any, **filters: Any) -> int:
    statement = select(func.max(model.position))
    for field, value in filters.items():
        statement = statement.where(getattr(model, field) == value)
    return int(db.scalar(statement) or 0) + 1


# --- Collections ------------------------------------------------------------


@router.get(
    "/collections",
    response_model=list[CollectionDetail],
    summary="List every collection with its contents",
)
def list_collections(db: DbSession) -> list[Collection]:
    """Return all collections, folders and requests in one call.

    Always includes contents, and eager-loads both relations. A union
    response model was tried here and removed: Pydantic evaluates every
    member of a union, which re-triggered the lazy loads this is meant to
    avoid and made the endpoint six times slower.
    """
    return list(
        db.scalars(
            select(Collection)
            .order_by(Collection.position, Collection.created_at)
            .options(
                selectinload(Collection.folders),
                selectinload(Collection.requests),
            )
        )
    )


@router.post(
    "/collections", response_model=CollectionOut, status_code=status.HTTP_201_CREATED
)
def create_collection(payload: CollectionCreate, db: DbSession) -> Collection:
    collection = Collection(
        name=payload.name,
        description=payload.description,
        position=payload.position or _next_position(db, Collection),
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


@router.get("/collections/{collection_id}", response_model=CollectionDetail)
def get_collection(collection_id: str, db: DbSession) -> Collection:
    collection = db.scalars(
        select(Collection)
        .where(Collection.id == collection_id)
        .options(
            selectinload(Collection.folders),
            selectinload(Collection.requests),
        )
    ).first()
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    return collection


@router.patch("/collections/{collection_id}", response_model=CollectionOut)
def update_collection(
    collection_id: str, payload: CollectionUpdate, db: DbSession
) -> Collection:
    collection = _get_collection(db, collection_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(collection, field, value)
    db.commit()
    db.refresh(collection)
    return collection


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: str, db: DbSession) -> None:
    db.delete(_get_collection(db, collection_id))
    db.commit()


# --- Folders ----------------------------------------------------------------


@router.post(
    "/collections/{collection_id}/folders",
    response_model=FolderOut,
    status_code=status.HTTP_201_CREATED,
)
def create_folder(
    collection_id: str, payload: FolderCreate, db: DbSession
) -> Folder:
    _get_collection(db, collection_id)

    if payload.parent_id:
        parent = db.get(Folder, payload.parent_id)
        if parent is None or parent.collection_id != collection_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Parent folder does not exist in this collection",
            )

    folder = Folder(
        collection_id=collection_id,
        name=payload.name,
        parent_id=payload.parent_id,
        position=payload.position
        or _next_position(db, Folder, collection_id=collection_id),
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@router.patch("/folders/{folder_id}", response_model=FolderOut)
def update_folder(folder_id: str, payload: FolderUpdate, db: DbSession) -> Folder:
    folder = db.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found")

    data = payload.model_dump(exclude_unset=True)

    if "parent_id" in data and data["parent_id"]:
        if data["parent_id"] == folder_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "A folder cannot be its own parent"
            )
        parent = db.get(Folder, data["parent_id"])
        if parent is None or parent.collection_id != folder.collection_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Parent folder does not exist in this collection",
            )
        # Walk up the chain so a move cannot create a cycle.
        cursor = parent
        seen = {folder_id}
        while cursor is not None:
            if cursor.id in seen:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "That move would create a circular folder structure",
                )
            seen.add(cursor.id)
            cursor = db.get(Folder, cursor.parent_id) if cursor.parent_id else None

    for field, value in data.items():
        setattr(folder, field, value)
    db.commit()
    db.refresh(folder)
    return folder


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(folder_id: str, db: DbSession) -> None:
    folder = db.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found")
    db.delete(folder)
    db.commit()


# --- Saved requests ---------------------------------------------------------


@router.post(
    "/collections/{collection_id}/requests",
    response_model=SavedRequestOut,
    status_code=status.HTTP_201_CREATED,
)
def create_request(
    collection_id: str, payload: SavedRequestCreate, db: DbSession
) -> SavedRequest:
    _get_collection(db, collection_id)

    if payload.folder_id:
        folder = db.get(Folder, payload.folder_id)
        if folder is None or folder.collection_id != collection_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Folder does not exist in this collection",
            )

    saved = SavedRequest(
        collection_id=collection_id,
        name=payload.name,
        description=payload.description,
        method=payload.method,
        url=payload.url,
        headers=_dump(payload.headers),
        query_params=_dump(payload.query_params),
        body_mode=payload.body_mode.value,
        body=payload.body,
        form_data=_dump(payload.form_data),
        auth=_dump(payload.auth),
        assertions=_dump(payload.assertions),
        folder_id=payload.folder_id,
        position=payload.position
        or _next_position(db, SavedRequest, collection_id=collection_id),
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.get("/requests/{request_id}", response_model=SavedRequestOut)
def get_request(request_id: str, db: DbSession) -> SavedRequest:
    return _get_request(db, request_id)


@router.patch("/requests/{request_id}", response_model=SavedRequestOut)
def update_request(
    request_id: str, payload: SavedRequestUpdate, db: DbSession
) -> SavedRequest:
    saved = _get_request(db, request_id)
    data = payload.model_dump(exclude_unset=True, mode="json")

    if data.get("folder_id"):
        folder = db.get(Folder, data["folder_id"])
        if folder is None or folder.collection_id != saved.collection_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Folder does not exist in this collection",
            )

    for field, value in data.items():
        setattr(saved, field, value)
    db.commit()
    db.refresh(saved)
    return saved


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(request_id: str, db: DbSession) -> None:
    db.delete(_get_request(db, request_id))
    db.commit()


@router.post(
    "/requests/{request_id}/duplicate",
    response_model=SavedRequestOut,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_request(request_id: str, db: DbSession) -> SavedRequest:
    source = _get_request(db, request_id)
    clone = SavedRequest(
        collection_id=source.collection_id,
        folder_id=source.folder_id,
        name=f"{source.name} (copy)",
        description=source.description,
        method=source.method,
        url=source.url,
        headers=list(source.headers or []),
        query_params=list(source.query_params or []),
        body_mode=source.body_mode,
        body=source.body,
        form_data=list(source.form_data or []),
        auth=dict(source.auth or {}),
        assertions=list(source.assertions or []),
        position=_next_position(db, SavedRequest, collection_id=source.collection_id),
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone
