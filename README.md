# multi-agentic

Vendor-neutral toolkit for multi-agent collaborative coding — writer/reviewer pattern, branch-per-agent, file-locks, multi-vendor attribution. Implementation home for the Tier 2 plan; the spec lives at [`docs/specs/tier2_multi_agent.md`](docs/specs/tier2_multi_agent.md).

## Status

**Alpha.** Scaffolded 2026-04-27. Public mirror as of 2026-06. Vendor-neutral spec + reference implementation for Claude Code; Codex and Mistral track adapters are placeholders pending runtime availability.

## Companion: lessons repo

The observation layer behind these conventions lives at [**`agentic-workflow-lessons`**](https://github.com/TobiasEdman/agentic-workflow-lessons) — a 2026 retrospective on long-running Claude Code sessions + post-rework follow-up + drop-in `~/.claude/` starter pack. If you arrived here cold, read the lessons-repo's [`docs/lessons/multi_user_multi_agent.md`](https://github.com/TobiasEdman/agentic-workflow-lessons/blob/main/docs/lessons/multi_user_multi_agent.md) first — it's the four-lens research synthesis that the conventions here distill.

## Source spec

The canonical spec for the toolkit lives here:

- [`docs/specs/tier2_multi_agent.md`](docs/specs/tier2_multi_agent.md) (v2, multi-vendor).

The vendor-neutral convention spec lives in two layers: [`docs/conventions-base.md`](docs/conventions-base.md) (universal — per-task commits, verify-artefakt, worktree lifecycle, writer/reviewer, CI-bot) and [`docs/conventions-multi-agent.md`](docs/conventions-multi-agent.md) (extension — file locks, branch-per-runtime, multi-vendor trailers, cross-runtime MCP). Single-agent repos only need base.

## For agents

If you are a Claude Code / Codex / Mistral session opened in this repo, read [`AGENTS.md`](AGENTS.md) first. Claude-specific quirks are in [`CLAUDE.md`](CLAUDE.md) as an addendum.

## Setup

```bash
uv sync && uv run pytest
```

`uv.lock` is committed release input, not local cache state. Regenerate it with
`uv --no-config lock` whenever `pyproject.toml` changes, verify with
`uv --no-config lock --check --offline`, and commit both files together.

Or with plain pip:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Usage — `agentic-task` CLI

Vendor-neutral command for the `.agents/tasks/` lock protocol (plan §A.1). All three runtimes (Claude / Codex / Mistral) call the same binary; coordination is via git push collisions.

```bash
# Claim the lowest-id pending task. Sets status=claimed + claimed_by +
# runtime + claimed_at, commits, pushes. On non-fast-forward push:
# pull --rebase + retry against another pending task. Prints the
# claimed task id on success.
AGENT_ID=te-claude AGENT_RUNTIME=claude  agentic-task claim  <repo-path>

# List tasks as a plain table. --status filters by lifecycle state.
agentic-task list  <repo-path> [--status pending|claimed|in_progress|completed|blocked|abandoned]

# Mark a task completed. Sets status=completed + completed_at, commits,
# pushes. Preserves claimed_by/runtime/claimed_at.
agentic-task complete  <repo-path> <task-id>
```

`AGENT_RUNTIME` must be one of `claude | codex | mistral`. The schema for `.agents/tasks/*.json` is `agentic_task.schema.TASK_SCHEMA` — same shape as the on-disk `.agents/schema.json` per repo (Track 1 #1 ships that file).

## License

MIT. See [LICENSE](LICENSE).
