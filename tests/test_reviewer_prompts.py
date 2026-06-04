"""Structural tests for the vendor-neutral reviewer prompts.

The three reviewer prompts (pragmatic / security / docs) are inputs to
the per-runtime review steps in the GH Action (Track 1 #6, separate
session). They are vendor-neutral by construction: capabilities, not
tool names; severity tags, not vendor-specific comment APIs.

These tests assert the **structure** so a careless edit can't drop a
required section. Content quality is reviewed by humans.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / ".agents" / "prompts"
_REQUIRED_SECTIONS = (
    "## Capabilities required",
    "## In-scope",
    "## Out-of-scope",
    "## Output format",
    "## Anti-patterns",
)
_SEVERITY_TAGS = ("[BLOCKER]", "[MAJOR]", "[MINOR]", "[NIT]", "[NOTE]")


@pytest.mark.parametrize(
    "prompt_name", ["pragmatic-reviewer", "security-reviewer", "docs-reviewer"]
)
def test_prompt_has_required_sections(prompt_name: str) -> None:
    text = (_PROMPTS_DIR / f"{prompt_name}.md").read_text()
    missing = [s for s in _REQUIRED_SECTIONS if s not in text]
    assert not missing, f"{prompt_name}.md missing sections: {missing}"


@pytest.mark.parametrize(
    "prompt_name", ["pragmatic-reviewer", "security-reviewer", "docs-reviewer"]
)
def test_prompt_references_severity_tags(prompt_name: str) -> None:
    """Every reviewer must reference at least the [BLOCKER] and [NOTE] tags
    so its output is interoperable with the standard summary template."""
    text = (_PROMPTS_DIR / f"{prompt_name}.md").read_text()
    for tag in ("[BLOCKER]", "[NOTE]"):
        assert tag in text, f"{prompt_name}.md doesn't mention {tag}"


@pytest.mark.parametrize(
    "prompt_name", ["pragmatic-reviewer", "security-reviewer", "docs-reviewer"]
)
def test_prompt_has_runtime_placeholder_in_summary(prompt_name: str) -> None:
    """The summary template prefixes comments with [<runtime>/lens] so the
    same prompt can be driven by Claude / Codex / Mistral and the comments
    stay distinguishable on the PR."""
    text = (_PROMPTS_DIR / f"{prompt_name}.md").read_text()
    assert "<runtime>/" in text, (
        f"{prompt_name}.md doesn't use <runtime>/lens prefix in summary template"
    )


def test_no_vendor_specific_tool_names_in_prompts() -> None:
    """Vendor-neutrality guard: prompts must not hardcode vendor-specific tool
    names. Capabilities are described in prose; the per-runtime mapping lives
    in the GH Action workflow, not here."""
    forbidden = (
        "mcp__github_inline_comment__create_inline_comment",
        "Skill(",
        "anthropics/claude-code-action",
        "claude_args",
    )
    for prompt in _PROMPTS_DIR.glob("*-reviewer.md"):
        text = prompt.read_text()
        for bad in forbidden:
            assert bad not in text, (
                f"{prompt.name} contains vendor-specific token {bad!r}"
            )
