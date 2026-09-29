from resume_tailorer.artifacts.models import (
    ChangeCategory,
    ChangeDisposition,
    ResumeChange,
    ValidationStatus,
)
from resume_tailorer.models import CareerTruthProfile, EducationEntry, WorkExperience
from resume_tailorer.pdf.content_validator import validate_pdf_content


def _profile() -> CareerTruthProfile:
    return CareerTruthProfile(
        contact_info={"name": "Test Candidate", "email": "candidate@example.test"},
        education=[EducationEntry("Example University", "MBA", "Business", "2027", [])],
        work_experience=[
            WorkExperience(
                employer="Example Corp",
                title="Manager",
                dates="2022-2024",
                responsibilities=[],
                accomplishments=["Improved retention by 20%"],
            )
        ],
        skills=[],
        tools=[],
        certifications=[],
        accomplishments=[],
    )


def _accepted_change() -> ResumeChange:
    return ResumeChange(
        change_id="paragraph:1",
        section="work_experience",
        source_index=1,
        original_text="Improved retention by 20%",
        proposed_text="Improved customer retention by 20%",
        category=ChangeCategory.REPHRASED,
        reason="Verified wording",
        job_requirement="customer retention",
        evidence_source="original_resume",
        evidence_text="Improved retention by 20%",
        validation_status=ValidationStatus.PASS,
        disposition=ChangeDisposition.ACCEPTED,
    )


def test_missing_contact_is_a_failure():
    text = "Example Corp Manager 2022-2024 Example University MBA 2027 Improved retention by 20%"
    findings = validate_pdf_content(text, _profile(), [])
    assert "CONTACT_MISSING" in {finding.code for finding in findings}


def test_missing_employer_metric_and_accepted_change_are_failures():
    text = "Test Candidate candidate@example.test Example University MBA 2027 Manager 2022-2024"
    findings = validate_pdf_content(text, _profile(), [_accepted_change()])
    codes = {finding.code for finding in findings}
    assert {"EMPLOYER_MISSING", "METRIC_MISSING", "ACCEPTED_CHANGE_MISSING"} <= codes


def test_duplicate_bullet_and_placeholder_are_failures():
    text = """Test Candidate candidate@example.test
Example Corp Manager 2022-2024
Example University MBA 2027
- Improved customer retention by 20%
- Improved customer retention by 20%
[INSERT RESULT]
"""
    findings = validate_pdf_content(text, _profile(), [_accepted_change()])
    codes = {finding.code for finding in findings}
    assert "DUPLICATE_BULLET" in codes
    assert "PLACEHOLDER_TEXT" in codes


def test_complete_content_has_no_failures():
    text = """Test Candidate candidate@example.test
Example Corp Manager 2022-2024
Example University MBA Business 2027
- Improved customer retention by 20%
"""
    assert validate_pdf_content(text, _profile(), [_accepted_change()]) == []


def test_education_year_as_a_real_int_does_not_crash():
    """EducationEntry.year is typed `int` (see models/career_profile.py) --
    a resume parsed from a real file always produces an int here, not the
    str this file's other fixtures happen to pass. Found live via the
    Task 9 acceptance fixtures: any parsed resume with a graduation year
    crashed validate_pdf_content with a TypeError before this fix."""
    profile = CareerTruthProfile(
        contact_info={"name": "Test Candidate", "email": "candidate@example.test"},
        education=[EducationEntry(degree="MBA", field="Business", institution="Example University", year=2027)],
        work_experience=[],
        skills=[], tools=[], certifications=[], accomplishments=[],
    )
    text = "Test Candidate candidate@example.test Example University MBA Business 2027"
    findings = validate_pdf_content(text, profile, [])
    assert "EDUCATION_DATE_MISSING" not in {finding.code for finding in findings}

    text_missing_year = "Test Candidate candidate@example.test Example University MBA Business"
    findings = validate_pdf_content(text_missing_year, profile, [])
    assert "EDUCATION_DATE_MISSING" in {finding.code for finding in findings}


