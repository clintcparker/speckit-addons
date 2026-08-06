# Core patch: make `feature_numbering` actually work

`specify init` writes `"feature_numbering"` into `.specify/init-options.json`,
and the [send-it harness](send-it-harness.md) tells you to set it to
`"timestamp"` so parallel worktrees stop colliding on "the next number".

Setting it is necessary but **not sufficient**. Through spec-kit 0.15.2 the core
script that owns feature-directory naming never reads the key.

## The split

Two forks of the same naming logic ship in a harness repo, and only one reads
config:

| Script | Reads config? | Effect |
|---|---|---|
| `extensions/git/scripts/bash/create-new-feature-branch.sh` (this repo's fork) | yes — `branch_numbering` from `git-config.yml` | branch and worktree are timestamped |
| `.specify/scripts/bash/create-new-feature.sh` (core spec-kit) | **no** — only an explicit `--timestamp` flag | `specs/` keeps getting `001-`, `002-`, … |

This is easy to miss, because the two halves disagree silently. The branch and
the worktree look correct — `20260806-102818-durability-and-data` — while the
spec directory beside them is `003-durability`. Nothing errors; the spec file
itself records the timestamped branch name in its header, so a repo can run this
way for weeks before anyone notices the directory prefix never changed.

There is a second path to the same drift. The spec directory is created by the
**agent** following the `speckit.specify` command prose, not by any script, and
that prose asks the model to derive the prefix by hand — "next available 3-digit
number after scanning existing directories in `specs/`". A model that skims the
`feature_numbering` bullet above it produces a sequential name that no config
change can prevent. Some preset copies of that command file (for example
`companion-standard`) are staler still and only mention the deprecated
`branch_numbering` key, which `init` no longer writes.

So the fix has two halves: teach the script to read the key, and make the prose
delegate to the script instead of hand-deriving anything.

## Patch 1 — the script

In `.specify/scripts/bash/create-new-feature.sh`, insert after the
`--number`/`--timestamp` conflict warning and before `# Determine branch prefix`:

```bash
INIT_OPTIONS_FILE="$REPO_ROOT/.specify/init-options.json"

# Read a top-level string value from .specify/init-options.json.
read_init_option() {
    local key="$1"
    [ -f "$INIT_OPTIONS_FILE" ] || return 0
    if command -v python3 >/dev/null 2>&1; then
        SPECKIT_INIT_OPTIONS="$INIT_OPTIONS_FILE" SPECKIT_KEY="$key" python3 -c '
import json, os, sys
try:
    with open(os.environ["SPECKIT_INIT_OPTIONS"], encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, ValueError):
    sys.exit(0)
value = data.get(os.environ["SPECKIT_KEY"])
if isinstance(value, str):
    print(value.strip())
' 2>/dev/null
        return
    fi
    # Fallback when python3 is unavailable; init-options.json is flat and generated.
    grep -E "\"${key}\"[[:space:]]*:" "$INIT_OPTIONS_FILE" 2>/dev/null \
        | head -n 1 \
        | sed -E "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"([^\"]*)\".*/\1/"
}

# Honor init-options.json feature_numbering when the caller didn't decide
# explicitly. Without this the configured strategy is dead and every feature
# directory falls back to sequential numbering regardless of config. An explicit
# --number still forces sequential, mirroring the git extension's
# create-new-feature-branch.sh handling of branch_numbering.
if [ "$USE_TIMESTAMP" != true ] && [ -z "$BRANCH_NUMBER" ]; then
    FEATURE_NUMBERING=$(read_init_option feature_numbering)
    if [ -z "$FEATURE_NUMBERING" ]; then
        FEATURE_NUMBERING=$(read_init_option branch_numbering)
        if [ -n "$FEATURE_NUMBERING" ]; then
            >&2 echo "[specify] Warning: 'branch_numbering' in init-options.json is deprecated. Rename it to 'feature_numbering'."
        fi
    fi
    if [ "$FEATURE_NUMBERING" = "timestamp" ]; then
        USE_TIMESTAMP=true
    fi
fi
```

It mirrors the precedent already set by this repo's `git` fork, which honors
`branch_numbering` for hook callers that cannot pass flags. Both preserve the
same escape hatches: an explicit `--number N` still forces sequential, and an
explicit `--timestamp` still works under a `sequential` config.

## Patch 2 — the command prose

In the installed `speckit.specify` command body — and in the generated
`.claude/skills/speckit-specify/SKILL.md` copy, which is what the agent actually
runs — replace the hand-derivation branch of the
`SPECIFY_FEATURE_DIRECTORY` resolution order with a delegation:

> 2. Otherwise, **run the script** — it is the single source of truth for the
>    directory name:
>
>    ```bash
>    .specify/scripts/bash/create-new-feature.sh --json --short-name "<short-name>" "<feature description>"
>    ```
>
>    Parse `SPEC_FILE` from its JSON output, set `SPECIFY_FEATURE_DIRECTORY` to
>    its parent directory, and skip the manual creation steps.
>
>    **Never hand-compute the prefix.** Do not scan `specs/` for the highest
>    `NNN` and add one — that silently produces sequential names in a repo
>    configured for `timestamp`.

Keep the manual steps as a fallback for an explicitly supplied
`SPECIFY_FEATURE_DIRECTORY` and for non-bash environments.

The skill copy is the one that matters at run time, and per the harness's
skill-regeneration gotcha, `specify extension add <id> --force` and
`specify extension update` will revert command-file edits. Re-apply after either.

## Verifying

Run against a throwaway repo so a real `specs/` is never touched. Six cases —
both numbering modes, absent config, the deprecated key, and both flag
overrides:

```bash
run_case() { # <label> <init-options-json> <expected-regex> [extra args...]
    local label="$1" init_json="$2" expected="$3"; shift 3
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.specify" "$tmp/specs/001-existing" "$tmp/specs/002-existing"
    cp -R "$SRC_SPECIFY/scripts" "$tmp/.specify/scripts"
    cp -R "$SRC_SPECIFY/templates" "$tmp/.specify/templates" 2>/dev/null || true
    printf '%s\n' "$init_json" > "$tmp/.specify/init-options.json"
    git -C "$tmp" init -q 2>/dev/null
    local out
    out=$(cd "$tmp" && bash "$tmp/.specify/scripts/bash/create-new-feature.sh" \
        --json --dry-run --short-name "probe" "$@" "probe feature" 2>/dev/null)
    printf '%s' "$out" | grep -Eq "$expected" \
        && echo "  PASS  $label" || echo "  FAIL  $label -> $out"
    rm -rf "$tmp"
}

run_case 'timestamp config'        '{"feature_numbering": "timestamp"}'  '"BRANCH_NAME":"[0-9]{8}-[0-9]{6}-probe"'
run_case 'sequential config'       '{"feature_numbering": "sequential"}' '"BRANCH_NAME":"003-probe"'
run_case 'no config (default)'     '{}'                                  '"BRANCH_NAME":"003-probe"'
run_case 'deprecated key'          '{"branch_numbering": "timestamp"}'   '"BRANCH_NAME":"[0-9]{8}-[0-9]{6}-probe"'
run_case '--number wins'           '{"feature_numbering": "timestamp"}'  '"BRANCH_NAME":"007-probe"' --number 7
run_case '--timestamp wins'        '{"feature_numbering": "sequential"}' '"BRANCH_NAME":"[0-9]{8}-[0-9]{6}-probe"' --timestamp
```

Set `SRC_SPECIFY` to the `.specify` directory holding the patched script. The
`001-existing`/`002-existing` fixtures matter: they prove a timestamp-configured
repo ignores pre-existing sequential directories rather than continuing the run.

## After upgrading spec-kit

The patched file no longer matches its recorded hash in
`.specify/integrations/speckit.manifest.json` (pristine 0.15.2 is
`ad09a94a2c1107e25e5386a834da1d7a31f9abb06ab8bfd323a7b84038221e39`). Leave that
mismatch in place — it is what makes `specify upgrade` flag the file as locally
modified instead of silently reverting the patch. Re-apply both patches after
any core upgrade, and re-run the six cases.
