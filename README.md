# speckit-addons

Community add-ons for [Spec Kit](https://github.github.io/spec-kit/) — workflows,
and over time presets, extensions, and bundles.

Everything here installs through Spec Kit's own catalog mechanism. Nothing needs
to be copy-pasted into `.specify/` by hand.




## Add-ons

### Workflows

| ID | Version | Description |
|---|---|---|
| [`yolo`](workflows/yolo/) | 0.1.1 | Full SDD cycle — `specify` → `plan` → `tasks` → `implement`, no review gates |


#### Install

Register this repo's workflow catalog once, per project or per user:

```bash
specify workflow catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/workflows/catalog.json
specify workflow add yolo
```

_OR_

Registering the catalog also means every workflow published here later is
available with no further setup — `specify workflow list` and
`specify workflow add <id>` just see them.

To install a single workflow without registering the catalog:

```bash
specify workflow add yolo --from \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/yolo-v0.1.1/workflows/yolo/workflow.yml
```

Then set to work:

```bash

specify workflow run yolo -i spec="make the app do the thing"
```



### More
Presets, extensions, and bundles will appear here as they are published, each
with its own catalog under a directory of the same name. Spec Kit keeps a
separate catalog for each add-on type, so each one is registered separately.

## Versioning

Each add-on is versioned and tagged independently, as `<id>-v<version>` — for
example `yolo-v0.1.1`. Catalog entries pin their install URL to a tag, never to
a branch, so an install is reproducible and a change never reaches existing
users until they run `specify workflow update`.

See [workflows/README.md](workflows/README.md) for the release procedure.

## Security

Spec Kit add-ons are third-party code. The Spec Kit maintainers
[do not review, audit, endorse, or support](https://github.github.io/spec-kit/reference/workflows.html)
community workflows, and that applies to everything in this repo too. Read a
workflow before you install it — they are short, and this one is four steps.

Two things worth understanding about the execution model:

- **`requires` is advisory, not a sandbox.** It declares a Spec Kit version and
  a compatibility hint. It does not restrict what a workflow can do at runtime.
- **`shell` steps run with your full privileges.** Nothing here uses one — the
  `yolo` workflow is entirely `command` steps — but if you add one via an
  overlay, put a `gate` step in front of anything destructive.

And specific to this repo: `yolo` deliberately removes the human review gates
that the built-in `speckit` workflow provides. That is its whole purpose. Run it
on a branch.

## Contributing

These are personal add-ons, but issues and pull requests are welcome — bug
reports especially. If you want to change how a workflow behaves in your own
project, you probably want a
[workflow overlay](https://github.github.io/spec-kit/reference/workflows.html#workflow-overlays)
rather than a fork; overlays survive `specify workflow update`.

## License

[MIT](LICENSE)
