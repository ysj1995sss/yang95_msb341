"""
Tests for the Resume Tailoring Optimizer.

Tests verify that the optimization loop correctly:
1. Scores resumes using keyword alignment
2. Detects when target (85%) is reached
3. Detects plateau (< 2% improvement) and stops
4. Respects the Career Truth Profile constraint (no fabrication)
"""

import pytest
from unittest.mock import MagicMock, patch

from resume_tailorer.models import CareerTruthProfile, WorkExperience, EducationEntry
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.gap_analyzer import GapReport, GapItem, GapCategory
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.tailorer.optimizer import (
    ResumeTailoringOptimizer,
    OptimizationResult,
)


def _mock_llm(return_text: str = "Refined resume text") -> MagicMock:
    """Build a MagicMock LLMClient with complete() returning return_text."""
    llm = MagicMock(spec=LLMClient)
    llm.complete.return_value = return_text
    return llm


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
    """A sample gap report with a Category E ("never add") item, used to
    verify the optimizer excludes D/E items from its improvement targets."""
    return GapReport(
        items=[
            GapItem(
                requirement="Python",
                category=GapCategory.A,
                reason="Already on resume",
                candidate_evidence="Software Engineer experience",
            ),
            GapItem(
                requirement="Kubernetes",
                category=GapCategory.B,
                reason="Supported but missing",
                candidate_evidence="Led migration to Kubernetes",
            ),
            GapItem(
                requirement="NoSQL",
                category=GapCategory.E,
                reason="Not found in profile; do not add",
                candidate_evidence="None",
            ),
        ],
        summary="Found 1 aligned, 1 supported but missing, 1 truly missing requirements.",
    )


def test_optimizer_instantiation():
    """Test that optimizer can be instantiated."""
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())
    assert optimizer is not None
    assert optimizer.max_iterations == 5
    assert optimizer.target_score == 0.85


def test_optimizer_target_score_is_85_percent():
    """Test that optimizer uses 85% as the target score."""
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())
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
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())

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


def test_optimizer_excludes_category_e_from_improvement_targets(
    sample_profile, sample_job_analysis, sample_gap_report
):
    """C2 verification: a Category E ("never add") gap item must never
    appear in the "missing keywords to address" list passed to
    _build_improvement_prompt(). sample_gap_report marks "NoSQL" as
    Category E; the optimizer must filter it out of the refinement target
    list even though it may legitimately be a "missing" keyword by pure
    keyword-alignment scoring.
    """
    optimizer = ResumeTailoringOptimizer(max_iterations=1, llm=_mock_llm("Refined resume text"))

    captured_prompts = []
    original_build = optimizer._build_improvement_prompt

    def spy_build(current_resume, job_analysis, missing_keywords):
        captured_prompts.append(missing_keywords)
        return original_build(current_resume, job_analysis, missing_keywords)

    optimizer._build_improvement_prompt = spy_build

    # A resume missing everything so the first-iteration score is low and
    # refinement (and therefore _build_improvement_prompt) definitely runs.
    initial_tailored = "Generic resume with no relevant keywords"

    optimizer.optimize(sample_profile, sample_job_analysis, initial_tailored, sample_gap_report)

    assert captured_prompts, "Improvement prompt should have been built at least once"
    # sample_job_analysis title-cases skills (e.g. "nosql" -> "Nosql"), so
    # compare case-insensitively against the Category E requirement.
    for missing_keywords in captured_prompts:
        assert not any(kw.lower() == "nosql" for kw in missing_keywords), (
            "Category E item 'NoSQL' must be excluded from improvement targets"
        )


def test_optimizer_build_improvement_prompt():
    """Test that improvement prompt is built correctly."""
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())
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
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())
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


def test_optimizer_optimize_returns_optimization_result(
    sample_profile, sample_job_analysis, sample_gap_report
):
    """Test that optimize returns OptimizationResult."""
    optimizer = ResumeTailoringOptimizer(
        max_iterations=1,
        llm=_mock_llm("Refined resume with Python and Docker"),
    )
    initial_tailored = "Python engineer with Docker experience"

    result = optimizer.optimize(
        sample_profile, sample_job_analysis, initial_tailored, sample_gap_report
    )

    assert isinstance(result, OptimizationResult)
    assert isinstance(result.tailored_resume, str)
    assert isinstance(result.final_score, float)
    assert isinstance(result.iterations, int)
    assert isinstance(result.ceiling_reached, bool)
    assert isinstance(result.missing_qualifications, list)


