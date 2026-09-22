"""
Resume Tailoring Engine using LLM provider via LLMClient.

This module provides the ResumeTailorer class, which uses an LLM to rewrite
resume content to match job requirements while strictly adhering to the
Career Truth Profile (no fabrication).

Core Rule: Optimize presentation, never manufacture qualifications.
Every rewrite must cite the Career Truth Profile only.
"""

import re

from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.gap_analyzer import GapReport, GapCategory
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.llm.settings import LLMSettings, resolve_settings

# Live testing (2026-09-21, DeepSeek-v4-flash-Free) showed the model ignoring
# "output ONLY the resume content" and appending a trailing "NOTES:" section
# explaining its reasoning. That commentary would get baked straight into the
# generated PDF. The prompt is tightened below, but LLMs don't reliably follow
# format instructions, so this is a defense-in-depth cleanup applied to every
# tailor/refine call regardless of prompt compliance.
_COMMENTARY_HEADER_WORDS = {"NOTE", "NOTES", "EXPLANATION", "SUMMARYOFCHANGES", "REASONING", "DISCLAIMER"}
_PREAMBLE_LINE = re.compile(
    r"^\s*(here('?s| is)|below is|i('ve| have)\s+(tailored|revised|updated|refined))\b.*?:?\s*$",
    re.IGNORECASE,
)
_DIVIDER_LINE = re.compile(r"^\s*(-{3,}|_{3,}|\*{3,})\s*$")


def _is_commentary_header(line: str) -> bool:
    """Match a line like "NOTES:", "**Notes**", "**NOTES:**" regardless of
    where markdown bold markers or the colon land."""
    normalized = re.sub(r"[*:\s]", "", line).upper()
    return normalized in _COMMENTARY_HEADER_WORDS


def _strip_non_resume_content(text: str) -> str:
    """Strip a leading conversational preamble and a trailing commentary
    section (e.g. a "NOTES:" block, optionally after a divider line) from
    LLM output, without touching the resume content in between."""
    lines = text.strip("\n").split("\n")

    while lines and (not lines[0].strip() or _PREAMBLE_LINE.match(lines[0])):
        lines.pop(0)

    for i, line in enumerate(lines):
        if _DIVIDER_LINE.match(line):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and _is_commentary_header(lines[j]):
                lines = lines[:i]
                break
        elif _is_commentary_header(line):
            lines = lines[:i]
            break

    return "\n".join(lines).strip()


class ResumeTailorer:
    """
    LLM-powered resume tailoring engine.

    Rewrites resume content to match job requirements while strictly adhering
    to the Career Truth Profile. This is the MOST safety-critical component:
    the system prompt IS the fabrication guardrail.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        settings: LLMSettings | None = None,
    ):
        """Initialize the ResumeTailorer with an LLMClient.

        Args:
            llm: Optional pre-built LLMClient. If given, used directly.
            settings: Optional LLMSettings. Used to build LLMClient when llm
                is not provided. If neither is given, resolves from env.
        """
        if llm is not None:
            self.llm = llm
        elif settings is not None:
            self.llm = LLMClient(settings)
        else:
            self.llm = LLMClient(resolve_settings())

    def tailor(
        self,
        profile: CareerTruthProfile,
        job_analysis: JobAnalysis,
        gap_report: GapReport,
    ) -> str:
        """
        Tailor resume content to match job requirements.

        Args:
            profile: The Career Truth Profile (the only source of truth)
            job_analysis: Parsed job description with requirements
            gap_report: Gap analysis classifying each requirement A-E

        Returns:
            Tailored resume text (string)

        This method calls the LLM via LLMClient with strict constraints to ensure:
        - No fabrication of experience, skills, certifications, numbers, dates, or employers
        - Only rephrase, reorganize, prioritize existing experience
        - Respect gap categories: fill A/B/C, ignore D/E
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(profile, job_analysis, gap_report)
        raw = self.llm.complete(system_prompt, user_prompt, max_tokens=2000)
        return _strip_non_resume_content(raw)

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt that constrains Claude to Career Truth Profile only.

        This is CRITICAL: the system prompt IS the fabrication guardrail.
        It must explicitly forbid adding experience, skills, certifications,
        numbers, dates, or employers not in the Career Truth Profile.
        """
        return """You are a professional resume tailoring specialist.

