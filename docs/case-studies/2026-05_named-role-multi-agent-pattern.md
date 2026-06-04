# Case study — <biz-gui-repo> (May 2026)

**Status:** in-flight at time of writing (session `<session-X>`, ~22 h elapsed, last event 2026-05-12 11:19 UTC)
**Source repo:** `~/Developer/<biz-gui-repo>/` (cut from `<biz-analytics-repo>` mid-session)
**Session JSONL:** `~/.claude/projects/-Users-tobiasedman-Developer-<biz-analytics-repo>/<session-X>.jsonl`
**Why this case matters:** first observed session that runs the Tier 2 multi-agent pattern from this repo's `specs/` in production, with **named role agents** (Product Owner, Developer, Architect, Reviewer/EC, BC, Frontend Builder), not generic Explore dispatches.

## What got built in one session

A meta-frontend replacing <system-A> UI + <system-B> UI for the application-review process at <organisation>:

- **Backend:** FastAPI, SQLite reviews store, LLM-stub
- **Frontend:** Vite + React, Application List (Table + Kanban) + Application Detail
- **<system-A> integration:** mock rewritten to **verified real-world shapes** — confirmed live against `<internal-api-host>` TESTMILJÖ session
- **<system-B> integration:** mock with fixtures
- **Compliance engine:** `backend/compliance.py`, 12 rules (§<delegation-rule> margin/size, export-control, dual-use, <example-funding-instrument> margin floor, BP-step-1/BP-step-2 gates, GDPR keywords, etc.), **29/29 pytest green**
- **LLM-stöd:** 4 roller (drafta / sammanfatta / compliance / smart routing)
- **Parallel review workflow:** BC + avd-affärsutvecklare + EC kan flagga & blocka oberoende

93 distinct files written. 1 commit so far (working-dir state is large).

## The multi-agent shape — observed, not specified

22 `Agent` dispatches over the session, clustering into **five distinct phases**, each using the same pattern: *parallel role dispatches → synthesise → next phase*.

### Phase 1 — Discovery (5 parallel agents, t = 0)

```
14:00  Agent 1: Funder landscape
14:00  Agent 2: Document & content reuse
14:01  Agent 3: Consortium & partners
14:01  Agent 4: Budget & finance
14:01  Agent 5: Workflow & governance
```

Five exploratory agents fired in 60 seconds. Outputs landed in `docs/feature-spec/01–05_*.md` + `00_synthesis.md`. This is the "fan out to discover the problem space" move — the analogue of the four-lens retrospective method in `<workflow-repo>`, but on a *forward-looking* design problem.

### Phase 2 — Build infrastructure (3 parallel agents, t + 18 h)

```
08:43  vLLM deploy plan + scripts on ICE
08:44  Frontend Phase 2 Kanban list
08:44  Compliance regelmotor module
```

Three independent infrastructure tracks dispatched in parallel. Each one produced a working module that landed in the repo. No coordination overhead between agents — each owned a separate file tree.

### Phase 3 — Per-role LLM mapping (4 parallel agents)

```
09:12  LLM mapping från Researcher-perspektiv
09:12  LLM mapping från admin-role-perspektiv
09:12  LLM mapping från Reviewer/Chef-perspektiv
09:13  LLM mapping från Business Controller-perspektiv
```

Four agents map *the same problem* (where does LLM-help add value?) from *four different stakeholder perspectives*. This is the **structural parallel** the multi-angle retrospective method (in `<workflow-repo>/docs/lessons/multi_angle_report.md`) used for analysis, applied here to *forward design*.

### Phase 4 — Flow simulation per role (4 parallel agents)

```
10:00  Simulering: researcher-role driver <example-flow>
10:00  Simulering: FA stödjer <example-flow>
10:01  Simulering: Reviewer/EC granskar <example-flow>
10:01  Simulering: BC granskar <example-flow> ekonomiskt
```

The same four roles now simulate *running* the <example-funding> application flow they helped map in Phase 3. This is a **two-pass design pattern** — same agents, same roles, deeper grounding. Phase 3 produces *what should happen*; Phase 4 produces *what actually happens when you walk through it*.

### Phase 5 — Spec / dev / arch loop (sequential + parallel)

```
10:21  Product Owner skriver user stories
10:23  Clarification till PO om grant-livscykeln
10:38  Developer gap-analys mot user stories      (parallel)
10:38  Architect arkitektur-analys                (parallel)
11:14  Frontend Builder: Phase 2 UI-iteration
```

The PO produces user stories. The user (<author>) asks a clarifying question back to the PO. Developer + Architect run *in parallel* against the user stories — each takes its own angle. The Frontend Builder iterates the UI based on the synthesised gap-analysis.

**This is the canonical multi-agent dev loop the Tier 2 spec describes**, observed in the wild for the first time.

## Why this matters for `<multi-agent-toolkit>`

Three things this session validates that were *speculative* in the Tier 2 spec:

### 1. Named role agents work in practice

Pre-rework, all `Agent` dispatches were generic (`Explore`, `Plan`, `general-purpose` for research). This session is the first where **the role names carry real meaning** — Product Owner, Architect, Developer, Reviewer/EC, BC, Frontend Builder. Each role is a *persona*, not just a task definition, and the persona shapes the output.

