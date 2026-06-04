"""Tests for .github/scripts/classify-pr.sh — risk-tier classifier.

Spec: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §C.1.

Each test builds a synthetic two-commit git repo, runs the classifier
against base..head, and asserts the (tier, lenses, models) output.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLASSIFY = _REPO_ROOT / ".github" / "scripts" / "classify-pr.sh"


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _init_repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test")
    (r / "seed.txt").write_text("seed\n")
    _git(r, "add", "seed.txt")
    _git(r, "commit", "-q", "-m", "seed")
    return r


def _classify(repo: Path, base: str = "HEAD~1", head: str = "HEAD") -> dict[str, str]:
    out = subprocess.check_output(
        ["bash", str(_CLASSIFY), base, head], cwd=repo, text=True
    )
    parsed: dict[str, str] = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            parsed[k] = v
    return parsed


# --- Tier boundaries --------------------------------------------------------


def test_trivial_one_file_few_lines(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "a.py").write_text("x = 1\n")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-q", "-m", "tiny")
    out = _classify(repo)
    assert out["tier"] == "trivial"
    assert out["lenses"] == '["docs"]'
    assert out["models"] == '["claude"]'


def test_lite_medium_change(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    for i in range(3):
        (repo / f"m{i}.py").write_text("\n".join(f"line_{j}" for j in range(20)) + "\n")
        _git(repo, "add", f"m{i}.py")
    _git(repo, "commit", "-q", "-m", "lite")
    out = _classify(repo)
    assert out["tier"] == "lite"
    assert out["lenses"] == '["quality","docs"]'


def test_full_large_change(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    # 1 file, 200 LOC — exceeds lite's 100-LOC ceiling
    (repo / "big.py").write_text("\n".join(f"line_{j}" for j in range(200)) + "\n")
    _git(repo, "add", "big.py")
    _git(repo, "commit", "-q", "-m", "big")
    out = _classify(repo)
    assert out["tier"] == "full"
    assert out["lenses"] == '["quality","security","docs"]'


def test_full_many_files(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    # 25 files, 1 LOC each — exceeds lite's 20-file ceiling
    for i in range(25):
        (repo / f"f{i}.py").write_text("x\n")
        _git(repo, "add", f"f{i}.py")
    _git(repo, "commit", "-q", "-m", "many")
    out = _classify(repo)
    assert out["tier"] == "full"


# --- Security path override -------------------------------------------------


@pytest.mark.parametrize("dir_name", ["auth", "crypto", "secrets", "security"])
def test_security_paths_force_full(tmp_path: Path, dir_name: str) -> None:
    """A 1-line tweak under auth/ etc. is full-tier regardless of size."""
    repo = _init_repo(tmp_path)
    sec = repo / dir_name
    sec.mkdir()
    (sec / "tweak.py").write_text("x\n")
    _git(repo, "add", f"{dir_name}/tweak.py")
    _git(repo, "commit", "-q", "-m", "tiny security tweak")
    out = _classify(repo)
    assert out["tier"] == "full", f"{dir_name}/ should force full tier"
    assert out["lenses"] == '["quality","security","docs"]'


def test_security_substring_in_filename_is_not_full(tmp_path: Path) -> None:
    """`securitylog.py` (no /) must not trigger the security-path override."""
    repo = _init_repo(tmp_path)
    (repo / "securitylog.py").write_text("x\n")
    _git(repo, "add", "securitylog.py")
    _git(repo, "commit", "-q", "-m", "log helper")
    out = _classify(repo)
    assert out["tier"] == "trivial"


# --- Output schema ----------------------------------------------------------


def test_outputs_contain_required_keys(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "a.py").write_text("x\n")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-q", "-m", "x")
    out = _classify(repo)
    assert {"tier", "lenses", "models", "loc", "files"} <= out.keys()
    assert out["loc"].isdigit()
    assert out["files"].isdigit()
