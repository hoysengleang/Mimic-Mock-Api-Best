"""Schemas for executing a request and recording the result."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import (
    Assertion,
    AssertionResult,
    AuthConfig,
    BodyMode,
    KeyValue,
    Method,
    Page,
)


class ExecuteRequest(BaseModel):
    """An ad-hoc request to send. Mirrors a SavedRequest but is not persisted."""

    name: str = Field("", max_length=200)
    request_id: str | None = None

    method: Method = "GET"
    url: str = Field(..., min_length=1, max_length=4_000)
    headers: list[KeyValue] = Field(default_factory=list, max_length=100)
    query_params: list[KeyValue] = Field(default_factory=list, max_length=100)
    body_mode: BodyMode = BodyMode.NONE
    body: str = Field("", max_length=1_000_000)
    form_data: list[KeyValue] = Field(default_factory=list, max_length=100)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    assertions: list[Assertion] = Field(default_factory=list, max_length=100)

    environment_id: str | None = None
    follow_redirects: bool = True
    timeout_seconds: float | None = Field(None, gt=0, le=300)
    save_history: bool = True

    @field_validator("method")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


class RedirectHop(BaseModel):
    url: str
    status_code: int
    location: str


class ExecuteResponse(BaseModel):
    """The outcome of one executed request."""

    ok: bool
    error: str | None = None

    status_code: int | None = None
    status_text: str = ""
    final_url: str = ""
    duration_ms: float = 0.0
    size_bytes: int = 0

    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    is_json: bool = False
    truncated: bool = False
    redirects: list[RedirectHop] = Field(default_factory=list)

    assertion_results: list[AssertionResult] = Field(default_factory=list)
    assertions_passed: int = 0
    assertions_failed: int = 0

    history_id: str | None = None


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str | None = None
    name: str = ""
    method: str
    url: str
    status_code: int | None = None
    duration_ms: float = 0.0
    response_size: int = 0
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: str = ""
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: str = ""
    truncated: bool = False
    error: str | None = None
    assertion_results: list[AssertionResult] = Field(default_factory=list)
    created_at: datetime


class HistoryPage(Page):
    items: list[HistoryOut]
