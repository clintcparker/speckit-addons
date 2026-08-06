# The send-it harness

The harness turns a one-line feature description into an open pull request with
before/after UI screenshots, unattended. Six extensions and two workflows compose
into one chain: an explicit `worktree` step cuts the feature branch straight into
a new git worktree and moves the agent session there, the spec/plan/tasks phases
run inside it, baseline screenshots are captured while the tree still renders
what the pull request's base commit would, the implementation lands, the same
views are captured again, and `ship` commits, pushes, and opens the PR with the
before/after tables embedded. Everything below installs through Spec Kit's own
catalog mechanism — nothing an add-on owns is hand-patched into `.specify/`. The
only hand edits anywhere are to core spec-kit: one key, plus the patch that
makes core actually read it (see
[core-feature-numbering.md](core-feature-numbering.md)).

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
| [`worktrees`](../extensions/worktrees/) | 2.1.0 | hosted here | `speckit.worktrees.create` — creates the feature branch inside a new worktree and moves the session into it. Registered on `before_specify` *and* dispatched as each workflow's first step; idempotent since 2.1.0 so both can fire in one run |
| [`git`](../extensions/git/) | 1.1.0 | hosted here | Feature-branch naming and numbering. The worktrees hook delegates to its `create-new-feature-branch.sh` to derive the branch name |
| [`screenshots`](../extensions/screenshots/) | 0.1.0 | hosted here | `speckit.screenshots.capture` — before/after captures committed to the branch, driven by a per-repo app profile |
| `ship` | 1.0.0 | [arunt14/spec-kit-ship](https://github.com/arunt14/spec-kit-ship) | `speckit.ship.run` — pre-flight, rebase, push, PR creation |
| `staff-review` | 1.0.0 | [arunt14/spec-kit-staff-review](https://github.com/arunt14/spec-kit-staff-review) | `speckit.staff-review.run` — review report into `FEATURE_DIR/reviews/` |
| `qa` | 1.0.0 | [arunt14/spec-kit-qa](https://github.com/arunt14/spec-kit-qa) | `speckit.qa.run` — QA report into `FEATURE_DIR/qa/` |
| [`send-it`](../workflows/send-it/) | 0.3.0 | hosted here | The eight-step workflow: worktree → specify → plan → tasks → screenshots → implement → screenshots → ship |
| [`send-it-checked`](../workflows/send-it-checked/) | 0.3.0 | hosted here | The same, plus `review` and `qa` between implement and the after-capture |
| [`yolo`](../workflows/yolo/) | 0.2.0 | hosted here | The gate-free core cycle: worktree → specify → plan → tasks → implement. No screenshots, no ship |

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
   when unset); and, because `enter_worktree: true`, moves the agent session into
   the worktree. It runs *before* the spec is written because a branch can live
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
5. **The session model.** Every later step runs *in the worktree*, because they
   are all the same agent session and the working directory carries forward. The
   primary checkout stays on its own branch, untouched. Nothing downstream may
   assume the primary is on the feature branch.
6. **The rest of the chain.** `plan` → `tasks` → `screenshots-before` →
   `implement` → (`review` → `qa`, in `send-it-checked`) → `screenshots-after` →
   `ship`. The baseline capture has to sit between `tasks` and `implement`: at
   that point the worktree differs from the base only by spec documents, so the
   app renders exactly what the pull request's base commit would. In
   `send-it-checked` the after-capture sits after `qa` rather than after
   `implement`, so it shows the tree that actually ships rather than one the
   review pass has since changed.
7. **`ship` closes it out.** It commits what is outstanding, rebases onto the
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
  dispatch when the extension is absent. It must be at **2.1.0 or later** — the
  step relies on the idempotent case detection added there, and against 2.0.0 the
  step and the `before_specify` hook would each derive a branch name and mint two
  feature numbers.

The forks are what make this a pure `catalog add` + `extension add` sequence with
**no hand edits to `.specify/extensions.yml`**: `worktrees` 2.1.0 declares its
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
- **Sequential feature numbering collides under parallel worktrees.** Each
  worktree computes "the next number" independently from the same `specs/`
  directory and the same refs. Use timestamps, in both
  `.specify/init-options.json` (`feature_numbering`) and, for upstream's
  bundled `git` extension rather than this harness's fork, `git-config.yml`
  (`branch_numbering`) — the fork here already defaults `branch_numbering` to
  `timestamp`. Note that `feature_numbering` alone changes nothing until core is
  patched to read it; see [core-feature-numbering.md](core-feature-numbering.md).

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
