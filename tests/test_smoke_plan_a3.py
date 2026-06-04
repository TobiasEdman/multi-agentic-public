"""Replicates the plan §A.3 verifieringsartefakt as a pytest test.

Source: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §A.3.

The plan-doc shows the lock protocol end-to-end: a single task transitions
pending → claimed → completed across 3 commits, with jq verifying the
final shape and ``jsonschema -i`` confirming schema-conformance.

This test runs the same flow via the CLI (claim + complete subcommands)
instead of hand-rolled jq pipelines, so the test fails if either the
shell pipeline OR the CLI drifts from the §A.3 contract.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentic_task.cli import app
from agentic_task.schema import validate_task

runner = CliRunner()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    for k, v in [
        ("user.email", "t@t.t"),
        ("user.name", "t"),
        ("commit.gpgsign", "false"),
    ]:
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / ".agents" / "tasks").mkdir(parents=True)
    return tmp_path


def _git_log_lines(repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def test_pending_claim_complete_yields_three_commits(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plan §A.3 step-for-step: pending → claimed → completed, 3 commits."""
    # ── 1. Skapa pending task (plan: jq + git commit) ────────────────────
    initial = {
        "id": "0001",
        "subject": "test",
        "status": "pending",
        "created_at": "2026-04-27T13:00:00Z",
        "updated_at": "2026-04-27T13:00:00Z",
    }
    task_file = repo / ".agents" / "tasks" / "0001.json"
    task_file.write_text(json.dumps(initial, indent=2) + "\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "task 0001: pending"],
        check=True,
    )

    # ── 2. Claim (plan: jq pipeline; here: CLI) ──────────────────────────
    monkeypatch.setenv("AGENT_ID", "te-claude")
    monkeypatch.setenv("AGENT_RUNTIME", "claude")
    r1 = runner.invoke(app, ["claim", str(repo)])
    assert r1.exit_code == 0, r1.output
    assert r1.output.strip() == "0001"

    # ── 3. Complete (plan: jq pipeline; here: CLI) ───────────────────────
    r2 = runner.invoke(app, ["complete", str(repo), "0001"])
    assert r2.exit_code == 0, r2.output

    # ── Verify: 3 commits exist ──────────────────────────────────────────
    log = _git_log_lines(repo)
    assert len(log) == 3, f"expected 3 commits, got {len(log)}:\n{log}"
    assert any("pending" in line for line in log)
    assert any("claimed by te-claude" in line for line in log)
    assert any("completed" in line for line in log)

    # ── Verify: final state matches plan §A.3 jq output ──────────────────
    # Plan asserts: 0001 \t completed \t te-claude \t claude
    final = json.loads(task_file.read_text())
    assert final["id"] == "0001"
    assert final["status"] == "completed"
    assert final["claimed_by"] == "te-claude"
    assert final["runtime"] == "claude"
    assert final["claimed_at"].endswith("Z")
    assert final["completed_at"].endswith("Z")

    # ── Verify: jsonschema-validation passes (plan: `jsonschema -i ...`) ─
    validate_task(final)
