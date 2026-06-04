# Merge Queue — design only, no install

## What this is

A short note on when to enable GitHub native Merge Queue on a target repo, surfaced by the ChatGPT "Collaborative Coding Agents" reference architecture which lists a Merge Queue as a distinct delivery gate (Layer 4: CI/Test → Human PR Review → **Merge Queue** → Deploy).

The toolkit does **not** ship a merge-queue workflow today. GitHub's native single-threaded merge is sufficient until proven otherwise.

## When to enable

Enable GitHub native Merge Queue (Settings → General → Pull requests → "Allow merge queue") on a target repo only when the following has actually happened:

> A merge-conflict-on-rebase between two agent-pair branches cost a session of cleanup. Not a "could happen" — an "it happened, here's the PR thread, here's the human-time it cost."

That is the trigger. Until that's observed, the queue would be a solution to a problem the repo doesn't have, and the cost (CI minutes, configuration drift, learning curve) outweighs the benefit.

## What enabling looks like

1. Settings → General → Pull requests → enable **"Allow merge queue"**
2. Settings → Branches → branch protection rule for `main`:
   - Require a pull request before merging ✅
   - Require status checks to pass ✅
   - Require **branches to be up to date before merging** ✅ (this is what the queue enforces)
   - **Require merge queue** ✅
3. (Optional) Tune `merge_method` (squash for our convention) and `max_entries_to_build`.

No workflow file changes — the queue is GitHub-native, not implemented in `.github/workflows/`.

## Why not now

- **Zero observed contention.** `.agents/tasks/.gitkeep` was the directory's only content as of 2026-04-29. No two agent pairs have ever pushed concurrent PRs in this repo.
- **Cost is real.** Merge queue serializes CI; PRs that would land in 30 seconds wait for the queue to drain. With current usage that cost is pure overhead.
- **GitHub's default is fine for serial merges.** When one PR lands per day, the queue adds nothing.

## Cross-references

- [`docs/specs/tier2_multi_agent.md`](specs/tier2_multi_agent.md) §C (agent-CI) — the per-PR review gate is in place; the merge gate is GitHub-native.
- [`docs/contract-tests.md`](contract-tests.md) — orthogonal mechanism. Contract tests prevent API drift between pairs; the merge queue prevents merge-order races. Both matter at different points in the lifecycle.

## Trigger logging

When the trigger event occurs, log it in the next checkpoint with the tag `[merge-queue-trigger]` and a one-line description (e.g. "PR #42 vs #43 collided on rebase, cost ~30min cleanup"). Two such events in a month flips this from "design only" to "enable now."
