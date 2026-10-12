# One-off upload source disclosure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task after builder review. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Disclose file versus effective facts and preserve their correct provenance/version in one-off runs.

**Architecture:** Resolve an effective fact context once, use it consistently in tailoring and saved metadata, and share source labels across both frontends. Preserve Career Profile precedence and the existing Word/PDF behavior; do not add an override/merge feature.

**Tech Stack:** Existing Python, pytest, FastAPI, Streamlit, Next.js and Playwright.
**Spec:** `specs/017-one-off-resume-source-disclosure.md` (approved 2026-10-11).
**Status:** Builder approved; implementation, full local verification and independent code review completed, including the Streamlit batch-source refusal follow-up. See decisions 039/041 and the independent-review/live-Streamlit experiment.

## Global Constraints

- "No new dependency, upload parser, full redesign or source-of-truth migration."
- "The master resume, Career Profile, current job and old reviews are never changed by disclosure."
- "Selecting another file must not turn unconfirmed saved facts into confirmed facts or suppress stale-profile protection."
- "Reviews disclose their own run snapshot, not whatever file/profile happens to be selected later."
- Synthetic data only; preserve `.claude/settings.local.json`, both apps and review format 2; no real data, home `.env`, account/cost/deployment or push.

## Review Focus

- One-off callers currently pass provenance None even when the effective facts come from a saved profile; optional unconfirmed facts must stay unconfirmed.
- Word-aligned role ordering must not change the canonical provenance paths or profile hash.
- A new selected upload must not relabel an already saved review as if it used that file.
- Legacy source metadata is unknown, not whatever profile/file is currently selected.
- Filenames are user-controlled strings: render as escaped text, never HTML or a filesystem path to fetch.

## Task 1: Effective fact context and frozen source metadata

**Files:** create `product/resume_tailorer/resume_source.py`; modify `session_profile.py` only if needed, `tailoring_service.py`, API `workspace/tailor_router.py`, Streamlit `pages/5_Tailor.py`; add `product/tests/test_resume_source.py`, `apps/api/tests/test_workspace_resume_sources.py`; extend `product/tests/test_tailoring_service.py`.

**Interfaces:** `FactContext(profile: CareerTruthProfile, provenance: dict | None, source: str, version: str | None)`; `resolve_fact_context(session, parsed_profile, *, career_profile=None, provenance=None) -> FactContext`; `source_details(filename: str, one_off: bool, facts: FactContext) -> dict`. Existing `set_career_profile` canonical precedence stays unchanged. Saved state gains `source_info` with `file_source`, `filename`, `kind`, `fact_source`, `profile_version` and derived disclosure labels.

- [ ] Step 1: add a service regression using the existing synthetic profile/one-off fixtures. Keep the parser, service, profile store and review storage real; stub only the writing/conversion boundaries as the existing tests do.

```python
def test_one_off_run_keeps_effective_profile_freshness(tailor_client):
    from tests.test_workspace_tailor import _ready, _run
    from tests.workspace_helpers import resume_docx
    _ready(tailor_client)
    tailor_client.post("/v2/profile/confirm")
    tailor_client.post("/v2/tailor/one-off", files={
        "file": ("different.docx", resume_docx(), "application/octet-stream"),
    })
    assert _run(tailor_client)["status"] == "done"
    tailor_client.put("/v2/profile/summary", json={"summary": "Corrected synthetic summary."})
    assert tailor_client.get("/v2/tailor").json()["stale_message"]
```

Add a genuinely different one-off summary/tool fixture and assert persisted Career Profile bytes/facts stay unchanged. Add unconfirmed optional-role facts and inspect the resulting requirement status; no-profile one-off retains parsed-file context/version None. Reordered Word roles use canonical hash/provenance, not aligned role order.

- [ ] Step 2: run new source tests and the API one-off regression. Expected: current run lacks effective-source metadata/version and does not show the stale message.
- [ ] Step 3: resolve actual effective source once, after parsing/explicit profile selection and before building the requirement review. Obtain saved provenance from `session['profile_record']` when the effective source is FACT_VAULT, even if the caller passed None. Hash the canonical effective Career Profile before Word role alignment.

