#!/usr/bin/env bash
# spec-kit-worktree-parallel: write-run-context.sh
# Pin one run's feature identity to a file every later step can read.
#
# Usage:
#   write-run-context.sh --branch <name> --isolation <state> --session <where> \
#     [--worktree-path <dir>] [--feature-dir <dir>] [--base-ref <ref>] \
#     [--run-id <id>] [--repo-root <dir>] [--force] [--json]
#
# Why this exists: a workflow engine with no step-output templating gives each
# later step nothing but its own args, so every step re-answers "which feature is
# this?" from the current branch and .specify/feature.json. Immediately after a
# merge both name the PREVIOUS feature, and the back half of the run (review, qa,
# screenshots, ship) silently drifts onto it. This file is the run's answer,
# written once, read by everything after.
#
# Two copies, deliberately:
#   <worktree>/.specify/run-context.json  the canonical one, in the tree the
#                                         feature actually lives in
#   <primary>/.specify/run-context.json   a pointer, written only when the two
#                                         differ -- an unattended run's session
#                                         usually stays in the primary checkout
#                                         (EnterWorktree needs an approval nobody
#                                         is there to give), and a step standing
#                                         there has no other way to find the
#                                         first copy
#
# Neither copy is ever committed: the file is appended to $GIT_COMMON_DIR/info/exclude,
# which is local, untracked, and shared by every worktree of the repo.
#
# Exit codes: 0 written, 1 usage/environment error, 3 collision (another run's
# pointer is in the primary and still live -- see --force).

set -euo pipefail

BRANCH=""
ISOLATION=""
SESSION=""
WORKTREE_PATH=""
FEATURE_DIR=""
BASE_REF=""
RUN_ID=""
REPO_ROOT=""
FORCE=false
JSON_MODE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)        BRANCH="$2"; shift 2 ;;
    --isolation)     ISOLATION="$2"; shift 2 ;;
    --session)       SESSION="$2"; shift 2 ;;
    --worktree-path) WORKTREE_PATH="$2"; shift 2 ;;
    --feature-dir)   FEATURE_DIR="$2"; shift 2 ;;
    --base-ref)      BASE_REF="$2"; shift 2 ;;
    --run-id)        RUN_ID="$2"; shift 2 ;;
    --repo-root)     REPO_ROOT="$2"; shift 2 ;;
    --force)         FORCE=true; shift ;;
    --json)          JSON_MODE=true; shift ;;
    --help|-h)
      echo "Usage: $0 --branch <name> --isolation <state> --session <where> [options]"
      echo ""
      echo "Required:"
      echo "  --branch <name>        Feature branch this run owns"
      echo "  --isolation <state>    created|already|entered|recovered|failed"
      echo "  --session <where>      worktree|primary"
      echo ""
      echo "Options:"
      echo "  --worktree-path <dir>  Worktree holding the branch (omit when there is none)"
      echo "  --feature-dir <dir>    Spec directory (default: <tree>/specs/<branch>)"
      echo "  --base-ref <ref>       Ref the branch was cut from"
      echo "  --run-id <id>          Run identifier (default: <utc-timestamp>-<branch>)"
      echo "  --repo-root <dir>      Repository root (default: git rev-parse)"
      echo "  --force                Displace another run's pointer in the primary"
      echo "  --json                 Output the context JSON instead of key=value"
      echo "  --help                 Show this help"
      exit 0
      ;;
    *)
      echo "Error: unknown argument $1" >&2; exit 1 ;;
  esac
done

# Spelled out rather than looped: ${var,,} needs bash 4 and macOS ships 3.2.
for required in "branch:$BRANCH" "isolation:$ISOLATION" "session:$SESSION"; do
  if [[ -z "${required#*:}" ]]; then
    echo "Error: --${required%%:*} is required" >&2
    echo "Usage: $0 --branch <name> --isolation <state> --session <where>" >&2
    exit 1
  fi
done

case "$ISOLATION" in
  created|already|entered|recovered|failed) ;;
  *) echo "Error: --isolation must be created|already|entered|recovered|failed, got '$ISOLATION'" >&2; exit 1 ;;
esac

case "$SESSION" in
  worktree|primary) ;;
  *) echo "Error: --session must be worktree|primary, got '$SESSION'" >&2; exit 1 ;;
esac

# --- resolve the primary checkout ---
# Every path below is absolute. A later step may be standing in the primary, in
# the worktree, or (with SPECIFY_INIT_DIR exported) somewhere else entirely, so a
# relative path in this file would resolve differently per reader.
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