YOUR CORE CONSTRAINT - CRITICAL FOR SAFETY:
You may ONLY rewrite resume content using information from the Career Truth Profile provided.
You must NEVER fabricate, invent, or add:
- Experience not in the profile
- Skills not listed in the profile
- Certifications not in the profile
- Numbers, metrics, or accomplishments not explicitly stated
- Dates, employers, titles, or employment types not in the profile

ALLOWED TRANSFORMATIONS:
- Rephrase existing bullets to use job description language
- Reorganize sections to prioritize job-relevant experience
- Shorten or expand existing accomplishments (but never add new achievements)
- Change bullet structure or layout while preserving the facts
- Highlight existing skills in more prominent positions

FORBIDDEN TRANSFORMATIONS:
- Adding new experience
- Inventing metrics or achievements
- Changing dates, employers, titles
- Adding skills or tools not in the profile
- Exaggerating or misrepresenting experience

You will be shown:
1. The Career Truth Profile (source of all truth)
2. Job requirements and skills needed
3. Gap report showing which requirements are already on resume (A), supported but missing (B), rephrasable (C), need confirmation (D), or truly missing (E)

GAPS TO FILL:
- Category A (Already on resume): Optimize presentation
- Category B (Supported but missing): Bring into resume using profile evidence
- Category C (Rephrasable): Rewrite to match job language

GAPS TO IGNORE:
- Category D (Needs confirmation): Do not add; mark for user review
- Category E (Truly missing): NEVER add; these are gaps the candidate doesn't have

OUTPUT FORMAT - CRITICAL:
Output ONLY the resume content itself: contact info, section headings, and bullet points.
Do NOT include any notes, explanations, meta-commentary, reasoning, disclaimers, or a
summary of what you changed or what's missing. If a requirement is missing or uncertain,
silently omit it from the output -- do not mention it there.

Your output must be a revised resume that increases alignment with the job while maintaining 100% truthfulness to the Career Truth Profile."""

    def _build_user_prompt(
        self,
        profile: CareerTruthProfile,
        job_analysis: JobAnalysis,
        gap_report: GapReport,
    ) -> str:
        """
        Build the user prompt requesting tailored resume.

        Args:
            profile: Career Truth Profile
            job_analysis: Parsed job requirements
            gap_report: Gap analysis results

        Returns:
            Formatted user prompt for Claude
        """
        profile_str = self._profile_to_string(profile)
        gaps_str = self._format_gaps(gap_report)
        job_requirements = self._format_job_requirements(job_analysis)

        return f"""Please tailor the following resume to match the job requirements below.

CAREER TRUTH PROFILE (Source of all truth - do NOT add anything beyond this):
{profile_str}

JOB REQUIREMENTS:
{job_requirements}

GAP ANALYSIS (What to fill and what to ignore):
{gaps_str}

INSTRUCTIONS:
1. Review the gap report to understand what's already on the resume, what should be added from existing experience, and what should be rephased
2. Create a tailored version of the resume that highlights the most relevant experience
3. Use language from the job description where possible without misrepresenting experience
4. NEVER add experience, skills, or accomplishments not in the Career Truth Profile
5. NEVER change dates, employers, titles, or employment types
6. Organize bullets to emphasize job-relevant accomplishments
7. Output ONLY the revised resume content (bullet points and sections), ready to be inserted
   into the original resume template -- no notes, no explanations, no commentary about what
   you changed or what's missing

