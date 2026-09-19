from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Variable(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key    : str  = Field("", max_length=200)
    value  : str  = Field("", max_length=100_000)
    enabled : bool = True
    secret  : bool = False


class EnvironmentBase(BaseModel):
    name: str = Field("New environment", min_length=1, max_length=200)
    is_active: bool = False
    variables: list[Variable] = Field(default_factory=list, max_length=500)


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    is_active: bool | None = None
    variables: list[Variable] | None = Field(None, max_length=500)


class EnvironmentOut(EnvironmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
