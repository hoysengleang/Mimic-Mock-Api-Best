"""Sending requests, and the history of what was sent."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import delete, func, select

from app.api.deps import AppSettings, DbSession
from app.core.config import Settings
from app.core.security import redact_headers
from app.db.models import HistoryEntry
from app.schemas.execution import (
    ExecuteRequest,
    ExecuteResponse,
    HistoryOut,
    HistoryPage,
)
from app.services import executor
from app.services.runner import RunnerError, resolve_context
from app.rate_limit import limiter, send_limit

router = APIRouter(tags=["execution"])


def _record_history(
    db: DbSession,
    request: ExecuteRequest,
    prepared_url: str,
    prepared_headers: dict[str, str],
    response: ExecuteResponse,
    settings: Settings,
) -> str | None:
    """Persist one execution, redacting credentials and capping body size."""
    cap = settings.history_max_body_bytes

    request_body = request.body or ""
    response_body = response.body or ""
    truncated = response.truncated

    if len(request_body) > cap:
        request_body = request_body[:cap]
        truncated = True
    if len(response_body) > cap:
        response_body = response_body[:cap]
        truncated = True

    entry = HistoryEntry(
        request_id=request.request_id,
        name=request.name or "",
        method=request.method,
        url=prepared_url,
        status_code=response.status_code,
        duration_ms=response.duration_ms,
        response_size=response.size_bytes,
        request_headers=redact_headers(prepared_headers),
        request_body=request_body,
        response_headers=redact_headers(response.headers),
        response_body=response_body,
        truncated=truncated,
        error=response.error,
        assertion_results=[r.model_dump(mode="json") for r in response.assertion_results],
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    _trim_history(db, settings.history_max_entries)
    return entry.id


def _trim_history(db: DbSession, keep: int) -> None:
    """Keep history bounded so the database cannot grow without limit."""
    total = db.scalar(select(func.count()).select_from(HistoryEntry)) or 0
    if total <= keep:
        return

    cutoff = db.scalars(
        select(HistoryEntry.created_at)
        .order_by(HistoryEntry.created_at.desc())
        .offset(keep)
        .limit(1)
    ).first()
    if cutoff is None:
        return

    db.execute(delete(HistoryEntry).where(HistoryEntry.created_at < cutoff))
    db.commit()


@router.post("/send", response_model=ExecuteResponse, summary="Send one request")
@limiter.limit(send_limit)
async def send_request(
    request: Request,
    payload: ExecuteRequest,
    db: DbSession,
    settings: AppSettings,
) -> ExecuteResponse:
    """Execute a request server-side and return the full response.

    Running server-side is what lets Mimic call APIs the browser cannot --
    no CORS preflight, no mixed-content blocking -- and measure true timings.
    """
    try:
        context = resolve_context(db, payload.environment_id)
    except RunnerError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    prepared = executor.prepare(payload, context)
    response = await executor.execute(payload, context, settings)

    if payload.save_history:
        response.history_id = _record_history(
            db, payload, prepared.url, prepared.headers, response, settings
        )

    return response


@router.get("/history", response_model=HistoryPage, summary="List past executions")
def list_history(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    request_id: str | None = Query(None),
) -> HistoryPage:
    statement = select(HistoryEntry)
    count_statement = select(func.count()).select_from(HistoryEntry)

    if request_id:
        statement = statement.where(HistoryEntry.request_id == request_id)
        count_statement = count_statement.where(HistoryEntry.request_id == request_id)

    total = db.scalar(count_statement) or 0
    items = list(
        db.scalars(
            statement.order_by(HistoryEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )

    return HistoryPage(
        total=total,
        limit=limit,
        offset=offset,
        items=[HistoryOut.model_validate(item) for item in items],
    )


@router.get("/history/{entry_id}", response_model=HistoryOut)
def get_history_entry(entry_id: str, db: DbSession) -> HistoryEntry:
    entry = db.get(HistoryEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "History entry not found")
    return entry


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(db: DbSession) -> None:
    db.execute(delete(HistoryEntry))
    db.commit()


@router.delete("/history/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_entry(entry_id: str, db: DbSession) -> None:
    entry = db.get(HistoryEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "History entry not found")
    db.delete(entry)
    db.commit()
