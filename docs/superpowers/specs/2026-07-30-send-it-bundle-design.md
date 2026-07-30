# `send-it` — spec-to-PR bundle for Spec Kit

**Date:** 2026-07-30
**Status:** Approved design, pre-implementation
**Repo:** clintcparker/speckit-addons

## Goal

One command — `specify workflow run send-it -i spec="..."` — takes a described
change all the way from nothing to an open GitHub pull request, unattended:
spec, plan, tasks, implementation in a git worktree, then release engineering
(commit everything, sync, changelog, push, PR) with every confirmation
auto-accepted. The PR itself is the only human review gate.

This is a personal daily driver. It is published through this repo's catalog
machinery because that is where these add-ons live, but the design optimizes
for the owner's use, not for strangers.

## Verified decisions

Each of these was confirmed explicitly during design review.

| # | Decision | Choice |
|---|---|---|
| 1 | Audience | Personal daily driver; publishing is incidental |
| 2 | Worktree "enforcement" | dango85 extension's default-on `after_specify` hook, as-is. Spec files landing on the primary tree first is accepted. No custom worktree-first glue |
| 3 | Autonomy | Fully unattended through PR creation: commit, rebase, push, open PR with zero prompts. The PR is the review gate |
| 4 | Review/QA | Two workflows: `send-it` (lean, no review/QA) and `send-it-checked` (adds staff-review + QA before ship) |
| 5 | Third-party distribution | Extension catalog entries pin `download_url` to upstream GitHub tag zips (dango85, arunt14). No mirroring |
| 6 | `after_implement` hooks | Disabled post-install (documented one-time edit to `.specify/extensions.yml`) for ship, staff-review, and qa. Workflow steps are the only trigger. The worktrees `after_specify` hook stays enabled — it is the enforcement |
| 7 | Naming | Bundle `send-it`; workflows `send-it` (lean) and `send-it-checked` |
| 8 | Bundle packaging | One bundle containing all four extensions + both workflows |
| 9 | Unattended remediation | On CHANGES REQUIRED / FAILURES FOUND: fix blockers, re-run the failed check once, then ship regardless, summarizing remaining findings in the PR description |
| 10 | Spec scope | One spec covering everything (chosen over decomposition, trade-off acknowledged) |

## Composition

`specify bundle install send-it` installs, via the bundle manifest's
`provides` lists (each pinned to a version, resolved through the user's
registered catalog stacks):

| Kind | Id | Version | Source of bits |
|---|---|---|---|
| extension | `worktrees` | 1.3.2 | `dango85/spec-kit-worktree-parallel` tag `v1.3.2` zip |
| extension | `ship` | 1.0.0 | `arunt14/spec-kit-ship` tag `v1.0.0` zip |
| extension | `staff-review` | 1.0.0 | `arunt14/spec-kit-staff-review` tag `v1.0.0` zip |
| extension | `qa` | 1.0.0 | `arunt14/spec-kit-qa` tag `v1.0.0` zip |
| workflow | `send-it` | 0.1.0 | this repo, tag `send-it-v0.1.0` |
| workflow | `send-it-checked` | 0.1.0 | this repo, tag `send-it-checked-v0.1.0` |

The existing `yolo` workflow is untouched.

### Mechanism facts this design rests on

Established by reading `specify-cli` 0.14.2 source and the upstream repos —
not from docs:

- The bundler installs components **by id through the registered catalog
  stacks**. `ComponentRef.source` is parsed from `bundle.yml` but never used by
  the installer. Therefore the extensions must be resolvable from a registered
  **extension catalog**, which this repo must now publish.
- Extension catalog entries carry a `download_url` which may be any HTTPS zip —
  including a third-party GitHub tag archive. `ExtensionCatalog.download_extension`
  enforces HTTPS but not host.
- Bundles are packaged by `specify bundle build` into a reproducible
  `<id>-<version>.zip` (manifest + README), distributed via a **bundle catalog**
  whose entries also carry `download_url`. Required entry fields: `id`, `name`,
  `version`, `role`, `description`, `author`, `license`, `download_url`,
  `requires.speckit_version`; payload top-level key is a `bundles` object.
- Ship's `/speckit.ship.run` command reads `$ARGUMENTS` first ("You MUST
  consider the user input before proceeding") — this is the designed lever for
  unattended operation. No fork or overlay of ship is needed, and manual
  `/speckit.ship.run` keeps its safe-by-default prompts.
- Ship's pre-flight review/QA checks are **conditional**: they only run when
  `FEATURE_DIR/reviews/` / `FEATURE_DIR/qa/` exist. The lean workflow therefore
  passes pre-flight honestly without waivers. `staff-review` and `qa` write
  exactly those directories, so the checked workflow's pre-flight is real.
