# Decision 003: Fix resume design fidelity (spec item 16) after real-user testing

**Date:** 2026-09-22
**Status:** Active

## Context

My first tailored resume from a real end-to-end run looked nothing like the original: literal
`**`/`*` Markdown characters throughout, every line (including "CVS Health | Woonsocket, RI")
flattened into a bullet point, my MBA (a second, in-progress degree) missing entirely, its
scholarship bullets gone, and the professional summary paragraph dropped. Spec item 16
("Preserve Resume Design") had been marked `✓ Built`, but it had never been tested against a
resume with two degrees, a summary paragraph, and an LLM that formats its own output in Markdown.

## Options considered

1. **Do nothing -- accept the output as "good enough" for an MVP.** Rejected: the output was
   actively worse-looking than not tailoring at all, and undermines trust in the whole tool.
2. **Rewrite PDFGenerator to fully re-implement the original PDF's exact layout** (columns,
   fonts, exact spacing). Rejected as over-scoped for this fix -- the real, fixable problems were
   specific and identifiable, not "the whole renderer is wrong."
3. **Fix the five specific, identified gaps**: strip Markdown (defense-in-depth, both at the
   tailoring layer and the PDF layer), detect "Employer | Location Dates" lines and render them
   bold/italic instead of flattening them, add a `summary` field to the profile schema (it had
   nowhere to live before), rewrite education extraction the same way work-experience extraction
   was already fixed (anchor on the institution line, don't drop the second entry or its bullets).

## Decision

Went with option 3. Each gap traced to a specific, fixable root cause rather than a vague
"doesn't look right": `CareerTruthProfile` had no `summary` field at all; `_extract_education`
used the same fragile per-line splitter that `_extract_work_experience` had before its own fix,
and lost the second degree and its bullets the same way; the LLM formats output in Markdown
despite never being asked to, and `PDFGenerator` has no Markdown parser, so it rendered the raw
characters and mis-read Markdown-prefixed lines as bullet points.

## What would change our mind

If a future resume format defeats the "Employer | Location Dates" pipe-and-year heuristic (e.g.
a resume that never uses a pipe separator), that heuristic would need broadening -- the fix here
is real but still pattern-based, not a general resume-layout parser.
