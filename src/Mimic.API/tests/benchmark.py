"""Throughput benchmark for the hot paths.

Not part of the test suite — run it directly:

    .venv/bin/python -m tests.benchmark

It exists so performance claims can be checked rather than asserted.
"""

from __future__ import annotations

import os
import statistics
import time

os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("SEED_DEMO_DATA", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.db.base import Base, build_engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

MOCK_COUNT = 200
COLLECTIONS = 10
REQUESTS_EACH = 20
ROUNDS = 400


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * p))
    return ordered[index]


def report(label: str, timings: list[float]) -> None:
    ops = 1 / statistics.mean(timings)
    print(
        f"  {label:38} "
        f"mean {statistics.mean(timings) * 1000:7.3f} ms   "
        f"p95 {percentile(timings, 0.95) * 1000:7.3f} ms   "
        f"{ops:8.0f} ops/s"
    )


def main() -> None:
    settings = Settings(
        database_url="sqlite://", rate_limit_enabled=False, seed_demo_data=False
    )
    engine = build_engine(settings)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        print(f"\nSeeding {MOCK_COUNT} mocks …")
        for index in range(MOCK_COUNT):
            client.post(
                "/api/mocks",
                json={
                    "path": f"/api/resource{index}/:id",
                    "method": "GET",
                    "response": {"index": index, "payload": "x" * 200},
                },
            )

        print(f"Seeding {COLLECTIONS} collections x {REQUESTS_EACH} requests …")
        for c in range(COLLECTIONS):
            collection = client.post(
                "/api/collections", json={"name": f"Collection {c}"}
            ).json()
            for r in range(REQUESTS_EACH):
                client.post(
                    f"/api/collections/{collection['id']}/requests",
                    json={
                        "name": f"Request {r}",
                        "method": "GET",
                        "url": "http://127.0.0.1:9/x",
                    },
                )

        print(f"\nBenchmarking ({ROUNDS} rounds each)\n")

        # 1. Mock serving — the hottest path.
        timings = []
        for i in range(ROUNDS):
            target = f"/mock/api/resource{i % MOCK_COUNT}/42"
            start = time.perf_counter()
            response = client.get(target)
            timings.append(time.perf_counter() - start)
            assert response.status_code == 200, response.text
        report(f"serve mock (1 of {MOCK_COUNT})", timings)

        # 2. Listing all mocks.
        timings = []
        for _ in range(ROUNDS // 4):
            start = time.perf_counter()
            client.get("/api/mocks")
            timings.append(time.perf_counter() - start)
        report(f"list {MOCK_COUNT} mocks", timings)

        # 3. Building the sidebar — what the UI actually does on load.
        #    The old client fetched the index, then each collection in turn.
        ids = [c["id"] for c in client.get("/api/collections").json()]

        timings = []
        for _ in range(ROUNDS // 8):
            start = time.perf_counter()
            for collection_id in ids:
                client.get(f"/api/collections/{collection_id}")
            timings.append(time.perf_counter() - start)
        report(f"load sidebar — {COLLECTIONS} separate calls", timings)

        timings = []
        for _ in range(ROUNDS // 8):
            start = time.perf_counter()
            client.get("/api/collections")
            timings.append(time.perf_counter() - start)
        report("load sidebar — 1 call with contents", timings)

        # 4. Single collection detail.
        timings = []
        for _ in range(ROUNDS // 4):
            start = time.perf_counter()
            client.get(f"/api/collections/{ids[0]}")
            timings.append(time.perf_counter() - start)
        report(f"collection detail ({REQUESTS_EACH} requests)", timings)

        # 5. Health, as a floor for framework overhead.
        timings = []
        for _ in range(ROUNDS):
            start = time.perf_counter()
            client.get("/api/health")
            timings.append(time.perf_counter() - start)
        report("health (framework floor)", timings)

    app.dependency_overrides.clear()
    print()


if __name__ == "__main__":
    main()
