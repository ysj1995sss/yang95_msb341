from dataclasses import dataclass
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.competency_map import (
    extract_profile_sentences,
    find_education_status_evidence,
    find_transferable_evidence,
)
from resume_tailorer.utils.scoring import calculate_keyword_alignment, _semantic_match_qualification


@dataclass
class ResumeBenchmark:
    """Score of the original resume against a job description."""
    original_match_score: float  # 0-1.0
    keywords_matched: list[str]
    keywords_missing: list[str]
    qualifications_covered: list[str]
    qualifications_missing: list[str]


class ResumeBenchmarker:
    """
    Benchmarks an original resume against job requirements.
    Produces a match score distinct from Candidate Fit Score.
    """

    def benchmark(self, profile: CareerTruthProfile, job_analysis: JobAnalysis) -> ResumeBenchmark:
        """Score how well the original resume represents the candidate for a job."""
        # Combine all resume content into one searchable text
        resume_text = self._profile_to_text(profile)

        # Calculate keyword match
        keywords_matched, keywords_missing = self._match_keywords(resume_text, job_analysis.skills_required + job_analysis.tools_required)

        # Calculate qualifications match
        qualifications_covered, qualifications_missing = self._match_qualifications(profile, job_analysis)

        # Overall score
        keyword_score = len(keywords_matched) / max(1, len(keywords_matched) + len(keywords_missing))
        qual_score = len(qualifications_covered) / max(1, len(qualifications_covered) + len(qualifications_missing))

        overall_score = (keyword_score * 0.6 + qual_score * 0.4)  # Weight keywords more heavily

        return ResumeBenchmark(
            original_match_score=overall_score,
            keywords_matched=keywords_matched,
            keywords_missing=keywords_missing,
            qualifications_covered=qualifications_covered,
            qualifications_missing=qualifications_missing,
        )

    def _profile_to_text(self, profile: CareerTruthProfile) -> str:
        """Convert profile to searchable text."""
        parts = []
        parts.extend(profile.skills)
        parts.extend(profile.tools)
        parts.extend(profile.certifications)

        for job in profile.work_experience:
            parts.append(job.title)
            parts.append(job.dates)
            parts.extend(job.responsibilities)
            parts.extend(job.accomplishments)

        # Education/consulting-project evidence participates in the
        # baseline score too (found live, 2026-09-23: a Mondelez/Nielsen-
        # Circana consulting project stored as an EducationEntry note was
        # invisible to benchmarking entirely, even though it's real CPG/
        # business-analysis evidence). The degree/institution/year fields
        # themselves were ALSO missing -- a requirement naming "MBA" and
        # "2027" scored as completely unsupported despite the profile
        # literally having an MBA graduating 2027, just never in `.notes`.
        for edu in profile.education:
            parts.append(edu.degree)
            parts.append(edu.field)
            parts.append(edu.institution)
            parts.append(str(edu.year))
            parts.extend(edu.notes)
        if profile.summary:
            parts.append(profile.summary)

        return " ".join(parts).lower()

    def _match_keywords(self, resume_text: str, job_keywords: list[str]) -> tuple[list[str], list[str]]:
        """Find which job keywords are already in the resume.

        Uses calculate_keyword_alignment's word-boundary regex matching
        (rather than bare substring matching) so that, e.g., a job requiring
        "Go" does not falsely match inside a resume mentioning "Django".
        """
        _, matched, missing = calculate_keyword_alignment(resume_text, job_keywords)
        return matched, missing

    def _match_qualifications(self, profile: CareerTruthProfile, job_analysis: JobAnalysis) -> tuple[list[str], list[str]]:
        """Check which job qualifications the candidate has."""
        covered = []
        missing = []

        # Check if required qualifications are represented
        for qual in job_analysis.required_qualifications[:5]:  # Check top 5
            if self._has_qualification(profile, qual):
                covered.append(qual)
            else:
                missing.append(qual)

        return covered, missing

    def _has_qualification(self, profile: CareerTruthProfile, qualification: str) -> bool:
        """
        Check if a qualification is represented in the profile.

        Also consults the curated competency map so the baseline score
        reflects transferable evidence (e.g. "on-time delivery" + "risk
        mitigation" demonstrating "project management") instead of only
        literal word overlap -- found live (2026-09-23): a resume with
        substantial real evidence scored a baseline as low as 12% purely
        because the job description's own phrasing never appeared verbatim.
        """
        if _semantic_match_qualification(self._profile_to_text(profile), qualification):
            return True
        if find_transferable_evidence(qualification, extract_profile_sentences(profile)) is not None:
            return True
        return find_education_status_evidence(qualification, profile) is not None
