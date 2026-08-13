---
description: "Spawn an isolated git worktree for a feature branch (default-on, configurable layout)"
---

# Create Worktree

Spawn an isolated git worktree for a feature branch so you can work on multiple features — or run multiple agents — in parallel without switching branches.

This command **owns feature-branch creation** in this project. A branch can be checked out in exactly one worktree, so if anything checks the branch out in the primary repo first (the git extension's `speckit.git.feature` hook used to), no worktree can be attached to it for as long as the primary stays there. That hook is therefore disabled in `.specify/extensions.yml`, and this command creates branch and worktree together with `git worktree add -b`. The primary checkout is not moved — except by the one recovery path in `## Outline` step 0, which needs a provably clean primary and reports the move.

The command is **idempotent**. Workflows that must not depend on `speckit.specify` running (a resumed run, or a fix-up over an already-specified feature) declare it as an explicit step *and* inherit the `before_specify` hook; step 0 makes the second of those a no-op.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). The user may specify:

- A branch name (e.g., `005-user-auth`)
- `current` to create a worktree for the current branch
- `--in-place` or `--no-worktree` to skip worktree creation entirely

When this command runs as the **`before_specify` hook**, `$ARGUMENTS` is the *feature description* the user typed after `/speckit-specify`, not a branch name. In that mode the branch usually does not exist yet — pass the description through with `--from-description` and let the script derive the name. The same is true of an explicit `worktree` workflow step that forwards the workflow's spec input. Neither is a licence to assume the branch is absent: `## Outline` step 0 checks first, and `--from-description` is correct only in its case 3.

## Prerequisites

1. Verify the project is a git repository (`git rev-parse --show-toplevel`)
2. Verify `git worktree` is available (`git worktree list` succeeds)

## Configuration

Read configuration from `.specify/extensions/worktrees/worktree-config.yml` if it exists. Defaults apply when the file is absent.

| Key | Default | Description |
|-----|---------|-------------|
| `layout` | `sibling` | `sibling` — worktree at `../<repo>--<branch>` (IDE-friendly); `nested` — at `.worktrees/<branch>/` inside repo |
| `auto_create` | `true` | When `true`, the hook creates a worktree without prompting |
| `sibling_pattern` | `{{repo}}--{{branch}}` | Name pattern for sibling directories |
| `dotworktrees_dir` | `.worktrees` | Subdirectory name for nested layout |
| `base_ref` | *(empty)* | Ref new branches fork from. Empty = auto-detect `origin/main` → `main` → `origin/master` → `master` → `HEAD` |
| `enter_worktree` | `true` | Move the agent session into the worktree after creating it |

Environment variable `SPECIFY_WORKTREE_PATH` overrides the computed path entirely.

## Outline

