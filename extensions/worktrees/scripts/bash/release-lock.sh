#!/usr/bin/env bash
# spec-kit-worktree-parallel: release-lock.sh
# Release the per-primary-checkout run lock, only when it belongs to this run.
#
# A lock held by a different run is left untouched: it may belong to a
# concurrent run that is still active, and removing it would silently allow a
# second run to acquire the lock it relies on.
#
# Usage:
#   release-lock.sh --run-id <id> [--repo-root <dir>] [--json]
#
# Exit codes: 0 success (released, not-held, or not-ours), 1 usage/environment error

set -euo pipefail

RUN_ID=""
REPO_ROOT=""
JSON_MODE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id)    RUN_ID="$2"; shift 2 ;;
    --repo-root) REPO_ROOT="$2"; shift 2 ;;
    --json)      JSON_MODE=true; shift ;;
    --help|-h)
      echo "Usage: $0 --run-id <id> [--repo-root <dir>] [--json]"
      echo ""
      echo "Required:"
      echo "  --run-id <id>      Run identifier to release"
      echo ""
      echo "Options:"
      echo "  --repo-root <dir>  Repository root (default: git rev-parse)"
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

json_str_field() {
  sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$1" 2>/dev/null | head -1
}

json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

RELEASE_STATUS="not-held"

if [[ -f "$LOCK_FILE" ]]; then
  EXISTING_RUN_ID="$(json_str_field "$LOCK_FILE" run_id)"
  if [[ "$EXISTING_RUN_ID" == "$RUN_ID" ]]; then
    rm -f "$LOCK_FILE"
    RELEASE_STATUS="released"
  else
    # Somebody else's lock — leave it alone.
    RELEASE_STATUS="not-ours"
  fi
fi

if $JSON_MODE; then
  printf '{"release_status":"%s","run_id":"%s","lock_file":"%s"}\n' \
    "$RELEASE_STATUS" "$(json_escape "$RUN_ID")" "$(json_escape "$LOCK_FILE")"
else
  echo "RELEASE_STATUS=$RELEASE_STATUS"
  echo "RUN_ID=$RUN_ID"
  echo "LOCK_FILE=$LOCK_FILE"
fi
echo "[worktrees] Lock $RELEASE_STATUS: $LOCK_FILE" >&2