- `/speckit.review` and `/speckit.qa` (name-dropped in ship's README) are not
  core commands; the real commands are `/speckit.staff-review.run` and
  `/speckit.qa.run` from arunt14's sibling extensions.

## Deliverables

### 1. `workflows/send-it/` (workflow.yml, README.md, CHANGELOG.md)

Yolo's four steps plus a ship step. New input `target_branch` (default
`main`). Sketch:

```yaml
schema_version: "1.0"
workflow:
  id: "send-it"
  name: "Spec to PR, unattended"
  version: "0.1.0"
  author: "clintcparker"
  description: "specify → plan → tasks → implement → ship; no gates, ends in an open PR"

requires:
  speckit_version: ">=0.8.12"   # same floor as yolo (integration: auto)
  integrations:
    any: ["claude"]             # advisory hint, as in yolo

inputs:
  spec:          { type: string, required: true, prompt: "Describe what you want to build" }
  integration:   { type: string, default: "auto" }
  target_branch: { type: string, default: "main", prompt: "PR target branch" }

steps:
  # specify / plan / tasks / implement — identical to yolo 0.1.1
  - id: ship
    command: speckit.ship.run
    integration: "{{ inputs.integration }}"
    input:
      args: >-
        Target branch: {{ inputs.target_branch }}. UNATTENDED RUN — no user is
        present. Answer YES to every confirmation this command would normally
        ask (branch sync, rebase, push, PR creation). Before pre-flight, commit
        all uncommitted working-tree changes with a descriptive message instead
        of prompting. Prefer rebase for branch sync. If gh is unavailable or CI
        status cannot be verified, proceed and note it in the PR description.
        If rebase conflicts arise that cannot be resolved trivially, stop and
        leave the branch for manual resolution rather than forcing.
```

The exact `args` prose is an implementation detail to be tuned; the contract
is: auto-yes on every ship confirmation, auto-commit the working tree, PR at
the end, and hard conflicts are the one legitimate stop.

### 2. `workflows/send-it-checked/` (workflow.yml, README.md, CHANGELOG.md)

Same as `send-it` with two steps inserted between `implement` and `ship`:

```yaml
  - id: review
    command: speckit.staff-review.run
    integration: "{{ inputs.integration }}"
    input:
      args: >-
        UNATTENDED RUN. Review the implementation. If the verdict is CHANGES
        REQUIRED, fix all Blocker findings and re-run the review exactly once.
        Do not pause for user input.

  - id: qa
    command: speckit.qa.run
    integration: "{{ inputs.integration }}"
    input:
      args: >-
        UNATTENDED RUN. Prefer CLI QA mode unless browser QA is clearly
        configured. If the verdict is FAILURES FOUND, fix the failures and
        re-run QA exactly once. Do not pause for user input.
```

