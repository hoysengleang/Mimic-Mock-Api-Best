"""Evaluation of declarative response assertions.

Assertions are data, never code. There is no ``eval`` anywhere in this module,
so importing someone else's collection can never execute anything. The cost is
that only the operators enumerated in ``AssertionOperator`` are supported,
which in practice covers the checks people actually write.
"""

from __future__ import annotations

import json
import re
from typing import Any

from jsonpath_ng.ext import parse as parse_jsonpath

from app.schemas.common import (
    Assertion,
    AssertionOperator,
    AssertionResult,
    AssertionSource,
)

MAX_PATTERN_LENGTH = 500
_NOT_FOUND = object()


class ResponseView:
    """The response surface an assertion may inspect."""

    def __init__(
        self,
        *,
        status_code: int | None,
        duration_ms: float,
        headers: dict[str, str],
        body: str,
    ) -> None:
        self.status_code = status_code
        self.duration_ms = duration_ms
        self.headers = {key.lower(): value for key, value in headers.items()}
        self.body = body
        self._json: Any = _NOT_FOUND

    @property
    def json_body(self) -> Any:
        if self._json is _NOT_FOUND:
            try:
                self._json = json.loads(self.body) if self.body else None
            except (json.JSONDecodeError, ValueError):
                self._json = _NOT_FOUND
        return self._json


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _extract(assertion: Assertion, response: ResponseView) -> Any:
    source = assertion.source

    if source == AssertionSource.STATUS:
        return response.status_code
    if source == AssertionSource.RESPONSE_TIME:
        return response.duration_ms
    if source == AssertionSource.BODY:
        return response.body
    if source == AssertionSource.HEADER:
        return response.headers.get(assertion.property.strip().lower(), _NOT_FOUND)
    if source == AssertionSource.JSON_PATH:
        payload = response.json_body
        if payload is _NOT_FOUND:
            return _NOT_FOUND
        path = assertion.property.strip()
        if not path:
            return payload
        try:
            matches = parse_jsonpath(path).find(payload)
        except Exception:  # noqa: BLE001 - jsonpath-ng raises bare exceptions
            raise ValueError(f"'{path}' is not a valid JSON path.") from None
        if not matches:
            return _NOT_FOUND
        if len(matches) == 1:
            return matches[0].value
        return [match.value for match in matches]

    return _NOT_FOUND


def _compare(
    operator: AssertionOperator, actual: Any, target: str
) -> tuple[bool, str]:
    """Return (passed, message)."""
    exists = actual is not _NOT_FOUND

    if operator == AssertionOperator.EXISTS:
        return exists, "" if exists else "value was not found"
    if operator == AssertionOperator.NOT_EXISTS:
        return not exists, "" if not exists else "value was found"

    if not exists:
        return False, "value was not found"

    actual_text = _stringify(actual)

    if operator == AssertionOperator.IS_EMPTY:
        empty = actual in (None, "", [], {}) or actual_text == ""
        return empty, "" if empty else f"'{actual_text}' is not empty"
    if operator == AssertionOperator.IS_NOT_EMPTY:
        empty = actual in (None, "", [], {}) or actual_text == ""
        return not empty, "" if not empty else "value is empty"

    if operator in (AssertionOperator.LESS_THAN, AssertionOperator.GREATER_THAN):
        actual_number = _as_number(actual)
        target_number = _as_number(target)
        if actual_number is None or target_number is None:
            return False, f"'{actual_text}' and '{target}' are not both numbers"
        if operator == AssertionOperator.LESS_THAN:
            ok = actual_number < target_number
            return ok, "" if ok else f"{actual_number} is not less than {target_number}"
        ok = actual_number > target_number
        return ok, "" if ok else f"{actual_number} is not greater than {target_number}"

    if operator in (AssertionOperator.EQUALS, AssertionOperator.NOT_EQUALS):
        actual_number = _as_number(actual)
        target_number = _as_number(target)
        if actual_number is not None and target_number is not None:
            equal = actual_number == target_number
        else:
            equal = actual_text == target
        if operator == AssertionOperator.EQUALS:
            return equal, "" if equal else f"expected '{target}', got '{actual_text}'"
        return not equal, "" if not equal else f"value equals '{target}'"

    if operator in (AssertionOperator.CONTAINS, AssertionOperator.NOT_CONTAINS):
        contains = target in actual_text
        if operator == AssertionOperator.CONTAINS:
            return contains, "" if contains else f"'{target}' not found in response"
        return not contains, "" if not contains else f"'{target}' was found in response"

    if operator == AssertionOperator.MATCHES:
        if len(target) > MAX_PATTERN_LENGTH:
            return False, f"pattern exceeds {MAX_PATTERN_LENGTH} characters"
        try:
            pattern = re.compile(target)
        except re.error as exc:
            return False, f"invalid regular expression: {exc}"
        ok = pattern.search(actual_text) is not None
        return ok, "" if ok else f"'{actual_text}' does not match /{target}/"

    return False, f"unsupported operator '{operator}'"


def evaluate(
    assertions: list[Assertion], response: ResponseView
) -> list[AssertionResult]:
    """Run every enabled assertion against *response*."""
    results: list[AssertionResult] = []

    for assertion in assertions:
        if not assertion.enabled:
            continue

        try:
            actual = _extract(assertion, response)
        except ValueError as exc:
            results.append(
                AssertionResult(
                    source=assertion.source.value,
                    property=assertion.property,
                    operator=assertion.operator.value,
                    target=assertion.target,
                    actual="",
                    passed=False,
                    message=str(exc),
                )
            )
            continue

        passed, message = _compare(assertion.operator, actual, assertion.target)

        results.append(
            AssertionResult(
                source=assertion.source.value,
                property=assertion.property,
                operator=assertion.operator.value,
                target=assertion.target,
                actual="" if actual is _NOT_FOUND else _stringify(actual)[:2_000],
                passed=passed,
                message=message,
            )
        )

    return results
