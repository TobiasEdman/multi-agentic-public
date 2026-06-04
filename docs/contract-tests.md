# Contract tests — the agent-pair integration boundary

## Why this exists

Reviewer agents (`docs/specs/tier2_multi_agent.md` §C) catch human-style problems: quality, security, docs. They don't catch API drift. When two agent pairs ship in parallel — one on `agent/te/claude/api-...`, another on `agent/te/codex/ui-...` — the UI pair consumes whatever shape the API pair last published. If the API pair changes a request body field, the UI pair's tests pass locally and fail at integration.

The fix is to make the **OpenAPI spec the integration boundary**. Both pairs see the same contract. CI verifies that the running implementation matches it. Drift becomes a red check on the offending PR, not a Slack thread on Friday afternoon.

This pattern is from the ChatGPT "Collaborative Coding Agents" reference architecture (Layer 3, "Contracts") and from `multi-agentic/docs/patterns.md` §P1 (git is the coordination substrate; contracts are the cross-pair piece of that substrate).

## When to enable this workflow in a target repo

Enable when **all** of the following hold:

1. The repo ships an HTTP API (or gRPC, or GraphQL) that has external consumers — including agent-pair branches consuming each other.
2. There is a machine-readable contract: `openapi.json` / `openapi.yaml` (REST), `*.proto` (gRPC), or `*.graphql` (GraphQL).
3. Multiple agent pairs are realistically going to land in the same week.

Skip if any of the above is false — the tooling has a real cost (CI minutes, maintenance) and provides no value without a real consumer/provider split.

For `multi-agentic` itself: not enabled. This is a toolkit repo with no service. The template is for *target repos* installing the toolkit via `agentic-task init`.

## Tool choice — Schemathesis (MVP) vs. Pact (upgrade)

| | Schemathesis | Pact |
|---|---|---|
| Direction | Provider verifies own spec | Consumer drives contract |
| Setup cost | Single CI job pointing at OpenAPI URL | Broker + consumer tests + provider verification |
| Catches | Implementation drift from spec | Consumer-side breaking changes |
| Best when | One team owns API + spec | Multiple teams share consumer/provider boundary |

**Default: Schemathesis.** It's a property-based fuzzer that consumes the OpenAPI spec and generates conforming requests; runs against your live service; flags any 5xx response, schema-violating response, or path the spec promises but the implementation doesn't deliver. One CI job, no broker, no separate test suite.

**Upgrade to Pact when** different teams own consumer and provider, and the consumer's expectations need to drive the contract (not the other way round). Pact's broker becomes the source of truth; provider PRs verify against published consumer expectations. This is real overhead — only worth it when you have it.

For agent-pair branches inside one repo, Schemathesis is almost always enough.

## Wiring the template

`templates/_github/workflows/contract-tests.yml.tmpl` ships with placeholders:

| Placeholder | Meaning | Example |
|---|---|---|
| `{{API_SOURCE_PATHS}}` | Extra path-trigger globs (one per line, indented under `paths:`). | `"src/myapi/handlers/**"` |
| `{{API_STARTUP_CMD}}` | Shell command to start the API in CI. | `uvicorn imint.api.main:app --port 8000 &` |
| `{{API_HEALTH_URL}}` | URL the workflow polls until 200 before running schemathesis. | `http://localhost:8000/v1/healthz` |
| `{{API_OPENAPI_URL}}` | URL of the OpenAPI document. | `http://localhost:8000/v1/openapi.json` |

`agentic-task init` will substitute these from a `.agentic-task.yaml` config in the target repo (TBD — config schema not yet shipped). For now, edit the materialised workflow by hand after `agentic-task init`.

## Verifying the workflow works

In a target repo with the workflow installed:

```bash
# 1. Open a draft PR that intentionally breaks the contract:
git checkout -b agent/te/claude/contract-test-smoke
# Edit src/api/handlers.py — change a response field name.
gh pr create --draft --title "smoke: break a response field"

# 2. Wait ~60s; the contract-tests check should be red.
gh pr checks --watch

# 3. Revert the breaking change. The check should be green within a minute.
git revert HEAD
git push
gh pr checks --watch
```

Expected outcome: the workflow fails on the breaking change and recovers on the revert. Capture the workflow run URLs in the PR body — that's the verify-artefakt for installing this workflow in a new repo.

## Failure modes the workflow catches

- Implementation returns a field the spec doesn't declare → schema violation, red.
- Spec promises a path; implementation 404s on it → coverage failure, red.
- Implementation 500s on a request the spec says is valid → check failure, red.
- Spec drifts from implementation in subtle ways (enum values, format constraints) → property-based test surfaces it.

## Failure modes it does **not** catch

- Semantic changes that conform to the spec (e.g. renaming a value within an enum the spec already allows). For these, you need a versioning policy on the spec itself + reviewer agents.
- Changes to the spec that break consumers but the provider implements correctly. For these, you need Pact (or a manual changelog discipline).

## Cross-references

- Spec: [`docs/specs/tier2_multi_agent.md`](specs/tier2_multi_agent.md) §C describes reviewer agents (complementary mechanism).
- Patterns: [`docs/patterns.md`](patterns.md) §P1 (git as coordination substrate) and §P3 (shared-context governance) are the conceptual underpinnings.
- Convention extension: [`docs/conventions-multi-agent.md`](conventions-multi-agent.md) cross-pair section.
