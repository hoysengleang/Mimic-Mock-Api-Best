"""Mock path matching.

Supported patterns, in descending specificity:

``/users``          exact segment match
``/users/:id``      named parameter, captures one segment
``/files/*``        trailing wildcard, captures the rest of the path

When several mocks match the same request, the winner is decided by, in order:
explicit ``priority`` (higher first), then specificity (exact beats parameter
beats wildcard), then the most recently updated. Without that ordering, adding
a catch-all mock would silently shadow every specific one.
"""

from __future__ import annotations

from dataclasses import dataclass

SEGMENT_EXACT = 3
SEGMENT_PARAM = 2
SEGMENT_WILDCARD = 1


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    params: dict[str, str]
    score: tuple[int, ...]


NO_MATCH = MatchResult(matched=False, params={}, score=())


def split_path(path: str) -> list[str]:
    return [segment for segment in path.strip("/").split("/") if segment != ""]


def match_path(pattern: str, path: str) -> MatchResult:
    """Match a concrete *path* against a mock *pattern*."""
    return match_segments(tuple(split_path(pattern)), tuple(split_path(path)))


def match_segments(
    pattern_segments: tuple[str, ...], path_segments: tuple[str, ...]
) -> MatchResult:
    """Match pre-split segments.

    Split once and reuse: on the mock-serving hot path the pattern never
    changes between requests, so re-splitting it every time is pure waste.
    """
    params: dict[str, str] = {}
    score: list[int] = []

    for index, expected in enumerate(pattern_segments):
        if expected == "*":
            # Trailing wildcard swallows whatever remains, including nothing.
            params["*"] = "/".join(path_segments[index:])
            score.append(SEGMENT_WILDCARD)
            return MatchResult(matched=True, params=params, score=tuple(score))

        if index >= len(path_segments):
            return NO_MATCH

        actual = path_segments[index]

        if expected.startswith(":"):
            name = expected[1:]
            if not name:
                return NO_MATCH
            params[name] = actual
            score.append(SEGMENT_PARAM)
            continue

        if expected != actual:
            return NO_MATCH
        score.append(SEGMENT_EXACT)

    if len(path_segments) != len(pattern_segments):
        return NO_MATCH

    return MatchResult(matched=True, params=params, score=tuple(score))


def rank_key(mock: object, result: MatchResult) -> tuple[int, int, tuple[int, ...], float]:
    """Sort key for choosing between competing matches. Higher sorts first.

    Every component is coerced to a comparable primitive: a mock loaded from
    an older export, or one with a hand-edited priority, must not make the
    whole comparison raise.
    """
    try:
        priority = int(getattr(mock, "priority", 0) or 0)
    except (TypeError, ValueError):
        priority = 0

    updated_at = getattr(mock, "updated_at", None)
    try:
        recency = updated_at.timestamp() if updated_at is not None else 0.0
    except (AttributeError, TypeError, ValueError, OSError):
        recency = 0.0

    return (priority, len(result.score), result.score, recency)


def find_best_match(
    mocks: list, path: str, method: str
) -> tuple[object, MatchResult] | None:
    """Return the highest-ranked enabled mock matching *path* and *method*.

    Accepts either ORM rows or pre-compiled entries. An entry carrying a
    ``segments`` tuple skips the per-request string split, which is most of
    the cost once there are a few hundred mocks.
    """
    normalized_method = method.upper()
    path_segments = tuple(split_path(path))

    best: tuple[object, MatchResult] | None = None
    best_key: tuple | None = None

    for mock in mocks:
        if not getattr(mock, "is_enabled", True):
            continue

        mock_method = (getattr(mock, "method", "") or "").upper()
        if mock_method not in (normalized_method, "ANY"):
            continue

        segments = getattr(mock, "segments", None)
        if segments is None:
            segments = tuple(split_path(getattr(mock, "path", "")))

        result = match_segments(segments, path_segments)
        if not result.matched:
            continue

        # Track the winner as we go rather than collecting every candidate
        # and sorting afterwards.
        key = rank_key(mock, result)
        if best_key is None or key > best_key:
            best, best_key = (mock, result), key

    return best
