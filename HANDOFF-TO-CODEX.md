# Handoff to Codex — Job Copilot

**Date:** 2026-09-28
**From:** Claude Code (Steps 21-24 revision, on top of the Steps 16-20 handoff)
**Repo:** `ysj1995sss/yang95_msb341`
**Audience:** A fresh Codex session continuing this product.

Read this file first, then `AGENTS.md`, then the decisions listed below. Do not re-litigate
decisions 001, 006, 009, 012, 014, 015, 016, or 017 unless new evidence forces it.

---

## 1. What this product is

Automated job-application copilot for job seekers:

1. Upload resume → Career Truth Profile (the only source of truth the AI can draw from)
2. Search / discover jobs (Steps 3-9)
3. Triage → **Apply** hands off into resume tailoring (Step 10+)
4. Tailor the resume against the job (Steps 10-15)
5. Application modes, submission, status dashboard (Steps 21-24)

**Non-negotiable:** optimize presentation; never invent qualifications, employers, dates, or
metrics. This rule has driven nearly every fix in this project's history — take it as literally
as it reads.

---

## 2. Architecture (source of truth)

| Layer | Path | Role |
| --- | --- | --- |
| Product engine + Streamlit UI | `product/resume_tailorer/` | Primary implementation (decision 001) |
| Job discovery engine | `product/resume_tailorer/job_search/` | Scout, dedupe, fit, quality, dashboard helpers, SQLite |
| Tailoring pipeline | `product/resume_tailorer/analyzers/`, `tailorer/`, `docx_export/` | Steps 10-15 — see decision 013 |
| Validated artifact pipeline | `product/resume_tailorer/artifacts/` | Steps 16-20 — see decisions 014, 015 |
| Application flow | `product/resume_tailorer/applications/` | Steps 21-24 — see decisions 012, 016, 017 |
| FastAPI backend | `apps/api/` | Profile, jobs upsert/list, tailor; delegates dedupe/normalize/fit to product |
| Specs / decisions / sprints | `specs/`, `decisions/`, `sprints/` | Product truth and history |

Dual stack is intentional for now: Streamlit SQLite job search **and** API Job/UserJob. Shared
logic lives in `product/`; API must not fork a second scorer, fingerprint, or tailoring engine.

**Two tailoring paths exist, deliberately, for different upload types** — not an accident to
"fix" by merging them:
- **DOCX originals** → `docx_export/pipeline.py` → `DocxBulletTailorer`: splices tailored text
  into the ORIGINAL document's own paragraphs (decision 006), preserving fonts/margins exactly.
