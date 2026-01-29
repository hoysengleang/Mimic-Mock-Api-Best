from __future__ import annotations

from pathlib import Path
from threading import Lock
import json
import uuid

from app.schemas.mock import MockCreate, MockDefinition, MockUpdate


class MockStore:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._lock = Lock()
        self._items: list[MockDefinition] = []
        self._load()

    def _ensure_parent(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        if not self._file_path.exists():
            self._items = []
            return
        try:
            raw = self._file_path.read_text()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            self._items = []
            return
        if not isinstance(payload, list):
            self._items = []
            return
        self._items = [MockDefinition(**item) for item in payload]

    def _save(self) -> None:
        self._ensure_parent()
        payload = [item.model_dump() for item in self._items]
        self._file_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def list(self) -> list[MockDefinition]:
        with self._lock:
            return list(self._items)

    def get(self, mock_id: str) -> MockDefinition | None:
        with self._lock:
            for item in self._items:
                if item.id == mock_id:
                    return item
        return None

    def create(self, payload: MockCreate) -> MockDefinition:
        with self._lock:
            mock = MockDefinition(id=str(uuid.uuid4()), **payload.model_dump())
            self._items.append(mock)
            self._save()
            return mock

    def update(self, mock_id: str, payload: MockUpdate) -> MockDefinition | None:
        with self._lock:
            for index, item in enumerate(self._items):
                if item.id != mock_id:
                    continue
                data = item.model_dump()
                update_data = payload.model_dump(exclude_unset=True)
                data.update(update_data)
                updated = MockDefinition(**data)
                self._items[index] = updated
                self._save()
                return updated
        return None

    def delete(self, mock_id: str) -> bool:
        with self._lock:
            for index, item in enumerate(self._items):
                if item.id != mock_id:
                    continue
                del self._items[index]
                self._save()
                return True
        return False

    def find_match(self, path: str, method: str) -> MockDefinition | None:
        normalized_method = method.upper()
        with self._lock:
            for item in self._items:
                if item.path == path and item.method == normalized_method:
                    return item
        return None
