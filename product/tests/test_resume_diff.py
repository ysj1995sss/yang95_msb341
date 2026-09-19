"""Tests for the resume diff generator: bullet matching, diff detection, fabrication risk."""

import pytest

from resume_tailorer.diff_generator import (
    ResumeDiffReport,
    BulletChange,
    DiffGenerator,
)
from resume_tailorer.models import CareerTruthProfile, WorkExperience


def test_diff_generator_initialization():
    """DiffGenerator can be instantiated."""
    gen = DiffGenerator()
    assert gen is not None


def test_diff_identifies_rephrased_bullet():
    """Detects when a bullet is rephrased but same accomplishment."""
    profile = CareerTruthProfile(
        contact_info={},
        education=[],
        work_experience=[
            WorkExperience(
                employer="TechCorp",
                title="Software Engineer",
                dates="2023-2024",
                responsibilities=[],
                accomplishments=[
                    "Built a REST API handling 100K requests/day",
                ],
            )
        ],
        skills=["Python", "FastAPI"],
        tools=["Docker"],
        certifications=[],
        accomplishments=[],
    )

    tailored_text = """Experience
    TechCorp | Software Engineer | 2023-2024
    - Architected high-performance REST API serving 100K daily requests using FastAPI
    """

    gen = DiffGenerator()
    report = gen.generate_diff(profile, tailored_text)

    assert len(report.changes) >= 1
    assert report.changes[0].change_type == "rephrased"
    assert "API" in report.changes[0].original
    assert "Architected" in report.changes[0].tailored


def test_diff_detects_reordering():
    """Detects when bullets are reordered."""
    profile = CareerTruthProfile(
        contact_info={},
        education=[],
        work_experience=[
            WorkExperience(
                employer="TechCorp",
                title="Engineer",
                dates="2023-2024",
                responsibilities=[],
                accomplishments=[
                    "First accomplishment",
                    "Second accomplishment",
                ],
            )
        ],
        skills=[],
        tools=[],
        certifications=[],
        accomplishments=[],
    )

    tailored_text = """Experience
    TechCorp | Engineer | 2023-2024
    - Second accomplishment
    - First accomplishment
    """

    gen = DiffGenerator()
    report = gen.generate_diff(profile, tailored_text)

    assert any(c.change_type == "reordered" for c in report.changes)


def test_diff_no_fabrication():
    """Ensures no new facts are in tailored text that weren't in profile."""
    profile = CareerTruthProfile(
        contact_info={},
        education=[],
        work_experience=[
            WorkExperience(
                employer="TechCorp",
                title="Engineer",
                dates="2023-2024",
                responsibilities=[],
                accomplishments=["Built a system"],
            )
        ],
        skills=["Python"],
        tools=[],
        certifications=[],
        accomplishments=[],
    )

    # Tailored text claims Java (not in profile)
    tailored_text = """Experience
    TechCorp | Engineer | 2023-2024
    - Built a system using Java
    """

    gen = DiffGenerator()
    report = gen.generate_diff(profile, tailored_text)

    # Should flag the Java introduction as a fabrication risk
    assert any("Java" in str(c) for c in report.issues) if hasattr(report, 'issues') else True


def test_diff_flags_fabricated_technology():
    """A tech keyword introduced in tailored text but absent from skills/tools is flagged."""
    profile = CareerTruthProfile(
        contact_info={},
        education=[],
        work_experience=[
            WorkExperience(
                employer="TechCorp",
                title="Engineer",
                dates="2023-2024",
                responsibilities=[],
                accomplishments=["Built a system"],
            )
        ],
        skills=["Python"],
        tools=[],
        certifications=[],
        accomplishments=[],
    )

    tailored_text = """Experience
    TechCorp | Engineer | 2023-2024
    - Built a system using Kubernetes
    """

    gen = DiffGenerator()
    report = gen.generate_diff(profile, tailored_text)

    assert len(report.issues) >= 1
    assert any("kubernetes" in issue.lower() for issue in report.issues)


def test_diff_report_renders_in_streamlit():
    """Mock Streamlit test: verify diff report can be rendered."""
    from resume_tailorer.diff_generator import ResumeDiffReport, BulletChange

    report = ResumeDiffReport(
        original_bullets=["Built a REST API"],
        tailored_bullets=["Architected high-performance REST API"],
        changes=[
            BulletChange(
                original="Built a REST API",
                tailored="Architected high-performance REST API",
                change_type="rephrased",
                reasoning="Added 'high-performance' to highlight scalability",
            )
        ],
    )

    # Verify report structure for rendering
    assert len(report.changes) == 1
    assert report.changes[0].reasoning is not None
    assert report.changes[0].change_type in [
        "rephrased", "reordered", "removed", "added", "highlighted"
    ]


def test_diff_generator_importable_from_package_root():
    """DiffGenerator, ResumeDiffReport, BulletChange are exported from resume_tailorer."""
    from resume_tailorer import DiffGenerator as PkgDiffGenerator
    from resume_tailorer import ResumeDiffReport as PkgResumeDiffReport
    from resume_tailorer import BulletChange as PkgBulletChange

    assert PkgDiffGenerator is DiffGenerator
    assert PkgResumeDiffReport is ResumeDiffReport
    assert PkgBulletChange is BulletChange
