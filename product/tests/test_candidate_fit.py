import pytest
from datetime import datetime
from resume_tailorer.job_search.candidate_fit import CandidateFitScorer
from resume_tailorer.models.career_profile import (
    CareerTruthProfile,
    EducationEntry,
    WorkExperience,
)
from resume_tailorer.job_search.models import JobPosting, JobSource


@pytest.fixture
def sample_profile():
    """Create a sample candidate profile with 5 years of experience."""
    return CareerTruthProfile(
        contact_info={"name": "John Doe", "email": "john@example.com", "phone": "555-1234", "location": "Seattle"},
        education=[
            EducationEntry(
                degree="BS",
                field="Computer Science",
                institution="University of Washington",
                year=2018,
                gpa="3.8"
            )
        ],
        work_experience=[
            WorkExperience(
                employer="Tech Company A",
                title="Software Engineer",
                dates="2018-2020",
                responsibilities=["Built APIs", "Wrote tests"],
                accomplishments=["Led microservices migration"],
                location="Seattle",
                employment_type="Full-time"
            ),
            WorkExperience(
                employer="Tech Company B",
                title="Senior Software Engineer",
                dates="2020-2023",
                responsibilities=["Architected systems", "Mentored juniors"],
                accomplishments=["Reduced latency by 50%"],
                location="Seattle",
                employment_type="Full-time"
            )
        ],
        skills=["Python", "Go", "JavaScript", "AWS", "Docker", "Kubernetes", "PostgreSQL"],
        tools=["Docker", "Kubernetes", "PostgreSQL", "GitHub", "CircleCI"],
        certifications=["AWS Solutions Architect"],
        accomplishments=["Led migration to microservices", "Built distributed system handling 10M requests/day"]
    )


@pytest.fixture
def junior_profile():
    """Create a junior candidate profile with 1 year of experience."""
    return CareerTruthProfile(
        contact_info={"name": "Jane Smith", "email": "jane@example.com", "phone": "555-5678", "location": "NYC"},
        education=[
            EducationEntry(
                degree="BS",
                field="Computer Science",
                institution="Stanford",
                year=2023,
                gpa="3.9"
            )
        ],
        work_experience=[
            WorkExperience(
                employer="Startup Inc",
                title="Junior Software Engineer",
                dates="2023-2024",
                responsibilities=["Implemented features", "Fixed bugs"],
                accomplishments=["Shipped mobile app feature"],
                location="NYC",
                employment_type="Full-time"
            )
        ],
        skills=["JavaScript", "React", "Node.js"],
        tools=["Git", "npm", "Visual Studio Code"],
        certifications=[],
        accomplishments=["Shipped first production feature"]
    )


@pytest.fixture
def sample_job():
    """Create a sample job posting requiring 5+ years of experience."""
    return JobPosting(
        source=JobSource.LINKEDIN,
        source_id="linkedin-12345",
        company="TechCorp",
        title="Senior Software Engineer",
        location="Seattle, WA",
        description="""
        We are looking for a Senior Software Engineer with strong experience in Python, Go, and AWS.
        You should be proficient in Docker and Kubernetes for building scalable microservices.
        Experience with distributed systems is a must.
        You will work with PostgreSQL and modern database technologies.
        Requirements:
        - 5+ years of software engineering experience
        - Strong proficiency in Python and Go
        - Experience with Kubernetes and Docker
        - AWS experience
        - PostgreSQL or similar database experience
        """,
        experience_required="5+ years",
        education_required="BS in Computer Science or related field",
        sponsorship_available=True,
        work_mode="on-site",
        url="https://example.com/job/12345",
        ats_platform="Lever"
    )


@pytest.fixture
def junior_job():
    """Create a job posting for junior level (entry-level)."""
    return JobPosting(
        source=JobSource.INDEED,
        source_id="indeed-67890",
        company="StartupCo",
        title="Junior Frontend Developer",
        location="NYC, NY",
        description="""
        We are looking for a Junior Frontend Developer with experience in JavaScript and React.
        This is a great opportunity to grow your skills in a fast-paced environment.
        Requirements:
        - 0-2 years of experience
        - JavaScript and React knowledge
        - Basic understanding of web development
        """,
        experience_required="0-2 years",
        education_required="High School or equivalent",
        sponsorship_available=False,
        work_mode="remote",
        url="https://example.com/job/67890"
    )


@pytest.fixture
def no_requirements_job():
    """Create a job posting with no specific requirements listed."""
    return JobPosting(
        source=JobSource.LINKEDIN,
        source_id="linkedin-99999",
        company="UnknownCorp",
        title="Software Engineer",
        location="Remote",
        description="Join our team as a Software Engineer. Great opportunity to work on interesting problems.",
        experience_required=None,
        education_required=None,
        sponsorship_available=True,
        work_mode="remote",
        url="https://example.com/job/99999"
    )


