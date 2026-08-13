"""Tests for acquire-lock.sh and release-lock.sh.

The lockfile is the first line of defence against two concurrent unattended
runs interfering with each other. The properties that matter: a live lock is
refused with exit 3; a stale lock (dead PID) is silently replaced; the same
run can refresh its own lock; an explicit release clears the file only for the
owning run; and the lock file is never committable.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ACQUIRE = (
    REPO_ROOT
    / "extensions"
    / "worktrees"
    / "scripts"
    / "bash"
    / "acquire-lock.sh"
)
RELEASE = (
    REPO_ROOT
    / "extensions"
    / "worktrees"
    / "scripts"
    / "bash"
    / "release-lock.sh"
)

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None,
    reason="needs git and bash",
)


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def acquire(*args: str, cwd: Path, check: bool = True):
    return subprocess.run(
        ["bash", str(ACQUIRE), *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def release(*args: str, cwd: Path, check: bool = True):
    return subprocess.run(
        ["bash", str(RELEASE), *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def lock_of(primary: Path) -> dict:
    return json.loads((primary / ".specify" / "run.lock").read_text("utf-8"))


@pytest.fixture
def primary(tmp_path):
    """A repo with one commit on main, standing in for the primary checkout."""
    root = tmp_path / "project"
    root.mkdir()
    git("init", "-b", "main", cwd=root)
    git("config", "user.email", "test@example.com", cwd=root)
    git("config", "user.name", "Test", cwd=root)
    (root / "README.md").write_text("# project\n", encoding="utf-8")
    git("add", "-A", cwd=root)
    git("commit", "-m", "init", cwd=root)
    return root


def live_pid() -> str:
    """PID of this test process — guaranteed alive for the test's lifetime."""
    return str(os.getpid())


def dead_pid() -> str:
    """PID of a process that has already exited."""
    proc = subprocess.Popen(["sleep", "3600"])
    pid = proc.pid
    proc.terminate()
    proc.wait()
    return str(pid)


# ---------------------------------------------------------------------------
# acquire-lock.sh
# ---------------------------------------------------------------------------

def test_acquires_lock_on_empty_primary(primary):
    result = acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
        cwd=primary,
    )
    assert result.returncode == 0
    assert "LOCK_STATUS=acquired" in result.stdout
    data = lock_of(primary)
    assert data["run_id"] == "20260812T112100Z-005-user-auth"


def test_lock_file_contains_run_id_pid_timestamp(primary):
    acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
        cwd=primary,
    )
    data = lock_of(primary)
    assert "run_id" in data
    assert "pid" in data
    assert "timestamp" in data
    assert data["run_id"] == "20260812T112100Z-005-user-auth"
    assert isinstance(data["pid"], int)


def test_live_lock_is_refused_with_exit_3(primary):
    """A second concurrent run with a live PID is refused."""
    acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
        cwd=primary,
    )

    result = acquire(
        "--run-id", "20260812T112530Z-006-chat",
        "--pid", live_pid(),
        cwd=primary,
        check=False,
    )

    assert result.returncode == 3
    assert "20260812T112100Z-005-user-auth" in result.stderr
    # First run's lock is unchanged.
    assert lock_of(primary)["run_id"] == "20260812T112100Z-005-user-auth"


def test_stale_lock_is_replaced(primary):
    """A lock with a dead PID is treated as litter and replaced."""
    stale = dead_pid()
    acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", stale,
        cwd=primary,
    )

    result = acquire(
        "--run-id", "20260812T112530Z-006-chat",
        "--pid", live_pid(),
        cwd=primary,
    )

    assert result.returncode == 0
    assert "LOCK_STATUS=stale-replaced" in result.stdout
    assert lock_of(primary)["run_id"] == "20260812T112530Z-006-chat"


def test_same_run_refreshes_idempotently(primary):
    """The command is idempotent: re-acquiring the same run_id succeeds."""
    args = (
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
    )
    acquire(*args, cwd=primary)
    result = acquire(*args, cwd=primary)

    assert result.returncode == 0
    assert "LOCK_STATUS=refreshed" in result.stdout


def test_force_displaces_a_live_lock(primary):
    """--force is for operator cleanup, never for races — but it must work."""
    acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
        cwd=primary,
    )

    result = acquire(
        "--run-id", "20260812T112530Z-006-chat",
        "--pid", live_pid(),
        "--force",
        cwd=primary,
    )

    assert result.returncode == 0
    assert "LOCK_STATUS=forced" in result.stdout
    assert lock_of(primary)["run_id"] == "20260812T112530Z-006-chat"


def test_lock_file_is_never_committable(primary):
    """ship's brief is 'commit every uncommitted change' — the lock must not land there."""
    acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
        cwd=primary,
    )

    status = git("status", "--porcelain", cwd=primary)
    assert ".specify/run.lock" not in status


def test_exclude_entry_written_once(primary):
    """Re-running must not duplicate the gitignore entry."""
    exclude = primary / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("*.tmp", encoding="utf-8")

    args = ("--run-id", "20260812T112100Z-005-user-auth", "--pid", live_pid())
    acquire(*args, cwd=primary)
    acquire(*args, cwd=primary)  # second call with same run-id

    lines = exclude.read_text("utf-8").splitlines()
    assert "*.tmp" in lines
    assert lines.count(".specify/run.lock") == 1


def test_json_mode_output(primary):
    result = acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
        "--json",
        cwd=primary,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout.strip())
    assert data["lock_status"] == "acquired"
    assert data["run_id"] == "20260812T112100Z-005-user-auth"


def test_rejects_missing_run_id(primary):
    result = acquire("--pid", live_pid(), cwd=primary, check=False)
    assert result.returncode == 1
    assert not (primary / ".specify" / "run.lock").exists()


# ---------------------------------------------------------------------------
# release-lock.sh
# ---------------------------------------------------------------------------

def test_release_removes_own_lock(primary):
    acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
        cwd=primary,
    )

    result = release("--run-id", "20260812T112100Z-005-user-auth", cwd=primary)

    assert result.returncode == 0
    assert "RELEASE_STATUS=released" in result.stdout
    assert not (primary / ".specify" / "run.lock").exists()


def test_release_does_not_touch_anothers_lock(primary):
    """Removing another run's lock would allow a new run to acquire it unchecked."""
    acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
        cwd=primary,
    )

    result = release("--run-id", "20260812T112530Z-006-chat", cwd=primary)

    assert result.returncode == 0
    assert "RELEASE_STATUS=not-ours" in result.stdout
    # The first run's lock is still in place.
    assert lock_of(primary)["run_id"] == "20260812T112100Z-005-user-auth"


def test_release_with_no_lock_is_a_noop(primary):
    result = release("--run-id", "20260812T112100Z-005-user-auth", cwd=primary)

    assert result.returncode == 0
    assert "RELEASE_STATUS=not-held" in result.stdout


def test_release_rejects_missing_run_id(primary):
    result = release(cwd=primary, check=False)
    assert result.returncode == 1


def test_release_json_mode(primary):
    acquire(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--pid", live_pid(),
        cwd=primary,
    )

    result = release(
        "--run-id", "20260812T112100Z-005-user-auth",
        "--json",
        cwd=primary,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout.strip())
    assert data["release_status"] == "released"
