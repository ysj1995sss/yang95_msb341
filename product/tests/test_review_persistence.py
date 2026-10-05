"""Tailor reviews survive a new session (decision 027). Synthetic data only."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from resume_tailorer.analyzers.gap_analyzer import GapCategory, GapItem, GapReport
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.models import ArtifactValidation, FidelityMode, ValidationStatus
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
