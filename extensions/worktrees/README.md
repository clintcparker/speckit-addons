# spec-kit-worktree-parallel

> **This is a fork.** Published from
> [clintcparker/speckit-addons](https://github.com/clintcparker/speckit-addons)
> as `worktrees` v2.0.0 — dango85 v1.0.0 plus `--from-description`,
> `enter_worktree`, `base_ref`, the worktree-first flow, and a `before_specify`
> hook declaration. Upstream v1.3.2 is not merged; see
> [CHANGELOG.md](CHANGELOG.md). Original MIT license retained in
> [LICENSE](LICENSE).

A [Spec Kit](https://github.com/github/spec-kit) extension for **default-on** git worktree isolation — work on multiple features (or run parallel agents) without checkout switching.

## Why another worktree extension?

The community [spec-kit-worktree](https://github.com/Quratulain-bilal/spec-kit-worktree) extension is a good starting point. This extension differs in three ways:

1. **Default-on** — worktrees are created automatically after `/speckit.specify`. Opt *out* with `--in-place`, rather than opting in.
2. **Sibling-dir layout** — worktrees live at `../<repo>--<branch>` by default, so each feature gets its own top-level IDE window. Nested `.worktrees/` is available as an option.
3. **Deterministic bash script** — a real script (`create-worktree.sh`) with `--json` output, `--dry-run`, and `SPECIFY_WORKTREE_PATH` override, suitable for CI and scripted workflows.

## Installation

```bash
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5

specify extension add worktrees
```

## Layout modes

### Sibling (default)

Each worktree is a sibling directory of the primary clone:

```
parent/
├── my-project/                  ← primary checkout (main)
├── my-project--005-user-auth/   ← worktree (005-user-auth branch)
├── my-project--006-chat/        ← worktree (006-chat branch)
```

Open each directory in its own IDE window. No `.gitignore` changes needed.

### Nested

Worktrees live inside the repo under `.worktrees/` (auto-gitignored):

```
my-project/
├── .worktrees/
│   ├── 005-user-auth/           ← worktree
│   ├── 006-chat/                ← worktree
├── specs/
├── src/
```

Switch with `layout: nested` in `worktree-config.yml`.

## Configuration

Create `.specify/extensions/worktrees/worktree-config.yml` to override defaults:

```yaml
layout: "sibling"           # sibling | nested
auto_create: true            # false to prompt instead of auto-creating
sibling_pattern: "{{repo}}--{{branch}}"
dotworktrees_dir: ".worktrees"
base_ref: ""                 # ref new branches are cut from; "" = auto-detect
                              # (origin/main → main → origin/master → master → HEAD)
lock_ttl_minutes: 240         # how long an unreleased run lock keeps blocking the
                               # next run against this checkout
enter_worktree: true          # move the session into the new worktree; false to
                               # just print the path and stay put
```

## Commands

| Command | Description | Modifies files? |
|---------|-------------|-----------------|
| `/speckit.worktrees.create` | Spawn a worktree for a feature branch | Yes |
| `/speckit.worktrees.list` | Dashboard: status, artifacts, tasks | No |
| `/speckit.worktrees.clean` | Remove merged/stale worktrees | Yes |

## Hook

**`before_specify`** (priority 20) — creates the feature branch inside a new worktree and moves the session there *before* the spec is written. Controlled by the `auto_create` config value.

This runs before rather than after `/speckit.specify` because a branch can live in exactly one worktree: if the spec were written first, `/speckit.specify` would create (and check out) the branch in the primary checkout, and `git worktree add` cannot claim that branch for as long as the primary stays there. Worktree-first avoids this failure mode by cutting the branch straight into its worktree, then writing the spec — and every later phase — there from the start.

### The hook is not enough on its own

It fires only when a run actually *starts* at `/speckit.specify`. A resumed run, or a fix-up over a feature that was already specified, enters at a later phase, never triggers the hook, and executes entirely in the primary checkout — silently. Any workflow that must not depend on where a run entered should declare `speckit.worktrees.create` as an **explicit first step** as well. The command is idempotent as of 2.1.0 (`## Outline` step 0), so whichever of the two lands second finds the session already isolated and no-ops; there is no double-creation and no spurious second feature number.

`speckit-addons`' own [`send-it`](../../workflows/send-it/), [`send-it-checked`](../../workflows/send-it-checked/) and [`yolo`](../../workflows/yolo/) workflows all do this.

### When the branch is already checked out in the primary

`git worktree add` cannot succeed until the primary moves off it. Step 0 recovers *only* when the primary is provably clean — `git status --porcelain` and `git stash list` both empty — by checking the primary out to the base ref, attaching the worktree, and reporting `worktree_isolation=recovered` along with the base ref the primary now sits on. A dirty tree or any stash entry falls back to `worktree_isolation=failed`: the run continues in place and reports loudly, and nothing of yours is moved, stashed, or forced.

## Reported outcomes

The command reports **three** machine-readable fields. The first two are orthogonal — one describes
the worktree, the other describes where the agent session is standing.

| Field | Values | Meaning |
|---|---|---|
| `worktree_isolation` | `created`, `already`, `entered`, `recovered`, `failed` | What happened to the branch and its worktree (`## Outline` step 0) |
| `session` | `worktree`, `primary` | Whether the session's working directory actually moved (`## Outline` step 4) |
| `run_context` | a path, or `collision` | Where this run's feature identity was pinned (`## Outline` step 5) |

Moving the session needs the `EnterWorktree` tool, which requires interactive approval. In an
**unattended workflow run there is nobody to approve it**, so the normal result is
`worktree_isolation=created` with `session=primary`: the worktree is correct and nothing is standing
in it. That combination is why a single enum was not enough — 2.1.0 reported it as a bare `created`,
which a ship step reads as unqualified success.

Whenever `session=primary`, the command emits the overrides that keep the rest of the run out of the
primary checkout:

```text
session=primary
SPECIFY_INIT_DIR=/path/to/worktree
SPECIFY_FEATURE_DIRECTORY=/path/to/worktree/specs/<feature-dir>
worktree_path=/path/to/worktree
```

The first two are first-priority overrides honored by `.specify/scripts/bash/common.sh`.
`SPECIFY_INIT_DIR` has to be exported for every `.specify/scripts/**` invocation for the remainder of
the run.

**The overrides are not isolation.** Nothing outside `.specify/scripts/**` reads them: plain `git`,
`gh`, build and test commands resolve against the *current working directory*, which under
`session=primary` is the primary checkout. A later step that runs a bare `git commit` commits onto
whatever branch the primary is standing on no matter how faithfully it exported `SPECIFY_INIT_DIR`.
That is why 2.5.0 also reports `worktree_path`: every later step has to point its own commands at
that path (`git -C <path> …`, or `cd <path>` first), and the invariant it inherits is that **all
writes happen in this run's worktree on this run's branch — a step about to write in the primary
checkout has failed rather than found a workaround**.

So `session=primary` is a **degraded run**: it stays correct only as long as each later step both
honors the overrides and directs its own commands at the worktree, and nothing enforces either. A
workflow that ships should put it in the pull request description.

### The run context file

As of 2.3.0 the command also writes down *which feature this run owns*, because nothing else does. A
workflow engine with no step-output templating hands each step nothing but its own args, so every one
of them re-answers the question from the current branch and `.specify/feature.json` — and immediately
after a merge both name the **previous** feature. That is how two unattended runs can implement their
features correctly and then review, QA, screenshot and ship the last feature that merged, with every
helper script exiting 0 the whole way.

```json
{
  "schema_version": "1.0",
  "run_id": "20260812T184205Z-005-user-auth",
  "created_at": "2026-08-12T18:42:05Z",
  "branch": "005-user-auth",
  "feature_dir": "/Users/me/code/MyProject--005-user-auth/specs/005-user-auth",
  "worktree_path": "/Users/me/code/MyProject--005-user-auth",
  "primary_path": "/Users/me/code/MyProject",
  "base_ref": "origin/main",
  "worktree_isolation": "created",
  "session": "primary"
}
```

The canonical copy lives at `<worktree>/.specify/run-context.json`. When the session is standing
somewhere else — the normal unattended case — a second copy goes to
`<primary>/.specify/run-context.json` pointing at the first, because a step standing in the primary
has no other way to find the worktree. Paths are absolute for the same reason. Neither copy is
committable: the script appends the path to `$GIT_COMMON_DIR/info/exclude`, which is local, untracked,
and shared by every worktree of the repo.

A later step resolves `FEATURE_DIR` from that file — `$SPECIFY_INIT_DIR/.specify/run-context.json`
first, then the current directory, then the primary checkout — and never from the current branch or
`.specify/feature.json`. `speckit-addons`' own workflows carry that instruction in every step after
the first.

**One run per primary checkout.** If a second run's pointer would displace a live one — the other
run's worktree and branch both still present — the script exits 3 and refuses, because displacing it
just aims the same drift at that run instead. The second run still gets its own canonical context, and
the command reports `run_context=collision` naming both branches. It is a loud degradation rather than
a guarantee; concurrent unattended runs against one primary checkout are not supported.

### The run lock

As of 2.4.0 that rule is enforced before anything is created, rather than discovered halfway through.
`## Outline` step 2 takes a lockfile at `<primary>/.specify/run.lock` as soon as the branch name is
known:

```json
{
  "run_id": "20260812T112100Z-005-user-auth",
  "pid": 98293,
  "timestamp": "2026-08-12T11:21:00Z",
  "epoch": 1786663260,
  "ttl_minutes": 240
}
```

A second run with a different `run_id` is refused with **exit 3** while that lock is live, and the
lock is live when *either* signal says so:

- **the pid is alive** (`kill -0`), or
- **the lock is younger than `lock_ttl_minutes`** (default 240; `--ttl-minutes` overrides).

Only when the process is gone *and* the TTL has expired is the lock treated as litter and taken over
(`LOCK_STATUS=stale-replaced`).

**The age is what holds the line; the pid is a hint.** An agent harness runs each command in a shell
that exits the moment the call returns, so a pid written by one call is already dead by the next. A
pid-only check reads its own lock as stale within milliseconds and lets every concurrent run through
— which is the bug this guard exists to stop. Pass `--pid "$PPID"` from the calling shell (the agent
process, which lives for the whole run), never `"$$"`.

Because the TTL is the backstop and not the mechanism, a run that finishes should hand the lock back:

```bash
bash scripts/bash/release-lock.sh --run-id 20260812T112100Z-005-user-auth
```

It removes the file only while that `run_id` still owns it — `RELEASE_STATUS` is `released`,
`not-ours`, or `not-held` — so it can never free somebody else's lock. All three `speckit-addons`
workflows call it from their final step. `--force` on `acquire-lock.sh` is for an operator clearing a
lock they know is dead, never for a command resolving a race.

### It reports hazards; it does not fix them

The command creates a branch in a worktree and moves the session into it. Conditions it merely
*observes* get named and left alone:

- **A base ref behind its local counterpart.** `base_ref` auto-detect prefers `origin/main` over
  `main` on purpose — forking from the pushed remote is what keeps the eventual pull request down to
  just the feature. When local `main` is ahead, the command says so and stops there. It will not
  merge or rebase to close the gap, because that drags unpushed commits onto the feature branch where
  they surface in the PR as if they were part of the feature. Set `base_ref: "main"` if forking from
  the local branch is what you want.
- **Untracked and ignored inputs.** A fresh worktree is a checkout of `base_ref`, so a gitignored
  `docs/` tree, local fixtures, or a `.env` are in the primary and not in the worktree, by
  construction. If the feature description names such a path, the command lists it as missing rather
  than copying it across — a feature whose input is not in version control cannot be reproduced from
  the branch.

## Script usage

The bash script can be called directly for automation:

```bash
# Create a sibling worktree for branch 005-user-auth
bash scripts/bash/create-worktree.sh --json 005-user-auth

# Nested layout
bash scripts/bash/create-worktree.sh --json --layout nested 005-user-auth

# Explicit path
bash scripts/bash/create-worktree.sh --json --path /tmp/my-worktree 005-user-auth

# Dry run (compute path without creating)
bash scripts/bash/create-worktree.sh --json --dry-run 005-user-auth

# Skip worktree (single-agent mode)
bash scripts/bash/create-worktree.sh --in-place 005-user-auth
```

Pinning the feature identity is a second script, called once the first has reported and the session
has (or has not) moved:

```bash
bash scripts/bash/write-run-context.sh \
  --branch 005-user-auth \
  --isolation created \
  --session primary \
  --worktree-path /Users/me/code/MyProject--005-user-auth \
  --base-ref origin/main
```

Exit 0 written, 1 usage or environment error, 3 another live run owns the pointer in this primary
checkout. `--json` prints the context it wrote; `--force` displaces a live pointer and exists for
clearing litter by hand, not for winning a race.

The lock is a third pair of scripts, taken before either of the above creates anything and handed
back by the last step of the run:

```bash
bash scripts/bash/acquire-lock.sh --run-id 20260812T112100Z-005-user-auth --pid "$PPID"
bash scripts/bash/release-lock.sh --run-id 20260812T112100Z-005-user-auth
```

`acquire-lock.sh` exits 0 acquired (`LOCK_STATUS` is `acquired`, `refreshed`, `stale-replaced` or
`forced`), 1 usage or environment error, 3 a live run holds the lock. `release-lock.sh` always exits
0 and reports `RELEASE_STATUS=released|not-ours|not-held`. Both take `--json`.

## Environment variables

| Variable | Description |
|----------|-------------|
| `SPECIFY_WORKTREE_PATH` | Override computed worktree path entirely |
| `SPECIFY_FEATURE` | Current feature name (set by spec-kit) |

## Related

- [#61](https://github.com/github/spec-kit/issues/61) — Spawn worktree when creating new branch (36+ upvotes)
- [#1476](https://github.com/github/spec-kit/issues/1476) — Native worktree support for parallel agents
- [#1940](https://github.com/github/spec-kit/issues/1940) — Git operations extracted to extension (closed)

## Requirements

- Spec Kit >= 0.4.0
- Git >= 2.15.0 (worktree support)

## License

MIT
