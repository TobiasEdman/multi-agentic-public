# Tier 2 Multi-Agent Implementation Plan

> **Translated from Swedish/English mash-up.** Original (planning-voice) lives at `agentic_workflow/docs/plans/tier2_multi_agent.md` commit `2563a7ec`; that file is now a redirect stub. This file is the canonical, install-target-grade spec.

**Status:** Plan-doc, **revision: v2** (2026-04-27, same day as v1). No implementations yet.

**v2 trigger:** v1 assumed Claude-only multi-agent. The whiteboard architecture showed that the vision is **multi-model multi-agent** — Mistral + Codex + Claude as three parallel agent tracks with shared context. v2 reformulates the foundational decisions so the Claude implementation becomes track 1 of three, not the whole picture.

**Sub-deliverables:** (A) vendor-neutral file-lock + task-claim, (B) branch-per-agent + worktree convention, (C) per-repo agent-CI with matrix over lens × model. Plus cross-cutting: **AGENTS.md as primary** (CLAUDE.md / CODEX.md / MISTRAL.md as addenda), **MCP-based shared context**, **vendor-track separation**, **trailer dual-mode**.

**Bottom line:** spec, conventions, and repo-state are **vendor-neutral from day one**. The Claude track is built first (it is what we have today); Codex and Mistral tracks are *additive* once their runtime support is in place. Estimated effort for the Claude track: 5–10 days over 6 sessions. Codex/Mistral tracks: separate sessions once API access and runtime selection are decided.

---

## Contents

