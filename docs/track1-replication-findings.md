# Track 1 #6 replication findings — first pass against `omni-rag`

> Status: **paused** after recon. Three friction points found before any file was written. Document first, fix the template, then replicate.

Track 1 sequencing #6 says: *"replicate Track 1 #1–5 to a second codebase to validate the spec is portable."* The candidate was `~/Developer/omni-rag/` — a RAG/retrieval system, not a multi-agent toolkit. Working tree clean on `main`. None of the five Track 1 artefacts (`AGENTS.md`, `CLAUDE.md`, `hooks/worktree-*.sh`, `docs/conventions.md`, `.github/workflows/agent-review.yml`) existed there.

Recon (read-only) surfaced three frictions that mean a mechanical copy would propagate problems instead of validating the spec.

---

## Friction #1 — hook symlinks don't scale per repo

**The current rule** (`CLAUDE.md` § Files that must match other files):

> `hooks/worktree-{create,remove}.sh` ↔ `~/.claude/hooks/worktree-{create,remove}.sh` — repo files are canonical; the global paths are symlinks installed at setup time.

**The problem.** `~/.claude/hooks/worktree-create.sh` is **one file per user**, not per repo. It is already a symlink to `multi-agentic/hooks/worktree-create.sh`. If we follow the same pattern from `omni-rag`, the symlinks collide — `~/.claude/hooks/worktree-create.sh` cannot point to two files.

**Why it didn't show up in multi-agentic.** With one repo, "repo-canonical + global symlink" is consistent. With two, the second repo has nowhere to be canonical from.

**Implications for the design:**

- The hook *file* is global (one per user); the per-repo *behaviour* is already factored out into `~/.claude/worktree-config/<repo>.env`. That factoring is correct.
- The "repo-canonical" framing is wrong. The hook implementation should live somewhere that doesn't pretend to belong to one project. Three candidates:
  1. **Global-canonical**: hook lives in `~/.claude/hooks/` directly. Multi-agentic loses its `hooks/worktree-*.sh` (or keeps a copy clearly marked as a snapshot/example).
  2. **Toolkit-canonical**: hook lives in `agentic_workflow/hooks/` or a future `agentic-task` package's data files. `~/.claude/hooks/` symlinks to *that*, not to a project.
  3. **Per-repo-fork**: every repo keeps its own copy. Drift is guaranteed; no thanks.

Option 2 is the cleanest if `agentic-task` is meant to be the install vehicle (per plan §A). Option 1 is fine in the interim.

## Friction #2 — `AGENTS.md` and `conventions.md` are vendor-neutral but **toolkit-specific**

**The setup.** `multi-agentic/AGENTS.md` and `multi-agentic/docs/conventions.md` describe the multi-agent collaboration spec: file locks under `.agents/tasks/`, branch-per-agent (`agent/<initials>/<runtime>/...`), writer/reviewer with three lenses, agent-as-CI-bot, multi-vendor attribution trailers.

**The problem.** `omni-rag` is not a multi-agent toolkit. It is a single-agent RAG/retrieval system. Roughly:

| `conventions.md` section | Portable to omni-rag? |
|---|---|
| §1 Vendor neutrality | n/a — single runtime |
| §2 Per-task commits | yes |
| §3 Verify-artefakt | yes |
| §4 Attribution trailers | yes (Claude trailer only) |
| §5 File locks (`.agents/tasks/`) | no — single agent |
| §6 Branch-per-agent | partial — only the Claude prefix is meaningful |
| §7 Worktree lifecycle | yes |
| §8 Writer/reviewer | yes |
| §9 Agent-as-CI-bot | yes |
| §10 Shared context (MCP) | partial |
| §11 Non-goals | mostly yes |

A mechanical copy gives `omni-rag` an `AGENTS.md` that describes a system it isn't.

**Implications for the design:**

- `templates/AGENTS.md.tmpl` cannot be a single static template. It needs to be parameterised by *what kind of repo this is* — at minimum: `single-agent | multi-agent`, and probably a list of which sections to include.
- The current stub status of `templates/AGENTS.md.tmpl` (`> Stub — not yet authored`) is hiding the fact that a real template would need this structure.
- The vendor-neutral *conventions* (per-task commits, verify-artefakt, attribution, worktree lifecycle, writer/reviewer) are universal and should be a base layer. The multi-agent *protocol* (file locks, branch-per-agent, agent-as-CI-bot matrix, shared context) is an opt-in extension.

A possible split:

- `docs/conventions-base.md` — universal (§§2, 3, 4, 7, 8, 9, 11). Every repo with an agent should have this.
- `docs/conventions-multi-agent.md` — extension (§§1, 5, 6, 10). Only repos coordinating across runtimes need this.

`AGENTS.md` then includes either base alone (for omni-rag) or base + extension (for multi-agentic, des-chatbot once they coordinate, etc.).

## Friction #3 — `agent-review.yml` has an undocumented dependency on `.agents/prompts/`

**The setup.** `.github/workflows/agent-review.yml` line 104 reads `.agents/prompts/{pragmatic,security,docs}-reviewer.md`. The three reviewer prompts exist in `multi-agentic/.agents/prompts/` (good). They are not mentioned in the Track 1 #5 description, in `templates/AGENTS.md.tmpl`, or in `CLAUDE.md` § Files that must match other files.

**The problem.** Replicating only "the workflow file + the classifier" (the two things Track 1 #5 names) leaves the workflow broken. The reviewer-prompt files are an implicit prerequisite.

**Implications for the design:**

- `templates/AGENTS.md.tmpl` (or whatever installer materialises Track 1 #5) needs to also produce `.agents/prompts/`.
- `CLAUDE.md` § Files that must match other files should add: `.github/workflows/agent-review.yml` ↔ `.agents/prompts/{pragmatic,security,docs}-reviewer.md` (workflow assumes the prompts exist at that path).
- The reviewer prompts themselves are vendor-neutral content; they don't need parameterisation, but they *do* need to ship with the workflow.

**Status: resolved 2026-04-28.** `CLAUDE.md` § Files that must match other files now declares the workflow ↔ prompts pairing. The workflow file itself carries a `REQUIRED COMPANION FILES` header comment so local readers see the dependency without chasing CLAUDE.md. Producing `.agents/prompts/` from the installer remains a future `agentic-task init` concern — not a blocker for replicating Track 1 #5 manually.

---

## Recommended order before replicating to a second repo

1. **Decide the hook canonicality question** (Friction #1). Pick option 1, 2, or 3 above. Update `CLAUDE.md` § Files that must match other files.
2. **Split `conventions.md` into base + extension** (Friction #2). Or accept that the template will only ever target multi-agent repos and document that limit explicitly.
3. **Add `.agents/prompts/` to the Track 1 #5 deliverable list** (Friction #3). Update the inventory and the (eventual real) `templates/AGENTS.md.tmpl`.
4. *Then* replicate to omni-rag (or another repo) and the friction surface should be much smaller — leftover frictions become real findings instead of artefacts of a half-finished template.

## Why we paused instead of pushing through

Per `~/.claude/CLAUDE.md` §6 (verify before declaring done): a mechanical replication would produce files that are technically present in `omni-rag` but semantically wrong (an `AGENTS.md` describing the wrong kind of repo, broken hook symlinks, a CI workflow that fails on a missing path). That is worse than no replication at all because it claims the test passed when it didn't.

The correct verify-artefakt for Track 1 #6 is *either* "omni-rag now has working Track 1 artefacts and CI is green on a test PR" *or* "the spec was found unportable in these specific ways, here are the corrections." This document is the second.
