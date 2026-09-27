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


# Live testing (2026-09-22) showed the model formatting its output in
# Markdown (**bold**, *italic*) despite never being asked to -- resume
# section headings and job-header lines came back as literal "**EDUCATION**"
# and "**CVS Health** | Woonsocket, RI". PDFGenerator has no Markdown
# parser, so every asterisk rendered as a literal character in the PDF
# (and worse: a line starting with "*" gets misread as a bullet point by
# PDFGenerator's own heuristic, corrupting the line's leading text too).
# Real resume text has no legitimate use for a literal asterisk, so this
# strips all of them unconditionally rather than trying to parse balanced
# Markdown pairs, which also don't reliably occur in malformed output.
def _strip_markdown_syntax(text: str) -> str:
    return text.replace("**", "").replace("*", "")


# _build_user_prompt() shows the model its own CareerTruthProfile rendered
# with internal labels like "Location:", "Responsibilities:", and
# "Accomplishments:" (see _profile_to_string) -- a weaker model can mirror
# that input structure straight into its output instead of transforming it
# into plain resume prose, especially in conservative mode where it's told
# to change as little as possible (found live, 2026-09-22: real output kept
# "Location: Woonsocket, RI" and a bare "Accomplishments:" line). These
# labels are never valid resume content on their own -- location is always
# folded into the deterministic header by _reconcile_headers_with_profile,
# and category labels add nothing a reader needs -- so they're dropped
# outright rather than chased with yet another formatting instruction.
_STRAY_LOCATION_LABEL = re.compile(r"^\s*Location\s*:\s*.*$", re.IGNORECASE)
_STRAY_CATEGORY_LABEL = re.compile(r"^\s*(Responsibilities|Accomplishments)\s*:\s*$", re.IGNORECASE)


def _strip_profile_dump_labels(text: str) -> str:
    lines = [
        line
        for line in text.split("\n")
        if not _STRAY_LOCATION_LABEL.match(line) and not _STRAY_CATEGORY_LABEL.match(line)
    ]
    return "\n".join(lines)


# The LLM phrases job/education header lines differently on essentially
# every call -- "Employer | Location Dates" one time, "Title at Employer"
# the next, "Degree from Institution (Year)" another -- and chasing each
# new phrasing with a PDF-layout heuristic is a losing game (found live,
# 2026-09-22, three separate times against the same real resume). The fix
# used by a reference implementation (github.com/jddavenportOpen/
# recruit-copilot) is to never let header formatting come from the LLM at
# all: render employer/title/dates/institution straight from the verified
# CareerTruthProfile every time. Rather than a full rewrite to a fully
# structured LLM response, this reconciles after the fact -- detect the
# header/bullets block for each job and education entry by its POSITION
# (bullets group N belongs to profile entry N, since job order is fixed
# going into the prompt) and replace only the header line(s), leaving the
# LLM's tailored bullet text untouched. This also closes a subtler gap:
# nothing previously enforced that the LLM's own header text stayed
# byte-identical to the verified employer name / dates rather than a
# paraphrase of them.
# Trailing colon must be optional -- the LLM sometimes writes "WORK
# EXPERIENCE:" instead of "WORK EXPERIENCE" despite the prompt's explicit
# "plain ALL CAPS on their own line" instruction (no colon shown in the
# example), and without it this regex silently failed to recognize the
# heading at all, which meant _find_section never located the section and
# header reconciliation below quietly skipped the whole section instead of
# fixing it (found live, 2026-09-22, against a real resume+job run: neither
# WORK EXPERIENCE nor EDUCATION got reconciled because both came back with
# a trailing colon).
_SECTION_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 &/-]{2,}:?$")


def _split_into_entry_blocks(lines: list[str]) -> list[tuple[list[str], list[str]]]:
    """Split a list of lines into (header_lines, bullet_lines) blocks. A new
    block starts whenever a non-bullet, non-heading line follows a run of
    bullets (or at the very start)."""
    blocks: list[tuple[list[str], list[str]]] = []
    header_lines: list[str] = []
    bullet_lines: list[str] = []
    in_bullets = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line or _SECTION_HEADING_RE.match(line):
            continue
        is_bullet = line.startswith(("-", "•"))
        if is_bullet:
            bullet_lines.append(line.lstrip("-• ").strip())
            in_bullets = True
        else:
            if in_bullets:
                blocks.append((header_lines, bullet_lines))
                header_lines, bullet_lines = [], []
                in_bullets = False
            header_lines.append(line)

    if header_lines or bullet_lines:
        blocks.append((header_lines, bullet_lines))
    return blocks