```python
context = resolve_fact_context(
    session, parsed_profile, career_profile=career_profile, provenance=provenance,
)
review_profile = context.profile
review = build_review(job_analysis, review_profile, provenance=context.provenance,
                      posting=job_description)
state["profile_version"] = context.version
state["source_info"] = source_details(filename, one_off, context)
```

Carry an explicit `one_off` flag to the service, default False for existing callers, rather than infer it from a display label. File/record metadata comes from the selected source, not a mutable later session. Keep style extraction, DOCX source bytes and canonical fact precedence unchanged. Independent parsed-file runs have no Career Profile hash and do not persist their parsed facts into the master record.

- [ ] Step 4: run full product/API suites. Verify frozen review metadata survives encode/decode and source changes; commit with `fix: preserve effective facts and provenance in one-off runs`.

## Task 2: Show file and facts before starting and in saved reviews

**Files:** source labels in `resume_source.py`; API `workspace/tailor_router.py`; `apps/web/src/lib/types.ts`, `apps/web/src/app/tailor/page.tsx`, `apps/web/src/app/tailor/review.tsx`; Streamlit `pages/5_Tailor.py`; add `product/tests/test_tailor_sources.py`, `apps/web/e2e/resume-sources.spec.ts`; extend `apps/api/tests/test_workspace_resume_sources.py`.

**Interfaces:** selected `resume.source_info` describes the next run; saved `review.source_info` describes that frozen review. Fields are additive and optional for old payloads/files. `source_disclosure(info: dict | None) -> dict` returns file/fact labels and explanatory note; None yields source-details-unavailable, not guessed current metadata.

- [ ] Step 1: add visible-output tests for canonical plus one-off, independent one-off, removal, later upload and legacy review. For saved reviews, assert the previous synthetic filename remains visible after selecting a second file. For batch refusal, verify the explanation and 409 persist.

```typescript
await expect(page.getByText("Resume file", { exact: true })).toBeVisible();
await expect(page.getByText("Facts", { exact: true })).toBeVisible();
await expect(page.getByText(/uploading here does not update/i)).toBeVisible();
```

- [ ] Step 2: run source API/AppTest/browser cases; expect the current UI/payload to omit file-versus-facts disclosure.
- [ ] Step 3: render escaped source labels and shared notes beside run controls and review details. Explain Word layout/bullets versus PDF rebuilding; never promise that every Word fact is synced on the one-off branch. Use `source_info` from the saved state for review details. Retain the existing remove-one-off control and batch policy.

```typescript
export type ResumeSourceInfo = {
  file_source: "career_profile" | "one_off";
  filename: string; kind: string;
  fact_source: "fact_vault" | "resume_upload";
  profile_version: string | null;
  file_label: string; facts_label: string; note: string;
};
// Add optional source_info to the existing resume and Review types.
```

- [ ] Step 4: run full suites, lint/types and all Playwright cases, plus a labeled synthetic browser exercise. Record the new stale guard for a one-off file using canonical facts and the independent-file exception.
- [ ] Step 5: commit verified UI changes, obtain the executing-plans final independent review, and update decision/AGENTS/handoffs after implementation. Do not push.

## Verification and self-review

Use the exact existing Python/Node commands in the spec-016 plan with unique scratch directories `spec017/product`, `spec017/api` and `spec017/web`. Browser tests use existing API Python, product-package PYTHONPATH and explicit synthetic data. Every completion claim needs observed exit/counts.

All spec-017 requirements are covered by Tasks 1–2. The five review-focus conditions are pinned in Task 1 (provenance/alignment) or Task 2 (snapshot/legacy/escaping). Task 2 consumes Task 1's `source_info` contract. Run Task 1 after spec-016 shared truth guards; spec-018 staging must preserve, not recompute, this snapshot.

Recommended execution: native in this session; builder review of this plan precedes product edits.
