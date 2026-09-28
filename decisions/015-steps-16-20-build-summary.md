# Decision 015: Steps 16-20 build (Tasks 6-9) — summary

**Date:** 2026-09-27
**Status:** Active

## Context

Decision 014 chose one shared validated-artifact pipeline for Steps 16-20 over patching Streamlit
and FastAPI independently. Codex built Tasks 1-5 (domain models, DOCX layout signatures, visual
PDF validation, the `ValidatedArtifactPipeline` orchestration shell, the unified report/change
models) on `codex/validated-artifacts-steps-16-20` and handed off at commit `15343c8` with a clean
tree, 582 product tests and 39 API tests passing. This session picked up Tasks 6-9, a whole-branch
review, and integration.

## Decision

Built Tasks 6-9 in order, each committed and tested independently, followed by one whole-branch
review and a fix pass before integrating into `main`.

- **Task 6 (persistence):** `TailoringRun`/`TailoredArtifact` SQLAlchemy models, additive SQLite
  migrations, `TailoringRunStore` (create/update a run, save a new artifact version, ownership-
  scoped reads). `supersedes_artifact_id` points backward to what a new version replaces; existing
  rows are never mutated.
- **Task 7 (API review/regenerate/download flow):** `POST /tailor/preview` now persists a run and
  returns the new report/validation/changes/artifacts fields additively, alongside every existing
  field unchanged. New endpoints: `GET /tailor/runs/{id}`, `PATCH /tailor/runs/{id}/changes`
  (accept/reject/restore/manually edit, with the same safety checks a manual edit needs),
  `POST /tailor/runs/{id}/regenerate` (rebuilds from the immutable original every time, never
  re-invokes the tailorer), `GET /tailor/artifacts/{id}` (ownership-checked, blocks `FAIL`
  downloads with 409). `finalize_docx_edits` was extracted from `run_docx_tailoring_pipeline` so
  regeneration shares the exact same splice/validate code the initial tailoring pass uses, instead
  of a second, parallel implementation.
- **Task 8 (Streamlit migration):** `product/resume_tailorer/app.py` now dispatches a DOCX upload
  to `run_docx_tailoring_pipeline` (previously it ALWAYS used the freeform reconstruction path,
  regardless of upload type -- exactly the fragmentation decision 014 named). Added
  `resume_tailorer/ui/artifact_review.py`, pure Streamlit-free state helpers (`visible_changes`,
  `build_review_payload`) for the new accept/reject/restore/manual-edit review controls, applied
  locally via `resume_tailorer.artifacts.regeneration` (no API call -- Streamlit has no accounts of
  its own to route through). Downloads gate on the final validation status.
- **Task 9 (acceptance, docs, verification):** Two anonymized fixtures (`sample_docx_resume.docx`,
  `sample_pdf_only_resume.pdf` -- fictitious candidates, no real PII) and
  `test_artifact_acceptance.py` exercising jobs/education/contact/metrics survival, zero
  unsupported claims, reject/manual-edit regeneration, and `RECONSTRUCTED` labeling end-to-end
  against them. Found and fixed a real, unrelated pre-existing bug while building these fixtures
  (see below).

## Bug found while building Task 9's fixtures

`validate_pdf_content` (`product/resume_tailorer/pdf/content_validator.py`) passed
`education.year` -- typed `int` on `EducationEntry` -- directly into a helper that calls
`unicodedata.normalize()` on it, crashing with a `TypeError` instead of returning an
`EDUCATION_DATE_MISSING` finding, for every resume with a real parsed graduation year. The
existing test fixture for this file happened to pass a string in that slot, masking the bug.
Fixed by coercing to `str()` before the check; added a regression test.

## Whole-branch review findings and resolutions

One review pass across the full branch diff (all of Tasks 1-9) against the spec's non-negotiable
rules, requested per the sprint plan's execution decision. Three findings, most severe first:

1. **Manual edits silently dropped on freeform regeneration -- FIXED.** `review_changes` (API) and
   `app.py`'s regenerate handler overwrote `ResumeChange.proposed_text` with the validated manual
   text in place, destroying the AI's original wording that `apply_dispositions_to_text` needs to
   find-and-replace in the run's baseline text. The substitution was always skipped, so a manual
   edit never appeared in the regenerated document (the DOCX path was unaffected -- it addresses
   paragraphs by index, not by string search). Fixed by adding `ResumeChange.manual_text` as a
   field distinct from `proposed_text` (which now always stays the untouched AI proposal).
   Regression tests added at both the product layer (`test_artifact_regeneration.py`) and the API
   layer (`test_tailor_review.py`); each was confirmed to fail against the pre-fix code before the
   fix was verified.
