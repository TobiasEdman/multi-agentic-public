# AGENTS.md — multi-agentic

> **Read this first.** This is the primary agent-facing document for the repo.
> `CLAUDE.md` is a Claude Code addendum that points back here for the bulk of the rules.

## Repo identity

- **Name:** `multi-agentic`
- **Purpose:** Vendor-neutral toolkit for multi-agent collaborative coding — implementation home for the Tier 2 plan.
- **Source spec:** [`docs/specs/tier2_multi_agent.md`](docs/specs/tier2_multi_agent.md) (v2, multi-vendor). Translated from `agentic_workflow/docs/plans/tier2_multi_agent.md` commit `2563a7ec`; that path is now a redirect stub.
- **Status:** alpha, private. No public release. No external consumers.

## Build & test

```bash
uv sync && uv run pytest
```

Falls back to plain pip if you don't have `uv`:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Smoke gate: `PYTHONPATH=src python -c "import agentic_task"` must succeed (catches import-time failures before they reach CI).

### Worktree bootstrap

When you start in a fresh `.claude/worktrees/<slug>/` (created by `claude -w "<slug>"`), the `WorktreeCreate` hook intentionally does **not** install dependencies — `uv` is not on the system `$PATH` of the non-interactive shell the hook runs in. Run the build & test commands above yourself as the first action in a new worktree session, then proceed with the task. The hook does set up `.env.local` with a deterministic `DEV_PORT` and copies any `.env*` files from the parent.

## Paths

| Path | Role |
|---|---|
| `src/agentic_task/` | CLI package (`agentic-task` entrypoint, when wired). Stub today. |
| `templates/` | Vendor-neutral templates the CLI materialises into target repos (AGENTS.md, `.agents/`, `.github/workflows/agent-review.yml`, `.claude/agents/*-reviewer.md`). |
| `hooks/` | Optional `~/.claude/hooks/` extensions (worktree-create, worktree-remove, co-authored-by-dual). |
| `docs/` | `installation.md`, `conventions-base.md` (universal spec) + `conventions-multi-agent.md` (cross-runtime extension; this repo uses both), `tracks.md` (per-vendor status). |
| `tests/` | pytest tests. Smoke today; real tests as pieces land. |

## Conventions

- **Per-task commits.** Each scaffolding step, each feature, each fix is its own commit. No "init everything" or "WIP" commits.
- **Verify-artefakt before declaring done.** Per global rule §6: every non-trivial change ships with a passing test, a confirming command output, or an explicit "I cannot verify in this environment" note.
- **Co-Authored-By trailer on every agent-authored commit** (global rule §7). The trailer identifies the agent vendor; the human stays as `author`. See `hooks/co-authored-by-dual.sh` for the multi-vendor extension.
- **Dogfooding.** This repo's own `AGENTS.md` (this file) is the canonical example of what the toolkit produces. If the template in `templates/AGENTS.md.tmpl` drifts from this file, fix the template.

## Convention spec

Two layers: [`docs/conventions-base.md`](docs/conventions-base.md) is the universal agent-collab spec (per-task commits, verify-artefakt, worktree lifecycle, writer/reviewer, CI-bot). [`docs/conventions-multi-agent.md`](docs/conventions-multi-agent.md) extends it for repos coordinating across runtimes (file locks, branch-per-runtime, multi-vendor trailers). This repo uses both.

Quick pointers:

