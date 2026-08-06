# Changelog

All notable changes to the `send-it-checked` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.2.0 (2026-08-05)

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

[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.1.0
