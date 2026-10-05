"""
Structural walker for a DOCX resume, used by the DOCX master-template
tailoring pipeline (product/resume_tailorer/docx_export/pipeline.py). Finds
WHICH paragraphs are bullet points inside the WORK EXPERIENCE section (plus
the PROFESSIONAL SUMMARY paragraph), by paragraph INDEX -- so that pipeline
can splice new text into the exact same paragraph objects afterward,
without ever adding, removing, or reordering a paragraph.

Deliberately does NOT build a CareerTruthProfile or duplicate any of
ResumeParser's regex-based field extraction -- this only answers "which
paragraph indices are splice targets," reusing the same anchor-by-year
algorithm and section-boundary set ResumeParser uses on PDF-flattened text
(see anchor_detection.py, section_headings.py), so the two never disagree
about where a job block starts or ends.
"""

from dataclasses import dataclass, field
import re

from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from resume_tailorer.parsers.anchor_detection import find_anchor_blocks
from resume_tailorer.parsers.bullets import strip_typed_bullet, typed_bullet_prefix
from resume_tailorer.parsers.section_headings import SECTION_BOUNDARY_RE, WORK_EXPERIENCE_HEADING_RE

_MIN_TITLE_LENGTH = 3
_NAME_SEARCH_LINES = 5

# Only "Core Competencies" is a rankable list of skills where REORDERING
# by relevance makes sense -- "Technical Proficiency"/"Certificates" lines
# elsewhere in the same ADDITIONAL section are tools/credentials, not
# competencies to prioritize, so they're deliberately not a splice target.
_COMPETENCY_LABEL_RE = re.compile(r"^\s*core\s+competencies\s*:", re.IGNORECASE)


def is_bullet_paragraph(paragraph: Paragraph) -> bool:
    """
    A real Word bullet/numbered-list paragraph: style name "List Paragraph"
    AND a <w:numPr> element present in the paragraph's own XML. Confirmed
    structural signal from direct inspection of a real resume (2026-09-22)
    -- paragraph.text NEVER contains a literal "•"/"-" for a genuine Word
    list item (the glyph is drawn from the numbering definition, not stored
    in the run text), so a text-prefix heuristic like the PDF path uses
    would silently see zero bullets on a resume that uses real Word lists.
    """
    if paragraph.style is not None and paragraph.style.name == "List Paragraph":
        if paragraph._p.find(f".//{qn('w:numPr')}") is not None:
            return True
    # Or a bullet typed into the text itself ("• Led ..."), common in resumes built by hand.
    return bool(typed_bullet_prefix(paragraph.text))


def _is_heading(paragraph: Paragraph) -> bool:
    text = paragraph.text.strip()
    return bool(text) and not is_bullet_paragraph(paragraph) and bool(SECTION_BOUNDARY_RE.match(text))


def _looks_like_contact_line(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("@", "http", "linkedin", "(")) or any(
        ch.isdigit() for ch in text
    )


@dataclass
class JobBlock:
    title_index: int | None
    anchor_index: int
    bullet_paragraph_indices: list[int] = field(default_factory=list)


@dataclass
class Bullet:
    """One splice target: a paragraph index plus enough job context for the
    LLM prompt. `job_index` is an index into `DocxStructure.jobs`, or None
    for a summary-paragraph or competencies target."""

    paragraph_index: int
    text: str
    section: str  # "summary" | "work_experience" | "competencies"
    job_index: int | None = None


