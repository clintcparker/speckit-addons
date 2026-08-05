#!/usr/bin/env python3
"""Validate this repo's add-on catalogs against the add-ons on disk.

The failure mode this guards against is silent. A catalog entry that disagrees
with its add-on's manifest, or an install URL pinned to a tag that was never
pushed, breaks installs for everyone who is not us -- and is completely
invisible when working locally, because nothing here ever reads the catalog.

Usage:
    python scripts/validate_catalog.py               # structural checks
    python scripts/validate_catalog.py --check-urls  # also verify URLs resolve

``--check-urls`` is deliberately not run on pull requests: the release tag does
not exist until the release commit is tagged, so a release PR would fail it by
construction. CI runs it on push to main and on a schedule instead.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


REPO_SLUG = "clintcparker/speckit-addons"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO_SLUG}"
BLOB_BASE = f"https://github.com/{REPO_SLUG}/blob"
REPO_ROOT = Path(__file__).resolve().parent.parent

# Entry fields every catalog entry must carry, whatever its type. Per-type
# additions live in AddonType.extra_required_fields.
REQUIRED_ENTRY_FIELDS = (
    "id",
    "name",
    "description",
    "author",
    "version",
    "license",
)

# Fields that document a specific release and must therefore be pinned to that
# release's tag rather than to a moving branch. Only meaningful for add-ons
# whose source lives in this repo.
TAG_PINNED_DOC_FIELDS = ("documentation", "changelog")

# A well-formed SHA-256 hex digest, optionally "sha256:"-prefixed -- the same
# shape specify-cli's verify_archive_sha256 accepts.
SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


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


ADDON_TYPES = (
    AddonType(
        directory="workflows",
        catalog_key="workflows",
        url_field="url",
        url_kind="raw-manifest",
        # "local-only" means every entry is hosted here, so this is the kind
        # actually consulted; url_kind stays set because the field is required,
        # even though the not-hosted branch is unreachable for this type.
        hosted_url_kind="raw-manifest",
        manifest="workflow.yml",
        manifest_section="workflow",
        extra_required_fields=("url",),
        locality="local-only",
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
    # AddonType(
    #     directory="bundles",
    #     catalog_key="bundles",
    #     url_field="download_url",
    #     url_kind="release-asset",
    #     manifest="bundle.yml",
    #     manifest_section="bundle",
    #     # A bundle id may collide with a workflow id -- `send-it` is both. The
    #     # prefix keeps their release tags distinct so the two can be versioned
    #     # independently.
    #     tag_prefix="bundle-",
    #     extra_required_fields=("download_url", "role", "sha256"),
    # ),
)


class Report:
    """Accumulates failures so one run reports every problem, not just the first."""

    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def check(self, ok: bool, where: str, message: str) -> bool:
        self.checks += 1
        if not ok:
            self.failures.append(f"{where}: {message}")
        return ok

    def fail(self, where: str, message: str) -> None:
        self.checks += 1
        self.failures.append(f"{where}: {message}")


def load_json(path: Path, report: Report) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.fail(rel(path), f"could not be parsed as JSON -- {exc}")
        return None


def load_yaml(path: Path, report: Report) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        report.fail(rel(path), f"could not be parsed as YAML -- {exc}")
        return None
    if not isinstance(data, dict):
        report.fail(rel(path), "top-level value must be a mapping")
        return None
    return data


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def url_resolves(url: str) -> str | None:
    """Return None if the URL returns 200, else a short description of why not."""
    request = urllib.request.Request(url, headers={"User-Agent": "speckit-addons-ci"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                return f"HTTP {response.status}"
            return None
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return f"unreachable -- {exc}"


def validate_addon_type(
    addon_type: AddonType, check_urls: bool, report: Report
) -> None:
    type_dir = REPO_ROOT / addon_type.directory
    if not type_dir.is_dir():
        # Every type in ADDON_TYPES is one this repo publishes. A missing
        # directory is a broken repo, not an opted-out add-on type -- silently
        # skipping it is precisely the invisible failure this script exists to
        # catch.
        report.fail(
            addon_type.directory,
            f"is declared in ADDON_TYPES but {addon_type.directory}/ does not exist",
        )
        return

    catalog_path = type_dir / "catalog.json"
    if not catalog_path.is_file():
        report.fail(addon_type.directory, "has add-on directories but no catalog.json")
        return

    catalog = load_json(catalog_path, report)
    if catalog is None:
        return

    where = rel(catalog_path)

    report.check(
        catalog.get("schema_version") == "1.0",
        where,
        f'schema_version must be "1.0", got {catalog.get("schema_version")!r}',
    )

    expected_catalog_url = f"{RAW_BASE}/main/{addon_type.directory}/catalog.json"
    report.check(
        catalog.get("catalog_url") == expected_catalog_url,
        where,
        f"catalog_url must be {expected_catalog_url!r}, got "
        f"{catalog.get('catalog_url')!r}",
    )

    entries = catalog.get(addon_type.catalog_key)
    if not isinstance(entries, dict):
        report.fail(
            where,
            f'"{addon_type.catalog_key}" must be an object mapping id -> entry',
        )
        return

    on_disk = (
        {
            child.name
            for child in sorted(type_dir.iterdir())
            if child.is_dir() and not child.name.startswith(".")
        }
        if addon_type.manifest is not None
        else set()
    )

    for missing in sorted(on_disk - set(entries)):
        report.fail(
            where,
            f"{addon_type.directory}/{missing}/ exists on disk but has no "
            f"catalog entry -- it is unreachable to users",
        )

    for addon_id in sorted(entries):
        validate_entry(
            addon_type=addon_type,
            addon_id=addon_id,
            entry=entries[addon_id],
            catalog_where=where,
            check_urls=check_urls,
            report=report,
        )


def validate_entry(
    *,
    addon_type: AddonType,
    addon_id: str,
    entry: Any,
    catalog_where: str,
    check_urls: bool,
    report: Report,
) -> None:
    where = f"{catalog_where} [{addon_id}]"

    if not isinstance(entry, dict):
        report.fail(where, "entry must be an object")
        return

    required = REQUIRED_ENTRY_FIELDS + addon_type.extra_required_fields
    for field in required:
        report.check(
            bool(entry.get(field)), where, f'missing required field "{field}"'
        )

    report.check(
        entry.get("id") == addon_id,
        where,
        f'entry "id" is {entry.get("id")!r} but its catalog key is {addon_id!r}',
    )

    entry_version = entry.get("version")

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


def manifest_agrees(
    *,
    addon_type: AddonType,
    addon_id: str,
    entry_version: Any,
    where: str,
    report: Report,
) -> bool:
    """Check the on-disk manifest against the catalog entry. False == distrust."""
    manifest_path = REPO_ROOT / addon_type.directory / addon_id / addon_type.manifest
    if not manifest_path.is_file():
        report.fail(
            f"{addon_type.directory}/{addon_id}",
            f"missing {addon_type.manifest}",
        )
        return False

    manifest = load_yaml(manifest_path, report)
    if manifest is None:
        return False

    section = manifest.get(addon_type.manifest_section)
    if not isinstance(section, dict):
        report.fail(
            rel(manifest_path),
            f'missing "{addon_type.manifest_section}" mapping',
        )
        return False

    manifest_id = section.get("id")
    manifest_version = section.get("version")

    report.check(
        manifest_id == addon_id,
        rel(manifest_path),
        f"{addon_type.manifest_section}.id is {manifest_id!r} but the directory "
        f"is named {addon_id!r} -- Spec Kit installs by id, so these must match",
    )

    report.check(
        manifest_version == entry_version,
        where,
        f"catalog version {entry_version!r} disagrees with "
        f"{addon_type.manifest}'s {manifest_version!r}",
    )

    return bool(entry_version) and manifest_version == entry_version


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
        expected = (
            f"{RAW_BASE}/{tag}/{addon_type.directory}/{addon_id}/{addon_type.manifest}"
        )
        report.check(
            url == expected,
            where,
            f'"{addon_type.url_field}" must be pinned to the release tag.\n'
            f"      expected: {expected}\n"
            f"      actual:   {url}",
        )
    elif url_kind == "release-asset":
        expected = (
            f"https://github.com/{REPO_SLUG}/releases/download/{tag}/"
            f"{addon_id}-{entry_version}.zip"
        )
        report.check(
            url == expected,
            where,
            f'"{addon_type.url_field}" must point at the release asset.\n'
            f"      expected: {expected}\n"
            f"      actual:   {url}",
        )
    else:  # external
        repository = str(entry.get("repository") or "").rstrip("/")
        expected_suffix = f"/archive/refs/tags/v{entry_version}.zip"
        report.check(
            isinstance(url, str) and url.startswith("https://"),
            where,
            f'"{addon_type.url_field}" must be an HTTPS URL, got {url!r}',
        )
        report.check(
            isinstance(url, str)
            and bool(repository)
            and url == f"{repository}{expected_suffix}",
            where,
            f'"{addon_type.url_field}" must be the upstream tag archive for the '
            f"pinned version.\n"
            f"      expected: {repository}{expected_suffix}\n"
            f"      actual:   {url}",
        )

    # Digests: required wherever the entry declares one (external entries always
    # do). A malformed digest silently disables verification in specify-cli's
    # older code paths, so check the shape, not just the presence.
    sha256 = entry.get("sha256")
    if sha256 is not None:
        report.check(
            isinstance(sha256, str) and bool(SHA256_RE.match(sha256)),
            where,
            f'"sha256" must be a 64-character hex digest, got {sha256!r}',
        )

    # Doc links: pinned to this repo's tag for our own add-ons; for external
    # add-ons they belong to the upstream repo and are only required to live
    # under it.
    for field in TAG_PINNED_DOC_FIELDS:
        value = entry.get(field)
        if not value:
            continue
        if not hosted:
            repository = str(entry.get("repository") or "").rstrip("/")
            report.check(
                bool(repository) and value.startswith(f"{repository}/"),
                where,
                f'"{field}" must live under the upstream repository '
                f"{repository!r}, got {value!r}",
            )
        else:
            report.check(
                value.startswith(f"{BLOB_BASE}/{tag}/"),
                where,
                f'"{field}" must be pinned to {tag}, got {value!r}',
            )

    if not check_urls:
        return

    for field in (addon_type.url_field, *TAG_PINNED_DOC_FIELDS):
        value = entry.get(field)
        if not value:
            continue
        problem = url_resolves(value)
        if problem:
            hint = (
                "      Has the upstream tag been deleted or re-pointed?"
                if not hosted
                else f"      Has the {tag} tag been pushed?"
            )
            report.fail(
                where,
                f'"{field}" does not resolve ({problem}) -- {value}\n{hint}',
            )


def validate_bundle_components(report: Report) -> None:
    """Check every bundle's pinned components against this repo's catalogs.

    A bundle installs its components *by id through the catalog stack*, and the
    bundler refuses when the resolved version differs from the pin. A bundle
    that pins a version this repo does not publish therefore fails at install
    time for the user and never here -- exactly the silent breakage this script
    exists to prevent.
    """
    bundles_dir = REPO_ROOT / "bundles"
    if not bundles_dir.is_dir():
        return

    published: dict[str, dict[str, str]] = {}
    for addon_type in ADDON_TYPES:
        if addon_type.catalog_key == "bundles":
            continue
        catalog = load_json(REPO_ROOT / addon_type.directory / "catalog.json", report)
        if catalog is None:
            continue
        entries = catalog.get(addon_type.catalog_key)
        if not isinstance(entries, dict):
            continue
        published[addon_type.catalog_key] = {
            addon_id: str(entry.get("version"))
            for addon_id, entry in entries.items()
            if isinstance(entry, dict)
        }

    for child in sorted(bundles_dir.iterdir()):
        manifest_path = child / "bundle.yml"
        if not child.is_dir() or not manifest_path.is_file():
            continue
        manifest = load_yaml(manifest_path, report)
        if manifest is None:
            continue
        provides = manifest.get("provides")
        if not isinstance(provides, dict):
            continue
        where = rel(manifest_path)
        for kind, refs in provides.items():
            if not isinstance(refs, list):
                continue
            available = published.get(kind)
            if available is None:
                report.fail(
                    where,
                    f"provides.{kind} pins components of a kind this repo does "
                    f"not publish -- there is no {kind}/catalog.json",
                )
                continue
            for ref in refs:
                if not isinstance(ref, dict):
                    report.fail(where, f"each provides.{kind} entry must be a mapping")
                    continue
                ref_id = ref.get("id")
                ref_version = str(ref.get("version"))
                if ref_id not in available:
                    report.fail(
                        where,
                        f"provides.{kind} pins {ref_id!r}, which is not in "
                        f"{kind}/catalog.json",
                    )
                    continue
                report.check(
                    available[ref_id] == ref_version,
                    where,
                    f"provides.{kind} pins {ref_id!r} at {ref_version!r} but "
                    f"{kind}/catalog.json publishes {available[ref_id]!r} -- "
                    f"the bundler refuses an install when these disagree",
                )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-urls",
        action="store_true",
        help="verify every pinned URL resolves (requires the release tag to be pushed)",
    )
    args = parser.parse_args()

    report = Report()
    for addon_type in ADDON_TYPES:
        validate_addon_type(addon_type, args.check_urls, report)
    validate_bundle_components(report)

    if report.failures:
        print(f"{len(report.failures)} problem(s) found:\n", file=sys.stderr)
        for failure in report.failures:
            print(f"  ✗ {failure}", file=sys.stderr)
        print(file=sys.stderr)
        return 1

    suffix = " (including URL reachability)" if args.check_urls else ""
    print(f"✓ {report.checks} checks passed{suffix}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
