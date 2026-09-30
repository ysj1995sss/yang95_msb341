"""Every reviewed disposition must show up in the regenerated text."""

from resume_tailorer.artifacts.models import (
    ChangeCategory, ChangeDisposition, ResumeChange, ValidationStatus,
)
from resume_tailorer.artifacts.regeneration import apply_dispositions_to_text
from resume_tailorer.models import CareerTruthProfile, WorkExperience

PROFILE = CareerTruthProfile(
    contact_info={"name": "Alex Kim"},
    education=[],
    work_experience=[
        WorkExperience(
            employer="Acme",
            title="Analyst",
            dates="2020-2023",
            responsibilities=["Built weekly sales dashboards in SQL", "Trained 4 new analysts"],
            accomplishments=[],
        ),
        WorkExperience(
            employer="Globex",
            title="Intern",
            dates="2019",
            responsibilities=["Cleaned CRM data"],
            accomplishments=[],
        ),
    ],
    skills=["SQL"],
    tools=[],
    certifications=[],
    accomplishments=[],
)

BASELINE = (
    "Alex Kim\n\nEXPERIENCE\nAcme | Analyst | 2020-2023\n"
    "- Built weekly sales dashboards in SQL\n"
    "Globex | Intern | 2019\n- Cleaned CRM data\n"
)


def _change(original, proposed, disposition, category=ChangeCategory.REPHRASED, manual=None):
    return ResumeChange(
        change_id="c", section="work_experience", source_index=0,
        original_text=original, proposed_text=proposed, category=category, reason="",
        job_requirement="", evidence_source="career_profile", evidence_text="",
        validation_status=ValidationStatus.PASS, disposition=disposition, manual_text=manual,
    )


def test_keep_original_restores_a_removed_bullet_under_its_own_job():
    removed = _change("Trained 4 new analysts", "", ChangeDisposition.RESTORED, ChangeCategory.CONDENSED)
    text = apply_dispositions_to_text(BASELINE, [removed], PROFILE)
    lines = text.splitlines()
    assert "- Trained 4 new analysts" in lines
    assert lines.index("- Trained 4 new analysts") < lines.index("Globex | Intern | 2019")


def test_accepted_removal_stays_removed():
    removed = _change("Trained 4 new analysts", "", ChangeDisposition.ACCEPTED, ChangeCategory.CONDENSED)
    assert apply_dispositions_to_text(BASELINE, [removed]) == BASELINE


def test_manual_edit_to_unchanged_bullet_is_applied():
    unchanged = _change(
        "Cleaned CRM data", "Cleaned CRM data", ChangeDisposition.MANUALLY_EDITED,
        ChangeCategory.UNCHANGED, manual="Cleaned and deduplicated CRM data",
    )
    text = apply_dispositions_to_text(BASELINE, [unchanged])
    assert "- Cleaned and deduplicated CRM data" in text
    assert "- Cleaned CRM data\n" not in text


def test_regeneration_is_idempotent_from_baseline():
    removed = _change("Trained 4 new analysts", "", ChangeDisposition.RESTORED, ChangeCategory.CONDENSED)
    once = apply_dispositions_to_text(BASELINE, [removed])
    assert apply_dispositions_to_text(BASELINE, [removed]) == once
    assert once.count("Trained 4 new analysts") == 1
