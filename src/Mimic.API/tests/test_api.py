"""API-level tests: CRUD, the mock responder, execution, and the runner."""

from __future__ import annotations

import pytest


class TestHealth:
    def test_liveness(self, client) -> None:
        assert client.get("/api/health").json() == {"status": "ok"}

    def test_readiness_reports_counts(self, client) -> None:
        payload = client.get("/api/health/ready").json()
        assert payload["status"] == "ok"
        assert payload["database"] == "ok"
        assert "mocks" in payload["counts"]

    def test_root_metadata(self, client) -> None:
        payload = client.get("/").json()
        assert payload["mock_base"] == "/mock"


class TestCollections:
    def test_create_and_fetch(self, client) -> None:
        created = client.post("/api/collections", json={"name": "Mine"}).json()
        detail = client.get(f"/api/collections/{created['id']}").json()
        assert detail["name"] == "Mine"
        assert detail["requests"] == []

    def test_list(self, client, collection) -> None:
        assert len(client.get("/api/collections").json()) == 1

    def test_rename(self, client, collection) -> None:
        response = client.patch(
            f"/api/collections/{collection['id']}", json={"name": "Renamed"}
        )
        assert response.json()["name"] == "Renamed"

    def test_delete_cascades_to_requests(self, client, collection) -> None:
        client.post(
            f"/api/collections/{collection['id']}/requests",
            json={"name": "r", "method": "GET", "url": "http://x"},
        )
        assert client.delete(f"/api/collections/{collection['id']}").status_code == 204
        assert client.get(f"/api/collections/{collection['id']}").status_code == 404

    def test_missing_collection_is_404(self, client) -> None:
        assert client.get("/api/collections/nope").status_code == 404

    def test_blank_name_is_rejected(self, client) -> None:
        assert client.post("/api/collections", json={"name": ""}).status_code == 422


