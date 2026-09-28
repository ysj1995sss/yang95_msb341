# Decision 018: The freeform diff's bullet extraction was too narrow, causing mass false "fabrication" flags

**Date:** 2026-09-28
**Status:** Active

## Context

First real, live end-to-end test of the tailoring pipeline (uploading a real resume, tailoring
against a real job description, through a live LLM) produced a validation **FAIL** on a resume
that contained no fabrication at all. Nearly every line derived from the resume's education
honors (Dean's List, a merit scholarship), skills list (Digital Marketing, Prompt Engineering,
etc.), and one work-experience bullet was labeled `COMPETENCY_CHANGED — NEW BULLET - should not
occur if tailoring is truthful` and rejected, even though every one of those facts existed
verbatim in the original resume.

## Root cause

`DiffGenerator._extract_bullets_from_profile()` (`product/resume_tailorer/diff_generator.py`),
which builds the freeform/PDF path's "known original content" list for pairing against the
tailored output, only ever read `job.accomplishments`. It never included `job.responsibilities`,
`education[*].notes` (honors, scholarships, GPA), `skills`, `tools`, `certifications`, or
`summary`. Any tailored bullet built from those categories had no possible match in the pairing
step and was unconditionally classified as a fabricated "added" bullet by `_compute_changes`,
regardless of how truthful it actually was.

This is the exact same gap `_profile_blob()` (the separate function that builds the fabrication-risk
check's trusted vocabulary) was already found and fixed for once before — its own docstring
documents a near-identical live bug from 2026-09-22 ("Top 1% of Class" flagged as a fabricated
metric because education notes weren't in that blob). That fix was never mirrored into
`_extract_bullets_from_profile`, the sibling function that decides `change_type` in the first
place, so the same class of bug reappeared one layer up.

Practical effect: because most real resumes have an education section and a skills section, this
bug meant the freeform/PDF tailoring path could not produce a passing validation for almost any
real resume — it was very likely close to completely broken for real use, not just an edge case.
Steps 16-20's own acceptance fixtures (Task 9, this session's earlier work) didn't catch this
because their synthetic PDF-only fixture's tailored text was hand-written directly in the test,
never round-tripped through this exact bullet-extraction/pairing path with a real LLM's output.

## Decision

Broadened `_extract_bullets_from_profile` to match `_profile_blob`'s scope: `job.accomplishments`,
`job.responsibilities`, every `education[*].notes` entry, `skills`, `tools`, `certifications`, and
`summary` (if present). Verified against a full live reproduction (real LLM call, real PDF
generation, real validation) that a resume with education honors and a skills section — the exact
shape of the resume that surfaced this live — now validates `WARNING` instead of `FAIL`, with the
only remaining finding being the expected, benign `VISUAL_CHECK_SKIPPED` (there is no true original
PDF to visually compare against on the freeform/reconstructed path; this is correct, not a bug).

`ACCEPTED_CHANGE_MISSING`, also seen in the original live failure, did not reproduce after this
fix — it was a downstream consequence of the same mis-pairing (a mislabeled change's expected text
no longer lined up with what actually appeared in the regenerated PDF), not a separate bug.

## A known, still-safe rough edge this fix did not resolve

When the number of skills/education-note items happens to be close to the number of *genuinely*
new/fabricated bullets in a tailored resume, `difflib.SequenceMatcher` can cross-pair an unrelated
skill (e.g. "Supply Chain Analytics") against a real fabricated bullet as a low-similarity
"modified" pair, instead of cleanly flagging the fabricated bullet as "added." The end-to-end
safety guarantee still holds — `build_freeform_changes`'s `AMBIGUOUS_PAIRING_THRESHOLD` (0.45)
catches the low similarity and still marks it `REJECTED`/`FAIL`, so nothing fabricated is ever
silently accepted — but the change is displayed to the reviewer with a confusing, nonsensical
"Original: Supply Chain Analytics" line instead of a clean "this bullet appears to be new" flag.
This is a review-UX quality issue, not a truthfulness violation, and is a known limitation, not
fixed in this pass (see "What would change our mind").

## Verification

- New regression tests (`product/tests/test_resume_diff.py::TestFreeformPathRecognizesTheWholeProfile`,
  4 tests) confirm: a skill, an education honor, and a responsibility restated as a tailored bullet
  are no longer flagged as fabricated; a genuinely fabricated bullet with no counterpart anywhere in
  the profile is still caught end-to-end (via `build_freeform_changes`, not just the raw diff).
- Full product suite: 689 passed (was 685 before this fix), no regressions.
- Live reproduction: real resume → real LLM tailoring call → real PDF generation → real validation,
  confirmed FAIL → WARNING for the exact resume shape that surfaced this bug.

## What would change our mind

If the skills/new-bullet cross-pairing rough edge above causes real reviewer confusion in practice
(not just a theoretical edge case), the correct fix is section-aware diffing — comparing tailored
SKILLS-section bullets only against profile skills/tools/certifications, EDUCATION-section bullets
only against education notes, and WORK EXPERIENCE bullets only against accomplishments/
responsibilities — rather than one flat list fed to a single `SequenceMatcher` pass. That is a
larger, riskier refactor of `_compute_changes` and deserves its own pass, not a quick patch bolted
onto this fix.