1. [Architecture premise (vendor diversity)](#premise)
2. [Decisions made in this session (v2)](#decisions)
3. [Sub-deliverable A — Vendor-neutral file-lock + task-claim](#a-filelock)
4. [Sub-deliverable B — Branch-per-agent + worktree convention](#b-branch)
5. [Sub-deliverable C — Per-repo agent-CI (matrix lens × model)](#c-ci)
6. [Cross-cutting D — Shared Context governance (MCP)](#d-context)
7. [Cross-cutting E — Vendor-track separation](#e-vendor)
8. [Cross-cutting F — AGENTS.md primary + per-vendor addenda](#f-agents)
9. [Cross-cutting G — Trailer dual-mode + per-vendor attribution](#g-trailer)
10. [Cross-cutting H — Orchestrator candidates (deferred)](#h-orchestrator)
11. [End-to-end smoke test](#smoke)
12. [Sequencing across sessions](#sequencing)
13. [Open questions](#open)
14. [Sources](#sources)

---

## <a id="premise"></a>Architecture premise

```
        Shared Context (Repo + Docs + KG/RAG via MCP)
                       │
        ┌──────────────┼──────────────┐
     Human A         Human B        Human C
        │              │              │
   Mistral-agent  Codex-agent    Claude-agent
        │              │              │
        └──────┬───────┴──────┬───────┘
            Orchestr.      CI/CD/Test
               │              │
               └──────┬───────┘
                 Codebase (Git)
```

**Three invariants:**

1. **The spec is vendor-neutral.** Repo conventions (`.agents/tasks/`, branch naming, AGENTS.md, commit trailers) must not be Claude-specific. Models are interchangeable; conventions persist.
2. **The runtime is vendor-specific.** Claude → Claude Code. Codex → OpenAI Codex CLI. Mistral → candidate: OpenCode (sst/opencode) or LiteLLM proxy. Different hooks, different CLI, different permission models.
3. **Coordination via git, not via the runtime.** Per `multi_user_multi_agent.md` C1: 4-of-4 lens convergence on *git as coordination substrate*. This means that even when Claude and Codex cannot speak directly to each other, both can read `.agents/tasks/*.json` and `git log`.

---

## <a id="decisions"></a>Decisions made in this session (v2)

The table below replaces v1 decisions entirely. ⚠ marks decisions that **break with v1**.

| # | Fork | Decision | Rationale |
|---|---|---|---|
| 1 | **Vendor diversity** | **Design the spec for 3 LLM tracks from day one.** Implement the Claude track first. | Whiteboard architecture. Lock-in protection. Cloudflare already does this (Sonnet/Opus/GPT-5.4 routing). |
| 2 | Lock-dir scope | **Per-repo `.agents/tasks/` (committed JSON), git-lock via push collision** (Anthropic C-compiler pattern). Leave the global `~/.claude/active-jobs/` untouched. | 4-of-4 lens convergence on git substrate. Vendor-neutral — all three LLMs read the same JSON. |
| 3 ⚠ | Task-claim runtime | **Breaks with v1.** Do **not** use Claude Code's Agent Teams (`~/.claude/tasks/`) — Claude-only, single-host, not cross-vendor. **Use** repo-committed JSON with atomic git push as the lock mechanism. | Agent Teams orchestrates only Claude teammates. Mistral/Codex would not see the task list. |
| 4 | CI architecture | **Per-repo GH Action with matrix over (lens × model)**. Claude-only in MVP; Codex/Mistral in v2 once a runtime image exists. | Matrix job with `fail-fast: false` + dynamic strategy. Upgrades are additive. |
| 5 | Risk-tier classifier | **3-line bash heuristic** (Cloudflare style) — vendor-neutral. | LOC + file count + security glob. Which lens runs is affected; which model drives the lens is orthogonal. |
| 6 ⚠ | OpenCode | **Breaks with v1.** v1 said "skip for Tier 2." v2: **evaluate OpenCode in sub-deliverable D** as a potential vendor-neutral runtime — Cloudflare-validated, MIT, provider-agnostic. | Cloudflare runs Mistral + Claude + GPT through OpenCode for exactly this reason. For 3 models, OpenCode is cheaper than 3 separate harnesses. |
| 7 ⚠ | LLM Gateway | **Breaks with v1.** v1 said "skip for 2–3 people." v2: **plan a Gateway evaluation** (Cloudflare AI Gateway / Portkey / LiteLLM / openrouter.ai) as a requirement, not an option. | Vendor diversity *is* the reason to have a proxy: one gateway → centralised token budget, observability, model routing, FX for API keys across 3 providers. |
| 8 | AGENTS.md | **Promote to primary.** CLAUDE.md / CODEX.md / MISTRAL.md become short vendor addenda. | Linux Foundation spec, read natively by Codex CLI + Vercel + Cloudflare + Cursor + 60k+ repos. Claude Code is the holdout but always reads CLAUDE.md. |
| 9 | Shared Context | **MCP as cross-vendor protocol** for KG/RAG access. Omni-rag is exposed via an MCP server (already exists); Codex CLI + OpenCode consume the same server. | MCP is an open standard; all three runtimes support it. The alternative (per-vendor RAG clients) is vendor lock-in at the data layer too. |
| 10 | Trailer policy | **Dual-mode hook + per-vendor pattern.** Claude: `Co-Authored-By:` (default) or `Assisted-by:` (#36105). Codex: `Codex-Generated:` (or whatever OpenAI standardises). Mistral: TBD. | Hook should validate different trailers per `CLAUDE_CODE_TRAILER_MODE`-style env var, per runtime. |

---

## <a id="a-filelock"></a>Sub-deliverable A — Vendor-neutral file-lock + task-claim

### A.1 MVP cut

**Repo-committed `.agents/tasks/*.json`** with git push as the atomic lock mechanism. Vendor-neutral: all three runtimes read and write the same files.

**Lock protocol** (Anthropic C-compiler pattern, scaled to multi-vendor):

1. An agent (any of them) picks a **pending** task. Writes `claimed_by` + `claimed_at` + `runtime` (`claude|codex|mistral`) → commits → `git push`.
2. Push succeeds → the agent holds the lock. Push fails (non-fast-forward) → the agent runs `git pull --rebase`, sees that the task status changed, picks a different one.
3. When the task is done: the agent writes `status: completed` + `completed_at` → commit + push.
4. Cleanup policy: completed tasks > 30 days are archived to `.agents/tasks/archive/YYYY-MM/`.

### A.2 Files

```
<repo>/
└── .agents/
    ├── README.md                          # convention (vendor-neutral)
    ├── schema.json                        # JSON Schema for task format
    └── tasks/
        ├── 0001.json                      # one task = one file (zero-padded id)
        └── 0002.json
```

**`.agents/schema.json`** (sketch, vendor-neutral):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "agentic-task",
  "type": "object",
  "required": ["id", "subject", "status", "created_at"],
  "properties": {
    "id":           {"type": "string", "pattern": "^[0-9]{4}$"},
    "subject":      {"type": "string", "maxLength": 120},
    "description":  {"type": "string"},
    "status":       {"enum": ["pending", "claimed", "in_progress", "completed", "blocked", "abandoned"]},
    "claimed_by":   {"type": ["string", "null"], "description": "agent identity, e.g. 'te-claude' or 'te-codex'"},
    "runtime":      {"enum": ["claude", "codex", "mistral", null]},
    "claimed_at":   {"type": ["string", "null"], "format": "date-time"},
    "completed_at": {"type": ["string", "null"], "format": "date-time"},
    "blocked_by":   {"type": "array", "items": {"type": "string"}},
    "blocks":       {"type": "array", "items": {"type": "string"}},
    "branch":       {"type": ["string", "null"], "description": "branch where work happened"},
    "pr":           {"type": ["string", "null"], "description": "PR URL when ready"},
    "created_at":   {"type": "string", "format": "date-time"},
    "updated_at":   {"type": "string", "format": "date-time"}
  }
}
```

**`.agents/README.md`** (~30 lines):
- Schema reference
- Lock protocol (3 points above)
- Cleanup policy
- Examples: `pending` task, `claimed` task, `completed` task
- Vendor-neutral: no coupling to `~/.claude/tasks/`, no Claude Code-specific convention

### A.3 Verification artifact

```bash
# Setup
TEST=/tmp/agents-task-claim-$(date +%s)
mkdir -p "$TEST/.agents/tasks" && cd "$TEST"
git init -q && git config user.email t@t.t && git config user.name t

# Create pending task
cat > .agents/tasks/0001.json <<EOF
{"id":"0001","subject":"test","status":"pending","created_at":"2026-04-27T13:00:00Z","updated_at":"2026-04-27T13:00:00Z"}
EOF
git add . && git commit -q -m "task 0001: pending"

# Claim (simulate Claude agent)
jq '.status="claimed" | .claimed_by="te-claude" | .runtime="claude" | .claimed_at="2026-04-27T13:01:00Z" | .updated_at="2026-04-27T13:01:00Z"' \
  .agents/tasks/0001.json > /tmp/_t && mv /tmp/_t .agents/tasks/0001.json
git commit -am "task 0001: claimed by te-claude"

# Complete
jq '.status="completed" | .completed_at="2026-04-27T13:02:00Z" | .updated_at="2026-04-27T13:02:00Z"' \
  .agents/tasks/0001.json > /tmp/_t && mv /tmp/_t .agents/tasks/0001.json
git commit -am "task 0001: completed"

# Verify
jq -r '[.id,.status,.claimed_by,.runtime] | @tsv' .agents/tasks/0001.json
# Should show: 0001    completed    te-claude    claude

git log --oneline
# Should show 3 commits
```

Pass criterion: 3 commits, JSON schema validation passes (`jsonschema -i .agents/tasks/0001.json .agents/schema.json`), status progression goes pending → claimed → completed.

### A.4 Open questions

1. **Push race in practice.** If two agents on the same machine claim simultaneously: both local commits can be made, but `push` resolves it. Cross-machine: same. But high-frequency claiming (3+ agents, 1+/min) → many failed pushes. **Mitigation:** low claiming frequency (3–5 times/hour/agent maximum) or future exponential backoff in the runtime wrapper.
2. **Manual edit vs. agent edit.** What happens when a human edits `.agents/tasks/0042.json` directly? **Decision:** the human is allowed to edit. We do not log who edited — `git blame` is sufficient.
3. **Vendor runtime wrapper.** Each runtime (Claude, Codex, Mistral) needs an *opt-in* wrapper that teaches it to claim-via-git. No runtime does this natively. **Plan:** a small Python CLI `agentic-task` that all three runtimes can invoke via the `Bash` tool. (New mini-deliverable, ~1 session.)

### A.5 Sequencing (track 1 — Claude track)

1. Create `.agents/{README.md,schema.json,tasks/}` in agentic_workflow
2. Write the `agentic-task` Python CLI (claim/list/complete) — vendor-neutral
3. Verify via the smoke test above
4. Patch the rise-repo-bootstrap template

---

## <a id="b-branch"></a>Sub-deliverable B — Branch-per-agent + worktree convention

### B.1 MVP cut

**Branch convention** (vendor-neutral):

```
agent/<initials>/<runtime>/<repo-area>-<short-slug>
```

Examples:
- `agent/te/claude/omnirag-bm25-bench`
- `agent/te/codex/agentic-cli-rewrite`
- `agent/te/mistral/des-contracts-extract`

`<runtime>` is mandatory — so `git branch --list 'agent/te/codex/*'` filters per model. Initials belong to the human (per CLAUDE.md §7 attribution rule).

Reserve `claude/<slug>`, `copilot/<slug>`, `codex/<slug>` for **fully autonomous PRs** (cloud sessions, scheduled tasks). This separates "I drove" from "the model ran unattended."

**Worktree path:** `.claude/worktrees/<slug>` for the Claude runtime. For other runtimes: TBD per runtime (open question — see §B.4). Slug = the last segment of the branch name.

**Lifecycle** (unchanged from v1, vendor-neutral):
1. Create — Claude: `claude -w "<slug>"`. Codex: TBD. Mistral: TBD.
2. In-flight signal: open PR as *draft* before the first push.
3. Ready signal: mark PR ready; reviewer = human.
4. Merge: squash; runtime trailer (Co-Authored-By / Assisted-by / Codex-Generated / Mistral-TBD).
5. Cleanup: per runtime.
6. Stale: a branch with no commits for 7d + no PR → human deletes/hands off.

### B.2 Files (Claude track)

```
~/.claude/
├── hooks/
│   ├── worktree-create.sh                 # NEW (Claude-only, Claude Code hook)
│   └── worktree-remove.sh                 # NEW (Claude-only)
├── worktree-config/
│   ├── default.env
│   ├── agentic_workflow.env
│   └── omni-rag.env
└── settings.json                          # WorktreeCreate/Remove block
```

Claude-track hooks are adapted from `tfriedel/claude-worktree-hooks` (MIT) — see [v1 details](https://github.com/anthropics/claude-code/issues) for the exact shell code (unchanged from v1 §B.2). Macports fixes (`md5 -q` / `awk -F=` / `uv sync`) remain.

### B.3 Files (Codex track + Mistral track)

**Open** — depends on the chosen runtime. Two candidates for Codex:
- **Codex CLI native** (`openai/codex`) — does it have hooks? *Open question, Wave 4 research.*
- **Wrapper** around `git worktree add` that the Codex CLI can invoke via the Bash tool. Most portable.

For Mistral: no first-party agent CLI yet (per Wave 3). Likely path: run the Mistral model inside OpenCode (sst/opencode), which has its own worktree events. If OpenCode is adopted (see §D), use its hook system.

### B.4 Verification artifact (Claude track)

```bash
# Inside agentic_workflow:
claude -w "tier2-test"

# Inside the worktree session:
pwd                                         # .claude/worktrees/tier2-test
git branch --show-current                   # worktree-tier2-test (or agent/te/claude/... if branch_prefix configured)
cat .env.local                              # DEV_PORT=<6000-6899>
git worktree list                           # 2 worktrees
exit

git worktree remove .claude/worktrees/tier2-test
```

Codex track + Mistral track: smoke test will be specced once the runtime selection is settled.

### B.5 Open questions

1. **Subagent naming** (#27749 closed) — accept v1 for the Claude track. Codex/Mistral unknown.
2. **Cross-runtime worktree** — can a Codex agent open a Claude worktree? Probably not (they don't care about the `.claude/worktrees/` path). **Convention:** runtime-specific worktree paths under a shared `.worktrees/<runtime>/<slug>/`.
3. **Branch protection vs. bot cleanup** — unknown per repo, verify per repo before rollout.
4. **Hooks are runtime-specific** — Claude Code's `WorktreeCreate`/`WorktreeRemove` do not exist in Codex/Mistral. The lifecycle convention is spec; hooks are implementation per runtime.

### B.6 Sequencing

1. Claude track: hooks + per-repo config (unchanged from v1)
2. Smoke test in agentic_workflow
3. Branch-naming convention documented in AGENTS.md
4. Codex/Mistral track: separate sessions when the runtime selection is settled

---

## <a id="c-ci"></a>Sub-deliverable C — Per-repo agent-CI (matrix lens × model)

### C.1 MVP cut

GH Action with matrix over **two dimensions**:
- **Lens:** quality, security, docs (vendor-neutral — all three models can do all three lenses)
- **Model:** claude (MVP), codex (v2), mistral (v3)

MVP runs only Claude. The action is written so that adding `codex` / `mistral` is a matter of adding rows to the matrix configuration.

The **risk-tier classifier** runs first (vendor-neutral bash). It sets both `tier` and `lenses` outputs. v2 adds a `models` output that can extend per tier (e.g. `full` tier runs all 3 models on the `quality` lens, `lite` runs only Claude).

### C.2 Files

```
<repo>/
├── .github/workflows/agent-review.yml
└── .claude/agents/
    ├── pragmatic-reviewer.md              # vendor-neutral persona
    ├── security-reviewer.md
    └── docs-reviewer.md
```

The reviewer prompts are **AGENTS.md-style** — vendor-neutral. They do not point at Claude-specific MCP tools but describe the capabilities the reviewer needs (`read diff`, `post inline comment`, `search repo`). Per-runtime adapters in `.github/workflows/agent-review.yml` map capabilities → actual tools per model.

**`.github/workflows/agent-review.yml`** (v2 — matrix over model + lens):

```yaml
# .github/workflows/agent-review.yml (v2 — multi-model)
name: Agent PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  issue_comment:
    types: [created]

concurrency:
  group: ${{ github.workflow }}-pr-${{ github.event.pull_request.number || github.event.issue.number }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write
  issues: read
  id-token: write

env:
  REVIEW_EVENT: COMMENT  # change to REQUEST_CHANGES to block merge

jobs:
  classify:
    if: |
      github.event_name == 'pull_request' ||
      (github.event_name == 'issue_comment' &&
       github.event.issue.pull_request &&
       contains(github.event.comment.body, '@review'))
    runs-on: ubuntu-latest
    outputs:
      tier:    ${{ steps.classify.outputs.tier }}
      lenses:  ${{ steps.classify.outputs.lenses }}
      models:  ${{ steps.classify.outputs.models }}
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Risk-tier classifier (vendor-neutral)
        id: classify
        run: |
          BASE="${{ github.event.pull_request.base.sha || 'HEAD~1' }}"
          HEAD="${{ github.event.pull_request.head.sha || 'HEAD' }}"
          LOC=$(git diff --shortstat "$BASE..$HEAD" | awk '{s+=$4+$6} END {print s+0}')
          FILES=$(git diff --name-only "$BASE..$HEAD" | wc -l | tr -d ' ')
          PATHS=$(git diff --name-only "$BASE..$HEAD")
          if echo "$PATHS" | grep -qE '(auth|crypto|secrets|security)/'; then
            TIER="full"; LENSES='["quality","security","docs"]'; MODELS='["claude"]'
          elif [ "$LOC" -le 10 ] && [ "$FILES" -le 5 ]; then
            TIER="trivial"; LENSES='["docs"]'; MODELS='["claude"]'
          elif [ "$LOC" -le 100 ] && [ "$FILES" -le 20 ]; then
            TIER="lite"; LENSES='["quality","docs"]'; MODELS='["claude"]'
          else
            TIER="full"; LENSES='["quality","security","docs"]'; MODELS='["claude"]'
          fi
          # MVP: claude only. v2: extend the MODELS array per tier.
          echo "tier=$TIER" >> "$GITHUB_OUTPUT"
          echo "lenses=$LENSES" >> "$GITHUB_OUTPUT"
          echo "models=$MODELS" >> "$GITHUB_OUTPUT"
          echo "::notice::tier=$TIER LOC=$LOC files=$FILES models=$MODELS"

  review:
    needs: classify
    runs-on: ubuntu-latest
    permissions: { contents: read, pull-requests: write }
    strategy:
      fail-fast: false
      matrix:
        lens:  ${{ fromJSON(needs.classify.outputs.lenses) }}
        model: ${{ fromJSON(needs.classify.outputs.models) }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha || github.sha }}
          fetch-depth: 0

      - name: Mask API keys
        run: |
          for k in ANTHROPIC_API_KEY OPENAI_API_KEY MISTRAL_API_KEY; do
            v="${!k:-}"
            [ -n "$v" ] && echo "::add-mask::$v"
          done
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          MISTRAL_API_KEY: ${{ secrets.MISTRAL_API_KEY }}

      # MVP: claude track. v2 adds matching steps per model.
      - name: Run review (model=${{ matrix.model }}, lens=${{ matrix.lens }})
        if: matrix.model == 'claude'
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          track_progress: true
          timeout_minutes: 30
          prompt: |
            REPO: ${{ github.repository }}
            PR NUMBER: ${{ github.event.pull_request.number }}
            LENS: ${{ matrix.lens }}
            RISK TIER: ${{ needs.classify.outputs.tier }}
            MODEL: claude

            Read .claude/agents/${{ matrix.lens == 'quality' && 'pragmatic-reviewer' || matrix.lens == 'security' && 'security-reviewer' || 'docs-reviewer' }}.md.

            You are the "${{ matrix.lens }}" reviewer (claude track). Stay in lens.
            Use `gh pr comment` for one summary, prefixed "[claude/${{ matrix.lens }}]".
            Use `mcp__github_inline_comment__create_inline_comment` for line-level findings.
          claude_args: |
            --max-turns 15
            --allowedTools "Read,Glob,Grep,mcp__github_inline_comment__create_inline_comment,Bash(git:*),Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*)"

      # PLACEHOLDER for v2:
      # - name: Run review (model=codex, lens=...)
      #   if: matrix.model == 'codex'
      #   run: |
      #     pip install codex-cli  # or equivalent
      #     codex review --pr ${{ github.event.pull_request.number }} \
      #       --lens ${{ matrix.lens }} \
      #       --prompt-file .claude/agents/${{ matrix.lens }}-reviewer.md
      #   env:
      #     OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      # - name: Run review (model=mistral, lens=...)
      #   if: matrix.model == 'mistral'
      #   run: |
      #     # Via OpenCode or direct Mistral SDK
      #     ...
```

Reviewer prompts (`pragmatic-reviewer.md` etc.) must be written vendor-neutrally:
- Describe capabilities (`read git diff`, `post inline pull-request comment`, `read repo files`) — not tool names
- Output format: standardised (markdown with severity tags). Rendering to GH inline comments happens per runtime.

### C.3 Verification artifact

```bash
# In a throwaway repo with the v2 workflow:
gh pr create --title "test" --body "trivial: typo"
sleep 30
gh pr view --comments | grep -c '\[claude/'
# Trivial → 1 comment ([claude/docs])

# Large PR
# Change > 100 LOC
gh pr create ...
sleep 60
gh pr view --comments | grep -c '\[claude/'
# Full → 3 comments ([claude/quality], [claude/security], [claude/docs])
```

v2 verification (once Codex+Mistral are in): a PR should get 3 model prefixes per lens; e.g. `[claude/quality]`, `[codex/quality]`, `[mistral/quality]`.

### C.4 Open questions

1. **Codex CLI's PR-review mode** — does it exist? Needs Wave 4 research. Assumption: `codex` has or will soon have a `--pr <n> --lens <x>` mode. If not, we need a wrapper that pipes the diff via stdin.
2. **Mistral CLI** — no first-party CLI. Likely paths: (a) OpenCode with Mistral as the backend, (b) LiteLLM proxy + custom CLI, (c) Mistral Agents API (if mature enough).
3. **Token-budget cap across models** — when 3 models × 3 lenses run on a large PR, the cost is 9× MVP. The risk-tier classifier is not enough; we need model routing per tier (trivial → 1 model, full → all 3).
4. **Cross-model dedup** — if all 3 models flag the same line, should that be 3 comments or 1? **Decision for MVP:** 1 comment per (model × lens × line). Dedup is a v3 feature.

### C.5 Sequencing

1. Write vendor-neutral reviewer prompts (pragmatic + security + docs)
2. Implement the v2 workflow with `MODELS=["claude"]` + placeholder steps for codex/mistral
3. Smoke test in agentic_workflow
4. Patch the rise-repo-bootstrap template
5. (v2 session, separate) Add a Codex step once the runtime selection is settled
6. (v3 session) Add a Mistral step

---

## <a id="d-context"></a>Cross-cutting D — Shared Context governance (MCP)

### D.1 Premise

The whiteboard architecture shows that **Shared Context (Repo + Docs + KG/RAG) is cross-vendor**. Three different models must be able to read the same context without vendor-specific integration.

**MCP (Model Context Protocol)** is an open standard that all three runtimes support:
- Claude Code: native MCP support via `mcp__*` tools
- OpenAI Codex CLI: MCP support shipped 2026-Q1 (verify in Wave 4)
- OpenCode: MCP server configuration is first-class
- Mistral via OpenCode: inherits MCP support

### D.2 What this means for us

**Omni-rag is exposed via an MCP server** (already exists; needs verification that the Codex CLI can read it).

**Repo conventions via filesystem** (AGENTS.md, `.agents/`, `.git/`) — all runtimes can read these.

**What does *not* work cross-vendor:**
- Anthropic-specific MCP tools (`mcp__github_inline_comment__create_inline_comment`) — only exist in claude-code-action. Reviewer prompts therefore must not hardcode this.
- Claude Code's `Skill` system — Claude-only.
- The `~/.claude/` filesystem — Claude-only.

### D.3 Concrete for the plan

1. **Verify omni-rag MCP server works with the Codex CLI** (Wave 4)
2. **Reviewer prompts (§C.2) must not reference Claude-specific MCP tools** — describe capabilities generically
3. **AGENTS.md (§F) gets a "Shared Context" section** listing MCP endpoints + files all agents must know

### D.4 Open questions

1. Codex CLI's MCP support — verify version + functionality
2. Mistral runtime — which of OpenCode / LiteLLM / other has the best MCP support?
3. ~~KG (knowledge graph) in the diagram — what is it concretely?~~ **Resolved 2026-04-29: defer.** See §D.5.

### D.5 Knowledge Graph — deferred (resolved 2026-04-29)

The original v2 plan put a KG box in the architecture diagram without specifying what it concretely is (Neo4j? tree-sitter+SCIP symbol graph? owners-and-modules table?). The ChatGPT "Collaborative Coding Agents" reference architecture made the gap visible — that diagram's Layer 3 names a Knowledge Graph as a distinct artefact alongside the RAG.

**Decision: defer the KG. Instrument a trigger metric instead.**

Rationale:

- The current RAG (omni-rag, semantic search over docs/checkpoints/sessions) covers most "where is X?" questions. The case for a structural graph is "RAG can't find the caller of a known symbol" — that's a *symbol/AST* graph, not the conceptual KG the diagram implied.
- Building Neo4j prematurely is weeks of schema design, ingestion, and maintenance for a problem that has not yet bitten in practice.
- A `tree-sitter` + `sourcegraph/scip` symbol graph would be cheap and repo-local, but only worth it once we observe RAG failing at known-symbol queries.

**Trigger metric** (instrumented in `~/.claude/checkpoints/`): log a line tagged `[kg-trigger]` whenever a session takes more than 3 tool calls to discover a caller of a function whose name was known at the start. If the count exceeds 3 logged events per month, revisit the KG decision and evaluate `tree-sitter` + SCIP first; Neo4j only if SCIP can't model the relationships the trigger surfaced.

**What we do not promise:** the diagram's "Knowledge Graph" box represents a *deferred* artefact, not a planned one. If we never observe the trigger metric firing, we never build it — and the conceptual gap is documented rather than papered over.

(Implementation, when triggered, lives in `omni-rag` per the repo division-of-labor — index/search infrastructure belongs there.)

---

## <a id="e-vendor"></a>Cross-cutting E — Vendor-track separation

### E.1 What is spec, what is implementation

| Layer | Vendor-neutral (spec) | Vendor-specific (implementation) |
|---|---|---|
| Repo conventions | `.agents/tasks/`, branch naming, AGENTS.md, commit trailers | — |
| Task schema | `.agents/schema.json` | — |
| Reviewer prompts | `.claude/agents/*.md` (content) | Path (could move to `.agents/prompts/` if we want) |
| Worktree lifecycle | "create / claim / work / signal / merge / cleanup" | Hooks per runtime |
| CI matrix | tier × lens × model | Action step per model |
| Trailer | "every agent commit must have an attribution trailer" | Trailer format per runtime (Co-Authored-By / Codex-Generated / TBD) |
| Shared Context | "read via MCP or filesystem" | MCP server implementation |
| Orchestration | "coordination via git push collisions" | Per-runtime CLI wrapper (`agentic-task` Python CLI) |

### E.2 Track-rollout strategy

- **Track 1 (Claude):** Implement per §A–§G. Vendor-neutral spec + Claude-specific runtime. Ships across ~6 sessions.
- **Track 2 (Codex):** *Additive.* Requires (a) Codex CLI installed with MCP support, (b) `OPENAI_API_KEY` in GH secrets, (c) Codex trailer format known. Sessions: ~3.
- **Track 3 (Mistral):** *Additive.* Requires runtime selection (OpenCode vs LiteLLM proxy) + API access. Sessions: ~3–5.
- **Track 0 (Gateway):** Before track 2/3 — set up an LLM Gateway (§7 in the decisions table). Otherwise we manage 3 separate API keys + 3 separate billing accounts.

### E.3 Sequencing effects

- Track 1 must *not* lock itself to Claude-specific solutions in the spec — costs nothing now, expensive to retrofit.
- Tracks 2 + 3 are scope for future Tier 2.5/Tier 3 sessions. Not in this plan-doc's sequencing.
- Gateway evaluation is a prerequisite for track 2 — comes first (see §sequencing).

---

## <a id="f-agents"></a>Cross-cutting F — AGENTS.md primary + per-vendor addenda

### F.1 File structure

```
<repo>/
├── AGENTS.md            # PRIMARY — vendor-neutral team rules
├── CLAUDE.md            # Claude-specific additions (skill pointers, hook references)
├── CODEX.md             # Codex-specific additions (when the Codex track is activated)
└── MISTRAL.md           # Mistral-specific additions (when the Mistral track is activated)
```

**AGENTS.md content** (vendor-neutral):
- Build & test commands
- Paths (immutable / generated / ignored)
- Conventions: per-task commits, verify-artifact rule, attribution-trailer format
- Multi-agent: points to `.agents/README.md` for task-claim, branch-naming convention for parallel work
- Shared Context: MCP endpoints + files all agents must read
- Non-goals: vendor-neutral (no DOCX commits, no secrets)

**CLAUDE.md** shrinks to Claude-specific quirks:
- Header: "Read AGENTS.md first. This file adds Claude Code-specific harness conventions."
- Echo-back §2 rule (Claude-specific harness feature)
- `/checkpoint`, `/recall`, `/brief` skill pointers
- Hook references (`~/.claude/hooks/*`)

**CODEX.md** (sketch for v2):
- Header: "Read AGENTS.md first. This file adds OpenAI Codex CLI-specific conventions."
- Codex CLI tools allowlist
- Codex-specific MCP server configurations

**MISTRAL.md** (TBD when the runtime selection is settled).

### F.2 Sequencing

1. Write AGENTS.md for agentic_workflow (vendor-neutral — full content)
2. Shrink CLAUDE.md to a Claude addendum + add a "Read AGENTS.md first" pointer
3. Replicate to omni-rag
4. Patch the rise-repo-bootstrap template
5. Add CODEX.md / MISTRAL.md per runtime when the tracks are activated

---

## <a id="g-trailer"></a>Cross-cutting G — Trailer dual-mode + per-vendor attribution

### G.1 Trailer format per runtime

| Runtime | Default trailer | Alt | Comment |
|---|---|---|---|
| Claude | `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` | `Assisted-by:` (#36105 open) | Dual-mode hook (env `CLAUDE_CODE_TRAILER_MODE`) |
| Codex | `Codex-Generated:` (TBD) or `Assisted-by:` | TBD | OpenAI has not standardised as of 2026-04 — verify Wave 4 |
| Mistral | TBD | TBD | No first-party convention |

### G.2 Hook update

`~/.claude/hooks/co-authored-by.sh` (Claude-only) → update per v1 plan §6: dual-mode with `CLAUDE_CODE_TRAILER_MODE=co-authored-by | assisted-by | both`.

For Codex + Mistral: no Claude Code hook helps (they have their own runtimes). The convention in AGENTS.md requires an attribution trailer; the per-runtime check is that each runtime injects one itself. If a runtime does not → server-side check via a GH Action or a `commit-msg` hook in `.husky/` (or equivalent).

**Concrete for v2:**
- Claude track: hook adapted to dual-mode
- Codex track + Mistral track: add a repo-level `commit-msg` hook that validates that *some* attribution trailer is present on agent-driven commits

### G.3 Open questions

1. Codex's actual trailer format as of 2026-04 (Wave 4)
2. Is the `Co-Authored-By:` vs. `Assisted-by:` question relevant for Codex/Mistral?
3. OSS publication of the co-authored-by hook → expand to multi-runtime (separate session)

---

## <a id="h-orchestrator"></a>Cross-cutting H — Orchestrator candidates (deferred)

Added 2026-04-29 in response to the ChatGPT "Collaborative Coding Agents" reference architecture, which places an explicit **Orchestrator** (decompose, assign, track) above the Human+Agent execution layer. The current toolkit has `.agents/tasks/*.json` as a static queue with manual claim — no decomposition, no dynamic assignment. That is fine while no agent pair has ever pulled from the queue; it stops being fine when ≥1 of the trigger conditions below holds.

### H.1 Candidates

| Candidate | Shape | Strengths | Mismatch |
|---|---|---|---|
| **ColonyOS** | Meta-orchestrator for distributed compute. Function specs → executors pull, ECDSA-signed. Author has prior operational experience with it. | Pull-based across machines; signature-grade attribution; vendor-neutral function specs; user already operates one. | Designed for stateless compute, not stateful coding sessions; no decomposer; non-trivial operational weight (server + Postgres + ETCD). |
| **Temporal** | Workflow engine with durable execution. | Mature; great for "long-running task with retries and human gates"; many language SDKs. | Heavyweight; brings workflow-orchestration semantics that overlap with git PR workflow already used. |
| **`cron` + `agentic-task` script** | Filesystem queue + scheduled poller. | Zero new infra; fits the current `.agents/tasks/` model directly. | No cross-machine pull; no signature-grade attribution; scales poorly past ~20 active tasks. |

### H.2 Adoption triggers

Do **not** start design or implementation until at least **two** of the following are observed:

1. **Multi-machine executors.** ≥1 contributor running agent sessions on hardware other than their primary laptop, with a real need to share the queue across hosts.
2. **In-flight queue pressure.** ≥5 tasks simultaneously in `claimed` / `in_progress` state across runtimes for ≥7 consecutive days.
3. **Attribution-grade need.** ≥1 attribution dispute (audit, compliance, governance) that signature-level orchestrator metadata would have prevented and the `Co-Authored-By:` trailer did not.

### H.3 What this section is *not*

- Not a recommendation to install ColonyOS now. The current `.agents/tasks/*.json` model has not been load-tested even once.
- Not a comparison of orchestrator products in the abstract — only of their fit for *this* toolkit's gap.
- Not the implementation plan. When triggered, the implementation lives in `multi-agentic` (or `omni-rag` if the dispatcher is treated as an index/queue infra concern), not in this spec.

### H.4 What we will do today

- Document this section (done with this commit).
- When writing checkpoints (`/checkpoint`), note any of the trigger conditions if observed, tagged `[orchestrator-trigger]`.
- Re-evaluate at the next monthly retrospective. If two triggers have fired, open a design session.

(See also the comparison-driven implementation plan that produced this section: `~/.claude/checkpoints/multi-agentic/2026-04-29_*.md` if it exists, or the session log around that date.)

---

## <a id="smoke"></a>End-to-end smoke test (verify-artifact for the plan itself)

Smoke test for the Claude track (track 1). Codex/Mistral track tests are specced separately.

```bash
#!/usr/bin/env bash
set -euo pipefail
TEST=/tmp/tier2-smoke-$(date +%s)
mkdir -p "$TEST" && cd "$TEST"
git init -q && git config user.email t@t.t && git config user.name t

# 1. §A — vendor-neutral task claim
mkdir -p .agents/tasks
cat > .agents/schema.json <<EOF
{"$schema":"https://json-schema.org/draft/2020-12/schema","title":"agentic-task","type":"object","required":["id","status"]}
EOF
cat > .agents/tasks/0001.json <<EOF
{"id":"0001","subject":"smoke","status":"pending","created_at":"2026-04-27T13:00:00Z","updated_at":"2026-04-27T13:00:00Z"}
EOF
git add . && git commit -q -m "agents: scaffold + task 0001"

# 2. §B — worktree (Claude-only, requires claude CLI)
# (Skip in smoke test if claude is not present)
command -v claude && claude -w "smoke-b" || echo "skip B (claude CLI not installed)"

# 3. §C — workflow YAML (validate via actionlint if present)
mkdir -p .github/workflows .claude/agents
# copy in agent-review.yml + 3 reviewer prompts
command -v actionlint && actionlint .github/workflows/agent-review.yml || echo "skip C lint"

# 4. §F — AGENTS.md primary
cat > AGENTS.md <<EOF
# AGENTS.md
## Build & test
\`uv sync && uv run pytest\`
EOF
cat > CLAUDE.md <<EOF
Read AGENTS.md first.
EOF
git add . && git commit -q -m "docs: AGENTS.md primary" --trailer "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

# 5. §G — trailer dual-mode
git commit --allow-empty -m "test1" --trailer "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
CLAUDE_CODE_TRAILER_MODE=assisted-by git commit --allow-empty -m "test2" \
  --trailer "Assisted-by: Claude Opus 4.6 <noreply@anthropic.com>"

# Cleanup
cd / && rm -rf "$TEST"
echo "smoke-test PASS"
```

Pass criterion: all 5 steps green, schema-validated task, AGENTS.md committed with trailer, dual-mode trailers accepted.

---

## <a id="sequencing"></a>Sequencing across sessions

> **Implementation home:** Track 1 implementation lives in `multi-agentic` (this repo). The `agentic_workflow` repo hosts the planning history (a redirect stub at `docs/plans/tier2_multi_agent.md` points here).

**Track 1 — Claude.**

| # | Session scope | Pre-req | Verify |
|---|---|---|---|
| 1 | AGENTS.md (primary) + shrink CLAUDE.md in agentic_workflow | — | AGENTS.md committed; CLAUDE.md has "Read AGENTS.md first" |
| 2 | `agentic-task` Python CLI + `.agents/{schema,README,tasks/}` scaffold | 1 | smoke test §A passes |
| 3 | Worktree hooks + per-repo config | 1 | `claude -w "test"` creates an isolated worktree with deterministic port |
| 4 | Trailer dual-mode hook | 1 | Both trailer formats accepted |
| 5 | GH Action workflow + 3 vendor-neutral reviewer prompts | 1, 4 | Trivial PR → 1 comment; full PR → 3 comments |
| 6 | Replicate 1–5 to omni-rag | 5 | Same smoke test passes in omni-rag |
| 7 | Patch the rise-repo-bootstrap template (parity) | 6 | Generate a test repo via the kit |

Total Claude track: 5–10 days over 7 sessions.

**Track 0 — Gateway evaluation.** *Before track 2.*

| # | Session scope | Verify |
|---|---|---|
| 0a | Evaluate Cloudflare AI Gateway / Portkey / LiteLLM / openrouter.ai for 3-provider routing | Decision: chosen gateway + token-budget policy |
| 0b | Set up the gateway locally + `OPENAI_API_KEY`/`MISTRAL_API_KEY`/`ANTHROPIC_API_KEY` via the gateway | Test call against all 3 providers passes via the gateway |

**Track 2 — Codex.** *Requires track 0 + track 1 done.* ~3 sessions. Specced in a separate plan-doc when it's time.

**Track 3 — Mistral.** *Requires track 0 + track 1 done + Mistral runtime selection.* ~3–5 sessions. Specced in a separate plan-doc when it's time.

---

## <a id="open"></a>Open questions (collected)

| # | Question | Decision-gated by |
|---|---|---|
| 1 | Race condition on parallel git pushes from different machines | Test under load; add exponential backoff in the `agentic-task` CLI |
| 2 | Codex CLI's MCP support + version | Wave 4 research |
| 3 | Codex CLI's PR-review mode (or wrapper need) | Wave 4 research |
| 4 | Mistral runtime choice (OpenCode vs LiteLLM vs Mistral Agents) | Track 3 design session |
| 5 | LLM Gateway choice (Cloudflare AI Gateway, Portkey, LiteLLM, openrouter.ai) | Track 0a session |
| 6 | KG in the architecture diagram — what is it concretely? Neo4j? | Clarification from the user |
| 7 | Codex's trailer convention (`Codex-Generated:` exists?) | Wave 4 + OpenAI docs |
| 8 | Cross-model dedup on reviewer comments | v3 feature; specced later |
| 9 | Token-budget cap across 3 models × 3 lenses | v2 feature; model routing per tier |
| 10 | Subagent naming (#27749 closed) | Accept v1 for the Claude track |
| 11 | Cross-runtime worktree paths | Convention: `.worktrees/<runtime>/<slug>/` |
| 12 | OSS publication of the attribution hook (multi-runtime) | Separate session |
| 13 | Anthropic issue #36105 outcome | Monitor monthly |
| 14 | OpenCode adoption — full or only Mistral runtime? | Track 3 design session |

---

## <a id="sources"></a>Sources

### Primary sources (fetched in waves 1–3, the originating session)

**Anthropic / Claude Code:**
- [Building a C compiler with Claude](https://www.anthropic.com/engineering/building-c-compiler) — git-push as lock mechanism
- [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams) — Agent Teams (rejected for v2)
- [Claude Code Hooks reference](https://code.claude.com/docs/en/hooks) — 24 events including WorktreeCreate/Remove
- [Claude Code Desktop](https://code.claude.com/docs/en/desktop) — `.claude/worktrees/<NAME>` default
- [anthropics/claude-code#36105](https://github.com/anthropics/claude-code/issues/36105) — Co-Authored-By → Assisted-by
- [anthropics/claude-code#27749](https://github.com/anthropics/claude-code/issues/27749) — subagent worktree naming closed not-planned

**Cloudflare:**
- [Cloudflare AI code review](https://blog.cloudflare.com/ai-code-review/) — risk-tier classifier + multi-model routing
- [Cloudflare internal AI engineering stack](https://blog.cloudflare.com/internal-ai-engineering-stack/) — JWT-Worker + AI Gateway

**OSS reviewer tools (all MIT):**
- [anthropics/claude-code-action](https://github.com/anthropics/claude-code-action) — Claude track GH Action
- [anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review) — `>80% confidence`
- [OneRedOak/claude-code-workflows](https://github.com/OneRedOak/claude-code-workflows) — Principal-Engineer persona
- [ChrisWiles/claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase) — workflow + agent prompt separation
- [snarktank/ai-pr-review](https://github.com/snarktank/ai-pr-review) — REVIEW_EVENT blocking

**Worktree tools:**
- [tfriedel/claude-worktree-hooks](https://github.com/tfriedel/claude-worktree-hooks) — Claude track hooks
- [Damian Galarza — Extending Claude Code Worktrees](https://www.damiangalarza.com/posts/2026-03-10-extending-claude-code-worktrees-for-true-database-isolation/)

**Vendor-neutral / multi-vendor:**
- [agents.md](https://agents.md/) — Linux Foundation spec, 60k+ repos
- [openai/codex AGENTS.md](https://github.com/openai/codex/blob/main/AGENTS.md) — Codex CLI's own
- [opencode.ai](https://opencode.ai/), [github.com/sst/opencode](https://github.com/sst/opencode) — provider-agnostic runtime (Cloudflare-validated)

**Academic (secondary):**
- [Git Context Controller (arXiv 2508.00031)](https://arxiv.org/abs/2508.00031)
- [AgentGit (arXiv 2511.00628)](https://arxiv.org/abs/2511.00628)
- [EvoGit (arXiv 2506.02049)](https://arxiv.org/abs/2506.02049)

**Practitioner literature:**
- [Addy Osmani — Code Agent Orchestra](https://addyosmani.com/blog/code-agent-orchestra/)
- [Kieran Klaassen swarm gist](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)

### v1 → v2 changelog

- **#3 Task-claim runtime** changed: Agent Teams (Claude-only) → repo-committed `.agents/tasks/` (vendor-neutral)
- **#6 OpenCode** changed: skip → evaluate as a Mistral runtime
- **#7 LLM Gateway** changed: skip → plan
- **#8 AGENTS.md** changed: alongside CLAUDE.md → primary
- **#9 Shared Context (NEW)** — MCP as cross-vendor protocol
- **#10 Trailer (EXTENDED)** — per-vendor patterns
- **§D (NEW)** — Shared Context governance
- **§E (NEW)** — Vendor-track separation

---

## Status

Plan-doc v2 written 2026-04-27 (same day as v1). **No implementations made in that session** — the plan is a starting document for the session sequence in §sequencing.

Verify-artifact for the plan-doc itself: the smoke test in §smoke. Before the first implementation session starts (#1 in sequencing), the smoke test should run at least once to catch design errors.

**Track 1 (Claude) is spec-stable.** Track 2 (Codex) and Track 3 (Mistral) require several open-question answers before their own plan-docs can be written.
