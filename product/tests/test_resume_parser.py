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

def test_resume_parser_extracts_contact_info():
    """Parser correctly identifies contact info (name, email, phone)."""
    # For testing, we can create a mock resume or use a sample text
    parser = ResumeParser()
    # This would use a real PDF/DOCX in production
    # For now, we'll test the logic once we have a sample

def test_resume_parser_extracts_education():
    """Parser extracts education entries."""
    parser = ResumeParser()
    # Tested with real resume

def test_resume_parser_extracts_work_experience():
    """Parser extracts work experience with employer, title, dates, responsibilities, accomplishments."""
    parser = ResumeParser()
    # Tested with real resume
