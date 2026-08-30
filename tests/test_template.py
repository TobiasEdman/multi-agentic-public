"""Tests for ``agentic_task.template`` and ``templates/AGENTS.md.tmpl``.

Two layers of verification:

1. Unit tests for the renderer's contract (variable substitution, conditional
   blocks, flag handling).
2. Integration tests that render ``templates/AGENTS.md.tmpl`` with both
   ``repo_kind`` profiles and assert the right sections appear / disappear.

The integration tests are the verify-artefakt for Friction #2 commit 4 — they
prove the template can produce both single-agent and multi-agent variants of
AGENTS.md from one source.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_task.template import render

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = _REPO_ROOT / "templates" / "AGENTS.md.tmpl"


# --- Unit: renderer contract ------------------------------------------------


def test_variable_substitution() -> None:
    out = render("Hello {{NAME}}", {"NAME": "world"})
    assert out == "Hello world"


def test_unresolved_variable_left_intact() -> None:
    """Missing values fail loudly rather than render as empty string."""
    out = render("Hello {{NAME}}", {})
    assert out == "Hello {{NAME}}"


def test_conditional_block_kept_when_flag_set() -> None:
    tmpl = "before\n<!--IF foo-->\nkept\n<!--/IF foo-->\nafter\n"
    out = render(tmpl, {"flags": ["foo"]})
    assert "kept" in out
    assert "before" in out
    assert "after" in out


def test_conditional_block_dropped_when_flag_unset() -> None:
    tmpl = "before\n<!--IF foo-->\nkept\n<!--/IF foo-->\nafter\n"
    out = render(tmpl, {"flags": []})
    assert "kept" not in out
    assert "<!--IF" not in out  # marker stripped along with body
    assert "before" in out
    assert "after" in out


def test_two_blocks_with_different_flags() -> None:
    tmpl = (
        "<!--IF a-->\nblock-a\n<!--/IF a-->\n"
        "<!--IF b-->\nblock-b\n<!--/IF b-->\n"
    )
    out = render(tmpl, {"flags": ["a"]})
    assert "block-a" in out
    assert "block-b" not in out


def test_flag_as_bare_string_does_not_iterate_chars() -> None:
    """``flags="foo"`` would be a foot-gun if treated as iterable of chars."""
    tmpl = "<!--IF foo-->\nkept\n<!--/IF foo-->\n"
    out = render(tmpl, {"flags": "foo"})
    assert "kept" in out


def test_vars_inside_dropped_block_do_not_need_values() -> None:
    """Missing-value strictness must not bite for blocks that get dropped."""
    tmpl = "<!--IF on-->\n{{NEEDED}}\n<!--/IF on-->\nstay\n"
    # Flag off → block stripped → NEEDED never queried.
    out = render(tmpl, {"flags": []})
    assert out.strip() == "stay"


# --- Integration: AGENTS.md.tmpl produces both variants ---------------------


@pytest.fixture
def template_text() -> str:
    return _TEMPLATE.read_text()


_BASE_CONTEXT = {
    "NAME": "demo-repo",
    "PURPOSE": "A demo.",
    "STATUS": "alpha, private.",
    "BUILD_CMD": "uv sync && uv run pytest",
    "SMOKE_NOTE": "Smoke gate: imports clean.",
    "PATHS_TABLE": "| `src/` | source |",
}


def _ctx(profile: str) -> dict[str, object]:
    return {**_BASE_CONTEXT, "flags": [profile]}


def test_multi_agent_render_includes_extension_pointer(template_text: str) -> None:
    out = render(template_text, _ctx("multi-agent"))
    assert "conventions-multi-agent.md" in out
    assert "conventions-base.md" in out
    assert ".agents/tasks/" in out
    assert "co-authored-by-dual.sh" in out
    assert "## Tracks" in out
    assert "Multi-vendor trailers." in out


def test_single_agent_render_omits_multi_agent_pieces(template_text: str) -> None:
    out = render(template_text, _ctx("single-agent"))
    assert "conventions-base.md" in out
    # Multi-agent-only artefacts must not leak in:
    assert "conventions-multi-agent.md" in out  # OK — appears in the negation phrase
    assert ".agents/tasks/" not in out
    assert "co-authored-by-dual.sh" not in out
    assert "## Tracks" not in out
    assert "Multi-vendor trailers." not in out
    # Sanity: the single-agent prose appears
    assert "single-agent" in out
    assert "agent/<initials>/<area>-<slug>" in out


def test_no_unrendered_conditional_markers_in_either_profile(template_text: str) -> None:
    for profile in ("multi-agent", "single-agent"):
        out = render(template_text, _ctx(profile))
        assert "<!--IF" not in out, f"unrendered IF marker in {profile} render"
        assert "<!--/IF" not in out, f"unrendered /IF marker in {profile} render"


def test_no_unresolved_placeholders_in_either_profile(template_text: str) -> None:
    """All known placeholders must resolve when the full _BASE_CONTEXT is given."""
    for profile in ("multi-agent", "single-agent"):
        out = render(template_text, _ctx(profile))
        assert "{{" not in out, f"unresolved placeholder in {profile} render"


_MANAGED_START = "<!-- agentic-task:coordination:start -->"
_MANAGED_END = "<!-- agentic-task:coordination:end -->"


def _strip_managed_blocks(text: str) -> str:
    """Drop installer-managed regions from a live AGENTS.md.

    `agentic-task init` appends its own coordination section *after* the
    template has been rendered, so those headers exist in every correctly
    installed repo by design and can never appear in a template render.
    Comparing them would fail the dogfooding check on exactly the repos
    that are properly installed.
    """
    kept: list[str] = []
    skipping = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == _MANAGED_START:
            skipping = True
        elif stripped == _MANAGED_END:
            skipping = False
        elif not skipping:
            kept.append(line)
    return "\n".join(kept)


def test_multi_agent_render_against_repo_agents_md(template_text: str) -> None:
    """Sanity check: rendering with multi-agentic's own values produces text
    structurally consistent with the live AGENTS.md (same section headers).

    This is not a byte-for-byte comparison — the template is a generic shape
    that can grow/shrink prose between renders. The contract is that the
    *section structure* matches, so dogfooding stays honest. Installer-managed
    blocks are excluded: they are appended post-render and are not the
    template's to produce.
    """
    live_agents_md = _strip_managed_blocks((_REPO_ROOT / "AGENTS.md").read_text())
    rendered = render(
        template_text,
        {
            **_BASE_CONTEXT,
            "NAME": "multi-agentic",
            "flags": ["multi-agent"],
        },
    )
    live_headers = [ln for ln in live_agents_md.splitlines() if ln.startswith("## ")]
    rendered_headers = [ln for ln in rendered.splitlines() if ln.startswith("## ")]
    assert live_headers == rendered_headers, (
        f"section structure drift between AGENTS.md and template render:\n"
        f"  live:     {live_headers}\n"
        f"  rendered: {rendered_headers}"
    )
