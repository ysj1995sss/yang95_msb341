"""
Splices tailored bullet text into the ORIGINAL DOCX's own paragraph
objects, in place -- never generates a new document. See
docx_structure.py for how splice targets are identified.
"""

from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph

from resume_tailorer.parsers.bullets import strip_typed_bullet, typed_bullet_prefix

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


def _marker_runs(paragraph: Paragraph) -> int:
    """How many leading runs hold exactly a typed bullet marker ("•" + tab), or 0.

    Those runs keep their own font (often Symbol) and are never rewritten."""
    prefix = typed_bullet_prefix(paragraph.text)
    if not prefix:
        return 0
    seen = ""
    for count, run in enumerate(paragraph.runs, start=1):
        seen += run.text
        if seen == prefix:
            return count
        if len(seen) >= len(prefix):
            return 0
    return 0


def inline_formatting_findings(
    paragraph: Paragraph, changed: bool
) -> list[ValidationFinding]:
    """Warn when a rewrite necessarily collapses genuinely different run styles."""
    if not changed:
        return []
    formats = {_run_format(run) for run in paragraph.runs[_marker_runs(paragraph):] if run.text}
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
        prefix = typed_bullet_prefix(paragraph.text)
        new_text = strip_typed_bullet(edit.new_text)
        keep = _marker_runs(paragraph)
        runs = paragraph.runs
        if keep and len(runs) > keep:
            target, rest = runs[keep], runs[keep + 1:]
        elif runs:
            # The typed marker shares a run with the text (or there is none): rewrite it in place.
            new_text = prefix + new_text
            target, rest = runs[0], runs[1:]
        else:
            paragraph.add_run(new_text)
            continue
        target.text = new_text
        for run in rest:
            run._element.getparent().remove(run._element)
    return doc


def save_docx(doc: DocxDocument, path: str) -> None:
    doc.save(path)
