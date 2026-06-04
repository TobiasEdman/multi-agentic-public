# Conventions (base) — universal agent collaboration spec

Universal practices for any repo where a code agent (Claude, Codex, Mistral, Copilot, …) makes commits. Vendor-neutral; works for single-agent repos and as the foundation for multi-agent setups.

If your repo coordinates multiple agent runtimes against the same codebase, also adopt [`conventions-multi-agent.md`](conventions-multi-agent.md) — it extends this file with the cross-runtime layer (file locks, branch-per-runtime, multi-vendor trailers, cross-runtime MCP).

Source plan (rationale, sequencing, open questions): [the lessons repo (`docs/specs/tier2_multi_agent.md` here is the canonical, English-translated version) (v2; commit `ed8d780`).

## Contents

1. [Runtime neutrality](#runtime-neutrality)
2. [Per-task commits](#per-task-commits)
3. [Verify-artefakt rule](#verify-artefakt-rule)
4. [Attribution — single trailer](#attribution)
5. [Branch-per-agent](#branch-per-agent)
6. [Worktree lifecycle](#worktree-lifecycle)
7. [Writer/reviewer pattern](#writer-reviewer)
8. [Agent-as-CI-bot — risk-tier × lens](#agent-as-ci-bot)
9. [Shared context](#shared-context)
10. [Non-goals](#non-goals)

---

## <a id="runtime-neutrality"></a>1. Runtime neutrality

Conventions in this file do not assume a specific agent runtime. File paths, schemas, branch names, and trailer formats avoid embedding Claude-specific (or any single vendor's) assumptions. Vendor-specific implementations live in clearly-named addenda (`CLAUDE.md`, `CODEX.md`, `MISTRAL.md`) or under per-runtime directories.

If your repo only ever uses one runtime, this is just good hygiene. If it later adopts a second, no convention has to be unlearned.

## <a id="per-task-commits"></a>2. Per-task commits

Each scaffolding step, each feature, each fix is **its own commit**. No `WIP`, no `init everything`, no bundled refactors-plus-features.

Why: a fresh-context reviewer (human or agent) can review one commit at a time. Bundled commits force the reviewer to hold the entire change in working memory.

Practical limits:

- Commit message: a single conventional-commit subject (`feat(cli): ...`, `fix(hooks): ...`, `test: ...`, `docs: ...`, `chore: ...`) plus a body that explains *why* and lists the verify command.
- One subsystem per commit. If a feature touches the CLI **and** the docs, that's two commits.
- Tests for a feature land in the same commit as the feature (so the commit is verifiable on its own — see §3).

## <a id="verify-artefakt-rule"></a>3. Verify-artefakt rule

Per `~/.claude/CLAUDE.md` §6: **every non-trivial commit ships with a verify artefact**. One of:

- A passing test (named in the commit message).
- A shell command whose output confirms correctness.
- An expected-output diff or screenshot comparison.
- An explicit "I cannot verify in this environment, please verify before closing" note.

Trivial changes (typo fix, log line added, single-file rename) are exempt but should still describe how a human would verify if they wanted.

## <a id="attribution"></a>4. Attribution — single trailer

Every agent-authored commit ends with an attribution trailer. The human stays as `author` (so `git blame` and `git log --author=` resolve to the human who asked for the change). The agent identity goes in the trailer.

Single-runtime form (Claude shown; substitute your runtime's vendor):

```
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Validation: `~/.claude/hooks/co-authored-by.sh` enforces presence of the trailer on every `git commit` (returns `permissionDecision: "ask"` when missing).

If your repo coordinates more than one runtime, see `conventions-multi-agent.md` §Attribution for the full vendor-trailer table and the validation hook that accepts any of them.

## <a id="branch-per-agent"></a>5. Branch-per-agent

Branch-naming convention (single-runtime form):

```
agent/<initials>/<repo-area>-<short-slug>
```

Examples:

- `agent/te/bm25-bench`
- `agent/te/auth-rewrite`

Initials belong to the **human**, not the agent (per [Attribution](#attribution)). Reserved prefix for **fully autonomous PRs** (cloud sessions, scheduled tasks): `claude/<slug>` (or your runtime's equivalent — `copilot/<slug>`, `codex/<slug>`). They distinguish "I drove" from "the model ran unattended."

If your repo coordinates more than one runtime, see `conventions-multi-agent.md` §Branch-per-agent for the runtime-aware extended form (`agent/<initials>/<runtime>/<area>-<slug>`).

## <a id="worktree-lifecycle"></a>6. Worktree lifecycle

Same lifecycle for every runtime; per-runtime hooks implement it:

1. **Create** — runtime opens a fresh checkout in an isolated path.
2. **In-flight signal** — open a *draft* PR before the first push.
3. **Ready signal** — mark the PR ready; reviewer = human.
4. **Merge** — squash; commit message gets the runtime's attribution trailer.
5. **Cleanup** — runtime removes the worktree.
6. **Stale** — branch with no commits 7 days + no PR → human deletes or hands off.

Worktree path (Claude default, others may differ): `.claude/worktrees/<slug>`.

Implementation: `~/.claude/hooks/worktree-{create,remove}.sh` — global-canonical hooks per `multi-agentic/CLAUDE.md` § Files that must match other files. Per-repo behaviour overrides via `~/.claude/worktree-config/<repo>.env`.

## <a id="writer-reviewer"></a>7. Writer/reviewer pattern

Two roles, never the same context:

- **Writer** — implements the change. Holds the design context built up across the planning conversation.
- **Reviewer** — opens with no design context. Reads the diff fresh. Catches what the writer was too close to see.

Reviewer prompts live in `.agents/prompts/` — three lenses, vendor-neutral:

- `pragmatic-reviewer.md` — code quality, design judgment.
- `security-reviewer.md` — concrete security risk introduced by the diff (≥ 80% confidence threshold).
- `docs-reviewer.md` — README / CHANGELOG / docstring drift caused by the diff.

Comment format (single-runtime): `[<lens>] <verdict>`. If your repo coordinates multiple runtimes, see `conventions-multi-agent.md` §Writer/reviewer for the `[<runtime>/<lens>]` extended form.

## <a id="agent-as-ci-bot"></a>8. Agent-as-CI-bot — risk-tier × lens

PR review runs as a GitHub Action with a matrix over **lens** (and, for multi-runtime repos, model — see extension), gated by a **risk-tier classifier** (Cloudflare-style 3-line bash heuristic on LOC + file count + security-glob match):

- **trivial** (≤ 10 LOC, ≤ 5 files) → docs lens only.
- **lite** (≤ 100 LOC, ≤ 20 files) → quality + docs lenses.
- **full** (anything bigger, or anything touching `auth/`, `crypto/`, `secrets/`, `security/`) → all three lenses.

Workflow file: `.github/workflows/agent-review.yml`. Risk-tier classifier: `.github/scripts/classify-pr.sh`. Reviewer prompts loaded from `.agents/prompts/` (vendor-neutral path) — the workflow's prompt-loading is an implicit dependency on that directory existing.

The model dimension is additive and only meaningful in multi-runtime repos; see `conventions-multi-agent.md` §Agent-as-CI-bot for the full lens × model matrix.

## <a id="shared-context"></a>9. Shared context

Agents need the same supporting context (knowledge graph, RAG corpus, repo state, conventions). Two channels:

- **Filesystem** — `.agents/`, `AGENTS.md`, `docs/conventions-*.md`, `git log`. Every runtime can read these.
- **MCP (Model Context Protocol)** — open standard for tool/context servers. Most modern code-agent runtimes (Claude Code, Codex CLI, OpenCode, …) support it. A repo's preferred MCP server (e.g. omni-rag for project-doc search) is configured per-runtime; the *protocol* is shared.

If your repo has multiple runtimes consuming the same MCP server, see `conventions-multi-agent.md` §Shared context for what does **not** travel cross-vendor (runtime-specific tool names, harness-specific paths).

## <a id="non-goals"></a>10. Non-goals

- **No DOCX/PDF in `.agents/`.** Tasks are JSON; specs are Markdown. Binary formats break diffing and hide drift.
- **No secrets in commits.** Trailers are public. API keys, model IDs that include account context, customer identifiers — none of these go in attribution.

(Multi-runtime-only non-goals — vendor-specific tool names in shared prompts, auto-resolving merge conflicts on `.agents/tasks/*.json` — live in `conventions-multi-agent.md` §Non-goals.)
