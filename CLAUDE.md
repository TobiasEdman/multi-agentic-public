# CLAUDE.md — multi-agentic (Claude Code addendum)

> **Read [`AGENTS.md`](AGENTS.md) first.** It is the primary, vendor-neutral agent-facing document. This file only adds Claude Code-specific quirks on top.

## What lives here vs. in AGENTS.md

`AGENTS.md` carries: repo identity, build/test, paths, conventions, multi-agent spec pointers, tracks. Don't duplicate it here.

This file holds **only** the things that are Claude-Code-specific and would be wrong (or weird) in a vendor-neutral document.

## Claude Code-specific quirks

- **Hook enforcement of session conduct.** [`AGENTS.md`](AGENTS.md) §Session conduct §1–§7 is the vendor-neutral source of the rules. Claude Code sessions get hook-level enforcement on top: `~/.claude/hooks/active-jobs-guard.sh` (rule §3, running code is read-only), `~/.claude/hooks/verify-artefakt.sh` (rule §6, `Verified-by:` trailer), and `~/.claude/hooks/co-authored-by.sh` (rule §7, attribution trailer). The personal continuity layer (`~/.claude/CLAUDE.md`, skills, checkpoints) is convenience for the human's own workflow; this repo does not require it to be installed.
- **Skills.** `/brief`, `/checkpoint`, `/recall`, `/review` are expected to work. Mid-session checkpoints land in `~/.claude/checkpoints/multi-agentic/`.
- **Co-Authored-By trailer.** The `~/.claude/hooks/co-authored-by.sh` hook handles this for Claude. The vendor-neutral `hooks/co-authored-by-dual.sh` in this repo (stub) is the extension that future Codex/Mistral sessions will use.
- **Path-scoped rules.** `.claude/rules/` is the path-scoped rules directory (per `rise-repo-bootstrap` W2.4). Empty for now — add files here as the repo grows past ~200 lines of CLAUDE.md / AGENTS.md guidance.

## Verification convention

Per `AGENTS.md` § Build & test:

- **Code change:** `pytest tests/` passes (existing + new tests for the change).
- **Public interface change:** bump version in `pyproject.toml` + CHANGELOG line (CHANGELOG TBD).
- **Smoke:** `PYTHONPATH=src python -c "import agentic_task"` succeeds.

Without a verification artefact: no commit. If verification is impossible in this environment, say so explicitly and ask the user to verify before closing the task.

## Files that must match other files

- [`AGENTS.md`](AGENTS.md) ↔ [`templates/AGENTS.md.tmpl`](templates/AGENTS.md.tmpl) — the template is a vendor-neutral parametrisation of this file (rendered with `repo_kind=multi-agent` for this repo). If they drift, fix the template (this repo dogfoods its own toolkit).
- [`docs/conventions-base.md`](docs/conventions-base.md) and [`docs/conventions-multi-agent.md`](docs/conventions-multi-agent.md) are **canonical content, not templates** — copied verbatim into target repos by the installer (single-agent repos take base only; multi-agent repos take both). If either changes here, every installer-touched repo needs an update — tracked via `agentic-task` install vehicle, not by symlink. The split was introduced 2026-04-27 per `docs/track1-replication-findings.md` Friction #2.
- [`hooks/co-authored-by-dual.sh`](hooks/co-authored-by-dual.sh) ↔ `~/.claude/hooks/co-authored-by.sh` — the dual-vendor hook here will eventually replace the Claude-only hook. Until it does, the global hook is canonical.
- [`.github/workflows/agent-review.yml`](.github/workflows/agent-review.yml) ↔ [`.agents/prompts/{pragmatic,security,docs}-reviewer.md`](.agents/prompts/) — the workflow loads the three reviewer prompts from `.agents/prompts/` at runtime (see the `prompt:` block, `Read .agents/prompts/...-reviewer.md` line). If the workflow is replicated to another repo, `.agents/prompts/` must travel with it or the review job fails on a missing path. Discovered 2026-04-27 per `docs/track1-replication-findings.md` Friction #3.
- [`hooks/worktree-create.sh`](hooks/worktree-create.sh) + [`hooks/worktree-remove.sh`](hooks/worktree-remove.sh) ↔ [`.claude/settings.json`](.claude/settings.json) — the project-scoped settings registers `WorktreeCreate`/`WorktreeRemove` against `$CLAUDE_PROJECT_DIR/hooks/worktree-{create,remove}.sh`. The repo files are **canonical** (no symlinks); the hook only fires when `claude -w` runs from inside this repo. [`tests/test_worktree_hooks.py`](tests/test_worktree_hooks.py) exercises the script directly via piped JSON. Per-user behaviour overrides live in `~/.claude/worktree-config/<repo>.env` — e.g. `BRANCH_PREFIX="agent/te/claude/multi-agentic-"` + `INSTALL_CMD="uv sync"` for this repo. The hook sources `default.env` first, then `<repo>.env` on top. Earlier attempt at user-global registration in `~/.claude/settings.json` failed validation ("Invalid key in record" for `WorktreeCreate` at the global scope) — these events are project-scoped only. Discovered 2026-04-28.

<!-- agentic-task:coordination:start -->
## Cross-runtime coordination mechanics

Shared policy lives in `AGENTS.md`. Claude-specific hooks may enforce it but
must not weaken or duplicate that policy. Use a Claude worktree for every
writing session and the vendor-neutral `agentic-task` CLI for task claims.
<!-- agentic-task:coordination:end -->