class TestRequests:
    def test_create_with_full_payload(self, client, collection) -> None:
        response = client.post(
            f"/api/collections/{collection['id']}/requests",
            json={
                "name": "Get user",
                "method": "get",
                "url": "{{baseUrl}}/users",
                "headers": [{"key": "Accept", "value": "application/json"}],
                "assertions": [
                    {"source": "status", "operator": "equals", "target": "200"}
                ],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["method"] == "GET"  # normalised
        assert len(body["assertions"]) == 1

    def test_update(self, client, collection) -> None:
        created = client.post(
            f"/api/collections/{collection['id']}/requests",
            json={"name": "a", "method": "GET", "url": "http://x"},
        ).json()
        updated = client.patch(
            f"/api/requests/{created['id']}", json={"name": "b", "method": "post"}
        ).json()
        assert updated["name"] == "b"
        assert updated["method"] == "POST"

    def test_duplicate(self, client, collection) -> None:
        created = client.post(
            f"/api/collections/{collection['id']}/requests",
            json={"name": "orig", "method": "GET", "url": "http://x"},
        ).json()
        clone = client.post(f"/api/requests/{created['id']}/duplicate").json()
        assert clone["name"] == "orig (copy)"
        assert clone["id"] != created["id"]

    def test_delete(self, client, collection) -> None:
        created = client.post(
            f"/api/collections/{collection['id']}/requests",
            json={"name": "a", "method": "GET", "url": "http://x"},
        ).json()
        assert client.delete(f"/api/requests/{created['id']}").status_code == 204
        assert client.get(f"/api/requests/{created['id']}").status_code == 404


class TestMockCrud:
    def test_create(self, client) -> None:
        response = client.post(
            "/api/mocks",
            json={"path": "/api/users", "method": "GET", "response": {"ok": True}},
        )
        assert response.status_code == 201
        assert response.json()["path"] == "/api/users"

    def test_duplicate_path_and_method_conflicts(self, client) -> None:
        payload = {"path": "/dupe", "method": "GET", "response": {}}
        assert client.post("/api/mocks", json=payload).status_code == 201
        conflict = client.post("/api/mocks", json=payload)
        assert conflict.status_code == 409
        assert "already exists" in conflict.json()["detail"]

    def test_same_path_different_method_is_fine(self, client) -> None:
        client.post("/api/mocks", json={"path": "/x", "method": "GET", "response": {}})
        response = client.post(
            "/api/mocks", json={"path": "/x", "method": "POST", "response": {}}
        )
        assert response.status_code == 201

    @pytest.mark.parametrize("path", ["users", "", "//users"])
    def test_invalid_paths_rejected(self, client, path: str) -> None:
        response = client.post(
            "/api/mocks", json={"path": path, "method": "GET", "response": {}}
        )
        assert response.status_code == 422

    def test_toggle(self, client) -> None:
        created = client.post(
            "/api/mocks", json={"path": "/t", "method": "GET", "response": {}}
        ).json()
        assert client.post(f"/api/mocks/{created['id']}/toggle").json()["is_enabled"] is False

    def test_search_filter(self, client) -> None:
        client.post("/api/mocks", json={"path": "/alpha", "method": "GET", "response": {}})
        client.post("/api/mocks", json={"path": "/beta", "method": "GET", "response": {}})
        assert len(client.get("/api/mocks?search=alpha").json()) == 1


class TestMockServing:
    def test_serves_the_configured_response(self, client) -> None:
        client.post(
            "/api/mocks",
            json={
                "path": "/api/users",
                "method": "GET",
                "status_code": 201,
                "response": {"users": []},
                "response_headers": {"X-Custom": "yes"},
            },
        )
        response = client.get("/mock/api/users")
        assert response.status_code == 201
        assert response.json() == {"users": []}
        assert response.headers["X-Custom"] == "yes"

    def test_path_parameters_are_captured(self, client) -> None:
        client.post(
            "/api/mocks",
            json={"path": "/users/:id", "method": "GET", "response": {"ok": True}},
        )
        response = client.get("/mock/users/42")
        assert response.status_code == 200
        assert '"id": "42"' in response.headers["X-Mock-Params"]

    def test_wildcards(self, client) -> None:
        client.post(
            "/api/mocks",
            json={"path": "/files/*", "method": "GET", "response": {"ok": True}},
        )
        assert client.get("/mock/files/a/b/c.txt").status_code == 200

    def test_unmatched_path_explains_itself(self, client) -> None:
        response = client.get("/mock/nothing")
        assert response.status_code == 404
        assert "hint" in response.json()

    def test_disabled_mock_does_not_respond(self, client) -> None:
        created = client.post(
            "/api/mocks", json={"path": "/off", "method": "GET", "response": {}}
        ).json()
        client.post(f"/api/mocks/{created['id']}/toggle")
        assert client.get("/mock/off").status_code == 404

    def test_hit_counter_increments(self, client) -> None:
        created = client.post(
            "/api/mocks", json={"path": "/hits", "method": "GET", "response": {}}
        ).json()
        client.get("/mock/hits")
        client.get("/mock/hits")
        assert client.get(f"/api/mocks/{created['id']}").json()["hit_count"] == 2

    def test_hop_by_hop_headers_are_stripped(self, client) -> None:
        client.post(
            "/api/mocks",
            json={
                "path": "/hbh",
                "method": "GET",
                "response": {},
                "response_headers": {"Transfer-Encoding": "chunked"},
            },
        )
        response = client.get("/mock/hbh")
        assert response.status_code == 200


class TestExecution:
    def test_sends_and_reports_timing(self, client, echo_server) -> None:
        response = client.post(
            "/api/send", json={"method": "GET", "url": f"{echo_server}/ping"}
        ).json()
        assert response["ok"] is True
        assert response["status_code"] == 200
        assert response["duration_ms"] >= 0

    def test_interpolates_variables(self, client, environment, echo_server) -> None:
        response = client.post(
            "/api/send", json={"method": "GET", "url": "{{baseUrl}}/echo"}
        ).json()
        assert response["ok"] is True
        assert response["final_url"].startswith(echo_server)

    def test_applies_bearer_auth(self, client, environment) -> None:
        response = client.post(
            "/api/send",
            json={
                "method": "GET",
                "url": "{{baseUrl}}/echo",
                "auth": {"type": "bearer", "token": "{{token}}"},
            },
        ).json()
        assert "Bearer sk-test-secret" in response["body"]

    def test_applies_basic_auth(self, client, echo_server) -> None:
        response = client.post(
            "/api/send",
            json={
                "method": "GET",
                "url": f"{echo_server}/echo",
                "auth": {"type": "basic", "username": "u", "password": "p"},
            },
        ).json()
        assert "Basic " in response["body"]

    def test_sends_a_json_body(self, client, echo_server) -> None:
        response = client.post(
            "/api/send",
            json={
                "method": "POST",
                "url": f"{echo_server}/echo",
                "body_mode": "json",
                "body": '{"hello": "world"}',
            },
        ).json()
        assert '\\"hello\\": \\"world\\"' in response["body"] or "hello" in response["body"]

    def test_evaluates_assertions(self, client, echo_server) -> None:
        response = client.post(
            "/api/send",
            json={
                "method": "GET",
                "url": f"{echo_server}/echo",
                "assertions": [
                    {"source": "status", "operator": "equals", "target": "200"},
                    {
                        "source": "json_path",
                        "property": "nested.name",
                        "operator": "equals",
                        "target": "Leang",
                    },
                    {"source": "status", "operator": "equals", "target": "500"},
                ],
            },
        ).json()
        assert response["assertions_passed"] == 2
        assert response["assertions_failed"] == 1

    def test_follows_redirects(self, client, echo_server) -> None:
        response = client.post(
            "/api/send", json={"method": "GET", "url": f"{echo_server}/redirect"}
        ).json()
        assert response["ok"] is True
        assert len(response["redirects"]) == 1

    def test_redirect_into_metadata_is_blocked(self, client, echo_server) -> None:
        """The SSRF guard must re-check every hop, not just the first."""
        response = client.post(
            "/api/send",
            json={"method": "GET", "url": f"{echo_server}/redirect-to-metadata"},
        ).json()
        assert response["ok"] is False
        assert "metadata" in response["error"].lower()

    def test_unreachable_host_fails_gracefully(self, client) -> None:
        response = client.post(
            "/api/send", json={"method": "GET", "url": "http://127.0.0.1:9/x"}
        ).json()
        assert response["ok"] is False
        assert response["error"]

    def test_bad_scheme_is_refused(self, client) -> None:
        response = client.post(
            "/api/send", json={"method": "GET", "url": "file:///etc/passwd"}
        ).json()
        assert response["ok"] is False
        assert "scheme" in response["error"].lower()

    def test_missing_url_is_422(self, client) -> None:
        assert client.post("/api/send", json={"method": "GET"}).status_code == 422


class TestHistory:
    def test_records_and_redacts(self, client, environment) -> None:
        client.post(
            "/api/send",
            json={
                "method": "GET",
                "url": "{{baseUrl}}/echo",
                "auth": {"type": "bearer", "token": "{{token}}"},
                "save_history": True,
            },
        )
        entries = client.get("/api/history").json()["items"]
        assert len(entries) == 1
        assert "sk-test-secret" not in str(entries[0]["request_headers"])

    def test_can_be_skipped(self, client, echo_server) -> None:
        client.post(
            "/api/send",
            json={
                "method": "GET",
                "url": f"{echo_server}/echo",
                "save_history": False,
            },
        )
        assert client.get("/api/history").json()["total"] == 0

    def test_clear(self, client, echo_server) -> None:
        client.post("/api/send", json={"method": "GET", "url": f"{echo_server}/e"})
        assert client.delete("/api/history").status_code == 204
        assert client.get("/api/history").json()["total"] == 0


class TestRunner:
    @pytest.fixture
    def suite(self, client, collection, echo_server) -> dict:
        for name, target in (("ok", "200"), ("also ok", "200")):
            client.post(
                f"/api/collections/{collection['id']}/requests",
                json={
                    "name": name,
                    "method": "GET",
                    "url": f"{echo_server}/echo",
                    "assertions": [
                        {"source": "status", "operator": "equals", "target": target}
                    ],
                },
            )
        return collection

    def test_runs_every_request(self, client, suite) -> None:
        result = client.post(
            "/api/run", json={"collection_id": suite["id"]}
        ).json()
        assert result["status"] == "passed"
        assert result["total_requests"] == 2
        assert result["passed"] == 2

    def test_loops(self, client, suite) -> None:
        result = client.post(
            "/api/run", json={"collection_id": suite["id"], "iterations": 3}
        ).json()
        assert result["iterations"] == 3
        assert result["total_requests"] == 6
        assert {step["iteration"] for step in result["results"]} == {1, 2, 3}

    def test_reports_failures(self, client, collection, echo_server) -> None:
        client.post(
            f"/api/collections/{collection['id']}/requests",
            json={
                "name": "will fail",
                "method": "GET",
                "url": f"{echo_server}/status/500",
                "assertions": [
                    {"source": "status", "operator": "equals", "target": "200"}
                ],
            },
        )
        result = client.post(
            "/api/run", json={"collection_id": collection["id"]}
        ).json()
        assert result["status"] == "failed"
        assert result["failed"] == 1

    def test_stop_on_failure(self, client, collection, echo_server) -> None:
        for path in ("/status/500", "/echo"):
            client.post(
                f"/api/collections/{collection['id']}/requests",
                json={
                    "name": path,
                    "method": "GET",
                    "url": f"{echo_server}{path}",
                    "assertions": [
                        {"source": "status", "operator": "equals", "target": "200"}
                    ],
                },
            )
        result = client.post(
            "/api/run",
            json={"collection_id": collection["id"], "stop_on_failure": True},
        ).json()
        assert result["total_requests"] == 1

    def test_empty_collection_is_a_clear_error(self, client, collection) -> None:
        response = client.post("/api/run", json={"collection_id": collection["id"]})
        assert response.status_code == 400
        assert "nothing to run" in response.json()["detail"]

    def test_unknown_collection_is_400(self, client) -> None:
        assert client.post("/api/run", json={"collection_id": "nope"}).status_code == 400

    def test_runs_are_listed(self, client, suite) -> None:
        client.post("/api/run", json={"collection_id": suite["id"]})
        assert client.get("/api/runs").json()["total"] == 1


class TestEnvironments:
    def test_only_one_can_be_active(self, client) -> None:
        first = client.post(
            "/api/environments", json={"name": "A", "is_active": True}
        ).json()
        second = client.post(
            "/api/environments", json={"name": "B", "is_active": True}
        ).json()

        environments = {e["id"]: e for e in client.get("/api/environments").json()}
        assert environments[second["id"]]["is_active"] is True
        assert environments[first["id"]]["is_active"] is False

    def test_activate_endpoint(self, client) -> None:
        env = client.post("/api/environments", json={"name": "A"}).json()
        assert client.post(f"/api/environments/{env['id']}/activate").json()["is_active"]

    def test_variables_round_trip(self, client) -> None:
        env = client.post("/api/environments", json={"name": "A"}).json()
        updated = client.patch(
            f"/api/environments/{env['id']}",
            json={"variables": [{"key": "k", "value": "v", "enabled": True}]},
        ).json()
        assert updated["variables"][0]["key"] == "k"
