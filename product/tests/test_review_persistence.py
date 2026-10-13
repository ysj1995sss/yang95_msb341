"""Tailor reviews survive a new session (decision 027). Synthetic data only."""

from pathlib import Path
from dataclasses import replace

import pytest


from resume_tailorer.analyzers.gap_analyzer import GapCategory, GapItem, GapReport
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.models import ArtifactValidation, ChangeCategory, FidelityMode, ValidationStatus
from resume_tailorer.artifacts.report import build_final_report
from resume_tailorer.identity import artifacts_dir
from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.review_store import discard_review, load_review, save_review, signature

APP = str(Path(__file__).resolve().parent.parent / "resume_tailorer" / "app.py")
JOB = {"job_id": "greenhouse_7", "title": "Data Analyst", "company": "Acme", "description": "SQL dashboards"}


def _state():
    profile = CareerTruthProfile(
        contact_info={"name": "Riley Park"}, education=[],
        work_experience=[WorkExperience(employer="Example Co", title="Analyst", dates="2022-2025",
                                        responsibilities=[], accomplishments=["Built SQL dashboards for sales"])],
        skills=["SQL"], tools=[], certifications=[], accomplishments=[],
    )
    gaps = GapReport(items=[
        GapItem("SQL dashboards", GapCategory.B, "Supported", "Built SQL dashboards for sales"),
        GapItem("Strong experience with Kubernetes administration, ideally at scale.", GapCategory.E, "Missing", "None"),
    ], summary="")
    changes = build_freeform_changes(profile, "- Built SQL dashboards for the sales team\n", gaps)
    report = build_final_report(candidate_fit=0.7, fit_breakdown={}, original_alignment=0.5, tailored_alignment=0.7,
                                gap_report=gaps, validation=ArtifactValidation(status=ValidationStatus.PASS),
                                artifacts=(), company="Acme", role="Data Analyst",
                                fidelity_mode=FidelityMode.RECONSTRUCTED, unsupported_claims=())
    return {
        "source_kind": "PDF", "original_bytes": b"x", "baseline_text": "", "target_length": "preserve",
        "style_hints": {}, "profile": profile, "gap_report": gaps, "job_analysis": None,
        "original_alignment": 0.5, "candidate_fit": 0.7, "company": "Acme", "role": "Data Analyst",
        "fidelity_mode": FidelityMode.RECONSTRUCTED, "changes": changes, "dispositions": {}, "manual_texts": {},
        "decided": set(), "dirty": False, "tailored_text": "Riley Park", "validation": report.validation,
        "docx_bytes": None, "pdf_bytes": b"%PDF-1.4", "report": report, "candidate_name": "Riley Park",
        "reviewed": False, "version": 2,
    }


def test_store_round_trip_and_discard(tmp_path):
    state = _state()
    state["decided"].add("c1")
    assert save_review(str(tmp_path), "job-1", state)
    loaded = load_review(str(tmp_path), "job-1")
    assert signature(loaded) == signature(state) and loaded["version"] == 2
    assert load_review(str(tmp_path), "job-2") is None
    discard_review(str(tmp_path), "job-1")
    assert load_review(str(tmp_path), "job-1") is None


def test_an_unreadable_file_is_ignored(tmp_path):
    save_review(str(tmp_path), "job-1", _state())
    (next((tmp_path / "reviews").iterdir())).write_bytes(b"not a review")
    assert load_review(str(tmp_path), "job-1") is None


def test_the_file_is_readable_json_with_a_real_job_analysis(tmp_path):
    import json

    from resume_tailorer.analyzers.job_analyzer import JobAnalyzer

    state = _state()
    state["job_analysis"] = JobAnalyzer().analyze(
        "Data Analyst. Requirements: 3+ years of SQL and Tableau. Preferred: Python.")
    state["decided"].add("c1")
    assert save_review(str(tmp_path), "job-1", state)
    (path,) = (tmp_path / "reviews").iterdir()
    assert path.suffix == ".json"
    assert json.loads(path.read_text(encoding="utf-8"))["format"] == 2
    loaded = load_review(str(tmp_path), "job-1")
    assert loaded["job_analysis"] == state["job_analysis"]
    assert loaded["report"] == state["report"] and loaded["changes"] == state["changes"]
    assert loaded["profile"] == state["profile"] and loaded["decided"] == {"c1"}
    assert loaded["pdf_bytes"] == b"%PDF-1.4"


