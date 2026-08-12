# Changelog

All notable changes to the `send-it-checked` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.1] — 2026-08-12

### Fixed
- **Plain `git`, `gh`, and test commands now target the worktree, not the primary checkout.**
  The ARTIFACT COMMIT blocks in 0.7.0 already used `git -C <worktree_path>` for the commit
  itself, but other operations in each step (code fixes in `review`, app builds in
  `screenshots-before`/`screenshots-after`, pushes in `ship`) defaulted to the working
  directory — the primary checkout when `session=primary`. This produced the 2026-08-12
  `send-it-checked` post-mortem failures: `screenshots-before` committed to `main`, `review`
  left fixes as uncommitted state on `main`, and `ship` had to cut a branch at `main`'s tip
  to avoid a `main→main` PR. Each non-worktree step now carries a WORKTREE INVARIANT block
  that makes the requirement explicit for every operation: use `git -C <worktree_path>` for
  all git commands and write files to absolute paths under `<worktree_path>/`. Finding
  yourself about to operate on the primary checkout is a failed step, not a workaround.

## [0.7.0] — 2026-08-12

### Fixed
- **Unattended runs no longer lose artifacts when a step fails or the run dies mid-pipeline.**
  Every artifact-producing step (`specify`, `plan`, `tasks`, `screenshots-before`,
  `implement`, `review`, `qa`, `screenshots-after`) committed nothing: the optional git
  auto-commit hook is `optional: true` and asks "Commit specification changes?" — a prompt
  an unattended run cannot answer. A full passing implementation could survive as
  uncommitted working-tree state in a disposable worktree, one `git worktree prune` away
  from being gone, which is exactly what caused a prior run's near-duplication of work.
  Each step now carries an ARTIFACT COMMIT block in its `args`: after completing its primary
  work, run `git -C <worktree_path> add .` and `git -C <worktree_path> commit` with a
  Conventional Commit message, skipping silently if there is nothing to commit. This is the
  unattended equivalent of answering YES to the optional git auto-commit hook. The `ship`
  step already did this; now every earlier step does too.

## [0.6.0] — 2026-08-12

### Fixed
- **A resumed run no longer regenerates artifacts it already produced.** Before this fix,
  `specify`, `plan`, `tasks`, and `implement` re-ran their full command even when the
  feature directory already contained a completed artifact from a prior run, wasting time and
  risking overwriting manually edited work. Each step now checks for prior work first: if the
  artifact exists, adopt it without re-running the command. Only generate from scratch when
  the artifact is missing or empty.

## [0.5.0] — 2026-08-12

### Fixed
- **Unattended steps no longer pause for input.** Only the `ship` step's args carried an
  UNATTENDED RUN declaration; each upstream step could still prompt for confirmation or ask
  the user to choose between alternatives. Every step now carries an explicit UNATTENDED RUN
  block: make every judgment call without asking, record the reasoning in the artifact, and
  flag any open decision for the `ship` step to surface in the PR description.

## [0.4.0] — 2026-08-12

### Fixed
- **Feature identity is pinned for the whole run instead of re-derived by every step.** The
  worktree step emitted carry-forward fields and the prose said "carry forward" — but nothing
  carried them. The engine has no step-output templating: `specify`/`plan`/`tasks`/`implement`
  received only `{{ inputs.spec }}` and `review`/`qa`/`screenshots`/`ship` only their mode
  text, so each one independently answered "which feature is this?" from the current branch
  and `.specify/feature.json`. An unattended run's session is usually standing in the
  *primary* checkout, where right after a merge both name the previously shipped feature.
  Two concurrent runs implemented their features correctly and then reviewed, QA'd,
  screenshotted and shipped the last feature that merged; the only pull request either
  produced was for a fix neither had been asked to make.
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
- **`review` and `qa` no longer pass by examining the wrong feature.** A review or QA run
  against an already-merged feature comes back clean and says nothing about the one this run
  built, which is the most expensive kind of false confidence this workflow can produce.
- **`ship` stops rather than guesses.** A missing or disagreeing run context means no commit,
  no push, and no pull request.

### Added
- `ship` surfaces `run_context=collision` near the top of the pull request description: a
  second unattended run owned the run-context pointer in the primary checkout, so both runs'
  later steps were one unexported environment variable away from building the wrong feature.
  Concurrent unattended runs against one primary checkout remain unsupported — this makes the
  condition loud rather than silent.

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
  worktree afterwards. This workflow never carried even the prose comment that `send-it`
  had; the fork dropped it.
- The QA step must read `screenshots/manifest.json` before declaring a scenario
  unrunnable for want of GUI automation. It previously filed window-dependent scenarios
  as 🔵 Skipped with a "no GUI automation available" rationale while a sibling step was
  driving that same window — the `screenshots-before` pass runs at step 5 and had already
  recorded `capture_blocked: false`.
- The ship step now surfaces a non-clean isolation outcome in the pull request
  description: `worktree_isolation=failed` near the top with the branch named, and
  `worktree_isolation=recovered` as a note that the primary checkout was moved to the
  base ref.

### Notes
- The step order is deliberately **unchanged**. Moving `screenshots-after` ahead of
  `review`/`qa` would have fixed the QA blind spot too, but review and QA each get one
  fix-and-re-run pass, so capturing before them would document a state the pull request
  never contains. The manifest is the cheaper evidence and it already existed.

### Requires
- The [`worktrees`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/worktrees)
  extension, at **2.1.0 or later** for the idempotent case detection the step relies on.
  The first step fails at dispatch without the extension. As with `screenshots`, Spec
  Kit's workflow schema cannot express this, so it is a documentation-only contract.

## [0.2.0] — 2026-08-05

### Added
- `screenshots-before` step between `tasks` and `implement`, and
  `screenshots-after` step between `qa` and `ship`. Both dispatch
  `speckit.screenshots.capture` from the `screenshots` extension, which
  self-skips when the feature has no UI surface.
- A SCREENSHOTS SECTION brief in the ship step, with repository-visibility
  detection so image embeds render in private and public repositories alike.

### Notes
- `screenshots-after` deliberately runs **after `qa`**, not right after
  `implement`. Review and QA each get one fix-and-re-run pass; capturing before
  those passes would document a state the pull request never contains.

### Requires
- The [`screenshots`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/screenshots)
  extension. Both capture steps fail at dispatch without it. Spec Kit's workflow
  schema has no machine-readable extension requirement, so this is a
  documentation-only contract.

## [0.1.0] — 2026-07-30

First published release. `send-it` 0.1.0 with two steps inserted before `ship`.

### Added

- Seven `command` steps: `specify` → `plan` → `tasks` → `implement` →
  `review` → `qa` → `ship`.
- `review` step (`speckit.staff-review.run` from the
  [`staff-review`](https://github.com/arunt14/spec-kit-staff-review) extension)
  with one fix-and-re-run pass on a CHANGES REQUIRED verdict.
- `qa` step (`speckit.qa.run` from the
  [`qa`](https://github.com/arunt14/spec-kit-qa) extension) with one
  fix-and-re-run pass on a FAILURES FOUND verdict, preferring CLI QA mode.
- `ship` step `args` instructing it to proceed past surviving review/QA
  findings and summarize them under "Known issues" in the pull request.

[0.7.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.7.0
[0.6.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.6.0
[0.5.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.5.0
[0.4.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.4.0
[0.3.1]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.3.1
[0.3.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.3.0
[0.2.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.2.0
[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.1.0