0. **Detect the case before doing anything.** This command is idempotent and may be invoked both as
   the `before_specify` hook and as an explicit workflow step in the same run. Resolve which of three
   situations applies, and never fall through to `--from-description` unless it is case 3:

   - **Case 1 — already isolated.** `git rev-parse --git-common-dir` differs from
     `git rev-parse --git-dir`, i.e. the session is inside a linked worktree. **No-op.** Report
     `worktree_isolation=already` with the path and exit 0. Do not create, do not enter, do not
     derive a branch name.
   - **Case 2 — primary checkout, feature branch already exists.** `git branch --show-current`
     returns a name that is not the base ref. Use that **branch name**; never `--from-description`,
     which would mint a spurious next feature number. If `git worktree list --porcelain` already
     shows a worktree for it, enter that worktree and report `worktree_isolation=entered`. If none
     exists, the branch is checked out here and `git worktree add` for it cannot succeed — see the
     failure path below.

     A detached HEAD (`git branch --show-current` empty) is *not* case 3. Resolve the branch through
     step 1's fallbacks — `SPECIFY_FEATURE`, else the most recent feature branch — and only treat it
     as case 3 when neither names one.
   - **Case 3 — primary checkout, on the base ref, no feature branch yet.** This is the
     `before_specify` case. Pass `--from-description "<description>"` and let the script derive the
     name.

   **Failure path (case 2 with no worktree).** The branch is checked out in the primary, so no
   worktree can attach to it until the primary moves off it. Attempt recovery, but only when it is
   provably safe:

   - **Recover** when `git status --porcelain` **and** `git stash list` are *both* empty in the
     primary. Nothing can be lost, so: resolve the base ref to a *local* branch where one exists
     (`origin/main` → `main`) rather than leaving the user on a detached HEAD, run
     `git checkout <base>` in the primary, then `git worktree add <path> <branch>` and enter it.
     Report `worktree_isolation=recovered` with the branch, the worktree path, and — prominently —
     that **the primary checkout was moved off the feature branch to `<base>`**. That side effect is
     the price of recovery and must never be silent.
   - **Otherwise fall back.** A dirty tree or any stash entry means the primary is holding work that
     is not this run's to move. Do not force it, do not delete the branch, do not stash, do not move
     the primary. Report `worktree_isolation=failed`, the branch name, and the reason ("the branch is
     checked out in the primary with uncommitted work; a branch can live in exactly one worktree").
     Continue in place so an unattended run still completes, and make the report available to later
     steps.

1. **Determine the target branch** — step 0 has already settled which case applies; this is how each
   one names its branch:
   - Case 3, the `before_specify` hook call → do **not** invent a branch name. Pass the feature description to the script as `--from-description "<description>"`; it delegates to the git extension's `create-new-feature-branch.sh --dry-run`, which computes the next sequential number from `specs/`, local branches and remote refs *without* creating or checking out anything.
   - Case 2, a feature branch already exists → use that branch name, never `--from-description`.
   - User supplied a branch name → use it.
   - User said `current` → use `git branch --show-current`.
   - Otherwise (manual call, no argument) → use `SPECIFY_FEATURE` if set, else the most recent feature branch.

2. **Acquire the run lock before creating anything.** Two concurrent unattended runs against the
   same primary checkout produce interleaved commits, both runs rewriting the same PR body, and one
   run's review step verifying the other's uncommitted working-tree state. A lockfile stops a second
   run before it creates anything:

   ```bash
   RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$BRANCH_NAME"
   bash .specify/extensions/worktrees/scripts/bash/acquire-lock.sh \
     --run-id "$RUN_ID" \
     --pid "$$" \
     [--json]
   ```

   The lockfile at `<primary>/.specify/run.lock` records `run_id`, `pid`, and `timestamp`. Stale-lock
   detection uses `kill -0` against the recorded `pid`: if that process is gone the lock is taken over
   silently (`LOCK_STATUS=stale-replaced`), not refused. Pass `--pid "$$"` so the lock is associated
   with the outer shell process rather than this transient subshell.

   **Exit code 3** means a live concurrent run holds the lock — its process is still alive. Report the
   conflict (the existing `run_id` and `pid`) and stop. Do not proceed to step 3, and do not pass
   `--force`. `--force` is for operator cleanup of a genuinely dead lock, not for resolving a race.

   **Skip this step** only when step 0 determined `worktree_isolation=already` (the session is already
   inside a linked worktree). An already-isolated session does not compete for the primary's lock.

   Pass `$RUN_ID` to `write-run-context.sh` via `--run-id` in step 5 so the lock and the run context
   share the same identifier.

3. **Invoke the script**:
   Run the deterministic bash script shipped with this extension:

   ```bash
   bash .specify/extensions/worktrees/scripts/bash/create-worktree.sh \
     --json \
     [--from-description "<feature description>" | "$BRANCH_NAME"] \
     [--layout sibling|nested] \
     [--path <override>] \
     [--in-place] \
     [--dry-run] \
     [--base-ref <ref>]
   ```

   The script reads `worktree-config.yml` automatically and outputs JSON:

   ```json
   {"branch":"005-user-auth","worktree":true,"path":"/Users/me/code/MyProject--005-user-auth","layout":"sibling"}
   ```

   `"reused": true` means the branch already had a worktree and nothing was created — that is success, not an error. A non-zero exit with a message naming the *primary* repo means the branch is checked out there: hand it to step 0's failure path — recover if the primary is provably clean, otherwise report and continue in place. Never force it and never delete the branch.

   If the script is unavailable (e.g., non-bash environment), perform the equivalent operations directly:
   - Resolve the worktree path based on layout config
   - Check `git worktree list --porcelain` first — if the branch already appears under a worktree, report that path and stop
   - Run `git worktree add -b <branch> <path> <base-ref>` (new branch) or `git worktree add <path> <branch>` (existing branch checked out nowhere)
   - For nested layout, ensure `.worktrees/` is in `.gitignore`

4. **Move into the worktree — or declare that you could not.** Skip only when `enter_worktree` is
   `false`, or the user passed `--in-place`/`--no-worktree`.

   Call the `EnterWorktree` tool with `path` set to the `path` from the script's JSON. The session's working directory becomes the worktree, which is what makes the rest of the feature land there: `specs/<dir>/spec.md`, `.specify/feature.json`, and every later phase (`/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, `/speckit-ship-run`) resolve relative to the worktree with no absolute-path juggling. Continue the current command — including the `/speckit-specify` body that invoked this hook — from there, and report `session=worktree`.

   **When the session cannot be moved.** Three distinct things produce that outcome:

   - **No such tool** — a non-Claude integration, where `EnterWorktree` does not exist.
   - **The call was refused** — the tool exists but needs interactive approval that nobody is present
     to give. This is the *normal* outcome of an unattended workflow run, not an error, and it is the
     case this command previously did not cover.
   - **The call failed** — the tool exists, was invoked, and returned an error.

   All three land in the same state: the worktree is real and correct, and only the session's working
   directory is wrong. **Do not silently write the spec into the primary checkout, and do not report
   this as an unqualified success.** Report `session=primary` and emit the override block in step 8's
   fields, verbatim:

   ```text
   SPECIFY_INIT_DIR=<worktree path>
   SPECIFY_FEATURE_DIRECTORY=<worktree path>/specs/<feature-dir>
   ```

   Both are first-priority overrides honored by `.specify/scripts/bash/common.sh`. `SPECIFY_INIT_DIR`
   must be exported for **every** `.specify/scripts/**` invocation from here to the end of the run;
   `SPECIFY_FEATURE_DIRECTORY` must be set before the spec is created. Under `before_specify` the
   feature directory does not exist yet — name the path it *will* have, deriving `<feature-dir>` from
   the branch name. These belong in the structured fields block precisely because prose gets skimmed
   and this is the only thing keeping the rest of the run out of the wrong tree.

   `session=primary` is a **degraded run**. It stays correct only as long as every later step honors
   the overrides, and nothing enforces that. A workflow that ships must surface it in the pull request
   description.

   When `enter_worktree` is `false` the session also stays put — report `session=primary (by
   configuration)`, which is a choice rather than a degradation. `--in-place`/`--no-worktree` creates
   no worktree at all; there is nothing to enter and no override to emit.

5. **Pin the run's feature identity to a file.** Everything decided above — which branch, which
   worktree, which feature directory — is known only to this step. A workflow engine with no
   step-output templating hands the next step nothing but its own args, so each one re-answers "which
   feature is this?" from the current branch and `.specify/feature.json`. Straight after a merge both
   name the *previous* feature, and the back half of a run drifts onto it while every script still
   exits 0. Write the answer down instead:

   ```bash
   bash .specify/extensions/worktrees/scripts/bash/write-run-context.sh \
     --branch "$BRANCH_NAME" \
     --isolation created|already|entered|recovered|failed \
     --session worktree|primary \
     --run-id "$RUN_ID" \
     [--worktree-path <path from the script's JSON>] \
     [--base-ref <resolved base ref>] \
     [--feature-dir <path>]
   ```

   Run it on **every** path through this command, including `worktree_isolation=failed` — the run
   with no worktree is the one that most needs its feature pinned. Omit `--worktree-path` when no
   worktree exists; the script then writes the context into the primary checkout, which is where that
   run executes. Pass `--feature-dir` only when the spec directory is already known and its name
   differs from the branch; otherwise the default (`<tree>/specs/<branch>`) is the same path step 4
   puts in `SPECIFY_FEATURE_DIRECTORY`, and the two must not disagree.

   The script writes `<worktree>/.specify/run-context.json` and, when the session is standing
   somewhere else, a second copy at `<primary>/.specify/run-context.json` pointing at the first.
   Neither is committable — it appends the path to `$GIT_COMMON_DIR/info/exclude`, which is local and
   covers every worktree of the repo. Report the canonical path as `run_context=<path>` in step 8's
   fields; that path is what every later step resolves `FEATURE_DIR` from.

   **Exit 3 is a collision**, not a failure to write: another unattended run already owns the
   pointer in this primary checkout, and its worktree and branch are both still live. Displacing it
   would aim this exact drift at *that* run instead, so the script refuses. This run's canonical
   context was still written. Report `run_context=collision` naming both branches, say plainly that
   two unattended runs cannot share one primary checkout, and continue — every remaining step now
   depends on `SPECIFY_INIT_DIR` being exported, because the pointer in the primary belongs to
   somebody else. Do not pass `--force` to win the race.

6. **Report what the new worktree does not carry.** A worktree is a fresh checkout of `base_ref`, so
   two classes of thing the primary has can be silently absent. Both are *reported*, never repaired —
   see `## Rules`.

   - **The base ref may lag a local branch of the same name.** `resolve_base_ref()` prefers
     `origin/main` over `main` deliberately: under the worktree-first flow the base ref — not the
     primary's HEAD — decides what the feature forks from, and forking from the *pushed* remote is
     what keeps the eventual pull request down to just the feature. When the resolved base ref is a
     remote branch whose local counterpart is ahead, say so with the count:
     `base_ref=origin/main; local main is 1 commit ahead`. Do **not** merge, rebase, cherry-pick or
     reset to close that gap — doing so drags unpushed commits into the feature branch, and they will
     show up in the pull request as if they were part of the feature. If forking from local `main` is
     what the user wants, that is a one-line `base_ref: "main"` in `worktree-config.yml`, and it is
     their call to make, not this command's.
   - **Untracked and ignored files do not exist here.** Anything gitignored or never committed — a
     `docs/` tree kept out of version control, local fixtures, a `.env` — is in the primary and not in
     the worktree, by construction. When the feature description names a path that exists in the
     primary but not in the worktree, list it:
     `missing in worktree: docs/ROADMAP.md (ignored by .gitignore:25)`. Do **not** copy it across. A
     feature whose input is not in version control cannot be reproduced from the branch, and a loud
     early report beats a run built on files the pull request will never contain.

7. **Verify spec artifacts** — only when the worktree already existed, or on a manual call. Under `before_specify` the worktree is new and intentionally has no spec yet; skip this step. Otherwise check `specs/<feature-dir>/` in the worktree and list which artifacts are present (spec.md, plan.md, tasks.md).

8. **Report**: Output a summary — the table, whichever step 6 notes actually fired, and the fields
   block. Nothing else; every later step of an unattended run reads this output as its context.

   ````markdown
   ## Worktree Created

   | Field | Value |
   |-------|-------|
   | **Branch** | 005-user-auth |
   | **Base ref** | origin/main |
   | **Layout** | sibling |
   | **Worktree path** | /Users/me/code/MyProject--005-user-auth |
   | **Isolation** | created |
   | **Session** | worktree |
   | **Run context** | /Users/me/code/MyProject--005-user-auth/.specify/run-context.json |

   ```text
   worktree_isolation=created
   session=worktree
   run_context=/Users/me/code/MyProject--005-user-auth/.specify/run-context.json
   ```

   **Next steps:**
   - Continue the current phase — you are already in the worktree
   - Run `/speckit-worktrees-list` to see all active worktrees
   ````

   Three machine-readable fields. The first two are **orthogonal** — one describes the worktree, the
   other describes where the session is standing:

   **`worktree_isolation`** carries step 0's outcome verbatim: `created` (case 3), `already` (case 1
   no-op), `entered` (case 2, worktree existed), `recovered` (the primary was moved off the branch —
   name the base ref it now sits on), or `failed` (running in the primary; name the branch and the
   reason).

   **`session`** carries step 4's outcome: `worktree` or `primary`. When it is `primary` for any
   reason other than `enter_worktree: false`, the `SPECIFY_INIT_DIR` and `SPECIFY_FEATURE_DIRECTORY`
   lines go in the fields block too, and the reason is named on the Session row (`primary —
   EnterWorktree declined, unattended run`).

   `worktree_isolation=created` together with `session=primary` is an ordinary unattended run, and it
   is exactly the combination a single enum could not express: the worktree is right and nothing is
   standing in it. Do not report it as clean.

   **`run_context`** carries step 5's outcome: the absolute path of the canonical
   `run-context.json`, or `collision` when another run owns the pointer in this primary checkout.
   Unlike the other two it is not a status — it is the address every later step needs in order to
   resolve `FEATURE_DIR` without guessing.

   **What must reach the end of the run.** Any of: `worktree_isolation` outside
   {`created`, `already`, `entered`}; `session=primary`; `run_context=collision`; or either step 6
   note firing. A ship step puts these in the pull request description rather than letting them die
   in a transcript.

## Rules

- **Idempotent** — safe to invoke twice in one run (the `before_specify` hook *and* an explicit workflow step). Step 0 decides the case before anything else happens; whichever call lands second finds the session already isolated and no-ops
- **Report hazards; never remedy them.** This command creates a branch in a worktree and moves the
  session into it. That is its entire mandate. Conditions it merely *observes* — a base ref behind
  its local counterpart, an input file that is gitignored, a stale remote, a missing dependency — get
  named in the report and left alone. Specifically: no `merge`, `rebase`, `cherry-pick`, `reset` or
  `pull` to move the branch off the base ref the script resolved, and no copying untracked or ignored
  files into the worktree. An unattended run says "never prompt", which is not a licence to act
  unilaterally — it means decide the cases this command defines and *report* everything else. A
  repair nobody asked for is worse than the condition it fixed, because the condition was visible and
  the repair is not
- **Acquire the lock before creating anything** — step 2 runs on every path that proceeds past step
  0's no-op, including `worktree_isolation=failed`. The run that needs the lock most is the one
  running in the primary checkout because its worktree failed: that is the run a concurrent session
  is most likely to collide with. Never pass `--force` from this command — that flag exists for
  operator cleanup of a genuinely dead lock, not for resolving a race between two live runs
- **Always write the run context** — step 5 runs on every path out of this command, including
  `worktree_isolation=failed` and the case-1 no-op. It is the only record of which feature this run
  owns, and the steps that need it most are the ones furthest from here. A run whose context file was
  never written is a run that will ship the previous feature
- **Never displace another run's pointer** — both the lock script's exit 3 (step 2) and the
  run-context writer's exit 3 (step 5) are decisions, not errors. `--force` exists for an operator
  clearing litter by hand, never for this command resolving a race
- **Default behavior is to create a worktree** — only skip if the user explicitly passes `--in-place` or `--no-worktree`, or `auto_create` is `false` in config and this is a hook call
- **One worktree per branch** — never create a duplicate; report the existing path and exit successfully
- **Never modify the primary checkout, with one narrow exception** — no `checkout`, no `switch`, no stash in normal operation. The primary stays where the user left it, which is the whole point of creating the branch inside the worktree. The single exception is step 0's recovery path, where the feature branch is *already* checked out in the primary and the primary is provably clean (empty `git status --porcelain`, empty `git stash list`). There, and only there, `git checkout <base>` is permitted so the branch can be released to a worktree — and the move must be reported loudly
- **Never create the branch outside the worktree** — `git worktree add -b` does both atomically; a preceding `git checkout -b` makes the worktree impossible
- **Always update .gitignore for nested layout** — add the `dotworktrees_dir` value if not present
- **Branch names come from the git extension** — call it with `--dry-run` rather than reimplementing the numbering, so branch names stay consistent with `speckit.git.feature`
- **`--from-description` only in the `before_specify` hook** — it answers "what is the *next* feature number", so calling it a second time for a feature that already has a branch mints a spurious new one. Once the branch exists, always pass the branch name
