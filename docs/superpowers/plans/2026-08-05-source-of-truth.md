# speckit-addons as the Source of Truth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish every piece of the send-it harness from this repo's catalogs — a
new `screenshots` extension, first-party forks of `worktrees` and `git`, both
send-it workflows at 0.2.0, and the write-up — so `homeapp1/.specify/` stops being
the only copy of anything.

**Architecture:** `extensions/` starts hosting first-party code alongside its pinned
third-party pointers. First-party extensions ship as byte-stable zips attached to
GitHub Releases under `ext-<id>-v<version>` tags; third-party entries keep pointing
at upstream tag archives. A generalized `scripts/validate_catalog.py` enforces the
disk-vs-catalog agreement for the hosted half while leaving the pointer half alone.
The `screenshots` extension splits generic command from per-repo app profile along
the exact seam the two hand-written `capture.md` variants already share.

**Tech Stack:** Python 3.12 (validator + build script, PyYAML), pytest (validator
tests), YAML extension/workflow manifests, Markdown commands, bash/PowerShell/Python
extension scripts, GitHub Releases via `gh`.

## Global Constraints

- Repo slug is `clintcparker/speckit-addons`. Everything pins to it.
- All work lands on the **`source-of-truth`** branch. PR reviewed by Clint.
  **Tags are cut only after merge** — Task 11 is the only task that tags or releases.
- First-party extension release tags: `ext-<id>-v<version>`. Release asset filename:
  `<id>-<version>.zip`. Workflow release tags stay `<id>-v<version>`.
- Catalog `documentation` / `changelog` for **hosted** add-ons pin to
  `https://github.com/clintcparker/speckit-addons/blob/<tag>/...`; for **pointer**
  add-ons they must live under the upstream `repository`.
- Never run `python scripts/validate_catalog.py --check-urls` before the tag is
  pushed — `raw.githubusercontent.com` caches negative responses for minutes, so an
  early request keeps 404ing *after* the tag lands.
- Python is invoked as `uv run --with pyyaml python ...` (no system PyYAML here).
  Tests: `uv run --with pyyaml --with pytest python -m pytest tests/ -q`.
- Versions being published: `screenshots` **0.1.0**, `worktrees` **2.0.0**,
  `git` **1.1.0**, `send-it` **0.2.0**, `send-it-checked` **0.2.0**.
- Commit messages are conventional-commit style, matching repo history.

## Findings that change the spec

These were verified by reading the installed `specify-cli 0.15.2` source at
`~/.local/share/uv/tools/specify-cli/lib/python3.12/site-packages/specify_cli/`.
They are binding; where a finding contradicts the spec, the finding wins.

1. **Config templates MUST be named `*-config.yml` or `*-config.local.yml`.**
   `ExtensionManager._target_follows_preserved_convention` (`extensions/__init__.py:2552`)
   rejects any other `provides.config` target name; `scaffold_config` then reports it
   as *failed* and never deploys it, and the `--force` backup/restore path
   (`extensions/__init__.py:2386-2408`) only preserves that same glob. The spec's
   `app-profile.md` would therefore be silently dropped on install and destroyed on
   reinstall — the exact failure the config mechanism was chosen to avoid.
   **The profile ships as `screenshots-config.yml` (YAML) instead of `app-profile.md`.**
   `ConfigManager` reads it from `.specify/extensions/screenshots/screenshots-config.yml`.

2. **Catalog priority cannot shadow the bundled `git` extension.**
   `extension_add` (`extensions/_commands.py:962-966`) calls
   `_locate_bundled_extension(extension)` **before** it ever constructs an
   `ExtensionCatalog`, and `git` is bundled at `specify_cli/core_pack/extensions/git/`.
   `specify extension add git` therefore always installs upstream's copy regardless of
   catalog priority. The spec's Risk-2 fallback is the only path:
   **the `git` fork installs with `specify extension add git --from <release-asset-url>`.**
   That branch (`extensions/_commands.py:947-960`) bypasses the bundled lookup and
   installs under the manifest's own id, so the id stays `git` and hook wiring is
   unaffected. Caveat to document: `--from` does **not** verify a sha256 (only
   catalog-resolved downloads call `verify_archive_sha256`), so the catalog digest is
   for manual verification.

3. **There is no machine-readable extension requirement for workflows.**
   `_RECOGNIZED_REQUIRES_KEYS = frozenset({"speckit_version", "integrations"})`
   (`workflows/engine.py:129`), and an unrecognized `requires` key is a hard
   validation error. The `screenshots` dependency is documented in the workflow
   `description` and README only.

4. **The wrapping-dir zip layout is correct.** `install_from_zip`
   (`extensions/__init__.py:2508-2519`) accepts `extension.yml` at the archive root
   *or* inside exactly one top-level subdirectory. Spec Risk 1 is retired.
   Exec bits need not survive: `install_from_directory` calls
   `ensure_executable_scripts(project_root)` afterwards
   (`extensions/__init__.py:2444-2458`). The builder preserves them anyway.

## File Structure

**Created**

| Path | Responsibility |
|---|---|
| `tests/test_validate_catalog.py` | Unit tests for the catalog validator's hosted/pointer branching |
| `tests/test_build_extension.py` | Unit tests for zip determinism and layout |
| `scripts/build_extension.py` | Build a byte-stable release zip for one first-party extension |
| `extensions/screenshots/extension.yml` | Manifest: one command, one config template |
| `extensions/screenshots/commands/capture.md` | The generic, never-edited-per-repo capture command |
| `extensions/screenshots/screenshots-config.yml` | App-profile template, ships unconfigured |
| `extensions/screenshots/examples/aspnet-playwright.yml` | homeapp1's mechanics as a profile |
| `extensions/screenshots/examples/tauri-applescript.yml` | site-checker's mechanics as a profile |
| `extensions/screenshots/README.md` | What it is, the seam, bootstrap, install |
| `extensions/screenshots/CHANGELOG.md` | 0.1.0 |
| `extensions/worktrees/**` | Fork of dango85 v1.0.0 + local patches, at 2.0.0 |
| `extensions/git/**` | Fork of spec-kit-core bundled v1.0.0 + numbering patch, at 1.1.0 |
| `docs/send-it-harness.md` | The scaffolding write-up |

**Modified**

| Path | Change |
|---|---|
| `scripts/validate_catalog.py` | Mixed-locality add-on types; hosted extension rules |
| `.github/workflows/validate.yml` | Run pytest before the validator |
| `extensions/catalog.json` | Add `screenshots`, `git`; repoint `worktrees` |
| `workflows/send-it/workflow.yml` | → 0.2.0, screenshot steps, visibility detection |
| `workflows/send-it/README.md`, `CHANGELOG.md` | 0.2.0 + screenshots dependency |
| `workflows/send-it-checked/workflow.yml` | → 0.2.0, screenshot steps around qa |
| `workflows/send-it-checked/README.md`, `CHANGELOG.md` | 0.2.0 + screenshots dependency |
| `workflows/catalog.json` | Both send-it entries → 0.2.0 |
| `workflows/README.md` | Version table; first-party extension release procedure |
| `extensions/README.md` | First-party (hosted) vs third-party (pointer) sections |
| `README.md` | Extension table; **delete the Bundles section**; link the write-up |

---

### Task 1: Validator support for first-party hosted extensions

The `extensions` catalog is about to hold two kinds of entry — code hosted here and
pointers at other people's repos. The validator currently assumes a type is all one
or all the other. Teach it per-entry locality, plus the two extension-specific checks
the spec asks for (config templates exist; version agreement) and one more that
Finding 1 makes essential (config target names survive `--force`).

**Files:**
- Create: `tests/test_validate_catalog.py`
- Modify: `scripts/validate_catalog.py`
- Modify: `.github/workflows/validate.yml`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `AddonType` gains `hosted_url_kind: str | None`, `locality: str`
  (`"local-only"` | `"pointer-only"` | `"mixed"`), `checks_config_templates: bool`;
  method `AddonType.hosted_here(addon_id: str) -> bool`. New module function
  `config_templates_are_installable(*, addon_type, addon_id, report) -> None`.
  `validate_entry_urls` gains keyword-only params `url_kind: str` and `hosted: bool`,
  replacing its internal reads of `addon_type.url_kind`. The extensions `AddonType`
  becomes `locality="mixed"`, `manifest="extension.yml"`,
  `manifest_section="extension"`, `tag_prefix="ext-"`,
  `hosted_url_kind="release-asset"`, `checks_config_templates=True`.
  Tasks 3–5 rely on this to publish hosted entries.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_validate_catalog.py`:

```python
"""Tests for the catalog validator's hosted-vs-pointer entry handling.

The validator's whole job is to catch disagreements that are invisible locally,
so its own branching is worth pinning down: a hosted entry and a pointer entry
live in the same catalog file and are validated by different rules.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "validate_catalog", REPO_ROOT / "scripts" / "validate_catalog.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_catalog"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def vc(tmp_path, monkeypatch):
    """The validator module, rooted at an empty temp repo."""
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    return module


def _write_catalog(root: Path, entries: dict) -> None:
    (root / "extensions").mkdir(parents=True, exist_ok=True)
    (root / "extensions" / "catalog.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-08-05T00:00:00Z",
                "catalog_url": "https://raw.githubusercontent.com/clintcparker/"
                "speckit-addons/main/extensions/catalog.json",
                "extensions": entries,
            }
        ),
        encoding="utf-8",
    )


def _write_extension(root: Path, ext_id: str, manifest_yaml: str) -> Path:
    ext_dir = root / "extensions" / ext_id
    ext_dir.mkdir(parents=True, exist_ok=True)
    (ext_dir / "extension.yml").write_text(manifest_yaml, encoding="utf-8")
    return ext_dir


def _hosted_entry(ext_id: str, version: str) -> dict:
    tag = f"ext-{ext_id}-v{version}"
    base = "https://github.com/clintcparker/speckit-addons"
    return {
        "id": ext_id,
        "name": ext_id,
        "description": "d",
        "author": "clintcparker",
        "version": version,
        "license": "MIT",
        "repository": base,
        "download_url": f"{base}/releases/download/{tag}/{ext_id}-{version}.zip",
        "sha256": "a" * 64,
        "documentation": f"{base}/blob/{tag}/extensions/{ext_id}/README.md",
        "changelog": f"{base}/blob/{tag}/extensions/{ext_id}/CHANGELOG.md",
    }


def _pointer_entry(ext_id: str, version: str) -> dict:
    repo = f"https://github.com/someone/spec-kit-{ext_id}"
    return {
        "id": ext_id,
        "name": ext_id,
        "description": "d",
        "author": "someone",
        "version": version,
        "license": "MIT",
        "repository": repo,
        "download_url": f"{repo}/archive/refs/tags/v{version}.zip",
        "sha256": "b" * 64,
        "documentation": f"{repo}/blob/v{version}/README.md",
        "changelog": f"{repo}/blob/v{version}/CHANGELOG.md",
    }


def _extensions_type(vc):
    return next(t for t in vc.ADDON_TYPES if t.catalog_key == "extensions")


def _run(vc):
    report = vc.Report()
    vc.validate_addon_type(_extensions_type(vc), False, report)
    return report


def test_hosted_and_pointer_entries_coexist(vc, tmp_path):
    _write_extension(
        tmp_path,
        "screenshots",
        'schema_version: "1.0"\n'
        "extension:\n  id: screenshots\n  version: 0.1.0\n",
    )
    _write_catalog(
        tmp_path,
        {
            "screenshots": _hosted_entry("screenshots", "0.1.0"),
            "ship": _pointer_entry("ship", "1.0.0"),
        },
    )
    assert _run(vc).failures == []


def test_hosted_entry_version_must_match_manifest(vc, tmp_path):
    _write_extension(
        tmp_path,
        "screenshots",
        'schema_version: "1.0"\n'
        "extension:\n  id: screenshots\n  version: 0.9.9\n",
    )
    _write_catalog(tmp_path, {"screenshots": _hosted_entry("screenshots", "0.1.0")})
    failures = _run(vc).failures
    assert any("disagrees with" in f for f in failures)


def test_hosted_entry_must_use_release_asset_url(vc, tmp_path):
    _write_extension(
        tmp_path,
        "screenshots",
        'schema_version: "1.0"\n'
        "extension:\n  id: screenshots\n  version: 0.1.0\n",
    )
    entry = _hosted_entry("screenshots", "0.1.0")
    entry["download_url"] = (
        "https://github.com/clintcparker/speckit-addons/archive/refs/tags/"
        "ext-screenshots-v0.1.0.zip"
    )
    _write_catalog(tmp_path, {"screenshots": entry})
    failures = _run(vc).failures
    assert any("release asset" in f for f in failures)


def test_hosted_extension_on_disk_without_catalog_entry_fails(vc, tmp_path):
    _write_extension(
        tmp_path,
        "orphan",
        'schema_version: "1.0"\nextension:\n  id: orphan\n  version: 0.1.0\n',
    )
    _write_catalog(tmp_path, {})
    failures = _run(vc).failures
    assert any("unreachable to users" in f for f in failures)


def test_config_template_must_exist(vc, tmp_path):
    _write_extension(
        tmp_path,
        "screenshots",
        'schema_version: "1.0"\n'
        "extension:\n  id: screenshots\n  version: 0.1.0\n"
        "provides:\n  config:\n"
        '    - name: "screenshots-config.yml"\n'
        '      template: "screenshots-config.yml"\n',
    )
    _write_catalog(tmp_path, {"screenshots": _hosted_entry("screenshots", "0.1.0")})
    failures = _run(vc).failures
    assert any("does not exist" in f for f in failures)


def test_config_target_name_must_survive_force_reinstall(vc, tmp_path):
    ext_dir = _write_extension(
        tmp_path,
        "screenshots",
        'schema_version: "1.0"\n'
        "extension:\n  id: screenshots\n  version: 0.1.0\n"
        "provides:\n  config:\n"
        '    - name: "app-profile.md"\n'
        '      template: "app-profile.md"\n',
    )
    (ext_dir / "app-profile.md").write_text("x", encoding="utf-8")
    _write_catalog(tmp_path, {"screenshots": _hosted_entry("screenshots", "0.1.0")})
    failures = _run(vc).failures
    assert any("-config.yml" in f for f in failures)


def test_real_repo_catalogs_pass():
    """The committed catalogs must validate against the add-ons on disk."""
    module = _load_module()
    report = module.Report()
    for addon_type in module.ADDON_TYPES:
        module.validate_addon_type(addon_type, False, report)
    assert report.failures == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pyyaml --with pytest python -m pytest tests/test_validate_catalog.py -q`

Expected: FAIL. `test_hosted_and_pointer_entries_coexist`,
`test_hosted_entry_version_must_match_manifest`,
`test_hosted_entry_must_use_release_asset_url`,
`test_hosted_extension_on_disk_without_catalog_entry_fails`,
`test_config_template_must_exist` and
`test_config_target_name_must_survive_force_reinstall` all fail — the extensions
`AddonType` still has `manifest=None`, so every entry is treated as a pointer and
`config_templates_are_installable` does not exist.
`test_real_repo_catalogs_pass` passes.

- [ ] **Step 3: Add locality to `AddonType`**

In `scripts/validate_catalog.py`, replace the `AddonType` dataclass body's field list
and `has_local_addons` property. The docstring's three URL-kind paragraphs stay; add
the locality note.

```python
@dataclass(frozen=True)
class AddonType:
    """One of Spec Kit's independent add-on catalog systems.

    Each type has its own catalog file, its own top-level key inside that file,
    and its own rules for what an entry's install URL must look like. The three
    URL kinds differ because the add-ons differ in where their bits live:

    ``raw-manifest``
        The add-on's manifest is a file in this repo; the entry points at it on
        raw.githubusercontent.com, pinned to the release tag.
    ``release-asset``
        The add-on is distributed as a built artifact attached to a GitHub
        Release in this repo.
    ``external``
        This repo publishes only a pointer -- the bits belong to somebody else.
        Nothing is on disk here and nothing is tagged here; the entry must
        instead pin a third-party tag archive and carry a sha256.

    ``locality`` says which of those a *type* may contain. ``extensions`` is
    ``"mixed"``: first-party extensions live here and release as assets, while
    third-party entries stay pointers. Locality is therefore decided per entry,
    by whether the add-on's manifest is on disk -- not per type.
    """

    directory: str  # repo directory holding this type's add-ons
    catalog_key: str  # top-level key inside catalog.json
    url_field: str  # entry field holding the install URL
    url_kind: str  # url kind for entries NOT hosted here
    manifest: str | None = None  # per-add-on manifest filename, if any
    manifest_section: str | None = None  # top-level key inside the manifest
    tag_prefix: str = ""  # release tag is f"{tag_prefix}{id}-v{version}"
    extra_required_fields: tuple[str, ...] = ()
    hosted_url_kind: str | None = None  # url kind for entries hosted here
    locality: str = "local-only"  # "local-only" | "pointer-only" | "mixed"
    checks_config_templates: bool = False  # verify provides.config is installable

    def hosted_here(self, addon_id: str) -> bool:
        """True when this add-on's source lives in this repo."""
        if self.manifest is None or self.locality == "pointer-only":
            return False
        return (REPO_ROOT / self.directory / addon_id / self.manifest).is_file()

    def tag_for(self, addon_id: str, version: str) -> str:
        return f"{self.tag_prefix}{addon_id}-v{version}"
