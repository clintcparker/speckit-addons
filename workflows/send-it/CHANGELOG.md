# Changelog

All notable changes to the `send-it` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] — 2026-08-13

### Fixed
- **Two concurrent unattended runs against the same primary checkout can no longer race.**
  The `worktree` step now acquires a per-primary-checkout lock (`acquire-lock.sh`) after
  determining the branch name (Outline step 1) and before creating anything (Outline step 3).
  A second run whose lock call returns exit code 3 stops immediately — it reports the
  existing `run_id` and `pid` and does not proceed to create a worktree, open a PR, or
  corrupt the first run's working tree. The lock and the run context now share the same
  `run_id` (passed explicitly via `--run-id "$RUN_ID"` to `write-run-context.sh`).
  Requires `worktrees` ≥ 2.4.0.

## [0.6.0] — 2026-08-12

### Fixed
- **Unattended runs no longer lose artifacts when a step fails or the run dies mid-pipeline.**
  The `specify`, `plan`, `tasks`, `screenshots-before`, `implement`, and `screenshots-after`
  steps committed nothing: the optional git auto-commit hook is `optional: true` and prompts
  for confirmation — a question an unattended run cannot answer. Each step now carries an
  ARTIFACT COMMIT block in its `args`: after completing its primary work, run
  `git -C <worktree_path> add .` and `git -C <worktree_path> commit` with a Conventional
  Commit message, skipping silently if there is nothing to commit. This is the unattended
  equivalent of answering YES to the optional git auto-commit hook. The `ship` step already
  did this; now every earlier step does too.

## [0.5.0] — 2026-08-12

### Fixed
- **Unattended steps no longer pause for input, and a resumed run no longer regenerates
  artifacts it already produced.** `specify`, `plan`, `tasks`, and `implement` each now carry
  an UNATTENDED RUN block (make every judgment call yourself; never pause) and a PRIOR WORK
  block (if the artifact already exists from a prior run, adopt it without re-running the
  command).

## [0.4.0] — 2026-08-12

### Fixed
- **Feature identity is pinned for the whole run instead of re-derived by every step.** The
  worktree step emitted carry-forward fields and the prose said "carry forward" — but nothing
  carried them. The engine has no step-output templating: `specify`/`plan`/`tasks`/`implement`
  received only `{{ inputs.spec }}` and the back-half steps only their mode text, so each one
  independently answered "which feature is this?" from the current branch and
  `.specify/feature.json`. An unattended run's session is usually standing in the *primary*
  checkout, where right after a merge both name the previously shipped feature — which is how
  a run can implement its feature correctly and then screenshot and ship a different one.
- The `worktree` step now writes `.specify/run-context.json` (`speckit.worktrees.create`
  `## Outline` step 4) on every path, including `worktree_isolation=failed`, and reports
  `run_context` as a third machine-readable field.
- **Every step after it carries an explicit FEATURE IDENTITY block** in its `args`: read the
  run context (`$SPECIFY_INIT_DIR` first, then the current directory, then the primary
  checkout), take `branch`/`feature_dir`/`worktree_path` from it, export the two `SPECIFY_*`
  overrides, and never infer the feature from the branch, from `feature.json`, or from the
  newest directory under `specs/`. If anything resolves a feature the run context does not
  name, the step fails loudly instead of adopting it — a script exiting 0 is not evidence it
  found the right feature, since `setup-plan.sh` exits 0 on the wrong one and plants a
  template `plan.md` there.
- **`ship` stops rather than guesses.** A missing or disagreeing run context means no commit,
  no push, and no pull request. It is the step that drifted, and the one whose mistake is
  hardest to notice.

### Added
- `ship` surfaces `run_context=collision` near the top of the pull request description: a
  second unattended run owned the run-context pointer in the primary checkout, so both runs'
  later steps were one unexported environment variable away from building the wrong feature.

### Changed
- The feature description leads each step's `args`, with the identity block fenced below a
  `--- RUN CONTROL ---` marker, so a preamble cannot be mistaken for part of the spec.

### Requires
- The [`worktrees`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/worktrees)
  extension, now at **2.3.0 or later** — the run context file and its writer are new there.

## [0.3.1] — 2026-08-06

