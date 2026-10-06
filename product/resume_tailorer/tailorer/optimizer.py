"""
Resume refinement loop for the free-form path (spec 010).

A bounded loop that works only on job requirements the candidate has confirmed evidence for
but the resume doesn't show yet (the requirement review). It stops when none are left, when a
round changes nothing or shows nothing new, or after `max_iterations` rounds. The keyword
overlap number is still computed and reported, but it is never a target: there is no universal
ATS score to aim for, and chasing one rewards repeating the posting's words over evidence.
"""

import re
from dataclasses import dataclass
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers import JobAnalysis
from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.analyzers.requirement_review import (
    RequirementReview,
    RequirementRow,
    blocked_terms,
    build_review,
    format_for_prompt,
    introduced_unsupported,
    unshown_targets,
)
from resume_tailorer.tailorer.resume_tailorer import ResumeTailorer
from resume_tailorer.utils.scoring import calculate_keyword_alignment, calculate_qualification_alignment
from resume_tailorer.analyzers.competency_map import find_education_status_evidence, find_transferable_evidence


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
    """True if supported requirements were still not shown when the loop stopped."""

    missing_qualifications: list[str]
    """Qualifications/keywords still missing from the final resume."""

    stop_reason: str = ""
    """Why the loop stopped, in plain words."""


