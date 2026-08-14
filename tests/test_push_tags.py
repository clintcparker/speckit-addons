"""Tests for push-tags.sh.

The bug this script exists to prevent is silent. GitHub emits no tag-push
events for a push carrying more than three tags, so cutting a release for four
add-ons at once lands the tags on the remote, never runs release.yml, and
reports nothing at all -- while the catalog on main goes on pinning URLs that
404 for every consumer. Nothing in this repo notices until the next push to
main runs `validate_catalog.py --check-urls`.

The properties that matter: no push ever carries more than three tags; the set
of tags is derived from the catalogs rather than typed by hand; third-party
entries are never tagged here, because they are released from their own repos;
an already-tagged version is not re-pushed; and tagging HEAD is refused when
HEAD does not actually represent what the catalogs describe.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PUSH_TAGS = REPO_ROOT / "scripts" / "push-tags.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None,
    reason="needs git and bash",
)

OURS = "https://github.com/clintcparker/speckit-addons"
THEIRS = "https://github.com/arunt14/spec-kit-ship"


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def run(*args: str, work: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(PUSH_TAGS), "--repo-root", str(work), *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A checkout with five untagged first-party versions and an origin."""
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    work.mkdir()
    git("init", "-q", "-b", "main", ".", cwd=work)
    git("remote", "add", "origin", str(origin), cwd=work)
    git("config", "user.email", "t@example.com", cwd=work)
    git("config", "user.name", "t", cwd=work)

    (work / "extensions").mkdir()
    (work / "workflows").mkdir()
    (work / "extensions" / "catalog.json").write_text(
        json.dumps(
            {
                "extensions": {
                    "screenshots": {"version": "0.3.0", "repository": OURS},
                    "worktrees": {"version": "2.5.0", "repository": OURS},
                    # Already released -- must not be pushed again.
                    "git": {"version": "1.1.0", "repository": OURS},
                    # Released from someone else's repo; no tag here fits it.
                    "ship": {"version": "1.0.0", "repository": THEIRS},
                }
            }
        )
    )
    (work / "workflows" / "catalog.json").write_text(
        json.dumps(
            {
                "workflows": {
                    "send-it": {"version": "0.9.0", "repository": OURS},
                    "send-it-checked": {"version": "0.10.0", "repository": OURS},
                    "yolo": {"version": "0.8.0", "repository": OURS},
                }
            }
        )
    )
    git("add", "-A", cwd=work)
    git("commit", "-qm", "init", cwd=work)
    git("push", "-q", "origin", "main", cwd=work)
    git("tag", "-a", "ext-git-v1.1.0", "-m", "git 1.1.0", cwd=work)
    git("push", "-q", "origin", "ext-git-v1.1.0", cwd=work)
    return work


def test_lists_only_untagged_first_party_versions(repo: Path) -> None:
    result = run("--list", work=repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [
        "ext-screenshots-v0.3.0",
        "ext-worktrees-v2.5.0",
        "send-it-v0.9.0",
        "send-it-checked-v0.10.0",
        "yolo-v0.8.0",
    ]


def test_third_party_entries_are_never_tagged_here(repo: Path) -> None:
    assert "ship" not in run("--list", work=repo).stdout


def test_no_push_carries_more_than_three_tags(repo: Path) -> None:
    """The whole point: >3 tags in one push means GitHub fires nothing."""
    pushes = [
        line.split(":", 1)[1].split()
        for line in run("--dry-run", work=repo).stdout.splitlines()
        if line.startswith("would push:")
    ]
    assert pushes, "expected at least one push"
    assert all(len(batch) <= 3 for batch in pushes)
    # Batched, not dropped.
    assert sum(len(batch) for batch in pushes) == 5


def test_batch_size_above_three_is_refused(repo: Path) -> None:
    result = run("--batch-size", "4", "--list", work=repo)
    assert result.returncode == 1
    assert "batch-size above 3" in result.stderr


def test_pushes_every_tag_and_is_idempotent(repo: Path) -> None:
    result = run("--no-verify", work=repo)
    assert result.returncode == 0, result.stderr

    origin = git("config", "--get", "remote.origin.url", cwd=repo)
    tags = set(git("tag", "-l", cwd=Path(origin)).split())
    assert tags == {
        "ext-git-v1.1.0",
        "ext-screenshots-v0.3.0",
        "ext-worktrees-v2.5.0",
        "send-it-v0.9.0",
        "send-it-checked-v0.10.0",
        "yolo-v0.8.0",
    }

    again = run("--no-verify", work=repo)
    assert again.returncode == 0
    assert "Nothing to push" in again.stdout


def test_dirty_tree_is_refused(repo: Path) -> None:
    (repo / "junk").write_text("x")
    result = run("--no-verify", work=repo)
    assert result.returncode == 1
    assert "dirty" in result.stderr


def test_head_behind_origin_is_refused(repo: Path) -> None:
    """A tag at HEAD would otherwise claim a tree main does not have."""
    git("commit", "-q", "--allow-empty", "-m", "local only", cwd=repo)
    result = run("--no-verify", work=repo)
    assert result.returncode == 1
    assert "not origin/main" in result.stderr
