#!/usr/bin/env bash
# hooks/worktree-remove.sh
# Claude Code WorktreeRemove hook — cleans up when a worktree is deleted.
#
# Adapted from tfriedel/claude-worktree-hooks (MIT) per
# ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §B.2.
# Macports/BSD-fix: awk -F= instead of grep -oP (BSD grep has no -P).
#
# Registered via project-scoped .claude/settings.json:
#   "WorktreeRemove" -> bash "$CLAUDE_PROJECT_DIR"/hooks/worktree-remove.sh
#
# Contract:
#   - stdin: JSON with 'worktree_path' field
#   - exit 0 = success
#
set -euo pipefail

INPUT=$(cat)
WORKTREE_PATH=$(echo "$INPUT" | jq -r '.worktree_path')

[ ! -d "$WORKTREE_PATH" ] && exit 0

# --- Kill any process listening on the worktree's DEV_PORT ---
if [ -f "${WORKTREE_PATH}/.env.local" ]; then
  DEV_PORT=$(awk -F= '$1=="DEV_PORT"{print $2; exit}' "${WORKTREE_PATH}/.env.local" 2>/dev/null || true)
  if [ -n "${DEV_PORT:-}" ]; then
    lsof -ti :"$DEV_PORT" 2>/dev/null | xargs -r kill 2>/dev/null || true
  fi
fi

# --- Capture branch BEFORE removing the worktree ---
BRANCH=$(git -C "$WORKTREE_PATH" rev-parse --abbrev-ref HEAD 2>/dev/null || true)

# --- Resolve parent repo (worktree-remove must run from there) ---
PARENT_REPO=$(git -C "$WORKTREE_PATH" rev-parse --git-common-dir 2>/dev/null | xargs -I{} dirname {} 2>/dev/null || true)

# --- Load same per-repo config that create.sh used, to know the branch prefix ---
BRANCH_PREFIX="worktree-"
if [ -n "${PARENT_REPO:-}" ] && [ -d "$PARENT_REPO" ]; then
  REPO_NAME=$(basename "$PARENT_REPO")
  CONFIG_DIR="${HOME}/.claude/worktree-config"
  [ -f "${CONFIG_DIR}/default.env" ] && . "${CONFIG_DIR}/default.env"
  [ -f "${CONFIG_DIR}/${REPO_NAME}.env" ] && . "${CONFIG_DIR}/${REPO_NAME}.env"
fi

# --- Remove worktree, then delete the branch only if it matches a known prefix ---
if [ -n "${PARENT_REPO:-}" ] && [ -d "$PARENT_REPO" ]; then
  git -C "$PARENT_REPO" worktree remove "$WORKTREE_PATH" --force 2>/dev/null || true
  if [ -n "${BRANCH:-}" ]; then
    case "$BRANCH" in
      worktree-*|"${BRANCH_PREFIX}"*)
        git -C "$PARENT_REPO" branch -D "$BRANCH" 2>/dev/null || true
        ;;
    esac
  fi
fi
