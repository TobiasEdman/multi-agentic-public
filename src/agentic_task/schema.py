"""JSON Schema for vendor-neutral agentic tasks.

Source: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §A.2.

The schema is the canonical source of truth — it gets serialised into
``.agents/schema.json`` per repo (Track 1 #1), and the CLI inline-validates
every write against ``TASK_SCHEMA`` here. Plan §A.3 verifies via the
``jsonschema`` CLI against the on-disk file; this module mirrors that.
"""

from __future__ import annotations

from typing import Any

from jsonschema import ValidationError
from jsonschema import validate as _jsonschema_validate

from agentic_task.goal_contract import (
    ESCALATION_REASONS,
    MAX_GOAL_LIST_ITEMS,
    MAX_GOAL_STRING_CHARS,
    GoalContractError,
    goal_digest,
)

TASK_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "agentic-task",
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "subject", "status", "created_at"],
    "properties": {
        "id": {"type": "string", "pattern": "^[0-9]{4}$"},
        "subject": {"type": "string", "maxLength": 120},
        "description": {"type": "string"},
        "goal": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "schema_version",
                "objective",
                "scope",
                "acceptance_criteria",
                "non_goals",
                "constraints",
            ],
            "properties": {
                "schema_version": {"const": "1"},
                "objective": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_GOAL_STRING_CHARS,
                },
                "scope": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_GOAL_LIST_ITEMS,
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_GOAL_STRING_CHARS,
                    },
                },
                "acceptance_criteria": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_GOAL_LIST_ITEMS,
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_GOAL_STRING_CHARS,
                    },
                },
                "non_goals": {
                    "type": "array",
                    "maxItems": MAX_GOAL_LIST_ITEMS,
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_GOAL_STRING_CHARS,
                    },
                },
                "constraints": {
                    "type": "array",
                    "maxItems": MAX_GOAL_LIST_ITEMS,
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_GOAL_STRING_CHARS,
                    },
                },
            },
        },
        "goal_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        "writer_goal_acknowledgement": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "agent_id",
                "runtime",
                "vendor",
                "goal_sha256",
                "acknowledged_at",
            ],
            "properties": {
                "agent_id": {"type": "string", "minLength": 1},
                "runtime": {"enum": ["claude", "codex", "mistral"]},
                "vendor": {"enum": ["anthropic", "openai", "mistral"]},
                "goal_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                "acknowledged_at": {"type": "string", "format": "date-time"},
            },
        },
        "escalation_reasons": {
            "type": "array",
            "maxItems": len(ESCALATION_REASONS),
            "uniqueItems": True,
            "items": {"enum": sorted(ESCALATION_REASONS)},
        },
        "status": {
            "enum": [
                "pending",
                "claimed",
                "in_progress",
                "completed",
                "blocked",
                "abandoned",
            ]
        },
        "claimed_by": {
            "type": ["string", "null"],
            "description": "agent identity, e.g. 'te-claude' or 'te-codex'",
        },
        "runtime": {"enum": ["claude", "codex", "mistral", None]},
        "coordination_authority": {
            "type": ["string", "null"],
            "pattern": "^sha256:[0-9a-f]{64}$",
            "description": (
                "repository discriminator: credential-free sha256 receipt of the"
                " canonical remote transport; names where claim arbitration"
                " happened and is not an authentication, attestation, or merge"
                " authority"
            ),
        },
        "claimed_at": {"type": ["string", "null"], "format": "date-time"},
        "completed_at": {"type": ["string", "null"], "format": "date-time"},
        "blocked_by": {"type": "array", "items": {"type": "string"}},
        "blocks": {"type": "array", "items": {"type": "string"}},
        "branch": {
            "type": ["string", "null"],
            "description": "branch where work happened",
        },
        "pr": {
            "type": ["string", "null"],
            "description": "PR URL when ready",
        },
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
    },
    "allOf": [
        {
            "if": {"required": ["goal"]},
            "then": {"required": ["goal_sha256"]},
        },
        {
            "if": {"required": ["goal_sha256"]},
            "then": {"required": ["goal"]},
        },
        {
            "if": {
                "properties": {"status": {"const": "pending"}},
                "required": ["status"],
            },
            "then": {
                "properties": {
                    "claimed_by": {"type": "null"},
                    "runtime": {"type": "null"},
                    "claimed_at": {"type": "null"},
                    "completed_at": {"type": "null"},
                }
            },
        },
        {
            "if": {
                "properties": {"status": {"enum": ["claimed", "in_progress"]}},
                "required": ["status"],
            },
            "then": {
                "required": ["claimed_by", "runtime", "claimed_at"],
                "properties": {
                    "claimed_by": {"type": "string", "minLength": 1},
                    "runtime": {"enum": ["claude", "codex", "mistral"]},
                    "claimed_at": {"type": "string", "format": "date-time"},
                    "completed_at": {"type": "null"},
                },
            },
        },
        {
            "if": {
                "properties": {"status": {"const": "completed"}},
                "required": ["status"],
            },
            "then": {
                "required": ["claimed_by", "runtime", "claimed_at", "completed_at"],
                "properties": {
                    "claimed_by": {"type": "string", "minLength": 1},
                    "runtime": {"enum": ["claude", "codex", "mistral"]},
                    "claimed_at": {"type": "string", "format": "date-time"},
                    "completed_at": {"type": "string", "format": "date-time"},
                },
            },
        },
        {
            "if": {
                "properties": {"status": {"enum": ["blocked", "abandoned"]}},
                "required": ["status"],
            },
            "then": {
                "properties": {"completed_at": {"type": "null"}},
                "oneOf": [
                    {
                        "properties": {
                            "claimed_by": {"type": "null"},
                            "runtime": {"type": "null"},
                            "claimed_at": {"type": "null"},
                        }
                    },
                    {
                        "required": ["claimed_by", "runtime", "claimed_at"],
                        "properties": {
                            "claimed_by": {"type": "string", "minLength": 1},
                            "runtime": {"enum": ["claude", "codex", "mistral"]},
                            "claimed_at": {"type": "string", "format": "date-time"},
                        },
                    },
                ],
            },
        },
    ],
}

