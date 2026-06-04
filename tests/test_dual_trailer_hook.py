"""Tests for hooks/co-authored-by-dual.sh — vendor-neutral attribution validator.

The hook is a bash script; pytest spawns it against fixture commit-msg
files and asserts exit codes per plan §G acceptance matrix.

Source spec: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §G.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parent.parent / "hooks" / "co-authored-by-dual.sh"


def _run(msg: str, tmp_path: Path) -> int:
    msg_file = tmp_path / "msg"
    msg_file.write_text(msg)
    r = subprocess.run(
        [str(_HOOK), str(msg_file)],
        capture_output=True,
        text=True,
    )
    return r.returncode


# --- Accept: agent attribution present -------------------------------------


@pytest.mark.parametrize(
    "trailer",
    [
        "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>",
        "Co-Authored-By: Codex <noreply@openai.com>",
        "Co-Authored-By: Mistral <noreply@mistral.ai>",
        "Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>",  # case variant
        "Assisted-by: Claude Opus 4.6 <noreply@anthropic.com>",
        "Assisted-by: Codex <noreply@openai.com>",
        "Assisted-By: Mistral <noreply@mistral.ai>",
        "Codex-Generated: gpt-5.4-code-2026-04-15",
    ],
)
def test_recognised_trailer_passes(trailer: str, tmp_path: Path) -> None:
    msg = f"feat: x\n\nbody\n\n{trailer}\n"
    assert _run(msg, tmp_path) == 0, f"trailer should pass: {trailer!r}"


# --- Accept: merge/revert commits inherit attribution from parents ---------


def test_merge_commit_skipped(tmp_path: Path) -> None:
    assert _run("Merge branch 'feature' into main\n", tmp_path) == 0


def test_revert_commit_skipped(tmp_path: Path) -> None:
    msg = "Revert \"feat: x\"\n\nThis reverts commit abcdef.\n"
    assert _run(msg, tmp_path) == 0


# --- Accept: empty messages defer to the regular commit-msg hook -----------


def test_empty_message_skipped(tmp_path: Path) -> None:
    assert _run("\n\n", tmp_path) == 0


# --- Reject: no agent attribution ------------------------------------------


def test_no_trailer_fails(tmp_path: Path) -> None:
    assert _run("feat: x\n\njust a body\n", tmp_path) == 1


def test_human_only_co_authored_by_fails(tmp_path: Path) -> None:
    """A Co-Authored-By: trailer pointing at a human (no vendor signal)
    is not agent attribution. Must fail."""
    msg = "feat: x\n\nCo-Authored-By: Test User <test@example.com>\n"
    assert _run(msg, tmp_path) == 1


# --- Reject: usage errors ---------------------------------------------------


def test_missing_file_exits_2(tmp_path: Path) -> None:
    r = subprocess.run(
        [str(_HOOK), str(tmp_path / "does-not-exist")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2


def test_no_arg_exits_nonzero(tmp_path: Path) -> None:
    r = subprocess.run([str(_HOOK)], capture_output=True, text=True)
    assert r.returncode != 0


# --- Mixed: human + agent trailers should still pass -----------------------


def test_human_and_agent_trailers_pass(tmp_path: Path) -> None:
    msg = (
        "feat: x\n\n"
        "Co-Authored-By: Test User <test@example.com>\n"
        "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>\n"
    )
    assert _run(msg, tmp_path) == 0
