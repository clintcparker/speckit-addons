# Changelog

All notable changes to the `send-it-checked` workflow are documented here.

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

[0.3.1]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.3.1
[0.3.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.3.0
[0.2.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.2.0
[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-checked-v0.1.0