def _job_header_lines(job) -> list[str]:
    location_part = f"{job.location}    " if job.location else ""
    return [f"{job.employer} | {location_part}{job.dates}".rstrip(), job.title]


def _education_header_lines(edu) -> list[str]:
    degree_line = f"{edu.degree} in {edu.field}" if edu.field else edu.degree
    return [f"{edu.institution} | {edu.year}", degree_line]


def _reassemble_section(
    section_lines: list[str], entries: list, header_builder
) -> list[str]:
    """Rebuild a section's lines with deterministic, profile-sourced headers,
    matching bullet blocks to profile entries by position. Falls back to
    leaving the section untouched if the block count doesn't match the
    profile's entry count -- safer than guessing a mismatched pairing."""
    blocks = _split_into_entry_blocks(section_lines)
    if len(blocks) != len(entries):
        return section_lines

    rebuilt: list[str] = []
    for (_, bullet_lines), entry in zip(blocks, entries):
        rebuilt.extend(header_builder(entry))
        rebuilt.extend(f"- {b}" for b in bullet_lines)
        rebuilt.append("")
    return rebuilt


def _find_section(lines: list[str], heading_pattern: str) -> tuple[int, int] | None:
    """Return (start, end) line indices of a section's BODY (excluding the
    heading itself), from the matching ALL-CAPS heading to the next ALL-CAPS
    heading or end of text."""
    heading_re = re.compile(heading_pattern, re.IGNORECASE)
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if start is None and heading_re.match(stripped) and _SECTION_HEADING_RE.match(stripped):
            start = i + 1
            continue
        if start is not None and _SECTION_HEADING_RE.match(stripped) and not heading_re.match(stripped):
            return start, i
    if start is not None:
        return start, len(lines)
    return None


def _reconcile_headers_with_profile(text: str, profile: CareerTruthProfile) -> str:
    """Replace job/education header lines with deterministic ones sourced
    directly from the verified profile, leaving tailored bullet text as-is."""
    lines = text.split("\n")

    if profile.work_experience:
        bounds = _find_section(lines, r"(?:WORK\s+)?EXPERIENCE")
        if bounds:
            start, end = bounds
            rebuilt = _reassemble_section(lines[start:end], profile.work_experience, _job_header_lines)
            lines = lines[:start] + rebuilt + lines[end:]

    if profile.education:
        bounds = _find_section(lines, r"EDUCATION")
        if bounds:
            start, end = bounds
            rebuilt = _reassemble_section(lines[start:end], profile.education, _education_header_lines)
            lines = lines[:start] + rebuilt + lines[end:]

    return "\n".join(lines)


# Module-level so DocxBulletTailorer (product/resume_tailorer/tailorer/
# docx_bullet_tailorer.py) can build the same profile/gap/job-requirements
# prompt sections without depending on a ResumeTailorer instance -- these
# never used `self` for anything but the call itself.
def profile_to_string(profile: CareerTruthProfile) -> str:
    """Convert Career Truth Profile to readable text format."""
    lines = []

    # Contact info
    lines.append("CONTACT INFORMATION:")
    lines.append(f"  Name: {profile.contact_info.get('name', 'N/A')}")
    lines.append(f"  Email: {profile.contact_info.get('email', 'N/A')}")
    lines.append(f"  Phone: {profile.contact_info.get('phone', 'N/A')}")
    lines.append(f"  Location: {profile.contact_info.get('location', 'N/A')}")
    lines.append("")

    # Professional summary (if the original resume had one)
    if profile.summary:
        lines.append("PROFESSIONAL SUMMARY:")
        lines.append(f"  {profile.summary}")
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
            for note in edu.notes:
                lines.append(f"    - {note}")
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


