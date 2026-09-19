"""``{{variable}}`` substitution.

Resolution is iterative so a variable may reference another variable, and is
depth-limited so a cycle (``a -> b -> a``) terminates instead of hanging.
Unknown variables are deliberately left untouched rather than replaced with an
empty string: a request to ``/users/{{userId}}`` failing loudly is far easier
to debug than a silent request to ``/users/``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

VARIABLE_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_.\-]+)\s*\}\}")
MAX_DEPTH = 10


@dataclass
class InterpolationResult:
    text: str
    missing: set[str] = field(default_factory=set)


def build_context(variables: list[dict[str, object]]) -> dict[str, str]:
    """Flatten a variable list into a lookup, skipping disabled rows."""
    context: dict[str, str] = {}
    for item in variables:
        if not item.get("enabled", True):
            continue
        key = str(item.get("key", "")).strip()
        if not key:
            continue
        context[key] = str(item.get("value", ""))
    return context


def interpolate(text: str, context: dict[str, str]) -> InterpolationResult:
    """Substitute every ``{{name}}`` in *text* using *context*."""
    if not text or "{{" not in text:
        return InterpolationResult(text=text or "")

    missing: set[str] = set()
    current = text

    for _ in range(MAX_DEPTH):
        if "{{" not in current:
            break

        replaced = False

        def _replace(match: re.Match[str]) -> str:
            nonlocal replaced
            name = match.group(1)
            if name in context:
                replaced = True
                return context[name]
            missing.add(name)
            return match.group(0)

        current = VARIABLE_PATTERN.sub(_replace, current)
        if not replaced:
            break

    return InterpolationResult(text=current, missing=missing)


def interpolate_pairs(
    pairs: list[dict[str, object]], context: dict[str, str]
) -> tuple[list[tuple[str, str]], set[str]]:
    """Interpolate a list of key/value rows, dropping disabled and unnamed ones."""
    out: list[tuple[str, str]] = []
    missing: set[str] = set()

    for pair in pairs:
        if not pair.get("enabled", True):
            continue
        key_result = interpolate(str(pair.get("key", "")), context)
        if not key_result.text.strip():
            continue
        value_result = interpolate(str(pair.get("value", "")), context)
        missing |= key_result.missing | value_result.missing
        out.append((key_result.text, value_result.text))

    return out, missing