2. **Regeneration used the user's CURRENT profile, not the run's immutable snapshot -- FIXED.**
   `review_changes` and `regenerate` re-fetched `db.get(Profile, user.id)` instead of the profile
   that was actually used to propose the run's changes, even though `TailoringRun` already stored
   a `profile_snapshot_hash` explicitly meant to detect this kind of drift (and the model's own
   docstring already promised "this run's own tailoring must always regenerate against the EXACT
   inputs it was proposed against"). A `PUT /profile` edit between preview and regenerate would
   silently change what a manual edit's fabrication check considers grounded, or feed a changed
   profile into re-splicing. Fixed by adding `TailoringRun.profile_snapshot_json` (additive
   migration) and pointing both endpoints at it. Regression test confirms a manual edit that's only
   grounded in the ORIGINAL profile still passes review after the live profile is changed to remove
   that grounding.
3. **The bounded one-retry correction loop is unwired -- NOT FIXED, documented instead.**
   `ValidatedArtifactPipeline` (Task 4, Codex) correctly implements and unit-tests the "at most one
   automatic correction, only for `PAGE_COUNT_CHANGED`/`TEXT_OVERFLOW`/`CLIPPED_TEXT`" policy spec
   002 section 8.5 requires -- but nothing outside its own test file ever imports it. Both adapters
   call `run_docx_tailoring_pipeline`/`PDFGenerator`/`PDFValidator` directly. Fixing the WIRING
   alone would not fix the underlying gap: `ValidatedArtifactPipeline.corrector` has no default
   implementation, because the actual correction behavior the spec describes --
   "request condensation only within already-approved claims and affected editable paragraphs" --
   is a real content-condensation feature (almost certainly another LLM call to shorten a specific
   paragraph without changing its meaning) that has never been built anywhere in this codebase.
   Wiring in a no-op corrector would be pure theater (retry with an identical request produces an
   identical failure); building a real one is new functionality, not a bug fix, and a material
   scope expansion beyond what this review-fix pass should do unplanned. See "Known limitations."

No other issues were found across ownership checks, artifact immutability/versioning, Candidate
Fit isolation, DOCX structural invariants, FAIL-blocks-download behavior, or PII in fixtures --
reported explicitly as checked, not silently passed over.

## Final verification

- Product suite: 610 passed (Codex's 582 baseline + 28 from Tasks 6-9 and the content-validator
  regression test).
- API suite: 60 passed (Codex's 39 baseline + 21 from Tasks 6-9 and the review-fix regression
  tests).
- No live LLM call was made anywhere in this session's automated tests: no `LLM_API_KEY`,
  `ANTHROPIC_API_KEY`, or `.env` file was present in this environment (checked explicitly). Every
  test that would otherwise need a real model call uses a deterministic stand-in, matching the
  precedent `product/tests/test_integration.py` already established for the same constraint.
  "Live verification" for this session's work is therefore the full acceptance suite run against
  real (anonymized) resume files through the real, non-mocked pipeline code (Task 9) -- not a
  network-dependent smoke test that could not have run here regardless.
- Word/`docx2pdf` is not installed in this environment, confirmed via the existing
  `DocxConversionUnavailable` fallback path exercised in `test_artifact_acceptance.py`: DOCX bytes
  are still produced, `conversion_available` is `False`, no crash, no page count claimed.

## Known limitations, stated honestly

- **The bounded correction/condensation loop is not wired into production.** See finding 3 above.
  Building it needs: an actual condensation prompt/LLM call scoped to "shorten this specific
  paragraph without changing its claims," a `CorrectionCallback` implementation using it, and
  wiring that callback into both `apps/api/app/tailor/router.py` and
  `product/resume_tailorer/app.py`. The orchestration shell and its bounded-retry test coverage
  already exist and don't need to be rebuilt.
- **Candidate Fit is not surfaced in Streamlit.** `product/resume_tailorer/app.py` reports
  `candidate_fit=None` honestly rather than fabricating a number -- `CandidateFitScorer` needs a
  structured `JobPosting`, which Streamlit's raw pasted-text job description input doesn't produce.
  The API path recomputes fit from the profile/job pair only (never from tailored output), which is
  correct per the spec.
- **No real scraped job posting was used for the Task 9 acceptance fixtures.** Both fixtures pair
  with the same synthetic-but-realistic postings `product/tests/fixtures/real_job_descriptions.py`
  already uses and documents this same constraint for -- actual scraped postings were not
  accessible in this environment, for either session.
- **The freeform/PDF-only path's known gaps from decision 013 (no repair loop, no hard length
  gate) are unchanged by this work** -- Steps 16-20 added validated artifact packaging and review
  around both tailoring paths; it did not change the tailoring paths' own generation quality.

## What would change our mind

If real usage surfaces DOCX or freeform artifacts that fail validation for a genuinely correctable
overflow reason often enough to matter, build the real condensation corrector next -- the
orchestration shell in `product/resume_tailorer/artifacts/pipeline.py` is the template, not
something to redesign. If a future session's whole-branch review finds the same "spec describes a
component that was never actually built behind a well-tested shell" pattern again, that's a signal
to add an explicit acceptance-criteria checklist step (not just tests passing) before any task is
marked done.
