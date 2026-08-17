# The send-it harness

The harness turns a one-line feature description into an open pull request with
before/after UI screenshots, unattended. Six extensions and two workflows compose
into one chain: an explicit `worktree` step cuts the feature branch straight into
a new git worktree (and moves the agent session there when a human is present to
approve it — see step 5), the spec/plan/tasks phases
land inside it, baseline screenshots are captured while the tree still renders
what the pull request's base commit would, the implementation lands, the same
views are captured again, and `ship` commits, pushes, and opens the PR with the
before/after tables embedded. Everything below installs through Spec Kit's own
catalog mechanism — nothing an add-on owns is hand-patched into `.specify/`. The
only hand edits anywhere are to core spec-kit: one key, plus the patch that
makes core actually read it (see
[core-feature-numbering.md](core-feature-numbering.md)), and an optional second
patch that stops the helper scripts answering "which feature is this?" from the
checkout (see [core-helper-scripts.md](core-helper-scripts.md)).

## Four separate catalog stacks

Spec Kit keeps an independent catalog system per add-on type — workflows,
extensions, presets, bundles are the four this harness touches; the CLI also
has an integration catalog and a workflow-step catalog that don't come up
here. Separate config files
(`.specify/workflow-catalogs.yml`, `.specify/extension-catalogs.yml`), separate
env-var overrides, separate resolution. Registering one catalog URL does not
register the others, which is why the harness needs two `catalog add` calls for
one repo's worth of add-ons.

Two behaviors surprise people:

**Registering a workflow or extension catalog for a project replaces the
built-in stack for that type.** `get_active_catalogs()` returns the project
config if it exists and never falls through to the built-in `default` +
`community` sources — the project file is read *instead of* them, not alongside.
Check what you actually have with `specify workflow catalog list` or
`specify extension catalog list`, and re-add the official catalogs explicitly if
you want them back.

**The upstream community extension catalog is discovery-only.** It is registered
with `install_allowed: false`, so `specify extension search` finds these
extensions there and `specify extension add` refuses to install them. Discovery
is not installability. That gap is the entire reason
[`extensions/catalog.json`](../extensions/catalog.json) exists.

## The pieces

