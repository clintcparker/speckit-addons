# Workflows

Spec Kit workflows published from this repo, and the catalog that makes them
installable.

## Available

| ID | Version | Description |
|---|---|---|
| [`yolo`](yolo/) | 0.1.1 | Full SDD cycle — `specify` → `plan` → `tasks` → `implement`, no review gates |
| [`send-it`](send-it/) | 0.1.0 | Spec to PR, unattended — `yolo` plus `ship`, ending in an open pull request |
| [`send-it-checked`](send-it-checked/) | 0.1.0 | `send-it` plus staff review and QA, each with one fix-and-re-run pass |

## Install

Register the catalog once:

```bash
specify workflow catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/workflows/catalog.json
```

Then install any workflow listed above by id:

```bash
specify workflow add yolo
```

## Layout

```
workflows/
  catalog.json          # the installable catalog — one entry per workflow
  <id>/
    workflow.yml        # workflow.id must equal the directory name
    README.md
    CHANGELOG.md
```

`catalog.json` lives on `main` and is fetched from `main`, so new versions become
discoverable as soon as they land. Each entry's `url`, by contrast, is pinned to
an immutable tag — what a user installs must be reproducible, and a bad commit
must not reach existing users automatically.

## Adding a workflow

1. Create `workflows/<id>/` containing `workflow.yml`, `README.md`, and
   `CHANGELOG.md`. Set `workflow.id` to the directory name and start
   `workflow.version` at `0.1.0`.
2. Add a `catalog.json` entry keyed by the same id, with `url` pinned to the tag
   you are about to create: `<id>-v<version>`.
3. Add a row to the table above.
4. Run the validator and fix anything it reports:

   ```bash
   python scripts/validate_catalog.py
   # or, without installing anything:
   uv run --with pyyaml python scripts/validate_catalog.py
   ```

   Do **not** pass `--check-urls` before the tag is pushed. Beyond the
   guaranteed 404, `raw.githubusercontent.com` caches negative responses for
   several minutes, so requesting the URL early makes it keep 404ing *after*
   you push the tag. Add the flag only once the tag is up.

5. Commit, then tag `<id>-v<version>` and push the tag.

## Releasing a new version

1. Bump `workflow.version` in `workflow.yml`.
2. Add a `CHANGELOG.md` entry.
3. Update the `catalog.json` entry's `version`, `url` tag, `documentation`,
   `changelog`, and `updated_at` — plus the catalog's own top-level
   `updated_at`.
4. Update the version in the table above.
5. Commit, tag `<id>-v<version>`, push the tag.

Versions are per workflow, not per repo, so releasing one workflow never forces
a version bump on the others.

Existing users stay on the version they installed until they run
`specify workflow update`.
