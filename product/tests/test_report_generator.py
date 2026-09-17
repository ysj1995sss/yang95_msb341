"""
Tests for the Final Report Generator.

Verifies that generate_report() assembles a dict with the expected keys and
correct score values from sample instances of all 6 consumed types, and that
recommendations are grounded in real GapReport/OptimizationResult/
ValidationResult data (no fabrication).
"""

import pytest

from resume_tailorer.models import CareerTruthProfile, WorkExperience, EducationEntry
from resume_tailorer.analyzers.job_analyzer import JobAnalysis, WeightedKeyword
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmark
from resume_tailorer.analyzers.gap_analyzer import GapReport, GapItem, GapCategory
from resume_tailorer.tailorer.optimizer import OptimizationResult
from resume_tailorer.pdf.validator import ValidationResult
from resume_tailorer.report_generator import ReportGenerator


@pytest.fixture
def profile():
    return CareerTruthProfile(
        contact_info={"name": "Jane Doe", "email": "jane@example.com", "phone": "555-1234", "location": "NYC"},
        education=[EducationEntry(degree="BS", field="Computer Science", institution="MIT", year=2018)],
        work_experience=[
            WorkExperience(
                employer="Acme Corp",
                title="Software Engineer",
                dates="2018-2023",
                responsibilities=["Built APIs", "Maintained services"],
                accomplishments=["Reduced latency by 30%"],
            )
        ],
        skills=["Python", "SQL"],
        tools=["Docker"],
        certifications=[],
        accomplishments=["Led migration project"],
    )


@pytest.fixture
def job_analysis():
    return JobAnalysis(
        required_qualifications=["5+ years experience", "Kubernetes"],
        preferred_qualifications=["AWS certification"],
        responsibilities=["Design systems"],
        skills_required=["Python", "Kubernetes"],
        tools_required=["Docker", "Terraform"],
        education_required="BS in Computer Science",
        experience_required="5+ years",
        weighted_keywords=[WeightedKeyword(keyword="python", weight="high", frequency=3)],
    )


@pytest.fixture
def benchmark():
    return ResumeBenchmark(
        original_match_score=0.55,
        keywords_matched=["Python", "Docker"],
        keywords_missing=["Kubernetes", "Terraform"],
        qualifications_covered=["5+ years experience"],
        qualifications_missing=["Kubernetes"],
    )


@pytest.fixture
def gap_report():
    return GapReport(
        items=[
            GapItem(requirement="Python", category=GapCategory.A, reason="Found in work experience", candidate_evidence="Software Engineer"),
            GapItem(requirement="Docker", category=GapCategory.B, reason="Implied by work but not stated", candidate_evidence="Based on related experience"),
            GapItem(requirement="CI/CD pipelines", category=GapCategory.C, reason="Could be rephrased", candidate_evidence="Needs rewriting"),
            GapItem(requirement="AWS certification", category=GapCategory.D, reason="Preferred qualification; needs confirmation", candidate_evidence="Unknown"),
            GapItem(requirement="Kubernetes", category=GapCategory.E, reason="Not found in profile; do not add", candidate_evidence="None"),
        ],
        summary="Found 1 aligned, 1 supported but missing, 1 truly missing requirements.",
    )


@pytest.fixture
def optimization_result():
    return OptimizationResult(
        tailored_resume="Jane Doe\nSoftware Engineer...",
        final_score=0.82,
        iterations=3,
        ceiling_reached=True,
        missing_qualifications=["Kubernetes"],
    )


@pytest.fixture
def pdf_validation_passed():
    return ValidationResult(passed=True, page_count=1, extracted_text="Jane Doe...", issues=[])


@pytest.fixture
def pdf_validation_failed():
    return ValidationResult(passed=False, page_count=3, extracted_text="", issues=["PDF has 3 pages, exceeding the MVP target of 2 page(s)."])


