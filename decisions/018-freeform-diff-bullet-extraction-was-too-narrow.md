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

## Update (same day): the rough edge below turned out to hit real resumes immediately, and was fixed

The "known, still-safe rough edge" originally documented in this section was NOT a theoretical
edge case — it hit the very next real resume tested (same day, one retry later), producing the
same class of false fabrication flag this decision already fixed once. The user's real resume
(BYU MBA, ~17 skills, 3-4 work-experience bullets, education honors) showed FIVE truthful, lightly
reworded bullets each appearing TWICE: once as a spurious `COMPETENCY_CHANGED — NEW BULLET`
("added", no original) and once as a spurious `CONDENSED` removal of the ORIGINAL wording — the
system had correctly recognized both halves of the same edit individually, but never recognized
them as the same bullet.

**Root cause of the split:** `_compute_changes`'s `"replace"` opcode branch pairs bullets by
similarity, but only WITHIN its own opcode block's slice
(`orig_slice = original[i1:i2]` / `tail_slice = tailored[j1:j2]`) — never against the full lists.
`difflib.SequenceMatcher`'s opcode partitioning is position-sensitive: because the tailored
document's natural section order (Education, then Experience, then Skills) differs from the
profile's internal storage order (job-by-job, then education, then skills — the order
`_extract_bullets_from_profile` emits in), a bullet's original and reworded versions can land in
DIFFERENT opcode blocks. One block reports the original as `"removed"` (no match in ITS slice); a
different block reports the reworded version as `"added"` (no match in ITS slice) — even though
they're obviously the same bullet with a clause appended.

A second, related symptom showed up under stress-testing with a larger, more realistic profile
(~24 original items across categories): a `"replace"` block's greedy pairing has NO minimum-quality
floor, so when a block happens to mix unrelated categories (e.g. skills interleaved with
work-experience bullets because of how the surrounding content lined up), it will confidently pair
e.g. `"Product Marketing"` against an unrelated new sentence at 13-25% similarity instead of
recognizing either as unmatched.

**Fix:** added `DiffGenerator._reconcile_cross_block_matches`, a global second pass over the
WHOLE `changes` list (not scoped to one opcode block). It pools every `"removed"`/`"added"` entry,
plus the two halves of any `"modified"`/`"rephrased"` pair below a trust floor
(`_MIN_TRUSTED_PAIR_SIMILARITY = 0.4`), and searches for a near-certain match
(`_RESCUE_SIMILARITY_THRESHOLD = 0.75`) for each, regardless of which opcode block produced it. A
low-confidence pair is only overridden when something clearly better is found elsewhere — a resume
with only one bullet on each side has no better option available, so its original (if imperfect)
pairing is kept rather than discarded, preserving the semantic-drift/length-delta checks that only
run on a real original/tailored pair.

A third, previously undiscovered bug in the SAME investigation: `validate_pdf_content`'s
`METRIC_MISSING` check built its "metrics that must survive" set from the profile's ENTIRE
work-experience text, unconditionally — so a metric-bearing bullet the user explicitly reviewed
and accepted condensing away (category `CONDENSED`, a visible, reviewable change) still made
validation FAIL, as if the metric had silently vanished. Any real resume needing even one
metric-bearing bullet trimmed for space would have hit this. Fixed by excluding a bullet's text
from the expected-metrics source when it has a corresponding `CONDENSED`-category change in
`accepted_changes` — an explicit, reviewed removal is not a silent one.

Re-verified end to end against the exact resume shape that surfaced all of this (real profile
structure, real tailored text, real PDF generation, real validation): **FAIL → clean WARNING**,
with only the expected, benign `VISUAL_CHECK_SKIPPED` remaining.

## Verification

- New regression tests (`product/tests/test_resume_diff.py::TestFreeformPathRecognizesTheWholeProfile`,
  6 tests after the update) confirm: a skill, an education honor, and a responsibility restated as
  a tailored bullet are no longer flagged as fabricated; a bullet split across opcode blocks is
  reconciled into one rephrased/modified change; an exact duplicate split across blocks is
  recognized as unchanged; a genuinely fabricated bullet with no counterpart anywhere in the
  profile is still caught end-to-end (via `build_freeform_changes`, not just the raw diff). Two new
  tests in `test_pdf_content_validator.py` cover the `METRIC_MISSING`/`CONDENSED` fix in both
  directions (legitimately condensed metric not flagged; a genuinely unexplained missing metric
  still is).
- Full product suite: 693 passed (was 685 before this whole investigation), no regressions. One
  pre-existing test (`test_reorder_plus_reword_plus_new_bullet_not_scrambled`) was updated: it had
  been pinning down the OLD, worse behavior (a pure bullet move showing as two spurious unpaired
  remove/add entries) as if it were a deliberate design choice, rather than the strictly-better
  "recognized as the same bullet" outcome the reconciliation pass now produces.
- Live reproduction: real profile structure → tailored text shaped like the real resume that
  surfaced this → real PDF generation → real validation, confirmed FAIL → clean WARNING.

## What would change our mind

If a future live test still finds a cross-category pairing that neither the reconciliation pass's
0.75 rescue threshold nor the 0.4 trust floor catches correctly, the next step is section-aware
diffing — comparing tailored SKILLS-section bullets only against profile skills/tools/
certifications, EDUCATION-section bullets only against education notes, and WORK EXPERIENCE
bullets only against accomplishments/responsibilities — rather than one flat list fed to a single
`SequenceMatcher` pass. That would need real section-header detection in the tailored text (the
DOCX path's anchor-detection logic is the closest existing precedent) and is a larger, riskier
refactor than this pass; only worth it if the cheaper reconciliation-pass fix proves insufficient
against further real-world testing.