```

- [ ] **Step 4: Redeclare the two add-on types**

Replace the `ADDON_TYPES` tuple (keep the commented-out bundles block untouched
below it):

```python
ADDON_TYPES = (
    AddonType(
        directory="workflows",
        catalog_key="workflows",
        url_field="url",
        url_kind="raw-manifest",
        manifest="workflow.yml",
        manifest_section="workflow",
        extra_required_fields=("url",),
        locality="local-only",
        # Every workflow is hosted here, so this -- not url_kind -- is the
        # branch that actually runs for them.
        hosted_url_kind="raw-manifest",
    ),
    AddonType(
        directory="extensions",
        catalog_key="extensions",
        url_field="download_url",
        # Pointer entries pin somebody else's tag archive; first-party entries
        # ship as release assets built from extensions/<id>/ in this repo.
        url_kind="external",
        hosted_url_kind="release-asset",
        manifest="extension.yml",
        manifest_section="extension",
        tag_prefix="ext-",
        extra_required_fields=("download_url", "repository", "sha256"),
        locality="mixed",
        checks_config_templates=True,
    ),
```

- [ ] **Step 5: Branch per entry in `validate_addon_type` and `validate_entry`**

In `validate_addon_type`, replace the `on_disk` assignment so directories are
collected whenever the type can hold local add-ons:

```python
    on_disk = (
        {
            child.name
            for child in sorted(type_dir.iterdir())
            if child.is_dir() and not child.name.startswith(".")
        }
        if addon_type.manifest is not None
        else set()
    )
```

In `validate_entry`, replace the block from `if addon_type.has_local_addons:` through
the `validate_entry_urls(...)` call with:

```python
    hosted = addon_type.hosted_here(addon_id)

    if addon_type.locality == "local-only" and not hosted:
        report.fail(
            where,
            f"{addon_type.directory}/{addon_id}/{addon_type.manifest} is missing "
            f"-- every entry of this type is published from this repo",
        )
        return

    if hosted:
        if not manifest_agrees(
            addon_type=addon_type,
            addon_id=addon_id,
            entry_version=entry_version,
            where=where,
            report=report,
        ):
            # A version we cannot trust makes every URL check below meaningless.
            return
        if addon_type.checks_config_templates:
            config_templates_are_installable(
                addon_type=addon_type, addon_id=addon_id, report=report
            )
    elif not entry_version:
        return

    validate_entry_urls(
        addon_type=addon_type,
        addon_id=addon_id,
        entry=entry,
        entry_version=entry_version,
        where=where,
        check_urls=check_urls,
        hosted=hosted,
        url_kind=(addon_type.hosted_url_kind if hosted else addon_type.url_kind),
        report=report,
    )
```

`validate_entry` no longer reads `on_disk` — `hosted_here` answers the same question
per entry. Drop the parameter from its signature and from the call in
`validate_addon_type`. The `on_disk` set itself stays: the orphan check above the
loop (`on_disk - set(entries)`) is what makes a hosted extension with no catalog
entry a failure.

Likewise, `manifest_agrees` keeps its `manifest_path.is_file()` guard even though
`hosted_here` has already established the file exists. It is a cheap invariant check
on a function that is reachable from more than one place, not dead code to remove.

- [ ] **Step 6: Make `validate_entry_urls` take the resolved kind**

Change its signature to accept `hosted: bool` and `url_kind: str`, and replace every
`addon_type.url_kind` read inside it with the parameter:

```python
def validate_entry_urls(
    *,
    addon_type: AddonType,
    addon_id: str,
    entry: dict[str, Any],
    entry_version: str,
    where: str,
    check_urls: bool,
    hosted: bool,
    url_kind: str,
    report: Report,
) -> None:
    tag = addon_type.tag_for(addon_id, entry_version)
    url = entry.get(addon_type.url_field)

    if url_kind == "raw-manifest":
```

then `elif url_kind == "release-asset":` for the middle branch, and in the doc-link
loop swap the condition:

```python
        if not hosted:
            repository = str(entry.get("repository") or "").rstrip("/")
```

and in the `--check-urls` hint:

```python
            hint = (
                "      Has the upstream tag been deleted or re-pointed?"
                if not hosted
                else f"      Has the {tag} tag been pushed?"
            )
```

- [ ] **Step 7: Add the config-template check**

Insert after `manifest_agrees` in `scripts/validate_catalog.py`:

```python
def config_templates_are_installable(
    *, addon_type: AddonType, addon_id: str, report: Report
) -> None:
    """Check provides.config against what Spec Kit will actually deploy.

    ``ExtensionManager.scaffold_config`` refuses any config target that is not a
    top-level ``*-config.yml`` / ``*-config.local.yml`` file, because remove()
    and the ``--force`` backup/restore path only preserve that shape. A
    differently-named target is never deployed on install and is destroyed on
    reinstall; a template file that does not exist is dropped just as quietly.
    Both failures are invisible until somebody's adaptation disappears.
    """
    manifest_path = REPO_ROOT / addon_type.directory / addon_id / addon_type.manifest
    manifest = load_yaml(manifest_path, report)
    if manifest is None:
        return

    provides = manifest.get("provides")
    if not isinstance(provides, dict):
        return

    where = rel(manifest_path)
    entries = provides.get("config", [])
    if not isinstance(entries, list):
        report.fail(where, '"provides.config" must be a list')
        return

    for entry in entries:
        if not isinstance(entry, dict):
            report.fail(where, "each provides.config entry must be a mapping")
            continue

        template = entry.get("template")
        if not isinstance(template, str) or not template:
            report.fail(where, 'a provides.config entry has no "template"')
            continue

        report.check(
            (manifest_path.parent / template).is_file(),
            where,
            f"provides.config template {template!r} does not exist in "
            f"{addon_type.directory}/{addon_id}/",
        )

        name = entry.get("name") or template
        report.check(
            isinstance(name, str)
            and "/" not in name
            and "\\" not in name
            and (
                name.endswith("-config.yml") or name.endswith("-config.local.yml")
            ),
            where,
            f"provides.config name {name!r} does not survive "
            f"'specify extension add --force' -- it must be a top-level file "
            f"ending in '-config.yml' or '-config.local.yml'",
        )
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `uv run --with pyyaml --with pytest python -m pytest tests/test_validate_catalog.py -q`

Expected: PASS, 7 passed.

- [ ] **Step 9: Run the validator against the real repo**

Run: `uv run --with pyyaml python scripts/validate_catalog.py`

Expected: `✓ NN checks passed.` — the four existing pointer entries still validate.

- [ ] **Step 10: Add pytest to CI**

In `.github/workflows/validate.yml`, change the pip step and insert a test step
before the validator step:

```yaml
      - run: pip install pyyaml pytest

      - name: Run tests
        run: python -m pytest tests/ -q

      - name: Validate catalogs against add-ons on disk
        run: python scripts/validate_catalog.py
```

- [ ] **Step 11: Commit**

```bash
git add tests/test_validate_catalog.py scripts/validate_catalog.py .github/workflows/validate.yml
git commit -m "feat(validator): support first-party hosted extension entries"
```

---

### Task 2: Reproducible extension zip builder

First-party extensions are distributed as release assets whose sha256 goes in the
catalog. The digest is computed *before* the tag exists (Tasks 3–5) and the asset is
uploaded *after* the merge (Task 11), so the build must be byte-identical across
runs and machines.

**Files:**
- Create: `scripts/build_extension.py`
- Create: `tests/test_build_extension.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `build_extension(extension_dir: Path, output_dir: Path) -> Path`,
  returning the path of the written `<id>-<version>.zip`. CLI:
  `python scripts/build_extension.py extensions/<id> --output <dir>`, printing the
  zip path and its sha256 as `<sha256>  <path>`. Tasks 3–5 call the CLI; Task 11
  rebuilds with it.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_build_extension.py`:

```python
"""Tests for the first-party extension zip builder.

The digest of this zip goes into a catalog entry that users verify, so the two
properties that matter are: the archive is byte-stable across builds, and its
layout is one that specify-cli's install_from_zip actually accepts.
"""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "build_extension", REPO_ROOT / "scripts" / "build_extension.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_extension"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def be():
    return _load_module()


@pytest.fixture
def sample(tmp_path):
    ext = tmp_path / "src" / "demo"
    (ext / "commands").mkdir(parents=True)
    (ext / "scripts" / "bash").mkdir(parents=True)
    (ext / "extension.yml").write_text(
        'schema_version: "1.0"\nextension:\n  id: demo\n  version: 1.2.3\n',
        encoding="utf-8",
    )
    (ext / "commands" / "run.md").write_text("# run\n", encoding="utf-8")
    script = ext / "scripts" / "bash" / "go.sh"
    script.write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")
    script.chmod(0o755)
    (ext / ".DS_Store").write_text("junk", encoding="utf-8")
    return ext


def test_names_archive_from_manifest(be, sample, tmp_path):
    out = be.build_extension(sample, tmp_path / "dist")
    assert out.name == "demo-1.2.3.zip"


def test_wraps_contents_in_a_single_top_level_dir(be, sample, tmp_path):
    out = be.build_extension(sample, tmp_path / "dist")
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert "demo/extension.yml" in names
    assert "demo/commands/run.md" in names
    assert "demo/scripts/bash/go.sh" in names
    assert {n.split("/")[0] for n in names} == {"demo"}


def test_excludes_junk_files(be, sample, tmp_path):
    out = be.build_extension(sample, tmp_path / "dist")
    with zipfile.ZipFile(out) as zf:
        assert not any(n.endswith(".DS_Store") for n in zf.namelist())


def test_is_byte_stable_across_builds(be, sample, tmp_path):
    first = (be.build_extension(sample, tmp_path / "a")).read_bytes()
    second = (be.build_extension(sample, tmp_path / "b")).read_bytes()
    assert first == second


def test_preserves_the_executable_bit(be, sample, tmp_path):
    out = be.build_extension(sample, tmp_path / "dist")
    with zipfile.ZipFile(out) as zf:
        modes = {i.filename: i.external_attr >> 16 for i in zf.infolist()}
    assert modes["demo/scripts/bash/go.sh"] & 0o111
    assert not modes["demo/commands/run.md"] & 0o111


def test_rejects_a_directory_without_a_manifest(be, tmp_path):
    empty = tmp_path / "nope"
    empty.mkdir()
    with pytest.raises(SystemExit):
        be.build_extension(empty, tmp_path / "dist")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pyyaml --with pytest python -m pytest tests/test_build_extension.py -q`

Expected: FAIL — collection error, `scripts/build_extension.py` does not exist.

- [ ] **Step 3: Write the builder**

Create `scripts/build_extension.py`:

```python
#!/usr/bin/env python3
"""Build a byte-stable release zip for a first-party extension.

The archive's SHA-256 is published in ``extensions/catalog.json`` and verified by
specify-cli before extraction, so the build has to be reproducible: the same
source tree must produce the same bytes on any machine, at any time. Everything
that would otherwise leak in -- mtimes, directory order, host umask, junk files
-- is pinned here.

Layout: a single top-level directory named after the extension id, holding
``extension.yml`` and everything beside it. ``ExtensionManager.install_from_zip``
accepts the manifest at the archive root or inside exactly one top-level
subdirectory; the wrapping dir matches the shape of the tag archives the
installer already handles.

Usage:
    python scripts/build_extension.py extensions/screenshots --output dist/
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


# The DOS timestamp epoch. Any fixed value works; this one is conventional for
# reproducible archives and is the earliest a zip can represent.
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

# Never shipped. Editor and OS droppings would otherwise change the digest
# depending on whose machine built the archive.
EXCLUDED_NAMES = frozenset({".DS_Store", "Thumbs.db", "__pycache__", ".git"})
EXCLUDED_SUFFIXES = (".pyc", ".swp", ".orig", ".rej")


def read_manifest(extension_dir: Path) -> dict:
    manifest_path = extension_dir / "extension.yml"
    if not manifest_path.is_file():
        sys.exit(f"No extension.yml in {extension_dir}")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.exit(f"{manifest_path} top-level value must be a mapping")
    section = data.get("extension")
    if not isinstance(section, dict):
        sys.exit(f'{manifest_path} is missing an "extension" mapping')
    for field in ("id", "version"):
        if not section.get(field):
            sys.exit(f'{manifest_path} extension.{field} is missing')
    return section


def is_excluded(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_NAMES for part in relative.parts):
        return True
    return path.name.endswith(EXCLUDED_SUFFIXES)


def collect_files(root: Path) -> list[Path]:
    """Every shipped file, in a stable order that does not depend on the OS."""
    files = [p for p in root.rglob("*") if p.is_file() and not is_excluded(p, root)]
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def build_extension(extension_dir: Path, output_dir: Path) -> Path:
    """Write ``<output_dir>/<id>-<version>.zip`` and return its path."""
    extension_dir = extension_dir.resolve()
    section = read_manifest(extension_dir)
    extension_id = str(section["id"])
    version = str(section["version"])

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{extension_id}-{version}.zip"
    if archive_path.exists():
        archive_path.unlink()

    # ZIP_STORED, not ZIP_DEFLATED: zlib emits different compressed bytes for
    # identical input across zlib versions, which would make the digest depend on
    # the building machine. These are small text trees -- compression saves a few
    # KB on a release asset; reproducibility is worth more than that.
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for source in collect_files(extension_dir):
            relative = source.relative_to(extension_dir).as_posix()
            info = zipfile.ZipInfo(f"{extension_id}/{relative}", date_time=ZIP_EPOCH)
            # writestr() with a ZipInfo ignores the archive-level compression=
            # kwarg, so the per-entry value must be set too.
            info.compress_type = zipfile.ZIP_STORED
            # Pinned so a Windows-built archive is byte-identical to a Unix one
            # (create_system otherwise defaults from sys.platform).
            info.create_system = 3
            # Only git's executable bit is meaningful and portable; collapse
            # everything else so a stray umask cannot change the digest. The
            # installer re-applies exec bits via ensure_executable_scripts
            # anyway, but a faithful archive is worth having.
            executable = source.stat().st_mode & 0o111
            info.external_attr = (0o755 if executable else 0o644) << 16
            archive.writestr(info, source.read_bytes())

    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extension_dir", type=Path, help="e.g. extensions/screenshots")
    parser.add_argument(
        "--output", type=Path, default=Path("dist"), help="output directory"
    )
    args = parser.parse_args()

    archive_path = build_extension(args.extension_dir, args.output)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    print(f"{digest}  {archive_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --with pyyaml --with pytest python -m pytest tests/test_build_extension.py -q`

Expected: PASS, 6 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_extension.py tests/test_build_extension.py
git commit -m "feat(scripts): add reproducible first-party extension zip builder"
```

---

### Task 3: `screenshots` extension v0.1.0

The two hand-written `capture.md` variants share the entire command skeleton and
differ only in app mechanics. Split along exactly that seam: a generic command that
is never edited per repo, and a config file that holds everything that varied.

**Files:**
- Create: `extensions/screenshots/extension.yml`
- Create: `extensions/screenshots/commands/capture.md`
- Create: `extensions/screenshots/screenshots-config.yml`
- Create: `extensions/screenshots/examples/aspnet-playwright.yml`
- Create: `extensions/screenshots/examples/tauri-applescript.yml`
- Create: `extensions/screenshots/README.md`
- Create: `extensions/screenshots/CHANGELOG.md`
- Modify: `extensions/catalog.json`

**Interfaces:**
- Consumes: `scripts/build_extension.py` (Task 2); validator hosted-entry support
  (Task 1).
- Produces: command name `speckit.screenshots.capture`, invoked with
  `mode: before` / `mode: after` in `$ARGUMENTS`. Config file deployed at
  `.specify/extensions/screenshots/screenshots-config.yml`. Manifest written to
  `FEATURE_DIR/screenshots/manifest.json` with keys `targets`, `viewports`,
  `baseline`, `notes`, `app`. Tasks 6 and 7 dispatch this command; Task 9's write-up
  documents it.

- [ ] **Step 1: Write the manifest**

Create `extensions/screenshots/extension.yml`:

```yaml
schema_version: "1.0"

extension:
  id: "screenshots"
  name: "UI Screenshots"
  version: "0.1.0"
  description: "Captures before/after UI screenshots for a feature and stages them on the branch for embedding in the pull request"
  author: "clintcparker"
  repository: "https://github.com/clintcparker/speckit-addons"
  license: "MIT"

requires:
  speckit_version: ">=0.1.0"

provides:
  commands:
    - name: "speckit.screenshots.capture"
      file: "commands/capture.md"
      description: "Capture 'before' or 'after' screenshots of the views a feature touches"

  config:
    # The name MUST end in -config.yml. specify-cli only preserves that shape
    # across `extension add --force`; anything else is dropped on install and
    # destroyed on reinstall, which is the whole reason the app profile is a
    # config file rather than an edited command.
    - name: "screenshots-config.yml"
      template: "screenshots-config.yml"
      description: "Per-repo app profile: how to launch, seed, target and capture this app"
      required: false

# No hooks on purpose: this command is invoked explicitly by workflows that want it
# (send-it adds it as two steps around implement). Registering an after_tasks /
# after_implement hook here would make every spec-kit flow pay the screenshot cost.

tags:
  - "process"
  - "qa"
  - "automation"
```

- [ ] **Step 2: Write the generic command**

Create `extensions/screenshots/commands/capture.md`:

````markdown
---
description: Capture before/after UI screenshots for the current feature and stage them on the branch for the pull request.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding. It must name a mode: `before` (baseline, run prior to implementation) or `after` (run once implementation is complete). If neither word is present, stop and report a usage error.

## Purpose

Produce visual evidence that the app runs and the change looks right — a cheap end-to-end smoke test that doubles as PR documentation. Output layout, all under the current feature's directory (`FEATURE_DIR`):

```
FEATURE_DIR/screenshots/
  manifest.json                    # targets, viewports, baseline, app-specific state
  SKIPPED.md                       # written instead of images when the feature has no UI surface
  before/<target-slug>-<viewport>.png
  after/<target-slug>-<viewport>.png
```

Everything here except app state is committed to the feature branch so `speckit.ship.run` can embed the images in the PR description.

## The app profile

This command is generic. Everything that depends on *this* app — how to launch it, how to sign in, where its data lives, what counts as a "view", how a screenshot is actually taken — lives in the profile at:

```
.specify/extensions/screenshots/screenshots-config.yml
```

Read it before step 3 and follow it. Its sections are `ui_surface`, `launch`, `auth`, `data`, `targets`, `viewports`, `capture_method`, and `cleanup`.

**If the profile has `unconfigured: true`**, derive it yourself before continuing: read the repo README, build manifests (`package.json`, `*.csproj`, `Cargo.toml`, `pyproject.toml`, `go.mod`), the app entry point, and any existing e2e/browser config (Playwright, Cypress, Puppeteer, Tauri). Write the profile with your findings, set `unconfigured: false`, record `"profile": "auto-generated"` in the manifest's `notes`, and continue. Do not stop to ask — a repo-agnostic install must be runnable with zero manual steps, and the profile is reviewable after the fact. The `examples/` directory in this extension shows two filled-in profiles.

## Execution Steps

### 1. Locate the feature

Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse `FEATURE_DIR`. All paths must be absolute.

### 2. Decide whether the feature is UI-relevant

- **Mode `before`**: read `FEATURE_DIR/spec.md` (and `plan.md` if present). The feature is UI-relevant iff it changes something a user sees, per the profile's `ui_surface`. If not UI-relevant, write `FEATURE_DIR/screenshots/SKIPPED.md` containing one line explaining why, commit it (`docs: screenshots skipped — <reason>`), and stop successfully.
- **Mode `after`**: if `SKIPPED.md` exists, verify the prediction with
  `git diff --name-only $(git merge-base HEAD <target>)..HEAD -- <ui_surface.paths>`,
  where `<target>` is the target branch named in `$ARGUMENTS` if given, else the profile's default, else the repo's default branch. If the diff is still empty, stop successfully. If implementation touched UI after all, delete `SKIPPED.md` and continue — there will be no baseline, so record `"baseline": "unavailable"` in the manifest and capture `after/` only.

### 3. Prepare data and launch the app

Follow the profile's `data` and `launch` sections, in whichever order the profile specifies — some apps must be seeded before launch, others after.

Two rules hold regardless of profile:

- **App state never lives inside the repo or worktree.** Auto-commit hooks would commit a database, a log, or a lockfile. Keep data directories and server logs on a path outside the checkout.
- **Real user data must survive every run, including a failed one.** If the profile's `data` section describes a backup/restore of a real file, treat the restore like a `trap`: perform it in both modes, on success and on failure, before reporting anything.

Mode `after` reuses the baseline state recorded in the manifest's `app` object so the before/after pair differs only by the UI change. If that state is gone, recreate it by replaying whatever the profile calls the seed procedure, then continue.

If the app fails to build or start, dump the log tail and stop with an error — a non-starting app is itself a finding worth reporting.

### 4. Authenticate

Follow the profile's `auth` section. If it says `none`, skip this step.

### 5. Choose targets

A "target" is whatever the profile's `targets` section says a capturable unit is — a page, a route, a window state, a view. Choose 1–4 from the spec: the ones the feature changes, plus the app's main screen if it is affected. Record each as `{ "slug": ..., "why": ... }`.

Mode `after` **must** reuse the manifest's target list, adding any targets the feature newly created.

### 6. Capture

For each target, capture at every viewport in the profile's `viewports` map. Use the profile's `capture_method`. Filenames: `<target-slug>-<viewport-label>.png` under `before/` or `after/` per mode.

Keep the total payload modest: PNG, viewport- or window-sized, 1–4 targets × the declared viewports.

### 7. Record, commit, clean up

Write/update `FEATURE_DIR/screenshots/manifest.json`:

```json
{
  "targets": [ { "slug": "dashboard", "why": "task list layout changed" } ],
  "viewports": { "mobile": "390x844", "desktop": "1280x900" },
  "baseline": "available",
  "notes": [],
  "app": {}
}
```

- `targets` — the captured units, each with a `slug` and a `why`.
- `viewports` — label → `WxH`, copied from the profile.
- `baseline` — `"available"` or `"unavailable"`.
- `notes` — free-form strings. Record failures here rather than dropping them.
- `app` — free-form, profile-specific state that mode `after` needs in order to
  reproduce mode `before`: a data directory path, a backup flag, seed steps, seed
  records. Its shape is the profile's business, not this command's.

Then clean up per the profile's `cleanup` section, and commit `FEATURE_DIR/screenshots/` with message `docs: <mode> screenshots for <feature>`. Never commit app data, server logs, or anything outside `FEATURE_DIR/screenshots/`.

## Constraints

- This command **never modifies application code**. If the app fails to build or start in mode `after`, that is an implementation defect: report it clearly and stop — do not patch around it.
- The data-protection rules in step 3 are not optional, and a crashed run must still restore real user data before reporting the failure.
- If the profile pins a port and it is occupied, pick another free port and use it consistently everywhere the profile references one (sign-in links and callback URLs are often stamped from it).
````

- [ ] **Step 3: Write the profile template**

Create `extensions/screenshots/screenshots-config.yml`:

```yaml
# Screenshots extension — per-repo app profile.
#
# commands/capture.md is generic and is never edited per repo. Everything that
# depends on *this* app lives here. Spec Kit preserves this file across
# `specify extension add screenshots --force`, so upgrading the extension never
# clobbers your adaptation.
#
# Leave `unconfigured: true` and the command will derive the profile itself on
# first run, write it back here, and note in the manifest that it was
# auto-generated. Filled-in examples for two very different apps live in
# examples/ inside this extension.

unconfigured: true

# Which paths mean "a user can see the difference". Used both to judge
# UI-relevance from the spec and, in after-mode, as the pathspec for the
# `git diff` that verifies a SKIPPED.md prediction.
ui_surface:
  paths: []
  notes: |
    Describe anything the paths above do not capture — for example a backend
    change that alters user-visible strings, or a config file that defines the
    window size.

# How to bring the app up, and how to know it is up.
launch: |
  Command, readiness probe, timeout, and any first-run setup (dependency
  install, cold build). Say how long a cold start may legitimately take.

# How to get past a sign-in screen. Write "none" if there is none.
auth: |
  none

# Where app state lives, how to seed it, how to protect real user data, and how
# after-mode reproduces the before-mode baseline. State must never live inside
# the repo or worktree.
data: |
  Describe the state location, the seed procedure, the backup/restore contract
  for any real user file, and what after-mode should reuse.

# What counts as a capturable unit here, and how to reach one.
targets: |
  Pages, routes, window states, views — and how to navigate to each.

# Label -> WxH. Say in `notes` why these sizes and not others.
viewports:
  mobile: "390x844"
  desktop: "1280x900"

# How a screenshot is actually taken.
capture_method: |
  For example: Playwright viewport screenshots; `screencapture -R x,y,w,h` of a
  window rect read from System Events; a headless renderer.

# How to stop the app and what to restore, in both modes, success or failure.
cleanup: |
  Process-tree caveats, files to restore, directories to delete.
```

- [ ] **Step 4: Write the ASP.NET + Playwright example**

Create `extensions/screenshots/examples/aspnet-playwright.yml`:

```yaml
# Example profile — ASP.NET Razor Pages app captured with Playwright.
# Distilled from homeapp1, the repo this extension was extracted from.
# Copy to .specify/extensions/screenshots/screenshots-config.yml and adapt.

unconfigured: false

ui_surface:
  paths:
    - "src/HomeApp/Pages"
    - "src/HomeApp/wwwroot"
  notes: |
    Razor pages, CSS and images, the action/invite confirm pages, and
    layout/shared partials are UI. Backend-only work — feed .ics internals,
    lifecycle rules, EF migrations, configuration — is not.

launch: |
  Start the server in the background, capturing stdout to a log file OUTSIDE the
  checkout:

      DATA_DIR=<data_dir> \
      APP_BASE_URL=http://localhost:8123 \
      ASPNETCORE_URLS=http://localhost:8123 \
      dotnet run --project src/HomeApp

  Poll `GET http://localhost:8123/healthz` until healthy, timeout ~60s. On
  failure, dump the log tail and stop with an error.

  Port 8123 avoids the dev default 8080. If it is occupied, pick another free
  port and use it for APP_BASE_URL too — sign-in links are stamped from it.

auth: |
  Magic-link flow. With no ACS/SMTP configured the console email fallback logs
  the sign-in link to stdout.

  1. Provision the screenshot user (idempotent; skip in mode `after` if the data
     dir survived):
         dotnet run --project src/HomeApp -- provision shots@example.test \
           --name "Screenshot Bot"
  2. Using the Playwright browser tools, navigate to
     http://localhost:8123/login and submit shots@example.test.
  3. Grep the server log for the most recent sign-in URL and navigate to it. The
     resulting cookie lasts the whole session.

data: |
  A SQLite database under DATA_DIR. NEVER inside the repo or worktree — the git
  auto-commit hooks would commit it.

  Mode `before`: create a fresh directory (`mktemp -d -t homeapp-shots`) and
  record its absolute path in the manifest as `app.data_dir`. Then, through the
  UI, create the minimum data that makes the targets meaningful — typically one
  home, one entity such as an appliance, and one maintenance task, so the
  dashboard and occurrence pages are non-empty. Record each step tersely in
  `app.seed_steps`.

  Mode `after`: reuse `app.data_dir` if it still exists. Startup migrations
  upgrade the schema, and reusing it keeps the data identical so the before/after
  diff shows only the UI change. If it is gone, create a fresh one and replay
  `app.seed_steps`. Then create whatever new data the feature itself introduces
  (a new field, a new page's records) so the change is visible.

  Leave the data dir in place after mode `before`; delete it after mode `after`.

targets: |
  Pages, addressed by route. Choose the pages the feature changes plus the
  dashboard if it is affected. Record `{ "slug": ..., "why": ... }` and keep the
  route in `app.paths` as slug -> path.

viewports:
  mobile: "390x844"
  desktop: "1280x900"

capture_method: |
  Playwright viewport screenshots — not full-page, unless the change is below
  the fold. The app is mobile-first with one breakpoint at 768px, which is why
  the two sizes straddle it.

cleanup: |
  Kill the `dotnet run` process and close the browser tab. Mode `before` leaves
  the data dir for mode `after`; mode `after` deletes it. Never commit the data
  dir or the server log.
```

- [ ] **Step 5: Write the Tauri + AppleScript example**

Create `extensions/screenshots/examples/tauri-applescript.yml`:

```yaml
# Example profile — Tauri desktop app captured with AppleScript + screencapture.
# Distilled from site-checker. Copy to
# .specify/extensions/screenshots/screenshots-config.yml and adapt.

unconfigured: false

ui_surface:
  paths:
    - "src"
    - "index.html"
    - "src-tauri/tauri.conf.json"
  notes: |
    The frontend and the window definition are UI. Backend-only Rust work — HTTP
    classifier internals, store, scheduling, config — is not, UNLESS it changes
    user-visible output such as status `reason` strings or the shape of the
    `site-status` event.

launch: |
  Seed the data file BEFORE launching (see `data`) — the app reads it at startup.

  A fresh worktree has no node_modules: run `pnpm install` first if it is
  missing. Start `pnpm tauri dev` in the background, capturing stdout+stderr to a
  log file OUTSIDE the checkout. The first cold cargo build can take several
  minutes — allow ~10 min before declaring failure.

  Vite is pinned to port 1420 with strictPort; if a stale dev server holds it,
  kill that process first.

  The dev window belongs to process `tauri-app` (bundled builds appear as
  `Site Checker`). Poll System Events until it exists:

      osascript -e 'tell application "System Events" to get position of window 1 of process "tauri-app"'

  Wait a few seconds after launch so Pending resolves to Up/Down before
  capturing — unless the feature is about the Pending state itself. Note the
  choice in the manifest.

auth: |
  none

data: |
  The app reads ~/Library/Application Support/com.clintparker.site-checker/sites.json
  (a bare JSON array) at startup. There is no env override, so seeding means
  touching the user's REAL file. Protect it:

  - If the file exists and no `sites.json.shots-backup` exists beside it, move it
    to `sites.json.shots-backup` and record `app.backup: true` in the manifest.
  - Write the seed file. Use `app.seed_sites` from the manifest if present — mode
    `after` must reproduce the baseline exactly — otherwise pick 2–4 sites that
    exercise the states the feature touches and record them. A dependable
    default:

        [
          { "id": "shots-up",   "url": "https://example.com",  "label": "Example",  "interval_secs": 60 },
          { "id": "shots-down", "url": "https://down.invalid", "label": "Never Up", "interval_secs": 60 }
        ]

    `.invalid` never resolves, so it renders the Down state without waiting on a
    real outage. Checks hit the real network; every site starts Pending on launch
    and results are never persisted.

  Restoring the backup is MANDATORY in both modes, every run, success or
  failure — see `cleanup`.

targets: |
  Single-window app, so "pages" are views/states: the main site list, the empty
  state, the add-site form, an error banner — whatever the spec touches. Reach
  each by driving the app with AppleScript keystrokes/clicks, or by temporarily
  emptying the seed file for the empty state.

viewports:
  default: "720x480"
  narrow: "480x320"

capture_method: |
  Resize with System Events:

      set size of window 1 of process "tauri-app" to {W, H}

  then read `position` and `size` and capture just the window with
  `screencapture -R x,y,w,h <file>` (`-l <windowid>` is fine too if you can get a
  CGWindowID). 720x480 is the shipped size in tauri.conf.json; 480x320 is the
  resizable floor, captured as a layout stress test.

  macOS screen-capture permission must already be granted to the terminal
  running the agent. If `screencapture` produces empty images, report that
  instead of retrying blindly.

cleanup: |
  Kill the `pnpm tauri dev` process TREE — it spawns vite, cargo and the app.
  Kill the process group, then verify no `tauri-app` process survives.

  Restore the user's data: if `sites.json.shots-backup` exists, move it back over
  `sites.json`; otherwise delete the seed `sites.json`. Do this in BOTH modes,
  every run, success or failure. `app.seed_sites` in the manifest is what makes
  the `after` run reproducible — not leftover state.
```

- [ ] **Step 6: Write README and CHANGELOG**

Create `extensions/screenshots/README.md`:

```markdown
# Screenshots

Before/after UI screenshots for a Spec Kit feature, committed to the feature
branch so the ship step can embed them in the pull request.

It is a cheap end-to-end smoke test that doubles as PR documentation: if the app
starts and the pages render, the change is at least alive.

## The seam

`commands/capture.md` is **generic and never edited per repo**. It owns the
before/after mode contract, the UI-relevance decision, the `SKIPPED.md`
self-skip and its after-mode verification, the manifest, filename conventions,
commit rules, and the two constraints that matter most — never modify app code,
and real user data must survive every run including a failed one.

`screenshots-config.yml` owns everything that differs between apps: `ui_surface`,
`launch`, `auth`, `data`, `targets`, `viewports`, `capture_method`, `cleanup`.

Because the profile is a Spec Kit **config file**, it survives
`specify extension add screenshots --force`. Upgrading the extension never
clobbers a repo's adaptation, and because the command body never changes per
repo, the `.claude/skills` copy of it never goes stale either.

> The config file has to be named `screenshots-config.yml`. Spec Kit only
> preserves top-level `*-config.yml` / `*-config.local.yml` files across a
> `--force` reinstall; a differently-named target is dropped on install and
> destroyed on reinstall.

## Bootstrap

A fresh install ships the profile with `unconfigured: true`. On first run the
command derives the profile itself — reading the README, build manifests, entry
points and any existing e2e config — writes it back, flips the flag, and notes
in the manifest that the profile was auto-generated. A repo-agnostic install is
runnable with zero manual steps; review the profile afterwards.

Two filled-in profiles are in [`examples/`](examples/): an ASP.NET Razor Pages
app captured with Playwright, and a Tauri desktop app captured with AppleScript
and `screencapture`.

## Manifest

`FEATURE_DIR/screenshots/manifest.json`:

| Key | Meaning |
|---|---|
| `targets` | Captured units, each `{ "slug", "why" }` |
| `viewports` | Label → `WxH`, copied from the profile |
| `baseline` | `"available"` or `"unavailable"` |
| `notes` | Free-form; failures are recorded here, not dropped |
| `app` | Free-form, profile-specific state `after` needs to reproduce `before` |

## Hooks

None, deliberately. Workflows that want screenshots add the steps explicitly —
`send-it` and `send-it-checked` both do. An `after_tasks` / `after_implement`
hook would make every Spec Kit flow pay the screenshot cost.

## Install

```bash
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5

specify extension add screenshots
```

## License

MIT
```

Create `extensions/screenshots/CHANGELOG.md`:

```markdown
# Changelog

## 0.1.0 (2026-08-05)

### Added
- `speckit.screenshots.capture` command — before/after UI screenshots for the
  current feature, committed to the branch for embedding in the pull request.
- Generic command + per-repo app profile split: `commands/capture.md` is never
  edited per repo; `screenshots-config.yml` holds everything app-specific and
  survives `specify extension add --force`.
- Bootstrap mode — a profile marked `unconfigured: true` is derived by the agent
  on first run, so a fresh install is runnable with no manual steps.
- Example profiles for ASP.NET + Playwright and Tauri + AppleScript.
- Generalized manifest schema: `targets`, `viewports`, `baseline`, `notes`, and
  a free-form `app` object for profile-specific state.

### Notes
- Extracted from the hand-written `capture.md` variants in `homeapp1` and
  `site-checker`, which shared the entire command skeleton and differed only in
  app mechanics.
```

- [ ] **Step 7: Build the zip and capture its digest**

Finish every edit inside `extensions/screenshots/` before this step — the whole
directory is packaged, so a later tweak changes the artifact and invalidates the
digest.

Run:

```bash
uv run --with pyyaml python scripts/build_extension.py extensions/screenshots \
  --output /tmp/speckit-addons-build
```

Expected: one line, `<64-hex>  /tmp/speckit-addons-build/screenshots-0.1.0.zip`.
Record the digest — it goes in the catalog entry in the next step.

- [ ] **Step 8: Add the catalog entry**

In `extensions/catalog.json`, set the top-level `"updated_at"` to
`"2026-08-05T00:00:00Z"` and add this entry inside `"extensions"`, before
`"worktrees"`. Substitute the digest from step 7 for `<SHA256>`.

```json
    "screenshots": {
      "id": "screenshots",
      "name": "UI Screenshots",
      "description": "Before/after UI screenshots for a feature, committed to the branch for embedding in the pull request",
      "author": "clintcparker",
      "version": "0.1.0",
      "download_url": "https://github.com/clintcparker/speckit-addons/releases/download/ext-screenshots-v0.1.0/screenshots-0.1.0.zip",
      "sha256": "<SHA256>",
      "repository": "https://github.com/clintcparker/speckit-addons",
      "homepage": "https://github.com/clintcparker/speckit-addons/tree/main/extensions/screenshots",
      "documentation": "https://github.com/clintcparker/speckit-addons/blob/ext-screenshots-v0.1.0/extensions/screenshots/README.md",
      "changelog": "https://github.com/clintcparker/speckit-addons/blob/ext-screenshots-v0.1.0/extensions/screenshots/CHANGELOG.md",
      "license": "MIT",
      "category": "process",
      "effect": "read-write",
      "requires": {
        "speckit_version": ">=0.1.0"
      },
      "provides": {
        "commands": 1,
        "hooks": 0
      },
      "tags": [
        "process",
        "qa",
        "automation",
        "screenshots"
      ],
      "verified": false,
      "created_at": "2026-08-05T00:00:00Z",
      "updated_at": "2026-08-05T00:00:00Z"
    },
```

- [ ] **Step 9: Validate**

Run: `uv run --with pyyaml python scripts/validate_catalog.py`

Expected: `✓ NN checks passed.`

Run: `uv run --with pyyaml --with pytest python -m pytest tests/ -q`

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add extensions/screenshots extensions/catalog.json
git commit -m "feat(screenshots): add first-party screenshots extension v0.1.0"
```

---

### Task 4: `worktrees` fork v2.0.0

Bring the battle-tested homeapp1 copy into this repo and fix the hook declaration
that has been reverted by every `--force` reinstall.

**Files:**
- Create: `extensions/worktrees/**` (copied, then edited)
- Modify: `extensions/catalog.json`

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: extension id `worktrees` at version `2.0.0`, declaring its
  `speckit.worktrees.create` hook at `before_specify` with priority 20. Config file
  `worktree-config.yml`. Task 9's write-up documents that a stock install now wires
  the worktree-first flow with no hand edits.

> **Note on the config filename.** `worktree-config.yml` already ends in
> `-config.yml`, so it satisfies the preservation convention unchanged. Do not
> rename it — `create-worktree.sh` reads it by that name.

- [ ] **Step 1: Copy the battle-tested source**

```bash
mkdir -p extensions/worktrees
cp -R /Users/clint/src/clintcparker/homeapp1/.specify/extensions/worktrees/. \
      extensions/worktrees/
find extensions/worktrees -name '.DS_Store' -delete
rm -rf extensions/worktrees/.specify-dev
ls -R extensions/worktrees
```

Expected: `CHANGELOG.md`, `LICENSE`, `README.md`, `extension.yml`,
`worktree-config.yml`, `commands/speckit.worktrees.{create,list,clean}.md`,
`scripts/bash/create-worktree.sh`.

- [ ] **Step 2: Confirm the script is executable**

Run: `test -x extensions/worktrees/scripts/bash/create-worktree.sh && echo executable`

Expected: `executable`. If not: `chmod +x extensions/worktrees/scripts/bash/create-worktree.sh`.

- [ ] **Step 3: Bump the version and fix the hook declaration**

In `extensions/worktrees/extension.yml`, change the `version` line:

```yaml
  version: "2.0.0"
```

and replace the whole `hooks:` block:

```yaml
hooks:
  before_specify:
    command: speckit.worktrees.create
    optional: false
    priority: 20
    description: "Create the feature branch inside a new worktree and work there"
```

Upstream declares this at `after_specify`, which spawns the worktree *after* the
spec has already been written into the primary checkout. Declaring it at
`before_specify` with priority 20 puts it after the git extension's branch hook
slot and makes a stock install wire the worktree-first flow correctly — the single
biggest recurring gotcha, because `--force` reinstalls reverted the hand edit every
time.

- [ ] **Step 4: Record the fork's lineage in the CHANGELOG**

Prepend to `extensions/worktrees/CHANGELOG.md`, directly under `# Changelog`:

```markdown

## 2.0.0 (2026-08-05)

Fork of [dango85/spec-kit-worktree-parallel](https://github.com/dango85/spec-kit-worktree-parallel)
**v1.0.0**, now published from
[clintcparker/speckit-addons](https://github.com/clintcparker/speckit-addons).

Upstream **1.3.2 is not merged**. It was read and rejected for this baseline: it
carries only partial `base_ref` support in the script, none of the other patches
below, plus tests and a post-install step that have never run here. Rebasing
these patches onto 1.3.2 remains possible later. The version is 2.0.0 purely so
catalog update logic moves forward from 1.3.2 — it does not imply 1.3.2 is
contained.

### Changed
- **The `speckit.worktrees.create` hook is declared at `before_specify`
  (priority 20)** instead of upstream's `after_specify`. A stock install now
  wires the worktree-first flow correctly, and `--force` reinstalls no longer
  revert a hand edit.

### Added (carried from local patches, not in upstream 1.0.0)
- `--from-description` — derive the branch name from the feature description by
  delegating to the git extension's `create-new-feature-branch.sh --dry-run`,
  so the `before_specify` hook can create the branch before a spec exists.
- `enter_worktree` config key — move the agent session into the new worktree so
  the spec and every later phase is written there rather than in the primary
  checkout.
- `base_ref` config key — the ref new feature branches fork from, auto-detected
  as `origin/main` → `main` → `origin/master` → `master` → `HEAD` when empty.
  Under the worktree-first flow the branch is created by `git worktree add -b`,
  so this — not the primary's HEAD — decides what a feature forks from.
- Worktree-first flow throughout the `speckit.worktrees.create` command.
```

- [ ] **Step 5: Note the fork at the top of the README**

Insert immediately after the first line (`# spec-kit-worktree-parallel`) of
`extensions/worktrees/README.md`:

```markdown

> **This is a fork.** Published from
> [clintcparker/speckit-addons](https://github.com/clintcparker/speckit-addons)
> as `worktrees` v2.0.0 — dango85 v1.0.0 plus `--from-description`,
> `enter_worktree`, `base_ref`, the worktree-first flow, and a `before_specify`
> hook declaration. Upstream v1.3.2 is not merged; see
> [CHANGELOG.md](CHANGELOG.md). Original MIT license retained in
> [LICENSE](LICENSE).
```

Then replace the install command under `## Installation`:

```bash
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5

specify extension add worktrees
```

- [ ] **Step 6: Build the zip and capture its digest**

```bash
uv run --with pyyaml python scripts/build_extension.py extensions/worktrees \
  --output /tmp/speckit-addons-build
```

Expected: `<64-hex>  /tmp/speckit-addons-build/worktrees-2.0.0.zip`.

- [ ] **Step 7: Repoint the catalog entry**

Replace the existing `"worktrees"` entry in `extensions/catalog.json` wholesale.
Substitute the digest from step 6 for `<SHA256>`.

```json
    "worktrees": {
      "id": "worktrees",
      "name": "Worktrees",
      "description": "Default-on worktree isolation for parallel agents — worktree-first flow, sibling or nested layout",
      "author": "clintcparker",
      "version": "2.0.0",
      "download_url": "https://github.com/clintcparker/speckit-addons/releases/download/ext-worktrees-v2.0.0/worktrees-2.0.0.zip",
      "sha256": "<SHA256>",
      "repository": "https://github.com/clintcparker/speckit-addons",
      "homepage": "https://github.com/clintcparker/speckit-addons/tree/main/extensions/worktrees",
      "documentation": "https://github.com/clintcparker/speckit-addons/blob/ext-worktrees-v2.0.0/extensions/worktrees/README.md",
      "changelog": "https://github.com/clintcparker/speckit-addons/blob/ext-worktrees-v2.0.0/extensions/worktrees/CHANGELOG.md",
      "license": "MIT",
      "category": "process",
      "effect": "read-write",
      "requires": {
        "speckit_version": ">=0.4.0"
      },
      "provides": {
        "commands": 3,
        "hooks": 1
      },
      "tags": [
        "worktree",
        "git",
        "parallel",
        "isolation",
        "agents"
      ],
      "verified": false,
      "created_at": "2026-07-30T00:00:00Z",
      "updated_at": "2026-08-05T00:00:00Z"
    },
```

- [ ] **Step 8: Validate**

Run: `uv run --with pyyaml python scripts/validate_catalog.py`

Expected: `✓ NN checks passed.`

- [ ] **Step 9: Commit**

```bash
git add extensions/worktrees extensions/catalog.json
git commit -m "feat(worktrees): fork dango85 v1.0.0 as first-party worktrees v2.0.0"
```

---

### Task 5: `git` fork v1.1.0

Spec Kit's bundled `git` extension creates the feature branch in the primary
checkout and ignores `branch_numbering: timestamp` when the worktrees hook calls it
without flags. Both had to be hand-fixed after every reinstall. Fork it.

**Files:**
- Create: `extensions/git/**` (copied from the bundled core pack, then edited)
- Modify: `extensions/catalog.json`

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: extension id `git` at version `1.1.0`, **not** declaring a
  `before_specify` hook, with `config-template.yml` defaulting
  `branch_numbering: timestamp`. Installed with `--from`, not by id — see Finding 2.
  Task 9's write-up and Task 10's READMEs document that install command.

- [ ] **Step 1: Copy the bundled baseline**

The baseline is spec-kit-core's bundled v1.0.0, not homeapp1's working copy — the
two differ only by the patches applied below, and starting from the pristine copy
keeps the fork's delta auditable.

```bash
BUNDLED=~/.local/share/uv/tools/specify-cli/lib/python3.12/site-packages/specify_cli/core_pack/extensions/git
mkdir -p extensions/git
cp -R "$BUNDLED"/. extensions/git/
find extensions/git -name '.DS_Store' -delete
rm -f extensions/git/git-config.yml
ls -R extensions/git
```

`git-config.yml` is the *deployed* config, not a shipped file — Spec Kit writes it
from `config-template.yml` at install time. It must not be in the fork.

Expected tree: `README.md`, `extension.yml`, `config-template.yml`,
`commands/speckit.git.{feature,validate,remote,initialize,commit}.md`,
`scripts/bash/{create-new-feature-branch,auto-commit,git-common,initialize-repo}.sh`,
`scripts/powershell/*.ps1`, `scripts/python/*.py`.

- [ ] **Step 2: Verify the copy matches the patched working copy except for the known deltas**

```bash
diff -ru extensions/git \
  /Users/clint/src/clintcparker/homeapp1/.specify/extensions/git \
  --exclude=git-config.yml
```

Expected: exactly three diffs, all of them the numbering patch about to be applied
in step 3 — in `scripts/bash/create-new-feature-branch.sh`,
`scripts/powershell/create-new-feature-branch.ps1`, and
`scripts/python/create_new_feature_branch.py`. Anything else means the baseline
drifted and must be investigated before continuing.

- [ ] **Step 3: Apply the numbering patch to all three script flavors**

In `extensions/git/scripts/bash/create-new-feature-branch.sh`, immediately after
`validate_branch_template "$BRANCH_TEMPLATE"` (around line 439), insert:

```bash

# Honor git-config.yml branch_numbering when the caller didn't decide explicitly:
# the worktrees hook calls this script without --timestamp, so the config value
# would otherwise be dead. An explicit --number N still forces sequential.
if [ "$USE_TIMESTAMP" != true ] && [ -z "$BRANCH_NUMBER" ] && \
   [ "$(read_git_config_value branch_numbering)" = "timestamp" ]; then
    USE_TIMESTAMP=true
fi
```

In `extensions/git/scripts/powershell/create-new-feature-branch.ps1`, immediately
after `Assert-BranchTemplateValid -Template $branchTemplate` (around line 402),
insert:

```powershell

# Honor git-config.yml branch_numbering when the caller didn't decide explicitly:
# the worktrees hook calls this script without -Timestamp, so the config value
# would otherwise be dead. An explicit -Number still forces sequential.
if (-not $Timestamp -and -not $PSBoundParameters.ContainsKey('Number') -and
    (Read-GitConfigValue -Key 'branch_numbering') -eq 'timestamp') {
    $Timestamp = $true
}
```

In `extensions/git/scripts/python/create_new_feature_branch.py`, immediately after
`validate_branch_template(branch_template)` (around line 474), insert:

```python

    # Honor git-config.yml branch_numbering when the caller didn't decide
    # explicitly: the worktrees hook calls this script without --timestamp, so
    # the config value would otherwise be dead. An explicit --number N still
    # forces sequential.
    if (
        not args.use_timestamp
        and not args.branch_number
        and read_git_config_value(config_file, "branch_numbering") == "timestamp"
    ):
        args.use_timestamp = True
```

- [ ] **Step 4: Verify the patch landed identically to the working copy**

```bash
diff -ru extensions/git \
  /Users/clint/src/clintcparker/homeapp1/.specify/extensions/git \
  --exclude=git-config.yml
```

Expected: no output. The fork's scripts now match the battle-tested copy exactly.

- [ ] **Step 5: Default the shipped template to timestamp numbering**

In `extensions/git/config-template.yml`, change:

```yaml
# Branch numbering strategy: "sequential" (001, 002, ...) or "timestamp" (YYYYMMDD-HHMMSS)
#
# Defaults to timestamp in this fork: parallel worktrees each compute "the next
# sequential number" independently, from the same specs/ directory and the same
# refs, so two features specified at once collide on 007. Timestamps do not.
branch_numbering: timestamp
```

- [ ] **Step 6: Bump the version and drop the `before_specify` hook**

In `extensions/git/extension.yml`, change:

```yaml
  version: "1.1.0"
  author: clintcparker
  repository: https://github.com/clintcparker/speckit-addons
```

and delete these four lines from the `hooks:` block:

```yaml
  before_specify:
    command: speckit.git.feature
    optional: false
    description: "Create feature branch before specification"
```

The `worktrees` extension creates the branch — inside the worktree — at
`before_specify` priority 20. Leaving the stock hook declared means both fire, so
the branch gets created twice and the second attempt lands in the primary checkout.
It had to be hand-disabled in `.specify/extensions.yml` after every reinstall. Every
other hook (auto-commit before/after each phase, `before_constitution` initialize)
keeps upstream behavior.

- [ ] **Step 7: Note the fork in the README**

Insert immediately after the first heading line of `extensions/git/README.md`:

```markdown

> **This is a fork** of the `git` extension bundled with
> [github/spec-kit](https://github.com/github/spec-kit), published from
> [clintcparker/speckit-addons](https://github.com/clintcparker/speckit-addons)
> as v1.1.0. Two deltas: `branch_numbering: timestamp` is honored when the caller
> passes no flag (so the worktrees hook gets it), and the `before_specify` hook is
> not declared (the worktrees extension creates the branch).
>
> **Install with `--from`, not by id.** `specify extension add git` resolves
> bundled extensions before it ever reads a catalog, so it always installs
> upstream's copy no matter what catalog priority you set:
>
> ```bash
> specify extension add git --force --from \
>   https://github.com/clintcparker/speckit-addons/releases/download/ext-git-v1.1.0/git-1.1.0.zip
> ```
>
> `--from` does not verify a digest. Check it yourself against the `sha256` in
> [extensions/catalog.json](../catalog.json):
>
> ```bash
> curl -sL <url> | shasum -a 256
> ```
```

- [ ] **Step 8: Add a CHANGELOG**

Create `extensions/git/CHANGELOG.md`:

```markdown
# Changelog

## 1.1.0 (2026-08-05)

Fork of the `git` extension bundled with
[github/spec-kit](https://github.com/github/spec-kit) at v1.0.0, published from
[clintcparker/speckit-addons](https://github.com/clintcparker/speckit-addons).

### Changed
- `create-new-feature-branch.{sh,ps1,py}` now honor `branch_numbering: timestamp`
  from `git-config.yml` when the caller passes no explicit flag. The worktrees
  hook calls the script without `--timestamp`, so the config value was
  previously dead. An explicit `--number N` still forces sequential numbering.
- `config-template.yml` ships `branch_numbering: timestamp` by default. Parallel
  worktrees each compute "the next sequential number" independently from the same
  `specs/` directory and refs, so two features specified at once collide.
- The `before_specify` → `speckit.git.feature` hook is **no longer declared**.
  The `worktrees` extension creates the feature branch inside the worktree; with
  both declared the branch is created twice and the second attempt lands in the
  primary checkout. Previously this had to be disabled by hand in
  `.specify/extensions.yml` after every reinstall.

### Unchanged
- All other hooks (auto-commit before/after each phase, `before_constitution`
  repository initialization) keep upstream behavior.
- All five commands, and the `speckit.git.feature` command itself — it is still
  installed and still callable directly, just not hooked.
```

- [ ] **Step 9: Build the zip and capture its digest**

```bash
uv run --with pyyaml python scripts/build_extension.py extensions/git \
  --output /tmp/speckit-addons-build
```

Expected: `<64-hex>  /tmp/speckit-addons-build/git-1.1.0.zip`.

- [ ] **Step 10: Add the catalog entry**

Add to `extensions/catalog.json` inside `"extensions"`, after `"worktrees"`.
Substitute the digest from step 9 for `<SHA256>`.

```json
    "git": {
      "id": "git",
      "name": "Git Branching Workflow (worktree-safe fork)",
      "description": "Fork of spec-kit's bundled git extension: honors branch_numbering: timestamp for hook callers and leaves branch creation to the worktrees extension. Install with --from; `specify extension add git` resolves the bundled copy first.",
      "author": "clintcparker",
      "version": "1.1.0",
      "download_url": "https://github.com/clintcparker/speckit-addons/releases/download/ext-git-v1.1.0/git-1.1.0.zip",
      "sha256": "<SHA256>",
      "repository": "https://github.com/clintcparker/speckit-addons",
      "homepage": "https://github.com/clintcparker/speckit-addons/tree/main/extensions/git",
      "documentation": "https://github.com/clintcparker/speckit-addons/blob/ext-git-v1.1.0/extensions/git/README.md",
      "changelog": "https://github.com/clintcparker/speckit-addons/blob/ext-git-v1.1.0/extensions/git/CHANGELOG.md",
      "license": "MIT",
      "category": "process",
      "effect": "read-write",
      "requires": {
        "speckit_version": ">=0.2.0"
      },
      "provides": {
        "commands": 5,
        "hooks": 17
      },
      "tags": [
        "git",
        "branching",
        "workflow",
        "worktree"
      ],
      "verified": false,
      "created_at": "2026-08-05T00:00:00Z",
      "updated_at": "2026-08-05T00:00:00Z"
    },
```

- [ ] **Step 11: Validate**

Run: `uv run --with pyyaml python scripts/validate_catalog.py`

Expected: `✓ NN checks passed.`

- [ ] **Step 12: Commit**

```bash
git add extensions/git extensions/catalog.json
git commit -m "feat(git): fork spec-kit's bundled git extension as v1.1.0"
```

---

### Task 6: `send-it` 0.2.0

Publish homeapp1's working workflow, generalized so the ship step stops asserting
that the repository is private.

**Files:**
- Modify: `workflows/send-it/workflow.yml`
- Modify: `workflows/send-it/README.md`
- Modify: `workflows/send-it/CHANGELOG.md`
- Modify: `workflows/catalog.json`

**Interfaces:**
- Consumes: `speckit.screenshots.capture` from Task 3.
- Produces: workflow `send-it` v0.2.0 with steps
  `specify → plan → tasks → screenshots-before → implement → screenshots-after → ship`.
  Task 7 grafts the same two steps into `send-it-checked`; Task 9 documents the flow.

> **Finding 3 applies here.** `requires` accepts only `speckit_version` and
> `integrations`; any other key is a hard validation error. The `screenshots`
> dependency is expressed in the `description`, the README, and the catalog
> `description` only.

- [ ] **Step 1: Rewrite the workflow**

Replace `workflows/send-it/workflow.yml` entirely:

```yaml
schema_version: "1.0"
workflow:
  id: "send-it"
  name: "Spec to PR, unattended"
  version: "0.2.0"
  author: "clintcparker"
  description: "specify → plan → tasks → screenshots → implement → screenshots → ship; no gates, ends in an open PR with before/after UI screenshots. Requires the `screenshots` and `ship` extensions."

requires:
  # Same floor as yolo: 0.8.12 is the first release with engine-side resolution
  # of ``integration: "auto"`` (spec-kit #2421). Older versions treat "auto" as
  # a literal integration key and fail at dispatch.
  #
  # The `screenshots` extension is a hard dependency -- the two capture steps
  # fail at dispatch without it -- but it cannot be declared here: `requires`
  # recognizes only speckit_version and integrations, and an unknown key is a
  # validation error. See this workflow's README.
  speckit_version: ">=0.8.12"
  integrations:
    # Advisory compatibility hint, not a closed set -- see workflows/yolo.
    any:
      - "claude"

inputs:
  spec:
    type: string
    required: true
    prompt: "Describe what you want to build"
  integration:
    type: string
    default: "auto"
    prompt: "Integration to use (e.g. claude, copilot, gemini; 'auto' uses the project's initialized integration)"
  target_branch:
    type: string
    default: "main"
    prompt: "Branch the pull request should target"

steps:
  # The before_specify hook (speckit.worktrees.create) creates the feature branch
  # inside a new worktree and moves the session into it, leaving the primary checkout
  # untouched on its current branch. Every step below therefore runs *in the worktree*
  # — they are the same agent session, so the working directory carries forward. Do
  # not add a step that assumes the primary checkout is on the feature branch.
  - id: specify
    command: speckit.specify
    integration: "{{ inputs.integration }}"
    input:
      args: "{{ inputs.spec }}"

  - id: plan
    command: speckit.plan
    integration: "{{ inputs.integration }}"
    input:
      args: "{{ inputs.spec }}"

  - id: tasks
    command: speckit.tasks
    integration: "{{ inputs.integration }}"
    input:
      args: "{{ inputs.spec }}"

  # Baseline screenshots MUST run before implement: at this point the worktree
  # differs from the target branch only by spec documents, so the app still
  # renders exactly what the PR's base commit would. The command self-skips
  # (writing screenshots/SKIPPED.md) when the spec has no UI surface.
  # Provided by the `screenshots` extension.
  - id: screenshots-before
    command: speckit.screenshots.capture
    integration: "{{ inputs.integration }}"
    input:
      args: >-
        mode: before. Target branch: {{ inputs.target_branch }}.

        UNATTENDED RUN — no user is present. Make every judgement call
        (UI-relevance, which targets, what seed data) yourself and record it in
        the manifest instead of asking. If the app profile is still
        unconfigured, derive it and write it back rather than stopping. A
        failure to build or start the app here means the *base* branch is
        broken: report it and continue the workflow without baseline
        screenshots rather than aborting.

  - id: implement
    command: speckit.implement
    integration: "{{ inputs.integration }}"
    input:
      args: "{{ inputs.spec }}"

  - id: screenshots-after
    command: speckit.screenshots.capture
    integration: "{{ inputs.integration }}"
    input:
      args: >-
        mode: after. Target branch: {{ inputs.target_branch }}.

        UNATTENDED RUN — no user is present. Reuse the manifest written by the
        before pass (same targets, same viewports, same app state if it
        survived) so the pair is comparable. If the app no longer builds or
        starts, that is an implementation defect: capture nothing, write the
        failure into the manifest notes, and let the workflow continue so ship
        can surface it in the pull request instead of silently dropping it.

  # speckit.ship.run is provided by the `ship` extension, not by core Spec Kit.
  # Its command reads $ARGUMENTS before anything else ("You MUST consider the
  # user input before proceeding"), which is the designed lever for turning a
  # safe-by-default interactive command into an unattended one.
  - id: ship
    command: speckit.ship.run
    integration: "{{ inputs.integration }}"
    input:
      args: >-
        Target branch: {{ inputs.target_branch }}.

        UNATTENDED RUN — no user is present and no prompt can be answered.
        Treat every confirmation this command would normally ask as answered
        YES and continue without waiting: the readiness summary, the
        rebase/merge confirmation, the push confirmation, the CHANGELOG
        prepend confirmation, and the pull request creation confirmation.

        Before the working-tree pre-flight check, commit every uncommitted
        change with a descriptive conventional-commit message instead of
        prompting to commit or stash.

        If any tasks in tasks.md are still incomplete, do not stop — proceed
        and list the incomplete tasks in the pull request description.

        Prefer rebase over merge when synchronizing with the target branch.

        Do not block on CI. If gh is unavailable, if no CI run exists yet for
        the branch, or if a run is still in progress, proceed and record the
        CI status in the pull request description rather than waiting. If CI
        has already failed, still open the pull request and call the failure
        out prominently in the description.

        The one legitimate stop is a rebase conflict that cannot be resolved
        trivially: leave the branch as it is for manual resolution and report
        what happened. Never force-push.

        SCREENSHOTS SECTION — after pushing the branch and before creating the
        pull request, check FEATURE_DIR/screenshots/. If it contains images,
        add a "## Screenshots" section to the PR description: one markdown
        table per captured target with Before and After columns, one row per
        viewport.

        Read repository visibility with
        `gh repo view --json visibility,nameWithOwner`. When the repository is
        PRIVATE, raw.githubusercontent.com URLs do NOT render for reviewers —
        embed each image as
        https://github.com/{owner}/{repo}/blob/{head_sha}/{path}?raw=true.
        When it is PUBLIC, either form renders; prefer
        https://raw.githubusercontent.com/{owner}/{repo}/{head_sha}/{path}.
        If gh cannot report visibility, assume PRIVATE and use the blob form —
        it renders in both cases.

        Always pin the pushed head commit SHA, never the branch name, which
        dies when the branch is deleted after merge. If a side is missing (no
        baseline, or the after pass recorded a failure in the manifest notes),
        say so in that table cell and surface any manifest failure notes
        prominently at the top of the section. If screenshots/SKIPPED.md exists
        instead, add the single line "No UI changes — screenshots skipped."
        Verify the screenshot commits are actually part of the pushed head
        before linking.
```

- [ ] **Step 2: Update the CHANGELOG**

Prepend to `workflows/send-it/CHANGELOG.md`, directly under `# Changelog`:

```markdown

## 0.2.0 (2026-08-05)

### Added
- `screenshots-before` step between `tasks` and `implement`, and
  `screenshots-after` step between `implement` and `ship`. Both dispatch
  `speckit.screenshots.capture` from the `screenshots` extension, which
  self-skips when the feature has no UI surface.
- A SCREENSHOTS SECTION brief in the ship step: the pull request gets one
  before/after table per captured target, with images pinned to the pushed head
  commit SHA.
- Comments documenting the worktree session model — every step after the
  `before_specify` worktree hook runs inside the worktree, not the primary
  checkout.

### Changed
- The ship step now **detects** repository visibility with
  `gh repo view --json visibility` instead of asserting the repository is
  private. Private repos get `blob/{sha}?raw=true` embeds (raw URLs do not
  render for reviewers); public repos get raw URLs. When `gh` cannot answer, it
  assumes private, which renders in both cases.

### Requires
- The [`screenshots`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/screenshots)
  extension. Both capture steps fail at dispatch without it. Spec Kit's workflow
  schema has no machine-readable extension requirement — `requires` accepts only
  `speckit_version` and `integrations` — so this is a documentation-only
  contract.
```

- [ ] **Step 3: Update the README**

In `workflows/send-it/README.md`, add a `## Requires` section immediately after the
intro paragraph, before whatever section currently follows it:

```markdown
## Requires

| Extension | Why |
|---|---|
| [`ship`](https://github.com/arunt14/spec-kit-ship) | The `ship` step dispatches `speckit.ship.run` |
| [`screenshots`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/screenshots) | The two capture steps dispatch `speckit.screenshots.capture` |

Both are hard dependencies: a missing extension means the step fails at dispatch.
Spec Kit's workflow schema cannot declare this — `requires` accepts only
`speckit_version` and `integrations` — so install them first:

```bash
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5
specify extension add ship screenshots
```

The worktree-first flow this workflow assumes additionally wants the `worktrees`
and `git` extensions — see [docs/send-it-harness.md](../../docs/send-it-harness.md).
```

Then update the step list wherever the README enumerates the steps, so it reads
`specify → plan → tasks → screenshots (before) → implement → screenshots (after) → ship`.

- [ ] **Step 4: Update the catalog entry**

In `workflows/catalog.json`, set the top-level `"updated_at"` to
`"2026-08-05T00:00:00Z"` and update the `"send-it"` entry's fields:

```json
      "description": "specify → plan → tasks → screenshots → implement → screenshots → ship; no gates, ends in an open PR with before/after UI screenshots. Requires the `screenshots` and `ship` extensions.",
      "version": "0.2.0",
      "url": "https://raw.githubusercontent.com/clintcparker/speckit-addons/send-it-v0.2.0/workflows/send-it/workflow.yml",
      "documentation": "https://github.com/clintcparker/speckit-addons/blob/send-it-v0.2.0/workflows/send-it/README.md",
      "changelog": "https://github.com/clintcparker/speckit-addons/blob/send-it-v0.2.0/workflows/send-it/CHANGELOG.md",
```

and add `"screenshots"` to that entry's `"tags"` array, and set its
`"updated_at"` to `"2026-08-05T00:00:00Z"`.

- [ ] **Step 5: Validate**

Run: `uv run --with pyyaml python scripts/validate_catalog.py`

Expected: `✓ NN checks passed.`

Confirm the workflow parses and its `requires` keys are legal:

```bash
uv run --with pyyaml python -c "
import yaml, pathlib
d = yaml.safe_load(pathlib.Path('workflows/send-it/workflow.yml').read_text())
assert d['workflow']['version'] == '0.2.0'
assert set(d['requires']) <= {'speckit_version', 'integrations'}, d['requires']
print([s['id'] for s in d['steps']])
"
```

Expected: `['specify', 'plan', 'tasks', 'screenshots-before', 'implement', 'screenshots-after', 'ship']`

- [ ] **Step 6: Commit**

```bash
git add workflows/send-it workflows/catalog.json
git commit -m "feat(send-it): 0.2.0 — screenshot steps and visibility detection"
```

---

### Task 7: `send-it-checked` 0.2.0

Same two steps, but `screenshots-after` goes after `qa` rather than right after
`implement` — review and QA each get a fix-and-re-run pass, and the captured
screenshots must match what actually ships.

**Files:**
- Modify: `workflows/send-it-checked/workflow.yml`
- Modify: `workflows/send-it-checked/README.md`
- Modify: `workflows/send-it-checked/CHANGELOG.md`
- Modify: `workflows/catalog.json`

**Interfaces:**
- Consumes: `speckit.screenshots.capture` (Task 3); the step bodies authored in
  Task 6.
- Produces: workflow `send-it-checked` v0.2.0 with steps
  `specify → plan → tasks → screenshots-before → implement → review → qa → screenshots-after → ship`.

- [ ] **Step 1: Bump the version and description**

In `workflows/send-it-checked/workflow.yml`, change the `workflow:` block's
`version` and `description`:

```yaml
  version: "0.2.0"
  author: "clintcparker"
  description: "send-it plus staff review and QA, each with one fix-and-re-run pass, before shipping — with before/after UI screenshots. Requires the `screenshots`, `ship`, `staff-review` and `qa` extensions."
```

and extend the `requires` comment to match send-it's:

```yaml
requires:
  # Same floor as yolo and send-it: engine-side ``integration: "auto"``.
  #
  # The `screenshots` extension is a hard dependency -- the two capture steps
  # fail at dispatch without it -- but it cannot be declared here: `requires`
  # recognizes only speckit_version and integrations, and an unknown key is a
  # validation error. See this workflow's README.
  speckit_version: ">=0.8.12"
```

- [ ] **Step 2: Insert `screenshots-before` between `tasks` and `implement`**

In `workflows/send-it-checked/workflow.yml`, insert immediately after the `tasks`
step and before the `implement` step:

```yaml
  # Baseline screenshots MUST run before implement: at this point the worktree
  # differs from the target branch only by spec documents, so the app still
  # renders exactly what the PR's base commit would. The command self-skips
  # (writing screenshots/SKIPPED.md) when the spec has no UI surface.
  # Provided by the `screenshots` extension.
  - id: screenshots-before
    command: speckit.screenshots.capture
    integration: "{{ inputs.integration }}"
    input:
      args: >-
        mode: before. Target branch: {{ inputs.target_branch }}.

        UNATTENDED RUN — no user is present. Make every judgement call
        (UI-relevance, which targets, what seed data) yourself and record it in
        the manifest instead of asking. If the app profile is still
        unconfigured, derive it and write it back rather than stopping. A
        failure to build or start the app here means the *base* branch is
        broken: report it and continue the workflow without baseline
        screenshots rather than aborting.
```

- [ ] **Step 3: Insert `screenshots-after` between `qa` and `ship`**

Insert immediately after the `qa` step and before the `ship` step:

```yaml
  # After qa, not after implement: review and qa each get one fix-and-re-run
  # pass, so the tree at this point is the tree that ships. Capturing right
  # after implement would document a state the pull request never contains.
  - id: screenshots-after
    command: speckit.screenshots.capture
    integration: "{{ inputs.integration }}"
    input:
      args: >-
        mode: after. Target branch: {{ inputs.target_branch }}.

        UNATTENDED RUN — no user is present. Reuse the manifest written by the
        before pass (same targets, same viewports, same app state if it
        survived) so the pair is comparable. If the app no longer builds or
        starts, that is an implementation defect: capture nothing, write the
        failure into the manifest notes, and let the workflow continue so ship
        can surface it in the pull request instead of silently dropping it.
```

- [ ] **Step 4: Add the SCREENSHOTS SECTION brief to the ship step**

Append to the end of the `ship` step's `args` block in
`workflows/send-it-checked/workflow.yml`, after the "Never force-push." line,
keeping the same indentation:

```yaml

        SCREENSHOTS SECTION — after pushing the branch and before creating the
        pull request, check FEATURE_DIR/screenshots/. If it contains images,
        add a "## Screenshots" section to the PR description: one markdown
        table per captured target with Before and After columns, one row per
        viewport.

        Read repository visibility with
        `gh repo view --json visibility,nameWithOwner`. When the repository is
        PRIVATE, raw.githubusercontent.com URLs do NOT render for reviewers —
        embed each image as
        https://github.com/{owner}/{repo}/blob/{head_sha}/{path}?raw=true.
        When it is PUBLIC, either form renders; prefer
        https://raw.githubusercontent.com/{owner}/{repo}/{head_sha}/{path}.
        If gh cannot report visibility, assume PRIVATE and use the blob form —
        it renders in both cases.

        Always pin the pushed head commit SHA, never the branch name, which
        dies when the branch is deleted after merge. If a side is missing (no
        baseline, or the after pass recorded a failure in the manifest notes),
        say so in that table cell and surface any manifest failure notes
        prominently at the top of the section. If screenshots/SKIPPED.md exists
        instead, add the single line "No UI changes — screenshots skipped."
        Verify the screenshot commits are actually part of the pushed head
        before linking.
```

- [ ] **Step 5: Update the CHANGELOG**

Prepend to `workflows/send-it-checked/CHANGELOG.md`, directly under `# Changelog`:

```markdown

## 0.2.0 (2026-08-05)

### Added
- `screenshots-before` step between `tasks` and `implement`, and
  `screenshots-after` step between `qa` and `ship`. Both dispatch
  `speckit.screenshots.capture` from the `screenshots` extension, which
  self-skips when the feature has no UI surface.
- A SCREENSHOTS SECTION brief in the ship step, with repository-visibility
  detection so image embeds render in private and public repositories alike.

### Notes
- `screenshots-after` deliberately runs **after `qa`**, not right after
  `implement`. Review and QA each get one fix-and-re-run pass; capturing before
  those passes would document a state the pull request never contains.

### Requires
- The [`screenshots`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/screenshots)
  extension. Both capture steps fail at dispatch without it. Spec Kit's workflow
  schema has no machine-readable extension requirement, so this is a
  documentation-only contract.
```

- [ ] **Step 6: Update the README**

In `workflows/send-it-checked/README.md`, add a `## Requires` section immediately
after the intro paragraph:

```markdown
## Requires

| Extension | Why |
|---|---|
| [`ship`](https://github.com/arunt14/spec-kit-ship) | The `ship` step dispatches `speckit.ship.run` |
| [`staff-review`](https://github.com/arunt14/spec-kit-staff-review) | The `review` step dispatches `speckit.staff-review.run` |
| [`qa`](https://github.com/arunt14/spec-kit-qa) | The `qa` step dispatches `speckit.qa.run` |
| [`screenshots`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/screenshots) | The two capture steps dispatch `speckit.screenshots.capture` |

All four are hard dependencies: a missing extension means the step fails at
dispatch. Spec Kit's workflow schema cannot declare this — `requires` accepts
only `speckit_version` and `integrations` — so install them first:

```bash
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5
specify extension add ship staff-review qa screenshots
```

The worktree-first flow this workflow assumes additionally wants the `worktrees`
and `git` extensions — see [docs/send-it-harness.md](../../docs/send-it-harness.md).
```

Then update the step list wherever the README enumerates the steps.

- [ ] **Step 7: Update the catalog entry**

In `workflows/catalog.json`, update the `"send-it-checked"` entry:

```json
      "description": "send-it plus staff review and QA, each with one fix-and-re-run pass, before shipping — with before/after UI screenshots. Requires the `screenshots`, `ship`, `staff-review` and `qa` extensions.",
      "version": "0.2.0",
      "url": "https://raw.githubusercontent.com/clintcparker/speckit-addons/send-it-checked-v0.2.0/workflows/send-it-checked/workflow.yml",
      "documentation": "https://github.com/clintcparker/speckit-addons/blob/send-it-checked-v0.2.0/workflows/send-it-checked/README.md",
      "changelog": "https://github.com/clintcparker/speckit-addons/blob/send-it-checked-v0.2.0/workflows/send-it-checked/CHANGELOG.md",
```

add `"screenshots"` to its `"tags"`, and set its `"updated_at"` to
`"2026-08-05T00:00:00Z"`.

- [ ] **Step 8: Validate**

Run: `uv run --with pyyaml python scripts/validate_catalog.py`

Expected: `✓ NN checks passed.`

Confirm step order:

```bash
uv run --with pyyaml python -c "
import yaml, pathlib
d = yaml.safe_load(pathlib.Path('workflows/send-it-checked/workflow.yml').read_text())
assert d['workflow']['version'] == '0.2.0'
assert set(d['requires']) <= {'speckit_version', 'integrations'}, d['requires']
print([s['id'] for s in d['steps']])
"
```

Expected: `['specify', 'plan', 'tasks', 'screenshots-before', 'implement', 'review', 'qa', 'screenshots-after', 'ship']`

- [ ] **Step 9: Commit**

```bash
git add workflows/send-it-checked workflows/catalog.json
git commit -m "feat(send-it-checked): 0.2.0 — screenshot steps around review and QA"
```

---

### Task 8: The scaffolding write-up

Deliverable #1 from the session handoff: what the harness is, how the pieces
compose, how to reproduce it in a new repo, and every gotcha that cost time.

**Files:**
- Create: `docs/send-it-harness.md`

**Interfaces:**
- Consumes: everything from Tasks 3–7 (ids, versions, install commands).
- Produces: the document linked from `README.md` in Task 9 and from both workflow
  READMEs (Tasks 6 and 7).

- [ ] **Step 1: Write the document**

Create `docs/send-it-harness.md` with these sections. Every fact listed under a
section is required content; write the connective prose around them.

**`# The send-it harness`** — one paragraph: an unattended pipeline from a
one-line feature description to an open pull request with before/after UI
screenshots, assembled from Spec Kit add-ons. Worktree → spec → screenshots →
implement → screenshots → PR.

**`## Four separate catalog stacks`** — Spec Kit keeps an independent catalog per
add-on type; registering one does not register the others. State the two behaviors
that surprise people: registering a **workflow** or **extension** catalog for a
project *replaces* the built-in `default` + `community` sources for that type
rather than adding to them (check with `specify <type> catalog list`, re-add the
official ones explicitly if you want them); and the upstream **community**
extension catalog is registered `discovery-only`, so you can find these extensions
there but not install them — which is why this repo's catalog exists.

**`## The pieces`** — a table: `worktrees` 2.0.0 (hosted here), `git` 1.1.0 (hosted
here), `screenshots` 0.1.0 (hosted here), `ship` 1.0.0, `staff-review` 1.0.0,
`qa` 1.0.0 (pointers at arunt14), `send-it` 0.2.0 and `send-it-checked` 0.2.0
(workflows). One line each on what it contributes.

**`## How it composes`** — the runtime chain, in order:
1. `specify init` writes `.specify/`; `feature_numbering` in
   `.specify/init-options.json` is core spec-kit's, not extension-owned.
2. Catalogs registered → extensions installed → `.specify/extensions.yml` gets the
   hook wiring.
3. `specify workflow run send-it -i spec="…"` dispatches step 1, `speckit.specify`.
4. The **`before_specify`** hook fires first: `speckit.worktrees.create` derives
   the branch name via `--from-description` (delegating to the git extension's
   `create-new-feature-branch.sh --dry-run`), creates the branch with
   `git worktree add -b` from `base_ref`, and — because `enter_worktree: true` —
   moves the agent session into the worktree.
5. **The session model:** every later step runs *in the worktree*, because they are
   the same agent session and the working directory carries forward. The primary
   checkout stays on its own branch, untouched. Nothing downstream may assume the
   primary is on the feature branch.
6. `plan` → `tasks` → `screenshots-before` (baseline; the tree differs from the
   base only by spec documents, so the app renders what the PR's base commit
   would) → `implement` → (`review` → `qa` in send-it-checked) →
   `screenshots-after` → `ship`.
7. `ship` commits, rebases, pushes, builds the PR description including the
   before/after screenshot tables, and opens the PR.

**`## Reproducing it in a new repo`** — the full command sequence, which is now
mostly `catalog add` + `extension add`:

```bash
specify init . --ai claude
# feature_numbering is core spec-kit's, not extension-owned:
# set "feature_numbering": "timestamp" in .specify/init-options.json

specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5
specify workflow catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/workflows/catalog.json

specify extension add worktrees screenshots ship staff-review qa

# `git` must use --from: see "Why git is installed with --from" below.
specify extension add git --force --from \
  https://github.com/clintcparker/speckit-addons/releases/download/ext-git-v1.1.0/git-1.1.0.zip

specify workflow add send-it
specify workflow run send-it -i spec="make the app do the thing"
```

State that the forks mean **no hand edits to `.specify/extensions.yml` are
required** — the `worktrees` hook lands at `before_specify` and the `git` fork
declares no competing hook.

**`## Remaining manual steps`** — exactly two:
- `feature_numbering: "timestamp"` in `.specify/init-options.json`. Core spec-kit
  owns this; no extension can set it. Without it, parallel worktrees collide on
  sequential feature numbers.
- Skill regeneration after editing any command file in `.specify/extensions/*/commands/`.
  `.claude/skills/` embeds a *copy* of the command body. The `screenshots`
  extension is designed so you never need to — its command is generic and its
  per-repo adaptation is a config file — but the rule holds for anything you do
  hand-edit.

**`## Why git is installed with --from`** — `specify extension add git` calls
`_locate_bundled_extension("git")` before it ever constructs an
`ExtensionCatalog`, and `git` is bundled at
`specify_cli/core_pack/extensions/git/`. No catalog priority can shadow a bundled
extension. `--from` takes a different branch that bypasses the bundled lookup and
installs under the manifest's own id, so the installed id is still `git` and hook
wiring is unaffected. Caveat: `--from` does not verify a digest — only
catalog-resolved downloads call `verify_archive_sha256` — so verify manually
against the catalog's `sha256`:

```bash
curl -sL https://github.com/clintcparker/speckit-addons/releases/download/ext-git-v1.1.0/git-1.1.0.zip \
  | shasum -a 256
```

**`## Gotchas`** — write these verbatim as a list:

- **`--force` reinstalls revert hand edits to `extension.yml`.** This is why both
  hook fixes are baked into the forks rather than applied per repo. What `--force`
  *does* preserve is config: top-level `*-config.yml` and `*-config.local.yml`
  files under `.specify/extensions/<id>/` are backed up and restored around the
  reinstall.
- **A config file that is not named `*-config.yml` is silently destroyed.**
  `scaffold_config` refuses any other `provides.config` target name, so it is never
  deployed on install; and the `--force` backup only globs that pattern, so an
  existing one is removed and not restored. This is why the screenshots app profile
  is `screenshots-config.yml` and not `app-profile.md`.
- **Bundled extensions win over catalogs, unconditionally.** See the `git` section
  above. Applies to any bundled id: `git`, `bug`, `assess`, `agent-context`.
- **Registering a project catalog replaces the built-in stack** for that add-on
  type — it is read *instead of* `default` + `community`, not alongside. Re-add the
  official catalogs explicitly if you want them.
- **The upstream community extension catalog is discovery-only.** It lists these
  extensions but `specify extension add` refuses to install from it. Discovery is
  not installability.
- **`raw.githubusercontent.com` negative-caches 404s for several minutes.**
  Requesting a release URL before its tag is pushed makes it keep 404ing *after*
  you push. Never run `validate_catalog.py --check-urls` before the tag is up.
- **GitHub tag archives are not contractually byte-stable**, which is why
  first-party extensions here ship as **release assets** instead: an uploaded asset
  is the bytes you uploaded. Third-party pointer entries still carry that risk, and
  the fix if it ever fires is to re-read the upstream code and recompute digests,
  not to drop the `sha256` field.
- **Workflow `requires` has no extension key.** Only `speckit_version` and
  `integrations` are recognized, and an unknown key is a hard validation error. A
  workflow's extension dependencies are documentation, enforced only by the step
  failing at dispatch.
- **Screenshot app state must live outside the checkout.** The git extension's
  auto-commit hooks will otherwise commit a SQLite database or a dev-server log.
- **Sequential feature numbering collides under parallel worktrees.** Each worktree
  computes "the next number" independently from the same `specs/` directory and the
  same refs. Use timestamps, in both `.specify/init-options.json`
  (`feature_numbering`) and the git extension's `git-config.yml`
  (`branch_numbering`).

**`## Publishing changes`** — point at
[`workflows/README.md`](../workflows/README.md) for the release procedures and note
that first-party extensions tag as `ext-<id>-v<version>` with a built zip attached
to the release.

- [ ] **Step 2: Verify every link and command in the document**

```bash
uv run --with pyyaml python - <<'PY'
import pathlib, re
doc = pathlib.Path("docs/send-it-harness.md").read_text(encoding="utf-8")
root = pathlib.Path(".")
missing = [
    target
    for target in re.findall(r"\]\((?!https?:)([^)#]+)", doc)
    if not (root / "docs" / target).resolve().exists()
]
print("broken relative links:", missing)
assert not missing
PY
```

Expected: `broken relative links: []`

- [ ] **Step 3: Commit**

```bash
git add docs/send-it-harness.md
git commit -m "docs: add the send-it harness write-up"
```

---

### Task 9: README restructure

The root README still documents a `bundles/` directory that was deleted in
`1dcd69b` / `2996929`, including install commands that 404. `extensions/README.md`
still opens with "None of the code here is this repo's", which stopped being true
two tasks ago.

**Files:**
- Modify: `README.md`
- Modify: `extensions/README.md`
- Modify: `workflows/README.md`

**Interfaces:**
- Consumes: `docs/send-it-harness.md` (Task 8); all versions from Tasks 3–7.
- Produces: no code interface.

- [ ] **Step 1: Delete the stale Bundles section from the root README**

In `README.md`, delete the entire `### Bundles` section — its heading, the table
row for `send-it` 0.1.0, and the `specify bundle catalog add` / `specify bundle
install send-it` code block, through to the paragraph ending
"one-line post-install edit."

Also delete the bundle clause from the `### A gotcha worth knowing` paragraph, so
it reads:

```markdown
### A gotcha worth knowing

Registering a **workflow** or **extension** catalog for a project *replaces*
Spec Kit's built-in `default` + `community` sources for that type — the project
config is read instead of them, not alongside. If you want the official catalogs
back after registering this one, add them explicitly and check with
`specify <type> catalog list`.
```

- [ ] **Step 2: Rewrite the root README's Extensions section**

Replace the whole `### Extensions` section body (keeping the heading) with:

```markdown
Some of these are **hosted here** — first-party code, released from this repo.
The rest are **pinned pointers** at somebody else's repository. See
[extensions/README.md](extensions/README.md).

| ID | Version | Source |
|---|---|---|
| [`screenshots`](extensions/screenshots/) | 0.1.0 | Hosted here |
| [`worktrees`](extensions/worktrees/) | 2.0.0 | Hosted here — fork of [dango85/spec-kit-worktree-parallel](https://github.com/dango85/spec-kit-worktree-parallel) v1.0.0 |
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
```

- [ ] **Step 3: Update the root README's workflow table and Security section**

In the `### Workflows` table, change both send-it rows to `0.2.0` and update their
descriptions to mention screenshots:

```markdown
| [`send-it`](workflows/send-it/) | 0.2.0 | Spec to PR, unattended — `yolo` plus screenshots and `ship`, ending in an open pull request |
| [`send-it-checked`](workflows/send-it-checked/) | 0.2.0 | `send-it` plus staff review and QA, each with one fix-and-re-run pass |
```

In `## Security`, replace the final paragraph ("The extension catalog published
here points at four repositories…") with:

```markdown
Three of the extensions published here are this repo's own code; the other three
are pointers at repositories this project does not control. Those three are
unreviewed third-party code that runs with your full privileges. Each pointer
entry pins a tag *and* a SHA-256 of that tag's archive, so a re-pointed tag fails
the install rather than swapping the code silently — but a pin is not a review.
See [extensions/README.md](extensions/README.md#trust).

`send-it` and `send-it-checked` also launch your application to take screenshots.
The `screenshots` extension never modifies application code, and its data rules
require app state to live outside the checkout and real user data to be restored
after every run including a failed one — but it does start your app and drive its
UI.
```

- [ ] **Step 4: Restructure `extensions/README.md`**

Replace everything from the top of the file through the end of the `## Available`
table with:

```markdown
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
| [`worktrees`](worktrees/) | 2.0.0 | Default-on worktree isolation — fork of [dango85/spec-kit-worktree-parallel](https://github.com/dango85/spec-kit-worktree-parallel) v1.0.0 |
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
```

Delete the line "All four are dependencies of the [`send-it` bundle](../bundles/send-it/)."
— that path no longer exists.

In `## Why this catalog exists at all`, change "All four extensions are already
listed" to "The three third-party extensions are already listed", and update the
`worktrees` pin sentence to: "The upstream community catalog also pins `worktrees`
at 1.0.0 — this repo publishes a 2.0.0 fork of it."

- [ ] **Step 5: Add the `--from` section and scope the trust notes**

In `extensions/README.md`, add after the `## Install` section:

```markdown
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
```

Then retitle `## What is pinned, and what that does not guarantee` to
`## Third-party pins, and what they do not guarantee`, and open it with: "This
section is about the third-party entries only. First-party extensions are released
from this repo as GitHub Release assets, which are the bytes we uploaded — the
archive-recompression risk below does not apply to them."

Retitle `## Trust` to `## Trust (third-party entries)` and change its first
sentence to "The three third-party extensions are unreviewed third-party code that
runs with your full privileges …".

- [ ] **Step 6: Update `workflows/README.md`**

Change the version table's two send-it rows to `0.2.0`.

Replace the `## Releasing a bundle` section entirely (bundles are gone) with:

```markdown
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
```

(the existing numbered list for pointer bumps follows unchanged, minus its step 5
about `bundles/*/bundle.yml`, which is deleted).

Also delete step 6 of `## Adding a workflow` ("If a bundle ships this workflow…") —
there are no bundles.

- [ ] **Step 7: Verify no stale bundle references remain**

```bash
grep -rn "bundle" README.md extensions/README.md workflows/README.md docs/send-it-harness.md || echo "clean"
```

Expected: `clean`, or only occurrences inside the phrase "bundled with spec-kit"
(which refer to spec-kit's bundled extensions, not to this repo's deleted
`bundles/` directory). Review each hit and remove any that points at `bundles/`.

- [ ] **Step 8: Validate and commit**

Run: `uv run --with pyyaml python scripts/validate_catalog.py`

Expected: `✓ NN checks passed.`

```bash
git add README.md extensions/README.md workflows/README.md
git commit -m "docs: first-party vs pointer extensions; drop the stale bundles section"
```

---

### Task 10: Full pre-merge verification and pull request

**Files:** none created or modified.

**Interfaces:**
- Consumes: Tasks 1–9.
- Produces: an open pull request against `main`.

- [ ] **Step 1: Run the whole suite**

```bash
uv run --with pyyaml --with pytest python -m pytest tests/ -q
uv run --with pyyaml python scripts/validate_catalog.py
```

Expected: all tests pass; `✓ NN checks passed.`

Do **not** add `--check-urls` — the tags do not exist yet, and requesting the URLs
now poisons `raw.githubusercontent.com`'s negative cache for several minutes after
they do.

- [ ] **Step 2: Confirm every zip still matches its published digest**

The catalog digests were taken in Tasks 3–5. If anything inside an extension
directory changed since, the digest is stale.

```bash
for ext in screenshots worktrees git; do
  uv run --with pyyaml python scripts/build_extension.py "extensions/$ext" \
    --output /tmp/speckit-addons-verify
done
uv run --with pyyaml python - <<'PY'
import json, hashlib, pathlib
catalog = json.loads(pathlib.Path("extensions/catalog.json").read_text())
for ext_id in ("screenshots", "worktrees", "git"):
    entry = catalog["extensions"][ext_id]
    zip_path = pathlib.Path(
        f"/tmp/speckit-addons-verify/{ext_id}-{entry['version']}.zip"
    )
    actual = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    status = "OK " if actual == entry["sha256"] else "STALE"
    print(f"{status} {ext_id}: catalog={entry['sha256'][:12]} built={actual[:12]}")
    assert actual == entry["sha256"], ext_id
PY
```

Expected: three `OK` lines. A `STALE` line means rebuild that extension and update
its catalog `sha256` before continuing.

- [ ] **Step 3: Confirm the working tree is clean and push**

```bash
git status --short
git push -u origin source-of-truth
```

Expected: no output from `git status --short`.

- [ ] **Step 4: Open the pull request**

```bash
gh pr create --base main --head source-of-truth \
  --title "speckit-addons as the source of truth" \
  --body "$(cat <<'EOF'
Everything the send-it harness needs now installs from this repo's catalogs.
`homeapp1/.specify/` stops being the only copy of anything.

## What lands

- **`screenshots` 0.1.0** (new, first-party) — generic capture command plus a
  per-repo app profile, with two worked examples and a bootstrap mode that
  derives the profile on first run.
- **`worktrees` 2.0.0** (fork of dango85 v1.0.0) — the battle-tested local
  patches, plus the `before_specify` hook declaration that `--force` reinstalls
  used to revert.
- **`git` 1.1.0** (fork of spec-kit's bundled v1.0.0) — honors
  `branch_numbering: timestamp` for hook callers, and no longer declares the
  `before_specify` hook that competed with worktrees.
- **`send-it` 0.2.0 / `send-it-checked` 0.2.0** — screenshot steps, and the ship
  step now detects repository visibility instead of asserting private.
- **`docs/send-it-harness.md`** — the write-up, with a gotchas appendix.
- Validator understands hosted-vs-pointer entries; new reproducible zip builder;
  first tests in the repo; the stale Bundles section is gone.

## Design deviations worth reviewing

1. The screenshots app profile ships as **`screenshots-config.yml`**, not
   `app-profile.md`. Spec Kit only preserves top-level `*-config.yml` files
   across `--force`; any other name is dropped on install and destroyed on
   reinstall — the exact failure the config mechanism was chosen to avoid.
2. The `git` fork installs with **`--from`**, not by id. `specify extension add`
   resolves bundled extensions before it reads any catalog, so no catalog
   priority can shadow the bundled `git`.
3. Workflows document their `screenshots` dependency in prose only. `requires`
   recognizes just `speckit_version` and `integrations`; anything else is a hard
   validation error.

## Not yet done

Tags and releases are cut after merge, then the smoke test runs against a fresh
`specify init` project.
EOF
)"
```

Expected: a PR URL.

---

### Task 11: Release and smoke test (post-merge)

Runs **only after the pull request is merged**. Tags point at merged commits.

**Files:** none created or modified in this repo.

**Interfaces:**
- Consumes: everything merged.
- Produces: five pushed tags, three GitHub Releases with attached zips, and a
  verified end-to-end install.

- [ ] **Step 1: Sync to the merged main**

```bash
git checkout main && git pull --ff-only
uv run --with pyyaml python scripts/validate_catalog.py
```

Expected: `✓ NN checks passed.`

- [ ] **Step 2: Rebuild the three zips from the merged tree**

```bash
rm -rf /tmp/speckit-addons-release
for ext in screenshots worktrees git; do
  uv run --with pyyaml python scripts/build_extension.py "extensions/$ext" \
    --output /tmp/speckit-addons-release
done
```

Expected: three digest lines matching the `sha256` values in
`extensions/catalog.json`. The build is reproducible, so they must match exactly.
If one does not, stop — the catalog is wrong and users would hit a digest
mismatch that reads like tampering.

- [ ] **Step 3: Tag and push all five tags**

```bash
git tag ext-screenshots-v0.1.0
git tag ext-worktrees-v2.0.0
git tag ext-git-v1.1.0
git tag send-it-v0.2.0
git tag send-it-checked-v0.2.0
git push origin ext-screenshots-v0.1.0 ext-worktrees-v2.0.0 ext-git-v1.1.0 \
  send-it-v0.2.0 send-it-checked-v0.2.0
```

- [ ] **Step 4: Create the three releases with their assets**

```bash
gh release create ext-screenshots-v0.1.0 \
  /tmp/speckit-addons-release/screenshots-0.1.0.zip \
  --title "screenshots 0.1.0" --notes-file extensions/screenshots/CHANGELOG.md

gh release create ext-worktrees-v2.0.0 \
  /tmp/speckit-addons-release/worktrees-2.0.0.zip \
  --title "worktrees 2.0.0" --notes-file extensions/worktrees/CHANGELOG.md

gh release create ext-git-v1.1.0 \
  /tmp/speckit-addons-release/git-1.1.0.zip \
  --title "git 1.1.0" --notes-file extensions/git/CHANGELOG.md
```

- [ ] **Step 5: Verify every pinned URL resolves**

Only now — the tags and assets exist, so no negative cache gets poisoned.

```bash
uv run --with pyyaml python scripts/validate_catalog.py --check-urls
```

Expected: `✓ NN checks passed (including URL reachability).`

- [ ] **Step 6: Smoke test a clean install**

```bash
rm -rf /tmp/send-it-smoke && mkdir -p /tmp/send-it-smoke && cd /tmp/send-it-smoke
git init -q && git commit -q --allow-empty -m "init"
specify init . --ai claude

specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5
specify workflow catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/workflows/catalog.json

specify extension add screenshots
specify extension add worktrees
specify extension add git --force --from \
  https://github.com/clintcparker/speckit-addons/releases/download/ext-git-v1.1.0/git-1.1.0.zip
specify extension add ship

specify workflow add send-it
specify extension list
specify workflow list
```

Expected: four extensions and one workflow installed, `worktrees` at 2.0.0 and
`git` at 1.1.0.

- [ ] **Step 7: Verify the hook wiring landed with no hand edits**

```bash
cd /tmp/send-it-smoke
uv run --with pyyaml python - <<'PY'
import pathlib, yaml
data = yaml.safe_load(pathlib.Path(".specify/extensions.yml").read_text())
hooks = data.get("hooks", {})

before = hooks.get("before_specify", [])
worktree_hooks = [h for h in before if h.get("extension") == "worktrees"]
git_hooks = [h for h in before if h.get("extension") == "git"]

assert len(worktree_hooks) == 1, f"expected one worktrees before_specify hook: {before}"
assert worktree_hooks[0].get("enabled") is True, worktree_hooks[0]
assert not git_hooks, f"git must not declare a before_specify hook: {git_hooks}"

after = hooks.get("after_specify", [])
assert not [h for h in after if h.get("extension") == "worktrees"], after

print("hook wiring OK — worktrees at before_specify, no competing git hook")
PY
```

Expected: `hook wiring OK — worktrees at before_specify, no competing git hook`.

This is the assertion the whole forking exercise exists to make true. If it fails,
the fork's `extension.yml` hook declaration is wrong and needs a patch release
before anything else proceeds.

- [ ] **Step 8: Verify the config templates deployed**

```bash
cd /tmp/send-it-smoke
ls -l .specify/extensions/screenshots/screenshots-config.yml \
      .specify/extensions/worktrees/worktree-config.yml \
      .specify/extensions/git/git-config.yml
grep -n "^unconfigured:" .specify/extensions/screenshots/screenshots-config.yml
grep -n "^branch_numbering:" .specify/extensions/git/git-config.yml
```

Expected: all three files exist; `unconfigured: true`; `branch_numbering: timestamp`.

- [ ] **Step 9: Verify `--force` preserves an adaptation**

```bash
cd /tmp/send-it-smoke
printf '\n# adapted by the smoke test\n' >> \
  .specify/extensions/screenshots/screenshots-config.yml
specify extension add screenshots --force
grep -c "adapted by the smoke test" \
  .specify/extensions/screenshots/screenshots-config.yml
```

Expected: `1`. A `0` means the config naming convention is not being honored and
the profile is being clobbered on upgrade — the failure this design exists to
prevent.

- [ ] **Step 10: Run a bootstrap-mode capture**

In the smoke-test project, run a trivial feature through `speckit.specify` and then
dispatch `speckit.screenshots.capture` with `mode: before`. The project has no app,
so the correct outcome is a clean self-skip.

Expected: `specs/<feature>/screenshots/SKIPPED.md` exists, contains one line
explaining that the feature has no UI surface, and is committed. No images, no
error, and the command did not stop to ask a question.

- [ ] **Step 11: Report**

Report to Clint: the five tags, the three release URLs, the smoke-test results for
steps 6–10, and anything that had to be adjusted. If steps 7, 9 or 10 failed, say
so plainly with the output — those three are the design's load-bearing claims.

---

## Self-Review

**Spec coverage**

| Spec section | Task |
|---|---|
| Component 1 — screenshots extension, layout, seam, config rationale, bootstrap, manifest schema, no hooks | Task 3 (`app-profile.md` → `screenshots-config.yml`, per Finding 1) |
| Component 2 — worktrees fork 2.0.0, homeapp1 baseline, lineage in CHANGELOG, `before_specify` hook fix | Task 4 |
| Component 3 — git fork 1.1.0, numbering patch, no `before_specify` hook, timestamp template default, id shadowing | Task 5 (+ Finding 2: `--from` is the install path, not catalog priority) |
| Packaging — release-asset zips, wrapping dir, `ext-` tags, catalog fields, validator extension, smoke test | Tasks 1, 2, 3–5, 11 |
| Component 4 — send-it 0.2.0, visibility detection, send-it-checked 0.2.0 with `screenshots-after` post-QA, dependency documentation, release procedure | Tasks 6, 7 (+ Finding 3: prose only) |
| Component 5 — `docs/send-it-harness.md`, root README extensions table + Bundles removal, `extensions/README.md` restructure | Tasks 8, 9 |
| Release flow — `source-of-truth` branch, PR reviewed by Clint, tags only after merge | Tasks 10, 11 |
| Risk: installer zip-layout assumption | Retired by Finding 4; Task 11 step 6 still exercises it |
| Risk: `git` id shadowing | Resolved by Finding 2; decided in Task 5, documented in Tasks 5, 8, 9 |
| Risk: send-it without screenshots installed | Documented in Tasks 6, 7, 8 |

Out-of-scope items from the spec (send-it bundle resurrection, upstream PRs,
migrating homeapp1/site-checker to the published catalog) have no task, as
intended.

**Open decision for Clint** — Task 5 keeps the fork's id as `git` and installs it
with `--from`, per the spec's stated fallback. The alternative is a distinct id
such as `git-worktree-safe`, which would install cleanly from the catalog with
digest verification, but would break the `extension: git` hook keys, leave the
bundled `git` installable alongside it (double `before_specify` hooks), and
contradict the spec's "id stays `git`". Flag it at PR review rather than blocking.
