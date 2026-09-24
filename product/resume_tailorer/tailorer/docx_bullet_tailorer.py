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
from resume_tailorer.diff_generator import DiffGenerator
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


def _split_competency_line(text: str) -> tuple[str, list[str]]:
    """"Core Competencies: A | B | C" -> ("Core Competencies", ["A", "B", "C"])."""
    label, _, rest = text.partition(":")
    items = [item.strip() for item in rest.split("|") if item.strip()]
    return label.strip(), items

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
    # Set when the LLM asked to change this bullet but a code-level check
    # (length cap, semantic drift, competency itemset) overrode it back to
    # the original -- distinct from a plain "keep" the model chose itself,
    # so callers can tell "left alone on purpose" from "tried and blocked."
    rejected_reason: str | None = None


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
        self._diff_gen = DiffGenerator()

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
        return self._parse_and_validate(raw, bullets, profile)

    def _build_system_prompt(self) -> str:
        return """You are a resume tailoring specialist editing a resume IN PLACE. Your job is
NOT to insert job-description keywords into the resume. Your job is to find the candidate's
STRONGEST VERIFIED EVIDENCE for this job and express it clearly using job-relevant language,
without changing what actually happened.

YOUR CORE CONSTRAINT - CRITICAL FOR SAFETY:
You may ONLY rewrite bullet text using information from the Career Truth Profile provided.
You must NEVER fabricate, invent, or add:
- Experience not in the profile
- Skills not listed in the profile
- Certifications not in the profile
- Numbers, metrics, or accomplishments not explicitly stated
- Dates, employers, titles, or employment types not in the profile
- A characterization of an accomplishment that isn't supported (e.g. calling a project
  "loyalty-focused" when the profile never describes it that way, even if "loyalty" appears
  in the job description)

HOW TO APPROACH EACH BULLET -- work through this order, don't jump straight to rewriting:
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
   are rephrased well to surface real, strong evidence beats one where every bullet has a
   token keyword inserted.

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
Before finalizing any "rewrite", ask yourself: does the new wording still mean substantially
the same thing as the original? If a word central to the original claim is gone, revert to
"keep" for that bullet instead.

OTHER RULES:
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
- Only rewrite a bullet if doing so genuinely helps address a specific job requirement backed
  by real evidence (Category A/B/C in the gap report -- NEVER category D or E). Leave every
  other bullet unchanged.
- For the "competencies" section (if shown below), you may ONLY reorder the existing
  pipe-separated items to put the most job-relevant ones first -- never add, remove, or reword
  an item. "new_text" must contain exactly the same items, separated by " | ", just reordered.

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

    def _parse_and_validate(
        self, raw: str, bullets: list[Bullet], profile: CareerTruthProfile
    ) -> BulletTailoringResult:
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
            raw_new_text = element.get("new_text")

            # Defensive fallback for a malformed-but-recoverable response
            # shape found live (2026-09-23): the model echoed the INPUT
            # bullet objects back almost verbatim -- including a "text"
            # field, the input's own key name -- instead of the requested
            # {"change", "new_text"} output shape, but had actually
            # rewritten the bullet's content inside that "text" field. If
            # "change"/"new_text" are absent but "text" differs from the
            # bullet's real original, treat "text" as the intended
            # new_text rather than silently discarding real tailoring work
            # just because it arrived under the wrong key.
            if change != "rewrite" and raw_new_text is None:
                echoed_text = element.get("text")
                if isinstance(echoed_text, str) and echoed_text.strip() != bullet.text.strip():
                    change = "rewrite"
                    raw_new_text = echoed_text
                    warnings.append(
                        f"Recovered a rewrite for paragraph {paragraph_index} from a malformed "
                        "response (model echoed the input's \"text\" key instead of \"new_text\")."
                    )

            if change != "rewrite":
                resolved[paragraph_index] = BulletEdit(
                    paragraph_index, bullet.text, bullet.text, changed=False
                )
                continue

            new_text = raw_new_text if raw_new_text is not None else ""
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

            if bullet.section == "competencies":
                # Reorder-only: the LLM may only permute the existing
                # pipe-separated items, never add/remove/reword one (Problem
                # 6 -- "keep approximately the same number of competencies,
                # only include one when evidence exists"). A stricter,
                # exact-itemset check than the generic length/drift checks
                # below, which would tolerate reordering fine but wouldn't
                # catch e.g. a merged or reworded item that happens to keep
                # the same content words.
                orig_label, orig_items = _split_competency_line(bullet.text)
                new_label, new_items = _split_competency_line(new_text)
                if new_label != orig_label or sorted(new_items) != sorted(orig_items):
                    reason = "competencies item set changed"
                    warnings.append(
                        f"Rejected a competencies reorder for paragraph {paragraph_index}: "
                        "item set changed (must reorder the exact same items); kept original."
                    )
                    resolved[paragraph_index] = BulletEdit(
                        paragraph_index, bullet.text, bullet.text, changed=False, rejected_reason=reason
                    )
                else:
                    resolved[paragraph_index] = BulletEdit(
                        paragraph_index, bullet.text, new_text, changed=new_text != bullet.text
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
                    paragraph_index, bullet.text, bullet.text, changed=False, rejected_reason="length cap exceeded"
                )
                continue

            # Hard, code-level rejection of a rewrite that drops one of the
            # original bullet's own content words -- found live
            # (2026-09-23): "growth" silently replaced with "acquisition",
            # narrowing a broad claim to a specific one even though
            # "acquisition" was itself a legitimate word elsewhere in the
            # resume. Prompt instructions alone weren't trusted to prevent
            # this (same lesson as the length cap above), so it's enforced
            # again here regardless of what the system prompt says.
            drift_issues = self._diff_gen.check_semantic_drift(bullet.text, new_text)
            if drift_issues:
                warnings.append(f"Rejected a rewrite for paragraph {paragraph_index}: {drift_issues[0]}")
                resolved[paragraph_index] = BulletEdit(
                    paragraph_index, bullet.text, bullet.text, changed=False, rejected_reason="semantic drift"
                )
                continue

            # Hard, code-level rejection of an unverified characterization
            # sneaking in as fact -- found live (2026-09-23), TWICE:
            # "loyalty" added to describe a program the profile never
            # calls that, even though "loyalty" appears in the job
            # description. The system prompt explicitly forbids this (see
            # the "loyalty-focused" example above) and it still happened,
            # so it's enforced again here rather than trusted to the
            # prompt alone -- same lesson as length cap and semantic drift.
            fabrication_issues = self._diff_gen.check_bullet_pair_fabrication_risk(
                bullet.text, new_text, profile
            )
            if fabrication_issues:
                warnings.append(f"Rejected a rewrite for paragraph {paragraph_index}: {fabrication_issues[0]}")
                resolved[paragraph_index] = BulletEdit(
                    paragraph_index, bullet.text, bullet.text, changed=False, rejected_reason="unverified content"
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
