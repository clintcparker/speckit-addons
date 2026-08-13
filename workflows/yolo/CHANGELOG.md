# Changelog

All notable changes to the `yolo` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] — 2026-08-13

### Fixed
- **Artifacts a step writes under the feature directory are now made trackable once,
  instead of being force-added by every step that touches them.** Repos routinely ignore
  `specs/*/screenshots/` and `specs/*/releases/` for unrelated reasons, and the workflow
  needs their contents to reach the pushed head. Every step that met the conflict reached
  for `git add -f` independently — five separate times across two observed runs — which
  stages one commit and leaves the next step, the next run and the reviewer's checkout
  facing exactly the same rule. Every step now carries an ARTIFACT VISIBILITY block beside
  its WORKTREE DISCIPLINE block: run `git -C <tree> check-ignore -v` against `feature_dir`
  and the subdirectories the step wrote; when a rule matches, append `!<subdir>/` to
  `<feature_dir>/.gitignore` and commit it, because a `.gitignore` inside the feature
  directory outranks the repo root's and a plain `git add` works from then on. `git add -f`
  is now forbidden outright rather than left as the obvious workaround. The repo's own
  ignore rules are never edited.

## [0.7.0] — 2026-08-13

### Fixed
- **Worktree isolation now covers plain `git`, `gh`, build and test commands, not just
  `.specify` scripts.** `SPECIFY_INIT_DIR` and `SPECIFY_FEATURE_DIRECTORY` are read only by
  `.specify/scripts/**`; everything else a step runs resolves against the current working
  directory, which in an unattended run is the primary checkout — `EnterWorktree` needs an
  interactive approval nobody is there to give, so `session=primary` is the normal outcome.
  Steps therefore committed to whatever branch the primary was standing on. Every step now
  carries a WORKTREE DISCIPLINE block: direct every command at the run's tree explicitly
  (`git -C <tree> …` or `cd <tree>` first), where `<tree>` is the run context's
  `worktree_path`, or its `primary_path` when the run has no worktree; verify
  `git -C <tree> rev-parse --show-toplevel` and `git -C <tree> branch --show-current` against
  the run context before the first write; and treat being about to write in the primary
  checkout as a failed step rather than a workaround.
- **The ARTIFACT COMMIT blocks no longer break when the run has no worktree.** They ran
  `git -C <worktree_path>`, which is an empty argument on the `worktree_isolation=failed`
  path; they now use the `<tree>` the WORKTREE DISCIPLINE block resolves, which falls back to
  the primary checkout in exactly that case.
- **The lock release no longer depends on where the step is standing.** It invoked
  `release-lock.sh` by a repo-relative path, which resolves against the working directory
  — now that steps are told to work inside the worktree, that path could miss. The final
  step now invokes it as `<primary_path>/.specify/extensions/...`, taking `primary_path`
  from the run context; the lock itself has always lived in the primary checkout and the
  script resolves it from either tree.
- **The `worktree` step reports the invariant it establishes.** It now emits
  `worktree_path=<path>` in its fields block alongside the two overrides, and states that the
  overrides are honored only by `.specify/scripts/**` — so a `session=primary` report is no
  longer read as "isolated, as long as the overrides hold".

## [0.6.0] — 2026-08-13

### Fixed
- **Two concurrent unattended runs against the same primary checkout can no longer race.**
  The `worktree` step now acquires a per-primary-checkout lock (`acquire-lock.sh`) after
  determining the branch name (Outline step 1) and before creating anything (Outline step 3).
  A second run whose lock call returns exit code 3 stops immediately — it reports the
  existing `run_id` and `pid` and does not proceed to create a worktree or corrupt the
  first run's working tree. The lock and the run context now share the same `run_id`
  (passed explicitly via `--run-id "$RUN_ID"` to `write-run-context.sh`).
  Requires `worktrees` ≥ 2.4.0.
- **A dead PID is not evidence a run ended, so the lock does not rely on one.** An agent
  harness runs each command in a shell that exits as soon as the call returns; a lock
  stamped with that shell's `$$` reads as stale milliseconds later, which would have let
  every concurrent run through. The lock is held while its process is alive **or** while it
  is younger than `lock_ttl_minutes` (default 240), and the step passes `--pid "$PPID"` —
  the agent process — rather than `$$`.
- **The `implement` step releases the run lock as its final action**, so the next run
  against this checkout is not blocked until the lock's TTL expires. `release-lock.sh` frees
  the lock only while this run still owns it.

## [0.5.0] — 2026-08-12

### Fixed
- **Unattended runs no longer lose artifacts when a step fails or the run dies mid-pipeline.**
  The `specify`, `plan`, `tasks`, and `implement` steps committed nothing: the optional git
  auto-commit hook is `optional: true` and prompts for confirmation — a question an
  unattended run cannot answer. Each step now carries an ARTIFACT COMMIT block in its `args`:
  after completing its primary work, run `git -C <worktree_path> add .` and
  `git -C <worktree_path> commit` with a Conventional Commit message, skipping silently if
  there is nothing to commit. Do not prompt — treat the optional git auto-commit hook as
  answered YES.

## [0.4.0] — 2026-08-12

### Fixed
- **Unattended steps no longer pause for input, and a resumed run no longer regenerates
  artifacts it already produced.** `specify`, `plan`, `tasks`, and `implement` each now carry
  an UNATTENDED RUN block (make every judgment call yourself; never pause) and a PRIOR WORK
  block (if the artifact already exists from a prior run, adopt it without re-running the
  command).

