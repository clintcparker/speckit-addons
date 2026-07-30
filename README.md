# speckit-addons

Community add-ons for [Spec Kit](https://github.github.io/spec-kit/) — workflows,
and over time presets, extensions, and bundles.

Everything here installs through Spec Kit's own catalog mechanism. Nothing needs
to be copy-pasted into `.specify/` by hand.




## Add-ons

Spec Kit keeps a **separate catalog for each add-on type**, and registering one
does not register the others. Each section below has its own `catalog add`.

### Workflows

| ID | Version | Description |
|---|---|---|
| [`yolo`](workflows/yolo/) | 0.1.1 | Full SDD cycle — `specify` → `plan` → `tasks` → `implement`, no review gates |
| [`send-it`](workflows/send-it/) | 0.1.0 | Spec to PR, unattended — `yolo` plus `ship`, ending in an open pull request |
| [`send-it-checked`](workflows/send-it-checked/) | 0.1.0 | `send-it` plus staff review and QA, each with one fix-and-re-run pass |

```bash
specify workflow catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/workflows/catalog.json
specify workflow add yolo
```

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

### Extensions

Pointers, not code — every entry pins somebody else's repository at a tag and a
digest. See [extensions/README.md](extensions/README.md).

| ID | Version | Upstream |
|---|---|---|
| `worktrees` | 1.3.2 | [dango85/spec-kit-worktree-parallel](https://github.com/dango85/spec-kit-worktree-parallel) |
| `ship` | 1.0.0 | [arunt14/spec-kit-ship](https://github.com/arunt14/spec-kit-ship) |
| `staff-review` | 1.0.0 | [arunt14/spec-kit-staff-review](https://github.com/arunt14/spec-kit-staff-review) |
| `qa` | 1.0.0 | [arunt14/spec-kit-qa](https://github.com/arunt14/spec-kit-qa) |

```bash
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5
specify extension add ship
```

`--install-allowed` is not the default; without it every install is refused.

### Bundles

| ID | Version | Description |
|---|---|---|
| [`send-it`](bundles/send-it/) | 0.1.0 | Spec to PR, unattended — four extensions plus both `send-it` workflows |

```bash
specify bundle catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/bundles/catalog.json \
  --id speckit-addons --policy install-allowed --priority 5
specify bundle install send-it
```

A bundle resolves its components through *your* registered catalogs, so
`send-it` needs the workflow and extension catalogs registered too. Its
[README](bundles/send-it/README.md#install) has all three commands and the
one-line post-install edit.

### A gotcha worth knowing

Registering a **workflow** or **extension** catalog for a project *replaces*
Spec Kit's built-in `default` + `community` sources for that type — the project
config is read instead of them, not alongside. The **bundle** stack is the
exception: it merges. If you want the official catalogs back after registering
this one, add them explicitly and check with `specify <type> catalog list`.

### More

Presets will appear here if they are ever published, each with its own catalog
under a directory of the same name.

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

`send-it` and `send-it-checked` go further than `yolo`: they commit, rebase,
push, and open a pull request without asking. Point `target_branch` at a branch
you are happy to see a PR against.

The extension catalog published here points at four repositories this project
does not control. They are unreviewed third-party code that runs with your full
privileges. Each entry pins a tag *and* a SHA-256 of that tag's archive, so a
re-pointed tag fails the install rather than swapping the code silently — but a
pin is not a review. See [extensions/README.md](extensions/README.md#trust).

## Contributing

These are personal add-ons, but issues and pull requests are welcome — bug
reports especially. If you want to change how a workflow behaves in your own
project, you probably want a
[workflow overlay](https://github.github.io/spec-kit/reference/workflows.html#workflow-overlays)
rather than a fork; overlays survive `specify workflow update`.

## License

[MIT](LICENSE)
