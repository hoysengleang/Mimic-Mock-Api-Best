"""Schemas for the collection test runner."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import AssertionResult, Page


class RunRequest(BaseModel):
    """Run every request in a collection, optionally looped."""

    collection_id: str
    environment_id: str | None = None
    iterations: int = Field(1, ge=1, le=10_000)
    delay_ms: int = Field(0, ge=0, le=60_000, description="Pause between requests.")
    stop_on_failure: bool = False
    timeout_seconds: float | None = Field(None, gt=0, le=300)
    save_history: bool = False


class RunStepResult(BaseModel):
    iteration: int
    request_id: str
    name: str
    method: str
    url: str
    ok: bool
    status_code: int | None = None
    duration_ms: float = 0.0
    size_bytes: int = 0
    error: str | None = None
    assertion_results: list[AssertionResult] = Field(default_factory=list)
    assertions_passed: int = 0
    assertions_failed: int = 0


class RunResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str | None = None
    collection_name: str = ""
    environment_id: str | None = None

    iterations: int
    total_requests: int
    total_assertions: int
    passed: int
    failed: int
    duration_ms: float
    status: str

    results: list[RunStepResult] = Field(default_factory=list)
    created_at: datetime


class RunSummary(BaseModel):
    """A run without its per-step detail, for the history list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str | None = None
    collection_name: str = ""
    iterations: int
    total_requests: int
    total_assertions: int
    passed: int
    failed: int
    duration_ms: float
    status: str
    created_at: datetime


class RunPage(Page):
    items: list[RunSummary]
