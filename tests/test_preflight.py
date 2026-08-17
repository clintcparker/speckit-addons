"""Tests that each workflow checks its extensions are installed before it starts.

A workflow step names a command; the engine resolves that name at dispatch. When
the extension providing it is not installed, the dispatch does not fail the run —
it reports `Unknown command: /speckit-<name>` and the workflow proceeds to the
next step and finishes with status "completed". An observed send-it-checked run
lost `review`, `qa` and `ship` exactly that way: 93 minutes of work, a branch, no
review, no QA report, no pull request, a run lock held to its TTL, and a run
status of "completed" over the top of all of it.

`requires:` cannot express the dependency — it recognizes only `speckit_version`
and `integrations`, and an unknown key is a validation error — so the check lives
in prose, in the first step's args, where it costs a listing of
`.specify/extensions/` and stops before the lock is taken.

These are prose assertions for the same reason the ones in
test_workflow_isolation.py are: nothing else in this repo reads these files, so
nothing else notices when a step is added and the preflight is not updated with
the extension it depends on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_IDS = ("send-it", "send-it-checked", "yolo")

# The command that IS the first step. A run that reaches the preflight has
# already proved this extension is installed, so listing it as required would be
# a check that can never fire.
SELF_PROVIDED = "worktrees"


def load(workflow_id: str) -> dict:
    path = REPO_ROOT / "workflows" / workflow_id / "workflow.yml"
    return yaml.safe_load(path.read_text())


def first_step(workflow_id: str) -> dict:
    return load(workflow_id)["steps"][0]


def extension_id_for(command: str) -> str | None:
    """The extension id a dispatched command name implies, or None for core.

    Core spec-kit commands are two segments (`speckit.specify`); an extension's
    are three (`speckit.staff-review.run`), and the middle one is the id every
    installed extension is a directory name for under `.specify/extensions/`.
    """
    parts = command.split(".")
    return parts[1] if len(parts) == 3 else None


def required_extensions(workflow_id: str) -> set[str]:
    ids = {
        extension_id_for(step["command"]) for step in load(workflow_id)["steps"]
    }
    ids.discard(None)
    ids.discard(SELF_PROVIDED)
    return ids  # type: ignore[return-value]


@pytest.mark.parametrize("workflow_id", WORKFLOW_IDS)
def test_the_first_step_carries_a_preflight(workflow_id):
    """Nothing earlier than step 1 exists to check, so step 1 has to."""
    step = first_step(workflow_id)
    assert step["id"] == "worktree"
    assert "PREFLIGHT" in step["input"]["args"]


@pytest.mark.parametrize("workflow_id", WORKFLOW_IDS)
def test_the_preflight_runs_before_the_lock(workflow_id):
    """A run that stops at preflight must not have taken the lock first.

    Acquiring it and then stopping blocks the next run against this primary
    checkout for lock_ttl_minutes — 240 by default — over a missing extension
    the user could have installed in a minute.
    """
    args = first_step(workflow_id)["input"]["args"]
    assert args.index("PREFLIGHT") < args.index("ACQUIRE LOCK")


@pytest.mark.parametrize("workflow_id", WORKFLOW_IDS)
def test_the_preflight_names_every_extension_a_later_step_dispatches(workflow_id):
    """Adding a step without adding its extension here is the regression."""
    args = first_step(workflow_id)["input"]["args"]
    missing = [ext for ext in required_extensions(workflow_id) if ext not in args]
    assert not missing, (
        f"{workflow_id} dispatches commands from {sorted(missing)} but its "
        f"preflight never names them — a missing one would be discovered at "
        f"dispatch, after the run has already spent its time"
    )


@pytest.mark.parametrize("workflow_id", WORKFLOW_IDS)
def test_a_workflow_with_required_extensions_says_to_stop(workflow_id):
    """Reporting a missing extension and continuing is the failure, not the fix."""
    args = first_step(workflow_id)["input"]["args"]
    if not required_extensions(workflow_id):
        pytest.skip("no extension-provided commands after the first step")
    assert "STOP HERE" in args


@pytest.mark.parametrize("workflow_id", WORKFLOW_IDS)
def test_the_preflight_covers_the_git_extension(workflow_id):
    """`git` is a script dependency, not a dispatched command, so it needs saying.

    `create-worktree.sh --from-description` shells out to the git extension's
    `create-new-feature-branch.sh` and exits 1 without it. That is a degraded
    run, not a failed one — but the branch number then comes from the agent
    rather than from the numbering the rest of the repo uses, which is a fact
    about the branch that has to reach the report.
    """
    args = first_step(workflow_id)["input"]["args"]
    assert "git_extension=absent" in args


SHIPPERS = [w for w in WORKFLOW_IDS if "ship" in required_extensions(w)]


@pytest.mark.parametrize("workflow_id", SHIPPERS)
def test_ship_surfaces_a_hand_derived_branch_number(workflow_id):
    """The worktree step's report only matters if it reaches the pull request."""
    ship = [s for s in load(workflow_id)["steps"] if s["id"] == "ship"]
    assert ship, f"{workflow_id} requires `ship` but has no ship step"
    assert "git_extension=absent" in ship[0]["input"]["args"]
