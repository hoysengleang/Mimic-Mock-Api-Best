from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class MockBase(BaseModel):
    path: str = Field(..., min_length=1, description="Request path (must start with '/')")
    method: str = Field(..., min_length=1, description="HTTP method")
    response: Any
    status_code: int = Field(200, ge=100, le=599)
    delay: float = Field(0, ge=0)

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("path must start with '/'")
        return value

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str) -> str:
        return value.upper()


class MockCreate(MockBase):
    pass


class MockUpdate(BaseModel):
    path: str | None = Field(None, min_length=1)
    method: str | None = Field(None, min_length=1)
    response: Any | None = None
    status_code: int | None = Field(None, ge=100, le=599)
    delay: float | None = Field(None, ge=0)

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith("/"):
            raise ValueError("path must start with '/'")
        return value

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.upper()


class MockDefinition(MockBase):
    id: str
