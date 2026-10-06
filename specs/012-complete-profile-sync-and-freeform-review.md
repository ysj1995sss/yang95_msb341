# Spec 012: Complete Word profile sync and reviewable free-form section edits

**Status:** Implemented and locally verified on 2026-10-06; see decision 034 and the supervised-run record. Check CI separately after push.
**Date:** 2026-10-06
**Builds on:** specs 010–011 and decisions 032–033

## Problem and evidence

The Career Profile is the source of truth, but `docx_export/profile_sync.py` currently updates
only work-history bullets. A corrected title, date, summary, skills line or education entry can
remain stale in the Word file that Tailor uses. The Word supervised run in
`discovery/experiments/2026-10-spec-011-supervised-runs.md` proved that a new bullet reaches the
file; it did not test these other fields.

On the PDF-upload path, `artifacts/changes.py::build_freeform_changes` asks `DiffGenerator` for
bullets only. Its global bullet matcher should stay as decided in decision 018, but it cannot
produce an independent review choice for a changed summary or skills line. The supervised PDF
run added “project management” to the summary without a review row. It also observed a skills
line represented as “SQL → (empty)” when its text moved.

## Goal and user workflow

After a person edits their Career Profile and tailors its Word resume, the run makes a copy of
the original file, brings identifiable profile fields into that copy in place, and reports
exactly what changed or could not be placed. The person reviews the proposed job-specific
changes afterward. On a PDF/free-form run, summary and skills-line edits appear alongside
bullet edits as separate choices: accept, reject, restore or manually edit. Rebuilding the
artifact applies those choices without another model call.

Success means that a successful run never silently delivers an old, contradictory profile fact
in Word, and every meaningful free-form summary/skills edit can be decided separately. Neither
path may introduce unsupported qualifications or submit an application.

## A. Sync represented Career Profile facts into Word

1. Keep the original DOCX and work on a copy. If no field changes, return the original bytes
   unchanged. Keep paragraph order, section order, styles, numbering, margins and unchanged run
   XML. Rewrite a changed paragraph in place using `docx_export/splicer.py`'s run-preserving
   technique. The existing bullet add/remove behavior remains.
2. Cover the profile's resume-bearing fields where the Word layout provides a clear home:
   contact details; professional summary; employer, role title, dates and location; work
   bullets; skills and tools; education; and certifications. Do not treat goals, preferences or
   application answers as resume content. Never add a new section or move facts to an arbitrary
   location to claim full coverage.
3. Match work roles one-to-one. Prefer normalized employer **and** title. If the title changed,
   a unique employer plus a non-conflicting date/role anchor may identify the role. With two
   roles at one employer, or both title and dates changed, do not guess. Match education by an
   unambiguous institution/degree combination, with a unique-institution fallback for a degree
   correction. Preserve the file's order even if the profile order differs.
4. Use structural, section-aware targets for summary and skills rather than global text
   replacement. Update a skills/tools line only when it is clearly identified; preserve its
   label and any unrelated text that cannot be mapped. Keep education and certification
   formatting; do not collapse several entries into one paragraph. If a field is absent or
   structurally ambiguous, do not invent a placement.
5. Extend `SyncResult` with defaulted, structured details for fields updated and fields not
   placed (field, profile value or safe description, reason, and whether the mismatch blocks
   this Word run). Keep the existing bullet counts and `summary` behavior. Surface the same
   plain-language report through the existing Tailor `sync_summary` in both apps. A stale,
   contradictory identity, role title, date, education or credential must block a distributable
   artifact until resolved; a newly added fact with no safe place may be omitted with a clear
   warning and a suggestion to edit the Word template or use the rebuilt-layout path.
6. The working profile may be reordered for the Word bullet tailorer as today, but the stored
   Career Profile and its provenance stay in their original order. Nothing is written back to
   the uploaded master file or the Career Profile by this sync.

## B. Review summary and skills changes on the PDF/free-form path

1. Identify summary and skills lines by section before building review changes. Compare the
   tailored section with the Career Profile's corresponding source facts. A moved or wrapped
   skills line remains one logical section change, never a spurious `SQL → (empty)` bullet
   pairing. Preserve the existing global greedy bullet pairing algorithm; section extraction
   may exclude summary/skills from its input but must not alter how work bullets pair.
2. Emit separate `ResumeChange` rows for each meaningful summary or skills-line edit, with
   distinct, stable `freeform:summary:*` and `freeform:skills:*` IDs, explicit section labels,
   source/proposed text and evidence. Do not duplicate a section change in the bullet queue.
   No change means no review row. If a section cannot be identified confidently, report the
   ambiguity rather than guessing which line changed.