| Add-on | Version | Source | What it contributes |
|---|---|---|---|
| [`worktrees`](../extensions/worktrees/) | 2.5.0 | hosted here | `speckit.worktrees.create` — creates the feature branch inside a new worktree and moves the session into it *when it can*. Registered on `before_specify` *and* dispatched as each workflow's first step; idempotent since 2.1.0 so both can fire in one run. Since 2.2.0 it reports `session` separately from `worktree_isolation`, because an unattended run cannot enter the worktree; since 2.3.0 it also writes the run context file every later step reads its feature identity from; since 2.4.0 it takes the run lock that keeps two runs off one primary checkout; and since 2.5.0 it reports `worktree_path` and says plainly that the path overrides isolate only `.specify/scripts/**` |
| [`git`](../extensions/git/) | 1.1.0 | hosted here | Feature-branch naming and numbering. The worktrees hook delegates to its `create-new-feature-branch.sh` to derive the branch name |
| [`screenshots`](../extensions/screenshots/) | 0.4.0 | hosted here | `speckit.screenshots.capture` — before/after captures committed to the branch, driven by a per-repo app profile |
| `ship` | 1.0.0 | [arunt14/spec-kit-ship](https://github.com/arunt14/spec-kit-ship) | `speckit.ship.run` — pre-flight, rebase, push, PR creation |
| `staff-review` | 1.0.0 | [arunt14/spec-kit-staff-review](https://github.com/arunt14/spec-kit-staff-review) | `speckit.staff-review.run` — review report into `FEATURE_DIR/reviews/` |
| `qa` | 1.0.0 | [arunt14/spec-kit-qa](https://github.com/arunt14/spec-kit-qa) | `speckit.qa.run` — QA report into `FEATURE_DIR/qa/` |
| [`send-it`](../workflows/send-it/) | 0.10.0 | hosted here | The eight-step workflow: worktree → specify → plan → tasks → screenshots → implement → screenshots → ship |
| [`send-it-checked`](../workflows/send-it-checked/) | 0.11.0 | hosted here | The same, plus `review` and `qa` between implement and the after-capture |
| [`yolo`](../workflows/yolo/) | 0.9.0 | hosted here | The gate-free core cycle: worktree → specify → plan → tasks → implement. No screenshots, no ship |

The three first-party extensions are published from this repo as release assets
with a `sha256` in the catalog. The three third-party ones are pinned pointers at
somebody else's tag archive — same digest guarantee, but this repo does not
control those tags.

## How it composes

1. **`specify init` writes `.specify/`.** It also writes
   `.specify/init-options.json` with `"feature_numbering": "sequential"`. That
   key is core spec-kit's, not extension-owned, and nothing installed later can
   change it.
2. **Catalogs registered, extensions installed.** Each install writes the
   extension's hook declarations into `.specify/extensions.yml`, which is what
   the core command files read at run time.
3. **`specify workflow run send-it -i spec="…"`** dispatches step 1, the
   `worktree` step.
4. **The `worktree` step isolates the run.** `speckit.worktrees.create` derives
   the branch name via `--from-description`, which delegates to the git
   extension's `create-new-feature-branch.sh --dry-run --json` for numbering and
   slug rules; creates the branch with `git worktree add -b` from `base_ref`
   (auto-detected as `origin/main` → `main` → `origin/master` → `master` → `HEAD`
   when unset); and, because `enter_worktree: true`, tries to move the agent
   session into the worktree — which unattended it cannot, see step 5. It also
   reports what the fresh worktree does *not* carry: a base ref behind its local
   counterpart, and gitignored or untracked inputs the description names. Both are
   reported and left alone; the step creates a branch in a worktree and repairs
   nothing it merely observed. It runs *before* the spec is written because a branch can live
   in exactly one worktree: let `speckit.specify` create and check out the branch
   in the primary checkout first and `git worktree add` cannot claim it for as
   long as the primary stays there.

   **Why a step and not only the hook.** The `worktrees` extension also registers
   this command on `before_specify`, and until `send-it` 0.3.0 that was the only
   thing creating the worktree. A hook fires only when a run actually *starts* at
   `speckit.specify` — a resumed run, or a fix-up over an already-specified
   feature, enters at a later step, never triggers it, and executes entirely in
   the primary checkout, silently. The workflows now declare the step *and*
   inherit the hook; `speckit.worktrees.create` is idempotent as of `worktrees`
   2.1.0, so whichever lands second sees the session is already isolated and
   no-ops. It never mints a second feature number.

   **When the branch is already checked out in the primary** — the fix-up case —
   the step recovers only if the primary is provably clean (`git status
   --porcelain` and `git stash list` both empty): it moves the primary to the base
   ref, attaches the worktree, and reports `worktree_isolation=recovered`. Dirty
   tree or any stash: `worktree_isolation=failed`, the run continues in the
   primary, and `ship` puts that fact in the pull request description. Nothing of
   the user's is stashed, moved, or forced.
5. **The session model — and why an unattended run does not get one.** Moving the
   session into the worktree needs the `EnterWorktree` tool, and that tool requires
   interactive approval. **An unattended run has nobody to give it.** So the normal
   outcome of `specify workflow run send-it` is `worktree_isolation=created` with
   `session=primary`: the branch lives in its worktree, the agent session's working
   directory is still the primary checkout, and every later step lands in the right
   place only because the worktree step emitted

   ```text
   SPECIFY_INIT_DIR=<worktree path>
   SPECIFY_FEATURE_DIRECTORY=<worktree path>/specs/<feature-dir>
   worktree_path=<worktree path>
   ```

   and each step honors them. The first two are first-priority overrides in
   `.specify/scripts/bash/common.sh`. This is a **degraded run**: nothing enforces that
   the overrides are honored across seven remaining steps, which is exactly why `ship`
   puts `session=primary` in the pull request description rather than letting it die in
   a transcript.

   **And the overrides are only half the isolation.** Nothing outside
   `.specify/scripts/**` reads them — plain `git`, `gh`, build and test commands resolve
   against the *current working directory*, which under `session=primary` is the primary
   checkout. That is not theoretical either: a run's `screenshots-before` step committed
   straight to `main`, its `review` step left its fixes as uncommitted state on `main`,
   and `ship` then cut a branch at `main`'s tip to avoid a `main → main` pull request —
   moving the user's checkout under them and carrying unrelated `main` commits into the
   PR — while every step exported `SPECIFY_INIT_DIR` correctly the whole way.

   So `worktrees` 2.5.0 also reports `worktree_path`, and every step of all three
   workflows carries a **WORKTREE DISCIPLINE** block next to its FEATURE IDENTITY block:
   direct every command at the run's tree explicitly (`git -C <tree> …`, or `cd <tree>`
   first), where `<tree>` is the run context's `worktree_path` — or its `primary_path`
   when the run has no worktree at all; check `git -C <tree> rev-parse --show-toplevel`
   and `git -C <tree> branch --show-current` against the run context before the first
   write; and treat *being about to write in the primary checkout* as a failed step
   rather than a workaround. `ship` additionally pushes with `git -C <tree> push` and
   passes `--head` and `--base` to `gh pr create` explicitly, so no pull request is ever
   inferred from the branch the primary happens to be standing on.

   The other way to close the gap is to stop the run standing in the primary at all:
   pre-approve `EnterWorktree` in the harness's permission allowlist, and the session
   really does move (`session=worktree`), which makes the working directory right and
   the overrides and the discipline block redundant. That is a harness-side setting, not
   something a workflow or extension here can declare, which is why the discipline block
   is the fix that ships in this repo.

   When the tool *is* approved — an interactive run — the session really does move,
   `session=worktree`, the working directory carries forward, and the overrides are
   unnecessary. That was the only case documented before `worktrees` 2.2.0, and it is
   not the case the harness actually runs in.

   Either way the primary checkout stays on its own branch, untouched, and nothing
   downstream may assume the primary is on the feature branch.
6. **The run context pins which feature this is.** The overrides above only help a step
   that already knows to use them, and the engine has **no step-output templating**: a
   step receives its own `args` and nothing else — not the worktree step's report, not
   the previous step's output. Left to themselves, every step answers "which feature is
   this?" from the current branch and `.specify/feature.json`, and the session is
   standing in the primary checkout, where right after a merge both name the feature
   that just shipped. That is not a hypothetical: two concurrent unattended runs
   implemented their features correctly and then reviewed, QA'd, screenshotted and
   shipped the previous, already-merged one, while every helper script exited 0.

   So `worktrees` 2.3.0 writes `<worktree>/.specify/run-context.json` — `run_id`,
   `branch`, absolute `feature_dir`, `worktree_path`, `primary_path`, `base_ref`,
   `worktree_isolation`, `session` — plus a pointer copy at
   `<primary>/.specify/run-context.json` when the session stays in the primary, since a
   step standing there has no other way to find the worktree. Neither copy is
   committable; the path goes into `$GIT_COMMON_DIR/info/exclude`.

   Every step after `worktree` in all three workflows carries a FEATURE IDENTITY block
   in its `args`: read that file, take `branch`/`feature_dir`/`worktree_path` from it,
   export the two `SPECIFY_*` overrides from those values, and **fail the step loudly**
   rather than adopt a feature the run context does not name. `ship` refuses to commit,
   push, or open a pull request at all when the context is missing or disagrees. A
   script exiting 0 is not evidence it found the right feature — `setup-plan.sh` exits 0
   on the wrong one and plants a template `plan.md` there.

   The block is repeated verbatim in every step because there is nowhere else to put it.
   And there is exactly one pointer per primary checkout, so **one unattended run per
   primary checkout**: a second is reported as `run_context=collision` and surfaced in
   the pull request rather than silently repointing the first.

   **The block asks the agent to fail on a mismatch; the scripts still cannot refuse to
   produce one.** Unpinned, `get_feature_paths` resolves from `.specify/feature.json` —
   per-checkout state that every explicit resolution writes back to — so in the primary
   right after a merge it names the feature that just shipped, and there is no way for a
   caller to ask which source the answer came from. Consumers here close that from their
   own side: the `screenshots` extension cross-checks whatever
   `check-prerequisites.sh --paths-only --json` resolves against the pinned value and
   stops on a disagreement (issue #8). The other side of it is an opt-in
   `SPECIFY_STRICT_FEATURE=1` in core, which makes the fallback a hard error rather than
   a quiet answer — [core-helper-scripts.md](core-helper-scripts.md) has that patch and
   its verification, along with the `--allow-missing-plan` one for the mirror-image
   failure, where `check-prerequisites.sh --json` exits 1 on any feature that never ran
   `/speckit-plan`.
7. **The run lock enforces "one run per primary checkout" up front.** The collision
   report above is a diagnosis after the fact — by the time a second run reaches it, both
   runs have already been creating things. `worktrees` 2.4.0 takes a lockfile at
   `<primary>/.specify/run.lock` as soon as the branch name is known and before anything
   is created: `run_id`, `pid`, `timestamp`, `epoch`, `ttl_minutes`. A second run gets
   exit 3 and stops.

   **Liveness cannot be a PID question here.** Every command an agent runs gets a shell
   that exits the moment the call returns, so a PID recorded by one call is dead by the
   next; a PID-only check would call its own lock stale within milliseconds and let every
   concurrent run through. The lock is therefore held while its process is alive **or**
   while it is younger than `lock_ttl_minutes` (default 240, in `worktree-config.yml`),
   and the step passes `--pid "$PPID"` — the agent process — rather than `$$`. Because the
   TTL is a backstop and not the mechanism, each workflow's last step (`ship`, or
   `implement` in `yolo`) calls `release-lock.sh`, which frees the lock only while this
   run still owns it.

   The `ship` step carries the cheap second guard too: it ends the pull request
   description with `<!-- speckit-run-id: <run_id> -->` and will not overwrite a body
   whose marker names a *later* run — it comments instead. Run ids start with a UTC
   timestamp, so string order is time order.
8. **The rest of the chain.** `plan` → `tasks` → `screenshots-before` →
   `implement` → (`review` → `qa`, in `send-it-checked`) → `screenshots-after` →
   `ship`. The baseline capture has to sit between `tasks` and `implement`: at
   that point the worktree differs from the base only by spec documents, so the
   app renders exactly what the pull request's base commit would. In
   `send-it-checked` the after-capture sits after `qa` rather than after
   `implement`, so it shows the tree that actually ships rather than one the
   review pass has since changed.
9. **`ship` closes it out.** It commits what is outstanding, rebases onto the
   target branch, pushes, builds the PR description — including one screenshot
   table per captured target, with Before and After columns and a row per
   viewport, pinned to the pushed head SHA — and opens the pull request.

## Reproducing it in a new repo

```bash
specify init . --integration claude

# feature_numbering is core spec-kit's, not extension-owned. init writes
# "sequential"; change it to "timestamp" in .specify/init-options.json.
# Then patch core so it actually reads the key — stock spec-kit ignores it and
# keeps numbering specs/ sequentially. See docs/core-feature-numbering.md.

specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5
specify workflow catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/workflows/catalog.json

specify extension add worktrees
specify extension add screenshots
specify extension add ship
specify extension add staff-review    # send-it-checked only
specify extension add qa              # send-it-checked only

# git must be installed from a URL — see "Why git is installed with --from".
# This one prompts for confirmation; answer y, or pipe it in when scripting.
specify extension add git --force --from \
  https://github.com/clintcparker/speckit-addons/releases/download/ext-git-v1.1.0/git-1.1.0.zip

specify workflow add send-it
specify workflow add send-it-checked  # send-it-checked only
specify workflow run send-it -i spec="make the app do the thing"
```

Five things about that sequence:

- **`specify init` prompts for confirmation in a non-empty directory.**
  Reproducing the harness in an existing repo is exactly that case. Answer y,
  or pass `--force` (documented in `specify init --help`) to skip the prompt
  non-interactively.
- **`--integration` is the flag name as of specify 0.15.2**, which every CLI
  behavior described here was checked against; earlier releases spelled it
  `--ai`, and `.specify/init-options.json` still records both keys.
- **`--name` is required and `--install-allowed` is not the default** on
  `specify extension catalog add`. Without the latter the catalog registers as
  discovery-only and every install from it is refused.
- **`specify extension add` takes exactly one id per invocation.** Passing
  several fails with "Got unexpected extra argument(s)".
- **`worktrees` needs `git` installed to derive a branch name**, at
  `.specify/extensions/git/scripts/bash/create-new-feature-branch.sh`. The order
  of the two installs does not matter; both being installed before the first
  `workflow run` does.
- **`worktrees` is no longer optional for any of these workflows.** All three
  dispatch `speckit.worktrees.create` as their first step, which fails at
  dispatch when the extension is absent. It must be at **2.4.0 or later** — that
  is where the run lock lands, and without it two runs launched against one
  checkout interleave rather than the second one refusing to start. 2.3.0 is where
  the run context file every step after the first resolves its feature from was
  added. The workflows also rely on the `session` field and the
  `EnterWorktree`-refused path added in 2.2.0, and on the idempotent case
  detection added in 2.1.0. Against 2.0.0 the step and the `before_specify` hook
  would each derive a branch name and mint two feature numbers; against 2.1.0 an
  unattended run reports a bare `worktree_isolation=created` that hides the fact
  that the session never moved; against 2.2.0 there is no run context to read, so
  every step falls back to re-deriving the feature and the back half of the run
  drifts onto whatever merged last.

The forks are what make this a pure `catalog add` + `extension add` sequence with
**no hand edits to `.specify/extensions.yml`**: `worktrees` 2.2.0 declares its
hook at `before_specify` priority 20, and the `git` fork declares no competing
`before_specify` hook, so the branch is created once, in the worktree — and the
workflows' own `worktree` step no-ops when the hook got there first. The
`screenshots` extension ships its app profile with `unconfigured: true` and
derives it on first run, so there is nothing to fill in before the first pass
either — review what it wrote afterward, and see
[`examples/`](../extensions/screenshots/examples/) for two worked profiles.

## Remaining manual steps

There are exactly three.

**`feature_numbering: "timestamp"` in `.specify/init-options.json`.** Core
spec-kit owns this key and no extension can set it. Left at the default
`sequential`, parallel worktrees collide: each computes "the next number"
independently from the same `specs/` directory and the same refs.

**The core patch that makes that key do anything.** Setting it is necessary but
not sufficient: through spec-kit 0.15.2 `create-new-feature.sh` only honors an
explicit `--timestamp` flag and never reads `init-options.json`, and the
`speckit.specify` prose asks the agent to hand-derive the prefix by scanning
`specs/`. Both keep producing `001-`, `002-` while this repo's `git` fork
correctly timestamps the branch — so the branch and worktree look right and only
the spec directory drifts. [core-feature-numbering.md](core-feature-numbering.md)
carries both halves of the patch and a six-case test.

**Skill regeneration after editing any command file under
`.specify/extensions/*/commands/`.** Installing an extension generates
`.claude/skills/` entries that embed a *copy* of the command body, with
skills-shaped frontmatter substituted in. Edit the installed command file in
place and the agent keeps running the stale copy; skills are only re-registered
by an install, so regenerating means `specify extension add <id> --force` (or
`specify extension update`), which reverts the edit (see gotchas). Per-repo
adaptation therefore belongs in config, not in an edited command — the
`screenshots` extension is built exactly that way, its command generic and its
app profile a config file — but the rule holds for anything you do hand-edit.

## Why git is installed with `--from`

`specify extension add git` calls `_locate_bundled_extension("git")` before it
ever constructs an `ExtensionCatalog`, and `git` is bundled with spec-kit at
`specify_cli/core_pack/extensions/git/`. The bundled copy wins unconditionally;
no catalog priority can shadow it. `--from` takes a different branch that skips
the bundled lookup entirely and installs under the manifest's own id, so the
installed id is still `git` and hook wiring is unaffected.

Two caveats come with that branch.

**It prompts, and the default is no.** Any `--from` URL raises an "Untrusted
Source" panel followed by `typer.confirm("Continue with installation?",
default=False)`. The panel says the URL "is not listed in any of your configured
extension catalogs", but no such check runs — the prompt is unconditional for
`--from`, and registering this repo's catalog does not silence it. A
non-interactive run therefore aborts before downloading anything.
`specify extension add` has no pre-authorization flag; only
`specify init --extension <url>` has one (`--trust-extension-urls`). Scripted
installs feed the answer in:

```bash
printf 'y\n' | specify extension add git --force --from \
  https://github.com/clintcparker/speckit-addons/releases/download/ext-git-v1.1.0/git-1.1.0.zip
```

**It does not verify a digest.** Only catalog-resolved downloads call
`verify_archive_sha256`. Check the archive by hand against the `sha256` in
[`extensions/catalog.json`](../extensions/catalog.json):

```bash
curl -sL https://github.com/clintcparker/speckit-addons/releases/download/ext-git-v1.1.0/git-1.1.0.zip \
  | shasum -a 256
```

## Gotchas

- **`--force` reinstalls revert hand edits to `extension.yml`.** This is why both
  hook fixes are baked into the forks rather than applied per repo. What
  `--force` *does* preserve is config: top-level `*-config.yml` and
  `*-config.local.yml` files under `.specify/extensions/<id>/` are backed up and
  restored around the reinstall.
- **A config file that is not named `*-config.yml` is silently destroyed.**
  `scaffold_config` refuses any other `provides.config` target name, so it is
  never deployed on install; and the `--force` backup only globs that pattern, so
  an existing one is removed and not restored. This is why the screenshots app
  profile is `screenshots-config.yml` and not `app-profile.md`.
- **`config.defaults` in an extension manifest is live, not documentation.**
  `ConfigManager._get_extension_defaults()` reads it as the base layer of
  `get_config()`, beneath the deployed `<id>-config.yml`. That deployed file can
  legitimately be absent: `scaffold_config` only runs from `extension add` and
  `extension enable`, so an extension installed via `specify init --extension
  <url>` never gets one scaffolded, and a user can always delete or never commit
  the file. Whenever it's missing, the manifest's default is what takes effect.
  The `git` fork therefore sets `branch_numbering: timestamp` in *both*
  `config-template.yml` and `extension.yml`'s `config.defaults`. A fork that
  changes only the template leaves a stale default that silently reactivates the
  bug it was forked to fix.
- **Bundled extensions win over catalogs, unconditionally.** See the `git`
  section above. Applies to any bundled id: `git`, `bug`, `assess`,
  `agent-context`.
- **Registering a project workflow or extension catalog replaces the built-in
  stack** for that type — it is read *instead of* `default` + `community`, not
  alongside. Re-add the official catalogs explicitly if you want them.
- **The upstream community extension catalog is discovery-only.** It lists these
  extensions but `specify extension add` refuses to install from it. Discovery is
  not installability.
- **`raw.githubusercontent.com` negative-caches 404s for several minutes.**
  Requesting a release URL before its tag is pushed makes it keep 404ing *after*
  you push. Never run `validate_catalog.py --check-urls` before the tag is up.
- **GitHub tag archives are not contractually byte-stable**, which is why
  first-party extensions here ship as **release assets** instead: an uploaded
  asset is the bytes you uploaded. Third-party pointer entries still carry that
  risk, and the fix if it ever fires is to re-read the upstream code and
  recompute digests, not to drop the `sha256` field.
- **Workflow `requires` has no extension key.** Only `speckit_version` and
  `integrations` are recognized, and an unknown key is a hard validation error. A
  workflow's extension dependencies are documentation, enforced only by the step
  failing at dispatch.
- **Screenshot app state must live outside the checkout.** The git extension's
  auto-commit hooks — and ship's instruction to commit everything outstanding
  before its pre-flight — will otherwise commit a SQLite database or a
  dev-server log.
- **An artifact the pull request links has to be tracked, and `git add -f` is not
  how you get there.** Target repos ignore `specs/*/screenshots/` and
  `specs/*/releases/` often enough that it should be assumed, and the images are
  linked by path from the PR body — one that git still considers ignored was
  never in the pushed head, so the link 404s for every reviewer. A force-add
  clears one commit and leaves the next step with the same rule, which is how the
  same conflict got re-discovered five times in two runs (issue #7). The
  ARTIFACT VISIBILITY block in every step resolves it once instead: `git
  check-ignore` before committing, and on a hit a `!<subdir>/` line appended to
  `<feature_dir>/.gitignore`, which outranks the repo root's — so plain `git add`
  works for every later step and in the reviewer's checkout. The repo's own
  ignore rules are read, never edited. The `screenshots` extension does the same
  for its own directory in step 2 of `capture.md`, so the fix holds even when the
  command runs outside these workflows.
- **A feature whose inputs are not in version control cannot run in a worktree.**
  A worktree is a fresh checkout of `base_ref`, so anything gitignored or never
  committed — a `docs/` tree kept out of git, local fixtures, a `.env` — exists in
  the primary and not in the worktree, by construction. Point a spec description
  at `docs/ROADMAP.md` when `docs/` is gitignored and the run has no roadmap to
  read. `worktrees` 2.2.0 reports this rather than papering over it: copying the
  files across would build the feature against inputs the pull request can never
  contain and no reviewer can see. Commit the inputs, or pass their content in the
  description. This is the same hazard as the screenshot-state one above, running
  in the opposite direction.
- **An unattended run cannot enter its own worktree.** `EnterWorktree` needs
  interactive approval. Expect `session=primary` and a run that stays correct only
  because every step honors `SPECIFY_INIT_DIR` *and* aims its own commands at the
  worktree. See "The session model" above.
- **A path override is not a working directory.** `SPECIFY_INIT_DIR` and
  `SPECIFY_FEATURE_DIRECTORY` are read by `.specify/scripts/**` and by nothing else, so
  every plain `git`, `gh`, build or test command a step runs lands wherever the session
  is standing — the primary checkout, in an unattended run. Isolation by path override
  covers only the tooling that reads the override; everything else needs `git -C <tree>`
  or a `cd`. This is what the WORKTREE DISCIPLINE block in every workflow step is for,
  and pre-approving `EnterWorktree` is the alternative that removes the need for it.
- **A PID is not a run.** Every command an agent runs gets a shell that exits when
  the call returns, so nothing that outlives a single tool call can be identified
  by the PID that wrote it. The run lock records one, but only as positive
  evidence — alive means live, dead means nothing — and leans on
  `lock_ttl_minutes` for the actual guarantee. Anything else in this harness that
  wants to know whether a run is still going needs the same treatment.
- **A lock left unreleased blocks the next run for its whole TTL.** That is the
  cost of the previous bullet: with the PID unusable as an all-clear, only an
  explicit `release-lock.sh` or the TTL frees it. Each workflow's last step
  releases it; a run killed mid-flight does not, and the next run against that
  checkout waits (default four hours) or clears the file by hand.
- **Never let the worktree step repair what it reports.** A base ref behind local
  `main` is a real hazard, and `git merge --ff-only main` in the worktree is the
  wrong fix: it drags unpushed commits onto the feature branch, where they surface
  in the pull request as if they were part of the feature. `base_ref` in
  `worktree-config.yml` is the supported lever, and choosing it is the user's call.
- **Sequential feature numbering collides under parallel worktrees.** Each
  worktree computes "the next number" independently from the same `specs/`
  directory and the same refs. Use timestamps, in both
  `.specify/init-options.json` (`feature_numbering`) and, for upstream's
  bundled `git` extension rather than this harness's fork, `git-config.yml`
  (`branch_numbering`) — the fork here already defaults `branch_numbering` to
  `timestamp`. Note that `feature_numbering` alone changes nothing until core is
  patched to read it; see [core-feature-numbering.md](core-feature-numbering.md).
- **`.specify/feature.json` is per-checkout state, not per-run.** It is what
  `get_feature_paths` falls back to with no `SPECIFY_FEATURE_DIRECTORY` set, and
  every command that *does* resolve explicitly persists its answer back into it. So
  in the primary right after a merge it names the feature that just shipped, and
  the helper scripts exit 0 on it — `setup-plan.sh` goes further and plants a
  template `plan.md` there. Do not read an exit code as evidence of the right
  feature; cross-check what a script resolved against the run context, and see
  [core-helper-scripts.md](core-helper-scripts.md) for the `SPECIFY_STRICT_FEATURE`
  patch that turns the fallback into an error.
- **`check-prerequisites.sh --json` gates on `plan.md`.** Any feature that never
  ran `/speckit-plan` — a hand-started branch, a run that adopted an existing spec
  — makes it exit 1, including for callers that only wanted `FEATURE_DIR`. Use
  `--paths-only`, which resolves without validating and without persisting the
  override into `feature.json`.

## Publishing changes

Release procedures live in [`workflows/README.md`](../workflows/README.md) —
cutting a workflow version, and bumping a pinned third-party extension in the
extensions catalog. First-party extensions tag as
`ext-<id>-v<version>` — the `ext-` prefix keeps an extension's tag distinct from
a same-named workflow's — with the built zip attached to the GitHub Release. The
archive comes from [`scripts/build_extension.py`](../scripts/build_extension.py),
which pins timestamps, entry order, and permissions so the same tree produces the
same bytes anywhere; the catalog's `sha256` is the digest of that uploaded asset,
and [`scripts/validate_catalog.py`](../scripts/validate_catalog.py) checks every
catalog entry, cross-checking against the manifest on disk for add-ons hosted in
this repo — pointer entries like the three arunt14 extensions have no local
manifest to check against.
