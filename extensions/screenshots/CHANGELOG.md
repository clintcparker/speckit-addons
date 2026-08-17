# Changelog

## 0.4.0 (2026-08-17)

### Fixed
- **Seeding no longer has licence to touch a live external service.** Step 4 said
  where app state may live and that real user data must survive a failed run; it
  said nothing about where the state comes *from*. An observed run, seeding the
  `after` pass for an app whose only ingestion path is a hosted mail API, sent
  seven authenticated requests to that live API carrying a placeholder token. All
  seven were rejected before a mailbox was read, and the rule this adds does not
  depend on that: a rejected request is still an unattended run reaching for
  somebody's real account. Seeding now comes from fixtures, from a local stub, or
  from a direct write to the app's own store — and state that cannot be reached
  that way is left out and recorded, not fetched.
- **A capture no longer silently lands in the wrong checkout.** Step 7 said which
  method to use and what to call the file, and assumed the file would appear
  where it was asked for. A capture tool driven over a protocol rather than as a
  child process — the Playwright MCP server, a remote debugger — resolves a
  relative path against the invoking session's working directory, which in an
  unattended run is the primary checkout, not the run's worktree. One observed
  run had its PNGs and a `.playwright-mcp/` scratch directory land at the root of
  the primary and had to move them by hand. The step now asks for an absolute
  path under `FEATURE_DIR/screenshots/`, and where the tool will not take one,
  verifies the destination after the *first* capture rather than the last.

### Changed
- Step 4 requires state placed by hand into the data store to be labelled as such
  in the manifest's `notes`, along with what the resulting frame does and does not
  evidence. A hand-inserted row proves the UI renders it; a reviewer looking at the
  image has no way to tell that from an end-to-end result.
- Step 7 addresses the illegible frame: an empty-bodied error page or an
  unpainted window captures as a plausible solid-colour PNG indistinguishable
  from a failed capture. Capture a working control in the same pass so the frame
  means something, and record what the control establishes. Changing capture
  method to render a state legibly stays within the command's remit as long as
  both halves of a before/after pair are produced the same way.

## 0.3.0 (2026-08-13)

### Fixed
- **A feature without a `plan.md` no longer blocks the whole capture.** Step 1
  called `check-prerequisites.sh --json`, which validates before it reports and
  gates on `plan.md`: any feature that bypassed `/speckit-specify` or
  `/speckit-plan` — a hand-started branch, a run that adopted an existing spec —
  made the script exit 1 with `ERROR: plan.md not found`, and step 1 had no
  fallback. It now uses `--paths-only`, which performs the same resolution with
  no validation and, unlike the plain form, without persisting the override into
  `.specify/feature.json` on the way past. A screenshot pass needs a feature
  *directory*, never a plan.
- **The command no longer takes a helper script's word for which feature this
  is.** `FEATURE_DIR` is resolved from `$SPECIFY_FEATURE_DIRECTORY` first, then
  `.specify/run-context.json`, and only then from the script — and when a pinned
  value exists, the script's answer is compared against it. Unpinned, the script
  answers from `.specify/feature.json`, which in a primary checkout right after a
  merge names the feature that just shipped, and it exits 0 on it. A disagreement
  now stops the command naming both paths, instead of quietly capturing the wrong
  tree. A script exiting 0 is not evidence it found the right feature.

### Changed
- Step 3 treats a feature with neither `spec.md` nor `plan.md` as a normal input
  rather than an error. With nothing to read it judges UI-relevance from
  `$ARGUMENTS`, the branch name and the profile's `ui_surface`, and when that is
  not enough it captures the baseline anyway — an unnecessary baseline costs two
  PNGs, a missing one cannot be recreated once the implementation has landed.
  Either way the manifest records `"spec": "unavailable"` in `notes`.
- Two new constraints make both halves explicit: a spec-less feature is a
  supported input, and a feature the run context does not name is never adopted.

## 0.2.0 (2026-08-13)

### Fixed
- **The command now resolves an ignored screenshots directory instead of leaving
  every later step to work around it.** Repos routinely ignore `screenshots/` or
  `specs/*/screenshots/` for unrelated reasons, and the images still have to
  reach the pushed head because `speckit.ship.run` links them from the pull
  request body — a link to an ignored path 404s for every reviewer. The
  workaround each step reached for independently, `git add -f`, stages one commit
  and leaves the next step facing the same conflict. New step 2 checks
  `git check-ignore` against `FEATURE_DIR/screenshots/` before anything is
  written and, when a rule matches, appends `!screenshots/` to
  `FEATURE_DIR/.gitignore` and commits it. A `.gitignore` inside the feature
  directory outranks the repo root's, so plain `git add` works for the before
  pass, the after pass and ship. The repo's own ignore rule is untouched.
- The commit instruction in the final step now names `FEATURE_DIR/.gitignore`
  alongside `FEATURE_DIR/screenshots/`, and forbids `git add -f` outright — a
  force-add hides that step 2 did not run.

## 0.1.0 (2026-08-05)

### Added
- `speckit.screenshots.capture` command — before/after UI screenshots for the
  current feature, committed to the branch for embedding in the pull request.
- Generic command + per-repo app profile split: `commands/capture.md` is never
  edited per repo; `screenshots-config.yml` holds everything app-specific and
  survives `specify extension add --force`.
- Bootstrap mode — a profile marked `unconfigured: true` is derived by the agent
  on first run, so a fresh install is runnable with no manual steps.
- Example profiles for ASP.NET + Playwright and Tauri + AppleScript.
- Generalized manifest schema: `targets`, `viewports`, `baseline`, `notes`, and
  a free-form `app` object for profile-specific state.

### Notes
- Extracted from the hand-written `capture.md` variants in `homeapp1` and
  `site-checker`, which shared the entire command skeleton and differed only in
  app mechanics.
