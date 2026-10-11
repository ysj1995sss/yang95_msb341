"""Streamlit Apply must withhold a tailored file after the Career Profile changes."""

import hashlib

from resume_tailorer.active_job import remember_handoff
from resume_tailorer.freshness import profile_version
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.profile_import import store_for
from resume_tailorer.review_store import save_review
from tests.test_jobs_page import _click, _search, app  # noqa: F401


def test_streamlit_apply_blocks_a_stale_handoff_from_another_session(app, tmp_path):  # noqa: F811
    _search(app)
    _click(app, "Prepare this application")
    job_id = app.session_state["selected_job_id"]
    store = store_for("local")
    record = store.load()
    source_version = profile_version(CareerTruthProfile.from_dict(record["profile"]))
    pdf = tmp_path / "tailored.pdf"
    pdf.write_bytes(b"%PDF-1.4 synthetic")
    remember_handoff(record, {"job_id": job_id, "pdf_path": str(pdf),
                              "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "version": 2,
                              "validation_status": "PASS", "resume_match_score": 0.8}, True)
    record["profile"]["summary"] = "Corrected profile summary."
    store.save(record)
    assert save_review(app.session_state["artifacts_dir"], job_id, {"profile_version": source_version, "changes": []})

    app.switch_page("pages/3_Applications.py").run()
    assert not app.exception, app.exception
    track = next(b for b in app.button if b.label == "Track this application")
    assert track.disabled
    text = "\n".join(m.value for m in app.markdown)
    assert "Tailor it again" in text
    assert not app.get("download_button")
    assert "tailored_resume_v2.pdf" not in "\n".join(code.value for code in app.code)
    assert app.session_state["job_service"].applications_db.get_submissions_by_job(job_id) == []


def test_streamlit_keeps_an_old_pdf_blocked_when_another_frontend_updates_the_review(app, tmp_path):  # noqa: F811
    _search(app)
    _click(app, "Prepare this application")
    job_id = app.session_state["selected_job_id"]
    store = store_for("local")
    record = store.load()
    old_pdf = tmp_path / "old.pdf"
    old_pdf.write_bytes(b"%PDF-1.4 old synthetic resume")
    old_handoff = {"job_id": job_id, "pdf_path": str(old_pdf),
                   "sha256": hashlib.sha256(old_pdf.read_bytes()).hexdigest(), "version": 1,
                   "validation_status": "PASS", "resume_match_score": 0.8}
    remember_handoff(record, old_handoff, True)
    store.save(record)
    app.switch_page("pages/3_Applications.py").run()
    assert not app.exception, app.exception
    assert not next(b for b in app.button if b.label == "Track this application").disabled

    # The other frontend corrects the profile and tailors a new PDF. This Streamlit session
    # still holds its original in-memory handoff, even after it reloads the stored profile.
    record = store.load()
    record["profile"]["summary"] = "Corrected profile summary."
    new_bytes = b"%PDF-1.4 updated synthetic resume"
    new_pdf = tmp_path / "new.pdf"
    new_pdf.write_bytes(new_bytes)
    remember_handoff(record, {**old_handoff, "pdf_path": str(new_pdf),
                              "sha256": hashlib.sha256(new_bytes).hexdigest(), "version": 2}, True)
    store.save(record)
    assert save_review(app.session_state["artifacts_dir"], job_id, {
        "changes": [], "pdf_bytes": new_bytes, "version": 2,
        "profile_version": profile_version(CareerTruthProfile.from_dict(record["profile"])),
    })
    app.run()
    assert not app.exception, app.exception
    assert next(b for b in app.button if b.label == "Track this application").disabled
    assert "Open Tailor" in "\n".join(m.value for m in app.markdown)
    assert not app.get("download_button")
    assert "tailored_resume_v1.pdf" not in "\n".join(code.value for code in app.code)
    assert app.session_state["job_service"].applications_db.get_submissions_by_job(job_id) == []
