"""In-memory cache for the mock-serving hot path.

Serving a mock used to cost two database round trips: one to load every
enabled mock, and one to commit the incremented hit counter. Both happened on
*every* request, which put the mock server about four times slower than the
bare framework.

This module removes both:

* Mock definitions are cached, pre-split into path segments so matching does
  no string work per request.
* Hit counts accumulate in memory and are flushed in one bulk statement.

Consistency: writes through this process invalidate the cache immediately, so
a single-worker deployment (the normal way to run Mimic) is never stale. A TTL
bounds staleness for multi-worker deployments, where another worker's write is
not visible here until the entry expires.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from app.db.models import Mock
from app.services.matcher import split_path

# How long a cached snapshot may be reused without checking the database.
# Only matters across processes; local writes invalidate immediately.
DEFAULT_TTL_SECONDS = 2.0

# Flush the accumulated hit counts once either threshold is crossed.
HIT_FLUSH_COUNT = 50
HIT_FLUSH_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class CompiledMock:
    """A mock with everything the responder needs, resolved ahead of time."""

    id: str
    path: str
    method: str
    segments: tuple[str, ...]
    status_code: int
    response: Any
    response_headers: dict[str, str]
    content_type: str
    delay: float
    priority: int
    is_enabled: bool
    updated_at: datetime | None

    @classmethod
    def from_row(cls, row: Mock) -> CompiledMock:
        return cls(
            id=row.id,
            path=row.path,
            method=(row.method or "").upper(),
            segments=tuple(split_path(row.path or "")),
            status_code=row.status_code,
            response=row.response,
            response_headers=dict(row.response_headers or {}),
            content_type=row.content_type or "application/json",
            delay=row.delay or 0.0,
            priority=row.priority or 0,
            is_enabled=bool(row.is_enabled),
            updated_at=row.updated_at,
        )


class MockRegistry:
    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._entries: list[CompiledMock] | None = None
        self._loaded_at = 0.0
        self._hits: dict[str, int] = {}
        self._last_flush = time.monotonic()

    # --- Definitions --------------------------------------------------------

    def snapshot(self, session: Session) -> list[CompiledMock]:
        """Return every enabled mock, reloading only when the cache is cold."""
        now = time.monotonic()

        with self._lock:
            fresh = (
                self._entries is not None and (now - self._loaded_at) < self._ttl
            )
            if fresh:
                return self._entries  # type: ignore[return-value]

        # Load outside the lock: the query may block, and a duplicate load
        # under contention is harmless.
        rows = session.scalars(
            select(Mock).where(Mock.is_enabled.is_(True))
        ).all()
        entries = [CompiledMock.from_row(row) for row in rows]

        with self._lock:
            self._entries = entries
            self._loaded_at = time.monotonic()
        return entries

    def invalidate(self) -> None:
        """Drop the cached definitions. Called after any mock write."""
        with self._lock:
            self._entries = None
            self._loaded_at = 0.0

    # --- Hit counting -------------------------------------------------------

    def record_hit(self, mock_id: str) -> bool:
        """Count a hit. Returns True when the buffer is ready to be flushed."""
        with self._lock:
            self._hits[mock_id] = self._hits.get(mock_id, 0) + 1
            pending = sum(self._hits.values())
            elapsed = time.monotonic() - self._last_flush
            return pending >= HIT_FLUSH_COUNT or elapsed >= HIT_FLUSH_SECONDS

    def flush_hits(self, session: Session) -> int:
        """Write buffered hit counts in one statement. Returns rows touched."""
        with self._lock:
            pending = self._hits
            self._hits = {}
            self._last_flush = time.monotonic()

        if not pending:
            return 0

        now = datetime.now(timezone.utc)
        try:
            session.execute(
                update(Mock)
                .where(Mock.id.in_(pending.keys()))
                .values(
                    hit_count=Mock.hit_count
                    + case(pending, value=Mock.id, else_=0),
                    last_hit_at=now,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            # Put the counts back so they are not silently lost.
            with self._lock:
                for mock_id, count in pending.items():
                    self._hits[mock_id] = self._hits.get(mock_id, 0) + count
            raise

        return len(pending)

    def pending_hits(self) -> int:
        with self._lock:
            return sum(self._hits.values())

    def reset(self) -> None:
        """Clear everything. Used by tests."""
        with self._lock:
            self._entries = None
            self._loaded_at = 0.0
            self._hits = {}
            self._last_flush = time.monotonic()


registry = MockRegistry()
