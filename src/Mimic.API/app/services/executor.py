"""The outbound request engine.

Requests are sent from the server rather than the browser. That is what lets
Mimic reach APIs the browser could not (no CORS preflight, no mixed-content
block) and measure real timings -- but it also means every URL here is
attacker-influenced, so each one, including every redirect hop, passes through
the SSRF policy in :mod:`app.core.security`.

Redirects are followed manually for exactly that reason: httpx's built-in
``follow_redirects`` would chase a 302 into ``169.254.169.254`` without ever
consulting our policy.
"""

from __future__ import annotations

import base64
import json
import time
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

from app.core.config import Settings
from app.core.security import OutboundRequestBlocked, validate_outbound_url
from app.schemas.common import ApiKeyLocation, AuthType, BodyMode
from app.schemas.execution import ExecuteRequest, ExecuteResponse, RedirectHop
from app.services import assertions as assertion_service
from app.services.interpolate import interpolate, interpolate_pairs

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

STATUS_TEXT = {
    200: "OK", 201: "Created", 202: "Accepted", 204: "No Content",
    301: "Moved Permanently", 302: "Found", 303: "See Other",
    304: "Not Modified", 307: "Temporary Redirect", 308: "Permanent Redirect",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 408: "Request Timeout",
    409: "Conflict", 413: "Payload Too Large", 415: "Unsupported Media Type",
    422: "Unprocessable Entity", 429: "Too Many Requests",
    500: "Internal Server Error", 502: "Bad Gateway",
    503: "Service Unavailable", 504: "Gateway Timeout",
}

CONTENT_TYPES = {
    BodyMode.JSON: "application/json",
    BodyMode.XML: "application/xml",
    BodyMode.TEXT: "text/plain",
}


class PreparedRequest:
    """A fully resolved request, ready to send."""

    def __init__(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        content: bytes | None,
        data: dict[str, str] | None,
        missing_variables: set[str],
    ) -> None:
        self.method = method
        self.url = url
        self.headers = headers
        self.content = content
        self.data = data
        self.missing_variables = missing_variables


def _apply_query_params(url: str, params: list[tuple[str, str]]) -> str:
    if not params:
        return url
    parts = urlparse(url)
    existing = parts.query
    encoded = httpx.QueryParams(params).__str__()
    query = f"{existing}&{encoded}" if existing else encoded
    return urlunparse(parts._replace(query=query))


def prepare(request: ExecuteRequest, context: dict[str, str]) -> PreparedRequest:
    """Interpolate variables, apply auth, and assemble the outbound request."""
    missing: set[str] = set()

    url_result = interpolate(request.url.strip(), context)
    missing |= url_result.missing
    url = url_result.text

    if "://" not in url:
        url = f"http://{url.lstrip('/')}"

    header_pairs, header_missing = interpolate_pairs(
        [h.model_dump() for h in request.headers], context
    )
    query_pairs, query_missing = interpolate_pairs(
        [q.model_dump() for q in request.query_params], context
    )
    missing |= header_missing | query_missing

    headers = {key: value for key, value in header_pairs}

    # --- Auth ---------------------------------------------------------------
    auth = request.auth
    if auth.type == AuthType.BEARER:
        token = interpolate(auth.token, context)
        missing |= token.missing
        if token.text:
            headers["Authorization"] = f"Bearer {token.text}"
    elif auth.type == AuthType.BASIC:
        username = interpolate(auth.username, context)
        password = interpolate(auth.password, context)
        missing |= username.missing | password.missing
        raw = f"{username.text}:{password.text}".encode()
        headers["Authorization"] = f"Basic {base64.b64encode(raw).decode()}"
    elif auth.type == AuthType.API_KEY:
        key = interpolate(auth.key, context)
        value = interpolate(auth.value, context)
        missing |= key.missing | value.missing
        if key.text:
            if auth.add_to == ApiKeyLocation.QUERY:
                query_pairs.append((key.text, value.text))
            else:
                headers[key.text] = value.text

    url = _apply_query_params(url, query_pairs)

    # --- Body ---------------------------------------------------------------
    content: bytes | None = None
    data: dict[str, str] | None = None

    if request.body_mode == BodyMode.FORM:
        form_pairs, form_missing = interpolate_pairs(
            [f.model_dump() for f in request.form_data], context
        )
        missing |= form_missing
        data = dict(form_pairs)
    elif request.body_mode != BodyMode.NONE and request.body:
        body_result = interpolate(request.body, context)
        missing |= body_result.missing
        content = body_result.text.encode("utf-8")
        default_type = CONTENT_TYPES.get(request.body_mode)
        if default_type and not any(
            key.lower() == "content-type" for key in headers
        ):
            headers["Content-Type"] = default_type

    return PreparedRequest(
        method=request.method.upper(),
        url=url,
        headers=headers,
        content=content,
        data=data,
        missing_variables=missing,
    )


