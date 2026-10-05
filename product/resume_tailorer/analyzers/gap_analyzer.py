import re
from dataclasses import dataclass
from enum import Enum
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmark
from resume_tailorer.analyzers.term_match import mentions
from resume_tailorer.analyzers.competency_map import (
    extract_profile_sentences,
    find_education_status_evidence,
    find_transferable_evidence,
)
from resume_tailorer.utils.scoring import (
    _semantic_match_qualification,
    qualification_match_ratio,
)

class GapCategory(Enum):
    """Gap classification per the product vision spec."""
    A = "Already on resume"  # Requirement is on the current resume
    B = "Supported but missing"  # Candidate has experience but not on current resume
    C = "Rephrasable"  # Current resume wording can be adjusted to match JD language
    D = "Needs confirmation"  # System isn't sure; needs human review
    E = "Truly missing"  # Candidate doesn't have this experience; never add

class EvidenceLevel(Enum):
    """
    How strong the underlying evidence is, independent of GapCategory --
    the audit-prompt's 5-tier model. Related to, but not the same axis as,
    category: Category D and E both mean "not on the resume," but D means
    "preferred, no evidence found" and E means "required, no evidence
    found" -- both are UNSUPPORTED here, and the required/preferred
    distinction lives on the category and on JobRequirement.hard_gate,
    not on evidence_level.
    """
    DIRECT_VERIFIED = "Direct verified"
    STRONGLY_SUPPORTED = "Strongly supported"
    TRANSFERABLE_PARTIAL = "Transferable/partial"
    WEAK_INFERRED = "Weak/inferred"
    UNSUPPORTED = "Unsupported"

@dataclass
class GapItem:
    """A single gap between resume and job requirement."""
    requirement: str
    category: GapCategory
    reason: str  # Why it was classified this way
    candidate_evidence: str = ""  # What in the resume supports this classification
    evidence_level: EvidenceLevel = EvidenceLevel.UNSUPPORTED
    hard_gate: bool = False  # True if failing this alone is an honest, un-rewritable gap

