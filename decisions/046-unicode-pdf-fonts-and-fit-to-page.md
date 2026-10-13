# Decision 046: Unicode fonts in generated PDFs, and fitting a slightly long resume to its page limit

**Date:** 2026-10-13 (records changes made on 2026-10-12, commits `f30292e` and `371db3f`)
**Status:** Active. Partly reverses decision 005 (and the font rule in decision 003).

## Context

Two failures, both found on the builder's own resume:

- **Accents were lost.** The base-14 PDF fonts (Helvetica, Times) only cover the WinAnsi letters.
  The generator removed accents to stay inside them, so a name like "José" printed as "Jose".
  Changing someone's name on their resume is not acceptable.
- **A slightly long resume failed.** A free-form (PDF-only) resume a few lines over its 1- or
  2-page limit failed validation as "not usable". The only way out was to tailor again and hope.

## Decision

1. **Fonts:** generated PDFs embed a Unicode TrueType font from the same family as the original:
   - sans resumes use Liberation Sans or Arial;
   - serif resumes use Liberation Serif or Times New Roman.

   Liberation is installed in the server image (`packages.txt`), and Arial and Times on Windows. When
   no TrueType font is available, the generator falls back to base-14. It then keeps the WinAnsi
   letters (é, ñ, ü) instead of stripping every accent.
2. **Fit to page:** when a free-form resume is over its page limit, the generator tries tighter
   presets in small steps:
   - font size in 0.25pt steps, never below 8pt;
   - margins never below 0.4in;
   - spacing scaled down with them.

   It keeps the first preset that fits. If none fits, the resume still fails validation as before.
   Word resumes are never resized; their layout is the person's own.

## Why decision 005's objection no longer holds

Decision 005 rejected embedding "the literal original font" because it tied the PDF to whatever
fonts one machine had installed. This decision avoids that in two ways:
- The fonts are a known, open, metric-compatible pair that the server image installs on purpose,
  not whatever the person used.
- Embedding a TrueType font keeps the text extractable. The two-reader readability check
  (spec 010) still runs on every generated PDF and fails it if the text doesn't read back.

## Rejected

- **Keep base-14 and strip accents:** changes names and words on the resume.
- **Fail any resume over its page limit (no fitting):** fails resumes that are a few lines
  long for presentation reasons only.
- **Shrink without a floor:** below about 8pt type or 0.4in margins, a resume becomes hard to
  read. The floor keeps readability, page length and validation in charge, as spec 022 step 6 requires.

## Evidence

Tests in `product/tests/test_pdf_generator.py` cover the Unicode font path, the WinAnsi fallback,
fitting to the limit, and the floor.
