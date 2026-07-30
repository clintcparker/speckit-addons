# Bundles

Spec Kit bundles published from this repo, and the catalog that makes them
installable.

## Available

| ID | Version | Description |
|---|---|---|
| [`send-it`](send-it/) | 0.1.0 | Spec to PR, unattended — four extensions plus the `send-it` and `send-it-checked` workflows |

## Install

```bash
specify bundle catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/bundles/catalog.json \
  --id speckit-addons --policy install-allowed --priority 5

specify bundle install send-it
```

A bundle installs its components **by id through your registered catalog
stacks** — the `source:` field a bundle manifest may carry is parsed and then
ignored by the installer. So every catalog a bundle draws from has to be
registered separately first. `send-it` needs the workflow and extension
catalogs too; its [README](send-it/README.md#install) lists all three commands.

Unlike the workflow and extension stacks, the bundle stack **merges** with Spec
Kit's built-in sources rather than replacing them.

## Layout

```
bundles/
  catalog.json          # the installable catalog — one entry per bundle
  <id>/
    bundle.yml          # bundle.id must equal the directory name
    README.md           # required: `specify bundle build` refuses without it
    CHANGELOG.md
```

Everything inside `<id>/` is packaged into the distributable artifact by
`specify bundle build`, so nothing that is not meant to ship belongs there.

## Release tags

Bundles tag as `bundle-<id>-v<version>` — for example `bundle-send-it-v0.1.0`.
The `bundle-` prefix exists because a bundle id may collide with a workflow id
(`send-it` is both), and the two must be versionable independently.

See [workflows/README.md](../workflows/README.md#releasing-a-bundle) for the
release procedure.
