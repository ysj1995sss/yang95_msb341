"""Spec 011 batches: tailor several jobs in private sessions, then prepare only the reviewed,
passing ones as "Ready to apply". Nothing is ever submitted. Anonymized data, stubbed model."""

import json
import re

import pytest

from resume_tailorer.applications.models import ApplicationMode, ApplicationStatus
from resume_tailorer.batch import prepare_jobs, review_ready, tailor_job
from resume_tailorer.job_search.job_service import JobService
from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.review_store import load_review, save_review
from tests.test_profile_sync import A1, A2, A3, _docx, _profile


class RewritesTheSqlBullet:
    def complete(self, system, user, max_tokens=2000):
        found = re.search(r'\[\s*\{\s*"paragraph_index"', user)
        if not found:
            return "[]"
        bullets, _ = json.JSONDecoder().raw_decode(user[found.start():])
        out = []
        for b in bullets:
            if b["text"].startswith("Built SQL dashboards"):
                out.append({"paragraph_index": b["paragraph_index"], "change": "rewrite",
                            "new_text": "Built SQL dashboards used weekly by 40 regional managers"})
            else:
                out.append({"paragraph_index": b["paragraph_index"], "change": "keep", "new_text": ""})
        return json.dumps(out)


def _job(n, title):
    return JobPosting(source=JobSource.GREENHOUSE, source_id=str(n), title=title, company=f"Company {n}",
                      location="Remote", url=f"https://example.com/{n}",
                      description=f"{title}.\nRequirements:\n- SQL and dashboard reporting for business partners.\n")


def _fake_pdf(docx_path, pdf_path):
    """A real PDF of the Word file's text, without an office suite."""
    from docx import Document
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(pdf_path, pagesize=letter)
    y = 750
    for paragraph in Document(docx_path).paragraphs:
        pdf.drawString(54, y, paragraph.text[:110])
        y -= 16
    pdf.save()


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    from resume_tailorer.docx_export import converter

    from resume_tailorer.docx_export import pipeline

    monkeypatch.setattr(converter, "_word_platform", lambda: False)
    monkeypatch.setattr(converter, "_soffice", lambda: None)
    monkeypatch.setattr(pipeline, "convert_docx_to_pdf", _fake_pdf)
    service = JobService(db_path=str(tmp_path / "jobs.db"), applications_db_path=str(tmp_path / "apps.db"))
    jobs = [_job(1, "Data Analyst"), _job(2, "Marketing Analyst")]
    for job in jobs:
        service.db.save_job_posting(job)
    yield service, jobs, str(tmp_path / "artifacts")
    service.close()


def test_each_job_is_tailored_in_a_private_session_and_saved(setup):
    service, jobs, artifacts = setup
    for job in jobs:
        tailor_job(job, artifacts_dir=artifacts, original_bytes=_docx(), filename="r.docx",
                   llm=RewritesTheSqlBullet(), career_profile=_profile([A1, A2, A3]))
    for job in jobs:
        state = load_review(artifacts, f"greenhouse_{job.source_id}")
        assert state and state["role"] == job.title


def test_every_batch_review_gets_a_new_revision(setup):
    """A tab still open on an older review must never decide changes in a newer one at the same
    position: batch reviews used to be saved at revision 0 every time (code review, 2026-10-13)."""
    service, jobs, artifacts = setup
    revisions = []
    for _ in range(2):
        tailor_job(jobs[0], artifacts_dir=artifacts, original_bytes=_docx(), filename="r.docx",
                   llm=RewritesTheSqlBullet(), career_profile=_profile([A1, A2, A3]))
        revisions.append(load_review(artifacts, "greenhouse_1")["review_revision"])
    assert 0 < revisions[0] < revisions[1]


