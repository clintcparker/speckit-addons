# YOLO — Full SDD Cycle, no gates

Runs the complete Spec Kit cycle — `specify` → `plan` → `tasks` → `implement` —
straight through, with no human review gates in between.

The built-in `speckit` workflow pauses twice: once to review the generated spec,
once to review the plan. YOLO removes both. You describe what you want, walk
away, and come back to a finished branch.

```bash
specify workflow run yolo -i spec="make the app do the thing"
```

## Why you might want this

The gates exist for a good reason, and most of the time you should use them. But
when you already trust the shape of the change, the gates are two interruptions
that produce intermediate output you were never going to read carefully anyway.

That trade is only safe because of source control. Run YOLO on a branch. If it
goes sideways, throw the branch away and try again with a better prompt — which
is usually the real fix, since the quality of the result tracks the quality of
what you asked for.

## Install

If you have not already registered this repo's catalog:

```bash
specify workflow catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/workflows/catalog.json
```

Then:

```bash
specify workflow add yolo
```

Or install this one workflow directly, without registering the catalog:

```bash
specify workflow add yolo --from \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/yolo-v0.1.0/workflows/yolo/workflow.yml
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `spec` | yes | — | What you want built. Passed to every step. |
| `integration` | no | `auto` | Which agent integration to dispatch to. `auto` uses whatever the project was initialized with. |

Supply `spec` on the command line with `-i spec="..."`, or leave it off and
Spec Kit will prompt for it.

## Steps

Four `command` steps, no gates, no shell:

| Step | Command |
|---|---|
| `specify` | `speckit.specify` |
| `plan` | `speckit.plan` |
| `tasks` | `speckit.tasks` |
| `implement` | `speckit.implement` |

## Requirements

Spec Kit `>=0.8.5` — the first release that resolves `integration: "auto"`
engine-side. On older versions `auto` is treated as a literal integration name
and dispatch fails.

The `requires.integrations` list names `claude` as an advisory compatibility
hint, not a restriction. All four commands are core Spec Kit commands that every
integration provides, so YOLO runs against whatever your project is initialized
with.

## Adding your own steps

Rather than forking this file, use a workflow overlay — your changes then
survive `specify workflow update`. To lint after implementation, for example:

```yaml
id: "add-lint"
extends: "yolo"
priority: 10
edits:
  - insert_after: implement
    step:
      id: run-lint
      type: shell
      run: "ruff check src/"
```

```bash
specify workflow overlay add project-overlay.yml
```

Note that `shell` steps run with your full privileges and are not sandboxed. If
you add one, consider putting a `gate` step in front of it.

## Caveats

- **No review gates.** That is the entire point, and it is a real trade. Use a
  branch.
- **Not a substitute for knowing what you want.** YOLO removes the interruptions,
  not the need for a clear spec. A vague `spec` input produces a confident,
  fast, wrong implementation.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
