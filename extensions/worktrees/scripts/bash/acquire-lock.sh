#!/usr/bin/env bash
# spec-kit-worktree-parallel: acquire-lock.sh
# Acquire a per-primary-checkout run lock for unattended workflows.
#
# Usage:
#   acquire-lock.sh --run-id <id> [--pid <pid>] [--repo-root <dir>] [--force] [--json]
#
# The lock is stored at <primary>/.specify/run.lock as a JSON file containing
# run_id, pid, and timestamp. Stale-lock detection uses kill -0 against the
# recorded pid: if the process is gone the lock is treated as litter and taken
# over silently, not refused. Pass --pid with the outer session's PID (e.g. the
# shell's $$) so the lock outlives this transient subshell; defaults to $PPID.
#
# Exit codes: 0 acquired, 1 usage/environment error, 3 live lock held by another run

set -euo pipefail

RUN_ID=""
REPO_ROOT=""
FORCE=false
JSON_MODE=false
CALLER_PID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id)    RUN_ID="$2"; shift 2 ;;
    --pid)       CALLER_PID="$2"; shift 2 ;;
    --repo-root) REPO_ROOT="$2"; shift 2 ;;
    --force)     FORCE=true; shift ;;
    --json)      JSON_MODE=true; shift ;;
    --help|-h)
      echo "Usage: $0 --run-id <id> [--pid <pid>] [--repo-root <dir>] [--force] [--json]"
      echo ""
      echo "Required:"
      echo "  --run-id <id>      Run identifier for this run"
      echo ""
      echo "Options:"
      echo "  --pid <pid>        PID of the session process (default: \$PPID)"
      echo "  --repo-root <dir>  Repository root (default: git rev-parse)"
      echo "  --force            Displace a live lock (operator cleanup only)"
      echo "  --json             Output JSON instead of key=value"
      exit 0
      ;;
    *)
      echo "Error: unknown argument $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$RUN_ID" ]]; then
  echo "Error: --run-id is required" >&2
  echo "Usage: $0 --run-id <id>" >&2
  exit 1
fi

# Default: the parent of this subshell, which is more persistent than $$.
PID="${CALLER_PID:-$PPID}"

# --- resolve primary checkout ---
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "Error: not inside a git repository" >&2; exit 1
  }
fi

PRIMARY_ROOT="$(git -C "$REPO_ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || PRIMARY_ROOT=""
if [[ -n "$PRIMARY_ROOT" ]]; then
  PRIMARY_ROOT="$(dirname -- "$PRIMARY_ROOT")"
fi
[[ -n "$PRIMARY_ROOT" && -d "$PRIMARY_ROOT" ]] || PRIMARY_ROOT="$REPO_ROOT"

LOCK_FILE="$PRIMARY_ROOT/.specify/run.lock"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --- helpers ---
json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

json_str_field() {
  sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$1" 2>/dev/null | head -1
}

json_int_field() {
  sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p" "$1" 2>/dev/null | head -1
}

render_lock() {
  cat <<JSON
{
  "run_id": "$(json_escape "$RUN_ID")",
  "pid": $PID,
  "timestamp": "$NOW"
}
JSON
}

write_lock() {
  local tmp
  mkdir -p "$(dirname -- "$LOCK_FILE")"
  tmp="$(mktemp "${LOCK_FILE}.XXXXXX")"
  render_lock > "$tmp"
  mv -f "$tmp" "$LOCK_FILE"
}

# Keep the lock file out of every commit (same pattern as run-context.json).
exclude_lock() {
  local common_dir
  common_dir="$(git -C "$PRIMARY_ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 0
  [[ -n "$common_dir" && -d "$common_dir" ]] || return 0
  mkdir -p "$common_dir/info"
  local exclude_file="$common_dir/info/exclude"
  if ! grep -qxF ".specify/run.lock" "$exclude_file" 2>/dev/null; then
    if [[ -s "$exclude_file" ]] && [[ -n "$(tail -c 1 "$exclude_file")" ]]; then
      echo "" >> "$exclude_file"
    fi
    echo ".specify/run.lock" >> "$exclude_file"
  fi
}

# --- check for an existing lock ---
LOCK_STATUS="acquired"
EXISTING_RUN_ID=""
EXISTING_PID=""

if [[ -f "$LOCK_FILE" ]]; then
  EXISTING_RUN_ID="$(json_str_field "$LOCK_FILE" run_id)"
  EXISTING_PID="$(json_int_field "$LOCK_FILE" pid)"

  if [[ "$EXISTING_RUN_ID" == "$RUN_ID" ]]; then
    # Same run refreshing its own lock — idempotent.
    LOCK_STATUS="refreshed"
  elif $FORCE; then
    LOCK_STATUS="forced"
  elif [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    # The lock owner's process is still alive — live concurrent run.
    echo "Error: $LOCK_FILE is held by run '$EXISTING_RUN_ID' (pid $EXISTING_PID)." >&2
    echo "A second concurrent run against the same primary checkout is not supported." >&2
    echo "Wait for the other run to finish. If it has already finished and the lock is" >&2
    echo "stale (the process no longer exists), remove it with:" >&2
    echo "  rm \"$LOCK_FILE\"" >&2
    echo "or re-run with --force." >&2
    exit 3
  else
    # PID is gone — the lock is litter from a dead or finished run.
    LOCK_STATUS="stale-replaced"
  fi
fi

write_lock
exclude_lock

# --- output ---
if $JSON_MODE; then
  printf '{"lock_status":"%s","run_id":"%s","pid":%s,"lock_file":"%s"}\n' \
    "$LOCK_STATUS" "$(json_escape "$RUN_ID")" "$PID" "$(json_escape "$LOCK_FILE")"
else
  echo "LOCK_STATUS=$LOCK_STATUS"
  echo "RUN_ID=$RUN_ID"
  echo "PID=$PID"
  echo "LOCK_FILE=$LOCK_FILE"
fi

if [[ "$LOCK_STATUS" == "stale-replaced" ]]; then
  echo "[worktrees] Replaced stale lock left by run '$EXISTING_RUN_ID' (pid was $EXISTING_PID)." >&2
elif [[ "$LOCK_STATUS" == "forced" ]]; then
  echo "[worktrees] Forced displacement of lock held by run '$EXISTING_RUN_ID' (pid $EXISTING_PID)." >&2
fi
echo "[worktrees] Lock ${LOCK_STATUS}: $LOCK_FILE (run $RUN_ID, pid $PID)" >&2
