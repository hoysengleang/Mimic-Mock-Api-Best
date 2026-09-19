"""Shared value objects used across requests, mocks and the test runner."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")

Method = Annotated[str, Field(pattern=r"^(?i:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")]


class BodyMode(str, Enum):
    NONE = "none"
    JSON = "json"
    TEXT = "text"
    FORM = "form"
    XML = "xml"


class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "apikey"


class ApiKeyLocation(str, Enum):
    HEADER = "header"
    QUERY = "query"


class KeyValue(BaseModel):
    """One row of a headers / query-params / form-data table."""

    model_config = ConfigDict(extra="ignore")

    key: str = Field("", max_length=500)
    value: str = Field("", max_length=100_000)
    enabled: bool = True
    description: str = Field("", max_length=500)


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: AuthType = AuthType.NONE
    token: str = Field("", max_length=8_000)
    username: str = Field("", max_length=500)
    password: str = Field("", max_length=500)
    key: str = Field("", max_length=500)
    value: str = Field("", max_length=8_000)
    add_to: ApiKeyLocation = ApiKeyLocation.HEADER


class AssertionSource(str, Enum):
    STATUS = "status"
    RESPONSE_TIME = "response_time"
    BODY = "body"
    JSON_PATH = "json_path"
    HEADER = "header"


class AssertionOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    MATCHES = "matches"


class Assertion(BaseModel):
    """A declarative check against a response.

    Deliberately declarative: assertions are data, never code. Mimic does not
    evaluate user-supplied scripts, so a saved collection can never execute
    anything on the machine that runs it.
    """

    model_config = ConfigDict(extra="ignore")

    source: AssertionSource = AssertionSource.STATUS
    # Which header name, or which JSON path -- unused for `status`/`body`.
    property: str = Field("", max_length=500)
    operator: AssertionOperator = AssertionOperator.EQUALS
    target: str = Field("", max_length=10_000)
    enabled: bool = True

    @field_validator("property", "target", mode="before")
    @classmethod
    def _stringify(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if not isinstance(value, str):
            return str(value)
        return value


class AssertionResult(BaseModel):
    source: str
    property: str = ""
    operator: str
    target: str = ""
    actual: str = ""
    passed: bool
    message: str = ""


class Page(BaseModel):
    """Generic pagination envelope."""

    total: int
    limit: int
    offset: int
