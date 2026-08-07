# Workflows

Spec Kit workflows published from this repo, and the catalog that makes them
installable.

## Available

| ID | Version | Description |
|---|---|---|
| [`yolo`](yolo/) | 0.2.1 | Gate-free core cycle — `worktree` → `specify` → `plan` → `tasks` → `implement` |
| [`send-it`](send-it/) | 0.3.1 | Spec to PR, unattended — `yolo` plus screenshots and `ship`, ending in an open pull request |
| [`send-it-checked`](send-it-checked/) | 0.3.1 | `send-it` plus staff review and QA, each with one fix-and-re-run pass |

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

## Releasing a first-party extension

First-party extensions tag as `ext-<id>-v<version>` — the `ext-` prefix keeps an
extension's tag distinct from a same-named workflow's — and ship as a zip attached
to the GitHub Release. Release assets are used rather than tag archives for two
reasons: a whole-repo tag archive would put the extension three directories deep,
and GitHub's auto-generated archives are not contractually byte-stable, while an
uploaded asset is the bytes you uploaded.

1. Bump `extension.version` in `extensions/<id>/extension.yml` and add a
   `CHANGELOG.md` entry. Finish every edit inside `extensions/<id>/` before the
   next step — the whole directory is packaged, so a later doc tweak changes the
   artifact and invalidates the digest.
2. Build and take the digest:

   ```bash
   uv run --with pyyaml python scripts/build_extension.py extensions/<id> \
     --output /tmp/speckit-addons-build
   ```

   The build is reproducible, so rebuilding from the tagged commit gives the same
   bytes and the same digest.
3. Update the `extensions/catalog.json` entry's `version`, `download_url` tag,
   `sha256`, `documentation`, `changelog`, `provides` counts, and `updated_at` —
   plus the catalog's own top-level `updated_at`.
4. Update the tables in `extensions/README.md` and the root `README.md`.
5. Run the validator and the tests, commit, then tag `ext-<id>-v<version>` and
   push the tag.
6. Create the GitHub Release on that tag and attach the built zip:

   ```bash
   gh release create ext-<id>-v<version> \
     /tmp/speckit-addons-build/<id>-<version>.zip \
     --title "<id> <version>" --notes-file extensions/<id>/CHANGELOG.md
   ```

7. Verify the pinned URLs now resolve:

   ```bash
   uv run --with pyyaml python scripts/validate_catalog.py --check-urls
   ```

## Releasing a third-party pointer change

`extensions/catalog.json`'s third-party entries hold pointers, not code, so there
is no tag of ours to cut. To bump a pinned upstream version:

1. **Read the upstream diff.** A version bump means the third-party code that
   runs with your full privileges changed. Pinning without reading defeats the
   point of pinning.
2. Recompute the digest of the new tag archive:

   ```bash
   curl -sL "<download_url>" | shasum -a 256
   ```

3. Update `version`, `download_url`, `sha256`, `documentation`, `changelog`,
   and the entry's `updated_at`, plus the catalog's top-level `updated_at`.
4. Update the tables in `extensions/README.md` and the root `README.md`.
5. Run the validator, commit, push. No tag.