def format_gaps(gap_report: GapReport) -> str:
    """
    Format gap report for the prompt.

    Categories A/B/C are shown as things to highlight or add.
    Categories D/E are explicitly excluded from "fill" instructions.
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


def format_job_requirements(job_analysis: JobAnalysis) -> str:
    """Format job requirements for the prompt."""
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
        conservative: bool = False,
    ) -> str:
        """
        Tailor resume content to match job requirements.

        Args:
            profile: The Career Truth Profile (the only source of truth)
            job_analysis: Parsed job description with requirements
            gap_report: Gap analysis classifying each requirement A-E
            conservative: When True, restrict the rewrite to inserting missing
                ATS keywords/phrases into existing bullets rather than a full
                rewrite -- requested live (2026-09-22) for a user who wanted
                their resume's wording and structure left otherwise untouched.

        Returns:
            Tailored resume text (string)

        This method calls the LLM via LLMClient with strict constraints to ensure:
        - No fabrication of experience, skills, certifications, numbers, dates, or employers
        - Only rephrase, reorganize, prioritize existing experience
        - Respect gap categories: fill A/B/C, ignore D/E
        """
        system_prompt = self._build_system_prompt(conservative=conservative)
        user_prompt = self._build_user_prompt(profile, job_analysis, gap_report, conservative=conservative)
        raw = self.llm.complete(system_prompt, user_prompt, max_tokens=2000)
        cleaned = _strip_profile_dump_labels(_strip_markdown_syntax(_strip_non_resume_content(raw)))
        return _reconcile_headers_with_profile(cleaned, profile)

    def _build_system_prompt(self, conservative: bool = False) -> str:
        """
        Build the system prompt that constrains Claude to Career Truth Profile only.

        This is CRITICAL: the system prompt IS the fabrication guardrail.
        It must explicitly forbid adding experience, skills, certifications,
        numbers, dates, or employers not in the Career Truth Profile.
        """
        conservative_block = ""
        if conservative:
            conservative_block = """

CONSERVATIVE MODE - ADDITIONAL CONSTRAINT (this overrides ALLOWED TRANSFORMATIONS above):
The candidate wants their resume's wording and structure left as close to the
original as possible. Do NOT rewrite bullets that already communicate a
requirement adequately, and do NOT reorganize or restructure sections.
Your ONLY job is to weave the specific missing keywords/phrases from the job
posting (Category B and C gaps) into the existing bullets with the smallest
possible edit -- ideally adding or swapping a few words in place, not
rewriting the whole sentence. Leave every other bullet byte-for-byte
identical to the profile's wording. Do not add new bullets unless a
Category B item has no existing bullet it can be woven into."""
        return f"""You are a resume tailoring specialist. Your job is NOT to insert job-description
keywords into the resume. Your job is to find the candidate's STRONGEST VERIFIED EVIDENCE for
this job and express it clearly using job-relevant language, without changing what actually
happened.{conservative_block}

YOUR CORE CONSTRAINT - CRITICAL FOR SAFETY:
You may ONLY rewrite resume content using information from the Career Truth Profile provided.
You must NEVER fabricate, invent, or add:
- Experience not in the profile
- Skills not listed in the profile
- Certifications not in the profile
- Numbers, metrics, or accomplishments not explicitly stated
- Dates, employers, titles, or employment types not in the profile
- A characterization of an accomplishment that isn't supported (e.g. calling a project
  "loyalty-focused" when the profile never describes it that way, even if "loyalty" appears
  in the job description)

HOW TO APPROACH THE RESUME -- work through this order, don't jump straight to rewriting:
1. Look at EVERY bullet across EVERY job first. Many of the job's top requirements are often
   already demonstrated somewhere in the resume (e.g. "cross-functional stakeholder management"
   might already be evidenced by a bullet about aligning stakeholders, even if that bullet
   never uses the words "cross-functional" or "stakeholder management" verbatim). Find these
   BEFORE deciding anything needs a new phrase inserted.
2. For each bullet, decide: KEEP (already strong evidence, clear language -- leave untouched),
   REPHRASE (real evidence exists here, but job-relevant language would make it easier for a
   recruiter to recognize the match), or LEAVE UNCHANGED (no relevant requirement applies to
   this bullet -- most bullets should end up here).
3. Do not spread edits thin by touching many bullets superficially. A resume where 2-4 bullets
   per job are rephrased well to surface real, strong evidence beats one where every bullet has
   a token keyword inserted.

SEMANTIC PRESERVATION -- CRITICAL, CHECK THIS BEFORE EVERY REWRITE:
A rephrase may ADD job-relevant language. It must NEVER remove or replace a word that changes
WHAT was accomplished, narrowing or shifting the claim -- even if the replacement word is
itself a real word from elsewhere in the profile.
  WRONG: "Developed a front-store growth strategy" -> "Developed a front-store acquisition
  strategy". This is wrong even though "acquisition" is a real word used elsewhere in the
  resume -- the original claim was about GROWTH broadly (tied to incremental sales), and
  swapping in "acquisition" narrows and changes that claim. "Growth" must stay.
  RIGHT: "Developed a front-store growth strategy" -> "Developed a front-store growth and
  acquisition strategy" (ADDS the concept without dropping the original claim), or leave it
  unchanged and instead rephrase a DIFFERENT bullet that more naturally evidences acquisition
  work.
