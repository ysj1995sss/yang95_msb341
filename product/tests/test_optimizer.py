"""
Tests for the Resume Tailoring Optimizer.

Tests verify that the optimization loop correctly:
1. Scores resumes using keyword alignment
2. Works only on requirements with confirmed evidence that aren't shown yet (spec 010)
3. Stops when none are left, a round changes or shows nothing, or after 3 rounds
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
    """Spec 010: at most 3 rounds, and no score target at all."""
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())
    assert optimizer.max_iterations == 3
    assert not hasattr(optimizer, "target_score")


def test_no_code_path_reads_an_85_percent_target():
    import inspect

    from resume_tailorer.tailorer import optimizer as module

    source = inspect.getsource(module)
    assert "0.85" not in source and "target_score" not in source


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


def test_refinement_targets_only_supported_unshown_requirements():
    """Spec 010: a requirement without evidence (CPA, Tableau, Snowflake-only-listed, the
    ambiguous PM, unconfirmed Salesforce) is never a refinement target."""
    from resume_tailorer.analyzers.job_analyzer import JobAnalyzer as JA
    from resume_tailorer.analyzers.requirement_review import build_review
    from tests.fixtures.ats import POSTING, PROVENANCE, profile

    analysis = JA().analyze(POSTING)
    review = build_review(analysis, profile(), provenance=PROVENANCE, posting=POSTING)
    optimizer = ResumeTailoringOptimizer(max_iterations=1, llm=_mock_llm("Refined"))
    captured = []
    original = optimizer._build_improvement_prompt
    optimizer._build_improvement_prompt = lambda cur, rev, targets: captured.append(targets) or original(cur, rev, targets)

    optimizer.optimize(profile(), analysis, "Marketing analyst. Excel.", GapReport(items=[], summary=""), review=review)

    assert captured
    targeted = " ".join(r.text for r in captured[0])
    for unsupported in ("CPA", "Tableau", "Snowflake", "PM experience", "Salesforce"):
        assert unsupported not in targeted
    prompt = original("Marketing analyst. Excel.", review, captured[0])
    assert "Never add these terms anywhere new" in prompt and "CPA" in prompt  # named only as things to leave out


def test_optimizer_build_improvement_prompt_quotes_evidence_and_forbids_fabrication():
    from resume_tailorer.analyzers.job_analyzer import JobAnalyzer as JA
    from resume_tailorer.analyzers.requirement_review import build_review, unshown_targets
    from tests.fixtures.ats import POSTING, PROVENANCE, profile

    review = build_review(JA().analyze(POSTING), profile(), provenance=PROVENANCE, posting=POSTING)
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())
    prompt = optimizer._build_improvement_prompt("Resume", review, unshown_targets(review, "Resume"))
    assert 'Evidence (Marketing Analyst at Acme Retail, bullet 2): "Led on-time delivery' in prompt
    assert "do not invent or fabricate" in prompt.lower()
    assert "hidden text" in prompt.lower()


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


def test_optimizer_stops_when_nothing_supported_is_left(sample_profile, sample_job_analysis, sample_gap_report):
    """No unshown supported requirement means no round runs and the model isn't called."""
    llm = _mock_llm("should not be used")
    optimizer = ResumeTailoringOptimizer(max_iterations=3, llm=llm)
    everything = "Python Go JavaScript React Docker PostgreSQL AWS Git Kubernetes microservices REST APIs"
    result = optimizer.optimize(sample_profile, sample_job_analysis, everything, sample_gap_report)
    if result.iterations == 0:
        assert "shown" in result.stop_reason
        llm.complete.assert_not_called()


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


def test_optimizer_stops_after_a_round_that_changes_nothing():
    from resume_tailorer.analyzers.job_analyzer import JobAnalyzer as JA
    from resume_tailorer.analyzers.requirement_review import build_review
    from tests.fixtures.ats import POSTING, PROVENANCE, profile

    analysis = JA().analyze(POSTING)
    review = build_review(analysis, profile(), provenance=PROVENANCE, posting=POSTING)
    optimizer = ResumeTailoringOptimizer(max_iterations=3, llm=_mock_llm())
    with patch.object(optimizer.tailorer, "_refine_resume", return_value="Marketing analyst. Excel."):
        result = optimizer.optimize(profile(), analysis, "Marketing analyst. Excel.", GapReport([], ""), review=review)
    assert result.iterations == 1 and result.stop_reason == "A round changed nothing." and result.ceiling_reached


