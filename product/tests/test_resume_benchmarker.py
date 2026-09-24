import pytest
from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmarker, ResumeBenchmark

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

def test_benchmarker_scores_original_resume(sample_profile, sample_job_analysis):
    """Benchmarker produces a match score for the original resume."""
    benchmarker = ResumeBenchmarker()
    benchmark = benchmarker.benchmark(sample_profile, sample_job_analysis)

    assert isinstance(benchmark, ResumeBenchmark)
    assert 0 <= benchmark.original_match_score <= 1.0
    assert len(benchmark.keywords_matched) >= 0
    assert len(benchmark.keywords_missing) >= 0


def test_generic_word_overlap_does_not_cover_a_qualification(sample_profile):
    """Sharing 'team' or 'years' with a JD line is not evidence the candidate has that qualification."""
    from resume_tailorer.analyzers.job_analyzer import JobAnalysis

    job_analysis = JobAnalysis(
        required_qualifications=["strong communication and stakeholder leadership"],
        preferred_qualifications=[],
        responsibilities=[],
        skills_required=[],
        tools_required=[],
        education_required=None,
        experience_required=None,
        weighted_keywords=[],
    )

    benchmark = ResumeBenchmarker().benchmark(sample_profile, job_analysis)

    assert "strong communication and stakeholder leadership" in benchmark.qualifications_missing
    assert "strong communication and stakeholder leadership" not in benchmark.qualifications_covered
