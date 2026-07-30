# Extensions

Spec Kit extensions this repo makes **installable**. None of the code here is
this repo's — every entry is a pinned pointer at somebody else's repository.

## Available

| ID | Version | Upstream | Description |
|---|---|---|---|
| `worktrees` | 1.3.2 | [dango85/spec-kit-worktree-parallel](https://github.com/dango85/spec-kit-worktree-parallel) | Default-on git worktree isolation for parallel agents |
| `ship` | 1.0.0 | [arunt14/spec-kit-ship](https://github.com/arunt14/spec-kit-ship) | Release pipeline: pre-flight, branch sync, changelog, CI check, PR |
| `staff-review` | 1.0.0 | [arunt14/spec-kit-staff-review](https://github.com/arunt14/spec-kit-staff-review) | Staff-engineer-level code review against the spec |
| `qa` | 1.0.0 | [arunt14/spec-kit-qa](https://github.com/arunt14/spec-kit-qa) | Systematic QA, browser-driven or CLI |

All four are dependencies of the [`send-it` bundle](../bundles/send-it/).

## Why this catalog exists at all

All four extensions are already listed in Spec Kit's upstream **community**
extension catalog. That catalog is registered with `install_policy:
discovery-only`, so `specify extension add` and the bundler both refuse to
install from it — you can find these extensions there, but not get them. An
install-allowed catalog has to come from somewhere, so it comes from here.

The upstream community catalog also pins `worktrees` at 1.0.0. This catalog
pins 1.3.2.

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

## What is pinned, and what that does not guarantee

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

## Trust

These extensions are unreviewed third-party code that runs with your full
privileges — the same caveat this repo's [root README](../README.md#security)
makes about its own contents. The pinned versions were read before they were
pinned. A version bump here means they get read again.
