"""Tailor reviews survive a new session (decision 027). Synthetic data only."""

from pathlib import Path
from dataclasses import replace

import pytest

from streamlit.testing.v1 import AppTest

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


def _open_tailor(monkeypatch, tmp_path):
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[PENDING_TAILOR_JOB_KEY] = dict(JOB)
    at.switch_page("pages/5_Tailor.py")
    at.run()
    assert not at.exception, at.exception
    return at


def test_a_new_session_reopens_the_saved_review(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    save_review(artifacts_dir("local"), JOB["job_id"], _state())

    at = _open_tailor(monkeypatch, tmp_path)
    text = "\n".join(m.value for m in at.markdown)
    assert "Create your tailored resume" not in text
    assert "Missing, never added" in text
    assert "Kubernetes administration" in text and "ideally at scale" not in text  # short label

    # A decision made here is on disk for the next session.
    state = at.session_state["artifact_run_state"]
    change_id = state["changes"][0].change_id
    state["dispositions"][change_id] = "REJECTED"
    state["decided"].add(change_id)
    at.run()
    saved = load_review(artifacts_dir("local"), JOB["job_id"])
    assert change_id in saved["decided"] and saved["dispositions"][change_id] == "REJECTED"


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


def test_streamlit_shows_review_mode_before_start(tmp_path, monkeypatch):
    at = _open_tailor(monkeypatch, tmp_path)
    choice = next(item for item in at.radio if item.label == "Who reviews proposed changes?")
    assert choice.value == "I'll review changes"
    assert "AI-assisted review" in choice.options


def test_streamlit_full_review_and_selected_only_batch_choice(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    folder = artifacts_dir("local")
    assert save_review(folder, JOB["job_id"], _two_change_state())
    at = _open_tailor(monkeypatch, tmp_path)
    queue = next(item for item in at.selectbox if item.label == "Review queue")
    assert "Built SQL dashboards" in queue.options[0]
    assert "Led customer surveys" in queue.options[1]
    shown = "\n".join(item.value for item in at.text)
    assert "Built weekly SQL dashboards" in shown and "Led customer survey analysis" in shown
    selected = next(item for item in at.multiselect if item.label == "Select changes to decide together")
    selected.set_value(["paragraph:2"]).run()
    at.button(key="tailor_batch_reject").click().run()
    assert not at.exception, at.exception
    saved = load_review(folder, JOB["job_id"])
    assert saved["decided"] == {"paragraph:2"}
    assert saved["dispositions"]["paragraph:2"] == "REJECTED"
    assert saved["review_revision"] == 1
    assert saved["decision_origins"]["paragraph:2"]["by"] == "person"


def test_streamlit_stale_batch_choice_never_overwrites_newer_review(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    folder = artifacts_dir("local")
    assert save_review(folder, JOB["job_id"], _two_change_state())
    at = _open_tailor(monkeypatch, tmp_path)
    next_item = _decision_module().mutate_saved_review(
        folder, JOB["job_id"], 0, [("paragraph:1", "REJECTED")], "person")
    assert next_item["review_revision"] == 1
    selected = next(item for item in at.multiselect if item.label == "Select changes to decide together")
    selected.set_value(["paragraph:2"]).run()
    at.button(key="tailor_batch_accept").click().run()
    assert not at.exception, at.exception
    saved = load_review(folder, JOB["job_id"])
    assert saved["decided"] == {"paragraph:1"}
    assert saved["review_revision"] == 1


def test_streamlit_unsaved_local_edit_does_not_replace_newer_disk_review(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    folder = artifacts_dir("local")
    assert save_review(folder, JOB["job_id"], _two_change_state())
    at = _open_tailor(monkeypatch, tmp_path)
    _decision_module().mutate_saved_review(
        folder, JOB["job_id"], 0, [("paragraph:1", "REJECTED")], "person")
    at.session_state["artifact_run_state"]["manual_texts"]["paragraph:2"] = "Unsaved local wording"
    at.run()
    assert not at.exception, at.exception
    saved = load_review(folder, JOB["job_id"])
    assert saved["decided"] == {"paragraph:1"}
    assert saved["review_revision"] == 1
    assert "paragraph:2" not in saved["manual_texts"]


def test_streamlit_legacy_decision_does_not_invent_an_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    folder = artifacts_dir("local")
    state = _two_change_state()
    state["dispositions"]["paragraph:1"] = "REJECTED"
    state["decided"].add("paragraph:1")
    assert save_review(folder, JOB["job_id"], state)
    at = _open_tailor(monkeypatch, tmp_path)
    text = "\n".join(item.value for item in [*at.markdown, *at.caption])
    assert "Origin not recorded" in text
    assert "Chosen by you" not in text
