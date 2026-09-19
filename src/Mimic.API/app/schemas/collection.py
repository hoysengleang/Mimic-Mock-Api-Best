"""Schemas for collections, folders and saved requests."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import (
    Assertion,
    AuthConfig,
    BodyMode,
    KeyValue,
    Method,
)

ORM = ConfigDict(from_attributes=True)


# --- Saved requests ---------------------------------------------------------


class SavedRequestBase(BaseModel):
    name: str = Field("Untitled request", min_length=1, max_length=200)
    description: str = Field("", max_length=5_000)
    method: Method = "GET"
    url: str = Field("", max_length=4_000)
    headers: list[KeyValue] = Field(default_factory=list, max_length=100)
    query_params: list[KeyValue] = Field(default_factory=list, max_length=100)
    body_mode: BodyMode = BodyMode.NONE
    body: str = Field("", max_length=1_000_000)
    form_data: list[KeyValue] = Field(default_factory=list, max_length=100)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    assertions: list[Assertion] = Field(default_factory=list, max_length=100)
    folder_id: str | None = None
    position: int = 0

    @field_validator("method")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


class SavedRequestCreate(SavedRequestBase):
    pass


class SavedRequestUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5_000)
    method: Method | None = None
    url: str | None = Field(None, max_length=4_000)
    headers: list[KeyValue] | None = Field(None, max_length=100)
    query_params: list[KeyValue] | None = Field(None, max_length=100)
    body_mode: BodyMode | None = None
    body: str | None = Field(None, max_length=1_000_000)
    form_data: list[KeyValue] | None = Field(None, max_length=100)
    auth: AuthConfig | None = None
    assertions: list[Assertion] | None = Field(None, max_length=100)
    folder_id: str | None = None
    position: int | None = None

    @field_validator("method")
    @classmethod
    def _upper(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class SavedRequestOut(SavedRequestBase):
    model_config = ORM

    id: str
    collection_id: str
    created_at: datetime
    updated_at: datetime


# --- Folders ----------------------------------------------------------------


class FolderBase(BaseModel):
    name: str = Field("New folder", min_length=1, max_length=200)
    parent_id: str | None = None
    position: int = 0


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    parent_id: str | None = None
    position: int | None = None


class FolderOut(FolderBase):
    model_config = ORM

    id: str
    collection_id: str
    created_at: datetime
    updated_at: datetime


# --- Collections ------------------------------------------------------------


class CollectionBase(BaseModel):
    name: str = Field("New collection", min_length=1, max_length=200)
    description: str = Field("", max_length=5_000)
    position: int = 0


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5_000)
    position: int | None = None


class CollectionOut(CollectionBase):
    model_config = ORM

    id: str
    created_at: datetime
    updated_at: datetime


class CollectionDetail(CollectionOut):
    """A collection with its full contents, for the sidebar tree."""

    folders: list[FolderOut] = Field(default_factory=list)
    requests: list[SavedRequestOut] = Field(default_factory=list)
