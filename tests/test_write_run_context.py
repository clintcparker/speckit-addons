"""Tests for the worktrees extension's run-context writer.

This file is the only thing standing between a run's later steps and the wrong
feature, so the properties that matter are: the canonical copy lands in the tree
the feature actually lives in, a session left standing in the primary can still
find it, no copy is ever committable, and a second concurrent run is refused
rather than allowed to silently repoint the first one.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT
    / "extensions"
    / "worktrees"
    / "scripts"
    / "bash"
    / "write-run-context.sh"
)

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None,
    reason="needs git and bash",
)


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def run_script(*args: str, cwd: Path, check: bool = True):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def primary(tmp_path):
    """A repo with one commit on ``main``, standing in for the primary checkout."""
    root = tmp_path / "project"
    root.mkdir()
    git("init", "-b", "main", cwd=root)
    git("config", "user.email", "test@example.com", cwd=root)
    git("config", "user.name", "Test", cwd=root)
    (root / "README.md").write_text("# project\n", encoding="utf-8")
    git("add", "-A", cwd=root)
    git("commit", "-m", "init", cwd=root)
    return root


def add_worktree(primary: Path, branch: str) -> Path:
    path = primary.parent / f"project--{branch}"
    git("worktree", "add", "-b", branch, str(path), "main", cwd=primary)
    return path


def context_of(path: Path) -> dict:
    return json.loads((path / ".specify" / "run-context.json").read_text("utf-8"))


def test_writes_canonical_copy_into_the_worktree(primary):
    worktree = add_worktree(primary, "005-user-auth")
    run_script(
        "--branch", "005-user-auth",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(worktree),
        "--base-ref", "origin/main",
        cwd=primary,
    )

    context = context_of(worktree)
    assert context["branch"] == "005-user-auth"
    assert context["worktree_path"] == str(worktree)
    assert context["primary_path"] == str(primary)
    assert context["base_ref"] == "origin/main"
    assert context["worktree_isolation"] == "created"
    assert context["session"] == "primary"


def test_feature_dir_defaults_into_the_worktree_not_the_primary(primary):
    """The whole failure mode is a later step resolving a path in the primary."""
    worktree = add_worktree(primary, "005-user-auth")
    run_script(
        "--branch", "005-user-auth",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(worktree),
        cwd=primary,
    )

    feature_dir = Path(context_of(worktree)["feature_dir"])
    assert feature_dir == worktree / "specs" / "005-user-auth"
    assert feature_dir.is_absolute()


def test_explicit_feature_dir_is_absolutized(primary):
    worktree = add_worktree(primary, "005-user-auth")
    (worktree / "specs" / "005-auth-v2").mkdir(parents=True)
    run_script(
        "--branch", "005-user-auth",
        "--isolation", "created",
        "--session", "worktree",
        "--worktree-path", str(worktree),
        "--feature-dir", "specs/005-auth-v2",
        cwd=worktree,
    )

    assert Path(context_of(worktree)["feature_dir"]) == worktree / "specs" / "005-auth-v2"


def test_pointer_copy_lets_a_primary_session_find_the_worktree(primary):
    """session=primary is the normal unattended outcome; it has no other clue."""
    worktree = add_worktree(primary, "005-user-auth")
    result = run_script(
        "--branch", "005-user-auth",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(worktree),
        cwd=primary,
    )

    assert "POINTER_STATUS=written" in result.stdout
    pointer = context_of(primary)
    assert pointer["worktree_path"] == str(worktree)
    assert pointer["feature_dir"] == str(worktree / "specs" / "005-user-auth")


def test_no_worktree_still_pins_the_feature(primary):
    """worktree_isolation=failed is the run that most needs pinning."""
    result = run_script(
        "--branch", "005-user-auth",
        "--isolation", "failed",
        "--session", "primary",
        cwd=primary,
    )

    context = context_of(primary)
    assert context["worktree_path"] == ""
    assert context["feature_dir"] == str(primary / "specs" / "005-user-auth")
    assert "POINTER_STATUS=not-needed" in result.stdout


def test_run_context_is_never_committable(primary):
    worktree = add_worktree(primary, "005-user-auth")
    run_script(
        "--branch", "005-user-auth",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(worktree),
        cwd=primary,
    )

    # ship's brief is "commit every uncommitted change" -- in both trees.
    for tree in (primary, worktree):
        assert ".specify/run-context.json" not in git(
            "status", "--porcelain", cwd=tree
        )


def test_exclude_entry_is_written_once(primary):
    worktree = add_worktree(primary, "005-user-auth")
    exclude = primary / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    # No trailing newline: the pattern must not get glued onto this line.
    exclude.write_text("*.tmp", encoding="utf-8")

    for _ in range(2):
        run_script(
            "--branch", "005-user-auth",
            "--isolation", "created",
            "--session", "primary",
            "--worktree-path", str(worktree),
            cwd=primary,
        )

    lines = exclude.read_text("utf-8").splitlines()
    assert "*.tmp" in lines
    assert lines.count(".specify/run-context.json") == 1


def test_rewriting_the_same_branch_is_idempotent(primary):
    """The command is idempotent (hook + explicit step), so this must be too."""
    worktree = add_worktree(primary, "005-user-auth")
    args = (
        "--branch", "005-user-auth",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(worktree),
    )
    run_script(*args, cwd=primary)
    result = run_script(*args, cwd=primary)

    assert result.returncode == 0
    assert "POINTER_STATUS=refreshed" in result.stdout


def test_a_live_second_run_is_refused_not_silently_repointed(primary):
    """Displacing a live pointer aims the drift at the other run instead."""
    first = add_worktree(primary, "005-user-auth")
    second = add_worktree(primary, "006-chat")
    run_script(
        "--branch", "005-user-auth",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(first),
        cwd=primary,
    )

    result = run_script(
        "--branch", "006-chat",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(second),
        cwd=primary,
        check=False,
    )

    assert result.returncode == 3
    assert "005-user-auth" in result.stderr
    # The first run keeps its pointer...
    assert context_of(primary)["branch"] == "005-user-auth"
    # ...and the second still gets a canonical context of its own.
    assert context_of(second)["branch"] == "006-chat"


def test_force_displaces_a_live_pointer(primary):
    first = add_worktree(primary, "005-user-auth")
    second = add_worktree(primary, "006-chat")
    run_script(
        "--branch", "005-user-auth",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(first),
        cwd=primary,
    )

    result = run_script(
        "--branch", "006-chat",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(second),
        "--force",
        cwd=primary,
    )

    assert "POINTER_STATUS=forced" in result.stdout
    assert "005-user-auth" in result.stderr
    assert context_of(primary)["branch"] == "006-chat"


def test_a_finished_run_leaves_litter_not_a_collision(primary):
    """Otherwise the first feature ever shipped blocks every run after it."""
    first = add_worktree(primary, "005-user-auth")
    second = add_worktree(primary, "006-chat")
    run_script(
        "--branch", "005-user-auth",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(first),
        cwd=primary,
    )

    # The feature merged: worktree removed, branch deleted.
    git("worktree", "remove", "--force", str(first), cwd=primary)
    git("branch", "-D", "005-user-auth", cwd=primary)

    result = run_script(
        "--branch", "006-chat",
        "--isolation", "created",
        "--session", "primary",
        "--worktree-path", str(second),
        cwd=primary,
    )

    assert "POINTER_STATUS=stale-replaced" in result.stdout
    assert context_of(primary)["branch"] == "006-chat"


@pytest.mark.parametrize(
    "args",
    [
        ("--isolation", "created", "--session", "primary"),
        ("--branch", "x", "--session", "primary"),
        ("--branch", "x", "--isolation", "created"),
        ("--branch", "x", "--isolation", "sideways", "--session", "primary"),
        ("--branch", "x", "--isolation", "created", "--session", "elsewhere"),
    ],
)
def test_rejects_incomplete_or_invalid_input(primary, args):
    """A context file with a made-up isolation state is worse than none."""
    result = run_script(*args, cwd=primary, check=False)
    assert result.returncode == 1
    assert not (primary / ".specify" / "run-context.json").exists()
