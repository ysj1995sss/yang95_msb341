# Decision 006: Splice tailored text into the original DOCX instead of regenerating a PDF

**Date:** 2026-09-22
**Status:** Active

## Context

A real user tested the tailored PDF output and gave a precise architectural critique: the
pipeline was `extract text -> ask AI to write a new resume -> generate a new PDF from scratch`,
which is why fonts, margins, spacing, and page count drifted from the original -- it
reconstructs the document instead of editing it. They proposed the correct fix: for a DOCX
original, preserve its paragraph styles/runs/tabs/margins/bullet formatting unchanged, and let
the AI modify only the permitted text inside those containers, then export to PDF.

## Options considered

1. **Keep improving the from-scratch reportlab pipeline** (tighter fonts, better header
   heuristics, etc. -- most of this session's earlier work). Rejected as the long-term answer:
   decision 003 already tried this and explicitly scoped out "fully re-implement the original
   PDF's exact layout" as over-scoped; the user's critique shows that scope boundary was wrong
   for anyone whose original is a DOCX, since a DOCX's real layout can be preserved exactly
   rather than approximated.
2. **Splice into the original DOCX's own paragraphs, for DOCX originals only.** Chosen.

## Decision

Went with option 2. Because splicing only ever replaces TEXT inside pre-existing paragraph
objects -- never adding, removing, or reordering one -- section names, company count, education
count, and contact fields become structurally impossible to violate, not things checked and
rejected after the fact. Font, margin, indentation, tabs, and bullet numbering are untouched XML
on every paragraph not edited, and preserved on run[0] of every paragraph that is. The only two
things that can actually drift are page count (Word's own line-wrapping could push a rewritten
bullet onto an extra line) and per-bullet fabrication/length risk in the new text -- both are
checked explicitly (docx2pdf round-trip page-count comparison; per-bullet fabrication and
length-delta checks), rather than trying to enumerate every way a from-scratch render could go
wrong.

Implementation: `product/resume_tailorer/parsers/docx_structure.py` walks `doc.paragraphs`
directly (reusing the same anchor-by-year algorithm as the PDF-text parser, extracted into
`anchor_detection.py` so the two never drift apart) to find WORK EXPERIENCE bullets and the
PROFESSIONAL SUMMARY paragraph as splice targets -- education, skills, certifications, and every
header/contact paragraph are never touched. `docx_bullet_tailorer.py` asks the LLM for structured
per-bullet JSON edits (not freeform prose) so the result can be spliced directly.
`docx_export/splicer.py` replaces a changed bullet's text via its first run (keeping that run's
own formatting) and deletes the rest -- Word already fragments a single bullet across
identically-formatted runs from edit history, so this is safe for the vast majority of bullets. A
real, reproducible `docx2pdf`/Word-COM quirk was found and fixed along the way: converting two
documents back-to-back in the same process reliably fails the second time
(`AttributeError: Open.SaveAs`) because `word.Quit()` from the first call hasn't fully released
before the second call reconnects via the Running Object Table -- a short retry-with-delay in
`docx_export/converter.py` fixes it reliably.

PDF-only originals are unaffected: there is no editable structure to preserve for those, so they
keep the existing reportlab from-scratch pipeline exactly as before, selected by
`ResumeFile.filename`'s extension in `apps/api/app/tailor/router.py`.

## What would change our mind

If a resume's content genuinely can't fit the original page count even with keyword-only bullet
edits (found live already: a dense 4-job resume needed ~7.5pt font to fit 1 page, too small to be
professional), splicing alone can't fix that -- a content-trimming feature (choosing which
bullets/entries to drop) would be a distinct, separate piece of work, not an extension of this
one. If `docx2pdf`'s Word-COM automation turns out to be unreliable outside this single-user,
local, Windows-with-Word setup (e.g. concurrent requests contending for the same Word instance),
the page-count hard gate would need to degrade to a soft warning rather than a blocking check.
