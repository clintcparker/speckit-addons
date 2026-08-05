# Design: speckit-addons as the source of truth

**Date:** 2026-08-05
**Status:** Approved decisions from Q&A; spec pending user review
**Goal:** Everything the send-it harness needs installs from this repo's
catalogs. `homeapp1/.specify/` stops being the only copy of anything.

## Context

The working send-it harness (worktree → spec → screenshots → implement →
screenshots → PR) exists only as hand-patched files in
`homeapp1/.specify/`, copied once into `site-checker/.specify/`. This repo's
catalogs serve older versions (send-it v0.1.0) or none at all (screenshots,
the worktrees fork, the git patch). The full gap analysis is in the session
handoff; the porting gotchas are captured in the wiki
(`_raw/2026-08-05-speckit-harness-porting-gotchas.md`).

## Decisions already made (user-approved 2026-08-05)

1. **Screenshots extension**: generic core + per-repo app profile (not
   adapt-in-place, not reference flavors).
2. **Worktrees and git patches**: fork both into this repo. `extensions/`
   starts hosting first-party code alongside its pinned third-party pointers.
3. **Workflows**: send-it → 0.2.0 *and* send-it-checked → 0.2.0 with the same
   screenshot steps.
4. **Release flow**: all work lands on the `source-of-truth` branch, PR
   reviewed by Clint; tags are cut only after merge.

## Component 1 — screenshots extension (new, v0.1.0)

The two existing `capture.md` variants (homeapp1: ASP.NET + Playwright;
site-checker: Tauri + AppleScript/`screencapture`) share the entire command
skeleton and differ only in app mechanics. The published extension splits
along exactly that seam.

### Layout

```
extensions/screenshots/
  extension.yml            # provides the command and the config template
  commands/capture.md      # fully generic; never edited per-repo
  app-profile.md           # template, ships with an UNCONFIGURED marker
  examples/
    aspnet-playwright.md   # homeapp1's mechanics, distilled to profile form
    tauri-applescript.md   # site-checker's mechanics, distilled to profile form
  README.md
  CHANGELOG.md
```

### The seam

`commands/capture.md` keeps everything both variants share: the
before/after mode contract, UI-relevance decision structure, the
`SKIPPED.md` self-skip, manifest, filename conventions, commit rules, the
"never modify app code" / "after-mode failure is an implementation defect"
constraints, and the data-protection rules (state outside the checkout; real
user data must survive every run, including failed ones).

`app-profile.md` holds everything that varied between the two repos, as
sections the agent reads before step 3:

- **UI surface** — which paths count as UI-relevant (feeds the `git diff`
  check in after-mode SKIPPED verification).
- **Launch** — command, readiness probe, timeout, first-run setup.
- **Auth** — how to sign in, or "none".
- **Data** — where app state lives, how to seed it, how to protect the real
  data (backup/restore or temp-dir), how after-mode replays the baseline.
- **Targets & viewports** — what a "page/view" is here, which sizes to
  capture and why.
- **Capture method** — Playwright viewport shots, `screencapture -R` of a
  window rect, etc.
- **Cleanup** — how to stop the app (process tree caveats), what to restore.

### Why a config file and not an editable command

