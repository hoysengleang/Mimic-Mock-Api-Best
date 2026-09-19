"""Unit tests for the pure services: interpolation, assertions, matching."""

from __future__ import annotations

import pytest

from app.schemas.common import Assertion
from app.services.assertions import ResponseView, evaluate
from app.services.interpolate import build_context, interpolate, interpolate_pairs
from app.services.matcher import find_best_match, match_path


class TestInterpolation:
    def test_substitutes_a_variable(self) -> None:
        result = interpolate("{{base}}/users", {"base": "http://x"})
        assert result.text == "http://x/users"
        assert not result.missing

    def test_substitutes_several(self) -> None:
        result = interpolate("{{a}}/{{b}}/{{a}}", {"a": "1", "b": "2"})
        assert result.text == "1/2/1"

    def test_tolerates_whitespace(self) -> None:
        assert interpolate("{{  name  }}", {"name": "ok"}).text == "ok"

    def test_unknown_variables_are_left_visible(self) -> None:
        """A visible placeholder is far easier to debug than a silent blank."""
        result = interpolate("/users/{{missing}}", {})
        assert result.text == "/users/{{missing}}"
        assert result.missing == {"missing"}

    def test_nested_variables_resolve(self) -> None:
        result = interpolate("{{outer}}", {"outer": "{{inner}}", "inner": "done"})
        assert result.text == "done"

    def test_cycles_terminate(self) -> None:
        result = interpolate("{{a}}", {"a": "{{b}}", "b": "{{a}}"})
        assert "{{" in result.text  # gave up rather than hanging

    def test_empty_input(self) -> None:
        assert interpolate("", {}).text == ""

    def test_build_context_skips_disabled_and_unnamed(self) -> None:
        context = build_context(
            [
                {"key": "a", "value": "1", "enabled": True},
                {"key": "b", "value": "2", "enabled": False},
                {"key": "", "value": "3", "enabled": True},
            ]
        )
        assert context == {"a": "1"}

    def test_interpolate_pairs_drops_disabled_and_blank_keys(self) -> None:
        pairs, missing = interpolate_pairs(
            [
                {"key": "x", "value": "{{v}}", "enabled": True},
                {"key": "y", "value": "2", "enabled": False},
                {"key": "", "value": "3", "enabled": True},
            ],
            {"v": "42"},
        )
        assert pairs == [("x", "42")]
        assert not missing


@pytest.fixture
def response() -> ResponseView:
    return ResponseView(
        status_code=200,
        duration_ms=120.0,
        headers={"Content-Type": "application/json", "X-Req-Id": "abc"},
        body='{"user": {"name": "Leang", "age": 30, "tags": ["a", "b"]}, "ok": true}',
    )


def check(response: ResponseView, **kwargs: object) -> bool:
    return evaluate([Assertion(**kwargs)], response)[0].passed


