# Changelog

All notable changes to the `send-it` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.3.1]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.3.1
[0.3.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.3.0
[0.2.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.2.0
[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.1.0
