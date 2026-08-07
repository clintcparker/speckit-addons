# Changelog

All notable changes to the `yolo` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.1]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.2.1
[0.2.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.2.0
[0.1.1]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.1.1
[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.1.0
