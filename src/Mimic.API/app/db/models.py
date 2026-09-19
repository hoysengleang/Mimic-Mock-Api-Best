"""ORM models.

Identifiers are UUID strings rather than integers so that records can be
created client-side, exported, and re-imported across instances without
collisions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Collection(Base, TimestampMixin):
    """A named group of saved requests, optionally organised into folders."""

    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    folders: Mapped[list[Folder]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="Folder.position",
    )
    requests: Mapped[list[SavedRequest]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="SavedRequest.position",
    )


class Folder(Base, TimestampMixin):
    """A nestable group of requests inside a collection."""

    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    collection: Mapped[Collection] = relationship(back_populates="folders")
    children: Mapped[list[Folder]] = relationship(
        cascade="all, delete-orphan", order_by="Folder.position"
    )
    requests: Mapped[list[SavedRequest]] = relationship(
        back_populates="folder", order_by="SavedRequest.position"
    )


class SavedRequest(Base, TimestampMixin):
    """A reusable HTTP request definition."""

    __tablename__ = "saved_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[str | None] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="GET", nullable=False)
    url: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # [{key, value, enabled, description}]
    headers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    query_params: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    body_mode: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    form_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # {type: none|bearer|basic|apikey, token, username, password, key, value, add_to}
    auth: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # [{source, property, operator, target, enabled}]
    assertions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    collection: Mapped[Collection] = relationship(back_populates="requests")
    folder: Mapped[Folder | None] = relationship(back_populates="requests")


class Environment(Base, TimestampMixin):
    """A named set of variables substituted into requests via {{name}}."""

    __tablename__ = "environments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # [{key, value, enabled, secret}]
    variables: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class Mock(Base, TimestampMixin):
    """A stubbed endpoint served under /mock/*."""

    __tablename__ = "mocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    response: Mapped[Any] = mapped_column(JSON, default=dict)
    response_headers: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    content_type: Mapped[str] = mapped_column(
        String(100), default="application/json", nullable=False
    )

    delay: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Higher priority wins when several mocks match the same request.
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_hit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_mocks_method_enabled", "method", "is_enabled"),)


class HistoryEntry(Base):
    """A record of one executed request. Credentials are redacted on write."""

    __tablename__ = "history_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    method: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    response_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    request_headers: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    request_body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    response_headers: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    response_body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    assertion_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class TestRun(Base):
    """The aggregate result of running a collection, possibly looped."""

    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    collection_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    collection_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    environment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    iterations: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_assertions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="passed", nullable=False)
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
