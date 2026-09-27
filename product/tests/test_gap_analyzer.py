import pytest
from resume_tailorer.models import CareerTruthProfile, EducationEntry, WorkExperience
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmarker, ResumeBenchmark
from resume_tailorer.analyzers.gap_analyzer import (
    EvidenceLevel,
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


def _empty_benchmark() -> "ResumeBenchmark":
    return ResumeBenchmark(
        original_match_score=0.0,
        keywords_matched=[],
        keywords_missing=[],
        qualifications_covered=[],
        qualifications_missing=[],
    )


def _job_requiring(*required_qualifications: str) -> JobAnalysis:
    return JobAnalysis(
        required_qualifications=list(required_qualifications),
        preferred_qualifications=[],
        responsibilities=[],
        skills_required=[],
        tools_required=[],
        education_required=None,
        experience_required=None,
        weighted_keywords=[],
    )


class TestTransferableEvidenceRegression:
    """
    Regression suite for a real failure found live (2026-09-23): purely
    lexical requirement matching treated "the exact JD phrase is absent"
    as "unsupported," even when the resume contains clear, truthful,
    transferable evidence for the competency. These map directly onto the
    fix request's Test A-E cases, run through the real GapAnalyzer (not
    just the underlying competency_map module) so a regression in the
    classification wiring itself is caught, not just in the matcher.
    """

    def _gmdp_style_profile(self) -> CareerTruthProfile:
        return CareerTruthProfile(
            contact_info={"name": "Shangjun Yang", "email": "yang95@byu.edu"},
            education=[],
            work_experience=[
                WorkExperience(
                    employer="International Broadway",
                    title="Operational Specialist",
                    dates="Dec 2023-Apr 2024",
                    responsibilities=[],
                    accomplishments=[
                        "Led a 10-person operations team, diagnosed process bottlenecks through workflow mapping",
                        "Achieved 100% on-time delivery across 200+ performances via real-time communication and risk mitigation",
                    ],
                ),
                WorkExperience(
                    employer="CVS Health",
                    title="Marketing Strategy MBA Corporate Intern",
                    dates="May 2026-Aug 2026",
                    responsibilities=[],
                    accomplishments=[
                        "Aligned 30+ cross-functional stakeholders and distilled complex consumer research into "
                        "executive-ready recommendations, presented to C-suite and VP leaders",
                    ],
                ),
            ],
            skills=[],
            tools=[],
            certifications=[],
            accomplishments=[],
        )

    def test_a_project_management_is_not_unsupported(self):
        """Test A: 'project management' never appears literally, but
        on-time delivery + risk mitigation strongly demonstrate it --
        must land in B or C, never E."""
        profile = self._gmdp_style_profile()
        job_analysis = _job_requiring("cross-functional project management")
        gaps = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())
        item = next(g for g in gaps.items if g.requirement == "cross-functional project management")
        assert item.category in (GapCategory.A, GapCategory.B, GapCategory.C)
        assert item.candidate_evidence and item.candidate_evidence not in ("None", "Unknown")

    def test_b_business_analysis_from_analyzing_data(self):
        """Test B: 'business analysis' via a Mondelez/Nielsen-Circana
        consulting project stored in education notes, not work
        experience -- must participate in matching at all."""
        profile = self._gmdp_style_profile()
        profile.education.append(
            EducationEntry(
                degree="MBA",
                field="Business",
                institution="BYU",
                year=2027,
                notes=[
                    "Consulted Mondelēz: Analyzed Nielsen/Circana data to diagnose business "
                    "challenge and develop brand growth"
                ],
            )
        )
        job_analysis = _job_requiring("business analysis")
        gaps = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())
        item = next(g for g in gaps.items if g.requirement == "business analysis")
        assert item.category in (GapCategory.A, GapCategory.B, GapCategory.C)

    def test_c_executive_communication_from_presenting_to_leadership(self):
        """Test C: 'executive communication' via presenting to C-suite/VP
        leaders -- should score as strong/direct evidence."""
        profile = self._gmdp_style_profile()
        job_analysis = _job_requiring("executive communication")
        gaps = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())
        item = next(g for g in gaps.items if g.requirement == "executive communication")
        assert item.category in (GapCategory.A, GapCategory.B)

    def test_d_cpg_experience_is_partial_not_zero(self):
        """Test D: CPG experience via a consulting project must register
        as evidence (not zero, not full employment)."""
        profile = self._gmdp_style_profile()
        profile.education.append(
            EducationEntry(
                degree="MBA", field="Business", institution="BYU", year=2027,
                notes=["Consulted Mondelēz using Nielsen/Circana data."],
            )
        )
        job_analysis = _job_requiring("CPG experience")
        gaps = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())
        item = next(g for g in gaps.items if g.requirement == "CPG experience")
        assert item.category != GapCategory.E

    def test_e_missing_years_of_experience_remains_an_honest_gap(self):
        """Test E: a hard eligibility requirement with no supporting
        evidence anywhere must still classify as missing -- transferable-
        evidence recognition must never paper over a real gap."""
        profile = self._gmdp_style_profile()
        job_analysis = _job_requiring("4+ years of prior professional experience")
        gaps = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())
        item = next(g for g in gaps.items if g.requirement == "4+ years of prior professional experience")
        assert item.category in (GapCategory.D, GapCategory.E)


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