Provide the tailored resume content now:"""

    def _profile_to_string(self, profile: CareerTruthProfile) -> str:
        """
        Convert Career Truth Profile to readable text format.

        Args:
            profile: CareerTruthProfile object

        Returns:
            Formatted profile text
        """
        lines = []

        # Contact info
        lines.append("CONTACT INFORMATION:")
        lines.append(f"  Name: {profile.contact_info.get('name', 'N/A')}")
        lines.append(f"  Email: {profile.contact_info.get('email', 'N/A')}")
        lines.append(f"  Phone: {profile.contact_info.get('phone', 'N/A')}")
        lines.append(f"  Location: {profile.contact_info.get('location', 'N/A')}")
        lines.append("")

        # Education
        if profile.education:
            lines.append("EDUCATION:")
            for edu in profile.education:
                lines.append(
                    f"  {edu.degree} in {edu.field} from {edu.institution} ({edu.year})"
                )
                if edu.gpa:
                    lines.append(f"    GPA: {edu.gpa}")
            lines.append("")

        # Work Experience
        if profile.work_experience:
            lines.append("WORK EXPERIENCE:")
            for job in profile.work_experience:
                lines.append(f"  {job.title} at {job.employer} ({job.dates})")
                if job.location:
                    lines.append(f"    Location: {job.location}")
                if job.employment_type:
                    lines.append(f"    Type: {job.employment_type}")
                if job.responsibilities:
                    lines.append("    Responsibilities:")
                    for resp in job.responsibilities:
                        lines.append(f"      - {resp}")
                if job.accomplishments:
                    lines.append("    Accomplishments:")
                    for acc in job.accomplishments:
                        lines.append(f"      - {acc}")
            lines.append("")

        # Skills
        if profile.skills:
            lines.append("SKILLS:")
            lines.append(f"  {', '.join(profile.skills)}")
            lines.append("")

        # Tools
        if profile.tools:
            lines.append("TOOLS & PLATFORMS:")
            lines.append(f"  {', '.join(profile.tools)}")
            lines.append("")

        # Certifications
        if profile.certifications:
            lines.append("CERTIFICATIONS:")
            for cert in profile.certifications:
                lines.append(f"  - {cert}")
            lines.append("")

        # Accomplishments
        if profile.accomplishments:
            lines.append("CAREER ACCOMPLISHMENTS:")
            for acc in profile.accomplishments:
                lines.append(f"  - {acc}")
            lines.append("")

        return "\n".join(lines)

    def _format_gaps(self, gap_report: GapReport) -> str:
        """
        Format gap report for the prompt.

        Categories A/B/C are shown as things to highlight or add.
        Categories D/E are explicitly excluded from "fill" instructions.

        Args:
            gap_report: GapReport from gap analyzer

        Returns:
            Formatted gaps text
        """
        lines = []
        lines.append(gap_report.summary)
        lines.append("")

        # Organize by category
        by_category = {}
        for item in gap_report.items:
            if item.category not in by_category:
                by_category[item.category] = []
            by_category[item.category].append(item)

        # Category A: Already on resume
        if GapCategory.A in by_category:
            lines.append("CATEGORY A - Already on Resume (Optimize presentation):")
            for item in by_category[GapCategory.A]:
                lines.append(f"  - {item.requirement}")
                lines.append(f"    Reason: {item.reason}")
                lines.append(f"    Evidence: {item.candidate_evidence}")
            lines.append("")

        # Category B: Supported but missing
        if GapCategory.B in by_category:
            lines.append("CATEGORY B - Supported by Experience but Missing (Bring into resume):")
            for item in by_category[GapCategory.B]:
                lines.append(f"  - {item.requirement}")
                lines.append(f"    Reason: {item.reason}")
                lines.append(f"    Evidence: {item.candidate_evidence}")
            lines.append("")

        # Category C: Rephrasable
        if GapCategory.C in by_category:
            lines.append("CATEGORY C - Rephrasable (Rewrite to match JD language):")
            for item in by_category[GapCategory.C]:
                lines.append(f"  - {item.requirement}")
                lines.append(f"    Reason: {item.reason}")
                lines.append(f"    Evidence: {item.candidate_evidence}")
            lines.append("")

        # Category D: Needs confirmation
        if GapCategory.D in by_category:
            lines.append("CATEGORY D - Needs Confirmation (DO NOT ADD - needs user review):")
            for item in by_category[GapCategory.D]:
                lines.append(f"  - {item.requirement}")
                lines.append(f"    Reason: {item.reason}")
                lines.append("    ACTION: System is uncertain. Do not invent. Ask user.")
            lines.append("")

        # Category E: Truly missing
        if GapCategory.E in by_category:
            lines.append("CATEGORY E - Truly Missing (NEVER ADD - do not fabricate):")
            for item in by_category[GapCategory.E]:
                lines.append(f"  - {item.requirement}")
                lines.append(f"    Reason: {item.reason}")
                lines.append("    ACTION: Candidate does not have this. Do not add. Never invent.")
            lines.append("")

        return "\n".join(lines)

    def _format_job_requirements(self, job_analysis: JobAnalysis) -> str:
        """
        Format job requirements for the prompt.

        Args:
            job_analysis: JobAnalysis from job analyzer

        Returns:
            Formatted job requirements
        """
        lines = []

        if job_analysis.required_qualifications:
            lines.append("Required Qualifications:")
            for qual in job_analysis.required_qualifications:
                lines.append(f"  - {qual}")

        if job_analysis.preferred_qualifications:
            lines.append("\nPreferred Qualifications:")
            for qual in job_analysis.preferred_qualifications:
                lines.append(f"  - {qual}")

        if job_analysis.skills_required:
            lines.append("\nSkills Required:")
            for skill in job_analysis.skills_required:
                lines.append(f"  - {skill}")

        if job_analysis.tools_required:
            lines.append("\nTools Required:")
            for tool in job_analysis.tools_required:
                lines.append(f"  - {tool}")

        if job_analysis.education_required:
            lines.append(f"\nEducation: {job_analysis.education_required}")

        if job_analysis.experience_required:
            lines.append(f"\nExperience: {job_analysis.experience_required}")

        return "\n".join(lines)

    def _refine_resume(
        self,
        current_resume: str,
        improvement_prompt: str,
        profile: CareerTruthProfile,
    ) -> str:
        """
        Refine a tailored resume iteratively to improve alignment.

        Args:
            current_resume: The current version of the tailored resume
            improvement_prompt: Instructions for how to improve the resume
            profile: The Career Truth Profile (source of all truth). Passed
                through so refinement has access to the FULL profile, not
                just whatever happens to already be in the current resume
                text -- matching the guardrail scope used by tailor().

        Returns:
            Refined resume text

        This method follows the same safety pattern as tailor(): it uses the LLM
        with strict fabrication guardrails to iteratively improve the resume
        while staying true to the Career Truth Profile.
        """
        system_prompt = self._build_refinement_system_prompt()
        user_prompt = self._build_refinement_user_prompt(current_resume, improvement_prompt, profile)
        raw = self.llm.complete(system_prompt, user_prompt, max_tokens=2000)
        return _strip_non_resume_content(raw)

    def _build_refinement_system_prompt(self) -> str:
        """
        Build the system prompt for resume refinement (iteration step).

        This uses the same fabrication guardrails as the initial tailor() method.
        It constrains Claude to ONLY reorganize, rephrase, and prioritize existing
        content without adding new experience, skills, or achievements.
        """
        return """You are a professional resume refinement specialist.

