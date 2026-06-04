#!/usr/bin/env bash
# hooks/worktree-create.sh
# Claude Code WorktreeCreate hook — creates the worktree and runs setup.
#
# Adapted from tfriedel/claude-worktree-hooks (MIT) per
# ~/Developer/agentic_workflow/docs/plans/tier2_multi_agent.md §B.2.
# Macports/BSD-fix: md5 -q (BSD).
#
# Registered via project-scoped .claude/settings.json:
#   "WorktreeCreate" -> bash "$CLAUDE_PROJECT_DIR"/hooks/worktree-create.sh
#
# Contract:
#   - stdin: JSON with 'name', 'session_id', 'cwd' fields (read once)
#   - stdout: absolute worktree path — NOTHING ELSE
#   - /dev/tty: progress messages (bypasses Claude's stdout capture)
#
# Per-user behaviour overrides (sourced if present):
#   ~/.claude/worktree-config/<repo-basename>.env
# overrides
#   ~/.claude/worktree-config/default.env
#
# Recognized config vars:
#   BRANCH_PREFIX  default "worktree-"; for vendor-neutral use "agent/<initials>/claude/<repo>-"
#   ENV_FILES      space-separated; default ".env .env.local"
#   COPY_DIRS      space-separated; default empty
#   INSTALL_CMD    shell command run inside worktree; default empty (e.g. "uv sync")
#
set -euo pipefail

INPUT=$(cat)
NAME=$(echo "$INPUT" | jq -r '.name')
REPO_PATH="${CLAUDE_PROJECT_DIR:-$(pwd)}"
REPO_NAME=$(basename "$REPO_PATH")

# --- Load config (default first, repo-specific overrides) ---
CONFIG_DIR="${HOME}/.claude/worktree-config"
BRANCH_PREFIX="worktree-"
ENV_FILES=".env .env.local"
COPY_DIRS=""
INSTALL_CMD=""
[ -f "${CONFIG_DIR}/default.env" ] && . "${CONFIG_DIR}/default.env"
[ -f "${CONFIG_DIR}/${REPO_NAME}.env" ] && . "${CONFIG_DIR}/${REPO_NAME}.env"

BRANCH="${BRANCH_PREFIX}${NAME}"
WORKTREE_PATH="${REPO_PATH}/.claude/worktrees/${NAME}"

# --- Progress to /dev/tty; stdout reserved for Claude ---
TTY=/dev/tty
# Group the redirect so failures (no tty attached) are swallowed too.
log() { { echo "$*" > "$TTY"; } 2>/dev/null || true; }

# --- Deterministic port via BSD md5 -q (macports-fix from spec §B.2) ---
hash_port() {
  local hash
  hash=$(printf '%s' "$1" | md5 -q | tr -d -c '0-9' | head -c 5)
  echo $(( (hash % 6900) + 3100 ))
}
DEV_PORT=$(hash_port "$BRANCH")

log "Creating worktree (branch: $BRANCH, port: $DEV_PORT, repo: $REPO_NAME)..."

# --- Create the git worktree ---
# IMPORTANT: redirect git output away from stdout — Claude parses stdout for the path
mkdir -p "${REPO_PATH}/.claude/worktrees"
if git -C "$REPO_PATH" rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  git -C "$REPO_PATH" worktree add "$WORKTREE_PATH" "$BRANCH" >/dev/null 2>&1
else
  git -C "$REPO_PATH" worktree add -b "$BRANCH" "$WORKTREE_PATH" HEAD >/dev/null 2>&1
fi

# --- Copy env files from main repo ---
log "  Copying env files..."
for f in $ENV_FILES; do
  [ -f "${REPO_PATH}/$f" ] && cp "${REPO_PATH}/$f" "${WORKTREE_PATH}/$f"
done

# --- Copy directories (data, fixtures, etc.) ---
for d in $COPY_DIRS; do
  if [ -d "${REPO_PATH}/$d" ]; then
    mkdir -p "${WORKTREE_PATH}/$d"
    # BSD cp: -R preserves; trailing /. copies contents not the dir itself
    cp -R "${REPO_PATH}/$d/." "${WORKTREE_PATH}/$d/"
  fi
done

# --- Generate .env.local with deterministic port (appended if file exists) ---
if [ -f "${WORKTREE_PATH}/.env.local" ]; then
  printf '\nDEV_PORT=%s\n' "$DEV_PORT" >> "${WORKTREE_PATH}/.env.local"
else
  printf 'DEV_PORT=%s\n' "$DEV_PORT" > "${WORKTREE_PATH}/.env.local"
fi

# --- Install dependencies (per-repo INSTALL_CMD) ---
LOGFILE="${WORKTREE_PATH}/.worktree-setup.log"
SETUP_ERRORS=()

if [ -n "$INSTALL_CMD" ]; then
  log "  Running: $INSTALL_CMD"
  (cd "${WORKTREE_PATH}" && eval "$INSTALL_CMD") >> "$LOGFILE" 2>&1 \
    || SETUP_ERRORS+=("'$INSTALL_CMD' failed — see $LOGFILE")
fi

# --- Done ---
if [ ${#SETUP_ERRORS[@]} -gt 0 ]; then
  log "Setup completed with errors:"
  { printf '  - %s\n' "${SETUP_ERRORS[@]}" > "$TTY"; } 2>/dev/null || true
else
  log "Worktree ready: $WORKTREE_PATH"
fi

# THE ONLY THING ON STDOUT — Claude parses this as the worktree path
echo "$WORKTREE_PATH"
