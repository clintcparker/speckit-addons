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

    # ZIP_STORED (no compression), not ZIP_DEFLATED: these archives are small
    # text trees (markdown, YAML, shell scripts), so compression saves a
    # trivial number of kilobytes on a GitHub Release asset. DEFLATE's output
    # bytes are not guaranteed stable across zlib versions/implementations
    # even at a pinned compression level, so two builds of the same source
    # tree on machines with different bundled zlib can legitimately diverge --
    # exactly the failure this script exists to prevent. Reproducibility is
    # worth more than the bytes here.
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_STORED
    ) as archive:
        for source in collect_files(extension_dir):
            relative = source.relative_to(extension_dir).as_posix()
            info = zipfile.ZipInfo(f"{extension_id}/{relative}", date_time=ZIP_EPOCH)
            # ZipFile.writestr() called with a ZipInfo ignores the
            # archive-level compression= kwarg and honors
            # ZipInfo.compress_type, so it must be set here too.
            info.compress_type = zipfile.ZIP_STORED
            # ZipInfo.create_system defaults from sys.platform (0 on Windows,
            # 3 elsewhere) and that byte lands in the archive. Pin it to Unix
            # explicitly so a Windows-built archive is byte-identical to a
            # Unix-built one.
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
