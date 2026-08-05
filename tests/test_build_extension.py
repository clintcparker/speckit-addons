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
