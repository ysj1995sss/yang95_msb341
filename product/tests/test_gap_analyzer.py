import pytest
from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmarker, ResumeBenchmark
from resume_tailorer.analyzers.gap_analyzer import (
    GapAnalyzer,
    GapCategory,
    GapItem,
    GapReport,
    find_unsupported_claims,
)

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
    assert len(gaps.items) >= 1
    assert all(isinstance(gap.category, GapCategory) for gap in gaps.items)


def test_shared_generic_words_are_not_category_a(sample_profile):
    """A JD line that only shares filler words with the resume is missing, not 'already on resume'."""
    from resume_tailorer.analyzers.job_analyzer import JobAnalysis
    from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmark

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
    benchmark = ResumeBenchmark(
        original_match_score=0.0,
        keywords_matched=[],
        keywords_missing=[],
        qualifications_covered=[],
        qualifications_missing=[],
    )

    gaps = GapAnalyzer().analyze(sample_profile, job_analysis, benchmark)
    item = next(g for g in gaps.items if g.requirement == "strong communication and stakeholder leadership")
    assert item.category in (GapCategory.D, GapCategory.E)


def test_real_python_api_experience_is_category_a(sample_profile):
    """A requirement whose distinctive content is on the resume is Category A."""
    from resume_tailorer.analyzers.job_analyzer import JobAnalysis
    from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmark

    job_analysis = JobAnalysis(
        required_qualifications=["experience building Python APIs"],
        preferred_qualifications=[],
        responsibilities=[],
        skills_required=[],
        tools_required=[],
        education_required=None,
        experience_required=None,
        weighted_keywords=[],
    )
    benchmark = ResumeBenchmark(
        original_match_score=0.0,
        keywords_matched=[],
        keywords_missing=[],
        qualifications_covered=[],
        qualifications_missing=[],
    )

    gaps = GapAnalyzer().analyze(sample_profile, job_analysis, benchmark)
    item = next(g for g in gaps.items if g.requirement == "experience building Python APIs")
    assert item.category == GapCategory.A


class TestFindUnsupportedClaims:
    """
    Regression tests for the "unsupported claims added" check (spec 001
    item 19), added after live testing (2026-09-21) showed an LLM adding a
    Category E ("truly missing -- never add") item to the tailored output
    despite the prompt saying not to.
    """

    def _gap_report_with(self, category: GapCategory, requirement: str) -> GapReport:
        return GapReport(
            items=[GapItem(requirement=requirement, category=category, reason="test")],
            summary="test",
        )

    def test_flags_a_single_keyword_e_item_that_appears_in_output(self):
        gap_report = self._gap_report_with(GapCategory.E, "Kubernetes")
        tailored_text = "Deployed services using Kubernetes and Docker."
        assert find_unsupported_claims(gap_report, tailored_text) == ["Kubernetes"]

    def test_does_not_flag_an_e_item_that_stays_out_of_the_output(self):
        gap_report = self._gap_report_with(GapCategory.E, "Kubernetes")
        tailored_text = "Deployed services using Docker."
        assert find_unsupported_claims(gap_report, tailored_text) == []

    def test_flags_a_sentence_style_e_item_via_qualification_overlap(self):
        gap_report = self._gap_report_with(GapCategory.E, "leading a team of engineers")
        tailored_text = "Experienced in leading a team of engineers on critical projects."
        assert find_unsupported_claims(gap_report, tailored_text) == ["leading a team of engineers"]

    def test_ignores_non_e_categories(self):
        gap_report = GapReport(
            items=[
                GapItem(requirement="Kubernetes", category=GapCategory.A, reason="test"),
                GapItem(requirement="Docker", category=GapCategory.B, reason="test"),
            ],
            summary="test",
        )
        tailored_text = "Used Kubernetes and Docker extensively."
        assert find_unsupported_claims(gap_report, tailored_text) == []
