"""The collection test runner.

Executes every request in a collection, optionally looping N times, and
aggregates assertion outcomes into a single pass/fail report. Looping is what
makes this useful beyond a one-shot send: it surfaces flaky endpoints,
intermittent timeouts, and rate-limit thresholds that a single request hides.
"""

from __future__ import annotations

import asyncio
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Collection, Environment, SavedRequest, TestRun
from app.schemas.common import Assertion, AuthConfig, KeyValue
from app.schemas.execution import ExecuteRequest
from app.schemas.runner import RunRequest, RunStepResult
from app.services import executor
from app.services.interpolate import build_context


class RunnerError(ValueError):
    """Raised when a run cannot be started."""


def _to_execute_request(
    saved: SavedRequest, run: RunRequest, *, save_history: bool
) -> ExecuteRequest:
    return ExecuteRequest(
        name=saved.name,
        request_id=saved.id,
        method=saved.method,
        url=saved.url,
        headers=[KeyValue(**row) for row in (saved.headers or [])],
        query_params=[KeyValue(**row) for row in (saved.query_params or [])],
        body_mode=saved.body_mode,
        body=saved.body or "",
        form_data=[KeyValue(**row) for row in (saved.form_data or [])],
        auth=AuthConfig(**(saved.auth or {})),
        assertions=[Assertion(**row) for row in (saved.assertions or [])],
        environment_id=run.environment_id,
        timeout_seconds=run.timeout_seconds,
        save_history=save_history,
    )


def resolve_context(session: Session, environment_id: str | None) -> dict[str, str]:
    """Build the variable context, falling back to the active environment."""
    environment: Environment | None = None

    if environment_id:
        environment = session.get(Environment, environment_id)
        if environment is None:
            raise RunnerError(f"Environment '{environment_id}' was not found.")
    else:
        environment = session.scalars(
            select(Environment).where(Environment.is_active.is_(True))
        ).first()

    if environment is None:
        return {}
    return build_context(list(environment.variables or []))


async def run_collection(
    session: Session, run: RunRequest, settings: Settings
) -> TestRun:
    """Execute a collection and persist the aggregate result."""
    collection = session.get(Collection, run.collection_id)
    if collection is None:
        raise RunnerError(f"Collection '{run.collection_id}' was not found.")

    if run.iterations > settings.runner_max_iterations:
        raise RunnerError(
            f"iterations may not exceed {settings.runner_max_iterations}."
        )

    requests = list(
        session.scalars(
            select(SavedRequest)
            .where(SavedRequest.collection_id == collection.id)
            .order_by(SavedRequest.position, SavedRequest.created_at)
        )
    )
    runnable = [item for item in requests if (item.url or "").strip()]

    if not runnable:
        raise RunnerError(
            "This collection has no requests with a URL set, so there is "
            "nothing to run."
        )

    planned = len(runnable) * run.iterations
    if planned > settings.runner_max_requests_per_run:
        raise RunnerError(
            f"That would send {planned} requests, over the "
            f"{settings.runner_max_requests_per_run} limit for a single run. "
            "Reduce the iteration count or split the collection."
        )

    context = resolve_context(session, run.environment_id)

    results: list[RunStepResult] = []
    passed = failed = total_assertions = 0
    started = time.perf_counter()
    stop = False

    for iteration in range(1, run.iterations + 1):
        if stop:
            break

        for saved in runnable:
            execute_request = _to_execute_request(
                saved, run, save_history=run.save_history
            )
            response = await executor.execute(execute_request, context, settings)

            total_assertions += len(response.assertion_results)
            passed += response.assertions_passed
            failed += response.assertions_failed

            step_ok = response.ok and response.assertions_failed == 0

            results.append(
                RunStepResult(
                    iteration=iteration,
                    request_id=saved.id,
                    name=saved.name,
                    method=execute_request.method,
                    url=response.final_url or execute_request.url,
                    ok=step_ok,
                    status_code=response.status_code,
                    duration_ms=response.duration_ms,
                    size_bytes=response.size_bytes,
                    error=response.error,
                    assertion_results=response.assertion_results,
                    assertions_passed=response.assertions_passed,
                    assertions_failed=response.assertions_failed,
                )
            )

            if not step_ok and run.stop_on_failure:
                stop = True
                break

            if run.delay_ms:
                await asyncio.sleep(run.delay_ms / 1000)

    duration_ms = (time.perf_counter() - started) * 1000
    any_failed = failed > 0 or any(not step.ok for step in results)

    test_run = TestRun(
        collection_id=collection.id,
        collection_name=collection.name,
        environment_id=run.environment_id,
        iterations=run.iterations,
        total_requests=len(results),
        total_assertions=total_assertions,
        passed=passed,
        failed=failed,
        duration_ms=round(duration_ms, 2),
        status="failed" if any_failed else "passed",
        results=[step.model_dump(mode="json") for step in results],
    )

    session.add(test_run)
    session.commit()
    session.refresh(test_run)
    return test_run
