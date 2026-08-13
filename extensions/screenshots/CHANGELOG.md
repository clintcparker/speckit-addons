# Changelog

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