Before finalizing any rewrite, ask yourself: does the new wording still mean substantially the
same thing as the original? If a word central to the original claim is gone, leave that bullet
as-is instead.

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
Output PLAIN TEXT ONLY. Do not use Markdown formatting of any kind: no **bold**, no
*italics*, no # headings, no markdown bullet syntax. Write section headings in plain
ALL CAPS on their own line, and write each bullet as a plain line starting with "-".
Keep each job's "Employer | Location    Dates" line and "Job Title" line as their own
plain lines, NOT bulleted -- bullets are only for the accomplishment/responsibility
lines underneath them.

Your output must be a revised resume that increases alignment with the job while maintaining 100% truthfulness to the Career Truth Profile."""

    def _build_user_prompt(
        self,
        profile: CareerTruthProfile,
        job_analysis: JobAnalysis,
        gap_report: GapReport,
        conservative: bool = False,
    ) -> str:
        """
        Build the user prompt requesting tailored resume.

        Args:
            profile: Career Truth Profile
            job_analysis: Parsed job requirements
            gap_report: Gap analysis results
            conservative: See ResumeTailorer.tailor().

        Returns:
            Formatted user prompt for Claude
        """
        profile_str = self._profile_to_string(profile)
        gaps_str = self._format_gaps(gap_report)
        job_requirements = self._format_job_requirements(job_analysis)

        if conservative:
            instructions = """INSTRUCTIONS (CONSERVATIVE MODE - minimal edits only):
1. Start from the resume exactly as described in the Career Truth Profile above
2. For each Category B/C gap, find the existing bullet it relates to and insert the
   missing keyword/phrase into that bullet with the smallest edit that fits it in
3. Do NOT rewrite bullets that don't relate to a gap -- keep them exactly as given
4. Do NOT reorder or reorganize sections, jobs, or bullets
5. NEVER add experience, skills, or accomplishments not in the Career Truth Profile
6. NEVER change dates, employers, titles, or employment types
7. If a PROFESSIONAL SUMMARY is provided above, keep it as-is unless a gap keyword
   naturally fits into it with a small edit
8. Output ONLY the revised resume content (bullet points and sections), ready to be inserted
   into the original resume template -- no notes, no explanations, no commentary about what
   you changed or what's missing"""
        else:
            instructions = """INSTRUCTIONS:
1. Review the gap report to understand what's already on the resume, what should be added from existing experience, and what should be rephased
2. Create a tailored version of the resume that highlights the most relevant experience
3. Use language from the job description where possible without misrepresenting experience
4. NEVER add experience, skills, or accomplishments not in the Career Truth Profile
5. NEVER change dates, employers, titles, or employment types
6. Organize bullets to emphasize job-relevant accomplishments
7. If a PROFESSIONAL SUMMARY is provided above, include a short summary paragraph near the
   top of the output, lightly adapted toward this job -- do not drop it
8. Output ONLY the revised resume content (bullet points and sections), ready to be inserted
   into the original resume template -- no notes, no explanations, no commentary about what
   you changed or what's missing"""

        return f"""Please tailor the following resume to match the job requirements below.

CAREER TRUTH PROFILE (Source of all truth - do NOT add anything beyond this):
{profile_str}

JOB REQUIREMENTS:
{job_requirements}

GAP ANALYSIS (What to fill and what to ignore):
{gaps_str}

{instructions}

Provide the tailored resume content now:"""

    def _profile_to_string(self, profile: CareerTruthProfile) -> str:
        return profile_to_string(profile)

    def _format_gaps(self, gap_report: GapReport) -> str:
        return format_gaps(gap_report)

    def _format_job_requirements(self, job_analysis: JobAnalysis) -> str:
        return format_job_requirements(job_analysis)

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
        cleaned = _strip_profile_dump_labels(_strip_markdown_syntax(_strip_non_resume_content(raw)))
        return _reconcile_headers_with_profile(cleaned, profile)

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
Output PLAIN TEXT ONLY. Do not use Markdown formatting of any kind: no **bold**, no
*italics*, no # headings. Write section headings in plain ALL CAPS on their own line,
and each bullet as a plain line starting with "-". Keep each job's "Employer | Location
Dates" line and "Job Title" line as their own plain lines, NOT bulleted.

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