def test_fit_scorer_initialization():
    """CandidateFitScorer can be instantiated."""
    scorer = CandidateFitScorer()
    assert scorer is not None
    assert isinstance(scorer, CandidateFitScorer)


def test_fit_perfect_match(sample_profile, sample_job):
    """Candidate with all required skills and matching experience should score high (80-100)."""
    scorer = CandidateFitScorer()
    score = scorer.score_fit(sample_profile, sample_job)

    assert isinstance(score, (int, float))
    assert 0 <= score <= 100
    assert score >= 80, f"Expected score >= 80 for perfect match, got {score}"


def test_fit_missing_skills(junior_profile, sample_job):
    """Candidate missing most required skills should score lower."""
    scorer = CandidateFitScorer()
    score = scorer.score_fit(junior_profile, sample_job)

    assert isinstance(score, (int, float))
    assert 0 <= score <= 100
    # Junior has only JavaScript, missing Python, Go, AWS, Kubernetes, Docker, PostgreSQL
    assert score < 60, f"Expected score < 60 for missing most skills, got {score}"


def test_fit_underqualified_experience(junior_profile, sample_job):
    """Candidate with less experience than required should score lower."""
    scorer = CandidateFitScorer()
    score = scorer.score_fit(junior_profile, sample_job)

    assert isinstance(score, (int, float))
    assert 0 <= score <= 100
    # Junior has 1 year, job requires 5+ years (two levels off: entry vs senior)
    # Experience score should be 40% (two+ levels off)
    assert score < 65, f"Expected lower score for underqualified experience, got {score}"


def test_fit_overqualified(sample_profile, junior_job):
    """Candidate with more experience than required should score well (but not penalized for overqualification)."""
    scorer = CandidateFitScorer()
    score = scorer.score_fit(sample_profile, junior_job)

    assert isinstance(score, (int, float))
    assert 0 <= score <= 100
    # Senior with 5 years applying for junior role (0-2 years)
    # Experience score is 100 (meets or exceeds requirement)
    assert score >= 60, f"Expected score >= 60 for overqualified, got {score}"


def test_fit_education_match(sample_profile, sample_job):
    """Candidate with matching degree should score higher than without."""
    scorer = CandidateFitScorer()
    score_with_degree = scorer.score_fit(sample_profile, sample_job)

    # Create profile without relevant education
    profile_no_degree = CareerTruthProfile(
        contact_info=sample_profile.contact_info,
        education=[
            EducationEntry(
                degree="BA",
                field="Philosophy",
                institution="Some University",
                year=2018
            )
        ],
        work_experience=sample_profile.work_experience,
        skills=sample_profile.skills,
        tools=sample_profile.tools,
        certifications=sample_profile.certifications,
        accomplishments=sample_profile.accomplishments
    )
    score_wrong_degree = scorer.score_fit(profile_no_degree, sample_job)

    assert isinstance(score_with_degree, (int, float))
    assert isinstance(score_wrong_degree, (int, float))
    assert score_with_degree > score_wrong_degree, "Matching education should result in higher score"


def test_fit_no_requirements(sample_profile, no_requirements_job):
    """When job has no requirements specified, score should be neutral (around 80%)."""
    scorer = CandidateFitScorer()
    score = scorer.score_fit(sample_profile, no_requirements_job)

    assert isinstance(score, (int, float))
    assert 0 <= score <= 100
    # With no requirements, all components default to 80%
    assert 70 <= score <= 90, f"Expected neutral score (70-90) for no requirements, got {score}"


def test_fit_returns_0_to_100(sample_profile, sample_job, junior_profile, junior_job):
    """Score should always be between 0 and 100."""
    scorer = CandidateFitScorer()

    # Test various combinations
    scores = [
        scorer.score_fit(sample_profile, sample_job),
        scorer.score_fit(junior_profile, sample_job),
        scorer.score_fit(sample_profile, junior_job),
        scorer.score_fit(junior_profile, junior_job),
    ]

    for score in scores:
        assert isinstance(score, (int, float)), f"Score should be numeric, got {type(score)}"
        assert 0 <= score <= 100, f"Score should be between 0 and 100, got {score}"


def test_fit_score_is_float():
    """Score should be returned as an actual float (e.g. 85.0, not 85)."""
    scorer = CandidateFitScorer()
    profile = CareerTruthProfile(
        contact_info={"name": "Test", "email": "test@example.com"},
        education=[],
        work_experience=[],
        skills=["Python"],
        tools=[],
        certifications=[],
        accomplishments=[]
    )
    job = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="test-123",
        company="Test Corp",
        title="Test Role",
        location="Remote",
        description="Test description with Python requirement",
        sponsorship_available=True
    )

    score = scorer.score_fit(profile, job)
    assert isinstance(score, float), f"Score should be a float, got {type(score)}"
    assert 0 <= score <= 100