HANDOFF_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "agentic-handoff",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "task_id",
        "created_at",
        "repository_key",
        "source_runtime",
        "source_session",
        "target",
        "active_goal",
        "current_state",
        "changed_paths",
        "off_limits",
        "next_steps",
        "blockers",
        "active_rules",
        "commit",
        "verification",
    ],
    "properties": {
        "schema_version": {"const": "1"},
        "task_id": {"type": "string", "pattern": "^[0-9]{4}$"},
        "created_at": {"type": "string", "format": "date-time"},
        "repository_key": {"type": "string", "minLength": 1},
        "source_runtime": {"enum": ["claude", "codex", "mistral", "human"]},
        "source_session": {"type": "string", "minLength": 1},
        "target": {"type": ["string", "null"]},
        "active_goal": {"type": "string", "minLength": 1},
        "current_state": {"type": "string", "minLength": 1},
        "changed_paths": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
                "pattern": (
                    r"^(?!/)(?!.*\\)(?!.*(?:^|/)\.\.?(?:/|$))"
                    r"(?!.*//)(?!.*\/$)[^\x00-\x1f\x7f/]+"
                    r"(?:/[^\x00-\x1f\x7f/]+)*$"
                ),
            },
        },
        "off_limits": {"type": "array", "items": {"type": "string"}},
        "next_steps": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "minLength": 1},
        },
        "blockers": {"type": "array", "items": {"type": "string"}},
        "active_rules": {"type": "array", "items": {"type": "string"}},
        "commit": {"type": ["string", "null"], "pattern": "^[0-9a-f]{40}$"},
        "verification": {"type": "string", "minLength": 1},
    },
}


def validate_task(task: dict[str, Any]) -> None:
    """Validate ``task`` against ``TASK_SCHEMA``. Raises ``ValidationError`` on failure."""
    _jsonschema_validate(instance=task, schema=TASK_SCHEMA)
    goal = task.get("goal")
    acknowledgement = task.get("writer_goal_acknowledgement")
    if goal is None:
        if acknowledgement is not None:
            raise ValidationError("writer goal acknowledgement requires a goal contract")
        return
    try:
        expected_digest = goal_digest(goal)
    except GoalContractError as exc:
        raise ValidationError(str(exc)) from exc
    if task.get("goal_sha256") != expected_digest:
        raise ValidationError("goal_sha256 does not match the canonical goal contract")
    unclaimed_goal_state = task["status"] == "pending" or (
        task["status"] in {"blocked", "abandoned"}
        and task.get("claimed_by") is None
        and task.get("runtime") is None
        and task.get("claimed_at") is None
    )
    if unclaimed_goal_state:
        if acknowledgement is not None:
            raise ValidationError(
                "unclaimed task cannot carry a writer goal acknowledgement"
            )
        return
    if not isinstance(acknowledgement, dict):
        raise ValidationError("claimed goal task requires writer goal acknowledgement")
    vendor = {"claude": "anthropic", "codex": "openai", "mistral": "mistral"}.get(
        task.get("runtime")
    )
    expected = {
        "agent_id": task.get("claimed_by"),
        "runtime": task.get("runtime"),
        "vendor": vendor,
        "goal_sha256": expected_digest,
    }
    if any(acknowledgement.get(field) != value for field, value in expected.items()):
        raise ValidationError("writer goal acknowledgement differs from the task owner or goal")


def validate_handoff(handoff: dict[str, Any]) -> None:
    """Validate a committable task-scoped handoff record."""
    _jsonschema_validate(instance=handoff, schema=HANDOFF_SCHEMA)
