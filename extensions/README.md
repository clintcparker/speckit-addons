# Extensions

Spec Kit extensions this repo makes **installable**. Two kinds live here:

- **First-party** — code hosted in this repo, released as a zip attached to a
  GitHub Release under an `ext-<id>-v<version>` tag.
- **Third-party** — a pinned pointer at somebody else's repository. Nothing of
  theirs is on disk here.

## First-party (hosted here)

| ID | Version | Description |
|---|---|---|
| [`screenshots`](screenshots/) | 0.1.0 | Before/after UI screenshots for a feature, committed to the branch for the pull request |
| [`worktrees`](worktrees/) | 2.5.0 | Default-on worktree isolation — fork of [dango85/spec-kit-worktree-parallel](https://github.com/dango85/spec-kit-worktree-parallel) v1.0.0 |
| [`git`](git/) | 1.1.0 | Worktree-safe fork of spec-kit's bundled `git` v1.0.0 |

Both forks exist to bake in fixes that a `--force` reinstall used to revert: the
`worktrees` hook is declared at `before_specify` (upstream says `after_specify`),
and the `git` fork declares no `before_specify` hook at all, because `worktrees`
creates the branch. See each extension's CHANGELOG for the full lineage.

## Third-party (pinned pointers)

| ID | Version | Upstream | Description |
|---|---|---|---|
| `ship` | 1.0.0 | [arunt14/spec-kit-ship](https://github.com/arunt14/spec-kit-ship) | Release pipeline: pre-flight, branch sync, changelog, CI check, PR |
| `staff-review` | 1.0.0 | [arunt14/spec-kit-staff-review](https://github.com/arunt14/spec-kit-staff-review) | Staff-engineer-level code review against the spec |
| `qa` | 1.0.0 | [arunt14/spec-kit-qa](https://github.com/arunt14/spec-kit-qa) | Systematic QA, browser-driven or CLI |

## Why this catalog exists at all

The three third-party extensions are already listed in Spec Kit's upstream
**community** extension catalog. That catalog is registered with `install_policy:
discovery-only`, so `specify extension add` refuses to install from it — you can
find these extensions there, but not get them. An install-allowed catalog has to
come from somewhere, so it comes from here.

The upstream community catalog also pins `worktrees` at 1.0.0 — this repo
publishes a 2.0.0 fork of it.

## Install

Register this catalog, then install by id:

```bash
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5

specify extension add ship
```

Two things to know about that command:

- **`--install-allowed` is not the default.** Without it the catalog registers
  as discovery-only and every install fails with "is from a discovery-only
  catalog".
- **Registering a project extension catalog replaces the built-in stack.**
  Spec Kit reads `.specify/extension-catalogs.yml` *instead of* its built-in
  `default` + `community` sources, not in addition to them. If you still want
  those, add them back explicitly:

  ```bash
  specify extension catalog add \
    https://raw.githubusercontent.com/github/spec-kit/main/extensions/catalog.json \
    --name default --install-allowed --priority 10
  specify extension catalog add \
    https://raw.githubusercontent.com/github/spec-kit/main/extensions/catalog.community.json \
    --name community --priority 20
  ```

  Check the result with `specify extension catalog list`.

## The `git` fork installs with `--from`

`specify extension add git` calls `_locate_bundled_extension("git")` before it
ever constructs a catalog, and `git` ships bundled with spec-kit. No catalog
priority can shadow a bundled extension, so installing the fork by id silently
gets you upstream's copy. Use the URL form, which takes a different code path:

```bash
specify extension add git --force --from \
  https://github.com/clintcparker/speckit-addons/releases/download/ext-git-v1.1.0/git-1.1.0.zip
```

`--from` does not verify a digest — only catalog-resolved downloads call
`verify_archive_sha256`. Check it yourself against the `sha256` in
[`catalog.json`](catalog.json):

```bash
curl -sL <url> | shasum -a 256
```

## Third-party pins, and what they do not guarantee

This section is about the third-party entries only. First-party extensions are
released from this repo as GitHub Release assets, which are the bytes we
uploaded — the archive-recompression risk below does not apply to them.

Each entry pins a GitHub tag archive (`/archive/refs/tags/vX.Y.Z.zip`) and a
`sha256` of that archive, taken on 2026-07-30. Spec Kit verifies the digest
before extracting, so a re-pointed or replaced tag fails the install instead of
silently swapping the code that is about to run with your full privileges.

The cost of that choice: GitHub's auto-generated source archives are not
contractually byte-stable. GitHub has changed archive compression once before,
which invalidated checksums across the whole site. If that happens again these
installs fail with a digest mismatch that reads like tampering. The fix is to
re-read the upstream code, recompute the digests, and publish an updated
catalog — not to drop the field.

This repo **does not control these tags**. dango85 and arunt14 can move or
delete them. The weekly `--check-urls` run in CI is what surfaces that.

## Trust (third-party entries)

The three third-party extensions are unreviewed third-party code that runs with
your full privileges — the same caveat this repo's
[root README](../README.md#security) makes about its own contents. The pinned
versions were read before they were pinned. A version bump here means they get
read again.
