"""
Resume Tailoring Optimization Loop.

This module provides an iterative optimization loop that tailors a resume,
scores it, and iteratively refines it to reach an 85% alignment target
(or identifies when a ceiling has been reached).
"""

from dataclasses import dataclass
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers import JobAnalysis
from resume_tailorer.analyzers.gap_analyzer import GapReport, GapCategory
from resume_tailorer.tailorer.resume_tailorer import ResumeTailorer
from resume_tailorer.utils.scoring import calculate_keyword_alignment, calculate_qualification_alignment


@dataclass
class OptimizationResult:
    """Result of the optimization loop."""

    tailored_resume: str
    """The final tailored resume after optimization."""

    final_score: float
    """Final keyword/qualification alignment score (0-1.0)."""

    iterations: int
    """Number of iterations performed."""

    ceiling_reached: bool
    """True if the optimization hit a plateau (< 2% improvement) before reaching target."""

    missing_qualifications: list[str]
    """Qualifications/keywords still missing from the final resume."""


class ResumeTailoringOptimizer:
    """
    Iterative optimizer for resume tailoring.

    Runs a loop: tailor → score → improve, continuing until reaching
    ≥85% alignment or detecting no further improvement is possible.

    The optimizer respects the Career Truth Profile constraint: it ONLY
    refines existing content, never fabricates.
    """

    def __init__(self, max_iterations: int = 5, llm=None):
        """
        Initialize the optimizer.

        Args:
            max_iterations: Maximum number of refinement iterations (default: 5)
            llm: Optional LLMClient forwarded to ResumeTailorer. When omitted,
                ResumeTailorer resolves settings from the environment.
        """
        self.max_iterations = max_iterations
        self.target_score = 0.85  # 85% alignment target
        self.tailorer = ResumeTailorer(llm=llm) if llm is not None else ResumeTailorer()

    def optimize(
        self,
        profile: CareerTruthProfile,
        job_analysis: JobAnalysis,
        initial_tailored: str,
        gap_report: GapReport,
        conservative: bool = False,
    ) -> OptimizationResult:
        """
        Optimize the tailored resume iteratively.

        Args:
            profile: Career Truth Profile (source of truth passed through to
                the refinement prompt so it has the same guardrail scope as
                the initial tailor() call)
            job_analysis: Job description analysis
            initial_tailored: Initial tailored resume text
            gap_report: Gap analysis classifying each requirement A-E. Used
                to exclude Category D ("needs confirmation") and Category E
                ("truly missing / never add") items from the "missing
                keywords to address" list handed to the refinement prompt,
                so the optimizer never asks Claude to "better address"
                something the candidate doesn't actually have.
            conservative: When True, skip the iterative refinement loop
                entirely and score the single conservative tailor() pass
                as-is. Refinement's whole purpose is to reorganize/rephrase
                for alignment, which is exactly what conservative mode
                (minimal keyword-only edits) is meant to avoid.

        Returns:
            OptimizationResult with final resume, score, iterations, and status
        """
        if conservative:
            score, matched, missing = self._score_resume(initial_tailored, job_analysis)
            return OptimizationResult(
                tailored_resume=initial_tailored,
                final_score=score,
                iterations=1,
                ceiling_reached=False,
                missing_qualifications=missing,
            )

        current_tailored = initial_tailored
        previous_score = 0.0

        # Requirements the candidate truly doesn't have (E) or that need
        # human confirmation (D) must never be surfaced as improvement
        # targets -- doing so would push the refinement prompt toward
        # fabrication.
        excluded_keywords = {
            item.requirement.lower()
            for item in gap_report.items
            if item.category in (GapCategory.D, GapCategory.E)
        }

        for iteration in range(self.max_iterations):
            # Score current version
            score, matched, missing = self._score_resume(current_tailored, job_analysis)

            # Check if target reached
            if score >= self.target_score:
                return OptimizationResult(
                    tailored_resume=current_tailored,
                    final_score=score,
                    iterations=iteration + 1,
                    ceiling_reached=False,
                    missing_qualifications=missing,
                )

            # Check if no improvement possible (< 2% improvement)
            if iteration > 0 and abs(score - previous_score) < 0.02:
                return OptimizationResult(
                    tailored_resume=current_tailored,
                    final_score=score,
                    iterations=iteration,
                    ceiling_reached=True,
                    missing_qualifications=missing,
                )

            previous_score = score

            # Improve: identify gaps and ask Claude to refine, excluding
            # anything classified as Category D/E in the gap report.
            addressable_missing = [
                keyword for keyword in missing if keyword.lower() not in excluded_keywords
            ]
            improvement_prompt = self._build_improvement_prompt(
                current_tailored, job_analysis, addressable_missing
            )
            current_tailored = self.tailorer._refine_resume(
                current_tailored, improvement_prompt, profile
            )

        # Max iterations reached
        final_score, matched, missing = self._score_resume(current_tailored, job_analysis)
        return OptimizationResult(
            tailored_resume=current_tailored,
            final_score=final_score,
            iterations=self.max_iterations,
            ceiling_reached=True,
            missing_qualifications=missing,
        )

    def _score_resume(
        self, resume_text: str, job_analysis: JobAnalysis
    ) -> tuple[float, list[str], list[str]]:
        """
        Score the resume against job requirements.

        Uses the SAME methodology as ResumeBenchmarker.benchmark() (keyword
        alignment weighted 60%, qualification alignment weighted 40%, top-5
        required qualifications) so that OptimizationResult.final_score is
        directly comparable to ResumeBenchmark.original_match_score.

        Args:
            resume_text: The resume text to score
            job_analysis: Job description analysis with requirements

        Returns:
            Tuple of (score, matched_keywords, missing_keywords)
        """
        all_keywords = job_analysis.skills_required + job_analysis.tools_required
        keyword_score, matched, missing = calculate_keyword_alignment(resume_text, all_keywords)

        qual_score, _covered, _missing_quals = calculate_qualification_alignment(
            resume_text, job_analysis.required_qualifications[:5]
        )

        score = (keyword_score * 0.6) + (qual_score * 0.4)
        return score, matched, missing

    def _build_improvement_prompt(
        self,
        current_resume: str,
        job_analysis: JobAnalysis,
        missing_keywords: list[str],
    ) -> str:
        """
        Build a prompt asking Claude to improve the resume.

        Args:
            current_resume: Current resume version
            job_analysis: Job analysis with requirements
            missing_keywords: Keywords not yet in the resume

        Returns:
            Formatted improvement prompt
        """
        # Only show top 5 missing keywords to focus the refinement
        top_missing = missing_keywords[:5]

        return f"""The current resume needs improvement to better align with the job requirements.

CURRENT MISSING KEYWORDS: {', '.join(top_missing)}

JOB REQUIREMENTS:
Skills: {', '.join(job_analysis.skills_required[:10])}
Tools: {', '.join(job_analysis.tools_required[:10])}

INSTRUCTIONS FOR REFINEMENT:
1. Identify opportunities to reorganize and rephrase existing experience to better match the job requirements
2. Highlight relevant skills and accomplishments that are present but not prominent
3. Reorganize bullet points to emphasize job-relevant experience
4. CRITICAL: Do not invent or fabricate any experience, skills, or accomplishments
5. Only rephrase and reorganize what is already in the resume
6. Never change dates, employers, titles, or employment types
7. Focus on better addressing the missing keywords using existing content

Provide an improved version of the resume that better highlights alignment with these requirements:"""
