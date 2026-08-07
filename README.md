# speckit-addons

Community add-ons for [Spec Kit](https://github.github.io/spec-kit/) — workflows
and extensions now, presets over time.

Everything here installs through Spec Kit's own catalog mechanism. Nothing needs
to be copy-pasted into `.specify/` by hand.




## Add-ons

Spec Kit keeps a **separate catalog for each add-on type**, and registering one
does not register the others. Each section below has its own `catalog add`.

### Workflows

| ID | Version | Description |
|---|---|---|
| [`yolo`](workflows/yolo/) | 0.2.0 | Full SDD cycle — `worktree` → `specify` → `plan` → `tasks` → `implement`, no review gates |
| [`send-it`](workflows/send-it/) | 0.3.0 | Spec to PR, unattended — `yolo` plus screenshots and `ship`, ending in an open pull request |
| [`send-it-checked`](workflows/send-it-checked/) | 0.3.0 | `send-it` plus staff review and QA, each with one fix-and-re-run pass |

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
  https://raw.githubusercontent.com/clintcparker/speckit-addons/yolo-v0.2.0/workflows/yolo/workflow.yml
```

Then set to work:

```bash
specify workflow run yolo -i spec="make the app do the thing"
```

### Extensions

Some of these are **hosted here** — first-party code, released from this repo.
The rest are **pinned pointers** at somebody else's repository. See
[extensions/README.md](extensions/README.md).

| ID | Version | Source |
|---|---|---|
| [`screenshots`](extensions/screenshots/) | 0.1.0 | Hosted here |
| [`worktrees`](extensions/worktrees/) | 2.2.0 | Hosted here — fork of [dango85/spec-kit-worktree-parallel](https://github.com/dango85/spec-kit-worktree-parallel) v1.0.0 |
| [`git`](extensions/git/) | 1.1.0 | Hosted here — fork of spec-kit's bundled `git` v1.0.0 |
| `ship` | 1.0.0 | Pointer → [arunt14/spec-kit-ship](https://github.com/arunt14/spec-kit-ship) |
| `staff-review` | 1.0.0 | Pointer → [arunt14/spec-kit-staff-review](https://github.com/arunt14/spec-kit-staff-review) |
| `qa` | 1.0.0 | Pointer → [arunt14/spec-kit-qa](https://github.com/arunt14/spec-kit-qa) |

```bash
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5
specify extension add screenshots
```

`--install-allowed` is not the default; without it every install is refused.

`git` is the exception: `specify extension add git` resolves spec-kit's **bundled**
copy before it ever reads a catalog, so the fork installs with `--from` instead.
[extensions/README.md](extensions/README.md#the-git-fork-installs-with---from) has
the command.

### The send-it harness

These add-ons compose into an unattended pipeline from a one-line description to a
pull request with before/after UI screenshots.
**[docs/send-it-harness.md](docs/send-it-harness.md)** is the write-up: how the
pieces fit, how to reproduce it in a new repo, and the gotchas.

### A gotcha worth knowing

Registering a **workflow** or **extension** catalog for a project *replaces*
Spec Kit's built-in `default` + `community` sources for that type — the project
config is read instead of them, not alongside. If you want the official catalogs
back after registering this one, add them explicitly and check with
`specify <type> catalog list`.

### More

Presets will appear here if they are ever published, each with its own catalog
under a directory of the same name.

## Versioning

Each add-on is versioned and tagged independently, as `<id>-v<version>` — for
example `yolo-v0.2.0`. Catalog entries pin their install URL to a tag, never to
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

Three of the extensions published here are this repo's own code; the other three
are pointers at repositories this project does not control. Those three are
unreviewed third-party code that runs with your full privileges. Each pointer
entry pins a tag *and* a SHA-256 of that tag's archive, so a re-pointed tag fails
the install rather than swapping the code silently — but a pin is not a review.
See [extensions/README.md](extensions/README.md#trust-third-party-entries).

`send-it` and `send-it-checked` also launch your application to take screenshots.
The `screenshots` extension never modifies application code, and its data rules
require app state to live outside the checkout and real user data to be restored
after every run including a failed one — but it does start your app and drive its
UI.

## Contributing

These are personal add-ons, but issues and pull requests are welcome — bug
reports especially. If you want to change how a workflow behaves in your own
project, you probably want a
[workflow overlay](https://github.github.io/spec-kit/reference/workflows.html#workflow-overlays)
rather than a fork; overlays survive `specify workflow update`.

## License

[MIT](LICENSE)
