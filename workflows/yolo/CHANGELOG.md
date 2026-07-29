# Changelog

All notable changes to the `yolo` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/yolo-v0.1.0
