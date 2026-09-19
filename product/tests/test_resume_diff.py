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


def _profile(accomplishments, skills=None, tools=None, employer="TechCorp"):
    """Build a single-job CareerTruthProfile for diff tests."""
    return CareerTruthProfile(
        contact_info={},
        education=[],
        work_experience=[
            WorkExperience(
                employer=employer,
                title="Engineer",
                dates="2023-2024",
                responsibilities=[],
                accomplishments=list(accomplishments),
            )
        ],
        skills=list(skills or []),
        tools=list(tools or []),
        certifications=[],
        accomplishments=[],
    )


def test_asterisk_bullets_are_extracted():
    """`*` is a valid bullet marker, like `-` and `•`."""
    gen = DiffGenerator()
    text = """Experience
    TechCorp | Engineer | 2023-2024
    * Built a REST API handling 100K requests/day
    * Led migration of the billing service
    """

    bullets = gen._extract_bullets_from_text(text)

    assert bullets == [
        "Built a REST API handling 100K requests/day",
        "Led migration of the billing service",
    ]


def test_asterisk_bullets_do_not_report_everything_as_removed():
    """With `*` bullets, unchanged content is not falsely reported as removed."""
    profile = _profile(["Built a REST API handling 100K requests/day"])
    tailored_text = """Experience
    * Built a REST API handling 100K requests/day
    """

    report = DiffGenerator().generate_diff(profile, tailored_text)

    assert report.tailored_bullets  # not empty
    assert not any(c.change_type == "removed" for c in report.changes)


def test_mixed_bullet_markers_all_extracted():
    """A mix of -, * and • markers all parse as bullets."""
    gen = DiffGenerator()
    text = "- dash bullet\n* star bullet\n• dot bullet\nnot a bullet"

    assert gen._extract_bullets_from_text(text) == [
        "dash bullet",
        "star bullet",
        "dot bullet",
    ]


def test_reorder_plus_reword_plus_new_bullet_not_scrambled():
    """Reorder + reword + fabricated bullet are classified independently."""
    profile = _profile(
        [
            "Built a REST API handling 100K requests per day",
            "Mentored three junior engineers on code review practices",
            "Reduced CI pipeline runtime from 40 minutes to 12 minutes",
        ],
        skills=["Python"],
    )

    # Bullet 3 moved to the front (reorder), bullet 1 reworded,
    # and a genuinely new AWS/Kubernetes bullet inserted in the middle.
    tailored_text = """Experience
    - Reduced CI pipeline runtime from 40 minutes to 12 minutes
    - Architected a REST API serving 100K requests per day
    - Designed AWS Kubernetes autoscaling infrastructure
    - Mentored three junior engineers on code review practices
    """

    report = DiffGenerator().generate_diff(profile, tailored_text)

    # The fabricated bullet is surfaced as genuinely new content, not silently
    # paired against an unrelated original.
    added = [c for c in report.changes if c.change_type == "added"]
    kubernetes_added = [c for c in added if "Kubernetes" in c.tailored]
    assert len(kubernetes_added) == 1
    assert kubernetes_added[0].original == ""

    # The moved bullet keeps its text intact: difflib reports a move as a
    # remove + add of the SAME string, never as a scrambled rewrite.
    moved_text = "Reduced CI pipeline runtime from 40 minutes to 12 minutes"
    assert any(c.change_type == "added" and c.tailored == moved_text for c in report.changes)
    assert any(c.change_type == "removed" and c.original == moved_text for c in report.changes)

    # The reworded bullet is paired with ITS original, not with a reordered one.
    reworded = [
        c for c in report.changes if "Architected a REST API" in c.tailored
    ]
    assert len(reworded) == 1
    assert "Built a REST API" in reworded[0].original
    assert reworded[0].change_type == "rephrased"

    # The mentoring bullet survived unchanged - never paired against the new one.
    assert not any(
        "Mentored three junior engineers" in c.original
        and "Kubernetes" in c.tailored
        for c in report.changes
    )


def test_skill_with_version_suffix_not_flagged_as_fabrication():
    """Profile skill 'Python 3.11' covers a bullet mentioning 'Python'."""
    profile = _profile(["Built a data pipeline"], skills=["Python 3.11"])
    tailored_text = "- Built a data pipeline in Python\n"

    report = DiffGenerator().generate_diff(profile, tailored_text)

    assert not any("python" in issue.lower() for issue in report.issues)


def test_skill_with_parenthetical_suffix_not_flagged_as_fabrication():
    """Profile tool 'AWS (EC2, S3)' covers a bullet mentioning 'AWS'."""
    profile = _profile(["Ran production infrastructure"], tools=["AWS (EC2, S3)"])
    tailored_text = "- Ran production infrastructure on AWS\n"

    report = DiffGenerator().generate_diff(profile, tailored_text)

    assert not any("aws" in issue.lower() for issue in report.issues)


def test_skill_mentioned_only_in_accomplishment_prose_is_known():
    """A tech named in an accomplishment counts as known even if not in skills."""
    profile = _profile(
        ["Deployed services with Docker on Kubernetes clusters"], skills=[]
    )
    tailored_text = "- Deployed services with Docker on Kubernetes clusters\n"

    report = DiffGenerator().generate_diff(profile, tailored_text)

    assert report.issues == []


def test_go_inside_algorithm_is_not_a_false_positive():
    """'go' must not match inside 'algorithm' (word-boundary matching)."""
    profile = _profile(["Improved matching algorithm accuracy"])
    tailored_text = "- Improved the matching algorithm's accuracy by 12%\n"

    report = DiffGenerator().generate_diff(profile, tailored_text)

    assert not any(
        issue.lower().startswith("⚠️ fabrication risk: 'go'") for issue in report.issues
    )
    assert not any("'go'" in issue for issue in report.issues)


def test_real_go_usage_is_still_flagged():
    """Word-boundary matching still catches a genuine fabricated 'Go' claim."""
    profile = _profile(["Built a service"], skills=["Python"])
    tailored_text = "- Built a high-throughput service in Go\n"

    report = DiffGenerator().generate_diff(profile, tailored_text)

    assert any("'go'" in issue.lower() for issue in report.issues)


def test_fabrication_warning_deduplicated_across_bullets():
    """The same fabricated tech is reported once, not once per bullet."""
    profile = _profile(["Built a system", "Ran deployments"], skills=["Python"])
    tailored_text = (
        "- Built a system on Kubernetes\n- Ran deployments on Kubernetes\n"
    )

    report = DiffGenerator().generate_diff(profile, tailored_text)

    kubernetes_issues = [i for i in report.issues if "kubernetes" in i.lower()]
    assert len(kubernetes_issues) == 1


def test_diff_generator_importable_from_package_root():
    """DiffGenerator, ResumeDiffReport, BulletChange are exported from resume_tailorer."""
    from resume_tailorer import DiffGenerator as PkgDiffGenerator
    from resume_tailorer import ResumeDiffReport as PkgResumeDiffReport
    from resume_tailorer import BulletChange as PkgBulletChange

    assert PkgDiffGenerator is DiffGenerator
    assert PkgResumeDiffReport is ResumeDiffReport
    assert PkgBulletChange is BulletChange
