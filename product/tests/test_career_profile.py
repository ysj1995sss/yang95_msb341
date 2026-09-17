import pytest
from resume_tailorer.models.career_profile import (
    CareerTruthProfile,
    WorkExperience,
    EducationEntry,
)


def test_career_profile_creation():
    """Profile can be created with all required fields."""
    profile = CareerTruthProfile(
        contact_info={"name": "John Doe", "email": "john@example.com"},
        education=[
            EducationEntry(degree="BS", field="Computer Science", institution="MIT", year=2020)
        ],
        work_experience=[
            WorkExperience(
                employer="Acme Corp",
                title="Software Engineer",
                dates="2020-2022",
                responsibilities=["Built APIs", "Mentored junior engineers"],
                accomplishments=["Reduced latency by 40%"],
            )
        ],
        skills=["Python", "JavaScript", "Go"],
        tools=["Docker", "Kubernetes", "PostgreSQL"],
        certifications=["AWS Solutions Architect"],
        accomplishments=["Led migration to microservices"],
    )
    assert profile.name == "John Doe"
    assert len(profile.work_experience) == 1
    assert profile.work_experience[0].employer == "Acme Corp"


def test_career_profile_serialization():
    """Profile can be serialized to dict and back."""
    original = CareerTruthProfile(
        contact_info={"name": "Jane Smith"},
        education=[],
        work_experience=[],
        skills=["Python"],
        tools=[],
        certifications=[],
        accomplishments=[],
    )
    data = original.to_dict()
    restored = CareerTruthProfile.from_dict(data)
    assert restored.name == "Jane Smith"
    assert restored.skills == ["Python"]


def test_work_experience_dates_validation():
    """Work experience dates are stored as strings; no validation here (resume parser owns validation)."""
    exp = WorkExperience(
        employer="Company",
        title="Role",
        dates="2020-2022",
        responsibilities=[],
        accomplishments=[],
    )
    assert exp.dates == "2020-2022"
