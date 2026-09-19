"""Running a whole collection, optionally in a loop."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import delete, func, select

from app.api.deps import AppSettings, DbSession
from app.db.models import TestRun
from app.rate_limit import limiter, run_limit
from app.schemas.runner import RunPage, RunRequest, RunResult, RunSummary
from app.services import runner as runner_service
from app.services.runner import RunnerError

router = APIRouter(tags=["runner"])


@router.post("/run", response_model=RunResult, summary="Run a collection")
@limiter.limit(run_limit)
async def run_collection(
    request: Request,
    payload: RunRequest,
    db: DbSession,
    settings: AppSettings,
) -> TestRun:
    """Execute every request in a collection and report pass/fail.

    Set ``iterations`` above 1 to loop the whole collection, which is how you
    catch flaky endpoints and intermittent timeouts that a single pass hides.
    """
    try:
        return await runner_service.run_collection(db, payload, settings)
    except RunnerError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/runs", response_model=RunPage, summary="List past runs")
def list_runs(
    db: DbSession,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    collection_id: str | None = Query(None),
) -> RunPage:
    statement = select(TestRun)
    count_statement = select(func.count()).select_from(TestRun)

    if collection_id:
        statement = statement.where(TestRun.collection_id == collection_id)
        count_statement = count_statement.where(TestRun.collection_id == collection_id)

    total = db.scalar(count_statement) or 0
    items = list(
        db.scalars(
            statement.order_by(TestRun.created_at.desc()).offset(offset).limit(limit)
        )
    )

    return RunPage(
        total=total,
        limit=limit,
        offset=offset,
        items=[RunSummary.model_validate(item) for item in items],
    )


@router.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str, db: DbSession) -> TestRun:
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return run


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, db: DbSession) -> None:
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    db.delete(run)
    db.commit()


@router.delete("/runs", status_code=status.HTTP_204_NO_CONTENT)
def clear_runs(db: DbSession) -> None:
    db.execute(delete(TestRun))
    db.commit()
