"""
LLM-driven per-bullet structured tailoring for the DOCX master-template
pipeline. Unlike ResumeTailorer.tailor(), which asks for a whole new resume
as freeform text, this asks for a JSON array of {paragraph_index, change,
new_text} edits -- one per bullet shown -- so the result can be spliced
directly into the ORIGINAL document's paragraphs (see
docx_export/splicer.py) instead of generating a new document from scratch.
"""

from dataclasses import dataclass, field
import json
import re

from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.llm.settings import LLMSettings, resolve_settings
from resume_tailorer.parsers.docx_structure import Bullet
from resume_tailorer.tailorer.resume_tailorer import (
    profile_to_string,
    format_gaps,
    format_job_requirements,
    _strip_markdown_syntax,
)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_WHITESPACE_RE = re.compile(r"[\r\n]+")

# The length ceiling is a prompt INSTRUCTION (see _build_system_prompt /
# "max_new_text_length"), but the prompt alone isn't trusted to be
# followed -- confirmed live (2026-09-22): a real model rewrote one bullet
# 71% longer than the original despite being told to keep length close,
# which alone pushed a 1-page resume to 2 pages. Enforced again here in
# code as a hard rule, per the user's own explicit ask that length limits
# live in code, not just the system prompt.
_MAX_LENGTH_GROWTH = 1.15


@dataclass
class BulletEdit:
    paragraph_index: int
    original_text: str
    new_text: str  # == original_text when unchanged
    changed: bool


@dataclass
class BulletTailoringResult:
    edits: list[BulletEdit] = field(default_factory=list)  # same order as input bullets
    warnings: list[str] = field(default_factory=list)


