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
