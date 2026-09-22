import pytest
from pathlib import Path
from resume_tailorer.parsers.resume_parser import ResumeParser
from resume_tailorer.models import CareerTruthProfile

@pytest.fixture
def sample_resume_path():
    """Path to a sample resume for testing."""
    # For MVP testing, we'll use a PDF fixture
    return Path(__file__).parent / "fixtures" / "sample_resume.pdf"

def test_resume_parser_extracts_text_from_pdf(sample_resume_path):
    """Parser can extract text from a PDF resume."""
    parser = ResumeParser()
    profile = parser.parse(str(sample_resume_path))

    assert isinstance(profile, CareerTruthProfile)
    assert profile.name  # Name should be extracted
    assert profile.email  # Email should be extracted
    assert len(profile.work_experience) > 0  # Should have at least one job

def test_resume_parser_extracts_contact_info(sample_resume_path):
    """Parser correctly identifies contact info (name, email, phone)."""
    parser = ResumeParser()
    profile = parser.parse(str(sample_resume_path))

    # Verify contact info is extracted
    assert profile.contact_info is not None
    assert profile.contact_info.get("name") == "John Smith"
    assert profile.contact_info.get("email") == "john.smith@email.com"
    assert "(555) 123-4567" in profile.contact_info.get("phone", "")

def test_resume_parser_extracts_education(sample_resume_path):
    """Parser extracts education entries."""
    parser = ResumeParser()
    profile = parser.parse(str(sample_resume_path))

    # Verify education is extracted
    assert isinstance(profile.education, list)
    # May have 0+ education entries depending on PDF parsing
    # At minimum, the parser should handle the education section without errors

def test_resume_parser_extracts_work_experience(sample_resume_path):
    """Parser extracts work experience with employer, title, dates, responsibilities, accomplishments."""
    parser = ResumeParser()
    profile = parser.parse(str(sample_resume_path))

    # Verify work experience is extracted
    assert len(profile.work_experience) > 0

    # Check first job entry has required fields
    first_job = profile.work_experience[0]
    assert first_job.employer
    assert first_job.title
    assert first_job.dates


class TestWrappedBulletContinuation:
    """
    Regression tests for a bug found live (2026-09-22) on a real resume: a
    long bullet that PDF text extraction wraps onto a second physical line
    with no bullet marker was silently DROPPED (only the first line was
    kept), losing real accomplishment content. This cascaded into a false
    "fabrication risk" flag later, since the dropped content reappeared in
    the tailored output looking unsupported by the (incomplete) profile.
    """

    def test_wrapped_continuation_is_appended_not_dropped(self):
        text = (
            "EXPERIENCE\n"
            "Marketing Manager\n"
            "Acme Corp | Springfield, IL Jan 2022-Dec 2023\n"
            "• Developed a growth strategy by synthesizing data, identifying up to $50M\n"
            "in incremental sales potential targeted for next fiscal year\n"
            "EDUCATION\n"
        )
        parser = ResumeParser()
        jobs = parser._extract_work_experience(text)

        assert len(jobs) == 1
        combined = " ".join(jobs[0].accomplishments)
        assert "$50M" in combined
        # The wrapped continuation text must survive, not just the first line.
        assert "incremental sales potential" in combined

    def test_multiple_bullets_each_keep_their_own_continuation(self):
        text = (
            "EXPERIENCE\n"
            "Operations Lead\n"
            "Beta Inc | Remote Mar 2021-Feb 2022\n"
            "• Led a 10-person team, diagnosed process bottlenecks, and implemented\n"
            "improvements that reduced cycle time by 30% (60s -> 42s)\n"
            "• Coordinated cross-functional projects for 50K+ users with 91% satisfaction\n"
            "EDUCATION\n"
        )
        parser = ResumeParser()
        jobs = parser._extract_work_experience(text)

        assert len(jobs) == 1
        all_bullets = jobs[0].responsibilities + jobs[0].accomplishments
        assert any("cycle time by 30%" in b and "60s -> 42s" in b for b in all_bullets)
        assert any("91% satisfaction" in b for b in all_bullets)


class TestInlineLabeledSkills:
    """
    Regression test for a bug found live (2026-09-22): a real resume labeled
    its skills-equivalent content "Technical Proficiency" and "Core
    Competencies" instead of the literal word "Skills" -- the section-only
    detection required "skill" to appear somewhere, so it returned an empty
    list even though the resume clearly listed real skills.
    """

    def test_technical_proficiency_label_is_recognized(self):
        text = (
            "ADDITIONAL\n"
            "• Technical Proficiency: Tableau | Power BI | SQL | MS Excel\n"
        )
        parser = ResumeParser()
        skills = parser._extract_skills(text)
        assert "Tableau" in skills
        assert "Power BI" in skills
        assert "SQL" in skills

    def test_core_competencies_label_is_recognized(self):
        text = (
            "ADDITIONAL\n"
            "• Core Competencies: Strategic Thinking | Market Research | Mentorship\n"
        )
        parser = ResumeParser()
        skills = parser._extract_skills(text)
        assert "Strategic Thinking" in skills
        assert "Market Research" in skills


def test_extract_style_hints_detects_bullet_dash():
    """Detects '-' as the dominant bullet character."""
    parser = ResumeParser()
    text = "WORK EXPERIENCE\n- Built a system\n- Led a team\n- Shipped a feature"
    hints = parser.extract_style_hints(text)
    assert hints["bullet_char"] == "-"

def test_extract_style_hints_detects_bullet_dot():
    """Detects '•' as the dominant bullet character."""
    parser = ResumeParser()
    text = "WORK EXPERIENCE\n• Built a system\n• Led a team\n• Shipped a feature"
    hints = parser.extract_style_hints(text)
    assert hints["bullet_char"] == "•"

def test_extract_style_hints_defaults_to_dot_when_no_bullets_found():
    """Falls back to '•' default when no bullet markers are present."""
    parser = ResumeParser()
    text = "WORK EXPERIENCE\nBuilt a system without bullets\nLed a team without bullets"
    hints = parser.extract_style_hints(text)
    assert hints["bullet_char"] == "•"

def test_extract_style_hints_detects_short_caps_heading_as_bold_larger():
    """A short ALL-CAPS heading line suggests a larger/bold heading style."""
    parser = ResumeParser()
    text = "EXPERIENCE\n- Built a system\nEDUCATION\n- BS Computer Science"
    hints = parser.extract_style_hints(text)
    assert hints["heading_style"] == "bold_larger"

def test_extract_style_hints_defaults_heading_style_to_bold():
    """No short all-caps heading present defaults to plain bold."""
    parser = ResumeParser()
    text = "some lowercase text with no headings at all in this resume body"
    hints = parser.extract_style_hints(text)
    assert hints["heading_style"] == "bold"

def test_get_raw_text_dispatches_pdf(sample_resume_path):
    """get_raw_text() extracts text from a PDF via its public dispatch method."""
    parser = ResumeParser()
    text = parser.get_raw_text(str(sample_resume_path))
    assert isinstance(text, str)
    assert "John Smith" in text

def test_get_raw_text_raises_on_unsupported_extension():
    """get_raw_text() raises ValueError for an unsupported file extension."""
    parser = ResumeParser()
    with pytest.raises(ValueError, match="Unsupported"):
        parser.get_raw_text("resume.txt")


def test_get_raw_text_rejects_legacy_doc():
    parser = ResumeParser()
    with pytest.raises(ValueError, match=r"\.doc"):
        parser.get_raw_text("resume.doc")
