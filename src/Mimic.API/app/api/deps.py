from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.db.store import MockStore


@lru_cache
def get_store() -> MockStore:
    settings = get_settings()
    return MockStore(settings.data_file)
