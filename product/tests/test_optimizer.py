"""
Tests for the Resume Tailoring Optimizer.

Tests verify that the optimization loop correctly:
1. Scores resumes using keyword alignment
2. Detects when target (85%) is reached
3. Detects plateau (< 2% improvement) and stops
4. Respects the Career Truth Profile constraint (no fabrication)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys

# Mock anthropic before importing to avoid import errors
mock_anthropic_module = Mock()
sys.modules['anthropic'] = mock_anthropic_module

from resume_tailorer.models import CareerTruthProfile, WorkExperience, EducationEntry
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.tailorer.optimizer import (
    ResumeTailoringOptimizer,
    OptimizationResult,
)


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


def setup_anthropic_mock():
    """Setup mocked Anthropic client for tests."""
    mock_client = MagicMock()
    sys.modules['anthropic'].Anthropic = MagicMock(return_value=mock_client)
    return mock_client


def test_optimizer_instantiation():
    """Test that optimizer can be instantiated."""
    setup_anthropic_mock()

    optimizer = ResumeTailoringOptimizer()
    assert optimizer is not None
    assert optimizer.max_iterations == 5
    assert optimizer.target_score == 0.85


def test_optimizer_target_score_is_85_percent():
    """Test that optimizer uses 85% as the target score."""
    setup_anthropic_mock()

    optimizer = ResumeTailoringOptimizer()
    assert optimizer.target_score == 0.85


def test_optimization_result_dataclass():
    """Test OptimizationResult stores all required fields."""
    result = OptimizationResult(
        tailored_resume="This is a refined resume",
        final_score=0.82,
        iterations=3,
        ceiling_reached=True,
        missing_qualifications=["NoSQL", "Kubernetes"],
    )

    assert result.tailored_resume == "This is a refined resume"
    assert result.final_score == 0.82
    assert result.iterations == 3
    assert result.ceiling_reached is True
    assert result.missing_qualifications == ["NoSQL", "Kubernetes"]


def test_optimizer_score_resume_uses_keyword_alignment(sample_job_analysis):
    """Test that _score_resume uses calculate_keyword_alignment."""
    setup_anthropic_mock()

    optimizer = ResumeTailoringOptimizer()

    # Create a resume with some keywords
    resume = "Python Docker PostgreSQL experience"
    score, matched, missing = optimizer._score_resume(resume, sample_job_analysis)

    # Score should be between 0 and 1
    assert 0 <= score <= 1.0
    # Should have matched some keywords
    assert isinstance(matched, list)
    assert isinstance(missing, list)
    # Matched + missing should equal total required keywords
    total_keywords = (
        len(sample_job_analysis.skills_required)
        + len(sample_job_analysis.tools_required)
    )
    assert len(matched) + len(missing) == total_keywords


def test_optimizer_build_improvement_prompt():
    """Test that improvement prompt is built correctly."""
    setup_anthropic_mock()

    optimizer = ResumeTailoringOptimizer()
    resume = "Current resume text"
    job_analysis = JobAnalyzer().analyze("Need Python and Docker")
    missing = ["Kubernetes", "NoSQL"]

    prompt = optimizer._build_improvement_prompt(resume, job_analysis, missing)

    # Prompt should contain instructions and missing keywords
    assert "Python" in prompt or "Docker" in prompt
    assert "Kubernetes" in prompt or "NoSQL" in prompt
    assert "fabricat" in prompt.lower() or "invent" in prompt.lower()


def test_optimizer_respects_no_fabrication_in_prompt():
    """Test that improvement prompt includes no-fabrication guardrails."""
    setup_anthropic_mock()

    optimizer = ResumeTailoringOptimizer()
    resume = "Current resume"
    job_analysis = JobAnalyzer().analyze("Job requirements")
    missing = ["Skill1"]

    prompt = optimizer._build_improvement_prompt(resume, job_analysis, missing)

    # Must explicitly forbid fabrication
    prompt_lower = prompt.lower()
    assert (
        "fabricate" in prompt_lower
        or "invent" in prompt_lower
        or "not add" in prompt_lower
        or "never" in prompt_lower
    )


def test_optimizer_optimize_returns_optimization_result(sample_profile, sample_job_analysis):
    """Test that optimize returns OptimizationResult."""
    mock_client = setup_anthropic_mock()

    # Mock the Claude response for _refine_resume
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "Refined resume with Python and Docker"
    mock_client.messages.create.return_value = mock_response

    optimizer = ResumeTailoringOptimizer(max_iterations=1)
    initial_tailored = "Python engineer with Docker experience"

    result = optimizer.optimize(sample_profile, sample_job_analysis, initial_tailored)

    assert isinstance(result, OptimizationResult)
    assert isinstance(result.tailored_resume, str)
    assert isinstance(result.final_score, float)
    assert isinstance(result.iterations, int)
    assert isinstance(result.ceiling_reached, bool)
    assert isinstance(result.missing_qualifications, list)


def test_optimizer_stops_at_target_score(sample_profile, sample_job_analysis):
    """Test that optimizer stops when reaching target score."""
    mock_client = setup_anthropic_mock()

    # Create a resume that already has high alignment
    high_alignment_resume = (
        "Python Go Docker Kubernetes PostgreSQL AWS "
        "microservices architecture REST APIs"
    )

    optimizer = ResumeTailoringOptimizer(max_iterations=3)
    result = optimizer.optimize(sample_profile, sample_job_analysis, high_alignment_resume)

    # Score should be at or near target (85%)
    assert result.final_score >= optimizer.target_score or result.ceiling_reached


def test_optimizer_limits_iterations_to_max(sample_profile, sample_job_analysis):
    """Test that optimizer respects max_iterations limit."""
    mock_client = setup_anthropic_mock()

    # Mock refinement to always return same text (no improvement)
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "Python experience"
    mock_client.messages.create.return_value = mock_response

    optimizer = ResumeTailoringOptimizer(max_iterations=2)
    initial_tailored = "Python experience"

    result = optimizer.optimize(sample_profile, sample_job_analysis, initial_tailored)

    # Iterations should not exceed max_iterations
    assert result.iterations <= optimizer.max_iterations


def test_optimizer_detects_plateau():
    """Test that optimizer detects when improvement plateaus (< 2% delta)."""
    setup_anthropic_mock()

    optimizer = ResumeTailoringOptimizer(max_iterations=5)

    # Mock job analysis with specific keywords
    job_analysis = MagicMock()
    job_analysis.skills_required = ["Python", "JavaScript"]
    job_analysis.tools_required = ["Docker", "PostgreSQL"]

    # Create a resume with 50% keyword match
    initial_resume = "Python Docker"  # 50% match

    # Mock _refine_resume to return similar content (no improvement)
    with patch.object(
        optimizer.tailorer,
        "_refine_resume",
        return_value="Python Docker experience",
    ):
        result = optimizer.optimize(
            MagicMock(), job_analysis, initial_resume
        )

        # Should detect plateau and ceiling_reached should be True
        assert result.ceiling_reached is True


def test_optimizer_calculates_correct_score():
    """Test that optimizer correctly calculates alignment score."""
    setup_anthropic_mock()

    optimizer = ResumeTailoringOptimizer()

    # Create job analysis
    job_analysis = MagicMock()
    job_analysis.skills_required = ["Python", "Go"]
    job_analysis.tools_required = ["Docker", "Kubernetes"]

    # Test perfect match
    perfect_resume = "Python Go Docker Kubernetes"
    score, matched, missing = optimizer._score_resume(perfect_resume, job_analysis)
    assert score == 1.0
    assert len(matched) == 4
    assert len(missing) == 0

    # Test partial match
    partial_resume = "Python Docker"
    score, matched, missing = optimizer._score_resume(partial_resume, job_analysis)
    assert score == 0.5
    assert len(matched) == 2
    assert len(missing) == 2


def test_optimizer_uses_correct_model():
    """Test that optimizer uses ResumeTailorer with correct model."""
    setup_anthropic_mock()

    optimizer = ResumeTailoringOptimizer()

    # Verify tailorer is initialized
    assert optimizer.tailorer is not None
    assert optimizer.tailorer.model == "claude-3-5-sonnet-20241022"
