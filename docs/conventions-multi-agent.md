# Conventions (multi-agent extension) — cross-runtime coordination spec

Extends [`conventions-base.md`](conventions-base.md). **Read base first**; this file only adds the cross-runtime layer for repos coordinating multiple agent runtimes (Claude Code, OpenAI Codex CLI, Mistral via OpenCode, …) against the same codebase.

If your repo has only one runtime, you don't need this file — the base spec is sufficient.

Source spec: [`docs/specs/tier2_multi_agent.md`](specs/tier2_multi_agent.md) (v2, multi-vendor).

## Contents

1. [Vendor neutrality (cross-runtime)](#vendor-neutrality)
2. [Attribution — multi-vendor trailers](#attribution-extended)
3. [Branch-per-agent (runtime-aware)](#branch-per-agent-extended)
4. [File locks — `.agents/tasks/`](#file-locks)
5. [Writer/reviewer (runtime tagging)](#writer-reviewer-extended)
6. [Agent-as-CI-bot — risk-tier × lens × model](#agent-as-ci-bot-extended)
7. [Shared context (cross-runtime)](#shared-context-extended)
8. [Non-goals (multi-agent-specific)](#non-goals-extended)

---

## <a id="vendor-neutrality"></a>1. Vendor neutrality (cross-runtime)

The toolkit assumes **three runtimes** running in parallel against the same repo: Claude Code, OpenAI Codex CLI, Mistral via OpenCode. The spec is shared; runtimes are interchangeable.

Two invariants follow:

- **Conventions are vendor-neutral by default.** File paths, schemas, branch names, trailer formats — none of these embed Claude-specific assumptions. Vendor-specific implementations live in clearly-named addenda (`CLAUDE.md`, `CODEX.md`, `MISTRAL.md`) or under per-runtime directories (`~/.claude/hooks/` is fine; `.agents/prompts/` is fine; `.claude/agents/` for shared content is *not*).
- **Coordination via git, not runtime.** Two agents on different runtimes can't talk to each other directly. They can both read `.agents/tasks/*.json` and `git log`. Everything coordinated between agents goes through one of those two.

When in doubt: would this convention still make sense if the only runtime were Codex? If the answer is "no, the convention bakes in Claude Code", refactor before merging.

(This is the cross-runtime version of `conventions-base.md` §1 *Runtime neutrality*. Base says "don't bake in any one runtime"; this section says "and assume three are running in parallel".)

## <a id="attribution-extended"></a>2. Attribution — multi-vendor trailers

Replaces base §4. The base form (`Co-Authored-By: Claude Opus 4.6 …`) is the single-runtime case. With multiple runtimes, every commit ends with one of the trailers below — the human stays as `author`, the agent identity goes in the trailer.

Per [spec §G](specs/tier2_multi_agent.md#g-trailer):

| Runtime | Trailer |
|---|---|
| Claude  | `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` (or `Assisted-by:` per anthropics/claude-code#36105) |
| Codex   | `Co-Authored-By: Codex <noreply@openai.com>`, `Assisted-by: Codex …`, or `Codex-Generated: <model-id>` |
| Mistral | `Co-Authored-By: Mistral <noreply@mistral.ai>` (TBD — Mistral has no first-party convention yet) |

Validation: [`hooks/co-authored-by-dual.sh`](../hooks/co-authored-by-dual.sh) accepts any of the patterns above. Use it as a `git commit-msg` hook (per agent session) or as a CI check (per PR commit). Single-vendor repos can keep using `~/.claude/hooks/co-authored-by.sh`; this hook is what survives the move to multi-vendor.

## <a id="branch-per-agent-extended"></a>3. Branch-per-agent (runtime-aware)

Replaces base §5 *Branch-per-agent*. Base form is `agent/<initials>/<area>-<slug>`; the runtime-aware form inserts `<runtime>`:

```
agent/<initials>/<runtime>/<repo-area>-<short-slug>
```

Examples:

- `agent/te/claude/omnirag-bm25-bench`
- `agent/te/codex/agentic-cli-rewrite`
- `agent/te/mistral/des-contracts-extract`

`<runtime>` is mandatory in this form — `git branch --list 'agent/te/codex/*'` then filters per model. Initials still belong to the human, not the agent.

Reserved prefixes for **fully autonomous PRs** (cloud sessions, scheduled tasks): `claude/<slug>`, `copilot/<slug>`, `codex/<slug>`. They distinguish "I drove" from "the model ran unattended."

## <a id="file-locks"></a>4. File locks — `.agents/tasks/`

Repo-committed JSON, one file per task, with git push as the atomic-lock mechanism (Anthropic C-compiler pattern, scaled to multi-vendor). Single-agent repos don't need this — there's no contention to resolve.

Spec: [`.agents/README.md`](../.agents/README.md). Schema: [`.agents/schema.json`](../.agents/schema.json), generated from [`agentic_task.schema.TASK_SCHEMA`](../src/agentic_task/schema.py).

Reference implementation: the `agentic-task` CLI in this repo (`agentic-task claim|list|complete <repo-path>`). Other runtimes are expected to call it via their shell-tool equivalent rather than reimplement the protocol.

The earlier v1 phrasing of "file-lock convention via `.agents/<agent-id>.json`" (per-agent file) was rejected in plan v2 in favour of the per-task model — it scales to multi-vendor and matches the C-compiler pattern.

## <a id="writer-reviewer-extended"></a>5. Writer/reviewer (runtime tagging)

Extends base §7. Base comment format is `[<lens>] <verdict>` (single runtime). With multiple runtimes reviewing the same PR, the format becomes:

```
[<runtime>/<lens>] <verdict>
```

So 3 runtimes × 3 lenses = 9 distinguishable summary comments on a PR. Reviewer prompts in `.agents/prompts/` are unchanged (already vendor-neutral); only the comment-prefix convention extends.

## <a id="agent-as-ci-bot-extended"></a>6. Agent-as-CI-bot — risk-tier × lens × model

Extends base §8. Base specifies the lens dimension (gated by risk-tier classifier); this section adds the **model** dimension as a matrix axis:

- MVP runs Claude only (the workflow's `model` matrix is `["claude"]`).
- Codex and Mistral are added when their runtimes are available — one matrix entry + one matching `if: matrix.model == '<x>'` step.
- Token-budget routing per tier (trivial → 1 model; full → all 3) is a v3 concern.

Workflow file: [`.github/workflows/agent-review.yml`](../.github/workflows/agent-review.yml). When new model rows land, the review step needs to load reviewer prompts from `.agents/prompts/` (vendor-neutral path), not `.claude/agents/` as the plan §C.2 draft YAML suggests.

**Complementary mechanism — contract tests.** Reviewer agents catch human-style problems (quality, security, docs); they don't catch API drift between agent-pair branches. When pair A ships `agent/te/claude/api-...` and pair B ships `agent/te/codex/ui-...` consuming the same OpenAPI spec, a contract-test workflow runs schemathesis against the live API and flags any deviation from the published spec as a red CI check. See [`contract-tests.md`](contract-tests.md) and the template at [`templates/_github/workflows/contract-tests.yml.tmpl`](../templates/_github/workflows/contract-tests.yml.tmpl). Enable in target repos that ship a machine-readable contract; skip otherwise.

## <a id="shared-context-extended"></a>7. Shared context (cross-runtime)

Extends base §9. Base mentions filesystem + MCP as the two channels. With multiple runtimes consuming the same MCP server (e.g. omni-rag for project-doc search), additional discipline applies on what does **not** travel cross-vendor:

- **Claude-specific MCP tools** (e.g. `mcp__github_inline_comment__create_inline_comment`). Reviewer prompts must not hardcode tool names — name the *capability* and let each runtime adapter map.
- **Claude Code's `Skill` system, `~/.claude/` filesystem, the harness echo-back conventions.** Those belong in `CLAUDE.md`, not in shared `.agents/prompts/` or `docs/conventions-*.md`.
- **Runtime-specific session/checkpoint formats.** A Codex session resume file isn't readable by Claude Code and vice-versa.

The omni-rag MCP server (lives in `agentic_workflow/`) is the canonical shared knowledge layer; all three runtimes consume the same server but each runtime's adapter handles tool-name mapping.

## <a id="non-goals-extended"></a>8. Non-goals (multi-agent-specific)

Extends base §10. Base lists "no DOCX/PDF in `.agents/`" and "no secrets in commits". Multi-agent-specific non-goals:

- **No vendor-specific tool names in shared prompts.** If a tool is Claude-only, name the *capability* in the prompt and let the per-runtime adapter map to the actual tool (see [`.agents/prompts/`](../.agents/prompts/) and the `agent-review.yml` workflow).
- **No "smart" auto-resolving of merge conflicts on `.agents/tasks/*.json`.** If two agents claim the same task and both push, one push fails — the loser rebases and picks again. Don't try to merge conflicting `claimed_by` fields.