@dataclass
class DocxStructure:
    jobs: list[JobBlock] = field(default_factory=list)
    summary_paragraph_indices: list[int] = field(default_factory=list)
    competency_paragraph_index: int | None = None

    def splice_targets(self, paragraphs: list[Paragraph]) -> list[Bullet]:
        """All Bullet objects (summary + work-experience bullets +
        competencies line) in document order -- the flattened input fed to
        DocxBulletTailorer."""
        targets = [
            Bullet(paragraph_index=i, text=strip_typed_bullet(paragraphs[i].text), section="summary")
            for i in self.summary_paragraph_indices
        ]
        for job_index, job in enumerate(self.jobs):
            targets.extend(
                Bullet(
                    paragraph_index=i,
                    text=strip_typed_bullet(paragraphs[i].text),
                    section="work_experience",
                    job_index=job_index,
                )
                for i in job.bullet_paragraph_indices
            )
        if self.competency_paragraph_index is not None:
            targets.append(
                Bullet(
                    paragraph_index=self.competency_paragraph_index,
                    text=strip_typed_bullet(paragraphs[self.competency_paragraph_index].text),
                    section="competencies",
                )
            )
        targets.sort(key=lambda b: b.paragraph_index)
        return targets


def _find_work_experience_body(paragraphs: list[Paragraph]) -> tuple[int, int] | None:
    """Return (start, end) indices of the WORK EXPERIENCE section's body
    (excluding the heading itself), from the heading to the next
    SECTION_BOUNDARY_RE heading (e.g. "ADDITIONAL") or end of document."""
    start = None
    for i, paragraph in enumerate(paragraphs):
        text = paragraph.text.strip()
        if start is None and not is_bullet_paragraph(paragraph) and WORK_EXPERIENCE_HEADING_RE.match(text):
            start = i + 1
            continue
        if start is not None and _is_heading(paragraph) and not WORK_EXPERIENCE_HEADING_RE.match(text):
            return start, i
    if start is not None:
        return start, len(paragraphs)
    return None


def _find_summary_paragraph_indices(paragraphs: list[Paragraph]) -> list[int]:
    """The free-text paragraph(s) between the name/contact block and the
    first recognized section heading -- mirrors
    ResumeParser._extract_summary's boundary logic, adapted to skip the
    name/contact lines by paragraph position and shape rather than by line
    index into a flattened string."""
    first_heading_idx = None
    for i, paragraph in enumerate(paragraphs):
        if _is_heading(paragraph):
            first_heading_idx = i
            break
    if first_heading_idx is None:
        return []

    indices = []
    for i in range(first_heading_idx):
        text = paragraphs[i].text.strip()
        if not text:
            continue
        if i < _NAME_SEARCH_LINES and len(text.split()) <= 6:
            continue  # name line
        if _looks_like_contact_line(text):
            continue
        if is_bullet_paragraph(paragraphs[i]):
            continue
        indices.append(i)
    return indices


def _find_competency_paragraph_index(paragraphs: list[Paragraph]) -> int | None:
    for i, paragraph in enumerate(paragraphs):
        if is_bullet_paragraph(paragraph) and _COMPETENCY_LABEL_RE.match(strip_typed_bullet(paragraph.text).strip()):
            return i
    return None


def extract_docx_structure(doc: DocxDocument) -> DocxStructure:
    paragraphs = doc.paragraphs

    structure = DocxStructure()
    structure.summary_paragraph_indices = _find_summary_paragraph_indices(paragraphs)
    structure.competency_paragraph_index = _find_competency_paragraph_index(paragraphs)

    body_bounds = _find_work_experience_body(paragraphs)
    if body_bounds is None:
        return structure

    start, end = body_bounds
    body = paragraphs[start:end]

    blocks = find_anchor_blocks(
        body,
        get_text=lambda p: p.text,
        is_bullet=is_bullet_paragraph,
    )

    for block in blocks:
        title_index = block.title_index + start if block.title_index is not None else None
        if title_index is not None:
            title_text = paragraphs[title_index].text.strip()
            if len(title_text) < _MIN_TITLE_LENGTH:
                title_index = None

        bullet_indices = [
            start + i for i in block.body_indices if is_bullet_paragraph(body[i])
        ]

        structure.jobs.append(
            JobBlock(
                title_index=title_index,
                anchor_index=block.anchor_index + start,
                bullet_paragraph_indices=bullet_indices,
            )
        )

    return structure
