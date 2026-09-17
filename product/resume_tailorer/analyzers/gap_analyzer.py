from dataclasses import dataclass
from enum import Enum
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmark

class GapCategory(Enum):
    """Gap classification per the product vision spec."""
    A = "Already on resume"  # Requirement is on the current resume
    B = "Supported but missing"  # Candidate has experience but not on current resume
    C = "Rephrasable"  # Current resume wording can be adjusted to match JD language
    D = "Needs confirmation"  # System isn't sure; needs human review
    E = "Truly missing"  # Candidate doesn't have this experience; never add

@dataclass
class GapItem:
    """A single gap between resume and job requirement."""
    requirement: str
    category: GapCategory
    reason: str  # Why it was classified this way
    candidate_evidence: str = ""  # What in the resume supports this classification

@dataclass
class GapReport:
    """Full gap analysis."""
    items: list[GapItem]
    summary: str  # High-level summary of gaps

class GapAnalyzer:
    """
    Analyzes gaps between a candidate's profile and job requirements.
    Classifies each gap as A-E per the product spec.
    """

    def analyze(self, profile: CareerTruthProfile, job_analysis: JobAnalysis, benchmark: ResumeBenchmark) -> GapReport:
        """Analyze gaps and return a GapReport."""
        items = []

        # Analyze required qualifications
        for qual in job_analysis.required_qualifications:
            item = self._classify_requirement(qual, profile, job_analysis)
            if item:
                items.append(item)

        # Analyze skills required
        for skill in job_analysis.skills_required:
            item = self._classify_skill(skill, profile, benchmark)
            if item:
                items.append(item)

        # Analyze tools required
        for tool in job_analysis.tools_required:
            item = self._classify_tool(tool, profile, benchmark)
            if item:
                items.append(item)

        # Generate summary
        summary = self._summarize_gaps(items)

        return GapReport(items=items, summary=summary)

    def _classify_requirement(self, requirement: str, profile: CareerTruthProfile, job_analysis: JobAnalysis) -> GapItem:
        """Classify a single requirement."""
        requirement_lower = requirement.lower()

        # Check if already on resume
        for job in profile.work_experience:
            combined = (job.title + " " + " ".join(job.accomplishments)).lower()
            if any(word in combined for word in requirement_lower.split() if len(word) > 3):
                return GapItem(
                    requirement=requirement,
                    category=GapCategory.A,
                    reason="Found in work experience or title",
                    candidate_evidence=job.title,
                )

        # Check if supported by experience but not explicitly mentioned
        if self._has_implicit_experience(requirement, profile):
            return GapItem(
                requirement=requirement,
                category=GapCategory.B,
                reason="Candidate likely has this from background but not explicitly stated",
                candidate_evidence="Based on related experience",
            )

        # Check if could be rephrased
        if self._could_be_rephrased(requirement, profile):
            return GapItem(
                requirement=requirement,
                category=GapCategory.C,
                reason="Current resume content could be rephrased to match JD language",
                candidate_evidence="Needs rewriting to highlight this aspect",
            )

        # If in preferred (not required), mark as D
        if requirement in job_analysis.preferred_qualifications:
            return GapItem(
                requirement=requirement,
                category=GapCategory.D,
                reason="Preferred qualification; system needs confirmation if candidate has this",
                candidate_evidence="Unknown",
            )

        # Otherwise, truly missing
        return GapItem(
            requirement=requirement,
            category=GapCategory.E,
            reason="Not found in profile; do not add",
            candidate_evidence="None",
        )

    def _classify_skill(self, skill: str, profile: CareerTruthProfile, benchmark: ResumeBenchmark) -> GapItem:
        """Classify a skill requirement."""
        skill_lower = skill.lower()

        # Check if in matched keywords
        if skill in benchmark.keywords_matched:
            return GapItem(
                requirement=skill,
                category=GapCategory.A,
                reason="Skill is already on resume",
                candidate_evidence=skill,
            )

        # Check if in profile skills
        if any(s.lower() == skill_lower for s in profile.skills):
            return GapItem(
                requirement=skill,
                category=GapCategory.A,
                reason="Skill is listed in profile",
                candidate_evidence=skill,
            )

        # Check if implied by work experience
        if self._skill_implied_by_work(skill, profile):
            return GapItem(
                requirement=skill,
                category=GapCategory.B,
                reason="Skill is implied by work experience but not explicitly listed",
                candidate_evidence="Inferred from job responsibilities",
            )

        # Truly missing
        return GapItem(
            requirement=skill,
            category=GapCategory.E,
            reason="Skill not found; do not add",
            candidate_evidence="None",
        )

    def _classify_tool(self, tool: str, profile: CareerTruthProfile, benchmark: ResumeBenchmark) -> GapItem:
        """Classify a tool requirement."""
        # Similar logic to skills
        if tool in benchmark.keywords_matched or tool in profile.tools:
            return GapItem(
                requirement=tool,
                category=GapCategory.A,
                reason="Tool is already listed",
                candidate_evidence=tool,
            )

        return GapItem(
            requirement=tool,
            category=GapCategory.E,
            reason="Tool not found; do not add",
            candidate_evidence="None",
        )

    def _has_implicit_experience(self, requirement: str, profile: CareerTruthProfile) -> bool:
        """Check if candidate likely has experience even if not explicitly stated."""
        # For MVP, this is simple; future versions use Claude for nuance
        return False

    def _could_be_rephrased(self, requirement: str, profile: CareerTruthProfile) -> bool:
        """Check if existing resume content could be rephrased to match requirement."""
        # For MVP, return False; Claude does the actual rephrasing
        return False

    def _skill_implied_by_work(self, skill: str, profile: CareerTruthProfile) -> bool:
        """Check if a skill is implied by job responsibilities."""
        skill_lower = skill.lower()
        for job in profile.work_experience:
            for resp in job.responsibilities:
                if skill_lower in resp.lower():
                    return True
        return False

    def _summarize_gaps(self, items: list[GapItem]) -> str:
        """Summarize gaps for the user."""
        a_count = sum(1 for i in items if i.category == GapCategory.A)
        b_count = sum(1 for i in items if i.category == GapCategory.B)
        e_count = sum(1 for i in items if i.category == GapCategory.E)

        return f"Found {a_count} aligned, {b_count} supported but missing, {e_count} truly missing requirements."
