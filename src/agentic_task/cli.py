"""agentic-task — vendor-neutral CLI for multi-agent task claim/list/complete.

Plan: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §A.

The three subcommands implement the lock protocol from §A.1: claim a
``pending`` task by writing JSON + committing + pushing; if push fails
(non-fast-forward) another agent already claimed it — pull --rebase and
try a different task. Vendor-neutral: any runtime (Claude / Codex /
Mistral) can call this CLI via its Bash-equivalent tool.

Subcommand bodies are filled in over commits 2–4. This file (commit 1)
wires the typer entrypoint and stubs the three commands.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import typer

from agentic_task.schema import validate_task

_VALID_RUNTIMES = {"claude", "codex", "mistral"}
_MAX_CLAIM_RETRIES = 3

app = typer.Typer(
    name="agentic-task",
    help=(
        "Vendor-neutral CLI for the .agents/tasks/ task-claim protocol. "
        "Set AGENT_ID + AGENT_RUNTIME (claude|codex|mistral) before claim."
    ),
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def claim(
    repo: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Path to a git repo containing .agents/tasks/.",
    ),
) -> None:
    """Claim the first pending task in <repo>/.agents/tasks/.

    Writes status=claimed, claimed_by=$AGENT_ID, runtime=$AGENT_RUNTIME,
    claimed_at=now. Commits + pushes. On push failure (non-fast-forward),
    pulls --rebase and tries another pending task.
    """
    agent_id = os.environ.get("AGENT_ID", "").strip()
    agent_runtime = os.environ.get("AGENT_RUNTIME", "").strip()
    if not agent_id:
        typer.echo("AGENT_ID env var required", err=True)
        raise typer.Exit(2)
    if agent_runtime not in _VALID_RUNTIMES:
        typer.echo(
            f"AGENT_RUNTIME must be one of: {', '.join(sorted(_VALID_RUNTIMES))}",
            err=True,
        )
        raise typer.Exit(2)

    tasks_dir = repo / ".agents" / "tasks"
    if not tasks_dir.is_dir():
        typer.echo(f"{tasks_dir} not found", err=True)
        raise typer.Exit(1)

    for _ in range(_MAX_CLAIM_RETRIES):
        task_file = _find_first_pending(tasks_dir)
        if task_file is None:
            typer.echo("no pending tasks", err=True)
            raise typer.Exit(1)

        task = json.loads(task_file.read_text())
        now = _utcnow_iso()
        task["status"] = "claimed"
        task["claimed_by"] = agent_id
        task["runtime"] = agent_runtime
        task["claimed_at"] = now
        task["updated_at"] = now
        validate_task(task)
        _write_task(task_file, task)

        _git(repo, "add", str(task_file))
        _git(repo, "commit", "-m", f"task {task['id']}: claimed by {agent_id}")

        if _try_push(repo):
            typer.echo(task["id"])
            return

        # Push failed (non-fast-forward) — undo local commit, rebase, retry
        # against whatever the remote now considers pending.
        _git(repo, "reset", "--hard", "HEAD~1")
        _git(repo, "pull", "--rebase")

    typer.echo("could not claim task after retries", err=True)
    raise typer.Exit(1)


@app.command(name="list")
def list_tasks(
    repo: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Path to a git repo containing .agents/tasks/.",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter to tasks with this status (pending|claimed|in_progress|completed|blocked|abandoned).",
    ),
) -> None:
    """List tasks in <repo>/.agents/tasks/ as a plain table."""
    tasks_dir = repo / ".agents" / "tasks"
    if not tasks_dir.is_dir():
        typer.echo(f"{tasks_dir} not found", err=True)
        raise typer.Exit(1)

    rows: list[tuple[str, str, str, str, str]] = []
    for f in sorted(tasks_dir.glob("*.json")):
        try:
            t = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if status is not None and t.get("status") != status:
            continue
        rows.append(
            (
                str(t.get("id", "?")),
                str(t.get("status", "?")),
                str(t.get("claimed_by") or "-"),
                str(t.get("runtime") or "-"),
                str(t.get("subject", "")),
            )
        )

    if not rows:
        return

    headers = ("id", "status", "claimed_by", "runtime", "subject")
    widths = [
        max(len(headers[i]), max(len(r[i]) for r in rows)) for i in range(len(headers))
    ]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    typer.echo(fmt.format(*headers))
    for r in rows:
        typer.echo(fmt.format(*r))


@app.command()
def complete(
    repo: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Path to a git repo containing .agents/tasks/.",
    ),
    task_id: str = typer.Argument(..., help="4-digit task id, e.g. 0001."),
) -> None:
    """Mark <task_id> as completed in <repo>/.agents/tasks/."""
    tasks_dir = repo / ".agents" / "tasks"
    task_file = tasks_dir / f"{task_id}.json"
    if not task_file.is_file():
        typer.echo(f"task {task_id} not found at {task_file}", err=True)
        raise typer.Exit(1)

    task = json.loads(task_file.read_text())
    now = _utcnow_iso()
    task["status"] = "completed"
    task["completed_at"] = now
    task["updated_at"] = now
    validate_task(task)
    _write_task(task_file, task)

    _git(repo, "add", str(task_file))
    _git(repo, "commit", "-m", f"task {task_id}: completed")
    _try_push(repo)
    typer.echo(task_id)


def main() -> None:
    """Console-script entrypoint. Wired via [project.scripts] in pyproject.toml."""
    app()


# --- helpers ----------------------------------------------------------------


def _utcnow_iso() -> str:
    """Return current UTC time as ``YYYY-MM-DDTHH:MM:SSZ`` (schema date-time format)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(
    repo: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _has_remote(repo: Path) -> bool:
    return bool(_git(repo, "remote").stdout.strip())


def _try_push(repo: Path) -> bool:
    """Push if a remote is configured. No remote → treat as success (local-only repo)."""
    if not _has_remote(repo):
        return True
    return _git(repo, "push", check=False).returncode == 0


def _find_first_pending(tasks_dir: Path) -> Path | None:
    """Return the lowest-id ``pending`` task file, ignoring archive/."""
    for f in sorted(tasks_dir.glob("*.json")):
        try:
            t = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if t.get("status") == "pending":
            return f
    return None


def _write_task(path: Path, task: dict) -> None:
    """Write task JSON deterministically (sorted-ish keys, trailing newline)."""
    path.write_text(json.dumps(task, indent=2) + "\n")


if __name__ == "__main__":
    main()
