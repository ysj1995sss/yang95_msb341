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
