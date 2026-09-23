"""
Splices tailored bullet text into the ORIGINAL DOCX's own paragraph
objects, in place -- never generates a new document. See
docx_structure.py for how splice targets are identified.
"""

from docx.document import Document as DocxDocument

from resume_tailorer.tailorer.docx_bullet_tailorer import BulletEdit


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
