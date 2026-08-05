"""Tests for the first-party extension zip builder.

The digest of this zip goes into a catalog entry that users verify, so the two
properties that matter are: the archive is byte-stable across builds, and its
layout is one that specify-cli's install_from_zip actually accepts.
"""

from __future__ import annotations

import importlib.util
import os
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
    (ext / "__pycache__").mkdir()
    (ext / ".git").mkdir()
    (ext / "extension.yml").write_text(
        'schema_version: "1.0"\nextension:\n  id: demo\n  version: 1.2.3\n',
        encoding="utf-8",
    )
    (ext / "commands" / "run.md").write_text("# run\n", encoding="utf-8")
    script = ext / "scripts" / "bash" / "go.sh"
    script.write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")
    script.chmod(0o755)
    # Excluded names (EXCLUDED_NAMES), including nested-directory cases to
    # prove exclusion matches on any path component, not just the leaf name.
    (ext / ".DS_Store").write_text("junk", encoding="utf-8")
    (ext / "Thumbs.db").write_text("junk", encoding="utf-8")
    (ext / "__pycache__" / "mod.pyc").write_text("junk", encoding="utf-8")
    (ext / ".git" / "config").write_text("junk", encoding="utf-8")
    # Excluded suffixes (EXCLUDED_SUFFIXES), as bare top-level files so the
    # suffix check is exercised independently of the directory-name check.
    (ext / "cache.pyc").write_text("junk", encoding="utf-8")
    (ext / "scratch.swp").write_text("junk", encoding="utf-8")
    (ext / "backup.orig").write_text("junk", encoding="utf-8")
    (ext / "patch.rej").write_text("junk", encoding="utf-8")
    # Contains an excluded suffix as a substring ("orig") but does not end
    # with it -- must survive, proving the suffix check is not over-eager.
    (ext / "notes.orig.md").write_text("# notes\n", encoding="utf-8")
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
        names = set(zf.namelist())

    excluded_names = {
        "demo/.DS_Store",
        "demo/Thumbs.db",
        "demo/__pycache__/mod.pyc",
        "demo/.git/config",
        "demo/cache.pyc",
        "demo/scratch.swp",
        "demo/backup.orig",
        "demo/patch.rej",
    }
    assert names.isdisjoint(excluded_names)

    # The shipped files -- including the one that merely contains an
    # excluded substring without matching it -- must still be present, so
    # this test cannot pass by excluding everything.
    shipped = {
        "demo/extension.yml",
        "demo/commands/run.md",
        "demo/scripts/bash/go.sh",
        "demo/notes.orig.md",
    }
    assert shipped <= names


def test_is_byte_stable_across_builds(be, sample, tmp_path):
    first = (be.build_extension(sample, tmp_path / "a")).read_bytes()
    second = (be.build_extension(sample, tmp_path / "b")).read_bytes()
    assert first == second


def test_is_byte_stable_across_umasks(be, sample, tmp_path):
    """A build's bytes must not depend on the host's umask.

    external_attr is derived from the source file's actual mode bits, not
    from a freshly-created file, so a differing umask on the building
    machine must not perturb the digest.
    """
    original_umask = os.umask(0o022)
    try:
        first = be.build_extension(sample, tmp_path / "umask-022").read_bytes()
        os.umask(0o077)
        second = be.build_extension(sample, tmp_path / "umask-077").read_bytes()
    finally:
        os.umask(original_umask)
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