- **Task lock protocol** — `.agents/tasks/*.json`, one file per task, git push as atomic lock (plan §A). Reference impl: the `agentic-task` CLI in this repo.
- **Branch-per-agent** — `agent/<initials>/<runtime>/<area>-<slug>` so `git branch --list 'agent/te/codex/*'` filters per runtime.
- **Writer/reviewer pattern** — three vendor-neutral reviewer prompts in [`.agents/prompts/`](.agents/prompts/) (pragmatic / security / docs lenses).
- **Multi-vendor attribution** — [`hooks/co-authored-by-dual.sh`](hooks/co-authored-by-dual.sh) accepts `Co-Authored-By: <Claude|Codex|Mistral>`, `Assisted-by:`, or `Codex-Generated:`.
- **Worktree lifecycle** — Claude-track hooks live in `~/.claude/hooks/` and [`hooks/worktree-{create,remove}.sh`](hooks/) (stubs today, Track 1 #3).
- **Agent-as-CI-bot** — risk-tier × lens × model matrix in `.github/workflows/agent-review.yml` (Track 1 #6, separate session).

## Tracks

The plan splits work into three vendor tracks. Status is tracked in [`docs/tracks.md`](docs/tracks.md).

## Session conduct

These rules apply to any agent runtime opening a session in this repo (Claude / Codex / Mistral / other). They are stated here vendor-neutrally so the toolkit does not require a specific runtime's continuity layer to be installed. Per-runtime addenda (`CLAUDE.md`, future `CODEX.md`, `MISTRAL.md`) may add hook-level enforcement; the rules themselves are policy regardless.

1. **Diagnosis vs. directive.** If the user's turn is a diagnosis, observation, or question, ask before acting. Only act on turns containing an explicit imperative verb (`fix`, `change`, `edit`, `replace`, `restart`, `run`, `write`, `add`, `remove`). When in doubt, restate your reading of the turn and ask.

2. **Echo-back discipline.** When the user states a session-wide rule or tool preference, repeat it verbatim and flag it as registered. Carry it as a precondition across subsequent turns, not a one-shot instruction.

3. **Running code is read-only.** Code that is currently executing — on a remote cluster, inside a running server, inside an active training job, inside a live fetch — is read-only. Do not edit, refactor, or propose structural changes to it until the user uses an explicit imperative verb. If the user asks a question about running code, answer the question; do not preemptively edit.

4. **Mid-session re-anchor.** In long sessions, restate the top-level goal before starting a new sub-topic. If the conversation has shifted topic without explicit user direction, ask whether to return to the original.

5. **Front-load the first turn.** For non-trivial work (more than ~3 tool calls or more than 2 files), if the user's opening turn doesn't include paths + env + prior attempts + non-goals, ask for them before diving in.

6. **Verify work before declaring done.** See *Conventions* above (verify-artefakt rule). Every commit ends with a `Verified-by: <how>` trailer recording the verification method (`pytest tests/ — 78 passed`, `smoke — import succeeded`, `trivial — typo fix`, or `cannot-verify — user to verify out-of-band`).

7. **Attribute agent-authored commits.** See *Conventions* above (Co-Authored-By trailer rule).

Per-runtime enforcement (where available):
- Claude Code sessions: rules §3, §6, and §7 are enforced by hooks at `~/.claude/hooks/active-jobs-guard.sh`, `~/.claude/hooks/verify-artefakt.sh`, and `~/.claude/hooks/co-authored-by.sh` respectively. See [`CLAUDE.md`](CLAUDE.md) for details.
- Codex / Mistral: hook-level enforcement is per-runtime; see the corresponding addendum file when those tracks activate. The rules above are policy regardless of enforcement mechanism.

<!-- agentic-task:coordination:start -->
## Cross-runtime coordination

This section is managed by `agentic-task`. Repository-specific instructions
outside this block remain authoritative.

- Every writing agent session uses an exclusively owned worktree.
- Use runtime-labelled branches: `agent/<initials>/<runtime>/<area>-<slug>`.
- Claim a task before editing and complete it afterward. Claims arbitrate whole
  tasks; coordinate intended file scope explicitly because the schema does not
  enforce path ownership.
- Run coordination commands through the absolute, non-editable operator wheel
  runtime bound by `.agents/toolchain-lock.json`. Never execute a verifier or
  coordination command from the repository or caller `PATH`.
- Transfer durable execution state through immutable, task-scoped files under
  `.agents/handoffs/<task-id>/`; never use one mutable `LATEST.md`.
- Never share a branch and working tree between concurrent writing sessions.
- A dirty working tree belongs to its current session; other agents must not
  edit it.
- Questions and diagnosis do not authorize mutation. Verify non-trivial work
  before declaring it complete.
- Personal checkpoints, snapshots, live inbox messages, active-session state,
  and running-code locks use the shared local `~/.agents/continuity/` store
  through runtime adapters, not vendor stores.
<!-- agentic-task:coordination:end -->
