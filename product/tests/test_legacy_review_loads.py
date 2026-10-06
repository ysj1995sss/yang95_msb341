"""Spec 010 compatibility: a review saved before requirement reviews existed (a real file
written by the pre-spec-010 code, tests/fixtures/ats/legacy_review_format2.json) still loads,
and Tailor can show it with a review worked out now."""

import shutil
from pathlib import Path

from resume_tailorer.review_store import _path, load_review
from resume_tailorer.ui.requirement_review_view import readability_view, review_for_state, review_view

FIXTURE = Path(__file__).parent / "fixtures" / "ats" / "legacy_review_format2.json"


def _load(tmp_path):
    target = _path(str(tmp_path), "greenhouse_1")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE, target)
    return load_review(str(tmp_path), "greenhouse_1")


def test_a_pre_spec_010_review_still_loads(tmp_path):
    state = _load(tmp_path)
    assert state is not None and state["changes"] and "requirement_review" not in state
    assert state["report"].original_alignment is not None  # stored numbers are untouched


def test_tailor_shows_it_with_a_review_worked_out_now(tmp_path):
    state = _load(tmp_path)
    review = review_for_state(state)
    view = review_view(review)
    assert review.computed_from == "now" and "worked out now" in view["note"]
    assert view["groups"] and view["summary"].startswith("Required:")
    readability = readability_view(state["report"].validation.findings, state["source_kind"],
                                   state["report"].validation.checks_run)
    assert all(item["state"] != "ok" or item["label"].startswith(("Text", "Your name")) for item in readability["items"])
