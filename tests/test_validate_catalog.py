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
