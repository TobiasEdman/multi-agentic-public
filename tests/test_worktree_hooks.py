"""Tests for hooks/worktree-create.sh + hooks/worktree-remove.sh.

The hooks are bash scripts adapted from tfriedel/claude-worktree-hooks (MIT)
per agentic_workflow/docs/plans/tier2_multi_agent.md §B.2. They run as
Claude Code WorktreeCreate/WorktreeRemove hooks; pytest exercises them
against a temp git repo with HOME overridden so the per-repo config
lookup (~/.claude/worktree-config/<repo>.env) is hermetic.

Verifies plan §B.4:
  - stdout = exactly the worktree path (Claude parses it)
  - .env.local carries a deterministic DEV_PORT in 3100-9999
  - branch is created with the configured prefix
  - remove.sh tears down both worktree and branch
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CREATE = _REPO_ROOT / "hooks" / "worktree-create.sh"
_REMOVE = _REPO_ROOT / "hooks" / "worktree-remove.sh"


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Init a fresh git repo with one commit, return its path."""
    r = tmp_path / "demo-repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test")
    (r / "README.md").write_text("demo\n")
    _git(r, "add", "README.md")
    _git(r, "commit", "-q", "-m", "init")
    return r


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    """A tmp HOME with an empty default worktree-config (default prefix)."""
    home = tmp_path / "home"
    cfg = home / ".claude" / "worktree-config"
    cfg.mkdir(parents=True)
    (cfg / "default.env").write_text(
        'BRANCH_PREFIX="worktree-"\n'
        'ENV_FILES=".env .env.local"\n'
        'COPY_DIRS=""\n'
        'INSTALL_CMD=""\n'
    )
    return home


def _create(repo: Path, home: Path, name: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(home), "CLAUDE_PROJECT_DIR": str(repo)}
    return subprocess.run(
        ["bash", str(_CREATE)],
        input=json.dumps({"name": name}),
        text=True,
        capture_output=True,
        env=env,
    )


def _remove(worktree: Path, home: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(
        ["bash", str(_REMOVE)],
        input=json.dumps({"worktree_path": str(worktree)}),
        text=True,
        capture_output=True,
        env=env,
    )


# --- Create -----------------------------------------------------------------


def test_create_stdout_is_only_worktree_path(repo: Path, fake_home: Path) -> None:
    r = _create(repo, fake_home, "feat-x")
    assert r.returncode == 0, r.stderr
    expected = repo / ".claude" / "worktrees" / "feat-x"
    assert r.stdout.strip() == str(expected)
    # Nothing else may sneak onto stdout — Claude parses it as the path.
    assert r.stdout.count("\n") == 1


def test_create_writes_dev_port_in_range(repo: Path, fake_home: Path) -> None:
    r = _create(repo, fake_home, "feat-x")
    assert r.returncode == 0, r.stderr
    env_local = Path(r.stdout.strip()) / ".env.local"
    line = next(
        (ln for ln in env_local.read_text().splitlines() if ln.startswith("DEV_PORT=")),
        None,
    )
    assert line is not None, env_local.read_text()
    port = int(line.split("=", 1)[1])
    assert 3100 <= port <= 9999


def test_create_uses_default_branch_prefix(repo: Path, fake_home: Path) -> None:
    r = _create(repo, fake_home, "feat-x")
    assert r.returncode == 0, r.stderr
    branch = _git(repo, "-C", r.stdout.strip(), "branch", "--show-current")
    # `git -C <path> -C <inner>` chains; branch shown is for the worktree
    assert branch == "worktree-feat-x"


def test_create_per_repo_override(repo: Path, fake_home: Path) -> None:
    """A <repo>.env file overrides default.env (vendor-neutral prefix)."""
    cfg = fake_home / ".claude" / "worktree-config" / f"{repo.name}.env"
    cfg.write_text('BRANCH_PREFIX="agent/te/claude/"\n')
    r = _create(repo, fake_home, "feat-x")
    assert r.returncode == 0, r.stderr
    branch = _git(repo, "-C", r.stdout.strip(), "branch", "--show-current")
    assert branch == "agent/te/claude/feat-x"


def test_create_port_is_deterministic(repo: Path, fake_home: Path) -> None:
    """Same slug → same port across separate runs."""
    r1 = _create(repo, fake_home, "feat-x")
    assert r1.returncode == 0, r1.stderr
    port1 = (Path(r1.stdout.strip()) / ".env.local").read_text()
    _remove(Path(r1.stdout.strip()), fake_home)
    r2 = _create(repo, fake_home, "feat-x")
    assert r2.returncode == 0, r2.stderr
    port2 = (Path(r2.stdout.strip()) / ".env.local").read_text()
    assert port1 == port2


# --- Remove -----------------------------------------------------------------


def test_remove_tears_down_worktree_and_branch(
    repo: Path, fake_home: Path
) -> None:
    r = _create(repo, fake_home, "feat-x")
    assert r.returncode == 0, r.stderr
    wt = Path(r.stdout.strip())
    assert wt.exists()

    rm = _remove(wt, fake_home)
    assert rm.returncode == 0, rm.stderr
    assert not wt.exists()
    branches = _git(repo, "branch", "--list", "worktree-feat-x")
    assert branches == ""


def test_remove_is_idempotent_on_missing_path(
    repo: Path, fake_home: Path
) -> None:
    rm = _remove(repo / ".claude" / "worktrees" / "nope", fake_home)
    assert rm.returncode == 0
