from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.job_search.ui_helpers import build_job_card_view


def _job(**overrides):
    values = dict(
        source=JobSource.GREENHOUSE,
        source_id="role-1",
        company="Example Co",
        title="Platform Engineer",
        location="Remote",
        description="Build reliable systems.",
        salary_min=None,
        salary_max=None,
        sponsorship_available=None,
        work_mode="remote",
        url="https://example.com/jobs/role-1",
    )
    values.update(overrides)
    return JobPosting(**values)


def test_unknown_fields_are_honest():
    card = build_job_card_view(_job(), None, None, None)
    assert card.fit == "Not assessed"
    assert card.compensation == "Not stated"
    assert card.sponsorship == "Not stated"


def test_known_salary_and_action_are_display_ready():
    card = build_job_card_view(
        _job(salary_min=120_000, salary_max=150_000), None, None, "save"
    )
    assert card.compensation == "$120K-$150K"
    assert card.action == "Saved"