## [0.3.0] — 2026-08-12

### Fixed
- **Every step after `worktree` now resolves the feature from the run context file instead of
  re-deriving it.** The engine has no step-output templating: `specify`, `plan`, `tasks` and
  `implement` received only `{{ inputs.spec }}`, so each one independently answered "which
  feature is this?" from the current branch and `.specify/feature.json` — and an unattended
  run's session is usually standing in the *primary* checkout, where right after a merge both
  name the previously shipped feature. Each step's `args` now carries an explicit FEATURE
  IDENTITY block: read `.specify/run-context.json` (`$SPECIFY_INIT_DIR` first, then the current
  directory, then the primary checkout), take `branch`/`feature_dir`/`worktree_path` from it,
  export the two `SPECIFY_*` overrides, and fail the step loudly if a helper script resolves a
  feature the run context does not name.
- **A script exiting 0 is no longer treated as evidence it found the right feature.** It is not:
  `setup-plan.sh` exits 0 on the wrong feature and plants a template `plan.md` there. The steps
  are told so explicitly.
- The `worktree` step writes the run context (`speckit.worktrees.create` `## Outline` step 4) on
  every path, including `worktree_isolation=failed`, and reports `run_context` as a third field.
  With no ship step here, the run summary carries it along with the other two.

### Changed
- The feature description leads each step's `args`, with the identity block fenced below a
  `--- RUN CONTROL ---` marker, so a preamble cannot be mistaken for part of the spec.

### Requires
- The [`worktrees`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/worktrees)
  extension, now at **2.3.0 or later** — the run context file and its writer are new there.

## [0.2.1] — 2026-08-06

### Fixed
- **The session model documented above the `worktree` step was false for unattended runs.**
  It claimed every later step runs in the worktree because the working directory carries
  forward. Moving the session needs the `EnterWorktree` tool, which requires interactive
  approval that an unattended run has nobody to give — so the working directory does *not*
  carry forward, and the real mechanism is the `SPECIFY_INIT_DIR` /
  `SPECIFY_FEATURE_DIRECTORY` overrides the worktree step emits. The comment now says so.
- The `worktree` step's brief tells it to expect `session=primary`, treat it as the normal
  outcome rather than an error, and emit the overrides as structured fields. This workflow
  has no ship step, so the run summary must carry both `worktree_isolation` and `session` —
  it is the only record the user gets.

### Changed
- **REPORT, DO NOT REMEDY** is explicit in the `worktree` step's brief. "Never prompt" was
  being read as licence to act unilaterally — closing a base-ref gap with `git merge`,
  copying gitignored feature inputs into the worktree. Neither is this step's mandate.

### Requires
- The [`worktrees`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/worktrees)
  extension, now at **2.2.0 or later** — the step relies on the `session` field and the
  `EnterWorktree`-refused path added there.

## [0.2.0] — 2026-08-06

### Fixed

- Worktree isolation is now an explicit first step rather than an inherited
  `before_specify` hook side-effect. A run that did not begin at `speckit.specify` —
  a resume, or a fix-up over an already-specified feature — previously got no worktree
  and executed in the primary checkout, silently, and the branch could not be attached
  to a worktree afterwards. `yolo` has no ship step, so the step reports the outcome in
  the run summary instead of a pull request description.

### Requires

- **Breaking for installs without it:** the
  [`worktrees`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/worktrees)
  extension, at **2.1.0 or later** for the idempotent case detection the step relies on.
  The first step now fails at dispatch when the extension is absent, where 0.1.1 ran
  fine without it. Spec Kit's workflow schema has no machine-readable extension
  requirement — `requires` accepts only `speckit_version` and `integrations` — so this
  is a documentation-only contract. Stay on 0.1.1 if you do not want worktree isolation.

## [0.1.1] — 2026-07-29

### Fixed

- Corrected `requires.speckit_version` from `>=0.8.5` to `>=0.8.12`. Engine-side
  resolution of `integration: "auto"` landed in 0.8.12
  ([spec-kit #2421](https://github.com/github/spec-kit/pull/2421)), not 0.8.5.
  The old floor let 0.8.5–0.8.11 pass the requirement check and then fail at
  dispatch, treating `auto` as a literal integration key — precisely the failure
  the requirement exists to prevent. Caught by the Spec Kit maintainers while
  reviewing the community catalog submission.

## [0.1.0] — 2026-07-29

First published release. Adapted from
[Spec Kit workflows: YOLO mode](https://blog.clintcparker.com/2026/07/28/speckit-workflows/),
with corrections.

### Added

- Four gate-free `command` steps: `specify` → `plan` → `tasks` → `implement`.
- `spec` and `integration` inputs.
- `requires.speckit_version: ">=0.8.5"` for engine-side `integration: "auto"`
  resolution.

### Fixed

- Restored the `{{ inputs.integration }}` and `{{ inputs.spec }}` expressions.
  The version published on the blog had them stripped by the site's Liquid
  templating, so every step rendered as `integration: ""` / `args: ""` — the
  workflow would run but pass an empty spec to each command.

### Removed

- The `scope` input (`full` / `backend-only` / `frontend-only`). It was
  inherited from the built-in `speckit` workflow and referenced by no step, so
  it prompted for a value that changed nothing.

[0.8.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.8.0
[0.7.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.7.0
[0.6.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.6.0
[0.5.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.5.0
[0.4.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.4.0
[0.3.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.3.0
[0.2.1]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.2.1
[0.2.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.2.0
[0.1.1]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.1.1
[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.1.0
