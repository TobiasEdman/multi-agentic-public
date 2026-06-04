# `.agents/` — vendor-neutral task-claim convention

This directory is the **coordination substrate** for multi-agent work in the repo. Any runtime — Claude Code, OpenAI Codex CLI, Mistral via OpenCode, a human with a text editor — reads and writes the same JSON files. Coordination happens through git push collisions, not through any vendor-specific orchestration layer.

Spec source: [`agentic_workflow/docs/plans/tier2_multi_agent.md`](https://github.com/TobiasEdman/agentic_workflow/blob/main/docs/plans/tier2_multi_agent.md) §A.

## Layout

```
.agents/
├── README.md     # this file
├── schema.json   # JSON Schema for tasks/*.json (draft 2020-12)
└── tasks/
    ├── 0001.json   # one task = one file (zero-padded 4-digit id)
    ├── 0002.json
    └── archive/
        └── YYYY-MM/   # tasks completed > 30 days ago, moved here
```

`schema.json` is generated from [`agentic_task.schema.TASK_SCHEMA`](../src/agentic_task/schema.py); a pytest test asserts they stay in lock-step.

## Lock protocol (from plan §A.1)

1. **Claim.** Agent picks a `pending` task, writes `status=claimed`, `claimed_by`, `runtime` (`claude|codex|mistral`), `claimed_at`. Commits, pushes.
2. **Push wins → lock acquired.** Push fails with non-fast-forward → another agent got there first. Run `git pull --rebase` and pick a different task.
3. **Complete.** When the work lands (PR merged), set `status=completed`, `completed_at`, `updated_at`. Commit, push.

The reference implementation is the `agentic-task` CLI in this repo (`agentic-task claim|list|complete <repo-path>`). Other runtimes are expected to call it via their shell-tool equivalent rather than reimplement the protocol.

## Cleanup

Tasks with `status=completed` and `completed_at` older than **30 days** are moved to `tasks/archive/YYYY-MM/` (matching their completion month). The repo doesn't archive automatically yet — for now this is a manual `git mv` when the directory grows.

## Examples

A pending task, freshly created by a human:

```json
{
  "id": "0001",
  "subject": "extract bm25 fixtures from omni-rag",
  "status": "pending",
  "created_at": "2026-04-27T13:00:00Z",
  "updated_at": "2026-04-27T13:00:00Z"
}
```

Same task after a Claude agent claims it:

```json
{
  "id": "0001",
  "subject": "extract bm25 fixtures from omni-rag",
  "status": "claimed",
  "claimed_by": "te-claude",
  "runtime": "claude",
  "claimed_at": "2026-04-27T13:01:00Z",
  "created_at": "2026-04-27T13:00:00Z",
  "updated_at": "2026-04-27T13:01:00Z"
}
```

After the PR merges and the agent runs `agentic-task complete`:

```json
{
  "id": "0001",
  "subject": "extract bm25 fixtures from omni-rag",
  "status": "completed",
  "claimed_by": "te-claude",
  "runtime": "claude",
  "claimed_at": "2026-04-27T13:01:00Z",
  "completed_at": "2026-04-27T15:42:00Z",
  "branch": "agent/te/claude/omnirag-bm25",
  "pr": "https://github.com/TobiasEdman/multi-agentic/pull/12",
  "created_at": "2026-04-27T13:00:00Z",
  "updated_at": "2026-04-27T15:42:00Z"
}
```

## What this is *not*

- **Not a queue** with priorities, dependencies, or ordering beyond lowest-id-first. `blocked_by`/`blocks` arrays exist in the schema but the CLI doesn't read them yet.
- **Not authoritative for in-flight work.** Once a task is `claimed`, the actual work happens on a branch (per branch-naming convention in `docs/conventions-multi-agent.md` §3) and the PR is the source of truth.
- **Not a replacement for an issue tracker.** Tasks here are short-lived coordination tickets between agents. Long-running roadmap items belong on whatever issue tracker the team uses.
