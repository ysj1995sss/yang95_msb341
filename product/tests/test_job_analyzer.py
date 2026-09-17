import pytest
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer, JobAnalysis

@pytest.fixture
def sample_job_description():
    return """
    Senior Software Engineer - Full Stack

    Requirements:
    - 5+ years of software engineering experience
    - Strong proficiency in Python and Go
    - Experience with Kubernetes and Docker
    - Familiarity with PostgreSQL or similar databases
    - Experience with microservices architecture

    Preferred:
    - Experience with AWS
    - Prior startup experience
    - Open source contributions

    Responsibilities:
    - Design and build scalable APIs
    - Mentor junior engineers
    - Participate in code reviews
    - Contribute to system architecture decisions

    We're looking for someone who can own projects end-to-end.
    """

def test_job_analyzer_extracts_requirements(sample_job_description):
    """Analyzer extracts required qualifications."""
    analyzer = JobAnalyzer()
    analysis = analyzer.analyze(sample_job_description)

    assert isinstance(analysis, JobAnalysis)
    assert "python" in [s.lower() for s in analysis.skills_required]
    assert "5+ years" in str(analysis.required_qualifications) or "5 years" in sample_job_description

def test_job_analyzer_extracts_preferred(sample_job_description):
    """Analyzer extracts preferred qualifications."""
    analyzer = JobAnalyzer()
    analysis = analyzer.analyze(sample_job_description)

    assert len(analysis.preferred_qualifications) > 0

def test_job_analyzer_identifies_weighted_keywords(sample_job_description):
    """Analyzer identifies keywords and weights them (high/medium/low)."""
    analyzer = JobAnalyzer()
    analysis = analyzer.analyze(sample_job_description)

    assert len(analysis.weighted_keywords) > 0
    # Keywords should include both hard skills and soft skills
