"""
Resume Tailoring Optimization Loop.

This module provides an iterative optimization loop that tailors a resume,
scores it, and iteratively refines it to reach an 85% alignment target
(or identifies when a ceiling has been reached).
"""

from dataclasses import dataclass
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers import JobAnalysis
from resume_tailorer.tailorer.resume_tailorer import ResumeTailorer
from resume_tailorer.utils.scoring import calculate_keyword_alignment


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

    def __init__(self, max_iterations: int = 5):
        """
        Initialize the optimizer.

        Args:
            max_iterations: Maximum number of refinement iterations (default: 5)
        """
        self.max_iterations = max_iterations
        self.target_score = 0.85  # 85% alignment target
        self.tailorer = ResumeTailorer()

    def optimize(
        self,
        profile: CareerTruthProfile,
        job_analysis: JobAnalysis,
        initial_tailored: str,
    ) -> OptimizationResult:
        """
        Optimize the tailored resume iteratively.

        Args:
            profile: Career Truth Profile (used for context)
            job_analysis: Job description analysis
            initial_tailored: Initial tailored resume text

        Returns:
            OptimizationResult with final resume, score, iterations, and status
        """
        current_tailored = initial_tailored
        previous_score = 0.0

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

            # Improve: identify gaps and ask Claude to refine
            improvement_prompt = self._build_improvement_prompt(
                current_tailored, job_analysis, missing
            )
            current_tailored = self.tailorer._refine_resume(
                current_tailored, improvement_prompt
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

        Args:
            resume_text: The resume text to score
            job_analysis: Job description analysis with requirements

        Returns:
            Tuple of (score, matched_keywords, missing_keywords)
        """
        all_keywords = job_analysis.skills_required + job_analysis.tools_required
        score, matched, missing = calculate_keyword_alignment(resume_text, all_keywords)
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
