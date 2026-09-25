"""Tests for APPLY → Step 10 tailor snapshot handoff helpers."""

from resume_tailorer.job_search.candidate_fit import CandidateFitScorer
from resume_tailorer.job_search.job_service import build_tailor_snapshot
from resume_tailorer.job_search.models import FitResult, JobPosting, JobSource
from resume_tailorer.models.career_profile import CareerTruthProfile, WorkExperience


def test_build_tailor_snapshot_includes_fit_and_description():
    job = JobPosting(
        source=JobSource.GREENHOUSE,
        source_id="99",
        company="Acme",
        title="Associate",
        location="Remote",
        description="Full JD text here with Python.",
        url="https://example.com/jobs/99",
    )
    fit = FitResult(
        overall_fit=72.0,
        eligibility=80.0,
        core_capabilities=70.0,
        preferred_qualifications=None,
        evidence_confidence=90.0,
        strong_matches=["Python"],
        scoring_version="cf-v2",
    )
    snap = build_tailor_snapshot(job, fit)
    assert snap["description"] == "Full JD text here with Python."
    assert snap["job_id"] == "greenhouse_99"
    assert snap["company"] == "Acme"
    assert snap["candidate_fit"]["scoring_version"] == "cf-v2"
    assert snap["candidate_fit"]["overall_fit"] == 72.0
    assert "selected_at" in snap


def test_build_tailor_snapshot_from_live_scorer():
    profile = CareerTruthProfile(
        contact_info={"name": "A", "email": "a@example.com"},
        education=[],
        work_experience=[
            WorkExperience(
                employer="Corp",
                title="Eng",
                dates="2020-2023",
                responsibilities=["Python APIs"],
                accomplishments=[],
            )
        ],
        skills=["Python"],
        tools=[],
        certifications=[],
        accomplishments=[],
    )
    job = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="1",
        company="Co",
        title="Eng",
        location="Remote",
        description="Requirements: Python",
    )
    fit = CandidateFitScorer().score_fit_detailed(profile, job)
    snap = build_tailor_snapshot(job, fit)
    assert snap["candidate_fit"]["scoring_version"] == "cf-v2"
