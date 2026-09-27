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
from resume_tailorer.analyzers.competency_map import extract_profile_sentences, supported_competencies
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
        max_repair_attempts: int = 1,
        priority_focus: list[str] | None = None,
    ) -> BulletTailoringResult:
        """
        max_repair_attempts: when a proposed rewrite is rejected by a
        safety check, the request's own rejection reason is fed back to
        the model in a bounded follow-up call asking for a safer
        alternative, rather than giving up on the whole bullet after one
        failed attempt (found live, 2026-09-23: a request explicitly
        asked for this -- "do not give up after one safe rewrite fails").
        1 attempt by default (2 LLM calls total, worst case) to bound
        cost/latency against a backend already known to be flaky; a
        second repair attempt rarely does much better than the first once
        the model has already been told exactly why it failed.

        priority_focus: optional list of specific requirement/evidence
        text to call out explicitly (Step 14's resume-wide optimization
        pass -- see run_docx_tailoring_pipeline). Used for a SECOND call
        on bullets a first pass already looked at once and judged not
        worth touching, so the model needs a stronger, specific nudge
        toward requirements that still have strong unused evidence,
        rather than the same general instructions producing the same
        result again.
        """
        if not bullets:
            return BulletTailoringResult(edits=[], warnings=[])

        by_index = {b.paragraph_index: b for b in bullets}
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(bullets, profile, job_analysis, gap_report, priority_focus)
        raw = self.llm.complete(system_prompt, user_prompt, max_tokens=2000)
        result = self._parse_and_validate(raw, bullets, profile)

        for _ in range(max_repair_attempts):
            rejected = [e for e in result.edits if e.rejected_reason]
            if not rejected:
                break
            rejected_bullets = [by_index[e.paragraph_index] for e in rejected]
            repair_prompt = self._build_repair_prompt(rejected, by_index)
            raw_repair = self.llm.complete(system_prompt, repair_prompt, max_tokens=1000)
            repair_result = self._parse_and_validate(raw_repair, rejected_bullets, profile)
            result = self._merge_repair(result, repair_result)

        return result

    def _build_repair_prompt(
        self, rejected: list[BulletEdit], by_index: dict[int, Bullet]
    ) -> str:
        items = []
        for edit in rejected:
            bullet = by_index[edit.paragraph_index]
            items.append(
                {
                    "paragraph_index": bullet.paragraph_index,
                    "section": bullet.section,
                    "text": bullet.text,
                    "text_length": len(bullet.text),
                    "max_new_text_length": round(len(bullet.text) * _MAX_LENGTH_GROWTH),
                    "your_previous_attempt_was_rejected_because": edit.rejected_reason,
                }
            )
        bullets_json = json.dumps(items, indent=2)
        return f"""Your previous rewrite for the bullets below was rejected by a safety check -- each
one shows exactly why. Propose a SAFER alternative that fixes that specific problem (e.g. if
rejected for dropping a word, add job-relevant language without removing that word; if rejected
for an unverified term, remove that term or replace it with something the evidence actually
supports). If no safe improvement is possible without repeating the same problem, use "change":
"keep" for that bullet rather than trying again with the same issue.

BULLETS TO REPAIR:
{bullets_json}

Return the JSON array now, in the same format as before:"""

    @staticmethod
    def _merge_repair(
        original: BulletTailoringResult, repair: BulletTailoringResult
    ) -> BulletTailoringResult:
        """Repaired bullets replace their original outcome (whether the
        repair succeeded or failed again with a new reason); every other
        bullet's outcome is untouched."""
        repair_by_index = {e.paragraph_index: e for e in repair.edits}
        merged_edits = [repair_by_index.get(e.paragraph_index, e) for e in original.edits]
        return BulletTailoringResult(
            edits=merged_edits, warnings=original.warnings + repair.warnings
        )

    @staticmethod
    def _validate_competency_edit(
        orig_label: str,
        orig_items: list[str],
        new_label: str,
        new_items: list[str],
        profile: CareerTruthProfile,
    ) -> str | None:
        """Returns a rejection reason, or None if the edit is a valid
        reorder and/or bounded evidence-backed swap of the Core
        Competencies line."""
        if new_label != orig_label:
            return "label changed"
        if len(new_items) != len(orig_items):
            return "item count changed"

        orig_lower = [i.lower() for i in orig_items]
        new_lower = [i.lower() for i in new_items]
        removed = [i for i in orig_lower if i not in new_lower]
        added = [i for i in new_lower if i not in orig_lower]
        if len(added) != len(removed):
            return "item set changed inconsistently"
        if len(added) > 2:
            return f"too many items swapped ({len(added)}); at most 2 allowed per pass"
        if not added:
            return None  # pure reorder

        evidence_backed = supported_competencies(extract_profile_sentences(profile))
        unverified = [item for item in added if item not in evidence_backed]
        if unverified:
            return f"new item(s) {unverified} are not backed by evidence in the profile"
        return None

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
- For the "competencies" section (if shown below), you may reorder the existing pipe-separated
  items to put the most job-relevant ones first, AND you may swap out up to 2 less-relevant
  items for ones from the "evidence_backed_alternatives" list shown with that bullet -- these
  are competencies the profile's own actions already demonstrate, just not currently named in
  this list. Never introduce an item that ISN'T in "evidence_backed_alternatives", never reword
  an existing item, and keep the total item count the same.

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
        priority_focus: list[str] | None = None,
    ) -> str:
        profile_str = profile_to_string(profile)
        gaps_str = format_gaps(gap_report)
        job_requirements = format_job_requirements(job_analysis)

        priority_block = ""
        if priority_focus:
            focus_lines = "\n".join(f"- {item}" for item in priority_focus)
            priority_block = f"""

RESUME-WIDE OPTIMIZATION PASS -- READ THIS FIRST:
A previous tailoring pass already ran on this resume. The requirements below have STRONG
verified evidence somewhere in this resume but are STILL not well represented after that pass.
Look specifically for a bullet that could surface each one (rephrase, reprioritize wording, or
a competency-section swap) before falling back to your general judgment on the rest:
{focus_lines}
Do not force an edit where none is safe -- if no bullet can honestly surface one of these
without violating SEMANTIC PRESERVATION or inventing something, leave it unaddressed."""

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
            if bullet.section == "competencies":
                _label, current_items = _split_competency_line(bullet.text)
                current_lower = {i.lower() for i in current_items}
                evidence_backed = supported_competencies(extract_profile_sentences(profile))
                item["evidence_backed_alternatives"] = [
                    key.title() for key in evidence_backed if key not in current_lower
                ]
            bullet_items.append(item)
        bullets_json = json.dumps(bullet_items, indent=2)

        return f"""CAREER TRUTH PROFILE (Source of all truth - do NOT add anything beyond this):
{profile_str}

JOB REQUIREMENTS:
{job_requirements}

GAP ANALYSIS (What to fill and what to ignore):
{gaps_str}
{priority_block}

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
                # Reorder AND up to 2 evidence-backed swaps (Problem 6/10:
                # "keep approximately the same number of competencies, only
                # include one when evidence exists" -- prioritizing a more
                # job-relevant, ALREADY-DEMONSTRATED competency over a less
                # relevant one is not fabrication, it's evidence-backed
                # abstraction). Never trusts the model's own judgment of
                # what's "evidence-backed" -- re-validates every added item
                # against the same curated competency map used to build the
                # prompt's suggestion list in the first place.
                orig_label, orig_items = _split_competency_line(bullet.text)
                new_label, new_items = _split_competency_line(new_text)
                rejection = self._validate_competency_edit(orig_label, orig_items, new_label, new_items, profile)
                if rejection:
                    warnings.append(f"Rejected a competencies edit for paragraph {paragraph_index}: {rejection}")
                    resolved[paragraph_index] = BulletEdit(
                        paragraph_index, bullet.text, bullet.text, changed=False, rejected_reason=rejection
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
