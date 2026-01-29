from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.deps import get_store
from app.db.store import MockStore
from app.schemas.mock import MockCreate, MockDefinition, MockUpdate

router = APIRouter(prefix="/mocks", tags=["mocks"])
mock_router = APIRouter(tags=["mocks"])


@router.get("", response_model=list[MockDefinition])
def list_mocks(store: MockStore = Depends(get_store)) -> list[MockDefinition]:
    return store.list()


@router.post("", response_model=MockDefinition, status_code=201)
def create_mock(payload: MockCreate, store: MockStore = Depends(get_store)) -> MockDefinition:
    return store.create(payload)


@router.get("/{mock_id}", response_model=MockDefinition)
def get_mock(mock_id: str, store: MockStore = Depends(get_store)) -> MockDefinition:
    mock = store.get(mock_id)
    if not mock:
        raise HTTPException(status_code=404, detail="Mock not found")
    return mock


@router.put("/{mock_id}", response_model=MockDefinition)
def update_mock(
    mock_id: str,
    payload: MockUpdate,
    store: MockStore = Depends(get_store),
) -> MockDefinition:
    mock = store.update(mock_id, payload)
    if not mock:
        raise HTTPException(status_code=404, detail="Mock not found")
    return mock


@router.delete("/{mock_id}", status_code=204)
def delete_mock(mock_id: str, store: MockStore = Depends(get_store)) -> None:
    if not store.delete(mock_id):
        raise HTTPException(status_code=404, detail="Mock not found")


@mock_router.api_route(
    "/mock/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def serve_mock(
    full_path: str,
    request: Request,
    store: MockStore = Depends(get_store),
) -> JSONResponse:
    path = f"/{full_path}"
    mock = store.find_match(path, request.method)
    if not mock:
        raise HTTPException(status_code=404, detail="Mock not found")
    if mock.delay > 0:
        await asyncio.sleep(mock.delay)
    return JSONResponse(content=mock.response, status_code=mock.status_code)
