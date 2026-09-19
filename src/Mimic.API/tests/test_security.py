"""Outbound-request policy and credential handling.

The most important tests in the suite. A regression here turns Mimic into an
SSRF proxy, so these run against the real resolver rather than a stub.
"""

from __future__ import annotations

import pytest

from app.core.security import (
    OutboundRequestBlocked,
    redact_headers,
    validate_outbound_url,
)


class TestSchemes:
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "gopher://example.com/",
            "ftp://example.com/",
            "data:text/plain;base64,aGk=",
            "javascript:alert(1)",
            "not-a-url",
            "",
        ],
    )
    def test_non_http_schemes_are_blocked(self, url: str) -> None:
        with pytest.raises(OutboundRequestBlocked):
            validate_outbound_url(url)

    @pytest.mark.parametrize("url", ["http://127.0.0.1", "https://127.0.0.1"])
    def test_http_and_https_are_allowed(self, url: str) -> None:
        assert validate_outbound_url(url, allow_private=True)


class TestMetadataEndpoints:
    """Cloud metadata is denied even when private networking is permitted."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "http://169.254.169.254:80/",
            "https://169.254.169.254/computeMetadata/v1/",
        ],
    )
    def test_metadata_is_always_blocked(self, url: str) -> None:
        with pytest.raises(OutboundRequestBlocked, match="metadata"):
            validate_outbound_url(url, allow_private=True)


class TestPrivateNetworkPolicy:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8080",
            "http://localhost:3000",
            "http://10.0.0.5",
            "http://192.168.1.1",
        ],
    )
    def test_private_allowed_when_permitted(self, url: str) -> None:
        assert validate_outbound_url(url, allow_private=True)

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8080",
            "http://localhost:3000",
            "http://10.0.0.5",
            "http://192.168.1.1",
            "http://[::1]:8080",
        ],
    )
    def test_private_denied_when_forbidden(self, url: str) -> None:
        with pytest.raises(OutboundRequestBlocked):
            validate_outbound_url(url, allow_private=False)


class TestHostBlocklist:
    def test_exact_host_is_blocked(self) -> None:
        with pytest.raises(OutboundRequestBlocked, match="blocked by policy"):
            validate_outbound_url(
                "http://127.0.0.1/", blocked_hosts=["127.0.0.1"]
            )

    def test_subdomains_are_blocked(self) -> None:
        with pytest.raises(OutboundRequestBlocked, match="blocked by policy"):
            validate_outbound_url(
                "http://api.internal.test/", blocked_hosts=["internal.test"]
            )

    def test_unrelated_host_passes(self) -> None:
        assert validate_outbound_url(
            "http://127.0.0.1/", blocked_hosts=["example.com"]
        )


class TestRedaction:
    @pytest.mark.parametrize(
        "header",
        [
            "Authorization",
            "authorization",
            "Cookie",
            "X-API-Key",
            "x-auth-token",
            "Proxy-Authorization",
        ],
    )
    def test_credential_headers_are_masked(self, header: str) -> None:
        result = redact_headers({header: "super-secret-value"})
        assert "super-secret-value" not in result[header]

    def test_ordinary_headers_survive(self) -> None:
        result = redact_headers(
            {"Accept": "application/json", "Content-Type": "text/plain"}
        )
        assert result["Accept"] == "application/json"
        assert result["Content-Type"] == "text/plain"

    def test_mixed_headers(self) -> None:
        result = redact_headers(
            {"Authorization": "Bearer abc123", "Accept": "*/*"}
        )
        assert "abc123" not in result["Authorization"]
        assert result["Accept"] == "*/*"


class TestMiddleware:
    def test_security_headers_are_present(self, client) -> None:
        response = client.get("/api/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"

    def test_oversized_body_is_rejected(self, client, monkeypatch) -> None:
        # Declare a body far larger than the configured limit.
        response = client.post(
            "/api/collections",
            content=b"{}",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(50 * 1024 * 1024),
            },
        )
        assert response.status_code in (413, 400)