abspath() {
  local target="$1" dir base
  [[ "$target" = /* ]] && { echo "${target%/}"; return; }
  dir="$(dirname -- "$target")"
  base="$(basename -- "$target")"
  echo "$(cd "$dir" 2>/dev/null && pwd)/$base"
}

if [[ -n "$WORKTREE_PATH" ]]; then
  WORKTREE_PATH="$(abspath "$WORKTREE_PATH")"
fi

# The tree the feature actually lives in. worktree_isolation=failed means there
# is no worktree and the run is executing in the primary -- that is precisely the
# run that most needs its identity pinned, so it gets a context file too.
if [[ -n "$WORKTREE_PATH" && -d "$WORKTREE_PATH" ]]; then
  FEATURE_TREE="$WORKTREE_PATH"
else
  FEATURE_TREE="$PRIMARY_ROOT"
  WORKTREE_PATH=""
fi

if [[ -z "$FEATURE_DIR" ]]; then
  FEATURE_DIR="$FEATURE_TREE/specs/$BRANCH"
else
  FEATURE_DIR="$(abspath "$FEATURE_DIR")"
fi

CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [[ -z "$RUN_ID" ]]; then
  RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$BRANCH"
fi

# --- JSON helpers ---
# jq is not a dependency of this extension and create-worktree.sh already gets by
# without it; the same sed fallbacks are used here for both directions.
json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

json_field() {
  # json_field <file> <key> -- first string value for that key, empty if absent.
  sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$1" 2>/dev/null | head -1
}

render_context() {
  cat <<JSON
{
  "schema_version": "1.0",
  "run_id": "$(json_escape "$RUN_ID")",
  "created_at": "$CREATED_AT",
  "branch": "$(json_escape "$BRANCH")",
  "feature_dir": "$(json_escape "$FEATURE_DIR")",
  "worktree_path": "$(json_escape "$WORKTREE_PATH")",
  "primary_path": "$(json_escape "$PRIMARY_ROOT")",
  "base_ref": "$(json_escape "$BASE_REF")",
  "worktree_isolation": "$ISOLATION",
  "session": "$SESSION"
}
JSON
}

write_context() {
  # Atomic: a later step reading this file concurrently sees the old bytes or the
  # new ones, never a half-written mixture.
  local dest="$1" tmp
  mkdir -p "$(dirname -- "$dest")"
  tmp="$(mktemp "${dest}.XXXXXX")"
  render_context > "$tmp"
  mv -f "$tmp" "$dest"
}

# --- keep the file out of every commit ---
# ship's brief is "commit every uncommitted change", so an unignored run-context
# lands in the pull request. info/exclude is in the common git dir, so one line
# covers the primary and every worktree, and none of it is tracked.
exclude_run_context() {
  local common_dir
  common_dir="$(git -C "$FEATURE_TREE" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 0
  [[ -n "$common_dir" && -d "$common_dir" ]] || return 0
  mkdir -p "$common_dir/info"
  local exclude_file="$common_dir/info/exclude"
  if ! grep -qxF ".specify/run-context.json" "$exclude_file" 2>/dev/null; then
    # A file that does not end in a newline would otherwise get our pattern glued
    # onto its last line.
    if [[ -s "$exclude_file" ]] && [[ -n "$(tail -c 1 "$exclude_file")" ]]; then
      echo "" >> "$exclude_file"
    fi
    echo ".specify/run-context.json" >> "$exclude_file"
  fi
}

# --- canonical copy, in the tree the feature lives in ---
CANONICAL="$FEATURE_TREE/.specify/run-context.json"
write_context "$CANONICAL"
exclude_run_context

# --- pointer copy in the primary, when the session will be standing there ---
POINTER=""
POINTER_STATUS="not-needed"
DISPLACED_BRANCH=""
if [[ "$FEATURE_TREE" != "$PRIMARY_ROOT" ]]; then
  POINTER="$PRIMARY_ROOT/.specify/run-context.json"
  if [[ -f "$POINTER" ]]; then
    EXISTING_BRANCH="$(json_field "$POINTER" branch)"
    EXISTING_WT="$(json_field "$POINTER" worktree_path)"
    if [[ "$EXISTING_BRANCH" == "$BRANCH" ]]; then
      POINTER_STATUS="refreshed"
    elif $FORCE; then
      POINTER_STATUS="forced"
      DISPLACED_BRANCH="$EXISTING_BRANCH"
    elif [[ -n "$EXISTING_WT" && -d "$EXISTING_WT" ]] \
      && git -C "$PRIMARY_ROOT" show-ref --verify --quiet "refs/heads/$EXISTING_BRANCH"; then
      # The other run's worktree and branch are both still there, so it is live,
      # not litter. Displacing its pointer would send its remaining steps at this
      # feature -- the exact drift this file exists to stop, just aimed the other
      # way. Refuse, and let the caller report it.
      echo "Error: $POINTER already belongs to run '$(json_field "$POINTER" run_id)' on branch '$EXISTING_BRANCH'." >&2
      echo "Two unattended runs cannot share one primary checkout: whichever pointer wins," >&2
      echo "the other run's later steps read it and build the wrong feature." >&2
      echo "The canonical context for this run was still written to:" >&2
      echo "  $CANONICAL" >&2
      echo "Export SPECIFY_INIT_DIR=$FEATURE_TREE for every remaining step, or re-run with" >&2
      echo "--force once the other run has finished." >&2
      exit 3
    else
      # Its worktree or its branch is gone, so the pointer outlived its run.
      POINTER_STATUS="stale-replaced"
      DISPLACED_BRANCH="$EXISTING_BRANCH"
    fi
  else
    POINTER_STATUS="written"
  fi
  write_context "$POINTER"
fi

# --- output ---
if $JSON_MODE; then
  render_context
else
  echo "RUN_ID=$RUN_ID"
  echo "BRANCH=$BRANCH"
  echo "FEATURE_DIR=$FEATURE_DIR"
  echo "WORKTREE_PATH=$WORKTREE_PATH"
  echo "PRIMARY_PATH=$PRIMARY_ROOT"
  echo "RUN_CONTEXT=$CANONICAL"
  echo "RUN_CONTEXT_POINTER=$POINTER"
  echo "POINTER_STATUS=$POINTER_STATUS"
fi

if [[ -n "$DISPLACED_BRANCH" ]]; then
  echo "[worktrees] Replaced a run-context pointer left behind by branch '$DISPLACED_BRANCH'." >&2
fi
echo "[worktrees] Run context: $CANONICAL" >&2
