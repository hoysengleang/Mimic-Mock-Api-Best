"""Shared test fixtures.

Environment variables are set before any application import, because the rate
limiter and the CORS middleware read settings at import time — configuring
them afterwards would be too late.
"""

from __future__ import annotations

import os

os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("SEED_DEMO_DATA", "false")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ALLOW_PRIVATE_NETWORK", "true")

import json  # noqa: E402
import threading  # noqa: E402
from collections.abc import Iterator  # noqa: E402
from http.server import BaseHTTPRequestHandler, HTTPServer  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.db.base import Base, build_engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        database_url="sqlite://",
        rate_limit_enabled=False,
        seed_demo_data=False,
        executor_timeout_seconds=5.0,
    )


@pytest.fixture(autouse=True)
def _reset_mock_registry() -> Iterator[None]:
    """Clear the mock cache around every test.

    The registry is a module-level singleton, so without this a cached
    snapshot from one test's database would leak into the next.
    """
    from app.services.mock_registry import registry

    registry.reset()
    yield
    registry.reset()


@pytest.fixture
def db_session(settings: Settings) -> Iterator[Session]:
    """A fresh in-memory database per test."""
    engine = build_engine(settings)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session, settings: Settings) -> Iterator[TestClient]:
    """A TestClient wired to the per-test database."""

    def override_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# --- A real HTTP server to send requests at --------------------------------


class _EchoHandler(BaseHTTPRequestHandler):
    """Echoes the request back, with a few special paths for edge cases."""

    def log_message(self, *args: object) -> None:  # silence test output
        return

    def _handle(self) -> None:
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length).decode() if length else ""

        if self.path.startswith("/redirect-to-metadata"):
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
            self.end_headers()
            return

        if self.path.startswith("/redirect"):
            self.send_response(302)
            self.send_header("Location", "/landed")
            self.end_headers()
            return

        if self.path.startswith("/status/"):
            try:
                code = int(self.path.rsplit("/", 1)[-1])
            except ValueError:
                code = 200
            payload = json.dumps({"code": code}).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        payload = json.dumps(
            {
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers),
                "body": body,
                "nested": {"name": "Leang", "age": 30, "tags": ["a", "b"]},
            }
        ).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Echo", "yes")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _handle


@pytest.fixture(scope="session")
def echo_server() -> Iterator[str]:
    """Start a throwaway HTTP server and yield its base URL."""
    server = HTTPServer(("127.0.0.1", 0), _EchoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()


# --- Convenience builders ---------------------------------------------------


@pytest.fixture
def make_mock():
    """Build a lightweight stand-in for a Mock row, for matcher unit tests."""
    from datetime import datetime, timezone

    def _make(
        path: str,
        *,
        method: str = "GET",
        priority: int = 0,
        enabled: bool = True,
    ):
        class _Mock:
            pass

        mock = _Mock()
        mock.path = path
        mock.method = method
        mock.priority = priority
        mock.is_enabled = enabled
        mock.updated_at = datetime.now(timezone.utc)
        return mock

    return _make


@pytest.fixture
def collection(client: TestClient) -> dict:
    response = client.post("/api/collections", json={"name": "Test collection"})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def environment(client: TestClient, echo_server: str) -> dict:
    response = client.post(
        "/api/environments",
        json={
            "name": "Test",
            "is_active": True,
            "variables": [
                {"key": "baseUrl", "value": echo_server, "enabled": True},
                {"key": "token", "value": "sk-test-secret", "enabled": True},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()
