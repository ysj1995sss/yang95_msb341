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
    assert detail.strong == () and "Match not assessed" in detail.summary


def _work_authorization_review():
    from resume_tailorer.analyzers.requirement_review import DIRECT, NONE, RequirementReview, RequirementRow

    gate = RequirementRow("r1", "Must be authorized to work in the U.S. without sponsorship.", "required", True, NONE,
                          (), (), "A required credential, license or degree that isn't in your Career Profile.")
    sql = RequirementRow("r2", "Advanced SQL", "required", False, DIRECT, ("SQL",), (), "SQL shown.")
    return RequirementReview((gate, sql))


def test_tailor_takes_work_authorization_from_the_persons_answer_like_jobs():
    # Follow-up to dogfood round 4: Tailor still said "No evidence · Hard requirement" and "Missing, never
    # added" for a work authorization question the person hadn't answered.
    from resume_tailorer.ui.requirement_review_view import review_view

    review = _work_authorization_review()
    assert review.summary == "Required: 1 of 1 with evidence"  # eligibility isn't a resume requirement
    for answer, label, gate, missing in (({}, "Not answered in Career Profile", False, False),
                                         ({"authorized_to_work": True}, "You said yes in Career Profile", False, False),
                                         ({"authorized_to_work": False}, "You said no in Career Profile", True, True)):
        row = review_view(review, authorization=answer)["groups"][0]["rows"][0]
        assert (row["label"], row["hard_gate"]) == (label, gate), answer
        assert "Career Profile" in row["reason"]
        assert any("authorized" in m["full"] for m in missing_list(review, authorization=answer)) is missing, answer
