# Decision 007: Revise Steps 1-3 (resume upload, Career Truth Profile, job search goals) per audit

**Date:** 2026-09-23
**Status:** Active

## Context

The user supplied a detailed revision spec for Steps 1-3 of the product, with an explicit
process: audit the existing codebase first, produce a gap-analysis table, then make the smallest
safe additive changes, reusing existing models/routes/schemas wherever possible rather than
rebuilding. Three parallel audits (resume storage, Career Truth Profile, job search goals)
confirmed the actual state before any code changed.

## Key audit finding that changed scope

`apps/api` already had a working, tested-by-nothing-but-functional `Goals`/`JobGoals`
single-profile backend (`GET`/`PUT /goals`) covering most of the spec's required job-search-goal
fields under different names (`titles` vs `target_roles`, `exclude_companies` vs
`excluded_companies`, etc.) — this was not part of any prior session's work and wasn't previously
known to be there. This changed Step 3 from "build from scratch" to "the single real gap is
multi-profile support," since `Goals` is structurally one-row-per-user and cannot hold more than
one named profile.

## Decisions per step

**Step 1 (resume upload):** Added additive columns to `ResumeFile` (stable `id`, `sha256`,
`size_bytes`, `version`) and a new `ResumeFileVersion` table that archives the row a re-upload
replaces, so history is no longer silently lost -- `ResumeFile` itself still holds only the one
current resume per user, so every existing reader of it (tailor pipeline, style-hint extraction)
is unaffected. Added file-size/empty-file validation and "EMPLOYMENT" as a recognized section
heading. Deliberately did NOT attempt deep PDF style-metadata extraction (font size, bold/italic,
margins, spacing, horizontal rules, tabs, per-bullet line count) -- the DOCX master-template
splice pipeline (decision 006) already solves true visual fidelity for the case that matters most
(DOCX originals) at a much deeper level than incremental PDF metadata extraction would, and
building a general PDF layout parser is a large, separate undertaking not justified by this pass.

**Step 2 (Career Truth Profile):** Added a `verification_json` column on `Profile` and a small,
purpose-built diffing module (`app/profile/verification.py`) that tags a fact `user_verified`
when a `PUT /profile` call introduces it (new/changed skill, contact field, education entry, or
work-experience bullet) and leaves everything else `resume_verified` by default -- correct by
construction, since parsing never invents content (no LLM runs at parse time; that only happens
during tailoring, already covered by the separate fabrication-risk/unsupported-claims machinery).
Re-uploading a resume resets the verification map, since prior edits belonged to the old document.
Built a genuinely new UI screen (`product/resume_tailorer/pages/1_Profile_Review.py`) against the
apps/api backend specifically, since that's where auth and persistence actually live -- the
existing Streamlit app talks to the tailoring engine in-process with no login concept at all.
Live-verified end to end in a browser against the real account and real DOCX resume from this
session: login, view profile with resume-verified/user-verified badges, edit a field, save, and
confirm the new field's tag via a direct API check.

**Step 3 (job search goals):** Added a new `JobSearchProfile` model + full CRUD router
(`app/job_search_profiles/`) supporting multiple named, independently pausable/duplicable
profiles per user, reusing the existing `JobGoals` field shape (extended with the fields the spec
calls for that it doesn't have: `target_functions`, `work_arrangements`, `relocation_preference`,
`salary_preferred`, `employment_types`, `keywords_include/exclude`). The old singular `/goals`
endpoint and `jobs/ranking.py`'s read of it are completely untouched -- wiring job-ranking to a
multi-profile system requires a design decision (which profile's preferences apply when several
exist?) that's out of scope for a Steps-1-3 revision and belongs with Step 4+ (job matching).

## What would change our mind

If `jobs/ranking.py` needs to start reading from `JobSearchProfile` instead of the legacy
`Goals` table (e.g. once job matching is built against a specific active profile), that's the
point to decide how multiple active profiles interact with ranking -- not before.