class DocxBulletTailorer:
    """
    Asks the LLM to edit a fixed set of existing bullets in place, never to
    write a new resume. There is no "conservative vs. full rewrite" toggle
    here (unlike ResumeTailorer) -- splicing into pre-existing paragraphs
    only ever supports minimal, in-place text replacement by construction.
    """

    def __init__(self, llm: LLMClient | None = None, settings: LLMSettings | None = None):
        if llm is not None:
            self.llm = llm
        elif settings is not None:
            self.llm = LLMClient(settings)
        else:
            self.llm = LLMClient(resolve_settings())

    def tailor_bullets(
        self,
        bullets: list[Bullet],
        profile: CareerTruthProfile,
        job_analysis: JobAnalysis,
        gap_report: GapReport,
    ) -> BulletTailoringResult:
        if not bullets:
            return BulletTailoringResult(edits=[], warnings=[])

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(bullets, profile, job_analysis, gap_report)
        raw = self.llm.complete(system_prompt, user_prompt, max_tokens=2000)
        return self._parse_and_validate(raw, bullets)

    def _build_system_prompt(self) -> str:
        return """You are a professional resume tailoring specialist editing a resume IN PLACE.

YOUR CORE CONSTRAINT - CRITICAL FOR SAFETY:
You may ONLY rewrite bullet text using information from the Career Truth Profile provided.
You must NEVER fabricate, invent, or add:
- Experience not in the profile
- Skills not listed in the profile
- Certifications not in the profile
- Numbers, metrics, or accomplishments not explicitly stated
- Dates, employers, titles, or employment types not in the profile

You are editing individual bullets of an EXISTING, already-formatted document. You are NOT
writing a new resume, and your output is NEVER shown to a reader directly -- it is spliced
back into the original document's own paragraphs. Because of this:
- Do not add new bullets, sections, or headings.
- Do not merge or split bullets.
- Do not restate the employer, title, or dates -- they are shown only for context.
- CRITICAL LENGTH LIMIT: each bullet in the input includes "text_length" (its current
  character count) and "max_new_text_length" (text_length + 15% -- the hard ceiling for
  "new_text"). This text replaces the original in a fixed-layout document; going over
  "max_new_text_length" risks pushing it onto an extra line or the whole resume onto an extra
  page. If your edit would exceed the limit, cut words elsewhere in the SAME bullet to stay
  under it rather than skip the keyword -- never submit a "new_text" longer than
  "max_new_text_length".
- Only rewrite a bullet if doing so genuinely helps address a specific missing job
  requirement (Category B or C in the gap report). Leave every other bullet unchanged.

OUTPUT FORMAT - CRITICAL:
Return ONLY a JSON array, no markdown code fences, no commentary before or after it. Include
exactly one object per bullet shown below, covering every "paragraph_index" exactly once, in
this shape:
[{"paragraph_index": <int, copied exactly from the input>, "change": "keep" or "rewrite", "new_text": "<full replacement text if rewriting, else empty>"}]
When "change" is "keep", "new_text" is ignored -- the original text is always used.
"new_text" must be plain text: no markdown, no leading bullet marker/dash, one line only."""

    def _build_user_prompt(
        self,
        bullets: list[Bullet],
        profile: CareerTruthProfile,
        job_analysis: JobAnalysis,
        gap_report: GapReport,
    ) -> str:
        profile_str = profile_to_string(profile)
        gaps_str = format_gaps(gap_report)
        job_requirements = format_job_requirements(job_analysis)

        bullet_items = []
        for bullet in bullets:
            item = {
                "paragraph_index": bullet.paragraph_index,
                "section": bullet.section,
                "text": bullet.text,
                "text_length": len(bullet.text),
                "max_new_text_length": round(len(bullet.text) * _MAX_LENGTH_GROWTH),
            }
            if bullet.section == "work_experience" and bullet.job_index is not None:
                job = profile.work_experience[bullet.job_index]
                item["employer"] = job.employer
                item["title"] = job.title
            bullet_items.append(item)
        bullets_json = json.dumps(bullet_items, indent=2)

        return f"""CAREER TRUTH PROFILE (Source of all truth - do NOT add anything beyond this):
{profile_str}

JOB REQUIREMENTS:
{job_requirements}

GAP ANALYSIS (What to fill and what to ignore):
{gaps_str}

EXISTING BULLETS (edit ONLY these, in place -- one JSON object per "paragraph_index"):
{bullets_json}

Return the JSON array now:"""

    def _parse_and_validate(self, raw: str, bullets: list[Bullet]) -> BulletTailoringResult:
        warnings: list[str] = []
        cleaned = _CODE_FENCE_RE.sub("", raw.strip()).strip()

        try:
            parsed = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            parsed = None

        if not isinstance(parsed, list):
            return BulletTailoringResult(
                edits=[
                    BulletEdit(b.paragraph_index, b.text, b.text, changed=False) for b in bullets
                ],
                warnings=["LLM returned malformed JSON; no bullets were changed."],
            )

        by_index = {b.paragraph_index: b for b in bullets}
        resolved: dict[int, BulletEdit] = {}

        for element in parsed:
            if not isinstance(element, dict):
                warnings.append(f"Skipped a non-object entry in the LLM response: {element!r}")
                continue
            paragraph_index = element.get("paragraph_index")
            if not isinstance(paragraph_index, int) or paragraph_index not in by_index:
                warnings.append(
                    f"Skipped an entry with an unknown/invalid paragraph_index: {element!r}"
                )
                continue
            if paragraph_index in resolved:
                warnings.append(f"Skipped a duplicate edit for paragraph {paragraph_index}.")
                continue

            bullet = by_index[paragraph_index]
            change = element.get("change")
            if change != "rewrite":
                resolved[paragraph_index] = BulletEdit(
                    paragraph_index, bullet.text, bullet.text, changed=False
                )
                continue

            new_text = element.get("new_text", "")
            if not isinstance(new_text, str):
                new_text = ""
            new_text = _strip_markdown_syntax(new_text)
            new_text = _WHITESPACE_RE.sub(" ", new_text).strip()
            new_text = new_text.lstrip("•-* ").strip()

            if not new_text:
                warnings.append(
                    f"Model requested a rewrite with empty text for paragraph {paragraph_index}; kept original."
                )
                resolved[paragraph_index] = BulletEdit(
                    paragraph_index, bullet.text, bullet.text, changed=False
                )
                continue

            max_len = round(len(bullet.text) * _MAX_LENGTH_GROWTH)
            if len(new_text) > max_len:
                warnings.append(
                    f"Rejected a rewrite for paragraph {paragraph_index}: {len(new_text)} chars "
                    f"exceeds the {max_len}-char limit ({_MAX_LENGTH_GROWTH:.0%} of the original "
                    f"{len(bullet.text)} chars); kept original."
                )
                resolved[paragraph_index] = BulletEdit(
                    paragraph_index, bullet.text, bullet.text, changed=False
                )
                continue

            resolved[paragraph_index] = BulletEdit(
                paragraph_index, bullet.text, new_text, changed=new_text != bullet.text
            )

        missing = [b for b in bullets if b.paragraph_index not in resolved]
        if missing:
            if len(missing) > 3:
                warnings.append(
                    f"LLM response did not cover {len(missing)} bullets; they were left unchanged."
                )
            for bullet in missing:
                resolved[bullet.paragraph_index] = BulletEdit(
                    bullet.paragraph_index, bullet.text, bullet.text, changed=False
                )

        edits = [resolved[b.paragraph_index] for b in bullets]
        return BulletTailoringResult(edits=edits, warnings=warnings)
