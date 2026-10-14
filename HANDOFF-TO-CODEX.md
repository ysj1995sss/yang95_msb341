# Handoff to Codex — Job Copilot

**Date:** 2026-10-12 (local spec-019 update); older sections below are history
**From:** Claude Code (specs 009–011) and Codex (spec 012, decision 034)
**Repo:** `ysj1995sss/yang95_msb341`
**Audience:** A fresh Codex session continuing this product.

Read this file first, then `AGENTS.md`, then the decisions listed below. Do not re-litigate
decisions 001, 006, 009, 012, 014, 015, 016, or 017 unless new evidence forces it.

---

## START HERE (2026-10-13, late) — Match score, Remote filter, certifications, "Left out"

Local commits on `main`, **not pushed**; the backend needs a Cloud Run rebuild after the push (spec 023).
- **Match replaces Candidate fit (decision 047).** The number is the share of the posting's stated
  requirements that the person's confirmed facts show (required ones count double; related
  experience or listed-only skills count half). It's worked out from the requirement review
  (`job_search/requirement_match.py`). Searches over 100 jobs get a quick first pass, and only the
  top 100 (plus the page shown) get the full Match. Older scores say "(older fit measure)".
- **Remote filter:** work mode is read from the location ("Remote, US"); an "Only jobs that say
  they're Remote" option hides jobs that don't state it.
- **Certifications** the model drops are put back, never proposed for removal.
- **Review list:** a change the checks kept out says "Left out", not "Not reviewed".
- **Room to reword (decision 048, approved):** the requirement's own wording is allowed on the
  bullet that is its evidence (not years, numbers or unshown terms); filler words may be dropped;
  the Word length cap is 25% (was 15%); the PDF instructions ask for every supported rephrase.
  One real Codex pass on the fixture: 2 rewrites accepted, both blocked under the old rules.
- **Dogfood round 4 (local):** 12 issues, 11 fixed (report outside the repo, `dogfood-output-4`).
  - **Match:** "check yourself" rows count by the skills they name (years stay uncounted); one broad
    word alone is half credit; work authorization is left out.
  - **Tailoring:** a requirement shown only "in other words" is no longer "already shown", so it gets
    rewritten (a real run had proposed nothing).
  - **Requirement sections:** "Skills & Experience" requirements are read.
  - **Remote:** the "only jobs that say they're remote" box starts ticked.
  - **Rewrites:** word-family grounding; grammar-only Word rewrites dropped.
  - **Supporting fact:** a rewrite's supporting fact is its own bullet.
  - **Still open:** Tailor's requirement review calls unanswered work authorization "missing".

## START HERE (2026-10-13, evening) — live on Vercel + Cloud Run; review, dogfood and bug fixes

Everything is on `main` (the codex branch matches it).
- **Live:** website on Vercel, backend on **Google Cloud Run**, model **Groq**
  (`groq/openai/gpt-oss-120b`). Deployment, settings and the backend update commands are in
  `specs/023-free-test-deployment.md`; build with `cloudbuild.yaml`. Render is replaced.
- **What today fixed** (details in the commit messages):
  - **Code review fixes:**
    - the shared-test sign-out lockout;
    - spec 022 additions blocked by the gap gate;
    - Word summaries never found;
    - duplicate tools and fake certifications on import;
    - batch review revision;
    - trailing-punctuation metrics.
  - **Dogfood fixes (PDF path):**
    - "N/A" printed as the location;
    - degree above the school line dropped;
    - "Tools:" ending the skills section;
    - stale reviews called ready;
    - raw server errors shown to people;
    - leadership evidence missing;
    - audit-language refusals;
    - plural and verb-form stemming blocking rewrites;
    - failed proposals built into the first resume ("not usable");
    - Core Competencies additions;
    - review-list states in words.
- **Backend not redeployed yet:** most fixes need the Cloud Run rebuild (spec 023).
- **Open:**
  - ~~"Candidate fit" scores nearly every job 85–96%~~ (fixed later the same day: decision 047);
  - free-form resumes get no level 2–3 additions;
  - Word-to-PDF conversion on Cloud Run hasn't been checked online;
  - 0 human testers;
  - the Gemini `reasoning_effort="disable"` bug (left by the builder; matters only if Gemini
    returns).
- **New decision:** 046 records the Unicode PDF fonts and fit-to-page shrink, which reverse part of 005.

## START HERE (2026-10-12, later) — Claude Code session: review fix, Word fix, direction, Streamlit retired

Branch `codex/truthful-tailoring-sources-publication`, **not merged or pushed**. Preserve
`.claude/settings.local.json`. The builder does not read code: explain in plain English and put
decisions to them as numbered questions, each with a recommended answer.

