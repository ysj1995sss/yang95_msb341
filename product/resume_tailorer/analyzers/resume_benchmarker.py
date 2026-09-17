from dataclasses import dataclass
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalysis


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
            parts.extend(job.responsibilities)
            parts.extend(job.accomplishments)

        return " ".join(parts).lower()

    def _match_keywords(self, resume_text: str, job_keywords: list[str]) -> tuple[list[str], list[str]]:
        """Find which job keywords are already in the resume."""
        matched = []
        missing = []

        for keyword in job_keywords:
            if keyword.lower() in resume_text:
                matched.append(keyword)
            else:
                missing.append(keyword)

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
        """Check if a qualification is represented in the profile."""
        qual_lower = qualification.lower()

        # Check work experience
        for job in profile.work_experience:
            combined = (job.title + " " + " ".join(job.responsibilities) + " " + " ".join(job.accomplishments)).lower()
            if any(word in combined for word in qual_lower.split() if len(word) > 3):
                return True

        # Check skills
        if any(skill.lower() in qual_lower for skill in profile.skills):
            return True

        return False
