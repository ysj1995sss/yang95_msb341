# Spec 017: Explain which resume and facts a one-off run uses

**Status:** Draft for builder review; no product change implemented.
**Date:** 2026-10-11
**Builds on:** specs 007, 011–012, 014–015 and decision 037.
**Evidence:** `discovery/experiments/2026-10-11-evidence-upload-and-worker-probes.md`.

## Goal and current behavior

Before paying time or model usage for tailoring, a person should know which file is selected,
which facts are used, and whether the operation changes their saved Career Profile.

`set_career_profile(..., RESUME_UPLOAD)` returns the already-loaded `FACT_VAULT` profile
instead of replacing it. The synthetic probe confirms that an uploaded distinct summary is
not the effective summary when a Career Profile is loaded. The API's one-off path passes
`career_profile=None` and `provenance=None`, but the service obtains its effective profile
through that setter. This is more subtle than the label `Use a different resume file for
this job only` suggests.

Distinguish file from facts: a one-off Word file supplies the document's bullets/layout;
PDF/free-form generation uses the effective profile for content and the file for style
extraction. Do not promise that every Word run replaces all document facts with the profile.
Current one-off bookkeeping records `profile_version=None` even when the effective profile
came from the saved Career Profile. That is a related safety mismatch, not evidence that the
uploaded file is actually an independent source of facts.

## Recommended behavior

1. Preserve saved Career Profile precedence. This spec does not silently replace or merge it
   with upload content. Show two source lines before starting: **Resume file** and **Facts**.
2. When a saved Career Profile is effective, say: `This file is for this run only. Your saved
   Career Profile remains the source of facts; uploading here does not update it. Review your
   Career Profile if these facts should change.` Also explain Word-layout versus rebuilt-PDF
   behavior without promising output fidelity for PDF uploads.
3. If no saved profile is loaded, disclose `Facts parsed from this one-off file; not saved to
   Career Profile`. Do not call these facts confirmed Career Profile facts or imply external
   verification. Retain existing safeguards for unverified proposals.
4. Add frozen, additive run metadata for file source/name/kind, effective fact source and the
   actual effective profile version when applicable. Reviews disclose their own run snapshot,
   not whatever file/profile happens to be selected later. Do not store credentials or infer
   metadata that an old review never recorded; show `Source details unavailable` for legacy.
5. Carry the actual saved profile's provenance/version when it is the effective fact source,
   including a one-off file run. Selecting another file must not turn unconfirmed saved facts
   into confirmed facts or suppress stale-profile protection. If no saved profile is used,
   keep an independent file snapshot and do not falsely couple it to later Career Profile edits.
6. Provide the existing `Use my Career Profile resume instead` control in both apps. Removing
   the one-off file changes the next run's source, not the source or facts of an existing review.
7. Preserve batch policy: batches use the Career Profile resume and refuse an active one-off
   source until removed. Explain the reason beside the source controls and existing 409.

Keep wording and source resolution shared where practical. API fields are additive; the
master resume, Career Profile, current job and old reviews are never changed by disclosure.

## Alternatives

- **Recommended:** expose actual precedence and fix source/provenance bookkeeping, retaining
  established canonical-profile behavior.
- **Rejected here:** automatically replace the profile with every uploaded file; that erases
  corrected facts and changes the product's source-of-truth policy.
- **Deferred:** a new selectable override/merge workflow. That requires its own approval,
  confirmation flow and conflict handling, not misleading copy over an unchanged implementation.

## Expected files

`session_profile.py`, `tailoring_service.py`, shared source labels/resolution, API
`workspace/tailor_router.py`, web Tailor controls/types, Streamlit `pages/5_Tailor.py`, and tests.
No new dependency, upload parser, full redesign or source-of-truth migration.

## Acceptance and definition of done

- [ ] Saved profile plus different Word/PDF upload shows both sources before the run.
- [ ] Different synthetic summary/tool facts never silently overwrite the saved profile.
- [ ] Effective profile/provenance/version match the disclosure and the saved run snapshot.
- [ ] An unconfirmed saved fact remains unconfirmed; a later effective-profile edit flags the run.
- [ ] No-profile one-off runs are labeled parsed, not confirmed; their file snapshot survives restart.
- [ ] Removal/another upload affects the next run only; batch refusal remains explained.
- [ ] Both UIs/API match; legacy reviews load with unknown source details rather than guesses.
- [ ] Synthetic browser checks and full suites pass; real/seeded/stubbed runs are labeled honestly.

**Review gate:** approve the spec before the detailed plan and code. This is clarification plus
accurate safety bookkeeping, not authorization to build a fact override workflow.
