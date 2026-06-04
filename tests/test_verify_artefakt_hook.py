"""Tests for ~/.claude/hooks/verify-artefakt.sh — §6 verify-artefakt enforcement.

The hook is a PreToolUse Bash hook (lives in ~/.claude/hooks/, not in this repo)
that surfaces a UI prompt when a `git commit` lacks a `Verified-by:` trailer.
Pattern mirrors ~/.claude/hooks/co-authored-by.sh.

Tests pipe a JSON payload to the hook and assert on stdout + exit code.

Source rule: ~/.claude/CLAUDE.md §6.
Hook canonical location: ~/.claude/hooks/verify-artefakt.sh.

The hook is global — these tests verify the canonical implementation, not
a repo-side copy. If the global hook is missing, tests skip rather than
fail (the dual-trailer hook in this repo follows the same pattern).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

_HOOK = Path.home() / ".claude" / "hooks" / "verify-artefakt.sh"

pytestmark = pytest.mark.skipif(
    not _HOOK.exists(),
    reason="verify-artefakt.sh not installed at ~/.claude/hooks/",
)


def _run(payload: dict) -> tuple[int, str]:
    """Pipe the JSON payload to the hook; return (returncode, stdout)."""
    r = subprocess.run(
        ["bash", str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout


def _bash_commit(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# --- Pass: trailer present (any case, any non-empty value) ----------------


@pytest.mark.parametrize(
    "trailer",
    [
        "Verified-by: pytest tests/ — 78 passed",
        "Verified-by: smoke — import succeeded",
        "Verified-by: trivial — typo fix",
        "Verified-by: cannot-verify — env-dependent",
        "verified-by: pytest",  # case variant
        "Verified-By: pytest",  # case variant
        "VERIFIED-BY: pytest",  # case variant
    ],
)
def test_trailer_present_silent(trailer: str) -> None:
    cmd = f'git commit -m "feat: x\\n\\n{trailer}"'
    rc, out = _run(_bash_commit(cmd))
    assert rc == 0, f"hook returned {rc} for trailer {trailer!r}"
    assert out == "", f"hook emitted output for valid trailer {trailer!r}: {out!r}"


# --- Pass: not a commit ----------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "pytest tests/",
        "git status",
        "git log --oneline",
        "git diff",
        "git stash",
        "echo 'git commit' # not actually a commit",
    ],
)
def test_non_commit_silent(command: str) -> None:
    rc, out = _run(_bash_commit(command))
    assert rc == 0
    assert out == ""


# --- Pass: not a Bash tool -------------------------------------------------


def test_non_bash_tool_silent() -> None:
    rc, out = _run({"tool_name": "Read", "tool_input": {"command": "git commit -m foo"}})
    assert rc == 0
    assert out == ""


def test_edit_tool_silent() -> None:
    rc, out = _run({"tool_name": "Edit", "tool_input": {"command": "git commit"}})
    assert rc == 0
    assert out == ""


# --- Pass: amend with no-edit (can't inject safely) -----------------------


def test_amend_no_edit_silent() -> None:
    rc, out = _run(_bash_commit("git commit --amend --no-edit"))
    assert rc == 0
    assert out == ""


# --- Pass: commit without -m (no message to inject into) ------------------


def test_commit_no_m_flag_silent() -> None:
    rc, out = _run(_bash_commit("git commit"))
    assert rc == 0, "git commit without -m opens $EDITOR; hook can't help, must defer"
    assert out == ""


# --- Ask: missing trailer --------------------------------------------------


def test_missing_trailer_asks() -> None:
    rc, out = _run(_bash_commit('git commit -m "feat: x"'))
    assert rc == 0, "hook always exits 0; signals via permissionDecision in JSON"
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert payload["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert "Verified-by" in payload["hookSpecificOutput"]["permissionDecisionReason"]
    assert "§6" in payload["hookSpecificOutput"]["permissionDecisionReason"]


def test_missing_trailer_with_body_asks() -> None:
    cmd = 'git commit -m "feat: x\\n\\nLong body explaining the change\\n\\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"'
    rc, out = _run(_bash_commit(cmd))
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "ask", (
        "Co-Authored-By alone (no Verified-by) must still ask — §6 is independent of §7"
    )


def test_empty_trailer_value_asks() -> None:
    """`Verified-by:` with no value must not satisfy the hook —
    the point is to force a verification claim, not just a label."""
    cmd = 'git commit -m "feat: x\\n\\nVerified-by: "'
    rc, out = _run(_bash_commit(cmd))
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "ask"


# --- Hook composition: §6 and §7 are independent --------------------------


def test_only_co_authored_by_still_asks_verify() -> None:
    """A commit with only Co-Authored-By (§7) but no Verified-by (§6)
    must still trigger this hook. The two rules are orthogonal."""
    cmd = (
        'git commit -m "feat: x\\n\\n'
        'Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"'
    )
    rc, out = _run(_bash_commit(cmd))
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_both_trailers_silent() -> None:
    """A commit with both §6 and §7 trailers passes both hooks."""
    cmd = (
        'git commit -m "feat: x\\n\\n'
        'Verified-by: pytest tests/ — 78 passed\\n'
        'Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"'
    )
    rc, out = _run(_bash_commit(cmd))
    assert rc == 0
    assert out == ""


# --- Robustness: malformed payload ----------------------------------------


def test_empty_payload_silent() -> None:
    """Malformed JSON should not crash; hook should fail open."""
    r = subprocess.run(
        ["bash", str(_HOOK)],
        input="",
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0


def test_unknown_tool_silent() -> None:
    rc, out = _run({"tool_name": "Glob", "tool_input": {"pattern": "*.py"}})
    assert rc == 0
    assert out == ""
