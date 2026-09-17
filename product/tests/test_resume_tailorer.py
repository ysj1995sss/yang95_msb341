import pytest
from unittest.mock import MagicMock, Mock
import sys

# Mock anthropic before importing ResumeTailorer to avoid import errors
mock_anthropic_module = Mock()
sys.modules['anthropic'] = mock_anthropic_module

from resume_tailorer.models import CareerTruthProfile, WorkExperience, EducationEntry
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmarker
from resume_tailorer.analyzers.gap_analyzer import GapAnalyzer, GapCategory, GapItem, GapReport
from resume_tailorer.tailorer import ResumeTailorer


@pytest.fixture
def sample_profile():
    """A sample career truth profile for testing."""
    return CareerTruthProfile(
        contact_info={
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "phone": "555-1234",
            "location": "San Francisco, CA",
        },
        education=[
            EducationEntry(
                degree="BS",
                field="Computer Science",
                institution="MIT",
                year=2018,
                gpa="3.8",
            )
        ],
        work_experience=[
            WorkExperience(
                employer="TechCorp",
                title="Software Engineer",
                dates="2020-2022",
                responsibilities=[
                    "Built microservices using Python and Go",
                    "Managed Docker containers",
                    "Wrote REST APIs",
                ],
                accomplishments=[
                    "Improved system performance by 30%",
                    "Led migration to Kubernetes",
                ],
                location="San Francisco, CA",
                employment_type="Full-time",
            ),
            WorkExperience(
                employer="StartupXYZ",
                title="Junior Developer",
                dates="2018-2020",
                responsibilities=[
                    "Developed frontend with React",
                    "Worked on PostgreSQL database",
                ],
                accomplishments=[
                    "Built user dashboard handling 10k+ users",
                ],
            ),
        ],
        skills=["Python", "Go", "JavaScript", "React"],
        tools=["Docker", "PostgreSQL", "AWS", "Git"],
        certifications=["AWS Solutions Architect"],
        accomplishments=[
            "Published technical blog with 50k+ monthly readers",
        ],
    )


@pytest.fixture
def sample_job_analysis():
    """A sample job analysis."""
    analyzer = JobAnalyzer()
    job_desc = """
    Senior Python Engineer

    Requirements:
    - 5+ years Python experience required
    - Docker and Kubernetes expertise essential
    - PostgreSQL and NoSQL database experience
    - Microservices architecture knowledge
    - AWS experience required

    Nice to have:
    - Go experience
    - Leadership experience
    - Published technical content
    """
    return analyzer.analyze(job_desc)


@pytest.fixture
def sample_gap_report():
    """A sample gap report."""
    return GapReport(
        items=[
            GapItem(
                requirement="Python",
                category=GapCategory.A,
                reason="Already on resume",
                candidate_evidence="Senior Python Engineer experience",
            ),
            GapItem(
                requirement="Docker",
                category=GapCategory.A,
                reason="Already on resume",
                candidate_evidence="Managed Docker containers",
            ),
            GapItem(
                requirement="Kubernetes",
                category=GapCategory.B,
                reason="Supported but missing",
                candidate_evidence="Led migration to Kubernetes",
            ),
            GapItem(
                requirement="Go",
                category=GapCategory.C,
                reason="Rephrasable",
                candidate_evidence="Can highlight Go experience in bullet points",
            ),
            GapItem(
                requirement="Secret Clearance",
                category=GapCategory.E,
                reason="Truly missing",
                candidate_evidence="None",
            ),
        ],
        summary="Found 2 aligned, 1 supported but missing, 1 rephrasable, 1 truly missing requirements.",
    )


def setup_anthropic_mock():
    """Setup mocked Anthropic client for tests."""
    mock_client = MagicMock()
    sys.modules['anthropic'].Anthropic = MagicMock(return_value=mock_client)
    return mock_client


def test_resume_tailorer_instantiation():
    """Test that ResumeTailorer can be instantiated."""
    setup_anthropic_mock()

    tailorer = ResumeTailorer()
    assert tailorer is not None
    assert tailorer.model == "claude-3-5-sonnet-20241022"


def test_resume_tailorer_system_prompt_forbids_fabrication():
    """Test that system prompt explicitly forbids fabrication."""
    setup_anthropic_mock()

    tailorer = ResumeTailorer()
    system_prompt = tailorer._build_system_prompt()

    # Critical: system prompt must forbid fabrication
    assert "fabricat" in system_prompt.lower() or "not add" in system_prompt.lower() or "never invent" in system_prompt.lower()
    assert "Career Truth Profile" in system_prompt or "truth" in system_prompt.lower()


def test_resume_tailorer_tailor_method_calls_claude(sample_profile, sample_job_analysis, sample_gap_report):
    """Test that tailor method calls Claude API (mocked)."""
    mock_client = setup_anthropic_mock()

    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "Here is the tailored resume content..."
    mock_client.messages.create.return_value = mock_response

    tailorer = ResumeTailorer()
    result = tailorer.tailor(sample_profile, sample_job_analysis, sample_gap_report)

    # Verify Claude was called
    assert mock_client.messages.create.called
    # Verify result is a string
    assert isinstance(result, str)


def test_resume_tailorer_gap_formatting_excludes_de_gaps(sample_profile, sample_job_analysis, sample_gap_report):
    """Test that D/E gaps are explicitly excluded from 'fill' instructions."""
    setup_anthropic_mock()

    tailorer = ResumeTailorer()
    formatted = tailorer._format_gaps(sample_gap_report)

    # Check that D/E gaps are present but marked as exclusions
    # The formatted output should note that D and E gaps should NOT be filled
    assert "Truly missing" in formatted or "Category E" in formatted or "never" in formatted.lower()


def test_resume_tailorer_profile_to_string(sample_profile):
    """Test that profile is correctly converted to readable text."""
    setup_anthropic_mock()

    tailorer = ResumeTailorer()
    profile_text = tailorer._profile_to_string(sample_profile)

    # Verify key profile elements are in the output
    assert "Alice Johnson" in profile_text
    assert "MIT" in profile_text
    assert "TechCorp" in profile_text
    assert "Python" in profile_text


def test_resume_tailorer_uses_correct_model():
    """Test that ResumeTailorer initializes with correct Claude model."""
    setup_anthropic_mock()

    tailorer = ResumeTailorer()

    # Verify the model attribute is set correctly
    assert tailorer.model == "claude-3-5-sonnet-20241022"
