#!/usr/bin/env bash
# spec-kit-worktree-parallel: acquire-lock.sh
# Acquire a per-primary-checkout run lock for unattended workflows.
#
# Usage:
#   acquire-lock.sh --run-id <id> [--pid <pid>] [--ttl-minutes <n>] \
#     [--repo-root <dir>] [--force] [--json]
#
# The lock is stored at <primary>/.specify/run.lock as a JSON file containing
# run_id, pid, timestamp, epoch and ttl_minutes.
#
# A held lock is LIVE, and a second run is refused with exit 3, when EITHER
# signal says so:
#
#   pid  — `kill -0 <pid>` succeeds. A positive answer is conclusive; a negative
#          one is not, because the recorded pid may never have been durable. An
#          agent harness runs each bash invocation in a shell that exits the
#          moment the call returns, so a lock stamped with that shell's $$ reads
#          as dead microseconds later and PID-only detection would wave every
#          concurrent run straight through. Pass --pid with a process that
#          outlives the call -- from the agent's shell, "$PPID" is the agent
#          process itself. The default ($PPID as seen from inside this script,
#          i.e. the shell that invoked it) is a best effort, not a guarantee.
#   age  — the lock is younger than its TTL (default 240 minutes, override with
#          --ttl-minutes or lock_ttl_minutes in worktree-config.yml). This is the
#          signal that actually holds the guarantee, and it is why a finished run
#          should call release-lock.sh rather than leave the file to expire.
#
# Only when both say otherwise -- the process is gone AND the lock has outlived
# its TTL -- is the lock treated as litter and taken over silently.
#
# Exit codes: 0 acquired, 1 usage/environment error, 3 live lock held by another run

set -euo pipefail

DEFAULT_TTL_MINUTES=240

RUN_ID=""
REPO_ROOT=""
CONFIG_FILE=""
FORCE=false
JSON_MODE=false
CALLER_PID=""
TTL_MINUTES=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id)      RUN_ID="$2"; shift 2 ;;
    --pid)         CALLER_PID="$2"; shift 2 ;;
    --ttl-minutes) TTL_MINUTES="$2"; shift 2 ;;
    --repo-root)   REPO_ROOT="$2"; shift 2 ;;
    --config)      CONFIG_FILE="$2"; shift 2 ;;
    --force)       FORCE=true; shift ;;
    --json)        JSON_MODE=true; shift ;;
    --help|-h)
      echo "Usage: $0 --run-id <id> [--pid <pid>] [--ttl-minutes <n>] [--repo-root <dir>] [--force] [--json]"
      echo ""
      echo "Required:"
      echo "  --run-id <id>       Run identifier for this run"
      echo ""
      echo "Options:"
      echo "  --pid <pid>         PID of a process that outlives this call (default: \$PPID)"
      echo "  --ttl-minutes <n>   Age past which an unreleased lock is litter"
      echo "                      (default: lock_ttl_minutes in config, else $DEFAULT_TTL_MINUTES)"
      echo "  --repo-root <dir>   Repository root (default: git rev-parse)"
      echo "  --config <file>     Path to worktree-config.yml (default: auto-detect)"
      echo "  --force             Displace a live lock (operator cleanup only)"
      echo "  --json              Output JSON instead of key=value"
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

if [[ -n "$TTL_MINUTES" && ! "$TTL_MINUTES" =~ ^[0-9]+$ ]]; then
  echo "Error: --ttl-minutes must be a non-negative integer, got '$TTL_MINUTES'" >&2
  exit 1
fi

# Default: the parent of this subshell, which is more persistent than $$.
PID="${CALLER_PID:-$PPID}"

if [[ ! "$PID" =~ ^[0-9]+$ ]]; then
  echo "Error: --pid must be a positive integer, got '$PID'" >&2
  exit 1
fi

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
NOW_EPOCH="$(date -u +%s)"

# --- config (same grep-not-a-parser reader as create-worktree.sh) ---
load_config_value() {
  local key="$1" default="$2" file="$CONFIG_FILE"
  if [[ -z "$file" ]]; then
    for candidate in \
      "$PRIMARY_ROOT/.specify/extensions/worktrees/worktree-config.yml" \
      "$PRIMARY_ROOT/.specify/extensions/worktrees/config.yml"; do
      if [[ -f "$candidate" ]]; then file="$candidate"; break; fi
    done
  fi
  if [[ -n "$file" ]] && [[ -f "$file" ]]; then
    local val
    val=$(grep -E "^${key}:" "$file" 2>/dev/null | head -1 | sed 's/^[^:]*: *//; s/ *#.*//; s/^"//; s/"$//' || true)
    if [[ -n "$val" ]]; then echo "$val"; return; fi
  fi
  echo "$default"
}