@dataclass
class GapReport:
    """Full gap analysis."""
    items: list[GapItem]
    summary: str  # High-level summary of gaps

    @property
    def unmet_hard_gates(self) -> list[GapItem]:
        """Truly-missing items that are also hard eligibility gates (e.g. a
        required years-of-experience threshold) -- the honest, un-rewritable
        gaps a caller should surface distinctly from the general gap list,
        per the audit prompt's 'a missing hard requirement remains an
        honest gap; do not let one hard gap erase every other match'."""
        return [item for item in self.items if item.hard_gate and item.category == GapCategory.E]

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

        # Analyze preferred qualifications. Found live (2026-09-27): this
        # loop didn't exist before -- _classify_requirement has always had
        # a branch for "requirement in job_analysis.preferred_qualifications
        # -> Category D", but nothing ever called it with a preferred-only
        # string (only required_qualifications/skills_required/
        # tools_required were iterated), so Category D was structurally
        # unreachable in normal operation. A preferred item with real
        # evidence still correctly resolves to A/B/C here, same as a
        # required one -- D only fires when truly no evidence is found.
        for qual in job_analysis.preferred_qualifications:
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
        """
        Classify a single requirement.

        Priority order (highest-confidence evidence first): literal/near-
        literal match (A) > competency-map STRONG match (B -- e.g. "on-time
        delivery" + "risk mitigation" strongly demonstrate "project
        management" even though the resume never uses that phrase) >
        partial lexical overlap (C) > competency-map PARTIAL match (C) >
        literal-substring implicit match (B) > preferred-with-no-evidence
        (D) > nothing found (E). Found live (2026-09-23): purely lexical
        matching put almost everything into E for a resume whose real
        bullets clearly demonstrated the requirement, just never in the
        job description's own words -- this is the fix.
        """
        profile_text = self._profile_to_text(profile)
        match_ratio = qualification_match_ratio(profile_text, requirement)
        hard_gate = self._is_hard_gate(requirement, job_analysis)

        education_evidence = find_education_status_evidence(requirement, profile)
        if education_evidence:
            return GapItem(
                requirement=requirement,
                category=GapCategory.A,
                reason="Matches an in-progress or completed degree in the candidate's education history",
                candidate_evidence=education_evidence,
                evidence_level=EvidenceLevel.DIRECT_VERIFIED,
                hard_gate=hard_gate,
            )

        if match_ratio >= 0.7:
            return GapItem(
                requirement=requirement,
                category=GapCategory.A,
                reason="Found in work experience, skills, or title",
                candidate_evidence=self._evidence_snippet(profile, requirement),
                evidence_level=EvidenceLevel.DIRECT_VERIFIED,
                hard_gate=hard_gate,
            )

        transferable = find_transferable_evidence(requirement, extract_profile_sentences(profile))
        if transferable and transferable.level == "strong":
            return GapItem(
                requirement=requirement,
                category=GapCategory.B,
                reason=(
                    f"Strongly supported by verified actions demonstrating "
                    f"'{transferable.competency}', even though the resume doesn't use that exact phrase"
                ),
                candidate_evidence=transferable.evidence_text,
                evidence_level=EvidenceLevel.STRONGLY_SUPPORTED,
                hard_gate=hard_gate,
            )

        if 0.4 <= match_ratio < 0.7:
            return GapItem(
                requirement=requirement,
                category=GapCategory.C,
                reason="Current resume content could be rephrased to match JD language",
                candidate_evidence=self._evidence_snippet(profile, requirement),
                evidence_level=EvidenceLevel.TRANSFERABLE_PARTIAL,
                hard_gate=hard_gate,
            )

        if transferable:  # partial-level match
            return GapItem(
                requirement=requirement,
                category=GapCategory.C,
                reason=(
                    f"Transferable/partial evidence for '{transferable.competency}' -- "
                    "existing wording can be adjusted to surface this, not invented"
                ),
                candidate_evidence=transferable.evidence_text,
                evidence_level=EvidenceLevel.TRANSFERABLE_PARTIAL,
                hard_gate=hard_gate,
            )

        if self._has_implicit_experience(requirement, profile):
            return GapItem(
                requirement=requirement,
                category=GapCategory.B,
                reason="Candidate likely has this from background but not explicitly stated",
                candidate_evidence="Based on related experience",
                evidence_level=EvidenceLevel.WEAK_INFERRED,
                hard_gate=hard_gate,
            )

        if requirement in job_analysis.preferred_qualifications:
            return GapItem(
                requirement=requirement,
                category=GapCategory.D,
                reason="Preferred qualification; system needs confirmation if candidate has this",
                candidate_evidence="Unknown",
                evidence_level=EvidenceLevel.UNSUPPORTED,
                hard_gate=False,  # a preferred item is never a hard gate by definition
            )

        return GapItem(
            requirement=requirement,
            category=GapCategory.E,
            reason="Not found in profile; do not add",
            candidate_evidence="None",
            evidence_level=EvidenceLevel.UNSUPPORTED,
            hard_gate=hard_gate,
        )

    @staticmethod
    def _is_hard_gate(requirement: str, job_analysis: JobAnalysis) -> bool:
        """Look up whether this requirement was flagged as a hard
        eligibility gate during Step 10 extraction (JobAnalyzer). Matched
        by exact text since structured_requirements is built directly from
        the same required_qualifications/preferred_qualifications strings
        this method receives."""
        return any(
            r.text == requirement and r.hard_gate
            for r in job_analysis.structured_requirements
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

        # Competency-map transferable evidence (same logic as
        # _classify_requirement -- a standalone skill token like "Project
        # Management" deserves the same evidence-based treatment as a full
        # requirement sentence, not just a literal-substring check).
        transferable = find_transferable_evidence(skill, extract_profile_sentences(profile))
        if transferable:
            category = GapCategory.B if transferable.level == "strong" else GapCategory.C
            return GapItem(
                requirement=skill,
                category=category,
                reason=(
                    f"{'Strongly supported' if transferable.level == 'strong' else 'Transferable/partial evidence'} "
                    f"by verified actions demonstrating '{transferable.competency}'"
                ),
                candidate_evidence=transferable.evidence_text,
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
        """Category B: distinctive words appear in responsibilities but not as a listed skill."""
        return self._skill_implied_by_work(requirement, profile)

    def _could_be_rephrased(self, requirement: str, profile: CareerTruthProfile) -> bool:
        """Partial distinctive-word overlap means wording can be tightened, not invented."""
        ratio = qualification_match_ratio(self._profile_to_text(profile), requirement)
        return 0.4 <= ratio < 0.7

    def _profile_to_text(self, profile: CareerTruthProfile) -> str:
        parts = []
        parts.extend(profile.skills)
        parts.extend(profile.tools)
        parts.extend(profile.certifications)
        parts.extend(profile.accomplishments)
        for job in profile.work_experience:
            parts.append(job.title)
            parts.append(job.employer)
            parts.append(job.dates)
            parts.extend(job.responsibilities)
            parts.extend(job.accomplishments)
        # Education/consulting-project evidence participates in matching
        # too (found live, 2026-09-23: a Mondelez/Nielsen-Circana
        # consulting project, stored as an EducationEntry note rather than
        # a work_experience bullet, is real CPG/business-analysis evidence
        # that was previously invisible to gap classification entirely).
        # The degree/institution/year fields themselves were ALSO missing
        # here (only `.notes` was included) -- a real gap found live on
        # the same test: a requirement naming "MBA" and "2027" scored as
        # completely unsupported despite the profile literally having an
        # MBA with a 2027 graduation year, just never in a `.notes` string.
        for edu in profile.education:
            parts.append(edu.degree)
            parts.append(edu.field)
            parts.append(edu.institution)
            parts.append(str(edu.year))
            parts.extend(edu.notes)
        if profile.summary:
            parts.append(profile.summary)
        return " ".join(parts)

    def _evidence_snippet(self, profile: CareerTruthProfile, requirement: str) -> str:
        for job in profile.work_experience:
            blob = " ".join([job.title, *job.responsibilities, *job.accomplishments])
            if _semantic_match_qualification(blob, requirement) or qualification_match_ratio(blob, requirement) >= 0.4:
                return job.title
        return "profile"

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


def find_unsupported_claims(gap_report: GapReport, tailored_text: str) -> list[str]:
    """
    Check whether any Category E ("truly missing -- never add") requirement now
    appears to be represented in the final tailored resume text.

    The LLM's system prompt says "GAPS TO IGNORE: Category E - NEVER add", but
    prompt compliance isn't guaranteed (observed live, 2026-09-21: the model
    added "CI/CD" despite it being flagged Category E). This reuses the exact
    matching logic gap_analyzer used to originally classify the requirement as
    missing, applied to the OUTPUT instead of the original profile -- so
    "unsupported claim added" means "the same logic that said this was
    missing now says it's present." This is the spec's own required metric
    (spec 001, item 19: "unsupported claims added -- should always be 0").

    A hit here does not necessarily mean fabrication -- it can also mean the
    E classification was itself a false negative (a real skill described
    with different wording than the matcher recognized). Either way, it's a
    claim in the output that the system could not itself verify, and belongs
    in front of the user for review, not silently accepted.
    """
    tailored_lower = tailored_text.lower()
    unsupported = []
    for item in gap_report.items:
        if item.category != GapCategory.E:
            continue
        req_lower = item.requirement.lower()
        if len(req_lower.split()) <= 2:
            if mentions(item.requirement, tailored_text):
                unsupported.append(item.requirement)
        elif qualification_match_ratio(tailored_lower, item.requirement) >= 0.7:
            unsupported.append(item.requirement)
    return unsupported