### Fixed
- **The session model documented above the `worktree` step was false for unattended runs.**
  It claimed every later step runs in the worktree because the working directory carries
  forward. Moving the session needs the `EnterWorktree` tool, which requires interactive
  approval that an unattended run has nobody to give — so the working directory does *not*
  carry forward, and the real mechanism is the `SPECIFY_INIT_DIR` /
  `SPECIFY_FEATURE_DIRECTORY` overrides the worktree step emits. The comment now says so.
- The `worktree` step's brief tells it to expect `session=primary`, treat it as the normal
  outcome rather than an error, and emit the overrides as structured fields.
- The `ship` step carries `session` as well as `worktree_isolation` into the pull request
  description, plus anything the worktree step reported as missing from the worktree.
  `worktree_isolation=created` with `session=primary` previously read as unqualified
  success and got no mention at all.

### Changed
- **REPORT, DO NOT REMEDY** is explicit in the `worktree` step's brief. "Never prompt" was
  being read as licence to act unilaterally — closing a base-ref gap with `git merge`,
  copying gitignored feature inputs into the worktree. Neither is this step's mandate, and
  the first silently drags unpushed commits into the pull request.

### Requires
- The [`worktrees`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/worktrees)
  extension, now at **2.2.0 or later** — the step relies on the `session` field and the
  `EnterWorktree`-refused path added there.

## [0.3.0] — 2026-08-06

### Fixed
- Worktree isolation is now an explicit first step rather than an inherited
  `before_specify` hook side-effect. A run that did not begin at `speckit.specify` — a
  resume, or a fix-up over an already-specified feature — previously got no worktree and
  executed in the primary checkout, silently, and the branch could not be attached to a
  worktree afterwards.
- The ship step now surfaces a non-clean isolation outcome in the pull request
  description: `worktree_isolation=failed` near the top with the branch named, and
  `worktree_isolation=recovered` as a note that the primary checkout was moved to the
  base ref.

### Changed
- The prose comment above `specify` that described the hook is replaced by the new
  `worktree` step's own comment, so there is a single account of the mechanism.

### Requires
- The [`worktrees`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/worktrees)
  extension, at **2.1.0 or later** for the idempotent case detection the step relies on.
  The first step fails at dispatch without the extension. As with `screenshots`, Spec
  Kit's workflow schema cannot express this, so it is a documentation-only contract.

## [0.2.0] — 2026-08-05

### Added
- `screenshots-before` step between `tasks` and `implement`, and
  `screenshots-after` step between `implement` and `ship`. Both dispatch
  `speckit.screenshots.capture` from the `screenshots` extension, which
  self-skips when the feature has no UI surface.
- A SCREENSHOTS SECTION brief in the ship step: the pull request gets one
  before/after table per captured target, with images pinned to the pushed head
  commit SHA.
- Comments documenting the worktree session model — every step after the
  `before_specify` worktree hook runs inside the worktree, not the primary
  checkout.

### Changed
- The ship step now **detects** repository visibility with
  `gh repo view --json visibility` instead of asserting the repository is
  private. Private repos get `blob/{sha}?raw=true` embeds (raw URLs do not
  render for reviewers); public repos get raw URLs. When `gh` cannot answer, it
  assumes private, which renders in both cases.

### Requires
- The [`screenshots`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/screenshots)
  extension. Both capture steps fail at dispatch without it. Spec Kit's workflow
  schema has no machine-readable extension requirement — `requires` accepts only
  `speckit_version` and `integrations` — so this is a documentation-only
  contract.

## [0.1.0] — 2026-07-30

First published release.

### Added

- Five `command` steps: `specify` → `plan` → `tasks` → `implement` → `ship`.
  The first four are `yolo`'s; `ship` is `speckit.ship.run` from the
  [`ship`](https://github.com/arunt14/spec-kit-ship) extension.
- `target_branch` input (default `main`), passed to the `ship` step.
- Unattended `args` prose for the `ship` step: auto-accept every confirmation,
  auto-commit the working tree, never block on CI, and stop only on a rebase
  conflict that cannot be resolved trivially.

[0.6.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.6.0
[0.5.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.5.0
[0.4.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.4.0
[0.3.1]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.3.1
[0.3.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.3.0
[0.2.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.2.0
[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.1.0
