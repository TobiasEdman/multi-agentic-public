"""Drift-test: .agents/schema.json must match agentic_task.schema.TASK_SCHEMA.

The Python module is canonical (CLI inline-validates against it). The
on-disk JSON file exists so other runtimes (Codex CLI, Mistral via
OpenCode, jq pipelines, the plan §A.3 manual replay) can validate
without importing Python.

If they drift, the CLI and external validators disagree on what a valid
task looks like — silent breakage. This test forces a regen of
``.agents/schema.json`` whenever ``TASK_SCHEMA`` changes.

Regen command (when this test fails on purpose):
    python -c "from agentic_task.schema import TASK_SCHEMA; \\
               import json; \\
               open('.agents/schema.json','w').write(json.dumps(TASK_SCHEMA, indent=2)+'\\n')"
"""

from __future__ import annotations

import json
from pathlib import Path

from agentic_task.schema import TASK_SCHEMA

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ON_DISK = _REPO_ROOT / ".agents" / "schema.json"


def test_on_disk_schema_matches_python_source() -> None:
    """Byte-equivalent comparison after a JSON round-trip (whitespace-agnostic)."""
    assert _ON_DISK.is_file(), f"{_ON_DISK} missing — regen with the command in the docstring"
    on_disk = json.loads(_ON_DISK.read_text())
    assert on_disk == TASK_SCHEMA, (
        ".agents/schema.json drifted from agentic_task.schema.TASK_SCHEMA. "
        "Regen with the command in this test's docstring."
    )


def test_on_disk_schema_is_pretty_printed() -> None:
    """Pretty-printed indented JSON with trailing newline (so git diffs read cleanly)."""
    text = _ON_DISK.read_text()
    assert text.endswith("\n")
    expected = json.dumps(TASK_SCHEMA, indent=2) + "\n"
    assert text == expected, (
        ".agents/schema.json formatting drifted (indent=2, trailing newline). "
        "Regen with the command in test_on_disk_schema's docstring."
    )
