# Changelog

All notable changes to the `send-it` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.2.0
[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.1.0
