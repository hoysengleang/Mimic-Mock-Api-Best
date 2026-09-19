"""Application settings.

Every value can be overridden with an environment variable of the same name
(case-insensitive), or via a ``.env`` file at the repository root.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Identity -----------------------------------------------------------
    app_name: str = "Mimic"
    app_version: str = "1.0.0"
    api_prefix: str = "/api"
    debug: bool = False

    # --- Storage ------------------------------------------------------------
    data_dir: Path = Path("data")
    database_url: str | None = Field(
        default=None,
        description="Full SQLAlchemy URL. Defaults to SQLite inside data_dir.",
    )

    # --- CORS ---------------------------------------------------------------
    # Locked to the dev/prod UI origins by default. A wildcard is never used,
    # because the API is same-origin in production and permissive CORS on a
    # tool that proxies arbitrary HTTP is a genuine risk.
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # --- Rate limiting ------------------------------------------------------
    rate_limit_enabled: bool = True
    rate_limit_default: str = "240/minute"
    rate_limit_send: str = "60/minute"
    rate_limit_run: str = "12/minute"

    # --- Request executor limits -------------------------------------------
    # These bound what a single outbound request may cost us.
    executor_timeout_seconds: float = Field(30.0, gt=0, le=300)
    executor_max_redirects: int = Field(5, ge=0, le=20)
    executor_max_response_bytes: int = Field(10 * 1024 * 1024, gt=0)
    max_request_body_bytes: int = Field(10 * 1024 * 1024, gt=0)

    # --- Test runner limits -------------------------------------------------
    runner_max_iterations: int = Field(100, ge=1, le=10_000)
    runner_max_requests_per_run: int = Field(2_000, ge=1)

    # --- SSRF policy --------------------------------------------------------
    # Mimic is a developer tool, so by default it MUST be able to reach
    # localhost and LAN addresses -- that is where your dev API lives.
    # Set allow_private_network=false when hosting Mimic on a shared server.
    # Cloud metadata endpoints are blocked unconditionally, in both modes.
    allow_private_network: bool = True
    blocked_hosts: list[str] = []
    
    seed_demo_data: bool = True

    history_max_entries: int = Field(1_000, ge=1)
    history_max_body_bytes: int = Field(256 * 1024, gt=0)

    @field_validator("data_dir", mode="after")
    @classmethod
    def _resolve_data_dir(cls, value: Path) -> Path:
        return value.expanduser()

    @field_validator("cors_origins", "blocked_hosts", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Accept both a JSON list and a plain comma-separated string."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return value
            return [part.strip() for part in stripped.split(",") if part.strip()]
        return value

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'mimic.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
