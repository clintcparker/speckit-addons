"""Tests that every workflow step is told to make its artifacts trackable.

The workflows commit evidence — screenshots, review reports, QA reports, ship
records — under the feature directory, and the pull request links those paths.
Target repos routinely ignore `specs/*/screenshots/` and `specs/*/releases/` for
unrelated reasons, so `git add` silently drops them and the PR's own links 404
(issue #7). Every step that hit this re-discovered it and reached for
`git add -f`, which stages one commit and leaves the next step, the next run and
the reviewer's checkout facing exactly the same rule.

The fix is a per-step ARTIFACT VISIBILITY block that resolves it once, in a
committed file: a negation in `<feature_dir>/.gitignore`, which outranks the repo
root's. These workflows are prose with no step-output templating, so — exactly as
for WORKTREE DISCIPLINE in test_workflow_isolation.py — the invariant holds only
while *every* step carries it, and the way it breaks is one step missing the
block.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_IDS = ("send-it", "send-it-checked", "yolo")
CAPTURE_COMMAND = REPO_ROOT / "extensions" / "screenshots" / "commands" / "capture.md"


def steps(workflow_id: str) -> list[tuple[str, str]]:
    path = REPO_ROOT / "workflows" / workflow_id / "workflow.yml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [(s["id"], s["input"]["args"]) for s in workflow["steps"]]


def all_steps() -> list[tuple[str, str, str]]:
    return [(wid, sid, args) for wid in WORKFLOW_IDS for sid, args in steps(wid)]


# The worktree step runs before the feature directory exists, so it has no
# artifacts of its own to make visible.
LATER_STEPS = [case for case in all_steps() if case[1] != "worktree"]
IDS = [f"{wid}:{sid}" for wid, sid, _ in LATER_STEPS]


@pytest.mark.parametrize("workflow_id,step_id,args", LATER_STEPS, ids=IDS)
def test_every_later_step_states_the_visibility_invariant(workflow_id, step_id, args):
    assert "ARTIFACT VISIBILITY" in args


@pytest.mark.parametrize("workflow_id,step_id,args", LATER_STEPS, ids=IDS)
def test_every_later_step_says_how_to_detect_and_how_to_fix(
    workflow_id, step_id, args
):
    """Detection is check-ignore; the fix is a negation in the feature dir."""
    assert "check-ignore" in args
    assert "<feature_dir>/.gitignore" in args
    assert "!<subdir>/" in args


@pytest.mark.parametrize("workflow_id,step_id,args", LATER_STEPS, ids=IDS)
def test_every_later_step_forbids_the_force_add(workflow_id, step_id, args):
    """`git add -f` is the workaround this block exists to displace."""
    assert "never `git add -f`" in args


@pytest.mark.parametrize("workflow_id", ["send-it", "send-it-checked"])
def test_ship_checks_the_linked_images_are_in_the_pushed_head(workflow_id):
    """A link to an image that was never committed is a 404 in the PR body."""
    args = dict(steps(workflow_id))["ship"]
    assert "ls-tree" in args
    assert "404" in args


def test_the_capture_command_owns_its_own_directory():
    """The extension resolves the conflict for screenshots/ without the workflow."""
    text = CAPTURE_COMMAND.read_text(encoding="utf-8")
    assert "### 2. Make the screenshots directory trackable" in text
    assert 'git check-ignore -v -- "$FEATURE_DIR/screenshots/"' in text
    assert "!screenshots/" in text


def test_the_capture_command_steps_are_numbered_consecutively():
    """Inserting step 2 renumbered the rest; a repeat or a gap misdirects."""
    headings = [
        line for line in CAPTURE_COMMAND.read_text(encoding="utf-8").splitlines()
        if line.startswith("### ")
    ]
    numbers = [int(h.removeprefix("### ").split(".", 1)[0]) for h in headings]
    assert numbers == list(range(1, len(numbers) + 1))
