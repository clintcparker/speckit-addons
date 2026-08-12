# Changelog

## 2.3.0 (2026-08-12)

### Added
- **`## Outline` step 4 pins the run's feature identity to a file.** Everything this command decides —
  branch, worktree, feature directory — was previously known only to the step that ran it. A workflow
  engine with no step-output templating hands the next step nothing but its own args, so each one
  re-answered "which feature is this?" from the current branch and `.specify/feature.json`. Straight
  after a merge both name the *previous* feature: two concurrent unattended runs implemented their
  features correctly and then reviewed, QA'd, screenshotted and shipped the last one that merged,
  while every helper script exited 0. The command now writes the answer down.
- **`scripts/bash/write-run-context.sh`**, the deterministic writer. It emits
  `<worktree>/.specify/run-context.json` — `run_id`, `branch`, absolute `feature_dir`,
  `worktree_path`, `primary_path`, `base_ref`, `worktree_isolation`, `session` — and, when the session
  is standing somewhere else, a second copy at `<primary>/.specify/run-context.json` pointing at the
  first. `session=primary` is the normal unattended outcome and a step standing there has no other way
  to find the worktree.
- **`run_context=<path>` is a third machine-readable field** in step 7's fields block, alongside
  `worktree_isolation` and `session`. It is an address rather than a status: it is what a later step
  resolves `FEATURE_DIR` from instead of guessing.
- **Concurrent runs are refused, not silently repointed.** When another run's pointer is already in
  the primary checkout and its worktree *and* branch are both still live, the script exits 3 and
  leaves it alone — displacing it would aim the same drift at that run instead. This run's canonical
  context is still written, and the command reports `run_context=collision` naming both branches. A
  pointer whose worktree or branch is gone is litter, not a collision, and is replaced.
- The context file is never committable: the script appends its path to `$GIT_COMMON_DIR/info/exclude`,
  which is local, untracked, and shared by every worktree of the repo. `ship`'s brief is "commit every
  uncommitted change", so an unignored file would land in the pull request.

### Changed
- `## Outline` steps 4, 5 and 6 renumbered to 5, 6 and 7 to make room. References inside the command
  and in the `send-it`, `send-it-checked` and `yolo` workflows were updated with them.

## 2.2.0 (2026-08-06)

### Added
- **`session` is a second machine-readable field, orthogonal to `worktree_isolation`.** One describes
  the worktree, the other describes where the agent session is standing: `session=worktree` or
  `session=primary`. `worktree_isolation=created` with `session=primary` is an ordinary unattended
  run — the worktree is right and nothing is standing in it — and no single enum could express it.
  2.1.0 reported that state as a bare `created`, which a ship step reads as unqualified success.
- **`## Outline` step 3 covers the case where `EnterWorktree` is refused.** 2.1.0 had a fallback, but
  scoped it to "if no such tool exists (non-Claude integration)". The common case is different and was
  uncovered: the tool *exists* and the call needs interactive approval nobody is present to give,
  which is the normal outcome of every unattended workflow run. All three ways the move can fail — no
  tool, refused, errored — now land in one defined state.
- **The `SPECIFY_INIT_DIR` / `SPECIFY_FEATURE_DIRECTORY` overrides are structured output, not
  advice.** They go in step 6's fields block whenever `session=primary`, because they are the only
  thing keeping the remaining steps out of the primary checkout and prose gets skimmed.
- **`## Outline` step 4 reports what the worktree does not carry** — the two things a fresh checkout
  of `base_ref` silently lacks. A base ref behind its local counterpart (`base_ref=origin/main; local
  main is 1 commit ahead`), and untracked or ignored inputs the description names that cannot exist in
  the worktree (`missing in worktree: docs/ROADMAP.md (ignored by .gitignore:25)`).

### Changed
- **New rule: report hazards, never remedy them.** No `merge`/`rebase`/`cherry-pick`/`reset`/`pull`
  to move the branch off the resolved base ref, and no copying untracked or ignored files into the
  worktree. Closing a base-ref gap by hand drags unpushed commits into the feature branch, where they
  surface in the pull request as if they were part of the feature; `base_ref` in `worktree-config.yml`
  is the supported way to change what a feature forks from, and it is the user's decision. "Never
  prompt" in an unattended run means decide the cases this command defines and report everything
  else — it is not a licence to act unilaterally.
