"""Tests that every workflow step carries its worktree-isolation instructions.

These workflows are prose: a step's `args` are the only context it gets, because
the engine has no step-output templating. Isolation therefore holds only while
*every* step is told, in its own args, which tree it belongs to — and the way it
has broken twice is a block present in most steps and missing from one (issue #1
for FEATURE IDENTITY, issue #5 for the working directory). Nothing else in this
repo reads these files, so nothing else notices.

Two failures are asserted apart from that. `git -C <worktree_path>` is an empty
argument on the `worktree_isolation=failed` path, where the run has no worktree
at all; and a `git`/`gh`/test command with no `-C` and no `cd` runs against
whatever the session's working directory is, which unattended is the primary
checkout.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_IDS = ("send-it", "send-it-checked", "yolo")


def load(workflow_id: str) -> dict:
    path = REPO_ROOT / "workflows" / workflow_id / "workflow.yml"
    return yaml.safe_load(path.read_text())


def steps(workflow_id: str) -> list[tuple[str, str]]:
    return [(s["id"], s["input"]["args"]) for s in load(workflow_id)["steps"]]


def all_steps() -> list[tuple[str, str, str]]:
    return [(wid, sid, args) for wid in WORKFLOW_IDS for sid, args in steps(wid)]


def ids(cases) -> list[str]:
    return [f"{wid}:{sid}" for wid, sid, _ in cases]


CASES = all_steps()
LATER_STEPS = [c for c in CASES if c[1] != "worktree"]


@pytest.mark.parametrize("workflow_id,step_id,args", CASES, ids=ids(CASES))
def test_every_step_states_the_worktree_invariant(workflow_id, step_id, args):
    """The invariant reaches every step, the worktree step included."""
    assert "WORKTREE DISCIPLINE" in args


@pytest.mark.parametrize("workflow_id,step_id,args", LATER_STEPS, ids=ids(LATER_STEPS))
def test_later_steps_resolve_the_feature_from_the_run_context(
    workflow_id, step_id, args
):
    assert "run-context.json" in args
    assert "SPECIFY_INIT_DIR" in args


@pytest.mark.parametrize("workflow_id,step_id,args", LATER_STEPS, ids=ids(LATER_STEPS))
def test_later_steps_name_the_tree_and_the_fallback(workflow_id, step_id, args):
    """<tree> is worktree_path, or primary_path when the run has no worktree."""
    assert "<tree>" in args
    assert "primary_path" in args
    assert "git -C <tree>" in args
    # The old spelling breaks on the worktree_isolation=failed path: an empty
    # worktree_path makes `git -C <worktree_path>` an empty argument.
    assert "git -C <worktree_path>" not in args


@pytest.mark.parametrize("workflow_id,step_id,args", LATER_STEPS, ids=ids(LATER_STEPS))
def test_later_steps_treat_a_write_in_the_primary_as_a_failure(
    workflow_id, step_id, args
):
    assert "ALL WRITES HAPPEN IN THIS RUN'S WORKTREE ON THIS RUN'S BRANCH" in args
    assert "FAILED STEP" in args


@pytest.mark.parametrize("workflow_id", ["send-it", "send-it-checked"])
def test_ship_pins_the_head_and_the_base_of_the_pull_request(workflow_id):
    """A PR must never be inferred from the branch the primary is standing on."""
    args = dict(steps(workflow_id))["ship"]
    assert "git -C <tree> push" in args
    assert "--head <branch>" in args
    assert "--base {{ inputs.target_branch }}" in args


@pytest.mark.parametrize("workflow_id", WORKFLOW_IDS)
def test_the_worktree_step_reports_the_path_later_steps_need(workflow_id):
    args = dict(steps(workflow_id))["worktree"]
    assert "worktree_path=<path>" in args


@pytest.mark.parametrize("workflow_id", WORKFLOW_IDS)
def test_catalog_version_matches_the_workflow(workflow_id):
    import json

    catalog = json.loads((REPO_ROOT / "workflows" / "catalog.json").read_text())
    assert (
        catalog["workflows"][workflow_id]["version"]
        == load(workflow_id)["workflow"]["version"]
    )
