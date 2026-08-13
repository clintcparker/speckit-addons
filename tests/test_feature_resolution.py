"""Tests that nothing here answers "which feature is this?" from the checkout.

Two failure modes, both observed in real runs and both filed as issue #8.

`check-prerequisites.sh --json` validates before it reports, and `plan.md` is one
of its gates: it exits 1 for every feature that never ran `/speckit-plan`. The
capture command's step 1 called exactly that form and had no fallback, so a
spec-less feature blocked the screenshot pass outright. `--paths-only` is the
same resolution with no validation — and, unlike the plain form, without the
`.specify/feature.json` write on the way past.

The other direction is worse because it succeeds. With no `SPECIFY_FEATURE_DIRECTORY`
in the environment, `get_feature_paths` falls back to `.specify/feature.json`,
which in the primary checkout right after a merge names the feature that just
shipped. `check-prerequisites.sh` exits 0 on it and `setup-plan.sh` exits 0 and
plants a template `plan.md` in it. So an exit code is not evidence, and every
consumer has to cross-check what a script resolved against what the run pinned.

These are prose assertions for the same reason the ones in test_workflow_isolation.py
are: nothing else in this repo reads these files, so nothing else notices when a
step loses the block.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_IDS = ("send-it", "send-it-checked", "yolo")
CAPTURE_COMMAND = REPO_ROOT / "extensions" / "screenshots" / "commands" / "capture.md"

# Every markdown file this repo ships as agent-facing instructions. A helper
# script invocation in any of them resolves a feature at run time.
COMMAND_FILES = sorted(
    (REPO_ROOT / "extensions").glob("*/commands/*.md")
)


def capture_text() -> str:
    return CAPTURE_COMMAND.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """The body of one `### ` section, up to the next heading of any level."""
    start = text.index(heading)
    rest = text[start + len(heading):]
    end = re.search(r"^#{2,3} ", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def test_step_one_prefers_the_explicit_override():
    """SPECIFY_FEATURE_DIRECTORY is first priority, ahead of anything on disk."""
    body = section(capture_text(), "### 1. Locate the feature")
    order = [
        body.index("$SPECIFY_FEATURE_DIRECTORY"),
        body.index("run-context.json"),
        body.index("check-prerequisites.sh"),
    ]
    assert order == sorted(order)


def test_step_one_falls_back_to_the_run_context():
    body = section(capture_text(), "### 1. Locate the feature")
    assert "run-context.json" in body
    assert "feature_dir" in body
    assert "SPECIFY_INIT_DIR" in body


def test_step_one_uses_the_validation_free_resolution():
    """--paths-only skips the plan.md gate that blocks a spec-less feature."""
    body = section(capture_text(), "### 1. Locate the feature")
    assert "check-prerequisites.sh --paths-only --json" in body
    assert "plan.md not found" in body


@pytest.mark.parametrize("path", COMMAND_FILES, ids=lambda p: p.name)
def test_no_command_resolves_a_feature_with_the_validating_form(path: Path):
    """The plain --json form hard-fails on any feature without a plan.md."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if "check-prerequisites.sh" not in line:
            continue
        assert "--paths-only" in line, f"{path.name}: {line.strip()}"


def test_step_one_cross_checks_the_script_against_the_pinned_feature():
    """Exit 0 is not evidence: the script answers from the checkout, not the run."""
    body = section(capture_text(), "### 1. Locate the feature")
    assert "cross-check" in body
    assert "feature.json" in body
    assert "exiting 0 is not evidence" in body


def test_step_one_fails_loudly_on_a_mismatch_rather_than_picking_a_side():
    body = section(capture_text(), "### 1. Locate the feature")
    assert "Stop and report the disagreement" in body
    assert "naming both paths" in body


def test_step_one_degrades_instead_of_blocking_when_the_script_fails():
    """A spec-less feature is a normal input; a pinned dir is enough to proceed."""
    body = section(capture_text(), "### 1. Locate the feature")
    assert "If source 3 fails outright" in body
    assert "continue with the pinned value" in body


def test_the_ui_relevance_step_tolerates_a_feature_with_no_documents():
    body = section(capture_text(), "### 3. Decide whether the feature is UI-relevant")
    assert "A feature with neither document is not an error here." in body
    assert "capture the baseline anyway" in body
    assert '"spec": "unavailable"' in body


def test_the_constraints_name_both_halves_of_the_invariant():
    text = capture_text()
    assert "A spec-less feature is a supported input, not a failure." in text
    assert "Never adopt a feature the run's own context does not name." in text


def steps(workflow_id: str) -> list[tuple[str, str]]:
    path = REPO_ROOT / "workflows" / workflow_id / "workflow.yml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [(s["id"], s["input"]["args"]) for s in workflow["steps"]]


SCREENSHOT_STEPS = [
    (wid, sid, args)
    for wid in WORKFLOW_IDS
    for sid, args in steps(wid)
    if sid.startswith("screenshots")
]


@pytest.mark.parametrize(
    "workflow_id,step_id,args",
    SCREENSHOT_STEPS,
    ids=[f"{w}:{s}" for w, s, _ in SCREENSHOT_STEPS],
)
def test_screenshot_steps_still_pin_the_feature_for_the_command(
    workflow_id, step_id, args
):
    """The command's source 1 only exists because the step exports it."""
    assert "SPECIFY_FEATURE_DIRECTORY" in args
    assert "run-context.json" in args
    assert "feature_dir" in args
