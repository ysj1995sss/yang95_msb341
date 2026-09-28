"""
Final Application Report Generator.

Assembles the outputs of the full pipeline (profile, job analysis, original
benchmark, gap analysis, optimization, and PDF validation) into a single
report dict for display in the Streamlit UI (Task 12).

This module does no scoring or classification of its own — it only reads
and summarizes results already produced upstream. In particular,
`recommendations` are derived strictly from `GapReport` items; nothing is
invented here.
"""

from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmark
from resume_tailorer.analyzers.gap_analyzer import GapReport, GapCategory, find_unsupported_claims
from resume_tailorer.tailorer.optimizer import OptimizationResult
from resume_tailorer.pdf.validator import ValidationResult
from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    FindingCategory,
    FindingSeverity,
    ValidationFinding,
)
from resume_tailorer.artifacts.report import build_final_report


class ReportGenerator:
    """
    Builds the final application report shown to the user after tailoring.

    The Candidate Fit Score (a Sprint 2 feature that scores the candidate's
    overall fit for the role, distinct from resume-text match scoring) is
    not implemented in the MVP. It is reported as `None` with an explicit
    `candidate_fit_score_available: False` flag so the UI can render a
    "coming soon" placeholder instead of a misleading zero or omitted key.
    """

    def generate_report(
        self,
        profile: CareerTruthProfile,
        job_analysis: JobAnalysis,
        benchmark: ResumeBenchmark,
        gap_report: GapReport,
        optimization_result: OptimizationResult,
        pdf_validation: ValidationResult,
    ) -> dict:
        """Assemble the final report dict from all pipeline outputs."""
        original_score = benchmark.original_match_score
        tailored_score = optimization_result.final_score
        score_improvement = tailored_score - original_score

        qualifications_summary = self._build_qualifications_summary(gap_report)
        recommendations = self._build_recommendations(gap_report, optimization_result, pdf_validation)
        unsupported_claims_added = find_unsupported_claims(gap_report, optimization_result.tailored_resume)
        shared_report = build_final_report(
            candidate_fit=None,
            fit_breakdown={},
            original_alignment=original_score,
            tailored_alignment=tailored_score,
            gap_report=gap_report,
            validation=self._as_artifact_validation(pdf_validation),
            role=self._infer_job_title(job_analysis),
            unsupported_claims=unsupported_claims_added,
        )

        return {
            "candidate_name": profile.name,
            "job_title": shared_report.role,
            # Sprint 2 feature — not implemented in MVP.
            "candidate_fit_score": shared_report.candidate_fit,
            "candidate_fit_score_available": False,
            "original_match_score": shared_report.original_alignment,
            # Spec 001 item 19: "unsupported claims added (should always be 0)".
            # A non-empty list here is a real signal to review, not necessarily
            # fabrication -- see find_unsupported_claims's docstring.
            "unsupported_claims_added": list(shared_report.unsupported_claims),
            "tailored_match_score": shared_report.tailored_alignment,
            "score_improvement": score_improvement,
            "optimization_iterations": optimization_result.iterations,
            "optimization_ceiling_reached": optimization_result.ceiling_reached,
            "qualifications_summary": qualifications_summary,
            "gaps_addressed_count": self._count_gaps_addressed(gap_report),
            "total_gaps_count": len(gap_report.items),
            "pdf_validation_passed": pdf_validation.passed,
            "pdf_validation_details": {
                "page_count": pdf_validation.page_count,
                "issues": list(pdf_validation.issues),
            },
            "recommendations": recommendations,
        }

    @staticmethod
    def _as_artifact_validation(pdf_validation: ValidationResult) -> ArtifactValidation:
        findings = [
            ValidationFinding(
                code="LEGACY_PDF_VALIDATION_ISSUE",
                severity=FindingSeverity.FAIL,
                category=FindingCategory.VISUAL,
                message=str(issue),
            )
            for issue in pdf_validation.issues
        ]
        return ArtifactValidation.from_findings(
            findings,
            tailored_page_count=pdf_validation.page_count,
            extracted_text=pdf_validation.extracted_text,
            checks_run=("legacy_pdf_validation",),
        )

    def _infer_job_title(self, job_analysis: JobAnalysis) -> str:
        """Best-effort job title placeholder; JobAnalysis has no title field."""
        return "Target Role"

    def _build_qualifications_summary(self, gap_report: GapReport) -> dict:
        """Group gap items by A-E category, keyed by the category letter."""
        summary = {category.name: [] for category in GapCategory}

        for item in gap_report.items:
            summary[item.category.name].append(
                {
                    "requirement": item.requirement,
                    "reason": item.reason,
                    "candidate_evidence": item.candidate_evidence,
                }
            )

        return summary

    def _count_gaps_addressed(self, gap_report: GapReport) -> int:
        """Count gaps in categories B/C (addressable by tailoring) as a rough signal."""
        return sum(
            1
            for item in gap_report.items
            if item.category in (GapCategory.B, GapCategory.C)
        )

    def _build_recommendations(
        self,
        gap_report: GapReport,
        optimization_result: OptimizationResult,
        pdf_validation: ValidationResult,
    ) -> list[str]:
        """
        Build recommendations grounded strictly in GapReport, OptimizationResult,
        and PDFValidationResult data. Never invents suggestions.
        """
        recommendations: list[str] = []

        # Category D: needs human confirmation.
        needs_confirmation = [item for item in gap_report.items if item.category == GapCategory.D]
        for item in needs_confirmation:
            recommendations.append(
                f"Confirm whether you have experience with \"{item.requirement}\" — "
                f"{item.reason}"
            )

        # Category E: truly missing, flagged for awareness (never to be added).
        truly_missing = [item for item in gap_report.items if item.category == GapCategory.E]
        if truly_missing:
            missing_list = ", ".join(item.requirement for item in truly_missing[:10])
            recommendations.append(
                f"The following requirements are not represented in your profile and were "
                f"not added to the resume: {missing_list}."
            )

        # Optimization ceiling reached without hitting target.
        if optimization_result.ceiling_reached and optimization_result.final_score < 0.85:
            recommendations.append(
                "Tailoring reached a plateau below the 85% alignment target "
                f"(final score: {optimization_result.final_score:.0%}). Remaining gaps may "
                "require adding genuinely new experience to your profile rather than rewording."
            )

        # PDF validation issues.
        if not pdf_validation.passed:
            for issue in pdf_validation.issues:
                recommendations.append(f"PDF validation issue: {issue}")

        return recommendations
