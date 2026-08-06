# Changelog

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