The ship step's `args` additionally says: if review or QA verdicts still carry
warnings or unresolved findings after the single remediation pass, proceed
anyway and summarize them in the PR description (decision #9).

### 3. `extensions/catalog.json` + `extensions/README.md`

New catalog stack (extension catalogs are independent of workflow catalogs).
Four entries — `worktrees`, `ship`, `staff-review`, `qa` — with
`download_url` pinned to the upstream tag zips listed under Composition.
Field set mirrors upstream `extensions/catalog.json`
(`github/spec-kit` repo); minimum: `id`, `name`, `version`, `description`,
`author`, `license`, `download_url`, `repository`. Implementation must verify
the exact upstream field set at build time rather than trusting this spec.

`extensions/README.md` states plainly: these entries point at third-party
repos; this repo pins tags but does not control them (decision #5's accepted
risk — upstream owners can re-point tags).

### 4. `bundles/send-it/bundle.yml` + `bundles/catalog.json` + `bundles/send-it/README.md`

`bundle.yml` sketch (schema per `specify-cli` bundler `manifest.py`):

```yaml
schema_version: "1.0"
bundle:
  id: "send-it"
  name: "Send It — spec to PR, unattended"
  version: "0.1.0"
  role: "solo-dev"
  description: "yolo-style full SDD cycle in a worktree, shipped to an open PR with zero prompts"
  author: "clintcparker"
  license: "MIT"
requires:
  speckit_version: ">=0.14.2"   # bundler floor: the release whose bundle machinery this design was verified against
  tools: ["git", "gh"]
provides:
  extensions:
    - { id: worktrees,    version: "1.3.2" }
    - { id: ship,         version: "1.0.0" }
    - { id: staff-review, version: "1.0.0" }
    - { id: qa,           version: "1.0.0" }
  workflows:
    - { id: send-it,         version: "0.1.0" }
    - { id: send-it-checked, version: "0.1.0" }
```

No `integration:` pin — the bundle stays integration-agnostic like yolo.

`bundles/catalog.json` gets one entry for `send-it`, `download_url` pointing at
the `send-it-0.1.0.zip` artifact built by `specify bundle build` and attached
to the `send-it-v0.1.0` GitHub Release. Include `sha256` (the schema supports
it; use it since we're distributing an executable-adjacent artifact).

`bundles/send-it/README.md` documents install, run, and post-install (below),
with a step graph per repo convention.

### 5. Post-install: hook policy (documented, one edit)

Ship, staff-review, and qa all self-register `after_implement` hooks. Per
decision #6, after `specify bundle install send-it` the user makes one edit to
`.specify/extensions.yml`, setting `enabled: false` on those three hooks.
The bundle README shows the exact YAML. The worktrees `after_specify` hook is
left enabled.

Also documented as a conditional note (from dango85's README): if the Spec Kit
Git extension is installed, consider disabling its `before_specify` →
`speckit.git.feature` hook so the primary checkout's HEAD stays put.

Rationale for manual-edit over automation: bundles cannot toggle hooks at
install time, and a shell-step "fixer" workflow would be more machinery than a
daily driver needs.

### 6. Validation + repo docs

- Extend `scripts/validate_catalog.py` to the two new catalogs: structural
  checks for `extensions/catalog.json` and `bundles/catalog.json`, URL checks
  under `--check-urls` (third-party URLs included — a vanished upstream tag
  should show up red on the scheduled run, since that is precisely the
  accepted risk of decision #5).
- Root `README.md`: add the new add-ons to the table, add the two extra
  `catalog add` registration commands (extension + bundle stacks are separate
  from the workflow stack; my distribution-model notes confirm registering one
  does not cover the others).
- `workflows/README.md` release procedure: extend to cover bundle builds
  (`specify bundle validate`, then `specify bundle build`, GitHub Release with
  the zip asset, sha256). Per the upstream bundle docs' publish guidance, the
  procedure ends with an install test from a clean project with the extension
  and bundle catalogs registered.

## What a run looks like (narrative, lean variant)

1. `specify workflow run send-it -i spec="add dark mode"` from the primary
   checkout.
2. `specify` writes the spec; the worktrees extension's `after_specify` hook
   creates `.worktrees/NNN-add-dark-mode/` with the feature branch; primary
   HEAD never moves. (Spec files touch the primary tree first — accepted.)
3. `plan`, `tasks`, `implement` proceed in the worktree.
4. `ship` step: commits everything, pre-flight (tasks complete, tree now
   clean; review/QA checks skipped — no reports exist), rebases on
   `origin/main`, pushes, opens the PR via `gh`, archives release artifacts in
   `FEATURE_DIR/releases/`.
5. You review the PR. That is the gate.

The checked variant inserts staff-review and QA (each with one fix-and-re-run
pass) between 3 and 4, and the PR description carries any surviving findings.

## Risks and accepted trade-offs

- **Upstream tags are not immutable.** dango85/arunt14 can re-point or delete
  tags. Accepted (decision #5); mitigated by scheduled `--check-urls` CI and
  `sha256` on the bundle artifact (not available for extension entries unless
  upstream format supports it — verify during implementation).
- **`args`-driven autonomy is prompt-level, not mechanical.** Ship's
  auto-accept relies on the agent honoring `$ARGUMENTS` over the command's
  safe-by-default prompts. If an agent refuses, the failure mode is a stalled
  run, not an unwanted push — the safe direction.
- **Isolation is partial by choice.** Specify runs on the primary tree;
  the worktree exists from plan onward, and step cwd discipline is
  agent-dependent (decision #2).
- **Third-party code runs with full privileges.** All four extensions are
  unreviewed-by-maintainers community code (as this repo's own security
  section says of itself). Pinned versions were read before pinning; bumps
  require re-reading.
- **Pin enforcement is install-time only.** The bundler's idempotency checks
  are id-based, not version-aware: a component already present is skipped on
  `install` without comparing versions. Bumped pins take effect via
  `specify bundle update send-it`, not by re-running `install`.

## Out of scope

- Worktree-first "full isolation" preset (rejected in decision #2).
- Mirroring third-party zips into this repo's releases (rejected in #5).
- Any fork/overlay of the four upstream extensions.
- Automated hook-disabling tooling (manual documented edit instead, #6).
- Submitting any of this to the upstream community catalogs (discovery-only
  anyway; can be done later independently).
