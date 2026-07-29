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

REQUIRED_ENTRY_FIELDS = (
    "id",
    "name",
    "description",
    "author",
    "version",
    "url",
    "license",
)

# Fields that document a specific release and must therefore be pinned to that
# release's tag rather than to a moving branch.
TAG_PINNED_DOC_FIELDS = ("documentation", "changelog")


@dataclass(frozen=True)
class AddonType:
    """One of Spec Kit's four independent add-on catalog systems.

    Each type has its own catalog file, its own top-level key inside that file,
    and its own manifest filename. Add a member to ``ADDON_TYPES`` below when
    this repo starts publishing presets, extensions, or bundles.
    """

    directory: str  # repo directory holding this type's add-ons
    catalog_key: str  # top-level key inside catalog.json
    manifest: str  # per-add-on manifest filename
    manifest_section: str  # top-level key inside the manifest holding id/version


ADDON_TYPES = (
    AddonType(
        directory="workflows",
        catalog_key="workflows",
        manifest="workflow.yml",
        manifest_section="workflow",
    ),
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

    on_disk = {
        child.name
        for child in sorted(type_dir.iterdir())
        if child.is_dir() and not child.name.startswith(".")
    }

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
            on_disk=on_disk,
            catalog_where=where,
            check_urls=check_urls,
            report=report,
        )


def validate_entry(
    *,
    addon_type: AddonType,
    addon_id: str,
    entry: Any,
    on_disk: set[str],
    catalog_where: str,
    check_urls: bool,
    report: Report,
) -> None:
    where = f"{catalog_where} [{addon_id}]"

    if not isinstance(entry, dict):
        report.fail(where, "entry must be an object")
        return

    for field in REQUIRED_ENTRY_FIELDS:
        report.check(
            bool(entry.get(field)), where, f'missing required field "{field}"'
        )

    report.check(
        entry.get("id") == addon_id,
        where,
        f'entry "id" is {entry.get("id")!r} but its catalog key is {addon_id!r}',
    )

    if addon_id not in on_disk:
        report.fail(
            where,
            f"no {addon_type.directory}/{addon_id}/ directory on disk",
        )
        return

    manifest_path = REPO_ROOT / addon_type.directory / addon_id / addon_type.manifest
    if not manifest_path.is_file():
        report.fail(
            f"{addon_type.directory}/{addon_id}",
            f"missing {addon_type.manifest}",
        )
        return

    manifest = load_yaml(manifest_path, report)
    if manifest is None:
        return

    section = manifest.get(addon_type.manifest_section)
    if not isinstance(section, dict):
        report.fail(
            rel(manifest_path),
            f'missing "{addon_type.manifest_section}" mapping',
        )
        return

    manifest_id = section.get("id")
    manifest_version = section.get("version")

    report.check(
        manifest_id == addon_id,
        rel(manifest_path),
        f"{addon_type.manifest_section}.id is {manifest_id!r} but the directory "
        f"is named {addon_id!r} -- Spec Kit installs by id, so these must match",
    )

    entry_version = entry.get("version")
    report.check(
        manifest_version == entry_version,
        where,
        f"catalog version {entry_version!r} disagrees with "
        f"{addon_type.manifest}'s {manifest_version!r}",
    )

    # A version we cannot trust makes every URL check below meaningless.
    if manifest_version != entry_version or not entry_version:
        return

    tag = f"{addon_id}-v{entry_version}"
    expected_url = (
        f"{RAW_BASE}/{tag}/{addon_type.directory}/{addon_id}/{addon_type.manifest}"
    )
    url = entry.get("url")
    report.check(
        url == expected_url,
        where,
        f'"url" must be pinned to the release tag.\n'
        f"      expected: {expected_url}\n"
        f"      actual:   {url}",
    )

    for field in TAG_PINNED_DOC_FIELDS:
        value = entry.get(field)
        if not value:
            continue
        report.check(
            value.startswith(f"{BLOB_BASE}/{tag}/"),
            where,
            f'"{field}" must be pinned to {tag}, got {value!r}',
        )

    if not check_urls:
        return

    for field in ("url", *TAG_PINNED_DOC_FIELDS):
        value = entry.get(field)
        if not value:
            continue
        problem = url_resolves(value)
        if problem:
            report.fail(
                where,
                f'"{field}" does not resolve ({problem}) -- {value}\n'
                f"      Has the {tag} tag been pushed?",
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