class TestEvidenceLevelAndHardGate:
    """Steps 10-15 audit Phase C: GapItem.evidence_level and .hard_gate,
    and GapReport.unmet_hard_gates -- run through the real JobAnalyzer so
    the Step 10 -> Step 12 wiring itself is covered, not just the fields
    in isolation."""

    def _profile_missing_everything(self) -> CareerTruthProfile:
        return CareerTruthProfile(
            contact_info={}, education=[],
            work_experience=[
                WorkExperience(
                    employer="Acme", title="Analyst", dates="2023-2024",
                    responsibilities=["Wrote internal memos"], accomplishments=[],
                )
            ],
            skills=[], tools=[], certifications=[], accomplishments=[],
        )

    def _jd(self) -> str:
        return """
        Required Qualifications:
        - 8+ years of enterprise sales experience
        - Strong stakeholder management skills

        Preferred:
        - Prior agency experience
        """

    def test_unmet_hard_gate_surfaces_in_the_rollup(self):
        job_analysis = JobAnalyzer().analyze(self._jd())
        profile = self._profile_missing_everything()
        report = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())

        unmet_texts = [item.requirement for item in report.unmet_hard_gates]
        assert "8+ years of enterprise sales experience" in unmet_texts

    def test_non_hard_gate_requirement_never_appears_in_the_rollup(self):
        job_analysis = JobAnalyzer().analyze(self._jd())
        profile = self._profile_missing_everything()
        report = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())

        unmet_texts = [item.requirement for item in report.unmet_hard_gates]
        assert "Strong stakeholder management skills" not in unmet_texts

    def test_preferred_qualification_is_never_in_the_hard_gate_rollup(self):
        """A Preferred item that's truly missing is Category D, not E --
        unmet_hard_gates only ever contains Category E items."""
        job_analysis = JobAnalyzer().analyze(self._jd())
        profile = self._profile_missing_everything()
        report = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())

        agency_item = next(i for i in report.items if "agency" in i.requirement.lower())
        assert agency_item.category == GapCategory.D
        assert agency_item not in report.unmet_hard_gates

    def test_direct_verified_evidence_gets_the_direct_verified_level(self):
        job_analysis = _job_requiring("Python programming experience")
        profile = CareerTruthProfile(
            contact_info={}, education=[],
            work_experience=[
                WorkExperience(
                    employer="Acme", title="Engineer", dates="2023-2024",
                    responsibilities=["Python programming experience with Django"],
                    accomplishments=[],
                )
            ],
            skills=[], tools=[], certifications=[], accomplishments=[],
        )
        report = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())
        item = next(i for i in report.items if i.requirement == "Python programming experience")
        assert item.evidence_level == EvidenceLevel.DIRECT_VERIFIED

    def test_unsupported_requirement_gets_the_unsupported_level(self):
        job_analysis = _job_requiring("Fluency in Mandarin")
        profile = self._profile_missing_everything()
        report = GapAnalyzer().analyze(profile, job_analysis, _empty_benchmark())
        item = next(i for i in report.items if i.requirement == "Fluency in Mandarin")
        assert item.evidence_level == EvidenceLevel.UNSUPPORTED
        assert item.category == GapCategory.E
