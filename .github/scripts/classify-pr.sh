#!/usr/bin/env bash
# .github/scripts/classify-pr.sh
# Vendor-neutral risk-tier classifier for the agent-review workflow.
#
# Source spec: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §C.1.
#
# Usage:
#   classify-pr.sh <base-sha> <head-sha>
#   BASE=<sha> HEAD=<sha> classify-pr.sh
#
# Output (one key=value per line, suitable for `>> $GITHUB_OUTPUT`):
#   tier=trivial|lite|full
#   lenses=["..."]                # JSON array of {quality,security,docs}
#   models=["claude"]             # JSON array; MVP = ["claude"]
#
# Tiers:
#   - paths under auth/ crypto/ secrets/ security/   → full (any size)
#   - LOC <=10 AND files <=5                         → trivial
#   - LOC <=100 AND files <=20                       → lite
#   - otherwise                                      → full

set -euo pipefail

BASE="${1:-${BASE:-HEAD~1}}"
HEAD="${2:-${HEAD:-HEAD}}"

# `git diff --shortstat` lines look like:
#   " 4 files changed, 17 insertions(+), 3 deletions(-)"
# Sum insertions + deletions to get total touched LOC.
LOC=$(git diff --shortstat "$BASE..$HEAD" | awk '{s+=$4+$6} END {print s+0}')
FILES=$(git diff --name-only "$BASE..$HEAD" | awk 'NF{c++} END {print c+0}')
PATHS=$(git diff --name-only "$BASE..$HEAD")

if printf '%s\n' "$PATHS" | grep -qE '(^|/)(auth|crypto|secrets|security)/'; then
  TIER="full"
elif [ "$LOC" -le 10 ] && [ "$FILES" -le 5 ]; then
  TIER="trivial"
elif [ "$LOC" -le 100 ] && [ "$FILES" -le 20 ]; then
  TIER="lite"
else
  TIER="full"
fi

case "$TIER" in
  trivial) LENSES='["docs"]';;
  lite)    LENSES='["quality","docs"]';;
  full)    LENSES='["quality","security","docs"]';;
esac

# MVP: claude only. v2 will route per tier (e.g. full → all three models).
MODELS='["claude"]'

printf 'tier=%s\n' "$TIER"
printf 'lenses=%s\n' "$LENSES"
printf 'models=%s\n' "$MODELS"
printf 'loc=%s\n' "$LOC"
printf 'files=%s\n' "$FILES"
