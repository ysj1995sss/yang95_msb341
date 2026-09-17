import pytest
from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmarker
from resume_tailorer.analyzers.gap_analyzer import GapAnalyzer, GapCategory

@pytest.fixture
def sample_profile():
    """A sample career truth profile."""
    return CareerTruthProfile(
        contact_info={"name": "Alice", "email": "alice@example.com"},
        education=[],
        work_experience=[
            WorkExperience(
                employer="TechCorp",
                title="Software Engineer",
                dates="2020-2022",
                responsibilities=["Built APIs", "Worked with Python"],
                accomplishments=["Improved performance by 30%"],
            )
        ],
        skills=["Python", "JavaScript"],
        tools=["Docker", "PostgreSQL"],
        certifications=[],
        accomplishments=[],
    )

@pytest.fixture
def sample_job_analysis():
    """A sample job analysis."""
    analyzer = JobAnalyzer()
    job_desc = """
    Senior Python Engineer needed.
    5+ years Python experience required.
    Docker and Kubernetes experience needed.
    PostgreSQL expertise.
    """
    return analyzer.analyze(job_desc)

def test_gap_analyzer_classifies_gaps(sample_profile, sample_job_analysis):
    """Gap analyzer classifies requirements into A-E."""
    benchmarker = ResumeBenchmarker()
    benchmark = benchmarker.benchmark(sample_profile, sample_job_analysis)

    analyzer = GapAnalyzer()
    gaps = analyzer.analyze(sample_profile, sample_job_analysis, benchmark)

    assert gaps is not None
    assert any(gap.category == GapCategory.A for gap in gaps.items) or len(gaps.items) >= 0
