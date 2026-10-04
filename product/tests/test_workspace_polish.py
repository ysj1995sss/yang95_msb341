from datetime import date

from resume_tailorer.applications.models import ApplicationStatus as S
from resume_tailorer.applications.weekly import build_weekly_summary, week_bounds
from resume_tailorer.job_search.ui_helpers import JobCardView, fit_tone, missing_line
from resume_tailorer.ui.fact_vault import build_section_completeness, overall_completeness


def _card(fit, gaps=()):
    return JobCardView("C", "T", "L", "", "", fit, "", "", (), (), tuple(gaps))


def test_fit_tone_never_scores_unassessed():
    assert fit_tone("Not assessed")[1] == "neutral"
    assert fit_tone("85%")[1] == "strong"
    assert fit_tone("50%")[1] == "partial"
    assert fit_tone("10%")[1] == "weak"


def test_missing_line_states_gaps_and_unknowns():
    assert "not assessed" in missing_line(_card("Not assessed")).lower()
    assert missing_line(_card("90%")).startswith("No gaps")
    assert missing_line(_card("30%", ["a", "b", "c", "d"])) == "Missing: a, b, c (+1 more)"


def test_section_completeness_reports_what_is_missing():
    profile = {
        "contact_info": {"name": "A", "email": "a@x.com", "phone": "", "location": ""},
        "work_experience": [{"title": "PM", "dates": "", "responsibilities": ["x"], "accomplishments": []}],
        "education": [],
        "skills": ["SQL"],
        "tools": [],
    }
    by = {s.name: s for s in build_section_completeness(profile)}
    assert by["Contact"].percent == 50 and by["Contact"].missing == ("Phone", "Location")
    assert by["Experience"].percent == 50 and by["Experience"].missing == ("PM: dates",)
    assert by["Education"].percent == 0
    assert by["Certifications"].percent is None
    assert 0 < overall_completeness(tuple(by.values())) < 100
    assert overall_completeness(build_section_completeness(None)) == 0


def test_weekly_summary_counts_only_this_week_submissions():
    today = date(2026, 10, 7)  # Wednesday
    assert week_bounds(today) == (date(2026, 10, 5), date(2026, 10, 11))
    entries = [
        (S.APPLIED, date(2026, 10, 6)),
        (S.INTERVIEW, date(2026, 9, 20)),
        (S.APPLIED, date(2026, 9, 30)),
        (S.READY_TO_APPLY, None),
        (S.INTERESTED, None),
    ]
    w = build_weekly_summary(entries, today)
    assert (w.applied, w.interviews, w.saved) == (1, 1, 1)