def test_loading_never_builds_types_from_outside_the_app(tmp_path):
    import json

    from resume_tailorer.review_store import _path

    path = _path(str(tmp_path), "job-1")
    path.parent.mkdir(parents=True)
    evil = {"$dataclass": "subprocess:Popen", "fields": {"args": ["calc"]}}
    path.write_text(json.dumps({"format": 2, "job_id": "job-1", "state": {"$dict": [["changes", evil]]}}))
    assert load_review(str(tmp_path), "job-1") is None


def test_an_old_pickle_review_is_removed_not_loaded(tmp_path):
    import pickle

    from resume_tailorer.review_store import _path

    old = _path(str(tmp_path), "job-1").with_suffix(".review")
    old.parent.mkdir(parents=True)
    old.write_bytes(pickle.dumps({"format": 1, "job_id": "job-1", "state": {"changes": []}}))
    assert load_review(str(tmp_path), "job-1") is None
    assert not old.exists()


def _decision_module():
    import importlib.util

    assert importlib.util.find_spec("resume_tailorer.review_decisions") is not None, "shared decision transaction is missing"
    from resume_tailorer import review_decisions

    return review_decisions


def _two_change_state():
    state = _state()
    source = state["changes"][0]
    first = replace(source, change_id="paragraph:1", section="work_experience", source_index=1,
                    original_text="Built SQL dashboards", proposed_text="Built weekly SQL dashboards",
                    validation_status=ValidationStatus.PASS, category=ChangeCategory.REPHRASED)
    second = replace(first, change_id="paragraph:2", source_index=2,
                     original_text="Led customer surveys", proposed_text="Led customer survey analysis")
    state["changes"] = [first, second]
    return state


def test_two_selected_decisions_change_once_without_mutating_the_loaded_state():
    review = _decision_module()
    before = _two_change_state()
    after = review.apply_decisions(before, [("paragraph:1", "ACCEPTED"), ("paragraph:2", "REJECTED")],
                                   origin="person", expected_revision=0)
    assert after["decided"] == {"paragraph:1", "paragraph:2"}
    assert after["dispositions"] == {"paragraph:1": "ACCEPTED", "paragraph:2": "REJECTED"}
    assert after["review_revision"] == 1 and before["decided"] == set()
    assert after["decision_origins"]["paragraph:1"]["by"] == "person"


def test_stale_review_and_invalid_selection_change_nothing():
    review = _decision_module()
    before = _two_change_state()
    with pytest.raises(review.ReviewConflict):
        review.apply_decisions(before, [("paragraph:1", "ACCEPTED")], origin="person", expected_revision=9)
    for entries in ([('unknown', 'ACCEPTED')], [('paragraph:1', 'ACCEPTED'), ('unknown', 'REJECTED')],
                    [('paragraph:1', 'ACCEPTED'), ('paragraph:1', 'REJECTED')]):
        with pytest.raises(review.ReviewSelectionError):
            review.apply_decisions(before, entries, origin="person", expected_revision=0)
    assert before["decided"] == set() and before["dispositions"] == {}


