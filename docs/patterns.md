# Patterns underlying this toolkit

> The *why* behind the conventions in [`docs/specs/tier2_multi_agent.md`](specs/tier2_multi_agent.md). Extracted from the four-lens research synthesis in [`agentic_workflow/docs/lessons/multi_user_multi_agent.md`](https://github.com/TobiasEdman/agentic_workflow/blob/main/docs/lessons/multi_user_multi_agent.md) §C1–C5 (Apr 2026), where four independent research lenses — Anthropic official, practitioners, academic, enterprise adoption — converged on the same patterns.

These are the load-bearing patterns. If you change the toolkit's design, change them in light of these.

---

## P1 — Git is the coordination substrate

Not messaging, not shared memory — git.

| Lens | How they said it |
|------|------------------|
| **Anthropic** | File-lock pattern in `current_tasks/` (C-compiler, 16 agents). Git worktree per session. *"Claude takes a 'lock' on a task by writing a text file… git's synchronization forces the second agent to pick a different one."* |
| **Practitioners** | *"Git itself remains the real multi-user substrate: branches, PRs, issues, CI."* Branch-/worktree-per-agent is the **default** isolation primitive. |
| **Academic** | **AgentGit** (Nov 2025), **Git Context Controller** (Aug 2025, >80% SWE-Bench Verified), **EvoGit** (Jun 2025) all formalise git operations (commit/branch/merge) as the coordination protocol. |
| **Enterprise** | **Cloudflare** ran 131,246 review-agent runs across 48,095 MRs in one month — all PR-gated. **Shopify** runs 10 agents in parallel with PRs as the human merge point. |

**The unifying claim:** you don't need a custom multi-agent coordination protocol. You need git worktrees, a lockfile convention, PRs as integration points, and CI as the verification gate. The infrastructure already exists.

**How this toolkit applies it:** `.agents/tasks/*.json` with git push as the atomic lock (spec §A); branch-per-agent convention `agent/<initials>/<runtime>/<area>-<slug>` (spec §B); reviewer agents as a PR gate (spec §C).

---

## P2 — Coordination > model

Memory matters more than model choice.

| Lens | Evidence |
|------|----------|
| **Academic** | Trace analyses across frameworks show 40–80% failure rates with **~37% attributable to inter-agent misalignment**. *"Has memory vs. no memory matters more than swapping LLM backbones."* |
| **Practitioners** | *"Verification is the constraint, not generation."* LLM-authored `AGENTS.md` hurts success by ~3% and cost by 20% — **human-curated coordination artifacts beat agent-written ones**. |
| **Anthropic** | Agent Teams docs: *"the lead agent can't steer subagents, subagents can't coordinate"* mid-run. Explicit task decomposition with output-format contracts is what works. |
| **Enterprise** | Shopify centralised an **LLM proxy** → bulk token buying, per-team quotas, model-agnostic routing. The proxy is the coordination primitive, not the model. |

**The unifying claim:** pick any reasonable frontier model; invest everything else in harness quality. *"Skill issue, not model issue."*

**How this toolkit applies it:** vendor-neutral spec from day one (Claude / Codex / Mistral all read the same `.agents/tasks/`); convention layers in [`docs/conventions-base.md`](conventions-base.md) + [`docs/conventions-multi-agent.md`](conventions-multi-agent.md) are the harness; per-task commits + verify-artifact rule are the coordination primitives, not any specific model.

---

## P3 — Shared-context governance is a first-class problem

Multi-user agent setups need explicit access control on memory, config, and secrets — and the tooling for this is just barely emerging.

| Lens | Finding |
|------|---------|
| **Academic** | **Collaborative Memory** (May 2025) introduces private/shared memory tiers with bipartite user-agent-resource graphs + auditable read/write policies. *"Who can see what an agent remembered"* must be first-class. |
| **Anthropic** | Cloud sessions only see what's **committed**. User-level `~/.claude/CLAUDE.md` does NOT propagate. Repo-level `.claude/` is the multi-user substrate. **No shared secrets store** (flagged by Anthropic as scoped-out). |
| **Practitioners** | *"Directory ownership per person"* as a soft-lock convention. AGENTS.md + per-directory CLAUDE.md files encode invariants. |
| **Enterprise** | Cloudflare's plugin architecture **explicitly isolates secrets** — "GitLab and Cloudflare AI Gateway plugins can't see each other's secrets." |

**The unifying claim:** memory and secrets need explicit tiering and access control. Personal context should not leak into team context.

**How this toolkit applies it:** AGENTS.md is the team substrate (committed, vendor-neutral); per-runtime `CLAUDE.md` / `CODEX.md` / `MISTRAL.md` are addenda; personal continuity (skills, checkpoints) lives outside the repo at `~/.claude/` and stays personal. Cross-vendor shared context is reached via MCP, not by reading each other's filesystems (spec §D).

---

## P4 — Agent-on-agent review is the emerging quality gate

The pattern is *not* one agent, one answer. It's specialised reviewer agents running in parallel, each with a different lens, against the same PR.

| Lens | Evidence |
|------|----------|
| **Anthropic** | Subagent definitions (`security-reviewer`, `test-runner`) reusable as one-shot subagents OR long-lived teammates. *"Define a role once… reuse as both."* |
| **Practitioners** | Three-tier review stack: in-process reviewer → local orchestrator → cloud-async PR reviewer. *"Dedicated reviewer agents using read-only access."* |
| **Academic** | **Croto** (ACL 2025): parallel red-team/blue-team agent squads beat single-team exploration on software-quality metrics. |
| **Enterprise** | Cloudflare's 2.7 reviewer runs per MR (multi-lens: security + perf + test-coverage). **Adversarial debate** for bug triage — 5 investigators defending different theories. |

**The unifying claim:** specialised reviewer agents in parallel, each with a different lens.

**How this toolkit applies it:** three vendor-neutral reviewer prompts in [`.agents/prompts/`](../.agents/prompts/) — pragmatic, security, docs lenses; risk-tier × lens × model matrix in `.github/workflows/agent-review.yml` (spec §C). Human approval remains the final gate.

---

## P5 — Attribution at the git layer (still an open problem)

The unsolved governance issue. The community has converged on a workaround, not a native solution.

| Lens | Finding |
|------|---------|
| **Enterprise** | **GitHub Copilot's cloud agent sets author to Copilot on squash-merge, breaking `git blame`** for the requesting human. Community consensus (Apr 2026): signed commits for execution identity, human as `author`, `Co-authored-by:` trailers for the agent. |
| **Anthropic** | Permissions inherit at spawn — *if the lead has --dangerously-skip-permissions, every teammate does too*. Tightening after spawn is not supported at spawn time. |
| **Practitioners** | *"Ultimate accountability still sits with humans"* — but who reviews AI code when everyone uses AI is an open problem. |
| **Academic** | Collaborative Memory formalises access control but *"lacks standardised evaluation."* |

**The unifying claim:** attribution tooling is retrofitted onto git via signed commits + trailers. It works, but it's unusual for a well-understood problem to still be in the workaround phase.

**How this toolkit applies it:** [`hooks/co-authored-by-dual.sh`](../hooks/co-authored-by-dual.sh) accepts `Co-Authored-By:`, `Assisted-by:`, or `Codex-Generated:` trailer forms (spec §G). Human stays as `author`; the agent vendor goes in the trailer. This is a workaround, not a final solution — see [anthropics/claude-code#36105](https://github.com/anthropics/claude-code/issues/36105) for the upstream discussion.

---

## Productive disagreements (the field hasn't settled these)

### Centralisation vs. decentralisation

- **Anthropic** favours orchestrator-worker. *"A lead agent coordinates… the lead is the lead for its lifetime."*
- **Academic (EvoGit)** shows decentralised git-phylogeny coordination works *without* a central orchestrator.
- **Enterprise (Shopify)** runs BOTH: 10 parallel agents with a human merge gatekeeper (centralised) + 45-min sequential critique loops (pipeline).

**Reconciliation:** orchestrator-worker for bounded tasks with clear decomposition; decentralised git-native coordination for longer, exploratory work. Don't mix paradigms inside one task.

### How many teammates?

- **Anthropic:** 3–5 teammates, 5–6 tasks each. *"More teammates means more communication… diminishing returns past ~5."*
- **Anthropic C-compiler:** **16 agents** worked — because each operated on an isolated file-locked task with no inter-agent coordination needed.
- **Shopify:** **10 agents in parallel** works when a human is the merge gatekeeper.

**Reconciliation:** team size is bounded by coordination overhead, not by compute. Independent tasks (branch-per-agent, file-lock) → scale out. Shared-context tasks → cap at ~5.

### Real-time collaboration

- **Anthropic** is explicit: **no** real-time cursors, no Google-Docs-style co-editing. *"Recipients see the latest state when they open the link, but their view doesn't update in real time."*
- **Practitioners** confirm: PRs are the integration point, not live editing.

Multi-user agentic coding in 2026 is snapshot-based, not streaming. This is the ceiling, not a disagreement.

---

## Citations

The full four-lens raw returns and the source synthesis are in [the lessons repo's `multi_user_multi_agent.md`](https://github.com/TobiasEdman/agentic-workflow-lessons/blob/main/docs/lessons/multi_user_multi_agent.md). Primary sources:

Anthropic — [agent-teams](https://code.claude.com/docs/en/agent-teams) · [C-compiler](https://www.anthropic.com/engineering/building-c-compiler) · [multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system)

Practitioners — [Osmani: agent teams](https://addyosmani.com/blog/claude-code-agent-teams/) · [Osmani: orchestra](https://addyosmani.com/blog/code-agent-orchestra/)

Academic — [AgentGit](https://arxiv.org/abs/2511.00628) · [Git Context Controller](https://arxiv.org/abs/2508.00031) · [EvoGit](https://arxiv.org/abs/2506.02049) · [Collaborative Memory](https://arxiv.org/abs/2505.18279) · [Croto (ACL 2025)](https://arxiv.org/abs/2406.08979)

Enterprise — [Cloudflare AI code review](https://blog.cloudflare.com/ai-code-review/) · [Cloudflare internal AI stack](https://blog.cloudflare.com/internal-ai-engineering-stack/) · [Shopify AI-first (Bessemer)](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook) · [Copilot commit attribution discussion](https://github.com/orgs/community/discussions/184395)
