"""Spec 011: Jobs and Tailor show the same gaps, from the requirement review. Anonymized."""

from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.requirement_review import build_review
from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.ui.job_view import build_detail
from resume_tailorer.ui.requirement_review_view import missing_list
from tests.fixtures.ats import POSTING, PROVENANCE, profile


def _job():
    return JobPosting(source=JobSource.GREENHOUSE, source_id="1", title="Senior Marketing Analyst",
                      company="Northwind Outdoor", location="Remote", description=POSTING, url="https://example.com/1")


def test_jobs_panel_lists_come_from_the_review():
    review = build_review(JobAnalyzer().analyze(POSTING), profile(), provenance=PROVENANCE, posting=POSTING)
    detail = build_detail(_job(), None, None, {}, None, review=review)
    strong = " ".join(e.requirement for e in detail.strong)
    partial = " ".join(e.requirement for e in detail.partial)
    assert "SQL" in strong and "project management" in partial.lower()
    assert any("Tableau" in g for g in detail.gaps)
    assert any("CPA" in h for h in detail.hard_gates)  # the hard requirement, from the review
    assert any(u.startswith("Only listed in your skills") and "Snowflake" in u for u in detail.unknowns)
    assert any(u.startswith("Not confirmed yet") and "Salesforce" in u for u in detail.unknowns)
    assert any(u.startswith("Check yourself") for u in detail.unknowns)


def test_tailor_missing_list_agrees_with_the_jobs_gaps():
    review = build_review(JobAnalyzer().analyze(POSTING), profile(), provenance=PROVENANCE, posting=POSTING)
    detail = build_detail(_job(), None, None, {}, None, review=review)
    missing = [m["full"] for m in missing_list(review)]
    for gap in detail.gaps:
        assert any(gap.lower()[:15] in full.lower() for full in missing)
    # A requirement Jobs counts as supported is never listed as missing in Tailor.
    supported = [r.text for r in review.rows if r.supported]
    assert not set(missing) & set(supported) or all(r.status == "partial" for r in review.rows if r.text in missing)


def test_without_a_review_the_jobs_panel_behaves_as_before():
    detail = build_detail(_job(), None, None, {}, None)
    assert detail.strong == () and "Fit not assessed" in detail.summary
