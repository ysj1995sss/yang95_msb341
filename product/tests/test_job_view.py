from datetime import datetime

from resume_tailorer.job_search.models import FitEvidence, FitResult, JobPosting, JobSource
from resume_tailorer.ui.job_view import build_detail, build_row, freshness_text, salary_text


def job(**kw):
    base = dict(source=JobSource.GREENHOUSE, source_id="1", company="Northwind", title="Analyst",
                location="Remote", description="SQL")
    base.update(kw)
    return JobPosting(**base)


def test_unknown_salary_and_fit_are_named_not_zero():
    row = build_row(job(), None, None)
    assert row.salary == "No salary stated"
    assert row.fit == "Fit not assessed" and row.fit_tone == "neutral"
    assert row.status == "New"
    assert "0" not in row.salary


def test_salary_ranges_read_plainly():
    assert salary_text(job(salary_min=90000, salary_max=120000)) == "$90k–$120k"
    assert salary_text(job(salary_min=90000)) == "From $90k"


def test_demo_sources_are_labeled_as_not_real():
    row = build_row(job(source=JobSource.LINKEDIN), None, None)
    assert row.is_demo and "not a real job" in row.source


def test_freshness():
    now = datetime(2026, 10, 4, 12)
    assert freshness_text(None) == "Post date not stated"
    assert freshness_text(datetime(2026, 10, 4, 8), now) == "Posted today"
    assert freshness_text(datetime(2026, 10, 1), now) == "Posted 3 days ago"


def test_detail_separates_evidence_gaps_hard_gates_and_unknowns():
    fit = FitResult(
        overall_fit=55.0, eligibility=40.0,
        strong_matches=["sql"], partial_matches=["stakeholder management"],
        true_gaps=["kubernetes", "experience: 8+ years"], unknown=["preferred unmet: go"],
        evidence=[FitEvidence("sql", "direct", "Built weekly SQL reports")],
    )
    detail = build_detail(job(sponsorship_available=False), fit, "save", {"sponsorship_required": True})
    assert detail.strong[0].evidence == "Built weekly SQL reports"
    assert detail.gaps == ("kubernetes",)
    assert any("8+ years" in g for g in detail.hard_gates)
    assert any("sponsor" in g for g in detail.hard_gates)
    assert detail.unknowns == ("Salary was not stated", "Preferred, not in your profile: go")
    assert "hard" in detail.summary


def test_no_sponsorship_is_not_a_gate_when_the_user_does_not_need_it():
    detail = build_detail(job(sponsorship_available=False), None, None, {"sponsorship_required": False})
    assert detail.hard_gates == ()
    assert detail.summary.startswith("Fit not assessed")


def test_unknown_salary_sponsorship_and_fit_are_named_as_unknowns():
    detail = build_detail(job(), None, None, {})
    assert detail.unknowns == ("Salary was not stated", "Sponsorship was not stated",
                               "Fit couldn't be assessed from what the posting says")