3. Run the existing fabrication, semantic-drift and
   `requirement_review.introduced_unsupported` checks on proposed section edits. The same
   unsupported-term guard applies to manual edits before rebuilding. A skills-list mention
   cannot become an experience claim. A failed proposal remains reviewable but cannot produce
   a downloadable artifact while included.
4. Regenerate from the saved baseline text, without another model call. Apply new section
   changes by a section-specific anchor/occurrence, not the first matching string anywhere in
   the document. If the anchor is missing or ambiguous, fail visibly rather than silently
   changing another occurrence. Preserve legacy bullet-change behavior for saved reviews.
5. Add an additive section label to the shared review view/API so Next.js and Streamlit call
   these “Summary” and “Skills” changes. Keep existing API fields, review decisions and saved
   format-2 reviews working; any new dataclass field has a default. Do not rename stored enum
   values or change existing change IDs in old reviews.

## Approach and trade-offs

- **Recommended: safe in-place Word edits plus section-aware free-form review.** Reuses the
  existing DOCX splicer, review model and regeneration pipeline; preserves formatting and
  avoids fabricating placements. Ambiguous templates require a visible human correction.
- **Rejected: rebuild the Word file from the profile.** It loses the person's layout and
  bullet order, against decision 006.
- **Rejected: one whole-document free-form diff.** It cannot give a reliable independent
  decision for summary versus skills and could replace the wrong repeated text.

## Compatibility, safety and scope

- Saved `review_store` format 2, including
  `product/tests/fixtures/ats/legacy_review_format2.json`, still loads and regenerates.
- `/v2` fields and the legacy `/tailor` API remain; additive review labels are allowed.
- Requirement review, local readability checks, page-length and validation gates, the
  unsupported-claim guards, and the hard no-submission gate remain unchanged.
- No new dependency, account, deployment, paid model or real user data is needed.
- Batch resume/restart behavior, per-fact confirmation, vocabulary expansion, and retiring
  Streamlit belong to later specs.

## Expected files and build sequence after approval

1. Add synthetic Word fixtures and failing tests in `product/tests/test_profile_sync.py` for
   the new field targets, unambiguous/ambiguous matching, formatting and missing placements;
   then extend `product/resume_tailorer/docx_export/profile_sync.py` and, only as needed, its
   structural helper in `parsers/docx_structure.py`.
2. Add failing tests for section extraction, decisions and regeneration in the product
   artifact/review tests; then extend `artifacts/changes.py`, `artifacts/regeneration.py`,
   `tailoring_service.py`, and the shared review view. Keep `DiffGenerator._compute_changes`
   untouched.
3. Add API and two-frontend tests for the sync report and labelled review rows; update the
   `/v2` review payload, `apps/web` Tailor view and retained Streamlit Tailor view only where
   needed. Write a decision record for the final matching and fail-closed rules.
4. Run all product, API, web lint/types and Playwright suites. Perform one supervised real-model
   run with synthetic Word and PDF resumes that exercise the new fields and review decisions;
   record before/after, rejected edits, validation and unresolved placements in
   `discovery/experiments/`. Then make small verified commits and push only after approval.

## Acceptance tests and definition of done

- [x] A Word profile edit to role title/date, summary, skills/tools and education appears in
      the copied Word file and final PDF; untouched paragraphs retain their formatting.
- [x] Reordered profile roles, two roles at one employer, a changed title and a missing section
      are handled without placing a fact under the wrong role; every unplaced fact is reported.
- [x] A conflicting stale title, date, education or credential cannot reach Apply as a passing
      artifact.
- [x] Summary and skills edits in a PDF/free-form run are separate review choices; accepting,
      rejecting and manually editing each produces the expected text after reload/rebuild.
- [x] A wrapped or moved skills line is not paired with an empty bullet; repeated wording in
      another section is not replaced by a summary/skills decision.
- [x] Unsupported terms in proposed or manual section edits are blocked; the final PDF passes
      the existing readability and content checks.
- [x] Legacy format-2 reviews load; the old API fields and both UIs continue to work.
- [ ] Product, API, lint/types and 20+ Playwright tests pass; a supervised real-model run is
      recorded. No application is submitted.

**Review gate:** The builder approved this spec on 2026-10-06. Review the detailed implementation
plans before product-code changes, dependency changes, commits or pushing to `main`.
