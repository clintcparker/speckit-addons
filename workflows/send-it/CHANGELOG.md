# Changelog

All notable changes to the `send-it` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] — 2026-08-13

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
- **The `ship` step verifies the screenshots it links are actually in the pushed head.**
  It said so in prose; it now says how — `git -C <tree> ls-tree -r <head_sha> --
  <feature_dir>/screenshots/` — and what to do when an image is missing, which was the
  concrete failure behind the force-adds: an image git still considers ignored was never
  committed, so every URL in the Screenshots table 404s for the reviewer.

## [0.8.0] — 2026-08-13

### Fixed
- **Worktree isolation now covers plain `git`, `gh`, build and test commands, not just
  `.specify` scripts.** `SPECIFY_INIT_DIR` and `SPECIFY_FEATURE_DIRECTORY` are read only by
  `.specify/scripts/**`; everything else a step runs resolves against the current working
  directory, which in an unattended run is the primary checkout — `EnterWorktree` needs an
  interactive approval nobody is there to give, so `session=primary` is the normal outcome.
  Steps therefore committed to whatever branch the primary was standing on, and `ship`
  opened its pull requests from it. Every step now carries a WORKTREE DISCIPLINE
  block: direct every command at the run's tree explicitly
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
- **The `ship` step can no longer open a pull request for a branch this run did not build.**
  It now pushes with `git -C <tree> push` and passes `--head <branch>` and `--base <target>`
  to `gh pr create` explicitly rather than letting the head be inferred from the primary's
  current branch, and it stops instead of cutting a new branch at the primary's tip to avoid
  a `base == head` pull request — a workaround that moved the user's checkout under them and
  carried unrelated commits from the primary into the pull request.

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
- **A dead PID is not evidence a run ended, so the lock does not rely on one.** An agent
  harness runs each command in a shell that exits as soon as the call returns; a lock
  stamped with that shell's `$$` reads as stale milliseconds later, which would have let
  every concurrent run through. The lock is held while its process is alive **or** while it
  is younger than `lock_ttl_minutes` (default 240), and the step passes `--pid "$PPID"` —
  the agent process — rather than `$$`.
- **The `ship` step stamps its `run_id` into the pull request description and refuses to
  overwrite a newer one.** The description now ends with
  `<!-- speckit-run-id: <run_id> -->`, and before rewriting the body of a pull request that
  already exists the step compares markers: a marker naming a later run (run ids start with
  a UTC timestamp, so string order is time order) means a newer run has already described
  this branch, and this one posts a comment instead of overwriting it. Belt and braces
  behind the lock, for when the lock was not held.
- **The `ship` step releases the run lock as its final action**, so the next run against
  this checkout is not blocked until the lock's TTL expires. `release-lock.sh` frees the
  lock only while this run still owns it.

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

[0.9.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.9.0
[0.8.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.8.0
[0.7.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.7.0
[0.6.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.6.0
[0.5.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.5.0
[0.4.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.4.0
[0.3.1]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.3.1
[0.3.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.3.0
[0.2.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.2.0
[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.1.0