- **Product direction changed (decision 043, read it first).**
  - **Auto-apply replaces "never submit"** (decision 016), with guardrails: checks must pass,
    a daily cap of 10, a pause button, a sent log, and an opt-in preview.
  - **Tailoring may add** unlisted and adjacent skills (levels 1–3), never invented facts.
  - **Online:** free tier with sign-in, for 3 testers first.
  - **The website is the product.** Nothing in 043 is built yet; each item needs a spec.
- **Glossary:** `CONTEXT.md` is a draft the builder is reviewing. Use its words.
- **Engineering skills:** issues go to GitHub Issues, and `decisions/` stands in for an ADR
  folder. See `docs/agents/`.
- **Spec 019 review fix (`fa06a33`):** change IDs are positional, and each new run reset
  `review_revision` to 0. A stale tab's batch or single decision could therefore land on a
  different proposal. Now:
  - new runs start at `new_review_revision()` (a millisecond timestamp);
  - single decisions accept `expected_revision`;
  - "Edit manually" with no text keeps the saved wording.

  This was a review by Claude, not the independent review, which remains outstanding.
- **Spec 020 Word conversion (`c243839`):** Windows conversions use a private Word instance
  (`DispatchEx`), open read-only, and always close and quit only their own instance. The
  two-process reproduction went from 2 failures in 12, with a stray Word process left behind,
  to 12 of 12 passing with no Word left over. Not yet checked with the builder's own Word open.
- **Playwright hang:** not reproduced. Several full runs exited 0 in about 1.5 minutes, so no
  cause is claimed.
- **Bug hunt** (`discovery/bug-hunt-2026-10-12.md`, real model, synthetic data): the importer
  misread one-line education, two one-line degrees, and a title written below
  "Company | City | Dates". Fixed in `93c190a`. Also, the model proposed 0 changes for the
  fixture resume; open.
- **Spec 021, Streamlit retired:**
  - **Removed:** `app.py`, `pages/`, the Streamlit-only `ui/` screens, `streamlit_views.py`,
    `code_freshness.py`, `llm/ui.py`, `.streamlit/`, the Streamlit stylesheet in
    `ui/design_system.py`, the `streamlit` requirement, and 67 Streamlit-only test cases (1,364 → 1,297).
  - **Correction:** `ui/__init__.py` used to import the Streamlit shell, so the backend *did*
    load Streamlit until now.
  - **Checked:** the backend and every product module load with Streamlit blocked.
  - **Kept:** `packages.txt`, because CI installs LibreOffice from it.
  - **The old app** is at the tag `ui-streamlit-v1`. The live streamlit.app demo breaks when
    this reaches `main`; that's the builder's account to switch off.
