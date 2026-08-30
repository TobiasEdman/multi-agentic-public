"""Canonical shared-goal contract used by task and governance records."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

GOAL_FIELDS = frozenset(
    {"schema_version", "objective", "scope", "acceptance_criteria", "non_goals", "constraints"}
)
ESCALATION_REASONS = frozenset(
    {
        "agent_disagreement",
        "ambiguous_goal",
        "ambiguous_policy",
        "security_or_legal",
        "public_publication",
        "destructive_action",
    }
)
MAX_GOAL_STRING_CHARS = 2_048
MAX_GOAL_LIST_ITEMS = 64
MAX_GOAL_CANONICAL_BYTES = 32_768


class GoalContractError(ValueError):
    """A goal or autonomous-merge acknowledgement is malformed."""


def _is_canonical_goal_text(value: object) -> bool:
    """Reject text whose displayed meaning can differ from its signed bytes."""

    return (
        isinstance(value, str)
        and bool(value.strip())
        and value == value.strip()
        and len(value) <= MAX_GOAL_STRING_CHARS
        and unicodedata.normalize("NFC", value) == value
        and not any(unicodedata.category(character).startswith("C") for character in value)
    )


def canonical_goal(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return one strict JSON-normalized goal contract."""
    if set(value) != GOAL_FIELDS:
        raise GoalContractError("goal contract fields are incomplete or unknown")
    if value.get("schema_version") != "1":
        raise GoalContractError("goal contract schema_version must be 1")
    objective = value.get("objective")
    if not _is_canonical_goal_text(objective):
        raise GoalContractError("goal objective must be a normalized non-empty string")
    result: dict[str, Any] = {"schema_version": "1", "objective": objective}
    for field in ("scope", "acceptance_criteria", "non_goals", "constraints"):
        raw = value.get(field)
        minimum = 1 if field in {"scope", "acceptance_criteria"} else 0
        if (
            not isinstance(raw, list)
            or len(raw) < minimum
            or len(raw) > MAX_GOAL_LIST_ITEMS
            or not all(
                _is_canonical_goal_text(item)
                for item in raw
            )
            or len(set(raw)) != len(raw)
        ):
            raise GoalContractError(f"goal {field} must be a unique normalized string list")
        result[field] = list(raw)
    if len(canonical_json(result).encode("utf-8")) > MAX_GOAL_CANONICAL_BYTES:
        raise GoalContractError("goal contract exceeds the canonical byte limit")
    return result


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def goal_digest(value: Mapping[str, Any]) -> str:
    goal = canonical_goal(value)
    return f"sha256:{hashlib.sha256(canonical_json(goal).encode('utf-8')).hexdigest()}"


def validate_goal_scope(goal: Mapping[str, Any], changed_paths: Sequence[str]) -> None:
    """Require the reviewed diff scope to equal the committed goal scope."""
    normalized = canonical_goal(goal)
    if sorted(normalized["scope"]) != sorted(set(changed_paths)):
        raise GoalContractError("goal scope differs from the exact changed-path set")


def validate_escalations(values: Sequence[str]) -> tuple[str, ...]:
    if (
        not all(isinstance(item, str) and item in ESCALATION_REASONS for item in values)
        or len(set(values)) != len(values)
    ):
        raise GoalContractError("escalation reasons are malformed")
    return tuple(sorted(values))
