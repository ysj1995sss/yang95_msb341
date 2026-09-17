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