def test_metric_in_a_legitimately_condensed_bullet_is_not_flagged_missing():
    """Found live (2026-09-28): a real resume with a metric-bearing bullet
    legitimately condensed for space (category CONDENSED -- a visible,
    reviewable change, not a silent drop) always failed METRIC_MISSING,
    because this check compared against ALL of the profile's work-
    experience text unconditionally, regardless of any reviewed
    disposition. A condensed bullet's metric must not still be
    "expected" once the condensing itself is what the reviewer sees."""
    condensed_change = ResumeChange(
        change_id="paragraph:2", section="work_experience", source_index=2,
        original_text="Improved retention by 20%", proposed_text="",
        category=ChangeCategory.CONDENSED, reason="Deprioritized for space",
        job_requirement="", evidence_source="original_resume",
        evidence_text="Improved retention by 20%", validation_status=ValidationStatus.PASS,
        disposition=ChangeDisposition.PENDING,
    )
    text = "Test Candidate candidate@example.test Example Corp Manager 2022-2024 Example University MBA 2027"
    findings = validate_pdf_content(text, _profile(), [condensed_change])
    assert "METRIC_MISSING" not in {finding.code for finding in findings}


def test_auto_rejected_ambiguous_pairing_does_not_require_original_to_reappear():
    """Found live (2026-09-28): a condensed skill weakly leftover-paired
    against an unrelated new bullet (category REJECTED = auto-rejected
    AMBIGUOUS pairing, not a user rejecting a confident rewrite) has no
    real substitution relationship -- its original_text was never
    actually replaced by the tailored text, so it must not be required
    to reappear once the pairing itself gets auto-rejected."""
    ambiguous_change = ResumeChange(
        change_id="paragraph:3", section="work_experience", source_index=3,
        original_text="Market Research", proposed_text="Relevant Coursework: Something Unrelated",
        category=ChangeCategory.REJECTED, reason="Ambiguous bullet pairing (23% similarity)",
        job_requirement="", evidence_source="original_resume",
        evidence_text="Market Research", validation_status=ValidationStatus.FAIL,
        disposition=ChangeDisposition.REJECTED,
    )
    text = "Test Candidate candidate@example.test Example Corp Manager 2022-2024 Example University MBA 2027"
    findings = validate_pdf_content(text, _profile(), [ambiguous_change])
    assert "ACCEPTED_CHANGE_MISSING" not in {finding.code for finding in findings}


def test_user_rejected_confident_change_still_requires_original_to_reappear():
    """The fix above must not weaken a real user rejection -- only the
    auto-rejected AMBIGUOUS-pairing category is exempted."""
    rejected_change = ResumeChange(
        change_id="paragraph:4", section="work_experience", source_index=4,
        original_text="Improved retention by 20%", proposed_text="Improved customer retention by 20%",
        category=ChangeCategory.REPHRASED, reason="Verified wording",
        job_requirement="customer retention", evidence_source="original_resume",
        evidence_text="Improved retention by 20%", validation_status=ValidationStatus.PASS,
        disposition=ChangeDisposition.REJECTED,
    )
    text = "Test Candidate candidate@example.test Example University MBA 2027 Manager 2022-2024"
    findings = validate_pdf_content(text, _profile(), [rejected_change])
    codes = {finding.code for finding in findings}
    assert "ACCEPTED_CHANGE_MISSING" in codes


def test_metric_missing_still_fires_when_not_explained_by_a_reviewed_change():
    """The fix above must not silently swallow a genuinely missing
    metric -- only a CONDENSED-category change explains its absence."""
    text = "Test Candidate candidate@example.test Example Corp Manager 2022-2024 Example University MBA 2027"
    findings = validate_pdf_content(text, _profile(), [])
    assert "METRIC_MISSING" in {finding.code for finding in findings}