def test_prepare_tracks_only_reviewed_jobs_and_never_submits(setup):
    service, jobs, artifacts = setup
    profile = _profile([A1, A2, A3])
    for job in jobs:
        tailor_job(job, artifacts_dir=artifacts, original_bytes=_docx(), filename="r.docx",
                   llm=RewritesTheSqlBullet(), career_profile=profile)
    reviewed = "greenhouse_1"
    state = load_review(artifacts, reviewed)
    state["decided"] = {c.change_id for c in state["changes"]}  # the person reviewed every change
    save_review(artifacts, reviewed, state)

    results = {r.job_id: r for r in prepare_jobs(["greenhouse_1", "greenhouse_2", "nope_9"],
                                                 service=service, profile=profile, artifacts_dir=artifacts)}
    assert results["greenhouse_1"].status == "tracked"
    assert results["greenhouse_2"].status == "review_first" and results["greenhouse_2"].message
    assert results["nope_9"].status == "not_found"

    submissions = service.applications_db.get_submissions_by_job("greenhouse_1")
    assert len(submissions) == 1 and submissions[0].mode == ApplicationMode.MANUAL
    assert service.applications_db.get_current_status(submissions[0].application_id) == ApplicationStatus.READY_TO_APPLY
    assert not service.applications_db.get_submissions_by_job("greenhouse_2")

    again = prepare_jobs(["greenhouse_1"], service=service, profile=profile, artifacts_dir=artifacts)
    assert again[0].status == "already_tracked"


def test_review_ready_explains_why_not():
    assert review_ready(None) == (False, "Not tailored yet.")


# --- spec 014: a tailored resume from an older Career Profile -------------------------------

def test_a_review_remembers_its_profile_and_flags_later_edits(setup):
    import copy

    from resume_tailorer.batch import item_freshness
    from resume_tailorer.freshness import profile_version, review_freshness

    service, jobs, artifacts = setup
    profile = _profile([A1, A2, A3])
    tailor_job(jobs[0], artifacts_dir=artifacts, original_bytes=_docx(), filename="r.docx",
               llm=RewritesTheSqlBullet(), career_profile=profile)
    state = load_review(artifacts, "greenhouse_1")  # saved and loaded: the new keys survive format 2
    assert state["profile_version"] == profile_version(profile) and state["tailored_at"]
    assert review_freshness(state, profile).stale is False

    edited = copy.deepcopy(profile)
    edited.skills.append("Looker")
    fresh = review_freshness(state, edited)
    assert fresh.stale is True and "changed after this was tailored" in fresh.message
    assert item_freshness(artifacts, {"job_id": "greenhouse_1", "status": "done"}, edited)["stale"] is True
    assert item_freshness(artifacts, {"job_id": "greenhouse_2", "status": "failed"}, edited)["stale"] is None

    # Preparing never tracks it: tailor it again first.
    state["decided"] = {c.change_id for c in state["changes"]}
    save_review(artifacts, "greenhouse_1", state)
    (result,) = prepare_jobs(["greenhouse_1"], service=service, profile=edited, artifacts_dir=artifacts)
    assert result.status == "tailor_again" and "Tailor it again first" in result.message
    assert not service.applications_db.get_submissions_by_job("greenhouse_1")
    (result,) = prepare_jobs(["greenhouse_1"], service=service, profile=profile, artifacts_dir=artifacts)
    assert result.status == "tracked"  # the unchanged profile still prepares


def test_reviews_without_a_profile_version_claim_nothing(tmp_path):
    import shutil
    from pathlib import Path

    from resume_tailorer.freshness import review_freshness
    from resume_tailorer.review_store import _path

    fixture = Path(__file__).parent / "fixtures" / "ats" / "legacy_review_format2.json"
    target = _path(str(tmp_path), "greenhouse_1")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture, target)
    legacy = load_review(str(tmp_path), "greenhouse_1")
    assert legacy is not None and "profile_version" not in legacy
    assert review_freshness(legacy, _profile([A1])).stale is None
    assert review_freshness({"profile_version": None}, _profile([A1])).stale is None  # a one-off file run
    assert review_freshness(None, _profile([A1])).stale is None
