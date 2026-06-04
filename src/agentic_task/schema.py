"""JSON Schema for vendor-neutral agentic tasks.

Source: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §A.2.

The schema is the canonical source of truth — it gets serialised into
``.agents/schema.json`` per repo (Track 1 #1), and the CLI inline-validates
every write against ``TASK_SCHEMA`` here. Plan §A.3 verifies via the
``jsonschema`` CLI against the on-disk file; this module mirrors that.
"""

from __future__ import annotations

from typing import Any

from jsonschema import validate as _jsonschema_validate

TASK_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "agentic-task",
    "type": "object",
    "required": ["id", "subject", "status", "created_at"],
    "properties": {
        "id": {"type": "string", "pattern": "^[0-9]{4}$"},
        "subject": {"type": "string", "maxLength": 120},
        "description": {"type": "string"},
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
}


def validate_task(task: dict[str, Any]) -> None:
    """Validate ``task`` against ``TASK_SCHEMA``. Raises ``ValidationError`` on failure."""
    _jsonschema_validate(instance=task, schema=TASK_SCHEMA)
