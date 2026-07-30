# Send It — spec to PR, unattended

One command takes a described change from nothing to an open pull request:
spec, plan, tasks, implementation in its own git worktree, then release
engineering — commit, sync, changelog, push, PR — with every confirmation
pre-answered.

```bash
specify workflow run send-it -i spec="add dark mode"
```

The pull request is the only human gate.

## What it installs

| Kind | ID | Version | Source |
|---|---|---|---|
| extension | `worktrees` | 1.3.2 | [dango85/spec-kit-worktree-parallel](https://github.com/dango85/spec-kit-worktree-parallel) |
| extension | `ship` | 1.0.0 | [arunt14/spec-kit-ship](https://github.com/arunt14/spec-kit-ship) |
| extension | `staff-review` | 1.0.0 | [arunt14/spec-kit-staff-review](https://github.com/arunt14/spec-kit-staff-review) |
| extension | `qa` | 1.0.0 | [arunt14/spec-kit-qa](https://github.com/arunt14/spec-kit-qa) |
| workflow | `send-it` | 0.1.0 | this repo |
| workflow | `send-it-checked` | 0.1.0 | this repo |

## Install

Spec Kit keeps a **separate catalog stack per add-on type**, and registering one
does not cover the others. This bundle needs all three registered before it can
resolve: the bundle itself, its two workflows, and its four extensions.

```bash
# 1. bundles
specify bundle catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/bundles/catalog.json \
  --id speckit-addons --policy install-allowed --priority 5

# 2. workflows
specify workflow catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/workflows/catalog.json \
  --name speckit-addons

# 3. extensions -- note --install-allowed; it is NOT the default
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5

specify bundle install send-it
```

**The workflow and extension registrations replace their built-in catalog
stacks** — Spec Kit reads the project config file *instead of* its built-in
`default` + `community` sources for those two types. (The bundle stack is the
exception: it merges.) If you want the official catalogs back, add them
explicitly; see [extensions/README.md](../../extensions/README.md#install).
`specify workflow catalog list` and `specify extension catalog list` show what
is actually active.

## Post-install: one edit

`ship`, `staff-review`, and `qa` each register an `after_implement` hook when
they install. This bundle drives all three from workflow steps instead, so the
hooks would double up — and the worktree isolation depends on `worktrees`'
hook staying on, so disabling hooks wholesale is not an option either.

Open `.specify/extensions.yml` and set `enabled: false` on exactly three
entries under `hooks.after_implement`:

```yaml
hooks:
  after_implement:
    - extension: ship
      command: speckit.ship.run
      enabled: false          # ← was true
      optional: true
      priority: 10
      prompt: Ship this feature?
      description: Runs pre-flight checks, syncs branches, generates changelog, and creates PR
      condition: null
    - extension: staff-review
      command: speckit.staff-review.run
      enabled: false          # ← was true
      optional: true
      priority: 10
      prompt: Run staff-level code review?
      description: Reviews implementation changes against spec for correctness, security, and quality
      condition: null
    - extension: qa
      command: speckit.qa.run
      enabled: false          # ← was true
      optional: true
      priority: 10
      prompt: Run QA testing?
      description: Validates acceptance criteria through browser-driven or CLI-based testing
      condition: null
  after_specify:
    - extension: worktrees
      command: speckit.worktrees.create
      enabled: true           # ← leave this one alone: it is the isolation
      optional: false
      priority: 10
      prompt: Execute speckit.worktrees.create?
      description: Auto-spawn a worktree after a new feature is specified
      condition: null
```

Change nothing but the three `enabled` values; the other fields are written by
the installer and may differ slightly in your file.

**Do not use `specify extension disable ship`** for this. That command also
unregisters the extension's commands, and the workflow steps need
`speckit.ship.run` to still exist.

**If you also have the Spec Kit Git extension installed**, consider disabling
its `before_specify` → `speckit.git.feature` hook too, so the primary
checkout's HEAD stays put while the worktree does the work. See dango85's
README, "Parallel agents and the Git extension".

This edit is manual on purpose. Bundles cannot toggle hooks at install time,
and a shell-step "fixer" workflow would be more machinery than this needs.

## What a run looks like

1. `specify workflow run send-it -i spec="add dark mode"` from the primary
   checkout.
2. `specify` writes the spec. The `worktrees` `after_specify` hook then creates
   `.worktrees/NNN-add-dark-mode/` on the feature branch. The primary checkout's
   HEAD never moves.
3. `plan`, `tasks`, and `implement` run in the worktree.
4. `ship` commits everything, runs pre-flight, rebases onto
   `origin/<target_branch>`, pushes, opens the PR with `gh`, and archives the
   release artifacts under `FEATURE_DIR/releases/`.
5. You review the PR.

Use `send-it-checked` instead to insert a staff review and a QA pass — each with
one fix-and-re-run attempt — between steps 3 and 4. Surviving findings go into
the PR description rather than stopping the run.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `spec` | yes | — | What you want built. |
| `integration` | no | `auto` | Agent integration to dispatch to. |
| `target_branch` | no | `main` | Branch the pull request targets. |

## Caveats

- **Isolation is partial by design.** `specify` runs on the primary checkout, so
  the spec files land there before the worktree exists. From `plan` onward the
  work happens in the worktree.
- **The unattended behaviour is prompt-level.** `ship` is safe by default and is
  steered by the text in the workflow step's `args`, not by a flag. If an agent
  declines to honour it, the run stalls — it does not push something unasked.
- **Third-party code, full privileges.** All four extensions are community code
  that neither the Spec Kit maintainers nor this repo audit. Versions were read
  before they were pinned.
- **Bumped pins need `update`, not `install`.** The bundler's idempotency check
  is id-based: a component already present is skipped by `specify bundle
  install` without comparing versions. Use `specify bundle update send-it`.
- **It opens pull requests.** Point `target_branch` somewhere you are happy to
  see one.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