class TestAssertions:
    def test_status_equals(self, response: ResponseView) -> None:
        assert check(response, source="status", operator="equals", target="200")
        assert not check(response, source="status", operator="equals", target="404")

    def test_response_time(self, response: ResponseView) -> None:
        assert check(
            response, source="response_time", operator="less_than", target="500"
        )
        assert not check(
            response, source="response_time", operator="less_than", target="10"
        )

    def test_json_path_value(self, response: ResponseView) -> None:
        assert check(
            response,
            source="json_path",
            property="user.name",
            operator="equals",
            target="Leang",
        )

    def test_json_path_numeric_comparison(self, response: ResponseView) -> None:
        assert check(
            response,
            source="json_path",
            property="user.age",
            operator="greater_than",
            target="18",
        )

    def test_json_path_array_index(self, response: ResponseView) -> None:
        assert check(
            response,
            source="json_path",
            property="user.tags[0]",
            operator="equals",
            target="a",
        )

    def test_json_path_boolean(self, response: ResponseView) -> None:
        assert check(
            response,
            source="json_path",
            property="ok",
            operator="equals",
            target="true",
        )

    def test_missing_json_path(self, response: ResponseView) -> None:
        assert check(
            response, source="json_path", property="user.email", operator="not_exists"
        )
        assert not check(
            response, source="json_path", property="user.email", operator="exists"
        )

    def test_header_checks(self, response: ResponseView) -> None:
        assert check(response, source="header", property="x-req-id", operator="exists")
        assert check(
            response,
            source="header",
            property="Content-Type",
            operator="contains",
            target="json",
        )

    def test_body_contains(self, response: ResponseView) -> None:
        assert check(response, source="body", operator="contains", target="Leang")
        assert check(
            response, source="body", operator="not_contains", target="Bob"
        )

    def test_regex(self, response: ResponseView) -> None:
        assert check(
            response,
            source="json_path",
            property="user.name",
            operator="matches",
            target="^Le.*g$",
        )

    def test_invalid_regex_fails_without_raising(self, response: ResponseView) -> None:
        result = evaluate(
            [
                Assertion(
                    source="body", operator="matches", target="([unclosed"
                )
            ],
            response,
        )[0]
        assert not result.passed
        assert "invalid" in result.message.lower()

    def test_invalid_json_path_fails_without_raising(
        self, response: ResponseView
    ) -> None:
        result = evaluate(
            [
                Assertion(
                    source="json_path",
                    property="user..[[",
                    operator="equals",
                    target="x",
                )
            ],
            response,
        )[0]
        assert not result.passed

    def test_disabled_assertions_are_skipped(self, response: ResponseView) -> None:
        results = evaluate(
            [
                Assertion(
                    source="status", operator="equals", target="999", enabled=False
                )
            ],
            response,
        )
        assert results == []

    def test_non_json_body_json_path(self) -> None:
        view = ResponseView(
            status_code=200, duration_ms=1.0, headers={}, body="plain text"
        )
        assert not check(
            view, source="json_path", property="a", operator="exists"
        )


class TestMatcher:
    @pytest.mark.parametrize(
        ("pattern", "path", "expected"),
        [
            ("/users", "/users", True),
            ("/users", "/users/", True),
            ("/users", "/users/1", False),
            ("/users/:id", "/users/42", True),
            ("/users/:id", "/users", False),
            ("/users/:id/posts", "/users/7/posts", True),
            ("/files/*", "/files/a/b/c.txt", True),
            ("/files/*", "/files", True),
            ("/a/b", "/a/c", False),
        ],
    )
    def test_patterns(self, pattern: str, path: str, expected: bool) -> None:
        assert match_path(pattern, path).matched is expected

    def test_captures_named_parameters(self) -> None:
        result = match_path("/users/:id/posts/:postId", "/users/7/posts/9")
        assert result.params == {"id": "7", "postId": "9"}

    def test_captures_wildcard_remainder(self) -> None:
        assert match_path("/files/*", "/files/a/b.txt").params == {"*": "a/b.txt"}

    def test_specificity_beats_generality(self, make_mock) -> None:
        mocks = [make_mock("/users/*"), make_mock("/users/:id"), make_mock("/users/me")]
        assert find_best_match(mocks, "/users/me", "GET")[0].path == "/users/me"
        assert find_best_match(mocks, "/users/9", "GET")[0].path == "/users/:id"
        assert find_best_match(mocks, "/users/a/b", "GET")[0].path == "/users/*"

    def test_explicit_priority_wins(self, make_mock) -> None:
        mocks = [make_mock("/users/me"), make_mock("/users/:id", priority=100)]
        assert find_best_match(mocks, "/users/me", "GET")[0].path == "/users/:id"

    def test_disabled_mocks_are_ignored(self, make_mock) -> None:
        assert find_best_match([make_mock("/x", enabled=False)], "/x", "GET") is None

    def test_method_must_match(self, make_mock) -> None:
        assert find_best_match([make_mock("/x")], "/x", "POST") is None

    def test_no_candidates(self) -> None:
        assert find_best_match([], "/x", "GET") is None
