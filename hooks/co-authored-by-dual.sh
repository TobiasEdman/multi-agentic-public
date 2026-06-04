#!/usr/bin/env bash
# co-authored-by-dual.sh — vendor-neutral agent-attribution validator.
#
# Plan: ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §G.
#
# Accepts attribution from any of the three runtimes:
#   Claude  → Co-Authored-By: Claude … / Assisted-by: Claude …
#   Codex   → Co-Authored-By: Codex …  / Assisted-by: Codex …  / Codex-Generated: …
#   Mistral → Co-Authored-By: Mistral … / Assisted-by: Mistral …
#
# Exit 0 = trailer present (and merge/revert commits, which inherit
# attribution from their parents). Exit 1 = no recognised trailer.
# Exit 2 = usage error (missing/unreadable message file).
#
# Usage:
#   As a git commit-msg hook (per agent session):
#     ln -s ../../hooks/co-authored-by-dual.sh .git/hooks/commit-msg
#
#   As a CI server-side check (per PR commit, e.g. in agent-review.yml):
#     for sha in $(git rev-list "$base..$head"); do
#       git log -1 --format=%B "$sha" \
#         | hooks/co-authored-by-dual.sh /dev/stdin || exit 1
#     done
#
# Note: by design this only validates the *trailer*. It does not require
# any specific vendor (single-vendor repos can still use the Claude-only
# ~/.claude/hooks/co-authored-by.sh). It rejects commits with only a
# human Co-Authored-By trailer and no agent signal — those commits
# should either gain an agent trailer or be marked human-authored
# upstream of this check.

set -euo pipefail

MSG_FILE="${1:?usage: $0 <commit-msg-file>}"

if [ ! -f "$MSG_FILE" ]; then
    echo "co-authored-by-dual: $MSG_FILE not found" >&2
    exit 2
fi

# Merge / revert commits inherit attribution from their parents.
if grep -qE '^(Merge|Revert) ' "$MSG_FILE"; then
    exit 0
fi

# Empty messages: defer to the regular commit-msg hook (we don't gate them).
if ! grep -qE '\S' "$MSG_FILE"; then
    exit 0
fi

# Vendor signal: case-insensitive vendor name anywhere in the trailer value.
VENDOR_RE='[Cc]laude|[Cc]odex|[Mm]istral'

if grep -qE "^[Cc]o-[Aa]uthored-[Bb]y:.*(${VENDOR_RE})" "$MSG_FILE"; then
    exit 0
fi

if grep -qE "^[Aa]ssisted-[Bb]y:.*(${VENDOR_RE})" "$MSG_FILE"; then
    exit 0
fi

if grep -qE '^Codex-Generated:' "$MSG_FILE"; then
    exit 0
fi

cat >&2 <<'EOF'
co-authored-by-dual: agent attribution missing from commit message.

This commit appears to be agent-authored. Add a trailer:

  Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
  Co-Authored-By: Codex <noreply@openai.com>
  Co-Authored-By: Mistral <noreply@mistral.ai>
  Assisted-by: Claude | Codex | Mistral …
  Codex-Generated: <model-or-session-id>

(Plan §G.2 — multi-vendor attribution.)
EOF
exit 1