class ResumeTailoringOptimizer:
    """
    Bounded refinement for the free-form path (spec 010; replaces spec 001 step 14's 85% target).

    Each round asks the model to make confirmed, evidence-backed requirements clearer. It never
    names a requirement the candidate hasn't shown evidence for, and a round that introduces an
    unsupported term is thrown away.
    """

    def __init__(self, max_iterations: int = 3, llm=None):
        """
        Args:
            max_iterations: The most refinement rounds to run (default 3).
            llm: Optional LLMClient forwarded to ResumeTailorer. When omitted,
                ResumeTailorer resolves settings from the environment.
        """
        self.max_iterations = max_iterations
        self.tailorer = ResumeTailorer(llm=llm) if llm is not None else ResumeTailorer()

    def optimize(
        self,
        profile: CareerTruthProfile,
        job_analysis: JobAnalysis,
        initial_tailored: str,
        gap_report: GapReport,
        conservative: bool = False,
        review: RequirementReview | None = None,
    ) -> OptimizationResult:
        """
        Refine the tailored resume while supported requirements remain unshown.

        Args:
            profile: Career Truth Profile (source of truth for the refinement prompt).
            job_analysis: Job description analysis.
            initial_tailored: Initial tailored resume text.
            gap_report: Kept for callers; the requirement review decides the targets.
            conservative: When True, no refinement rounds run (minimal edits only).
            review: The requirement review. Built from the profile when omitted (untracked
                facts count as the person's own).
        """
        review = review if review is not None else build_review(job_analysis, profile)
        current = initial_tailored
        rounds = 0
        stop_reason = "Conservative mode: no refinement rounds."
        if not conservative:
            stop_reason = f"Stopped after {self.max_iterations} rounds."
            for _ in range(self.max_iterations):
                targets = unshown_targets(review, current)
                if not targets:
                    stop_reason = "Every requirement with confirmed evidence is shown."
                    break
                refined = self.tailorer._refine_resume(
                    current, self._build_improvement_prompt(current, review, targets), profile
                )
                rounds += 1
                if _flat(refined) == _flat(current):
                    stop_reason = "A round changed nothing."
                    break
                if introduced_unsupported(current, refined, review):
                    stop_reason = "A round added something you haven't shown evidence for, so it was discarded."
                    break
                if len(unshown_targets(review, refined)) >= len(targets):
                    stop_reason = "A round showed nothing new, so it was discarded."
                    break
                current = refined

        score, _matched, missing = self._score_resume(current, job_analysis, profile)
        return OptimizationResult(
            tailored_resume=current,
            final_score=score,
            iterations=rounds,
            ceiling_reached=bool(unshown_targets(review, current)),
            missing_qualifications=missing,
            stop_reason=stop_reason,
        )

    @staticmethod
    def _score_resume(
        resume_text: str, job_analysis: JobAnalysis, profile: CareerTruthProfile | None = None
    ) -> tuple[float, list[str], list[str]]:
        """
        Score the resume against job requirements.

        Uses the SAME methodology as ResumeBenchmarker.benchmark() (keyword
        alignment weighted 60%, qualification alignment weighted 40%, top-5
        required qualifications) so that OptimizationResult.final_score is
        directly comparable to ResumeBenchmark.original_match_score.

        Found live (2026-09-23): this previously used ONLY literal-word
        qualification matching, while ResumeBenchmarker.benchmark() had
        since been upgraded to also recognize transferable competency-map
        evidence and in-progress/completed degrees. The two scores were no
        longer comparable -- a resume could score LOWER after tailoring than
        its own untouched original, purely because the original's score used
        a more evidence-aware methodology than the tailored score did. When
        `profile` is provided, qualifications that fail literal matching are
        re-checked the same way ResumeBenchmarker does: competency-map
        transferable evidence (against sentences from the resume text being
        scored, so credit reflects what THIS version of the resume actually
        conveys) and degree/enrollment-status evidence (against the
        profile's own education history, which doesn't change during
        tailoring).

        Args:
            resume_text: The resume text to score
            job_analysis: Job description analysis with requirements
            profile: Source-of-truth profile, used for evidence-aware
                fallback matching when literal matching fails. Optional so
                existing callers/tests that don't have a profile handy still
                work (falling back to literal-only matching).

        Returns:
            Tuple of (score, matched_keywords, missing_keywords)
        """
        all_keywords = job_analysis.skills_required + job_analysis.tools_required
        keyword_score, matched, missing = calculate_keyword_alignment(resume_text, all_keywords)

        qual_score, qual_covered, qual_missing = calculate_qualification_alignment(
            resume_text, job_analysis.required_qualifications[:5]
        )

        if profile is not None and qual_missing:
            resume_sentences = [line.strip() for line in resume_text.splitlines() if line.strip()]
            still_missing = []
            for qual in qual_missing:
                if (
                    find_transferable_evidence(qual, resume_sentences) is not None
                    or find_education_status_evidence(qual, profile) is not None
                ):
                    qual_covered.append(qual)
                else:
                    still_missing.append(qual)
            qual_missing = still_missing
            total = len(job_analysis.required_qualifications[:5])
            qual_score = len(qual_covered) / total if total > 0 else 0.0

        score = (keyword_score * 0.6) + (qual_score * 0.4)
        return score, matched, missing

    def _build_improvement_prompt(
        self,
        current_resume: str,
        review: RequirementReview,
        targets: list[RequirementRow],
    ) -> str:
        """The refinement prompt: the unshown supported requirements with their exact evidence,
        and the requirement review's do-not-add list. Missing requirements are never targets."""
        lines = []
        for row in targets[:5]:
            lines.append(f"- {row.section.upper()}: {row.text}")
            for evidence in row.evidence:
                lines.append(f'  Evidence ({evidence.source}): "{evidence.text}"')
        never, listed = blocked_terms(review)
        do_not = ", ".join([*never, *listed]) or "(none)"
        return f"""Make these job requirements clearer in the resume. The candidate has confirmed evidence
for each one, quoted below; it is not yet clear in the current resume.

{chr(10).join(lines)}

FULL REQUIREMENT REVIEW:
{format_for_prompt(review, current_resume)}

INSTRUCTIONS FOR REFINEMENT:
1. Use only the quoted evidence and the Career Truth Profile. Make terminology, context,
   responsibility or outcome clearer where the evidence supports it.
2. CRITICAL: Do not invent or fabricate any experience, skill, credential, duration, number or result.
3. Never add these terms anywhere new; where one already appears, keep it as it is (never delete a
   true fact): {do_not}
4. Never change dates, employers, titles, or employment types.
5. No hidden text, no keyword lists added to bullets, no repeating a term just to repeat it.
6. If a requirement can't be shown honestly with the evidence, leave it as it is.

Provide the improved resume:"""


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())
