"""Tests for the resume diff generator: bullet matching, diff detection, fabrication risk."""

import pytest

from resume_tailorer.diff_generator import (
    ResumeDiffReport,
    BulletChange,
    DiffGenerator,
)
from resume_tailorer.models import CareerTruthProfile, EducationEntry, WorkExperience


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


def _profile(accomplishments, skills=None, tools=None, employer="TechCorp", education=None, responsibilities=None):
    """Build a single-job CareerTruthProfile for diff tests."""
    return CareerTruthProfile(
        contact_info={},
        education=list(education or []),
        work_experience=[
            WorkExperience(
                employer=employer,
                title="Engineer",
                dates="2023-2024",
                responsibilities=list(responsibilities or []),
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
    """Reorder + reword + fabricated bullet are classified independently.

    Before the cross-block reconciliation pass (decision 018/019), a pure
    move landed as a spurious unpaired "removed" + "added" of the SAME
    string in different opcode blocks -- deterministic, but needlessly
    made an unchanged bullet look like it needed review. The reconciler
    now correctly recognizes these as the same bullet (change_type
    "unchanged"), which is strictly better for a reviewer without
    weakening the fabrication check below.
    """
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

    # The moved bullet keeps its text intact and is recognized as the same
    # bullet, not left as two unrelated remove/add entries.
    moved_text = "Reduced CI pipeline runtime from 40 minutes to 12 minutes"
    assert any(
        c.change_type == "unchanged" and c.original == moved_text and c.tailored == moved_text
        for c in report.changes
    )
    assert not any(c.tailored == moved_text and c.change_type == "added" for c in report.changes)
    assert not any(c.original == moved_text and c.change_type == "removed" for c in report.changes)

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
    # Long enough original that adding " in Python" stays under the length-
    # growth warning threshold -- this test is specifically about
    # fabrication-flagging, kept separate from the length check.
    profile = _profile(["Built and maintained a scalable data pipeline for the team"], skills=["Python 3.11"])
    tailored_text = "- Built and maintained a scalable data pipeline for the team in Python\n"

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
    # Long enough originals that adding " on Kubernetes" stays under the
    # length-growth warning threshold -- this test is specifically about
    # fabrication-dedup, kept separate from the length check.
    profile = _profile(
        ["Built a distributed system for internal tooling", "Ran deployments across every environment safely"],
        skills=["Python"],
    )
    tailored_text = (
        "- Built a distributed system for internal tooling on Kubernetes\n"
        "- Ran deployments across every environment safely on Kubernetes\n"
    )

    report = DiffGenerator().generate_diff(profile, tailored_text)

    kubernetes_issues = [i for i in report.issues if "kubernetes" in i.lower()]
    assert len(kubernetes_issues) == 1


def test_invented_metric_is_flagged_as_fabrication():
    """A percentage that does not appear in the Career Truth Profile is a fabrication risk."""
    profile = _profile(["Improved system reliability"], skills=["Python"])
    tailored_text = "- Improved system reliability by 47%\n"

    report = DiffGenerator().generate_diff(profile, tailored_text)

    assert any("47%" in issue for issue in report.issues)


def test_diff_generator_importable_from_package_root():
    """DiffGenerator, ResumeDiffReport, BulletChange are exported from resume_tailorer."""
    from resume_tailorer import DiffGenerator as PkgDiffGenerator
    from resume_tailorer import ResumeDiffReport as PkgResumeDiffReport
    from resume_tailorer import BulletChange as PkgBulletChange

    assert PkgDiffGenerator is DiffGenerator
    assert PkgResumeDiffReport is ResumeDiffReport
    assert PkgBulletChange is BulletChange


class TestFreeformPathSemanticDriftParity:
    """The freeform/PDF tailoring path (generate_diff) had NO semantic-drift
    protection at all before this consolidation -- only the DOCX splice
    path (DocxBulletTailorer) had it. These reproduce the exact real-world
    bug (decision 008: 'front-store growth strategy' silently narrowed to
    'front-store acquisition strategy') against generate_diff directly, to
    confirm the freeform path now catches what it previously would have
    missed entirely."""

    def test_semantic_narrowing_is_caught_on_the_freeform_path(self):
        profile = _profile(["Developed a front-store growth strategy identifying incremental sales"])
        tailored_text = "- Developed a front-store acquisition strategy identifying incremental sales\n"

        report = DiffGenerator().generate_diff(profile, tailored_text)

        assert any("semantic drift" in issue.lower() for issue in report.issues)

    def test_evidence_backed_competency_label_is_not_flagged(self):
        """The same evidence-backed-abstraction exemption DocxBulletTailorer
        gets (decision 009) must also apply here -- otherwise this
        consolidation would make the freeform path MORE conservative than
        before in a way that blocks legitimate, truthful abstraction."""
        profile = _profile(
            ["Achieved 100% on-time delivery across 200+ performances through risk mitigation"]
        )
        tailored_text = (
            "- Achieved 100% on-time project management delivery across 200+ "
            "performances through risk mitigation\n"
        )

        report = DiffGenerator().generate_diff(profile, tailored_text)

        assert not any("project" in issue.lower() or "management" in issue.lower() for issue in report.issues)

    def test_dropping_a_metric_is_caught_on_the_freeform_path(self):
        profile = _profile(["Achieved 100% on-time delivery across 200+ performances"])
        tailored_text = "- Achieved on-time delivery across 200+ performances\n"

        report = DiffGenerator().generate_diff(profile, tailored_text)

        assert any("semantic drift" in issue.lower() for issue in report.issues)


class TestFreeformPathLengthControl:
    """Steps 10-15 audit Phase F: bullet_length_delta existed but had no
    caller anywhere in the codebase before this -- length was purely a
    post-hoc PDFGenerator rendering concern for the freeform path, with no
    bullet-level signal at tailoring/validation time at all."""

    def test_bullet_that_grows_past_the_threshold_is_flagged(self):
        profile = _profile(["Managed a small team"])
        tailored_text = (
            "- Managed a cross-functional team of engineers, designers, and product "
            "managers across three continents\n"
        )

        report = DiffGenerator().generate_diff(profile, tailored_text)

        assert any("longer" in issue.lower() and "wrap" in issue.lower() for issue in report.issues)

    def test_bullet_within_the_threshold_is_not_flagged(self):
        profile = _profile(["Managed a cross-functional team of engineers and designers"])
        tailored_text = "- Led a cross-functional team of engineers and designers\n"

        report = DiffGenerator().generate_diff(profile, tailored_text)

        assert not any("wrap onto an extra line" in issue for issue in report.issues)


class TestFreeformPathRecognizesTheWholeProfile:
    """Found live (2026-09-28), first real end-to-end test with a live LLM:
    a real resume's education honors/scholarships and skills list both got
    mislabeled as fabricated 'added' bullets. _extract_bullets_from_profile
    only ever read job.accomplishments -- job.responsibilities, education
    notes, skills/tools/certifications, and summary were invisible to the
    pairing step, so ANY tailored bullet built from those (100% truthful)
    categories had no possible match and was always misclassified as new.
    This is the exact gap _profile_blob (the fabrication-risk check's
    trusted vocabulary) was already fixed for once before -- see its own
    docstring -- just never mirrored in the pairing step that decides
    change_type in the first place."""

    def test_a_skill_restated_as_a_bullet_is_not_flagged_as_added(self):
        profile = _profile(["Built internal tools"], skills=["Digital Marketing", "Prompt Engineering"])
        tailored_text = "- Built internal tools\n- Digital Marketing\n- Prompt Engineering\n"

        report = DiffGenerator().generate_diff(profile, tailored_text)

        added = [c for c in report.changes if c.change_type == "added"]
        assert added == []

    def test_an_education_honor_restated_as_a_bullet_is_not_flagged_as_added(self):
        profile = _profile(
            ["Built internal tools"],
            education=[EducationEntry(
                degree="BS", field="Business", institution="State University", year=2024,
                notes=["Dean's List x5 Semesters | Full Merit Scholar | GPA: 3.92/4.0"],
            )],
        )
        tailored_text = "- Built internal tools\n- Dean's List x5 Semesters | Full Merit Scholar | GPA: 3.92/4.0\n"

        report = DiffGenerator().generate_diff(profile, tailored_text)

        added = [c for c in report.changes if c.change_type == "added"]
        assert added == []

    def test_a_responsibility_restated_as_a_bullet_is_not_flagged_as_added(self):
        profile = _profile([], responsibilities=["Consulted clients on brand growth strategy"])
        tailored_text = "- Consulted clients on brand growth strategy\n"

        report = DiffGenerator().generate_diff(profile, tailored_text)

        added = [c for c in report.changes if c.change_type == "added"]
        assert added == []

    def test_reworded_bullet_split_across_opcode_blocks_is_not_flagged_as_added(self):
        """Found live (2026-09-28) on a REAL resume: SequenceMatcher's
        opcode blocks are position-local (see the "replace" tag's greedy
        pairing, scoped to only its own slice). When the tailored
        document's section order (e.g. Education, then Experience, then
        Skills) differs from the profile's internal storage order (job-by-
        job, then education, then skills), a lightly-reworded bullet's
        original and tailored versions can land in DIFFERENT opcode
        blocks -- one block reports the original as "removed" (no match
        in ITS slice), a completely different block reports the reworded
        version as "added" (no match in ITS slice) -- even though,
        globally, they're obviously the same bullet with one clause
        appended. This must be reconciled into a single rephrased/modified
        change, not two spurious removed+added entries."""
        profile = _profile(
            ["Consulted Acme Client: Analyzed data to diagnose business challenge and develop growth strategy"],
            skills=["Tableau", "SQL", "Excel", "Power BI", "PMS", "NIQ"],
        )
        # Tailored document order: skills-heavy content FIRST (unlike the
        # profile's storage order, which puts work-experience bullets
        # first) -- this reordering is what pushes the real match into a
        # different opcode block than the naive same-position case.
        tailored_text = (
            "- Tableau\n- SQL\n- Excel\n"
            "- Consulted Acme Client: Analyzed data to diagnose business challenge and develop "
            "growth strategy and long-term positioning\n"
        )

        report = DiffGenerator().generate_diff(profile, tailored_text)

        added = [c for c in report.changes if c.change_type == "added"]
        assert added == [], f"expected no false 'added' bullets, got: {added}"
        rescued = [c for c in report.changes if "long-term positioning" in c.tailored]
        assert rescued and rescued[0].change_type in ("rephrased", "modified")

    def test_an_exact_duplicate_split_across_blocks_is_recognized_as_unchanged(self):
        profile = _profile(
            ["Managed a small team"],
            education=[EducationEntry(
                degree="MBA", field="Business", institution="State University", year=2027,
                notes=["Awarded Half-Tuition Merit Scholarship"],
            )],
            skills=["Tableau", "SQL", "Excel", "Power BI"],
        )
        tailored_text = (
            "- Tableau\n- SQL\n- Excel\n"
            "- Awarded Half-Tuition Merit Scholarship\n"
            "- Managed a cross-functional team\n"
        )

        report = DiffGenerator().generate_diff(profile, tailored_text)

        added = [c for c in report.changes if c.change_type == "added"]
        assert not any("Scholarship" in c.tailored for c in added)

    def test_a_genuinely_new_bullet_with_no_match_anywhere_is_still_caught(self):
        """The fix must not swallow real fabrication detection. A bullet
        with no counterpart in accomplishments, responsibilities,
        education notes, skills, tools, or certifications must never end
        up silently accepted.

        With exactly one other profile-only item ("Python") in play, this
        can get SequenceMatcher-paired against the new bullet as "modified"
        (low similarity) rather than a clean "added" -- broadening
        original_bullets makes list lengths line up in this specific
        edge case. That's an acceptable trade: build_freeform_changes'
        AMBIGUOUS_PAIRING_THRESHOLD (0.45) still catches the low-similarity
        pairing and REJECTs it, so the end-to-end guarantee (never silently
        accepted) holds regardless of which path flags it -- verified via
        build_freeform_changes, the function actually used in production,
        not the raw DiffGenerator output alone."""
        from resume_tailorer.artifacts.changes import build_freeform_changes
        from resume_tailorer.analyzers.gap_analyzer import GapReport

        profile = _profile(["Built internal tools"], skills=["Python"])
        tailored_text = "- Built internal tools\n- Led a team of 50 engineers\n"

        changes = build_freeform_changes(profile, tailored_text, GapReport(items=[], summary=""))
        fabricated = [c for c in changes if "Led a team of 50 engineers" in c.proposed_text]

        assert fabricated, "the fabricated bullet must appear as a reviewable change"
        assert fabricated[0].disposition.value != "accepted"
        assert fabricated[0].validation_status.value != "pass"
