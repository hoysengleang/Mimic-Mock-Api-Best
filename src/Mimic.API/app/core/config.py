from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    app_name: str
    api_prefix: str
    data_dir: Path

    @property
    def data_file(self) -> Path:
        return self.data_dir / "mocks.json"


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Mimic Mock API"),
        api_prefix=os.getenv("API_PREFIX", "/api"),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
    )
