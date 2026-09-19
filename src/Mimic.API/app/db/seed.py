"""Demo data for a first run.

A brand new install with an empty screen gives someone no idea what the tool
does. Seeding a working example -- three mocks, a collection that calls them,
and an environment wired to both -- means the first thing a new user can do is
press Send and watch it succeed.

Only ever runs when the database is completely empty.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Collection, Environment, Mock, SavedRequest

DEMO_MOCKS = [
    {
        "name": "List users",
        "description": "Returns a small page of users.",
        "path": "/api/users",
        "method": "GET",
        "status_code": 200,
        "response": {
            "users": [
                {"id": 1, "name": "Leang", "role": "admin"},
                {"id": 2, "name": "Dara", "role": "editor"},
                {"id": 3, "name": "Sophea", "role": "viewer"},
            ],
            "total": 3,
        },
    },
    {
        "name": "Get one user",
        "description": "Demonstrates a :id path parameter.",
        "path": "/api/users/:id",
        "method": "GET",
        "status_code": 200,
        "response": {"id": 1, "name": "Leang", "role": "admin", "active": True},
    },
    {
        "name": "Create user",
        "description": "Returns 201 so you can assert on it.",
        "path": "/api/users",
        "method": "POST",
        "status_code": 201,
        "response": {"id": 4, "name": "New user", "created": True},
    },
    {
        "name": "Slow endpoint",
        "description": "Waits 1.5s — useful for testing timeouts and spinners.",
        "path": "/api/slow",
        "method": "GET",
        "status_code": 200,
        "response": {"message": "That took a moment."},
        "delay": 1.5,
    },
    {
        "name": "Server error",
        "description": "Always fails, so you can see how errors render.",
        "path": "/api/broken",
        "method": "GET",
        "status_code": 500,
        "response": {"error": "Something went wrong on the server."},
    },
]

DEMO_REQUESTS = [
    {
        "name": "List users",
        "method": "GET",
        "url": "{{baseUrl}}/mock/api/users",
        "assertions": [
            {"source": "status", "operator": "equals", "target": "200", "enabled": True},
            {
                "source": "json_path",
                "property": "total",
                "operator": "equals",
                "target": "3",
                "enabled": True,
            },
            {
                "source": "response_time",
                "operator": "less_than",
                "target": "2000",
                "enabled": True,
            },
        ],
    },
    {
        "name": "Get one user",
        "method": "GET",
        "url": "{{baseUrl}}/mock/api/users/{{userId}}",
        "assertions": [
            {"source": "status", "operator": "equals", "target": "200", "enabled": True},
            {
                "source": "json_path",
                "property": "name",
                "operator": "is_not_empty",
                "target": "",
                "enabled": True,
            },
        ],
    },
    {
        "name": "Create user",
        "method": "POST",
        "url": "{{baseUrl}}/mock/api/users",
        "body_mode": "json",
        "body": '{\n  "name": "Sokha",\n  "role": "editor"\n}',
        "assertions": [
            {"source": "status", "operator": "equals", "target": "201", "enabled": True},
            {
                "source": "json_path",
                "property": "created",
                "operator": "equals",
                "target": "true",
                "enabled": True,
            },
        ],
    },
]


def database_is_empty(session: Session) -> bool:
    for model in (Collection, Mock, Environment):
        count = session.scalar(select(func.count()).select_from(model)) or 0
        if count:
            return False
    return True


def seed(session: Session, *, force: bool = False) -> bool:
    """Populate demo data. Returns True if anything was written."""
    if not force and not database_is_empty(session):
        return False

    for definition in DEMO_MOCKS:
        session.add(Mock(**definition))

    environment = Environment(
        name="Local",
        is_active=True,
        variables=[
            {
                "key": "baseUrl",
                "value": "http://localhost:5000",
                "enabled": True,
                "secret": False,
            },
            {"key": "userId", "value": "1", "enabled": True, "secret": False},
            {"key": "token", "value": "demo-token", "enabled": True, "secret": True},
        ],
    )
    session.add(environment)

    collection = Collection(
        name="Getting started",
        description=(
            "A working example. Press Send on any request, or Run to execute "
            "the whole collection."
        ),
        position=1,
    )
    session.add(collection)
    session.flush()

    for index, definition in enumerate(DEMO_REQUESTS, start=1):
        session.add(
            SavedRequest(collection_id=collection.id, position=index, **definition)
        )

    session.commit()
    return True
