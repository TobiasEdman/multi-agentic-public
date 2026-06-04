"""End-to-end tests for the agentic-task CLI subcommands.

Each test gets a fresh tmp git repo (no remote) via the ``repo`` fixture.
``_try_push`` treats no-remote as success, so claim/complete commit locally
without needing a real upstream.

Source spec: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §A.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from agentic_task.cli import app

runner = CliRunner()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Initialise a tmp git repo with .agents/tasks/ scaffold."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    for k, v in [
        ("user.email", "t@t.t"),
        ("user.name", "t"),
        ("commit.gpgsign", "false"),
    ]:
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / ".agents" / "tasks").mkdir(parents=True)
    # Initial commit so HEAD~1 exists for any reset paths.
    (tmp_path / ".agents" / "tasks" / ".gitkeep").write_text("")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True
    )
    return tmp_path


def _add_pending(repo: Path, task_id: str, **overrides: Any) -> None:
    task: dict[str, Any] = {
        "id": task_id,
        "subject": f"task {task_id}",
        "status": "pending",
        "created_at": "2026-04-27T13:00:00Z",
        "updated_at": "2026-04-27T13:00:00Z",
    }
    task.update(overrides)
    f = repo / ".agents" / "tasks" / f"{task_id}.json"
    f.write_text(json.dumps(task, indent=2) + "\n")
    subprocess.run(["git", "-C", str(repo), "add", str(f)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", f"task {task_id}: pending"],
        check=True,
    )


def _read_task(repo: Path, task_id: str) -> dict[str, Any]:
    return json.loads((repo / ".agents" / "tasks" / f"{task_id}.json").read_text())


def _git_log(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


# --- claim ------------------------------------------------------------------


def test_claim_picks_lowest_id_pending(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_pending(repo, "0002")
    _add_pending(repo, "0001")  # added later, but lowest id wins
    monkeypatch.setenv("AGENT_ID", "te-claude")
    monkeypatch.setenv("AGENT_RUNTIME", "claude")

    result = runner.invoke(app, ["claim", str(repo)])
    assert result.exit_code == 0, result.output
    assert "0001" in result.output

    task = _read_task(repo, "0001")
    assert task["status"] == "claimed"
    assert task["claimed_by"] == "te-claude"
    assert task["runtime"] == "claude"
    assert task["claimed_at"].endswith("Z")
    # 0002 untouched
    assert _read_task(repo, "0002")["status"] == "pending"
    # commit landed
    assert "claimed by te-claude" in _git_log(repo)


def test_claim_requires_agent_id(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_pending(repo, "0001")
    monkeypatch.delenv("AGENT_ID", raising=False)
    monkeypatch.setenv("AGENT_RUNTIME", "claude")
    result = runner.invoke(app, ["claim", str(repo)])
    assert result.exit_code == 2
    assert "AGENT_ID" in result.output


def test_claim_requires_valid_runtime(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_pending(repo, "0001")
    monkeypatch.setenv("AGENT_ID", "te-claude")
    monkeypatch.setenv("AGENT_RUNTIME", "bard")
    result = runner.invoke(app, ["claim", str(repo)])
    assert result.exit_code == 2
    assert "AGENT_RUNTIME" in result.output


def test_claim_no_pending_tasks_exits_1(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_pending(
        repo,
        "0001",
        status="completed",
        completed_at="2026-04-27T14:00:00Z",
    )
    monkeypatch.setenv("AGENT_ID", "te-claude")
    monkeypatch.setenv("AGENT_RUNTIME", "claude")
    result = runner.invoke(app, ["claim", str(repo)])
    assert result.exit_code == 1
    assert "no pending tasks" in result.output


def test_claim_missing_agents_dir_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.setenv("AGENT_ID", "te-claude")
    monkeypatch.setenv("AGENT_RUNTIME", "claude")
    result = runner.invoke(app, ["claim", str(tmp_path)])
    assert result.exit_code == 1
    assert ".agents/tasks" in result.output


# --- list -------------------------------------------------------------------


def test_list_empty_repo_no_output(repo: Path) -> None:
    result = runner.invoke(app, ["list", str(repo)])
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_list_shows_all_tasks_with_header(repo: Path) -> None:
    _add_pending(repo, "0001")
    _add_pending(
        repo,
        "0002",
        status="claimed",
        claimed_by="te-claude",
        runtime="claude",
        claimed_at="2026-04-27T13:01:00Z",
    )
    result = runner.invoke(app, ["list", str(repo)])
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert lines[0].startswith("id")
    assert "status" in lines[0]
    assert any("0001" in line and "pending" in line for line in lines[1:])
    assert any(
        "0002" in line and "claimed" in line and "te-claude" in line
        for line in lines[1:]
    )


def test_list_status_filter(repo: Path) -> None:
    _add_pending(repo, "0001")
    _add_pending(repo, "0002", status="claimed", claimed_by="x", runtime="claude")
    _add_pending(
        repo,
        "0003",
        status="completed",
        claimed_by="x",
        runtime="claude",
        claimed_at="2026-04-27T13:01:00Z",
        completed_at="2026-04-27T13:02:00Z",
    )
    result = runner.invoke(app, ["list", str(repo), "--status", "claimed"])
    assert result.exit_code == 0
    assert "0002" in result.output
    assert "0001" not in result.output
    assert "0003" not in result.output


def test_list_missing_agents_dir_exits_1(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    result = runner.invoke(app, ["list", str(tmp_path)])
    assert result.exit_code == 1


# --- complete ---------------------------------------------------------------


def test_complete_marks_claimed_task_done(repo: Path) -> None:
    _add_pending(
        repo,
        "0001",
        status="claimed",
        claimed_by="te-claude",
        runtime="claude",
        claimed_at="2026-04-27T13:01:00Z",
    )
    result = runner.invoke(app, ["complete", str(repo), "0001"])
    assert result.exit_code == 0, result.output
    assert "0001" in result.output

    task = _read_task(repo, "0001")
    assert task["status"] == "completed"
    assert task["completed_at"].endswith("Z")
    # Earlier claim metadata preserved
    assert task["claimed_by"] == "te-claude"
    assert task["runtime"] == "claude"
    assert "task 0001: completed" in _git_log(repo)


def test_complete_unknown_id_exits_1(repo: Path) -> None:
    result = runner.invoke(app, ["complete", str(repo), "9999"])
    assert result.exit_code == 1
    assert "9999" in result.output