if [[ -z "$TTL_MINUTES" ]]; then
  TTL_MINUTES="$(load_config_value "lock_ttl_minutes" "$DEFAULT_TTL_MINUTES")"
  # A malformed config value must not silently disable the guarantee.
  [[ "$TTL_MINUTES" =~ ^[0-9]+$ ]] || TTL_MINUTES="$DEFAULT_TTL_MINUTES"
fi

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
  # `epoch` is written alongside the human-readable `timestamp` so age needs no
  # date parsing: `date -u +%s` is portable, `date -d` and `date -j -f` are not,
  # and this script has to run on macOS's bash 3.2 as well as on CI.
  cat <<JSON
{
  "run_id": "$(json_escape "$RUN_ID")",
  "pid": $PID,
  "timestamp": "$NOW",
  "epoch": $NOW_EPOCH,
  "ttl_minutes": $TTL_MINUTES
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
EXISTING_EPOCH=""
EXISTING_AGE=""

if [[ -f "$LOCK_FILE" ]]; then
  EXISTING_RUN_ID="$(json_str_field "$LOCK_FILE" run_id)"
  EXISTING_PID="$(json_int_field "$LOCK_FILE" pid)"
  EXISTING_EPOCH="$(json_int_field "$LOCK_FILE" epoch)"

  # Two independent liveness signals; either one alone keeps the lock held. See
  # the header for why the pid on its own cannot carry this.
  PID_ALIVE=false
  if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    PID_ALIVE=true
  fi

  WITHIN_TTL=false
  if [[ -n "$EXISTING_EPOCH" ]]; then
    EXISTING_AGE=$(( NOW_EPOCH - EXISTING_EPOCH ))
    # A lock stamped in the future (clock skew, a restored file) is not evidence
    # of expiry, so a negative age counts as young.
    if (( EXISTING_AGE < TTL_MINUTES * 60 )); then
      WITHIN_TTL=true
    fi
  else
    # A lock written before ttl/epoch existed, or one whose file was truncated.
    # There is no age to compare, so fall back to the pid alone.
    WITHIN_TTL=false
  fi

  if [[ "$EXISTING_RUN_ID" == "$RUN_ID" ]]; then
    # Same run refreshing its own lock — idempotent.
    LOCK_STATUS="refreshed"
  elif $FORCE; then
    LOCK_STATUS="forced"
  elif $PID_ALIVE || $WITHIN_TTL; then
    echo "Error: $LOCK_FILE is held by run '$EXISTING_RUN_ID' (pid $EXISTING_PID)." >&2
    if $PID_ALIVE; then
      echo "That run's process is still alive." >&2
    else
      echo "That run's process is gone, but the lock is ${EXISTING_AGE}s old and its TTL is" >&2
      echo "$(( TTL_MINUTES * 60 ))s. A dead pid is not proof the run ended: an agent harness runs each" >&2
      echo "command in a shell that exits immediately, so the recorded pid may never have" >&2
      echo "outlived the call that wrote it." >&2
    fi
    echo "A second concurrent run against the same primary checkout is not supported." >&2
    echo "Wait for the other run to finish — a run that ends cleanly releases the lock with" >&2
    echo "  bash release-lock.sh --run-id '$EXISTING_RUN_ID'" >&2
    echo "If you know that run is over, release it that way, remove the file:" >&2
    echo "  rm \"$LOCK_FILE\"" >&2
    echo "or re-run with --force." >&2
    exit 3
  else
    # Process gone AND older than the TTL — litter from a run that died without
    # releasing.
    LOCK_STATUS="stale-replaced"
  fi
fi

write_lock
exclude_lock

# --- output ---
if $JSON_MODE; then
  printf '{"lock_status":"%s","run_id":"%s","pid":%s,"ttl_minutes":%s,"lock_file":"%s"}\n' \
    "$LOCK_STATUS" "$(json_escape "$RUN_ID")" "$PID" "$TTL_MINUTES" "$(json_escape "$LOCK_FILE")"
else
  echo "LOCK_STATUS=$LOCK_STATUS"
  echo "RUN_ID=$RUN_ID"
  echo "PID=$PID"
  echo "TTL_MINUTES=$TTL_MINUTES"
  echo "LOCK_FILE=$LOCK_FILE"
fi

if [[ "$LOCK_STATUS" == "stale-replaced" ]]; then
  echo "[worktrees] Replaced stale lock left by run '$EXISTING_RUN_ID' (pid was $EXISTING_PID, age ${EXISTING_AGE}s)." >&2
elif [[ "$LOCK_STATUS" == "forced" ]]; then
  echo "[worktrees] Forced displacement of lock held by run '$EXISTING_RUN_ID' (pid $EXISTING_PID)." >&2
fi
echo "[worktrees] Lock ${LOCK_STATUS}: $LOCK_FILE (run $RUN_ID, pid $PID)" >&2
