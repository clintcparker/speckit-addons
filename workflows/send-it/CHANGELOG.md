# Changelog

All notable changes to the `send-it` workflow are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this workflow adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-07-30

First published release.

### Added

- Five `command` steps: `specify` → `plan` → `tasks` → `implement` → `ship`.
  The first four are `yolo`'s; `ship` is `speckit.ship.run` from the
  [`ship`](https://github.com/arunt14/spec-kit-ship) extension.
- `target_branch` input (default `main`), passed to the `ship` step.
- Unattended `args` prose for the `ship` step: auto-accept every confirmation,
  auto-commit the working tree, never block on CI, and stop only on a rebase
  conflict that cannot be resolved trivially.

[0.1.0]: https://github.com/clintcparker/speckit-addons/releases/tag/send-it-v0.1.0
