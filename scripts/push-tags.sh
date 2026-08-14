#!/usr/bin/env bash
# speckit-addons: push-tags.sh
# Push release tags in batches small enough that GitHub actually fires release.yml.
#
# Usage:
#   scripts/push-tags.sh                    # tag every catalog version missing a tag, push, verify
#   scripts/push-tags.sh <tag>...           # push exactly these tags instead
#   scripts/push-tags.sh --list             # print what would be pushed, touch nothing
#   scripts/push-tags.sh --dry-run          # print the batches, touch nothing
#   scripts/push-tags.sh --batch-size <n>   # default 3
#   scripts/push-tags.sh --no-verify        # skip the post-push release check
#   scripts/push-tags.sh --repo-root <dir>  # operate on another checkout (tests)
#
# WHY THIS EXISTS
#
# GitHub does not emit tag-push events for a push that carries more than three
# tags. The documented behavior is that events for the extra tags are dropped;
# what was observed here on 2026-08-13 is worse -- a single push of five tags
# produced zero workflow runs, not three. Either way the tags land on the remote
# looking perfectly healthy while release.yml never runs, so no release and no
# zip asset is ever created, and nothing anywhere reports an error. The catalog
# on main goes on pinning URLs that 404 for every consumer.
#
# That is not a rare shape in this repo: one fix routinely bumps worktrees,
# send-it, send-it-checked and yolo together, so cutting all four tags in one
# push is the natural move and is exactly the thing that silently does nothing.
#
# Batching alone is not enough, because the failure is silent by construction --
# so unless --no-verify is passed, this waits for the release to appear for every
# tag it pushed and exits non-zero if one never does.
#
# EXPECTED RED RUNS
#
# When several tags go up in sequence, every release.yml run except the last
# finishes red on its final `validate_catalog.py --check-urls` step: that step
# validates the whole catalog, and the later tags do not exist yet when the
# earlier runs reach it. The releases themselves publish correctly -- the publish
# step runs first. This script therefore verifies releases, not run conclusions.
# Confirm the end state with `gh workflow run validate --ref main`.
#
# Exit codes: 0 pushed and verified, 1 usage/preflight error, 2 a release never appeared

set -euo pipefail

DEFAULT_BATCH_SIZE=3
# raw.githubusercontent.com negative-caches a 404 for a few minutes, and
# release.yml's own URL check can outlast the release it just published.
VERIFY_TIMEOUT_SECONDS=300
VERIFY_POLL_SECONDS=10

BATCH_SIZE="$DEFAULT_BATCH_SIZE"
REPO_ROOT=""
LIST_ONLY=false
DRY_RUN=false
VERIFY=true
EXPLICIT_TAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --batch-size) BATCH_SIZE="${2:?--batch-size needs a value}"; shift 2 ;;
    --repo-root)  REPO_ROOT="${2:?--repo-root needs a value}"; shift 2 ;;
    --list)       LIST_ONLY=true; shift ;;
    --dry-run)    DRY_RUN=true; shift ;;
    --no-verify)  VERIFY=false; shift ;;
    --help|-h)    sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)           echo "unknown option: $1" >&2; exit 1 ;;
    *)            EXPLICIT_TAGS+=("$1"); shift ;;
  esac
done

if ! [[ "$BATCH_SIZE" =~ ^[0-9]+$ ]] || [[ "$BATCH_SIZE" -lt 1 ]]; then
  echo "--batch-size must be a positive integer" >&2
  exit 1
fi
if [[ "$BATCH_SIZE" -gt 3 ]]; then
  echo "--batch-size above 3 is the bug this script exists to prevent" >&2
  exit 1
fi

if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
cd "$REPO_ROOT"

# --- which tags -------------------------------------------------------------

# Catalogs are JSON, so this needs no third-party module -- push-tags.sh has to
# work in a checkout where nobody has installed pyyaml yet.
collect_missing_tags() {
  python3 - "$REPO_ROOT" <<'PY'
import json, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])
# Only ours: a third-party entry is released from its own repo, and no tag here
# would ever satisfy it.
OURS = "https://github.com/clintcparker/speckit-addons"

wanted = []
for rel, key, prefix in (
    ("extensions/catalog.json", "extensions", "ext-"),
    ("workflows/catalog.json", "workflows", ""),
):
    path = root / rel
    if not path.exists():
        continue
    for addon_id, entry in json.loads(path.read_text())[key].items():
        if entry.get("repository") != OURS:
            continue
        wanted.append(f"{prefix}{addon_id}-v{entry['version']}")

