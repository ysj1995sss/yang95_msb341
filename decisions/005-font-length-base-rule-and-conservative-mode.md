# Decision 005: Detect original font/length as a base rule; add conservative tailoring mode

**Date:** 2026-09-22
**Status:** Active

## Context

The user asked for two things on the same real resume + AT&T job posting: (1) a standing base
rule that whenever a resume is uploaded, the system detects its font family and page count and
matches them in the tailored output, rather than always defaulting to a fixed 1-page target
regardless of how long the original actually is; (2) for this specific request, keep the tailoring
itself minimal -- "just change the keywords" -- rather than the existing full-rewrite behavior.

Implementing and live-verifying both surfaced several pre-existing bugs that were masked until a
dense, real 4-job resume was run through the full pipeline end to end.

## Options considered

For font/length detection:
1. **Detect and embed the literal original font.** Rejected: ties the PDF to fonts installed on
   one machine, which is exactly the ATS-safety problem base-14-only fonts (decision 003) were
   adopted to avoid.
2. **Detect the original's font family and page count, map font to the closest ATS-safe base-14
   equivalent, and resolve "preserve length" to the real detected page count.** Chosen.

For tailoring aggressiveness:
1. **Add a separate, simpler prompt path for "conservative" mode** that restricts the LLM to
   inserting missing keywords into existing bullets with the smallest edit, and skips the
   optimizer's iterative refinement loop entirely (refinement's whole purpose -- reorganize/
   rephrase for alignment -- contradicts minimal-edit intent). Chosen, threaded through
   `ResumeTailorer.tailor(conservative=...)`, `ResumeTailoringOptimizer.optimize(conservative=...)`,
   the API's `TailorRequest.conservative` field, and a Streamlit checkbox / CLI flag.

## Decision

Went with option 2 for detection and the dedicated conservative path for tailoring. Implementation
notes and bugs found/fixed along the way:

- `ResumeParser._dominant_font_name()` walks the PDF content stream's `Tf`/`Tj`/`TJ` operators in
  order to find which font was actually used to draw visible text (reportlab always pre-registers
  an unused Helvetica resource first, so "first font found" silently picked the wrong one).
- pypdf's `page.get_contents()` wraps the stream in a fresh `ContentStream` whose own `get_data()`
  reliably returned empty bytes in testing, even on a freshly opened reader -- not true randomness,
  a real bug in that code path. Fixed by reading the `/Contents` stream object's `get_data()`
  directly instead of going through `ContentStream`.
- `PDFValidator` mapped `target_length="preserve"` to a lenient 10-page ceiling, so "preserve"
  never actually enforced the real detected page count. Added `PDFGenerator.resolve_target_length()`
  so both `generate()` and `validate()` enforce the same resolved 1-page/2-page limit.
- The work-experience section-boundary regex didn't stop at an "ADDITIONAL" heading, so a real
  resume's trailing Technical Proficiency / Certificates / Core Competencies lines got swallowed
  as extra bullets under the last job, duplicating content also captured by `_extract_skills`.
- The inline-skill-label regex's stop-lookahead didn't tolerate a bullet marker before the next
  label line, so one label's capture silently swallowed every subsequent labeled line, producing
  malformed skills like `"Certificates: Prompt Engineering"` instead of splitting it properly.
  Added matching extraction for `Certificates:`/`Certifications:` lines into `certifications`.
- The LLM sometimes mirrors the internal profile-dump labels (`Location:`, `Responsibilities:`,
  `Accomplishments:`) it's shown in the prompt straight into its output, especially in conservative
  mode where it's told to change as little as possible. Added `_strip_profile_dump_labels()`
  alongside the existing Markdown-stripping defense-in-depth cleanup.
- `_SECTION_HEADING_RE` (decision 004's header reconciliation) required an exact match with no
  trailing colon, so a `"WORK EXPERIENCE:"` heading (colon included, despite the prompt's example
  showing none) was never recognized at all -- `_find_section` returned no bounds, and
  reconciliation silently skipped the whole section instead of fixing it. Fixed by making the
  trailing colon optional.

All fixes verified against the full product test suite (381 tests) and apps/api suite (18 tests),
and live-verified end to end against the user's real resume and the AT&T posting.

## What would change our mind

Content-dense resumes (4+ jobs) may not fit the original page count at any font size that's still
readable (~7.5pt is the floor found live before it becomes unprofessionally small) -- "preserve"
can only match margins/font, not shorten content. If this comes up often, a content-trimming
feature (selecting which bullets/entries to keep) would be needed, distinct from this rule.
