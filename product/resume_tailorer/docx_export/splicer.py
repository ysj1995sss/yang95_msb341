"""
Splices tailored bullet text into the ORIGINAL DOCX's own paragraph
objects, in place -- never generates a new document. See
docx_structure.py for how splice targets are identified.
"""

from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph

from resume_tailorer.artifacts.models import FindingCategory, FindingSeverity, ValidationFinding
from resume_tailorer.tailorer.docx_bullet_tailorer import BulletEdit


def _run_format(run) -> tuple:
    return (
        run.bold,
        run.italic,
        run.underline,
        run.font.name,
        run.font.size.pt if run.font.size is not None else None,
    )


def inline_formatting_findings(
    paragraph: Paragraph, changed: bool
) -> list[ValidationFinding]:
    """Warn when a rewrite necessarily collapses genuinely different run styles."""
    if not changed:
        return []
    formats = {_run_format(run) for run in paragraph.runs if run.text}
    if len(formats) <= 1:
        return []
    return [
        ValidationFinding(
            "INLINE_FORMATTING_SIMPLIFIED",
            FindingSeverity.WARNING,
            FindingCategory.VISUAL,
            "A rewritten paragraph contained mixed inline formatting; the first run's style was preserved.",
        )
    ]


def splice_bullets_into_docx(doc: DocxDocument, edits: list[BulletEdit]) -> DocxDocument:
    """
    For each edit with changed=True, replace doc.paragraphs[edit.paragraph_index]'s
    text using the run[0]-keep-rest-delete technique: keep run[0] (its own
    font/size/bold/italic, and the paragraph's own style/indentation/
    numbering/tabs, are all untouched by construction -- nothing about the
    paragraph object itself is replaced or recreated), set its text to the
    new content, and delete every other run in the paragraph. Word already
    fragments a single bullet across multiple identically-formatted runs
    from edit history (confirmed on a real resume), so this is safe for the
    vast majority of bullets.

    Edits with changed=False are skipped entirely -- the paragraph is never
    touched, so it stays byte-identical (same run boundaries, same run
    XML) to the original, not just textually equal.

    Accepted, documented limitation: a bullet with genuine inline
    mid-sentence formatting (found once on a real resume: one bolded word
    inside an otherwise-plain bullet) loses that inline formatting if that
    specific bullet is rewritten -- not solved here; word-level run
    remapping is disproportionate complexity for a rare cosmetic edge case.
    """
    for edit in edits:
        if not edit.changed:
            continue
        paragraph = doc.paragraphs[edit.paragraph_index]
        runs = paragraph.runs
        if not runs:
            paragraph.add_run(edit.new_text)
            continue
        runs[0].text = edit.new_text
        for run in runs[1:]:
            run._element.getparent().remove(run._element)
    return doc


def save_docx(doc: DocxDocument, path: str) -> None:
    doc.save(path)
