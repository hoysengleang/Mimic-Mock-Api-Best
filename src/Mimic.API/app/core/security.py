"""Outbound-request safety.

Mimic sends HTTP requests on the user's behalf, from the server. That is a
server-side request forgery (SSRF) primitive unless it is fenced in, so every
outbound URL passes through :func:`validate_outbound_url` first -- including
each hop of a redirect chain.

Policy:

* Only ``http`` and ``https`` are allowed. Schemes like ``file://`` or
  ``gopher://`` are rejected outright.
* Cloud instance-metadata addresses are blocked unconditionally. These leak
  credentials and there is no legitimate reason to reach them from here.
* Private / loopback / link-local ranges are allowed by default, because Mimic
  is a developer tool and your dev API lives on localhost. Operators hosting
  Mimic for other people set ``ALLOW_PRIVATE_NETWORK=false`` to forbid them.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})

# Instance metadata services. Always denied, regardless of network policy.
ALWAYS_BLOCKED_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("169.254.169.254/32"),  # AWS / GCP / Azure / DO
    ipaddress.ip_network("fd00:ec2::254/128"),  # AWS IMDS over IPv6
)

# Headers whose values must never be persisted to history in the clear.
SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "x-access-token",
        "x-csrf-token",
        "x-session-token",
        "authentication",
    }
)

REDACTED = "••••••redacted••••••"


class OutboundRequestBlocked(ValueError):
    """Raised when a URL fails the outbound safety policy."""


@dataclass(frozen=True)
class ResolvedTarget:
    """A URL that has passed validation, plus the addresses it resolved to."""

    url: str
    host: str
    port: int
    scheme: str
    addresses: tuple[str, ...]


def _resolve_all(host: str, port: int) -> tuple[str, ...]:
    """Resolve a hostname to every address it advertises.

    Every address is checked, not just the first. A host that returns one
    public and one private address must not slip through on the public one.
    """
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise OutboundRequestBlocked(f"Could not resolve host '{host}'.") from exc
    return tuple({info[4][0] for info in infos})


def _check_address(raw: str, *, allow_private: bool) -> None:
    try:
        address = ipaddress.ip_address(raw)
    except ValueError as exc:  # pragma: no cover - getaddrinfo returns valid IPs
        raise OutboundRequestBlocked(f"Unparseable address '{raw}'.") from exc

    for network in ALWAYS_BLOCKED_NETWORKS:
        if address.version == network.version and address in network:
            raise OutboundRequestBlocked(
                "Requests to cloud metadata endpoints are blocked."
            )

    if allow_private:
        return

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    ):
        raise OutboundRequestBlocked(
            f"Address '{raw}' is on a private network, which this instance forbids."
        )


def validate_outbound_url(
    url: str,
    *,
    allow_private: bool = True,
    blocked_hosts: tuple[str, ...] | list[str] = (),
) -> ResolvedTarget:
    """Validate a URL against the outbound policy.

    Returns the resolved target on success, raises
    :class:`OutboundRequestBlocked` otherwise.
    """
    parts = urlsplit(url.strip())

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise OutboundRequestBlocked(
            f"Scheme '{parts.scheme or 'none'}' is not allowed. Use http or https."
        )

    host = parts.hostname
    if not host:
        raise OutboundRequestBlocked("The URL is missing a host.")

    normalized_host = host.lower().rstrip(".")
    for blocked in blocked_hosts:
        candidate = blocked.lower().strip().rstrip(".")
        if not candidate:
            continue
        if normalized_host == candidate or normalized_host.endswith(f".{candidate}"):
            raise OutboundRequestBlocked(f"Host '{host}' is blocked by policy.")

    try:
        port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise OutboundRequestBlocked("The URL has an invalid port.") from exc

    addresses = _resolve_all(normalized_host, port)
    if not addresses:
        raise OutboundRequestBlocked(f"Host '{host}' resolved to no addresses.")

    for address in addresses:
        _check_address(address, allow_private=allow_private)

    return ResolvedTarget(
        url=url,
        host=normalized_host,
        port=port,
        scheme=parts.scheme.lower(),
        addresses=addresses,
    )


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Mask credential-bearing headers before they are written to history."""
    return {
        key: (REDACTED if key.lower() in SENSITIVE_HEADERS else value)
        for key, value in headers.items()
    }
