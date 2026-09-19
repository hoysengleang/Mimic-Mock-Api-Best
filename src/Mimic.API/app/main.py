"""Mimic — API client, mock server and test runner.

Mounts three surfaces:

* ``/api/*``   the management API the UI talks to
* ``/mock/*``  the mock responder that serves configured stubs
* ``/docs``    interactive OpenAPI documentation
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import (
    collections,
    environments,
    execution,
    health,
    mocks,
    runner,
    serve,
)
from app.core.config import get_settings
from app.core.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.db.base import init_db
from app.rate_limit import limiter

logger = logging.getLogger("mimic")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()

    if settings.seed_demo_data:
        from app.db.base import session_scope
        from app.db.seed import seed

        with session_scope() as session:
            if seed(session):
                logger.info("Seeded demo data — open the app and press Send.")

    logger.info(
        "Mimic %s ready — database at %s",
        settings.app_version,
        settings.sqlalchemy_url,
    )

    yield

    # Mock hits are buffered in memory; write whatever is left before exiting
    # so a restart does not lose the counts.
    try:
        from app.db.base import session_scope
        from app.services.mock_registry import registry

        if registry.pending_hits():
            with session_scope() as session:
                registry.flush_hits(session)
    except Exception:  # noqa: BLE001 - shutdown must not raise
        logger.warning("Could not flush mock hit counts on shutdown", exc_info=True)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Design mock APIs, send real requests, assert on the responses, and "
        "run whole collections in a loop."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Mock-Id", "X-Mock-Params"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Slow down and try again shortly.",
            "limit": str(exc.detail),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    problems = [
        {
            "field": ".".join(str(part) for part in error.get("loc", ())[1:]) or "body",
            "message": error.get("msg", "Invalid value"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": "Some fields need fixing.", "problems": problems},
    )


api_prefix = settings.api_prefix
app.include_router(health.router, prefix=api_prefix)
app.include_router(collections.router, prefix=api_prefix)
app.include_router(environments.router, prefix=api_prefix)
app.include_router(mocks.router, prefix=api_prefix)
app.include_router(execution.router, prefix=api_prefix)
app.include_router(runner.router, prefix=api_prefix)
app.include_router(serve.router)


@app.get("/", tags=["meta"], summary="Service metadata")
def root() -> dict[str, object]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": api_prefix,
        "mock_base": "/mock",
    }