def test_a_round_that_adds_an_unsupported_term_is_discarded():
    """A stubbed model that slips in 'CPA' and 'Snowflake' claims: the round is thrown away."""
    from resume_tailorer.analyzers.job_analyzer import JobAnalyzer as JA
    from resume_tailorer.analyzers.requirement_review import build_review
    from tests.fixtures.ats import POSTING, PROVENANCE, profile

    analysis = JA().analyze(POSTING)
    review = build_review(analysis, profile(), provenance=PROVENANCE, posting=POSTING)
    start = "Marketing analyst. Excel."
    bad = "Licensed CPA. Led project management of Snowflake migrations with on-time delivery. Excel."
    optimizer = ResumeTailoringOptimizer(max_iterations=3, llm=_mock_llm())
    with patch.object(optimizer.tailorer, "_refine_resume", return_value=bad):
        result = optimizer.optimize(profile(), analysis, start, GapReport([], ""), review=review)
    assert result.tailored_resume == start
    assert "CPA" not in result.tailored_resume and "Snowflake" not in result.tailored_resume
    assert "discarded" in result.stop_reason


def test_a_round_that_shows_something_new_is_kept_and_rounds_are_capped():
    from resume_tailorer.analyzers.job_analyzer import JobAnalyzer as JA
    from resume_tailorer.analyzers.requirement_review import build_review
    from tests.fixtures.ats import POSTING, PROVENANCE, profile

    analysis = JA().analyze(POSTING)
    review = build_review(analysis, profile(), provenance=PROVENANCE, posting=POSTING)
    better = "Marketing analyst. Built SQL dashboards used by 40 regional managers. Excel."
    optimizer = ResumeTailoringOptimizer(max_iterations=3, llm=_mock_llm())
    calls = iter([better, better + " Led on-time delivery of a 6-month store launch across 4 teams, with weekly risk reviews.",
                  better + " more"])
    with patch.object(optimizer.tailorer, "_refine_resume", side_effect=lambda *a: next(calls)):
        result = optimizer.optimize(profile(), analysis, "Marketing analyst. Excel.", GapReport([], ""), review=review)
    assert "SQL dashboards" in result.tailored_resume and result.iterations <= 3


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


def test_score_resume_with_profile_recognizes_transferable_evidence_in_tailored_text():
    """Found live (2026-09-23): ResumeBenchmarker.benchmark() (the ORIGINAL
    score) was upgraded to recognize competency-map transferable evidence,
    but _score_resume (the TAILORED score) still only did literal-word
    matching -- so a resume could score LOWER after tailoring than its own
    untouched original purely from a methodology mismatch, not any real
    regression in content. Passing `profile` must close that gap."""
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())
    job_analysis = MagicMock()
    job_analysis.skills_required = []
    job_analysis.tools_required = []
    job_analysis.required_qualifications = ["cross-functional project management"]

    profile = CareerTruthProfile(
        contact_info={}, education=[], work_experience=[], skills=[], tools=[],
        certifications=[], accomplishments=[],
    )
    tailored_text = "Led a 10-person team and achieved 100% on-time delivery through risk mitigation."

    # Note: _score_resume's returned "missing" list is missing SKILLS/TOOLS
    # keywords (from calculate_keyword_alignment), not qualifications -- an
    # existing, pre-this-fix contract this test does not change. The
    # qualification-level evidence credit only shows up in `score`.
    score_without_profile, _, _ = optimizer._score_resume(tailored_text, job_analysis)
    assert score_without_profile == pytest.approx(0.0)

    score_with_profile, _, _ = optimizer._score_resume(tailored_text, job_analysis, profile)
    assert score_with_profile == pytest.approx(0.4)
    assert score_with_profile > score_without_profile


def test_score_resume_with_profile_recognizes_in_progress_degree():
    optimizer = ResumeTailoringOptimizer(llm=_mock_llm())
    job_analysis = MagicMock()
    job_analysis.skills_required = []
    job_analysis.tools_required = []
    job_analysis.required_qualifications = [
        "Currently enrolled in an accredited MBA program with an intended graduation of Spring 2027."
    ]

    profile = CareerTruthProfile(
        contact_info={},
        education=[
            EducationEntry(
                degree="Master of Business Administration",
                field="",
                institution="Brigham Young University",
                year=2027,
            )
        ],
        work_experience=[], skills=[], tools=[], certifications=[], accomplishments=[],
    )
    tailored_text = "EDUCATION\nBrigham Young University | 2027\nMaster of Business Administration"

    score, _, _ = optimizer._score_resume(tailored_text, job_analysis, profile)
    assert score == pytest.approx(0.4)


def test_optimizer_uses_llm_client():
    """Test that optimizer uses ResumeTailorer with an injected LLMClient."""
    llm = _mock_llm()
    optimizer = ResumeTailoringOptimizer(llm=llm)

    # Verify tailorer is initialized with the injected llm
    assert optimizer.tailorer is not None
    assert optimizer.tailorer.llm is not None
    assert optimizer.tailorer.llm is llm
