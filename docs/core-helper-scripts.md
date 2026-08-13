# Core patch: make the helper scripts say which feature they found

The three helper scripts every Spec Kit command leans on —
`check-prerequisites.sh`, `setup-plan.sh`, `setup-tasks.sh` — all answer "which
feature is this?" through one function, `get_feature_paths` in
`.specify/scripts/bash/common.sh`. Two of its properties break unattended runs,
and neither is visible from an exit code. Both were hit by the
[send-it harness](send-it-harness.md); this is the upstream half of
[issue #8](https://github.com/clintcparker/speckit-addons/issues/8).

Nothing in this repo vendors these scripts, so this page is a patch to apply,
the way [core-feature-numbering.md](core-feature-numbering.md) is. Verified
against spec-kit **0.16.2**.

## Problem 1 — a wrong answer with exit 0

`get_feature_paths` resolves in this order:

1. `SPECIFY_FEATURE_DIRECTORY`
2. `.specify/feature.json` → `feature_directory`
3. error

Step 2 is the trap. `feature.json` is per-*checkout* state, not per-run, and
every command that resolves a feature the explicit way persists its answer back
into it. So in a primary checkout right after a merge it names the feature that
just shipped — and a run whose step forgot to export the override reads it, gets
a real directory, and proceeds:

```console
$ bash .specify/scripts/bash/check-prerequisites.sh --json     # no override set
{"FEATURE_DIR":"…/specs/001-old-shipped","AVAILABLE_DOCS":[]}
$ echo $?
0
```

`setup-plan.sh` is the same resolution plus `mkdir -p "$FEATURE_DIR"` and a
template copy, so it does not merely misreport — it writes a `plan.md` into the
wrong feature and exits 0. Two concurrent unattended runs once implemented their
own features correctly and then reviewed, QA'd, screenshotted and shipped the
previous, already-merged one, while every helper script exited 0 the whole way.

There is no way for a caller to ask "did you resolve this from my override, or
from whatever the checkout remembers?" — which is the actual missing capability.

## Problem 2 — a hard failure where a warning would do

`check-prerequisites.sh --json` validates before it reports, and `plan.md` is one
of the gates:

```console
$ SPECIFY_FEATURE_DIRECTORY=specs/002-new bash …/check-prerequisites.sh --json
ERROR: plan.md not found in …/specs/002-new
Run /speckit.plan first to create the implementation plan.
$ echo $?
1
```

Every feature that bypassed `/speckit-specify` or `/speckit-plan` — a branch
started by hand, a run that adopted an existing spec — is unreadable through this
script, even for callers that only ever wanted `FEATURE_DIR`. Those callers have
`--paths-only`, which resolves with no validation and (since #3025) no
`feature.json` write; it is the right answer for pure path resolution and this
repo's `screenshots` extension now uses it. It is not the right answer for a
caller that *does* want the validation report and can live without a plan.

## Patch 1 — an opt-in strict mode

In `.specify/scripts/bash/common.sh`, inside `get_feature_paths`, insert after
`current_branch=$(get_current_branch)` and before the
`# Resolve feature directory.  Priority:` comment:

```bash
    # Strict feature pinning, for unattended and multi-worktree runs.
    # Without an explicit SPECIFY_FEATURE_DIRECTORY the resolution below falls
    # back to .specify/feature.json, which in a primary checkout right after a
    # merge names whichever feature was pinned last -- so every caller exits 0
    # on the wrong feature and setup-plan.sh plants a template plan.md in it.
    # SPECIFY_STRICT_FEATURE=1 makes that a hard error instead of a quiet answer.
    case "${SPECIFY_STRICT_FEATURE:-}" in
        1|true|TRUE|yes|YES)
            if [[ -z "${SPECIFY_FEATURE_DIRECTORY:-}" ]]; then
                echo "ERROR: SPECIFY_STRICT_FEATURE is set but SPECIFY_FEATURE_DIRECTORY is not." >&2
                echo "Refusing to resolve the feature from .specify/feature.json: in a primary checkout that names whichever feature was pinned last, not this run's." >&2
                return 1
            fi
            ;;
    esac
```

One env var, defaulting off, patching one function — so all three scripts inherit
it, `--paths-only` included. It does not check that the directory exists: the
first command of a feature's life legitimately creates it.

Export `SPECIFY_STRICT_FEATURE=1` alongside `SPECIFY_INIT_DIR` and
`SPECIFY_FEATURE_DIRECTORY` for the duration of an unattended run, and a step that
loses the override fails where it went wrong instead of eight steps later in
somebody else's feature directory.

## Patch 2 — degrade instead of blocking on a missing plan

In `.specify/scripts/bash/check-prerequisites.sh`, add the flag next to
`--require-tasks` (declaration, `case` arm, and help text):

```bash
ALLOW_MISSING_PLAN=false
```

```bash
        --allow-missing-plan)
            ALLOW_MISSING_PLAN=true
            ;;
```

```text
  --allow-missing-plan  Warn instead of failing when plan.md is absent
```

Then turn the gate itself into a warning under the flag:

```bash
if [[ ! -f "$IMPL_PLAN" ]]; then
    if $ALLOW_MISSING_PLAN; then
        echo "[specify] Warning: plan.md not found in $FEATURE_DIR; continuing without it." >&2
    else
        echo "ERROR: plan.md not found in $FEATURE_DIR" >&2
        echo "Run $(format_speckit_command plan "$REPO_ROOT") first to create the implementation plan." >&2
        exit 1
    fi
fi
```

The warning goes to stderr, so `--json` output stays parseable, and
`AVAILABLE_DOCS` still reports what the feature does have. The feature *directory*
check above it stays a hard error — a missing directory is a resolution failure,
not a missing document.

## Verifying

Seven cases: the bug itself, strict mode in both directions, the plan gate in both
directions, strict reaching `--paths-only`, and the untouched default. Run them
against a throwaway repo so a real `specs/` is never involved.

```bash
run_case() { # <label> <expected-exit> <expected-regex>; ENVV and ARGS set by caller
    local label="$1" want_exit="$2" want_re="$3"
    local T; T=$(mktemp -d)
    mkdir -p "$T/.specify/scripts/bash" "$T/specs/001-old-shipped" "$T/specs/002-new-feature"
    cp "$SRC_BASH"/*.sh "$T/.specify/scripts/bash/"
    printf '# old plan\n' > "$T/specs/001-old-shipped/plan.md"
    printf '{"feature_directory":"specs/001-old-shipped"}\n' > "$T/.specify/feature.json"
    git -C "$T" init -q
    local out rc
    out=$( cd "$T" && env "${ENVV[@]}" bash .specify/scripts/bash/check-prerequisites.sh "${ARGS[@]}" 2>&1 ) && rc=0 || rc=$?
    { [ "$rc" = "$want_exit" ] && printf '%s' "$out" | grep -Eq "$want_re"; } \
        && echo "  PASS  $label" || echo "  FAIL  $label (exit=$rc want=$want_exit) -> $out"
    rm -rf "$T"
}

ENVV=(FOO=bar); ARGS=(--json)
run_case 'unpinned resolves the last-pinned feature (the bug)'  0 '001-old-shipped'
ENVV=(SPECIFY_STRICT_FEATURE=1); ARGS=(--json)
run_case 'strict + no override -> hard error'                   1 'SPECIFY_STRICT_FEATURE is set but SPECIFY_FEATURE_DIRECTORY is not'
ENVV=(SPECIFY_STRICT_FEATURE=1 SPECIFY_FEATURE_DIRECTORY=specs/001-old-shipped); ARGS=(--json)
run_case 'strict + override -> resolves the pinned feature'     0 '001-old-shipped'
ENVV=(SPECIFY_FEATURE_DIRECTORY=specs/002-new-feature); ARGS=(--json)
run_case 'plan-less feature still blocks without the flag'      1 'plan.md not found'
ENVV=(SPECIFY_FEATURE_DIRECTORY=specs/002-new-feature); ARGS=(--json --allow-missing-plan)
run_case 'plan-less feature warns and emits what it can'        0 'Warning: plan.md not found'
ENVV=(SPECIFY_STRICT_FEATURE=1); ARGS=(--json --paths-only)
run_case 'strict applies to --paths-only too'                   1 'SPECIFY_STRICT_FEATURE is set'
ENVV=(FOO=bar); ARGS=(--json --paths-only)
run_case 'unset strict changes nothing'                         0 '001-old-shipped'
```

Set `SRC_BASH` to the directory holding the patched scripts. The first case is the
control: it must keep passing, because it asserts the *unpatched* behavior that
strict mode is opt-in around.

## What ships in this repo instead

A patch nobody applies fixes nothing, so the add-ons here do not depend on either
flag. They close the same two holes from the caller's side:

- Every step of all three workflows carries a FEATURE IDENTITY block: resolve the
  feature from `.specify/run-context.json`, export the overrides from it, and fail
  loudly rather than adopt a feature the run context does not name. That is the
  caller-side equivalent of patch 1, enforced by
  [`tests/test_workflow_isolation.py`](../tests/test_workflow_isolation.py).
- The `screenshots` extension resolves `FEATURE_DIR` from
  `SPECIFY_FEATURE_DIRECTORY` → `run-context.json` →
  `check-prerequisites.sh --paths-only --json`, cross-checks the script's answer
  against the pinned one, and treats a feature with no `spec.md` as a normal
  input. That is the caller-side equivalent of patch 2, enforced by
  [`tests/test_feature_resolution.py`](../tests/test_feature_resolution.py).

Apply the patches as well if you run the harness unattended: the workflow prose
asks the agent to fail on a mismatch, while `SPECIFY_STRICT_FEATURE` makes the
script itself refuse to produce one.

## After upgrading spec-kit

Both patched files stop matching their recorded hashes in
`.specify/integrations/speckit.manifest.json`. Leave the mismatch — it is what
makes `specify upgrade` flag the files as locally modified instead of silently
reverting them. Pristine 0.16.2:

| File | SHA-256 |
|---|---|
| `common.sh` | `de9a49210b1a136e4e7b2bc0c16010a773bace22ef6fa19419b6bc652d50bc3c` |
| `check-prerequisites.sh` | `42cdbe2d61203d0a3306b317c9a6563be25706a9504fbc9c0ea0e2048ee8cb86` |

Re-apply after any core upgrade and re-run the seven cases.