existing = set()
out = subprocess.run(
    ["git", "-C", str(root), "ls-remote", "--tags", "origin"],
    capture_output=True, text=True, check=True,
).stdout
for line in out.splitlines():
    ref = line.split("\t")[-1]
    # ls-remote lists the peeled ^{} entry for annotated tags too; same name.
    existing.add(ref.removeprefix("refs/tags/").removesuffix("^{}"))

for tag in wanted:
    if tag not in existing:
        print(tag)
PY
}

TAGS=()
if [[ ${#EXPLICIT_TAGS[@]} -gt 0 ]]; then
  TAGS=("${EXPLICIT_TAGS[@]}")
else
  # Not mapfile: macOS ships bash 3.2, where it does not exist.
  while IFS= read -r line; do
    [[ -n "$line" ]] && TAGS+=("$line")
  done < <(collect_missing_tags)
fi

if [[ ${#TAGS[@]} -eq 0 ]]; then
  echo "Every first-party catalog version already has a tag on origin. Nothing to push."
  exit 0
fi

if [[ "$LIST_ONLY" == true ]]; then
  printf '%s\n' "${TAGS[@]}"
  exit 0
fi

# --- preflight --------------------------------------------------------------

# Only enforced when tagging at HEAD. An explicit tag list may name tags that
# already exist locally at older commits, which is the backfill case.
if [[ ${#EXPLICIT_TAGS[@]} -eq 0 ]]; then
  branch="$(git rev-parse --abbrev-ref HEAD)"
  [[ "$branch" == "main" ]] || {
    echo "on '$branch', not main -- catalog versions describe main's tree" >&2; exit 1; }
  [[ -z "$(git status --porcelain)" ]] || {
    echo "working tree is dirty -- tagging HEAD would misrepresent the release" >&2; exit 1; }
  git fetch --quiet origin main
  [[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
    echo "HEAD is not origin/main -- push or pull first" >&2; exit 1; }
fi

for tag in "${TAGS[@]}"; do
  if ! git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
    if [[ "$DRY_RUN" == true ]]; then
      echo "would create $tag at $(git rev-parse --short HEAD)"
    else
      # ext-<id>-v<version> and <id>-v<version>; ids contain hyphens, so split
      # on the last -v, matching release.yml's parser.
      rest="${tag#ext-}"; id="${rest%-v*}"; version="${rest##*-v}"
      git tag -a "$tag" -m "$id $version"
    fi
  fi
done

# --- push, at most $BATCH_SIZE per push -------------------------------------

pushed=()
for ((i = 0; i < ${#TAGS[@]}; i += BATCH_SIZE)); do
  batch=("${TAGS[@]:i:BATCH_SIZE}")
  if [[ "$DRY_RUN" == true ]]; then
    echo "would push: ${batch[*]}"
    continue
  fi
  echo "pushing: ${batch[*]}"
  git push origin "${batch[@]}"
  pushed+=("${batch[@]}")
done

if [[ "$DRY_RUN" == true ]]; then
  exit 0
fi

# --- verify -----------------------------------------------------------------

if [[ "$VERIFY" == false ]]; then
  echo
  echo "Pushed ${#pushed[@]} tag(s), unverified. Confirm with: gh release list"
  exit 0
fi
if ! command -v gh >/dev/null 2>&1; then
  echo
  echo "gh not found -- skipping verification. Confirm each release exists by hand." >&2
  exit 0
fi

echo
echo "Waiting for release.yml to publish ${#pushed[@]} release(s)..."
missing=()
for tag in "${pushed[@]}"; do
  waited=0
  found=true
  until gh release view "$tag" >/dev/null 2>&1; do
    if [[ $waited -ge $VERIFY_TIMEOUT_SECONDS ]]; then
      found=false
      break
    fi
    sleep "$VERIFY_POLL_SECONDS"
    waited=$((waited + VERIFY_POLL_SECONDS))
  done
  if [[ "$found" == true ]]; then
    echo "  ✓ $tag"
  else
    missing+=("$tag")
    echo "  ✗ $tag -- no release after ${VERIFY_TIMEOUT_SECONDS}s"
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  cat >&2 <<EOF

${#missing[@]} tag(s) produced no release: ${missing[*]}

release.yml never ran, or it failed before publishing. Check:
  gh run list --workflow=release --limit ${#pushed[@]}
If there is no run at all for a tag, the event was dropped -- delete the remote
tag and push it again on its own:
  git push origin --delete <tag> && git push origin <tag>
EOF
  exit 2
fi

echo
echo "All ${#pushed[@]} release(s) published. Confirm the catalog end state with:"
echo "  gh workflow run validate --ref main"