async def _read_capped(response: httpx.Response, max_bytes: int) -> tuple[bytes, bool]:
    """Read a response body, stopping once *max_bytes* is exceeded."""
    chunks: list[bytes] = []
    total = 0
    truncated = False

    async for chunk in response.aiter_bytes():
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            truncated = True
            break

    body = b"".join(chunks)
    if truncated:
        body = body[:max_bytes]
    return body, truncated


def _decode(body: bytes, response: httpx.Response) -> str:
    encoding = response.charset_encoding or "utf-8"
    try:
        return body.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return body.decode("utf-8", errors="replace")


async def execute(
    request: ExecuteRequest,
    context: dict[str, str],
    settings: Settings,
) -> ExecuteResponse:
    """Send one request and evaluate its assertions."""
    prepared = prepare(request, context)

    timeout = request.timeout_seconds or settings.executor_timeout_seconds
    max_bytes = settings.executor_max_response_bytes
    blocked = tuple(settings.blocked_hosts)

    redirects: list[RedirectHop] = []
    started = time.perf_counter()

    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=False, verify=True
        ) as client:
            method = prepared.method
            url = prepared.url
            content = prepared.content
            data = prepared.data
            hops = 0

            while True:
                validate_outbound_url(
                    url,
                    allow_private=settings.allow_private_network,
                    blocked_hosts=blocked,
                )

                http_request = client.build_request(
                    method,
                    url,
                    headers=prepared.headers,
                    content=content,
                    data=data,
                )
                response = await client.send(http_request, stream=True)

                is_redirect = (
                    response.status_code in REDIRECT_STATUSES
                    and "location" in response.headers
                    and request.follow_redirects
                )

                if not is_redirect:
                    body, truncated = await _read_capped(response, max_bytes)
                    await response.aclose()
                    break

                location = response.headers["location"]
                await response.aclose()
                hops += 1
                if hops > settings.executor_max_redirects:
                    raise httpx.TooManyRedirects(
                        f"Exceeded {settings.executor_max_redirects} redirects."
                    )

                redirects.append(
                    RedirectHop(
                        url=url, status_code=response.status_code, location=location
                    )
                )
                url = urljoin(url, location)

                # 303, and 301/302 in practice, downgrade the method to GET
                # and drop the body, matching every mainstream HTTP client.
                if response.status_code in (301, 302, 303) and method not in (
                    "GET",
                    "HEAD",
                ):
                    method = "GET"
                    content = None
                    data = None

            duration_ms = (time.perf_counter() - started) * 1000

    except OutboundRequestBlocked as exc:
        return _failure(request, f"Blocked: {exc}", started)
    except httpx.TooManyRedirects as exc:
        return _failure(request, str(exc), started)
    except httpx.TimeoutException:
        return _failure(request, f"Request timed out after {timeout:g}s.", started)
    except httpx.ConnectError as exc:
        return _failure(request, f"Could not connect: {exc}", started)
    except httpx.HTTPError as exc:
        return _failure(request, f"Request failed: {exc}", started)

    text = _decode(body, response)
    headers = dict(response.headers)

    is_json = False
    if text:
        content_type = response.headers.get("content-type", "")
        if "json" in content_type.lower():
            is_json = True
        else:
            try:
                json.loads(text)
                is_json = True
            except (json.JSONDecodeError, ValueError):
                is_json = False

    view = assertion_service.ResponseView(
        status_code=response.status_code,
        duration_ms=duration_ms,
        headers=headers,
        body=text,
    )
    results = assertion_service.evaluate(request.assertions, view)

    return ExecuteResponse(
        ok=True,
        status_code=response.status_code,
        status_text=STATUS_TEXT.get(response.status_code, ""),
        final_url=str(response.url),
        duration_ms=round(duration_ms, 2),
        size_bytes=len(body),
        headers=headers,
        body=text,
        is_json=is_json,
        truncated=truncated,
        redirects=redirects,
        assertion_results=results,
        assertions_passed=sum(1 for r in results if r.passed),
        assertions_failed=sum(1 for r in results if not r.passed),
    )


def _failure(
    request: ExecuteRequest, message: str, started: float
) -> ExecuteResponse:
    """Build a failed result, still evaluating assertions so they report."""
    duration_ms = (time.perf_counter() - started) * 1000
    view = assertion_service.ResponseView(
        status_code=None, duration_ms=duration_ms, headers={}, body=""
    )
    results = assertion_service.evaluate(request.assertions, view)
    return ExecuteResponse(
        ok=False,
        error=message,
        duration_ms=round(duration_ms, 2),
        assertion_results=results,
        assertions_passed=sum(1 for r in results if r.passed),
        assertions_failed=sum(1 for r in results if not r.passed),
    )