YOUR CORE CONSTRAINT - CRITICAL FOR SAFETY:
You may ONLY rewrite resume content using information from the Career Truth Profile provided.
You must NEVER fabricate, invent, or add:
- Experience not in the profile
- Skills not listed in the profile
- Certifications not in the profile
- Numbers, metrics, or accomplishments not explicitly stated
- Dates, employers, titles, or employment types not in the profile

ALLOWED TRANSFORMATIONS:
- Rephrase existing bullets to better match job description language
- Reorganize sections to prioritize job-relevant experience
- Reorder bullet points by relevance
- Expand existing accomplishments (but never add new achievements)
- Change bullet structure or formatting
- Highlight relevant skills in more prominent positions

FORBIDDEN TRANSFORMATIONS:
- Adding new experience, skills, or accomplishments not in the Career Truth Profile
- Inventing metrics or achievements
- Changing dates, employers, or titles
- Adding technologies or tools not in the Career Truth Profile
- Exaggerating or misrepresenting experience

OUTPUT FORMAT - CRITICAL:
Output ONLY the resume content itself. Do NOT include any notes, explanations,
meta-commentary, reasoning, disclaimers, or a summary of what you changed.

Your task is to refine the resume iteratively to improve keyword and qualification alignment
while maintaining 100% truthfulness to the Career Truth Profile."""

    def _build_refinement_user_prompt(
        self, current_resume: str, improvement_prompt: str, profile: CareerTruthProfile
    ) -> str:
        """
        Build the user prompt for resume refinement.

        Args:
            current_resume: The current tailored resume text
            improvement_prompt: Specific instructions for improvement
            profile: The Career Truth Profile (source of all truth)

        Returns:
            Formatted user prompt for Claude
        """
        profile_str = self._profile_to_string(profile)

        return f"""Please refine the following resume to improve job alignment.

CAREER TRUTH PROFILE (Source of all truth - do NOT add anything beyond this):
{profile_str}

CURRENT RESUME:
{current_resume}

IMPROVEMENT INSTRUCTIONS:
{improvement_prompt}

REFINEMENT GUIDELINES:
1. Review the current resume for areas that could be better aligned with the job requirements
2. Reorganize and rephrase existing content to be more compelling and job-relevant
3. Highlight accomplishments and skills that may not be prominent enough
4. NEVER add experience, skills, or accomplishments not in the Career Truth Profile
5. NEVER change dates, employers, titles, or employment types
6. Maintain all factual accuracy while improving presentation
7. Output ONLY the refined resume content, preserving the structure but with improved wording
   and organization -- no notes, no explanations, no commentary

Provide the refined resume content now:"""