- **Verification (sequential, synthetic):** product **1,297 passed, 1 skipped**; API **157 passed**; web lint and types exit 0; Playwright **29 passed, exit 0** (92 s). One earlier browser failure was from two overlapping runs sharing `test-results`; the clean solo rerun passed.
- **Next, in the builder's order (Q19):** make tailoring visibly do more (Q9 levels 2–3, needs a
  spec); then an auto-apply pilot on one platform (spec); then online hosting with sign-in
  (spec, plus the builder's accounts). Human testers: 0.


## START HERE (2026-10-13) — handoff from Claude: online test is live, known 502s open

**Branch:** `codex/truthful-tailoring-sources-publication` at `246dd76` (51 commits ahead of `main`). Pushed to GitHub. Working tree clean. **`main` is not merged and must not be deployed from.** Preserve `.claude/settings.local.json`.

**Builder preferences (read first):** the builder does not read code. Explain in plain English, ask numbered questions with a recommended answer, never print or commit secrets or real data, and never create accounts or press deploy buttons on their behalf. Use synthetic data for tests (`apps/web/e2e/fixtures/resume.docx`, scratch data folders). Never use `D:\Yang\Vibe Coding\job-copilot-local-data`.

### Decisions this session (read before changing these areas)
- **043** Product direction: auto-apply replaces "never submit" (not built); tailoring may add levels 1-3 (never invented facts); website is the product; Streamlit retired (spec 021, tag `ui-streamlit-v1`).
- **044** Level 2-3 skills additions on the Word skills line; tools kept out of summaries (the check stays, the model is told); unconfirmed facts warning with two buttons.
- **045** **Shared test workspace, no sign-in** (builder's explicit choice, against recommendation). `SHARED_TEST_WORKSPACE=yes` on the website, only when Google sign-in is not configured. Anyone with the address shares one workspace and can spend the model key. Backend still refuses unsigned requests in production.
- Specs: 022 (levels 2-3, step 5 instructions done, PDF path NOT done), 023 (free deployment guide, updated for 045).

### Hosting state (all verified by the builder unless marked)
- **Backend:** Render, service `yang95-msb341` (URL `https://yang95-msb341.onrender.com`, `/health` returns ok), Docker, free plan, no disk. Env: `WORKSPACE_TOKEN_SECRET`, `LLM_MODEL=gemini/gemini-2.5-flash`, `LLM_API_KEY`. `render.yaml` is the free-plan blueprint.
- **Website:** Vercel project `yang95-msb341` (`https://yang95-msb341.vercel.app`), root `apps/web`, Production branch set to the codex branch, Vercel Deployment Protection "Require Log In" turned off. Env: `API_URL` (Config type, not Secret, since Secret values are write-only), `AUTH_SECRET`, `WORKSPACE_TOKEN_SECRET` (must equal Render's), `SHARED_TEST_WORKSPACE=yes`. Env changes only apply after a redeploy (Deploy Hook named `test` exists on Settings > Git; the Redeploy menu only rebuilds `main`).
- **Builder's secrets:** two secrets were pasted into chat once and replaced. Assume the originals are compromised. Don't ask for secret values; ask for length and first 4 characters only.
- **Open risk:** the Vercel site has returned **502** on Jobs and Home when the Render service restarts (free plan sleeps after 15 min; restarts observed in logs). Likely memory (Word/LibreOffice and job search), not confirmed. Next step: read Render Metrics > Memory and logs at the moment of 502, then either lighten the job search or upgrade plan (builder decides cost).
- **Not verified:** Word-to-PDF on Render (LibreOffice memory); the backend image size vs. 512 MB; PDF-path tailoring end to end on Render.

### Product state
- Tests at `246dd76`: product **1338 passed, 1 skipped**; API **166 passed**; web lint and types clean; Playwright **31 passed**. Run suites sequentially, one at a time (overlapping runs caused a false browser failure).
- Fixed this session (see `discovery/bug-hunt-2026-10-12.md`, bugs 1-16 and later): education and title parsing, PDF bullet glyphs, table headers, Word phone pattern (dates looked like phones), duplicate-key and finding labels, unconfirmed facts warning, accented names in PDFs (Unicode font), two-line education blocking Word sync, a fake "2027 M" metric, PDF fit-to-page (tighter spacing before failing).
- **Still failing for the builder's own resume (PDF path):** page-length (dry run: fits only at "2 pages"), and two proposed changes that add tools not in the profile (they must be kept as originals). The builder now has a 2-page setting and a dry-run result that passes with warnings after keeping originals.
- **Open product work:** level 2-3 additions are not yet on the PDF path (needs narrow exemptions in `content_validator.py` and `find_unsupported_claims`); `Select all unreviewed` should skip failed-check changes (builder asked for it, not confirmed); Tailor should explain the 2-page option inside the review, not only at Start over (offered, not confirmed).

### Next steps in order
1. Read Render Metrics (memory) and logs at a 502; report to the builder in plain English.
2. Confirm with the builder: upgrade Render (about $7/mo) or lighten search. Don't change plans without a yes.
3. Builder's Word resume re-import + batch run on the live site (one tester at a time, shared data).
4. Spec 022 PDF path, with tests first, after the builder approves.
5. Human testers: 3 required for the finish line. None done yet.

### Rules that bit us this session
- Vercel `Secret` env values can't be read back; use `Config` for non-secret values.
- Vercel Git branch tracking: a branch needs one deployment before it can be set as production.
- Render Blueprint form: env keys must not contain a slash; the model value goes in the value box.
- Run any test suite that uses ports 3100/8100 alone.

## START HERE (2026-10-12) — spec 019 local Tailor review redesign

This section supersedes older review UI notes. Current branch is
`codex/truthful-tailoring-sources-publication`; **not merged or pushed**. Read
`specs/019-tailor-review-clarity-batch-and-ai-assisted-decisions.md`, decision
042, and `discovery/experiments/2026-10-12-spec-019-tailor-review.md` before
changing Tailor review. Preserve `.claude/settings.local.json` and the separate
Next.js/Streamlit apps. Node is `D:/Yang/Software/cursor/NodeJs/node.exe`.

- Manual review is the default. Before a new run, either UI can choose a
  conservative AI-assisted mode. It uses the existing proposal and deterministic
  checks, never a second model call. Only anchored, individually passing,
  non-omitting rephrases are auto-accepted; clear failures keep originals;
  uncertainty remains for a person. Human overrides retain their origin.
- Distinct queue titles reflect source and proposed wording, not repeated job
  requirements. Both UIs show full original/proposed/requirement text and can
  decide a selected set at once. A revision-checked, per-user locked transaction
  prevents partial/stale batch writes; Streamlit's session save cannot overwrite
  a newer API/other-tab review. Legacy decisions say origin not recorded.
- Final artifact validation is unchanged. Failed PDFs cannot be downloaded or
  handed to Apply. No true duplicate proposals from the builder's resume were
  established, so decision 018's global matcher was not touched.
- Local verification (synthetic data): product **1349 passed, 1 skipped**,
  API **154 passed, 282 warnings**, web lint/types exit 0. The Playwright run
  printed **29 `ok` cases**, including the assisted review journey and mobile
  accessibility, but the Windows runner lingered after server shutdown and was
  interrupted; **no browser exit-0 claim**. An earlier concurrent product/API
  run had one process-race startup timeout; isolated and sequential reruns
  passed. No real-model run or human study was done for spec 019.
- A fresh independent review was requested under the superpowers review
  process but could not run because the workspace owner spend cap was reached;
  **approval is not claimed**. Next: independent review when available, clean
  browser/CI exit, then a supervised synthetic live-model check. Existing Word
  temporary-file lock remains a release risk. No merge, push, or deployment.

Latest spec-019 code commits: `060a45e`, `dcf1a50`, `51da087`, `fc61fec`,
`9313a98`, `28fe54f`, `a92fe4f`. New
decision/experiment: `decisions/042-*`, `discovery/experiments/2026-10-12-spec-019-tailor-review.md`.

## START HERE (2026-10-11) — specs 016–018 local fixes

This section supersedes older state below. Branch is `codex/truthful-tailoring-sources-publication`,
forked from main `a993491`. **Not merged or pushed.** Preserve `.claude/settings.local.json`.
Read specs 016–018, decisions 038–041 and both
`discovery/experiments/2026-10-11-specs-016-018-fixes.md` and
`discovery/experiments/2026-10-11-independent-review-and-live-streamlit.md` before changing these paths.

- Exact original activity guards new tool-use claims across Word/free-form, refinement,
  manual edits, Accept/rebuild and final PDF checks. Generic analytics does not establish
  Qualtrics; unknown explicit platforms stay Check yourself. Named tools share one vocabulary;
  summaries cannot attach broad skill mentions to a new employer/project. R&D is not R.
  Decision 018's global matcher and old review compatibility are retained.
- A one-off file does not replace canonical facts or confirm optional facts. Effective
  provenance/hash are frozen, so profile edits flag those reviews. Both apps show Resume file
  and Facts; selecting another upload cannot rename an existing review's source. One-off Word
  files are not promised full sync; independent uploads do not create master facts.
- Both actual batch hooks stage privately. Current execution/running-item ownership is checked
  under the recovery lock before publishing immutable bytes and the atomic review. Stop drains
  its owned job; failed saves remain resumable. API callbacks respect lock order and cannot
  overwrite a new batch or single run. Actual frontend and two-process races/junction safety pass.

Final local checks: **product 1329 passed, 1 skipped; API 148 passed, 282 warnings;
lint/types clean; Playwright 23 passed**. All exit 0; no new Linux/remote CI is claimed.
Latest code commits: `e92d9e6`, `6ddef84`, `b044535`, `4a7d591`, `352407b`, `9f114ff`, `bcb90cd`,
`2be3189`. HEAD may be a documentation-only follow-up.

**Review completed:** the same read-only reviewer resumed, found additional summary/list,
Rust/lowercase-platform and Streamlit one-off-source gaps; RED/GREEN follow-ups fixed them.
It approved the final code with no remaining critical/important findings. Supplemental tests
preserve products after determiners without inventing `any`/`unless` as platforms.

**Live checks completed with retries:** the original API no-answer job recovered through Continue
and reached 2/2. Its original cause is unproven; the model bridge was not speculatively changed.
Real Streamlit background, Stop/current drain, Continue, actual process interruption/restart
detection and preserved completed review were exercised; its batch also reached 2/2. All four
saved PDFs passed and read back as one page. No meaningful model edits were proposed by this fixture.

**Open release risk:** two real Streamlit attempts failed while cleaning a Word-locked temporary
`tailored.docx`; retries recovered but the converter/document lifetime bug remains unresolved.
Next: spec/reproduce exception-safe Word conversion/cleanup, then P01–P03 and the release checklist.
Do not kill the user's Word processes or hide cleanup exceptions. Human participants: **0**.
All-profile invalidation/PID-reuse heartbeat fallback remain. No merge/push/deployment authorized.

**Rollout:** restart both frontends together. Persistent `msvcrt`/`fcntl` OS locks replace
exclusive-create locks; old executable versions must not share this data folder. Existing
batch IDs/options and format-2 reviews remain compatible. Windows locks were exercised; POSIX
awaits CI. Node is `D:/Yang/Software/cursor/NodeJs/node.exe`. Use explicit synthetic scratch data,
existing separate venvs and `LITELLM_MODE=PRODUCTION`; personal data/home `.env` stay out of scope.

**Local deletion follow-up (2026-10-12):** commit `1fa2399` fixes Windows account deletion of
deep batch-staging paths. The first live retry then hit sandbox access denied inside
`product/.venv/tmp-codex`, not a file lock. The local API now uses the ignored, writable
`.codex-pytest-live-data` at the repository root as `JOB_COPILOT_DATA_DIR`; use a writable
scratch folder outside `.venv` when restarting it. The old local test user folder was removed,
and a delete through the web proxy returned 200, removed its user folder, and left no resume.
This is local synthetic data only; the fix has not been pushed.

**Local Jobs search follow-up (2026-10-12):** a sandboxed API process could not open outbound
connections (`WinError 10013`), so all 75 public boards reported unavailable in ~0.1 s.
The same Greenhouse endpoint returned HTTP 200 with approved network access. The local API
was restarted with that access and the same `.codex-pytest-live-data` folder; the saved
Manager search then reached all 75 boards and displayed 2,629 roles in the web UI. When
relaunching locally, give the API outbound access to the public board hosts. No search code
change or push was needed.

## Historical update — spec 015 release verification

This section supersedes everything below it. The older sections are history; trust the code, the
`specs/` and the `decisions/` over them.

**Spec 015 / decision 037 (newest):** Next.js is primary; retain maintained Streamlit.
Real `codex-cli` browser runs passed a three-job batch, Stop/Continue, actual test-server
restart, profile-stale guards and single-job redo. Fixes protect draining batch ownership,
cross-process recovery, execution state, Streamlit progress visibility/refresh, and Apply's
actual PDF/profile freshness. Windows profile saves tolerate brief read contention. A seeded
synthetic Summary/Skills review exposed a manual-edit newline bug; the fix preserves section
boundaries, including missing sections at EOF, without changing decision 018's matcher.
The real PDF model run proposed skills only: the seeded summary is not model evidence.

Final local tests: **product 1264 passed, 1 skipped; API 139 passed (276 existing warnings);
web lint/types clean; Playwright 22 passed, all exit 0**. Read decision 037 and
`discovery/experiments/2026-10-10-release-readiness.md` for exact results and release/CI status.
The builder authorized this release's commits and push; that is not standing permission to
push future work. Earlier "not pushed" statements below describe older sessions.
Release **`bbe372f` was pushed and all five CI jobs passed** on 2026-10-11:
[GitHub run 38173714857](https://github.com/ysj1995sss/yang95_msb341/actions/runs/38173714857).
Remote Linux counts: product **1265 passed**, API **139 passed** (274 warnings), browser
**22 passed**; web production build and API image startup also passed. This handoff update
is a documentation-only follow-up. See `git log` and the newest GitHub run for later revisions.

Node now lives at `D:/Yang/Software/cursor/NodeJs/node.exe` (not `_bak/NodeJs`). Tests/live
runs used only explicit ignored scratch directories and synthetic fixtures. Do not use the
builder's real data, touch the unrelated home `.env`, or stage `.claude/settings.local.json`.

Next priorities: precise project/tool evidence and one-off-upload wording need their own
spec/reproduction. All-profile invalidation and the three-minute PID/heartbeat fallback remain;
execution IDs do not fence an obsolete model hook's artifact writes after false recovery.
Use `docs/release-readiness-checklist.md` for deployment, backup/restore, real Google/Gmail,
Chrome runtime/store, manual screen readers and P01–P03 sessions. No public web deployment,
mailbox check, Chrome publishing, manual screen-reader pass or independent human test was
performed. Three agent walkthroughs are labeled separately; actual human participants: **0**.

**Spec 014 update (2026-10-07, historical baseline):** batches use one shared runner
(`product/resume_tailorer/batch_runner.py`) in both apps. A batch stopped by a restart, a failure
or "Stop" can be continued with its saved options (`POST /v2/batch/continue`). Reviews record the
Career Profile version (`profile_version`); a later profile edit flags them ("Profile changed")
and `prepare_jobs` returns `tailor_again` instead of tracking them. "Tailor again"
(`POST /v2/batch/again`) redoes one job inside the batch. Streamlit batches run in the background
with a self-refreshing fragment. Read `specs/014`, decision 036 and
`discovery/experiments/2026-10-spec-014-batch-polish.md`. Local verification: product 1,240
passed (1 skipped); API 134; web lint/types clean; 22 Playwright cases passed. Not pushed yet.

**Spec 013 update (2026-10-06):** people can add public Greenhouse, Lever, Ashby and
SmartRecruiters career boards (verified with the platform, saved per person in `custom_boards`,
searched with the 75 curated boards, failures named per board). The sponsorship filter keeps
unstated jobs, labeled. Shared search help (`ui/search_help.py`) names the filters that hide
roles and offers broader titles. Read `specs/013`, decision 035 and
`discovery/experiments/2026-10-spec-013-custom-boards.md`. Local verification: product 1,225
passed (1 skipped); API 132; web lint and types clean; 21 Playwright cases passed with a clean
exit. Committed locally and not pushed (the builder asked to push only on request).

**Spec 012 update (later 2026-10-06):** Word profile sync now covers identifiable contact,
summary, role title/date/location, skills/tools, education and certifications. Ambiguous
contradictions stop the Word artifact. PDF/free-form summary and skills edits have independent
review rows and saved spans; format-2 reviews remain compatible. Read `specs/012`, decision 034
and `discovery/experiments/2026-10-spec-012-supervised-runs.md` before changing this path.
Final local verification: product 1,154 passed, 1 skipped; API 118 passed; web lint/types passed;
all 20 Playwright cases reported `ok` on fresh data, though the runner lingered during Windows
shutdown and was stopped. The real-model Word run passed; a real-model PDF run blocked unsupported
claims, then rebuilt with only the expected visual-comparison warning after rejection. CI after
push must still be checked separately.

### 1. Where things stand

- **`main` is green in CI.** The last commit verified is `6281e4a`; all five jobs pass (product,
  api, web, web-e2e, api-image).
- **Two frontends share one Python engine** (`product/resume_tailorer`):
  - **New web app:** `apps/web`, Next.js 16 and Tailwind (spec 009, decisions 028–029). It talks
    to the FastAPI workspace API at `apps/api/app/workspace` (`/v2/*`) through the proxy
    `apps/web/src/app/api/backend/[...path]`. **Not deployed yet.**
  - **Old Streamlit app:** `product/resume_tailorer/app.py` plus `pages/`. Still live on Streamlit
    Cloud and still maintained; tag `ui-streamlit-v1`. **Do not delete it.**
- **Test baseline:** `product/` 1126 passed (1 skipped), `apps/api/` 117 passed, web lint and
  types clean, 20 Playwright tests.
- **Work done in the last sessions** (read these decisions; do not re-litigate them without new
  evidence):

| Area | Spec / decision | What it covers |
|---|---|---|
| Weak spots | decision 030 | durable runs, pasted job descriptions, per-run model, Your data (export, delete, sign out everywhere), limits, request ids, paging, dark theme, the browser helper attaching the resume, Gmail sync (testing mode), `/privacy`, error-alert webhook, time zones, a SQLite thread-safety fix |
| Codex as the model | decision 031 | the `codex-cli` model runs on the builder's ChatGPT plan through the Codex CLI. Local only; the API refuses it for signed-in users. |
| ATS help | spec 010 / decision 032 | no ATS score or 85% target. A requirement review (`analyzers/requirement_review.py`) lists each requirement as direct, transferable, partly supported, mentioned only, unconfirmed, check yourself, or no evidence, citing the exact profile passage. Tailoring may only make confirmed evidence clearer, with code guards on both paths. A local readability check (`pdf/readability.py`). |
| Profile, batches, keywords | spec 011 / decision 033 | see below |

- **Spec 011 / decision 033 in detail:**
  - **Tailoring from the Career Profile:** a Word file is first synced to the profile
    (`docx_export/profile_sync.py`), with roles matched by employer and title and the file's
    bullet order kept.
  - **Per-term statuses** and **one gap system** on every screen.
  - **A Keywords panel:** added in this version, still left out and why, not changed and why.
  - **Broader recognition:** a wider vocabulary, spelling variants, and requirement sentences in
    postings without headings.
  - **The model answers every target** with a rewrite or a reason.
  - **Two PDF readers** plus Word-file checks.
  - **Batches** of up to 10 jobs (`resume_tailorer/batch.py`, `apps/api/app/workspace/batch_router.py`).
    They never submit anything.
- **Supervised-run records** (real model, real Word):
  - `discovery/experiments/2026-10-ats-requirement-review.md`
  - `discovery/experiments/2026-10-spec-011-supervised-runs.md`

### 2. Recommended next work (in order)

Follow `AGENTS.md`: draft a spec in `specs/` before building, show the plan, and wait for the
builder's approval. Then build in small verified commits, and record decisions in `decisions/`.

1. **Spec 013 follow-ups:** support EU-hosted Greenhouse and Lever boards; clean up the repeated
   `gh_jid` in Greenhouse links; consider Workday as the next source (no public JSON API, so it
   needs its own spec); have a person add a real board through the web page.
2. **Spec 012 follow-up:** Test one additional anonymized Word template with unusual contact or
   education layout, and investigate the Playwright shutdown hang. Do not loosen fail-closed
   matching without a reproduction.
3. **Batch follow-ups (spec 014 is done):** run the Streamlit background batch once with the real
   model in a browser; consider warning only when facts the resume uses changed.
4. **Recognition:**
   - add vocabulary for fields the builder targets (`analyzers/ats_keywords.py`, `GENERIC_TERMS`,
     `AMBIGUOUS_ACRONYMS` in `requirement_review.py`);
   - make confirmation per fact instead of per section (`profile_store.fact_paths`).
5. **Deployment, Google sign-in and Gmail, and the Chrome Web Store.** These need the builder's
   accounts; ask first. The guides are spec 009 "Deploying", `extension/STORE.md` and decision 030.
6. **Supervised user tests** with 2–3 people (Sprint 2). This is the biggest unknown.

The builder also flagged a strategic question: two frontends double every feature. Raise "retire
Streamlit after the web app is deployed" with them; don't decide it alone.

### 3. How to run and verify

**Machine gotchas (builder's Windows PC):**

- **Node.js is off PATH.** A Cursor update moved it to `D:\Yang\Software\cursor\_bak\NodeJs`. In a
  shell, prepend it: `export PATH="/d/Yang/Software/cursor/_bak/NodeJs:$PATH"` (Git Bash). The
  `codex` CLI also needs Node on PATH. The builder may reinstall Node; then this isn't needed.
- **Two Python setups.** The system Python (3.14) runs the API, the e2e server and the product
  tests. `product/.venv` exists for Streamlit.
- **The console encoding is GBK.** Use `PYTHONIOENCODING=utf-8` when printing non-ASCII.
- **A stray `.env`.** `C:\Users\ysj19\.env` belongs to another project. `llm/client.py` sets
  `LITELLM_MODE=PRODUCTION` so litellm ignores it. Don't remove that line.

**Commands:**

```bash
# Product engine tests
cd product && python -m pytest -q

# API tests
cd apps/api && PYTHONPATH="../../product:$(pwd)" python -m pytest tests -q -m "not live"

# Web: lint, types, browser tests (Playwright starts its own stubbed API and web server)
cd apps/web && npx eslint src e2e && npx tsc --noEmit && npx playwright test

# Run the new site locally (single-user, no sign-in). Data goes to ../job-copilot-local-data
python apps/api/scripts/run_local.py --codex --node-dir "D:/Yang/Software/cursor/_bak/NodeJs"
cd apps/web && npm run dev    # then open http://localhost:3000
```

- **Model choice:** `--codex` uses the builder's ChatGPT plan through the Codex CLI. Without it,
  the model comes from `product/.env` (`LLM_MODEL`, `LLM_API_KEY`). **Never print or commit
  keys.**
- **The builder's real data** is in `D:\Yang\Vibe Coding\job-copilot-local-data` and
  `~/.job_copilot`. Read it only to debug what the builder reports; never commit it. Tests and
  fixtures use synthetic people only (Riley Park, Acme Retail and so on).

### 4. Rules that matter most here

- **Truthfulness:**
  - Never add a skill, credential, number, duration or result the person hasn't confirmed.
  - Never hide keywords.
  - Never promise an ATS score, pass rate or ranking.
  - Missing requirements stay visible as gaps.

  The guards are `requirement_review.introduced_unsupported` and the checks in
  `tailorer/docx_bullet_tailorer.py::_parse_and_validate`; they must stay.
- **Never submit an application.** Apply only tracks; Auto stays not offered (decision 016).
- **Both apps:** keep the Streamlit app and the web app saying the same thing. Shared text and view
  models live in `product/resume_tailorer/ui/` (`ats_explainer.py`, `requirement_review_view.py`,
  `job_view.py`); the API serves them to the web app.
- **Compatibility:** saved reviews (`review_store`, format 2) must keep loading. New dataclass
  fields need defaults; never rename stored enum values. There's a real pre-change fixture:
  `product/tests/fixtures/ats/legacy_review_format2.json`.
- **Before claiming "done":** run all three suites. For tailoring-quality changes, also do one
  supervised run with the real model (see the experiment records for the script approach) and
  write it up in `discovery/experiments/`.
- **Commits:** small and verified. End each message with the co-author line the builder uses.
  Push to `main` (CI runs on push).

### 5. Open items only the builder can do

- Rotate the Gemini API key that was pasted in a chat earlier.
- Move or rename `C:\Users\ysj19\.env`.
- Reboot the live Streamlit app.
- Reinstall Node.js.
- Choose and set up hosting (Render and Vercel are prepared: `render.yaml`, `apps/api/Dockerfile`).
- Set up the Google OAuth client and its test users.
- Get a Chrome Web Store developer account.
- Decide whether to pay for a stronger model.
- Review the two supervised-run records.

---

## Latest update (2026-10-04, later) — Jobs workspace and site polish

- **Spec 008 / decision 026.** Jobs has no stepper:
  - state comes from `ui/jobs_state.py`;
  - results use a list/detail workspace;
  - the detail panel puts the evidence first.
- **Persistence.** `active_job_id` and `active_handoff` in the Career Profile record let a new
  session reopen the chosen job and its tailored resume (`active_job.py`).
- **Home, Career Profile, Apply and Tracker:** a Home readiness checklist, a Career Profile
  section summary, empty-state guidance on Apply and Tracker, and a compact local-demo status.
- **Test baseline:** `product/` 925 passed, `apps/api/` 70 passed.

## Latest update (2026-10-04) — guided workflow redesign

- **Spec 007 and decision 025:** six destinations (Home, Career Profile, Jobs, Tailor, Apply,
  Tracker) replace the five tool-named workspaces and the global ribbon.
- **Career Profile storage:** one JSON file per user plus immutable resume versions, in the
  user's data folder (`product/resume_tailorer/profile_store.py`, `profile_import.py`). The
  Streamlit app no longer logs in to the FastAPI service; the API is unchanged for its own clients.
- **Moved:** tailoring is `pages/5_Tailor.py`; `app.py` is Home. View logic is in pure modules
  under `ui/` (`home_state`, `profile_readiness`, `job_view`, `tailor_progress`,
  `apply_readiness`, `tracker_views`).
- **Apply:** no typed job ID or PDF path; Manual is the only available mode; "Mark as applied"
  records the user's own status change.
- **Test baseline:** `product/` 874 passed, `apps/api/` 70 passed.

## Latest update (2026-09-29) — read this first

This document's body predates the work below. Where they disagree, this section and the listed
decisions win.

- **Discovery (`decisions/020`):**
  - Greenhouse only, 36 verified company boards.
  - No placeholder jobs.
  - Industry, level and job-type filters are applied.
  - Whole-word title matching.
  - The dashboard is scoped to the latest search run.
- **External audit, tasks 1–4 (`decisions/021`):**
  - Validation fails blank PDFs and unreviewed flagged claims.
  - One download rule: FAIL artifacts are never returned.
  - Regeneration uses the run's exact resume version.
  - One shared career profile (`session_profile.py`).
  - Job switching and the Launchpad handoff (`tailoring_session.py`).
  - Manual mode needs no ATS parsing, and previews never persist.
  - Every real-submit failure is audited.
- **Audit task 6 (`decisions/022`):**
  - One bounded length-correction pass (`artifacts/length_control.py`) and a freeform page
    limit.
  - An approved-only answer bank for custom questions.
  - Specs `005` (status sync) and `006` (browser Assist mode) are not built.
- **Audit task 5 (`decisions/023`):**
  - Google sign-in via Streamlit when `[auth]` is configured.
  - Per-user data folders under `JOB_COPILOT_DATA_DIR`.
  - The API refuses unsafe production config (`APP_ENV=production`).
  - Not deployed yet: follow the checklist in 023.
- **Audit task 7:**
  - CI runs both suites on every push.
  - LLM timeouts and bounded retries.
  - Persistence errors are surfaced instead of swallowed.
  - Batched triage reads and cached fit scores.
  - Dead dashboard code removed.
- **Test baseline:** `product/` 786 passed, `apps/api/` 70 passed.

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
cd product && ./.venv/Scripts/python.exe -m pytest -q          # expect 786 passed
cd apps/api && ./.venv/Scripts/python.exe -m pytest -q          # expect 70 passed
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