- **PDF-only originals** → `tailorer/resume_tailorer.py` → `ResumeTailorer`: freeform whole-resume
  rewrite through `PDFGenerator`, since there's no editable structure to preserve. As of decision
  013 both paths share the same evidence-based prompt guidance and validation checks
  (`diff_generator.py`), but the freeform path still lacks a repair loop and a hard length gate
  the DOCX path has (see decision 013's "known limitations").

---

## 3. Git status (as of handoff)

Steps 21-24 (spec 003, decisions 016/017) were revised directly on `main` in this session — no
feature branch, committed incrementally phase by phase, all on top of Steps 16-20 (spec 002,
decisions 014/015), which were themselves built on `codex/validated-artifacts-steps-16-20` and
integrated into `main` in the prior session. `main` should be fully up to date with everything
below by the time you read this — no open PRs, no uncommitted work, nothing to merge first.
`main` was 18 commits ahead of `origin/main` as of the Steps 16-20 handoff and was pushed at the
user's request; confirm with `git status` / `git log origin/main..main` whether this session's
Steps 21-24 commits have been pushed too. `git pull` before starting is still good practice in
case something landed after this doc was written.

Latest commits on `main`, newest first (Steps 21-24 slice):
- `docs: complete apply_for_job's docstring for the new snapshot/safety params`
- `test: guard against auto-filling sensitive/legally significant fields` (Phase F — security)
- `feat: rebuild the Applications dashboard` (Phase E — spec 003 Step 24)
- `feat: dashboard formatting/filtering/sorting helpers` (Phase E groundwork)
- `feat: expose status provenance through StatusTracker` (Phase D)
- `feat: track submission attempts, enforce idempotency, snapshot job/fit data` (Phase C)
- `fix: hard-gate real ATS submission on a proven capability, not a click` (Phase B — decision 016,
  the actual safety bug fix)
- `docs: specify Steps 21-24 application tracking revision` (spec 003)

Before this slice, latest commits on `main`, newest first (Steps 16-20 slice):
- `docs: close Steps 16-20 validated artifact build` (decision 015)
- `fix: preserve manual edits and pin regeneration to the run's profile snapshot` — whole-branch
  review fixes (decision 015)
- `test: add anonymized DOCX/PDF acceptance fixtures for Steps 16-20` (Task 9)
- `fix: coerce EducationEntry.year to str before content validation`
- `feat: add validated resume review workflow` (Task 8 — Streamlit migration)
- `refactor: move regeneration.py from apps/api to product/resume_tailorer`
- `feat: add tailoring review and regeneration API` (Task 7)
- `refactor: extract finalize_docx_edits for tailorer-free regeneration`
- `feat: persist immutable tailoring artifacts` (Task 6)
- Tasks 1-5 (Codex): validated artifact domain models, DOCX layout signature validation,
  structured visual PDF validation, unified report/change models, artifact orchestration pipeline

Before that slice, latest commits on `main`, newest first:
- `865d70b` — Steps 10-15 audit summary + Phase G live regression (decision 013)
- `4e30372` / `5a1ad23` / `6f8854c` / `b7eaa09` / `6024269` / `1636d6d` — Steps 10-15 audit Phases F/E/C/D/D/B
- `b136542` — Job Search → Applications handoff, Assist/Auto mode honesty fixes (decision 012)
- `dfe2325` / `2c94527` / `5cee92e` — PR #2 (Steps 4-9 completion slice) reconciliation + live bug fixes

---

## 4. What is already built (do not rebuild)

### Sprint 1 — Resume tailoring core (Steps 1-2, 10-20)
Career Truth Profile, job-description analysis, resume benchmarking, gap report, truthful
tailoring, PDF/DOCX export with validation. See decisions 002-006, 008, 009, 013.

### Sprint 2 — Job discovery (Steps 3-9), merged via PR #1 + #2 — decisions 010, 011
Shared fingerprint/normalize/dedupe; `CandidateFitScorer` cf-v2 with competency-map transferable
evidence; canonical triage SAVE/APPLY/PASS; APPLY → Step 10 handoff; dashboard filters/sort;
`SearchRunSummary`; job quality states (active/stale/expired/broken/unknown); honest source
labels (Greenhouse live, others limited/demo).

### Steps 10-15 — Job analysis through length control, rebuilt this session — decision 013
Structured `JobRequirement` model with hard-gate detection and importance ranking (Step 10);
explicit `evidence_level`/`hard_gate`/`unmet_hard_gates` on gap items (Steps 11-12); the freeform
tailoring path brought to parity with the DOCX path's semantic-drift and fabrication checks
(Step 13); a bounded resume-wide optimization pass for the DOCX path (Step 14); bullet-length
warnings wired into the freeform path (Step 15, `bullet_length_delta` had zero callers before
this).

### Steps 16-20 — Validated resume artifact pipeline, built this session — decisions 014, 015
One shared pipeline (`product/resume_tailorer/artifacts/`) both `apps/api` and Streamlit now go
through: structured `ArtifactValidation` (PASS/WARNING/FAIL) covering structure/content/truth/ATS/
visual checks; DOCX layout-signature validation (paragraph add/remove/reorder is a hard FAIL);
render-based visual PDF validation via PyMuPDF; a unified `FinalApplicationReport` shared by both
adapters; immutable `TailoringRun`/`TailoredArtifact` persistence (`supersedes_artifact_id` chains
backward, existing rows never mutated); a review API
(`GET/PATCH /tailor/runs/{id}`, `POST /tailor/runs/{id}/regenerate`, `GET /tailor/artifacts/{id}`)
supporting accept/reject/restore/manually-edit, all ownership-checked (404 for non-owned); Streamlit
migrated off its old freeform-only path onto the same DOCX/PDF dispatch and given the same review
controls. Two anonymized acceptance fixtures under `product/tests/fixtures/artifacts/` exercise
both paths end-to-end. **Known gap, not built:** the bounded one-retry correction/condensation loop
(`ValidatedArtifactPipeline` in `artifacts/pipeline.py`) is implemented and unit-tested but never
wired into either adapter, because a real corrector needs actual LLM-based paragraph condensation
that doesn't exist anywhere yet — see decision 015's "Known limitations" before building this.

### Steps 21-24 — Application flow, revised this session — decisions 012, 016, 017
`ApplicationMode`/`ApplicationStatus` domain models, full audit-trail database, submission engine,
Streamlit page with a submit tab (Preview-before-Submit gate) and a full status dashboard.
**Assist/Auto mode does not work against real ATS forms** — verified live: a real Greenhouse
application form is JavaScript-rendered with almost no server-side-named fields, which this
static-HTML-parsing pipeline structurally cannot read (decision 012). This session found and fixed
a real safety bug on top of that honest-but-unsafe state: the real-submit code path treated any
non-error HTTP response as a successful submission, which could have silently recorded a false
"Applied" status — see decision 016. `ATSCapability` now makes every platform declare
`final_submission=False` explicitly, and `SubmissionEngine` hard-blocks the real POST on that flag.
Also added this session: `SubmissionAttempt` audit tracking (a real-submit request always leaves a
row, including failures), idempotency (refuses a second real submit for an already-confirmed job),
immutable job/candidate-fit snapshots on every `ApplicationSubmission`, status provenance
(source/confidence/evidence, ready for a future email/ATS integration that doesn't exist yet), and
a full dashboard rebuild (saved views, filters, sorting, application detail, editable next-action).
Manual mode (generate resume, hand the candidate the link) remains the one mode that's honest and
reliable for actually submitting an application; the product says so in its own UI. See decision
017 for the full build summary and known limitations.

### Explicitly out of scope until the product asks
- Browser-automation-based Assist/Auto submission (decision 012 — a deliberate, separate decision
  with its own risk profile, not something to build silently)
- LLM-based Step 10 extraction (still regex/heuristic; decision 013 names this as a known gap)
- A repair loop or hard length gate for the freeform/PDF tailoring path (decision 013)
- The bounded correction/condensation loop's actual condensation logic (decision 015) — the
  orchestration shell exists and is tested; the LLM-based "shorten this paragraph without changing
  its claims" component it needs does not exist anywhere yet
- Real submission for any ATS platform (decision 016) — every platform declares
  `final_submission=False`; flipping this requires either a documented submission API or approved
  browser automation, not a code change alone
- Custom/job-specific application question answering (decision 017) — `custom_answers` is
  hardcoded to `{}`; the architecture anticipates this but nothing drafts or stores answers
- Email/ATS status integration (decision 017) — the `source`/`confidence`/`evidence` fields and
  `StatusTracker.record_low_confidence_signal` are groundwork only, nothing calls them yet
- New live ATS providers beyond Greenhouse (Lever/Ashby/Workday parsers exist but are unverified
  against real forms)
- Persisted `search_runs`/RawJob tables; live URL revalidation of every stored job on every load
- Porting React `apps/web` or a Chrome extension (noted in README as future)

---

## 5. Immediate next work (pick one, or propose something else)

There is no single mandated next step — the last session closed out its scope cleanly rather
than leaving something half-finished. Options, roughly in order of how contained they are:

### A. Freeform tailoring path parity gaps (decision 013's "known limitations")
Smallest, most contained: add a repair loop and/or a hard length-verification step to the
freeform/PDF path, mirroring what the DOCX path already has. Read decision 013 in full first.

### A2. Wire up the Steps 16-20 correction/condensation loop (decision 015's "known limitations")
`ValidatedArtifactPipeline` (`product/resume_tailorer/artifacts/pipeline.py`) already implements
and tests the bounded-one-retry policy; what's missing is a real `CorrectionCallback` that
actually condenses a specific paragraph within already-approved claims (spec 002 section 8.5),
almost certainly another LLM call, then wiring that callback + the pipeline class into
`apps/api/app/tailor/router.py`'s `tailor_preview`/`regenerate` and
`product/resume_tailorer/app.py`. Read decision 015 in full first — it explains exactly why this
wasn't built in the same session that found the gap.

### A3. Custom/job-specific application question answering (decision 017's "known limitations")
`SubmissionEngine`/`FormFiller` only ever fill a curated, safe whitelist (name/email/phone/
location/current employer/title). Free-text or select-type job-specific questions ("Why do you
want to work here?", "Years of experience with X?") are left blank for the user in Manual/Assist
mode; nothing drafts or suggests an answer. Building this needs its own careful design for what's
safe to suggest vs. what always needs the user's own input (spec 003's answer-source-of-truth
model already separates verified-reusable/job-specific/sensitive/unknown — that's the intended
shape, not yet implemented behind it).

### B. Real end-to-end usage
Get someone other than the builder through the full search → triage → tailor → apply loop and
see what breaks. No code changes implied until something real is found.

### C. Browser-automation-based Assist/Auto mode
The biggest, riskiest option. Decision 012 explicitly deferred this. **Before writing any code
here, have an explicit conversation with the product owner about the risk profile** (a program
driving a browser to submit real applications to real employers) — do not treat "the next logical
step" as implicit permission for this one.

### D. Something else
Check `specs/001-job-application-copilot.md` for the full product vision if none of the above
feels right, and propose a plan before implementing anything non-trivial (per `AGENTS.md`'s
working agreement).

**Before starting ANY of these:** run the full test suites (below) to confirm you're starting
from a green baseline, and check `git log`/`decisions/` for anything that landed after this doc
was written.

---

## 6. Key files to open first

```
AGENTS.md
decisions/001-consolidate-product-architecture.md
decisions/006-docx-master-template-splice-pipeline.md
decisions/009-transferable-evidence-and-scoring-consistency.md
decisions/012-assist-auto-mode-does-not-work-against-real-ats-forms.md
decisions/013-steps-10-15-rebuild-summary.md
decisions/014-use-one-validated-artifact-pipeline-for-steps-16-20.md
decisions/015-steps-16-20-build-summary.md
decisions/016-ats-capability-model-and-hard-submission-safety-gate.md
decisions/017-steps-21-24-revision-summary.md
specs/001-job-application-copilot.md
specs/002-steps-16-20-validated-artifact-pipeline.md
specs/003-steps-21-24-application-tracking-revision.md
product/resume_tailorer/analyzers/job_analyzer.py       # Step 10
product/resume_tailorer/analyzers/gap_analyzer.py        # Steps 11-12
product/resume_tailorer/tailorer/docx_bullet_tailorer.py # Step 13 (DOCX path)
product/resume_tailorer/tailorer/resume_tailorer.py      # Step 13 (freeform path)
product/resume_tailorer/docx_export/pipeline.py          # Step 14 + Steps 16-20 (finalize_docx_edits)
product/resume_tailorer/artifacts/                        # Steps 16-20 domain models/pipeline/regeneration
product/resume_tailorer/ui/artifact_review.py             # Steps 16-20 Streamlit review helpers
product/resume_tailorer/applications/                     # Steps 21-24
product/resume_tailorer/applications/capabilities.py       # Steps 21-24 ATSCapability lookup (decision 016)
product/resume_tailorer/applications/submission_engine.py  # Steps 21-24 safety gate + attempt tracking + idempotency
product/resume_tailorer/applications/ui_helpers.py         # Steps 21-24 dashboard views/filters/sorting
apps/api/app/tailor/router.py                              # Steps 16-20 preview/review/regenerate/download
apps/api/app/tailor/storage.py                             # Steps 16-20 immutable persistence
```

---

## 7. Environment setup checklist

1. `git pull` on `main` — confirm you're at or past `865d70b`.
2. Python 3.12+ recommended.
3. **Two separate venvs, not one:**
   ```bash
   cd product && python -m venv .venv && ./.venv/Scripts/pip install -r requirements.txt   # Windows
   cd apps/api && python -m venv .venv && ./.venv/Scripts/pip install -e .
   ```
4. Always set `PYTHONPATH` to include `product/` when running Streamlit or product tests
   directly from a shell (not needed when running `pytest` from inside `product/` itself).
5. LLM keys: only needed for live tailor tests; set in a local `.env`, never commit secrets or
   real PII (anonymize).
6. Greenhouse live scrapes need network; LIMITED sources (LinkedIn/Indeed/Handshake) work offline
   with mocks.

---

## 8. Verification commands

```bash
cd product && ./.venv/Scripts/python.exe -m pytest -q          # expect 685 passed
cd apps/api && ./.venv/Scripts/python.exe -m pytest -q          # expect 60 passed
```

Live smoke test (needs LLM keys configured):
```bash
cd apps/api
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
./.venv/Scripts/python.exe scripts/try_it_yourself.py --resume <path> --job <path>
```

---

## 9. Working agreements (mirror AGENTS.md)

- Ask before large refactors or new dependencies.
- Spec first for non-trivial features (`specs/`).
- Record meaningful choices in `decisions/`.
- Prefer shared helpers in `product/` over duplicating logic in `apps/api`.
- Preserve working handoffs: Job Search → Tailorer (`pending_tailor_job`), Job Search →
  Applications (same session-state key, job ID pre-fill).
- Tests: pytest; do not claim done without running the relevant suites.
- Audit before rebuilding: if something looks broken, read its existing implementation and
  decision history first — several "obvious" fixes this session turned out to already exist and
  just needed wiring, not reinventing.

---

## 10. Known pitfalls

- Streamlit must run with `PYTHONPATH` pointing at `product/` or imports of `resume_tailorer`
  fail.
- `search_and_store` returns `SearchRunSummary`, not a raw `int` — use `.total_stored`.
- A `bare navigate()`/full page-reload to a Streamlit URL starts a NEW session — `st.session_state`
  does not carry over that way. Use in-app sidebar links or `st.switch_page` to preserve state
  when testing handoffs live.
- Sponsorship silence is `NOT_STATED`, not `NO`.
- Do not create a second Candidate Fit scorer, tailoring engine, or fabrication/drift checker —
  this project's history is full of exactly that mistake being found and consolidated later.
- The DOCX splice pipeline never adds/removes/reorders paragraphs — that's what makes fidelity
  guarantees structural rather than something to detect-and-reject after the fact. Any new
  DOCX-path feature must preserve this.
- `git add` on a `.pdf`/`.docx` fixture on Windows will warn about LF/CRLF conversion — that's not
  cosmetic, it can silently corrupt binary content on checkout. `.gitattributes` now marks
  `*.pdf`/`*.docx`/`*.doc` as binary; if you add a new binary fixture type, extend it there rather
  than ignoring the warning.
- A `ResumeChange`'s `proposed_text` must always stay the untouched AI proposal — never overwrite
  it with a user's manual edit in place. Use `manual_text` for that. The freeform regeneration path
  finds `proposed_text` verbatim in the baseline text to substitute a change's final text; anything
  that mutates `proposed_text` breaks that lookup silently (see decision 015, finding 1).
- Anything reading a `TailoringRun`'s profile for regeneration/re-validation must use
  `run.profile_snapshot_json`, never `db.get(Profile, user.id)` — the run must regenerate against
  the exact profile it was proposed against, not whatever the user's profile looks like now
  (decision 015, finding 2).
- Never let `SubmissionEngine` perform a real POST for a platform whose `ATSCapability.final_submission`
  is `False` — that flag exists specifically because a prior version of this code treated any
  non-error HTTP response as a successful submission against a URL that was never a real
  form-submission endpoint (decision 016). If you're adding a new ATS platform, its capability
  must default to `final_submission=False` until independently proven working live.
- `ApplicationSubmission`/`SubmissionAttempt`/status-history columns are additive-only in
  `applications.db`, same pattern as `apps/api/app/migrations.py` — never rename or drop a
  column; add a new one guarded by an existence check in `_apply_additive_migrations`.

---

## 11. Success criteria for whatever you pick

- [ ] Both test suites green before AND after your changes
- [ ] A decision record for any non-trivial architectural choice
- [ ] Live verification (not just unit tests) for anything touching the tailoring or application
      pipelines — this project's history shows unit tests alone repeatedly missed real bugs that
      only showed up against a real posting/resume
- [ ] Honest reporting of what still doesn't work, matching this repo's established pattern
      (see decisions 012 and 013 for the tone/format)