**Implication for the spec:** the `subagent_type` field should support role-named personas, not just task-typed dispatches. Each role gets its own `~/.claude/agents/<role>.md` definition (analogous to how `savant-reviewer.md` is structured).

### 2. The parallel-role-mapping pattern is a primitive

Phase 3 (LLM mapping × 4 roles) and Phase 4 (Flow simulation × 4 roles) both use the same shape: *N agents in parallel, each with a different persona, examining the same problem*. This is the **multi-angle method**, originally documented for retrospective analysis, working equally well for **forward design**.

**Implication for the spec:** this pattern deserves a name and a section. Suggest `docs/patterns.md` §P-multi-angle or similar. The pattern has two variants:
- **Retrospective multi-angle**: agents analyse existing material (sessions, code, docs)
- **Forward multi-angle**: agents simulate future state from different stakeholder perspectives

Same mechanism, two domains.

### 3. The PO → Dev + Arch parallel loop is a near-substitute for a small team

In Phase 5, the user delegated:
- Stakeholder representation (PO writing user stories)
- Implementation gap analysis (Developer)
- Architectural review (Architect)
- UI iteration (Frontend Builder)

…to four parallel agent invocations. In a traditional team this is **four humans, three meetings, two days**. Here it's four `Agent` calls in 53 minutes.

**Implication for the spec:** the `<multi-agent-toolkit>` toolkit should ship templates for the *team-substitution* pattern. Concretely: a CLI `agentic-task team-loop --stakeholder=X --story=Y` that runs the PO → Dev + Arch → Frontend cascade. This is a Track 1 #2 (the agentic-task CLI) follow-on.

## What the corpus pattern-detector caught in this session

The continuous-analysis system flagged 8 findings against this session's JSONL (run: `python3 scripts/detect_patterns.py` in `<workflow-repo>`):

- **`file-re-read`** — `backend/applications.py` read **13×** in the same session. Working-memory pressure signal; this is exactly the kind of file that should have been pulled into a high-fidelity in-session reference.
- **`edit-without-read`** — 5 files edited without a prior Read (`mock_server/lime/fixtures.py`, `docker-compose.yml`, etc.). Indicates the long session was operating partly on memorised assumptions about file content rather than ground truth.

What the detector **missed** but probably should have caught:

- *"kör steg 1+2 nu"* — compressed-numeric plan reference. The `plan-without-todowrite` rule expects *"steg 1: … steg 2: …"*; the *"steg 1+2"* form is missed. **Rule needs widening.**
- **550 user turns, only 1 commit in 22 h** — there's no rule today for "uncommitted-work-spike". When this commit lands it will be a giant-commit, but the *risk window* (22 h of unmerged work in `/tmp`-equivalent state) is currently invisible to the detector.

Both findings are good carry-forwards for the next detector iteration.

## What the user said that captures the shift

Three user turns from late in the session are worth quoting:

> *"add a product owner that can formulate user stories based on the agent outputs and a developer and an architect agent as well, let them analyse based on the user stories and the architecture"*  — 10:20

This is the explicit pivot from generic agents to **named-role agents**. The session captures the moment the user moved from *"dispatch an Explore agent"* to *"dispatch the PO, then the Architect, then the Frontend Builder"*. It's not the same operation; it's a different ontological commitment.

> *"Vad rekommenderar du, i vilken ände är det bäst att börja? eller skall vi skicka tillbaks frågan till dev och arkitekt?"*  — 10:50

Delegation of an architectural decision to the dev + arch agents — treating them as **substitute team members**, not tools. The §1 "diagnosis vs directive" rule was *honoured* here: the user asked a question (*"vad rekommenderar du?"*), got a recommendation, then chose to escalate to the agent team.

> *"guit lämnar jag till agenterna"*  — 11:12

Full async-delegering. The UI domain handed to agents to iterate while the user moves on. This is §8 async hand-off applied to a *whole product surface*, not just a long-running shell job.

## Open question for the spec

The session demonstrates that the named-role pattern works. But it also surfaces a gap: **how do roles share context with each other across dispatches?**

Today the user is the broker — they receive output from agent N, decide what's relevant, paste it into agent N+1's prompt. In Phase 5 the Developer and Architect agents both got the user stories from the PO agent, but only because the user manually carried them across. This is exactly the *37% multi-agent failure rate from inter-agent misalignment* the AgentGit research identified.

The Tier 2 spec calls for `.agents/` as a shared-context substrate. This session is the **best evidence yet** that `.agents/` is necessary. Worth elevating in the next track 1 iteration.

## Pointers

- Session JSONL (truth source): `~/.claude/projects/-Users-tobiasedman-Developer-<biz-analytics-repo>/<session-X>.jsonl`
- In-repo checkpoint (user-written, 2026-05-12 milestone): see most recent file under `~/.claude/checkpoints/<biz-analytics-repo>/` or `~/.claude/checkpoints/<biz-gui-repo>/`
- Source repos: `~/Developer/<biz-analytics-repo>/` (parent), `~/Developer/<biz-gui-repo>/` (the actual build target)
- Tier 2 spec referenced: `~/Developer/<workflow-repo>/docs/plans/tier2_multi_agent.md`
- Pattern detector output: `~/Developer/<workflow-repo>/analysis/patterns/_summary.md` (filter by session_id `<session-X>`)

---

*Draft 2026-05-12 — written while the session is still live. Verify role-mapping details against the session JSONL before quoting in external materials.*
