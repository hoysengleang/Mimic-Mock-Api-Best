"""The mock responder.

Everything under ``/mock/*`` is matched against the stored mock definitions
and served back. This router is mounted without the API prefix so a mock
registered at ``/api/users`` is reachable at ``/mock/api/users``.

Definitions come from :mod:`app.services.mock_registry` rather than straight
from the database — see that module for why.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.deps import DbSession
from app.services.matcher import find_best_match
from app.services.mock_registry import registry

router = APIRouter(prefix="/mock", tags=["mock server"])

# Hop-by-hop headers a mock must not be allowed to set on the real response.
FORBIDDEN_RESPONSE_HEADERS = frozenset(
    {
        "content-length",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "upgrade",
        "te",
        "trailer",
        "proxy-authenticate",
    }
)


async def serve_mock(full_path: str, request: Request, db: DbSession) -> Response:
    path = "/" + full_path.strip("/")

    mocks = registry.snapshot(db)
    match = find_best_match(mocks, path, request.method)

    if match is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"No mock is configured for {request.method} {path}.",
                "hint": "Create one in the Mocks tab, and check that it is enabled.",
            },
        )

    mock, result = match

    if mock.delay > 0:
        await asyncio.sleep(min(mock.delay, 60))

    # Counted in memory; written in bulk once the buffer fills.
    if registry.record_hit(mock.id):
        await asyncio.to_thread(registry.flush_hits, db)

    headers = {
        key: value
        for key, value in mock.response_headers.items()
        if key.lower() not in FORBIDDEN_RESPONSE_HEADERS
    }
    if result.params:
        headers["X-Mock-Params"] = json.dumps(result.params)
    headers["X-Mock-Id"] = mock.id

    content_type = mock.content_type or "application/json"
    payload = mock.response

    if "json" in content_type.lower():
        return JSONResponse(
            status_code=mock.status_code,
            content=payload,
            headers=headers,
            media_type=content_type,
        )

    body = payload if isinstance(payload, str) else json.dumps(payload)
    return Response(
        content=body,
        status_code=mock.status_code,
        headers=headers,
        media_type=content_type,
    )


# Registered one method at a time so each gets a distinct OpenAPI operation id.
# A single multi-method `api_route` would emit duplicates and warn on startup.
for _method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
    router.add_api_route(
        "/{full_path:path}",
        serve_mock,
        methods=[_method],
        operation_id=f"serve_mock_{_method.lower()}",
        summary=f"Serve a configured mock ({_method})",
    )