class TestReportGenerator:
    def test_report_has_expected_keys(
        self, profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
    ):
        report = ReportGenerator().generate_report(
            profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
        )

        expected_keys = {
            "candidate_name",
            "job_title",
            "candidate_fit_score",
            "candidate_fit_score_available",
            "original_match_score",
            "tailored_match_score",
            "score_improvement",
            "optimization_iterations",
            "optimization_ceiling_reached",
            "qualifications_summary",
            "gaps_addressed_count",
            "total_gaps_count",
            "pdf_validation_passed",
            "pdf_validation_details",
            "recommendations",
        }
        assert expected_keys.issubset(report.keys())

    def test_candidate_fit_score_is_placeholder(
        self, profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
    ):
        report = ReportGenerator().generate_report(
            profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
        )
        assert report["candidate_fit_score"] is None
        assert report["candidate_fit_score_available"] is False

    def test_scores_match_inputs(
        self, profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
    ):
        report = ReportGenerator().generate_report(
            profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
        )
        assert report["original_match_score"] == benchmark.original_match_score
        assert report["tailored_match_score"] == optimization_result.final_score
        assert report["score_improvement"] == pytest.approx(
            optimization_result.final_score - benchmark.original_match_score
        )
        assert report["optimization_iterations"] == optimization_result.iterations
        assert report["optimization_ceiling_reached"] == optimization_result.ceiling_reached

    def test_qualifications_summary_groups_by_category(
        self, profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
    ):
        report = ReportGenerator().generate_report(
            profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
        )
        summary = report["qualifications_summary"]
        assert set(summary.keys()) == {"A", "B", "C", "D", "E"}
        assert len(summary["A"]) == 1
        assert summary["A"][0]["requirement"] == "Python"
        assert len(summary["B"]) == 1
        assert len(summary["C"]) == 1
        assert len(summary["D"]) == 1
        assert len(summary["E"]) == 1
        assert report["total_gaps_count"] == len(gap_report.items)
        # B + C are the "addressed by tailoring" categories.
        assert report["gaps_addressed_count"] == 2

    def test_pdf_validation_passed_included(
        self, profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
    ):
        report = ReportGenerator().generate_report(
            profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
        )
        assert report["pdf_validation_passed"] is True
        assert report["pdf_validation_details"]["page_count"] == 1
        assert report["pdf_validation_details"]["issues"] == []

    def test_pdf_validation_failed_surfaces_issues_in_recommendations(
        self, profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_failed
    ):
        report = ReportGenerator().generate_report(
            profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_failed
        )
        assert report["pdf_validation_passed"] is False
        assert any(
            "PDF has 3 pages" in rec for rec in report["recommendations"]
        )

    def test_recommendations_grounded_in_category_d_gaps(
        self, profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
    ):
        report = ReportGenerator().generate_report(
            profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
        )
        # The D-category item (AWS certification) must generate a confirmation recommendation.
        assert any("AWS certification" in rec for rec in report["recommendations"])

    def test_recommendations_mention_truly_missing_but_not_fabricated(
        self, profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
    ):
        report = ReportGenerator().generate_report(
            profile, job_analysis, benchmark, gap_report, optimization_result, pdf_validation_passed
        )
        # Kubernetes (category E) should be mentioned as not added, not recommended as added.
        missing_recs = [r for r in report["recommendations"] if "Kubernetes" in r]
        assert len(missing_recs) == 1
        assert "not added" in missing_recs[0] or "not represented" in missing_recs[0]

    def test_no_recommendations_invented_beyond_gap_data(
        self, profile, job_analysis, benchmark, optimization_result, pdf_validation_passed
    ):
        # Empty gap report + target score reached + passing PDF => no recommendations.
        empty_gap_report = GapReport(items=[], summary="No gaps found.")
        good_optimization = OptimizationResult(
            tailored_resume="text",
            final_score=0.9,
            iterations=1,
            ceiling_reached=False,
            missing_qualifications=[],
        )
        report = ReportGenerator().generate_report(
            profile, job_analysis, benchmark, empty_gap_report, good_optimization, pdf_validation_passed
        )
        assert report["recommendations"] == []
