import pytest
from unittest.mock import MagicMock

from resume_tailorer.models import CareerTruthProfile, WorkExperience, EducationEntry
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.gap_analyzer import GapCategory, GapItem, GapReport
from resume_tailorer.tailorer import ResumeTailorer
from resume_tailorer.tailorer.resume_tailorer import _strip_non_resume_content
from resume_tailorer.llm.client import LLMClient


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


def test_resume_tailorer_instantiation():
    """Test that ResumeTailorer can be instantiated with an injected LLMClient."""
    llm = MagicMock(spec=LLMClient)
    tailorer = ResumeTailorer(llm=llm)
    assert tailorer is not None
    assert tailorer.llm is llm


def test_resume_tailorer_system_prompt_forbids_fabrication():
    """Test that system prompt explicitly forbids fabrication."""
    tailorer = ResumeTailorer(llm=MagicMock())
    system_prompt = tailorer._build_system_prompt()

    # Critical: system prompt must forbid fabrication
    assert "fabricat" in system_prompt.lower() or "not add" in system_prompt.lower() or "never invent" in system_prompt.lower()
    assert "Career Truth Profile" in system_prompt or "truth" in system_prompt.lower()


def test_resume_tailorer_tailor_method_calls_llm(sample_profile, sample_job_analysis, sample_gap_report):
    """Test that tailor method calls LLMClient.complete (mocked)."""
    llm = MagicMock(spec=LLMClient)
    llm.complete.return_value = "Here is the tailored resume content..."
    tailorer = ResumeTailorer(llm=llm)
    result = tailorer.tailor(sample_profile, sample_job_analysis, sample_gap_report)

    assert llm.complete.called
    args, kwargs = llm.complete.call_args
    assert "fabricat" in args[0].lower() or "never" in args[0].lower()
    assert isinstance(args[1], str)
    assert isinstance(result, str)


def test_resume_tailorer_gap_formatting_excludes_de_gaps(sample_profile, sample_job_analysis, sample_gap_report):
    """Test that D/E gaps are explicitly excluded from 'fill' instructions."""
    tailorer = ResumeTailorer(llm=MagicMock())
    formatted = tailorer._format_gaps(sample_gap_report)

    # Check that D/E gaps are present but marked as exclusions
    # The formatted output should note that D and E gaps should NOT be filled
    assert "Truly missing" in formatted or "Category E" in formatted or "never" in formatted.lower()


def test_resume_tailorer_profile_to_string(sample_profile):
    """Test that profile is correctly converted to readable text."""
    tailorer = ResumeTailorer(llm=MagicMock())
    profile_text = tailorer._profile_to_string(sample_profile)

    # Verify key profile elements are in the output
    assert "Alice Johnson" in profile_text
    assert "MIT" in profile_text
    assert "TechCorp" in profile_text
    assert "Python" in profile_text


def test_resume_tailorer_has_llm():
    """Test that ResumeTailorer exposes an llm client."""
    llm = MagicMock(spec=LLMClient)
    tailorer = ResumeTailorer(llm=llm)
    assert tailorer.llm is not None
    assert tailorer.llm is llm


# --- _strip_non_resume_content: defense-in-depth cleanup for LLM output that
# ignores the "output ONLY resume content" instruction (observed live against
# DeepSeek-v4-flash-Free on 2026-09-21: it appended a trailing "NOTES:"
# section explaining its reasoning) --------------------------------------


def test_strip_removes_trailing_notes_section_after_divider():
    text = (
        "JANE DOE\n\nWORK EXPERIENCE\n- Built REST APIs\n\n"
        "---\n\n**NOTES:**\n- Kubernetes was not added per instructions."
    )
    result = _strip_non_resume_content(text)
    assert "NOTES" not in result
    assert "Kubernetes" not in result
    assert "Built REST APIs" in result


def test_strip_removes_trailing_notes_section_without_divider():
    text = "JANE DOE\n\nWORK EXPERIENCE\n- Built REST APIs\n\nNOTES:\n- Some commentary here."
    result = _strip_non_resume_content(text)
    assert "NOTES" not in result
    assert "Built REST APIs" in result


def test_strip_removes_leading_conversational_preamble():
    text = "Here is the tailored resume:\n\nJANE DOE\n\nWORK EXPERIENCE\n- Built REST APIs"
    result = _strip_non_resume_content(text)
    assert not result.lower().startswith("here")
    assert "JANE DOE" in result


def test_strip_leaves_normal_resume_content_untouched():
    text = "JANE DOE\n\nWORK EXPERIENCE\n- Built REST APIs\n- Managed a PostgreSQL database"
    result = _strip_non_resume_content(text)
    assert result == text


def test_tailor_strips_notes_commentary_from_llm_output(
    sample_profile, sample_job_analysis, sample_gap_report
):
    """End-to-end: tailor() must strip commentary, not just the helper function."""
    llm = MagicMock(spec=LLMClient)
    llm.complete.return_value = (
        "JANE DOE\n\nWORK EXPERIENCE\n- Built REST APIs\n\n"
        "---\n**NOTES:**\n- Kubernetes was flagged as missing and not added."
    )
    tailorer = ResumeTailorer(llm=llm)
    result = tailorer.tailor(sample_profile, sample_job_analysis, sample_gap_report)

    assert "NOTES" not in result
    assert "Kubernetes was flagged" not in result
    assert "Built REST APIs" in result