def test_optimizer_stops_at_target_score(sample_profile, sample_job_analysis, sample_gap_report):
    """Test that optimizer stops when reaching target score (or plateaus)."""
    high_text = (
        "Python Go Docker Kubernetes PostgreSQL AWS microservices architecture REST APIs"
    )
    optimizer = ResumeTailoringOptimizer(max_iterations=3, llm=_mock_llm(high_text))

    # Create a resume that already has high alignment
    high_alignment_resume = (
        "Python Go Docker Kubernetes PostgreSQL AWS "
        "microservices architecture REST APIs"
    )

    result = optimizer.optimize(
        sample_profile, sample_job_analysis, high_alignment_resume, sample_gap_report
    )

    # Score should be at or near target (85%), or the optimizer should have
    # detected a plateau before reaching it.
    assert result.final_score >= optimizer.target_score or result.ceiling_reached


def test_optimizer_limits_iterations_to_max(
    sample_profile, sample_job_analysis, sample_gap_report
):
    """Test that optimizer respects max_iterations limit."""
    optimizer = ResumeTailoringOptimizer(
        max_iterations=2,
        llm=_mock_llm("Python experience"),
    )
    initial_tailored = "Python experience"

    result = optimizer.optimize(
        sample_profile, sample_job_analysis, initial_tailored, sample_gap_report
    )

    # Iterations should not exceed max_iterations
    assert result.iterations <= optimizer.max_iterations


def test_optimizer_detects_plateau():
    """Test that optimizer detects when improvement plateaus (< 2% delta)."""
    optimizer = ResumeTailoringOptimizer(max_iterations=5, llm=_mock_llm())

    # Mock job analysis with specific keywords
    job_analysis = MagicMock()
    job_analysis.skills_required = ["Python", "JavaScript"]
    job_analysis.tools_required = ["Docker", "PostgreSQL"]

    # Create a resume with 50% keyword match
    initial_resume = "Python Docker"  # 50% match

    empty_gap_report = GapReport(items=[], summary="No gaps found.")

    # Mock _refine_resume to return similar content (no improvement)
    with patch.object(
        optimizer.tailorer,
        "_refine_resume",
        return_value="Python Docker experience",
    ):
        result = optimizer.optimize(
            MagicMock(), job_analysis, initial_resume, empty_gap_report
        )

        # Should detect plateau and ceiling_reached should be True
        assert result.ceiling_reached is True


def test_optimizer_calculates_correct_score():
    """Test that optimizer correctly calculates alignment score.

    _score_resume now blends keyword alignment (60%) with qualification
    alignment (40%), the same methodology ResumeBenchmarker.benchmark()
    uses (see I1 fix), so the two scores are directly comparable. With no
    required qualifications configured, the qualification component is 0,
    so the ceiling is keyword_score * 0.6 rather than 1.0.
    """
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())

    # Create job analysis
    job_analysis = MagicMock()
    job_analysis.skills_required = ["Python", "Go"]
    job_analysis.tools_required = ["Docker", "Kubernetes"]
    job_analysis.required_qualifications = []

    # Test perfect keyword match (qualification component is 0 -> 0.6 ceiling)
    perfect_resume = "Python Go Docker Kubernetes"
    score, matched, missing = optimizer._score_resume(perfect_resume, job_analysis)
    assert score == pytest.approx(0.6)
    assert len(matched) == 4
    assert len(missing) == 0

    # Test partial match
    partial_resume = "Python Docker"
    score, matched, missing = optimizer._score_resume(partial_resume, job_analysis)
    assert score == pytest.approx(0.3)
    assert len(matched) == 2
    assert len(missing) == 2


def test_optimizer_uses_llm_client():
    """Test that optimizer uses ResumeTailorer with an injected LLMClient."""
    llm = _mock_llm()
    optimizer = ResumeTailoringOptimizer(llm=llm)

    # Verify tailorer is initialized with the injected llm
    assert optimizer.tailorer is not None
    assert optimizer.tailorer.llm is not None
    assert optimizer.tailorer.llm is llm
