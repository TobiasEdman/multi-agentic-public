"""Schema-validation tests for agentic_task.schema.

Source spec: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §A.2.
"""

from __future__ import annotations

from typing import Any

import pytest
from jsonschema import ValidationError

from agentic_task.schema import TASK_SCHEMA, validate_task


def _sample(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "0001",
        "subject": "smoke",
        "status": "pending",
        "created_at": "2026-04-27T13:00:00Z",
        "updated_at": "2026-04-27T13:00:00Z",
    }
    base.update(overrides)
    return base


def test_minimal_pending_task_is_valid() -> None:
    validate_task(_sample())


def test_claimed_task_is_valid() -> None:
    validate_task(
        _sample(
            status="claimed",
            claimed_by="te-claude",
            runtime="claude",
            claimed_at="2026-04-27T13:01:00Z",
        )
    )


def test_completed_task_is_valid() -> None:
    validate_task(
        _sample(
            status="completed",
            claimed_by="te-claude",
            runtime="claude",
            claimed_at="2026-04-27T13:01:00Z",
            completed_at="2026-04-27T13:02:00Z",
        )
    )


def test_unknown_status_fails() -> None:
    with pytest.raises(ValidationError):
        validate_task(_sample(status="explosion"))


def test_unknown_runtime_fails() -> None:
    with pytest.raises(ValidationError):
        validate_task(_sample(runtime="bard"))


def test_short_id_fails() -> None:
    with pytest.raises(ValidationError):
        validate_task(_sample(id="1"))


def test_missing_required_field_fails() -> None:
    bad = _sample()
    del bad["created_at"]
    with pytest.raises(ValidationError):
        validate_task(bad)


def test_top_level_required_fields() -> None:
    assert TASK_SCHEMA["required"] == ["id", "subject", "status", "created_at"]
