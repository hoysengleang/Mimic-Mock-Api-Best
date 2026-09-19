"""Schemas for mock endpoint definitions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import Method


class MockBase(BaseModel):
    name: str = Field("", max_length=200)
    description: str = Field("", max_length=5_000)

    path: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description=(
            "Path to match, starting with '/'. Supports named parameters "
            "(/users/:id) and a trailing wildcard (/files/*)."
        ),
    )
    method: Method = "GET"

    status_code: int = Field(200, ge=100, le=599)
    response: Any = None
    response_headers: dict[str, str] = Field(default_factory=dict)
    content_type: str = Field("application/json", max_length=100)

    delay: float = Field(0, ge=0, le=60, description="Artificial latency in seconds.")
    is_enabled: bool = True
    priority: int = Field(0, description="Higher wins when several mocks match.")

    @field_validator("path")
    @classmethod
    def _normalize_path(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            raise ValueError("path must start with '/'")
        if "//" in value:
            raise ValueError("path must not contain '//'")
        return value.rstrip("/") or "/"

    @field_validator("method")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()

    @field_validator("response_headers")
    @classmethod
    def _limit_headers(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 50:
            raise ValueError("at most 50 response headers are allowed")
        return value


class MockCreate(MockBase):
    pass


class MockUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=5_000)
    path: str | None = Field(None, min_length=1, max_length=500)
    method: Method | None = None
    status_code: int | None = Field(None, ge=100, le=599)
    response: Any = None
    response_headers: dict[str, str] | None = None
    content_type: str | None = Field(None, max_length=100)
    delay: float | None = Field(None, ge=0, le=60)
    is_enabled: bool | None = None
    priority: int | None = None

    @field_validator("path")
    @classmethod
    def _normalize_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value.startswith("/"):
            raise ValueError("path must start with '/'")
        if "//" in value:
            raise ValueError("path must not contain '//'")
        return value.rstrip("/") or "/"

    @field_validator("method")
    @classmethod
    def _upper(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class MockOut(MockBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hit_count: int = 0
    last_hit_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