- The report contract is explicit about staying short. Every later step of an unattended run reads
  this output as its context.

## 2.1.0 (2026-08-06)

### Added
- **`speckit.worktrees.create` is idempotent.** A new `## Outline` step 0 resolves which
  of three cases applies *before* deriving anything: already inside a linked worktree
  (no-op), primary checkout with a feature branch that already exists (use the branch
  name), or primary checkout on the base ref (the `before_specify` case, the only one
  that may pass `--from-description`). The hook and an explicit workflow step can now
  both run in the same pass without minting a spurious second feature number.

  This is what lets a workflow declare worktree isolation as a **step** instead of
  depending on the `before_specify` hook firing. A run that entered past
  `speckit.specify` — a resume, or a fix-up over an already-specified feature — never
  triggered the hook and executed entirely in the primary checkout.
- **A recovery path for the unrecoverable case.** When the feature branch is already
  checked out in the primary, no worktree can attach to it. Step 0 now recovers when the
  primary is *provably* clean — `git status --porcelain` and `git stash list` both empty
  — by moving the primary to the base ref and attaching the worktree, and reports
  `worktree_isolation=recovered` naming the base ref the primary now sits on. A dirty
  tree or any stash entry falls back to `worktree_isolation=failed`: run in place, report
  loudly, never force and never move the user's work.
- **A machine-readable isolation outcome** in the report — `created`, `already`,
  `entered`, `recovered`, or `failed` — so a workflow's ship step can put a non-clean
  outcome in the pull request description rather than let it die in a transcript.

### Changed
- The **never modify the primary checkout** rule now carries its one narrow exception
  (the recovery path above) instead of contradicting it.
- A non-zero script exit naming the primary repo is no longer "report it and stop"; it
  routes to step 0's failure path.

## 2.0.0 (2026-08-05)

Fork of [dango85/spec-kit-worktree-parallel](https://github.com/dango85/spec-kit-worktree-parallel)
**v1.0.0**, now published from
[clintcparker/speckit-addons](https://github.com/clintcparker/speckit-addons).

Upstream **1.3.2 is not merged**. It was read and rejected for this baseline: it
carries only partial `base_ref` support in the script, none of the other patches
below, plus tests and a post-install step that have never run here. Rebasing
these patches onto 1.3.2 remains possible later. The version is 2.0.0 purely so
catalog update logic moves forward from 1.3.2 — it does not imply 1.3.2 is
contained.

### Changed
- **The `speckit.worktrees.create` hook is declared at `before_specify`
  (priority 20)** instead of upstream's `after_specify`. A stock install now
  wires the worktree-first flow correctly, and `--force` reinstalls no longer
  revert a hand edit.

### Added (carried from local patches, not in upstream 1.0.0)
- `--from-description` — derive the branch name from the feature description by
  delegating to the git extension's `create-new-feature-branch.sh --dry-run`,
  so the `before_specify` hook can create the branch before a spec exists.
- `enter_worktree` config key — move the agent session into the new worktree so
  the spec and every later phase is written there rather than in the primary
  checkout.
- `base_ref` config key — the ref new feature branches fork from, auto-detected
  as `origin/main` → `main` → `origin/master` → `master` → `HEAD` when empty.
  Under the worktree-first flow the branch is created by `git worktree add -b`,
  so this — not the primary's HEAD — decides what a feature forks from.
- Worktree-first flow throughout the `speckit.worktrees.create` command.

## 1.0.0 (2026-04-13)

### Added
- `speckit.worktrees.create` command — spawn isolated worktrees with configurable layout
- `speckit.worktrees.list` command — dashboard of all active worktrees with spec-artifact and task progress
- `speckit.worktrees.clean` command — safe cleanup of merged, orphaned, or stale worktrees
- `after_specify` hook — auto-creates worktree after feature specification (configurable)
- Two layout modes: **sibling** (`../<repo>--<branch>`) and **nested** (`.worktrees/<branch>/`)
- Bash script `create-worktree.sh` for deterministic worktree creation with JSON output
- Per-repo configuration via `worktree-config.yml`
- `SPECIFY_WORKTREE_PATH` environment variable for path overrides
- `--in-place` / `--no-worktree` opt-out for single-agent flows