def test_hidden_and_blocked_changes_cannot_be_batch_accepted():
    review = _decision_module()
    state = _two_change_state()
    state["changes"][1] = replace(state["changes"][1],
                                  proposed_text="Strong experience with Kubernetes administration, ideally at scale.")
    from resume_tailorer.ui.tailoring_view import group_changes

    assert group_changes(state["changes"], state["report"].true_gaps).blocked
    with pytest.raises(review.ReviewSelectionError):
        review.apply_decisions(state, [("paragraph:2", "ACCEPTED")], origin="person", expected_revision=0)
    state["changes"][1] = replace(state["changes"][1], proposed_text="Led customer survey analysis",
                                  category=ChangeCategory.UNCHANGED)
    with pytest.raises(review.ReviewSelectionError):
        review.apply_decisions(state, [("paragraph:2", "ACCEPTED")], origin="person", expected_revision=0)
    state["changes"][0] = replace(state["changes"][0], validation_status=ValidationStatus.FAIL)
    with pytest.raises(review.ReviewSelectionError):
        review.apply_decisions(state, [("paragraph:1", "ACCEPTED")], origin="person", expected_revision=0)


def test_retry_is_idempotent_and_legacy_review_defaults_remain_available(tmp_path):
    review = _decision_module()
    folder = tmp_path / "artifacts"
    legacy = _two_change_state()
    assert save_review(str(folder), "job-1", legacy)
    loaded = load_review(str(folder), "job-1")
    assert "review_revision" not in loaded and "review_mode" not in loaded
    first = review.mutate_saved_review(str(folder), "job-1", 0, [("paragraph:1", "REJECTED")], "person")
    again = review.mutate_saved_review(str(folder), "job-1", 1, [("paragraph:1", "REJECTED")], "person")
    assert first["review_revision"] == again["review_revision"] == 1
    assert load_review(str(folder), "job-1")["decided"] == {"paragraph:1"}


def test_failed_save_preserves_previous_review(tmp_path, monkeypatch):
    review = _decision_module()
    folder = tmp_path / "artifacts"
    assert save_review(str(folder), "job-1", _two_change_state())
    monkeypatch.setattr(review, "save_review", lambda *args: False)
    with pytest.raises(review.ReviewStorageError):
        review.mutate_saved_review(str(folder), "job-1", 0, [("paragraph:1", "REJECTED")], "person")
    saved = load_review(str(folder), "job-1")
    assert saved["decided"] == set() and saved.get("review_revision", 0) == 0


def test_a_new_review_never_starts_at_a_revision_an_old_tab_holds():
    # Change ids are positional, so a re-tailored review must not reuse revision 0 (or
    # any earlier run's number) that a stale tab could still send with its selection.
    from resume_tailorer.review_decisions import new_review_revision

    first = new_review_revision()
    assert first > 1_000_000_000_000 and new_review_revision() >= first


@pytest.mark.parametrize("selection", [["paragraph:1", "paragraph:2"], ["paragraph:2"]])
def test_accepting_a_failed_change_names_it_so_the_person_can_unselect_it(selection):
    # Review findings 2 and 5: "Select all unreviewed" then "Accept selected" failed with no
    # hint which change was the problem, and a single Accept was told about a "batch".
    review = _decision_module()
    state = _two_change_state()
    state["changes"][1] = replace(state["changes"][1], validation_status=ValidationStatus.FAIL)
    with pytest.raises(review.ReviewSelectionError) as raised:
        review.apply_decisions(state, [(cid, "ACCEPTED") for cid in selection], origin="person", expected_revision=0)
    message = str(raised.value)
    assert "Led customer surveys" in message and "2." in message
    assert "batch" not in message.lower()


def test_a_saved_review_never_reads_as_missing_while_it_is_being_replaced(tmp_path):
    # Windows: reading a file at the instant os.replace swaps it raises PermissionError, which
    # load_review treated as "no review" (the Tailor page could briefly lose the review).
    import threading

    folder = str(tmp_path / "artifacts")
    state = _state()
    assert save_review(folder, "job-a", state)
    stop, missing = threading.Event(), []

    def writer():
        while not stop.is_set():
            save_review(folder, "job-a", state)

    thread = threading.Thread(target=writer)
    thread.start()
    try:
        for _ in range(400):
            if load_review(folder, "job-a") is None:
                missing.append(1)
    finally:
        stop.set()
        thread.join(10)
    assert missing == []