`extension.yml` declares the profile via `provides.config` (the worktrees
extension's `worktree-config.yml` proves the mechanism). Spec-kit preserves
existing config files on `--force` reinstall, so upgrading the extension
never clobbers a repo's adaptation — the exact failure mode that bit the
hand-edited files. It also dissolves the stale-skill trap: `.claude/skills`
embeds a copy of the *command* body, and the command never changes per-repo.

### Bootstrap behavior

If `app-profile.md` still contains the `<!-- UNCONFIGURED -->` marker when
`capture.md` runs, the agent derives the profile itself — inspect README,
build manifests, entry points, existing e2e config — writes it (removing the
marker), notes in the manifest that the profile was auto-generated, and
continues. A repo-agnostic install is therefore runnable with zero manual
steps; the profile is reviewable after the fact.

### Manifest schema (generalized)

Core keys: `targets` (slug, why), `viewports` (label → WxH), `baseline`
("available" | "unavailable"), `notes`. Profile-specific state (data dir,
backup flag, seed steps/sites) goes under a free-form `app` object. The
examples show both existing manifests mapped onto this shape.

### Hooks

None, deliberately — same reasoning as today: workflows that want
screenshots add the steps explicitly; a hook would tax every flow.

## Component 2 — worktrees fork (v2.0.0)

- Hosted at `extensions/worktrees/`; catalog entry repointed from
  dango85/spec-kit-worktree-parallel to this repo. Id stays `worktrees` so
  existing hook wiring and docs keep working.
- **Baseline = the battle-tested homeapp1 copy** (upstream v1.0.0 + local
  patches: `--from-description`, `enter_worktree`, `base_ref`, worktree-first
  flow). Upstream 1.3.2 was checked: it has only partial `base_ref` in the
  script, none of the rest, plus unrelated additions (tests, post-install)
  that have never run here. Rebasing the patches onto 1.3.2 is possible
  later; it is not this change.
- **Version 2.0.0**: semver-above 1.3.2 so catalog update logic moves
  forward, while not implying it *contains* 1.3.2. CHANGELOG states the
  lineage explicitly (fork of dango85 v1.0.0 + patches; 1.3.2 not merged).
- **Hook declaration fix baked in**: the fork's `extension.yml` declares its
  `speckit.worktrees.create` hook at `before_specify` (priority 20) instead
  of upstream's `after_specify`. A stock install then wires the
  worktree-first flow correctly, and `--force` reinstalls stop reverting the
  hand edit — the single biggest recurring gotcha from the porting session.

## Component 3 — git fork (v1.1.0)

- Hosted at `extensions/git/`; id stays `git`. Baseline = spec-kit-core's
  bundled v1.0.0 plus the ~8-line patch to
  `create-new-feature-branch.{sh,ps1,py}` honoring
  `branch_numbering: timestamp` from `git-config.yml` when the worktrees
  hook calls without flags.
- The `speckit.git.feature` `before_specify` hook is **not declared** by the
  fork (worktrees creates the branch; the stock hook had to be hand-disabled
  after every reinstall). All other hooks (auto-commit, initialize) keep
  upstream behavior.
- Shipped `git-config.yml` template defaults `branch_numbering: timestamp` —
  parallel worktrees computing "next sequential number" independently would
  collide, which is the whole reason the patch exists.
- Catalog priority must let this fork shadow the spec-kit `default` catalog's
  `git` entry when both stacks are registered; verify resolution order during
  implementation.

## Packaging & release mechanics (first-party extensions)

- **Distribution**: per-extension zips attached to GitHub Releases (the
  bundle pattern from `workflows/README.md`), *not* whole-repo tag archives —
  a whole-repo archive would put the extension three directories deep, and
  release assets are byte-stable where tag archives are not (fixes the
  documented archive-recompression risk for these entries). Zip layout:
  a single wrapping top-level dir containing `extension.yml`, matching the
  shape of the tag archives the installer already accepts.
- **Tags**: `ext-<id>-v<version>` (mirrors the `bundle-` prefix convention).
- **Catalog entries**: `download_url` → the release asset; `sha256` of the
  uploaded zip; `repository`/`documentation`/`changelog` → this repo at the
  tag.
- **Validator**: extend `scripts/validate_catalog.py` to check hosted
  extension entries against `extensions/<id>/extension.yml` on disk (version
  agreement, declared config templates exist, sha256 shape) — the same
  disk-vs-catalog guarantee it gives workflows.
- **Smoke test** (post-tag): fresh `specify init` project, register this
  catalog, `specify extension add screenshots worktrees git`, confirm hook
  wiring lands correctly with no hand edits, then run a trivial capture in
  bootstrap mode.

## Component 4 — send-it 0.2.0 and send-it-checked 0.2.0

- **send-it 0.2.0**: publish homeapp1's workflow.yml with one
  generalization: the ship step's screenshots section currently asserts
  "this repository is PRIVATE"; change to *detect* visibility
  (`gh repo view --json visibility`) and use `blob/{head_sha}?raw=true`
  embedding only when private (public repos can use raw URLs). Keep the
  heavily-commented worktree-session-model notes — they are documentation.
- **send-it-checked 0.2.0**: same two steps grafted in: `screenshots-before`
  between `tasks` and `implement`; `screenshots-after` after `qa` (not right
  after `implement`) so the capture reflects the state after review/QA
  fix-and-rerun passes — it must match what ships.
- Both workflows' READMEs and catalog entries document the dependency on the
  `screenshots` extension (steps fail at dispatch without it). If the
  workflow schema supports a machine-readable extension requirement, use it;
  otherwise README + description. Verify during implementation.
- Standard release procedure per `workflows/README.md`: CHANGELOG, catalog
  bump, tags `send-it-v0.2.0` and `send-it-checked-v0.2.0` after merge.

## Component 5 — the scaffolding write-up + doc updates

- **`docs/send-it-harness.md`** — the handoff's deliverable #1: what the
  harness is; the four separate catalog stacks; how the pieces compose
  (init → catalogs → extensions → hook wiring → workflow run → worktree
  session model → screenshots → ship); reproducing it in a new repo (now
  mostly `catalog add` + `extension add` thanks to the forks); remaining
  manual steps (`feature_numbering` in `.specify/init-options.json` — core
  spec-kit, not extension-owned; skill regeneration after editing any
  command file); gotchas appendix distilled from the wiki capture (0.15.x
  discovery-only gating, catalog-add replaces the stack, `--force` revert
  behavior and which parts the forks now fix, the raw.githubusercontent
  negative-cache trap).
- **Root README**: extensions table gains the three first-party entries and
  distinguishes "hosted here" from "pinned pointer"; **remove the stale
  Bundles section** (bundles/ was deleted in `1dcd69b`/`2996929` but the
  README still documents it, including install commands that 404); link the
  write-up.
- **extensions/README.md**: restructure into first-party (hosted) vs
  third-party (pinned pointers) sections; the "pointers, not code" framing
  and trust notes now apply only to the latter.

## Out of scope

- Resurrecting the send-it bundle (deliberately deleted; revisit only if
  wanted later — the write-up's install sequence covers composition).
- Upstream PRs to dango85 / github/spec-kit (possible follow-up; MIT both
  ways).
- Committing site-checker's untracked `.specify/` or switching
  homeapp1/site-checker to install from the published catalog (follow-up
  once tags exist).

## Risks & error handling

- **Installer zip-layout assumption**: the wrapping-dir shape is inferred
  from how tag-archive installs behave, not documented contract; the smoke
  test gates the release and the layout gets adjusted to whatever it proves
  out.
- **`git` id shadowing**: if catalog priority cannot shadow the bundled
  `default` entry, fallback is documented `--from`-style install or a
  post-install note; decide from the smoke test.
- **send-it 0.2.0 without screenshots installed** fails at dispatch; the
  dependency is documented everywhere the workflow is, and the bundle-less
  install sequence in the write-up installs the extension first.
