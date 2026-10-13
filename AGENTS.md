# AGENTS.md

Loaded at the start of every Codex session in this repo. Keep it current. It should let
a brand new session act like a colleague who already knows what you are working on and why.

## What I am working on

- **My role:** Product decisions, engineering/coding, and interface design. I'm building the full product end-to-end.
- **What it is:** An automated job application tool that helps job seekers reduce repetitive work by tailoring resumes, searching jobs across multiple boards, and auto-applying.
- **Who it is for:** Job seekers navigating the current job market who want to spend less time on repetitive application tasks.
- **Who uses my work:** Job seekers, starting with peers and word-of-mouth during testing; future go-to-market via online advertising.
- **Why they would use it:** Job applications are tedious and repetitive. This tool automates resume tailoring, job matching, and application submission.

## Current state

> **Newest (2026-10-13, evening, Claude Code):** live on Vercel + Google Cloud Run with Groq (spec 023).
> Read the top "START HERE (2026-10-13, evening)" section of `HANDOFF-TO-CODEX.md` first: today's code
> review, dogfood fixes, what is open, and that the backend still needs redeploying.

> **Newest (2026-10-12, later, Claude Code):** read the top "START HERE" section of either handoff
> first. Decision 043 changed the product direction (auto-apply, levels 1–3 tailoring, online,
> website only). Streamlit is retired (spec 021, tag `ui-streamlit-v1`); ignore older notes about
> keeping both frontends. Glossary: `CONTEXT.md`. The builder doesn't read code; explain plainly.

> **Newest local work (2026-10-12, spec 019):** the Tailor review redesign is
> implemented on `codex/truthful-tailoring-sources-publication`, not merged or
> pushed. Read `specs/019-tailor-review-clarity-batch-and-ai-assisted-decisions.md`,
> decision 042 and `discovery/experiments/2026-10-12-spec-019-tailor-review.md`
> before modifying review decisions. Both UIs now offer manual (default) or
> conservative AI-assisted review before a new run, full before/after text,
> distinctive queue titles, and atomic selected accept/keep-original actions.
> Shared revisioned persistence prevents stale Streamlit/API saves; legacy
> decision origin is shown as unknown. AI assistance uses deterministic checks
> and a strict no-omission gate, not a second model. Full product/API and browser
> evidence is in the experiment and handoffs. Independent review was blocked by
> the owner spend cap; Windows Playwright printed passing cases but did not
> exit cleanly. Preserve `.claude/settings.local.json`; no push/merge/deploy was
> authorized. The Word conversion lock and 0 human participants remain open.

> **Newest state (2026-10-11):** read the specs 016–018 local-fixes update at the top of `HANDOFF-TO-CODEX.md`
> first. The fixes are on `codex/truthful-tailoring-sources-publication`, not merged or pushed.
> It covers the Next.js web app (`apps/web`), specs 009–018, decisions 028–041, how to
> run and test on the builder's PC, and the recommended next work. The notes below are older.

- **Latest fixes:** exact-source project/tool guards across artifact/manual/refinement/final
  paths, named-platform evidence, frozen effective facts/provenance with file-versus-facts
  disclosure, and execution-owned staged batch publication in both apps. Read decisions
  038–040 and `discovery/experiments/2026-10-11-specs-016-018-fixes.md` before changing these.
- **Review/live update:** independent code review approved after additional reproduced/fixed
  gaps. The original no-answer batch recovered with Continue; its root cause is unproven.
  Real-model Streamlit background/Stop/Continue/process restart reached 2/2 after retries.
  **Open release risk:** two real Word conversions left `tailored.docx` locked during temporary
  cleanup; successful retries do not fix it. Before conversion work, read decision 041 and
  `discovery/experiments/2026-10-11-independent-review-and-live-streamlit.md`.
  Human participants: 0. No merge/push/deployment/new account authorized.
- **Lock rollout:** restart both frontends together. Persistent OS locks replace exclusive-create
  locks; old executable versions must not share the data folder. PID/heartbeat detection remains.

- **Where we are:** Sprint 2 (Steps 3–9 job discovery) is in progress, and all 24 spec steps
  exist on `main`. A 2026-09-29 external audit was worked through in full: tasks 1–4 are in
  `decisions/021`, task 6 in `decisions/022`, and task 5 in `decisions/023`.
  - **Discovery:** real Greenhouse, Lever, Ashby and SmartRecruiters results only (75 curated
    company boards, no placeholder jobs), with goal filters that actually filter (`decisions/020`).
  - **Release safeguards (2026-10-11, spec 015 / decision 037):** real-model browser batches
    passed Stop/Continue, restart and profile-change/single-job redo checks on synthetic data.
    Stop drains the current job before allowing more work; execution IDs protect batch state.
    Apply checks profile freshness and the handed-off PDF against the current review, including
    direct download/Track actions. Windows profile saves retry brief file contention. Manual
    section edits preserve heading boundaries. Next.js is primary; keep Streamlit maintained.
    Evidence: `discovery/experiments/2026-10-10-release-readiness.md`. Three agent walkthroughs
    are not independent user research (0 human participants). Deployment/integration/accessibility
    and participant checklists: `docs/release-readiness-checklist.md`. Account-dependent checks
    remain unverified; do not claim a public web deployment or manual screen-reader pass.
    Release `bbe372f` is pushed; all five CI jobs passed (GitHub run 38173714857).
    Linux verification: product 1265 passed, API 139 passed, browser 22 passed.
  - **Added company boards (2026-10-06, spec 013 / decision 035):** a person can paste a public
    Greenhouse, Lever, Ashby or SmartRecruiters board link; it's verified with the platform's API,
    saved in their profile record (`custom_boards`, up to 25), and searched with the curated
    boards. Failures are named per board. "I need visa sponsorship" keeps unstated jobs, labeled.
    Shared search help (`ui/search_help.py`) explains filters and offers broader titles.
  - **Batch polish (2026-10-07, spec 014 / decision 036):** one batch runner for both apps
    (`resume_tailorer/batch_runner.py`, state in `tailor/batch.json`); a batch stopped by a
    restart, failure or stop can be continued; reviews record their Career Profile version, and
    a later profile edit flags them and blocks "Prepare" until tailored again. Streamlit batches
    run in the background.
  - **Validation:** blank PDFs and unreviewed made-up claims fail; failed artifacts are never
    handed out.
  - **ATS help (2026-10-05, spec 010 / decision 032):** an evidence-based requirement review and a
    local readability check replace any ATS-style score. Never promise an ATS pass, score or ranking.
  - **Complete profile sync and review (2026-10-06, spec 012 / decision 034):** identifiable
    Career Profile fields reach a copy of the Word file; ambiguous contradictions block the
    artifact. PDF/free-form summary and skills edits are independent, safely anchored review
    choices. Both apps share labels and guards; legacy format-2 reviews still load.
  - **Regeneration** uses the run's exact resume version.
  - **Jobs workspace (2026-10-04, spec 008 / decision 026):** Jobs is a stateful list/detail
    browser driven by `ui/jobs_state.py`; the chosen job and its tailored resume persist across
    sessions; Career Profile is a section summary with one editor.
  - **Guided workflow (2026-10-04, spec 007 / decision 025):** six destinations (Home, Career
    Profile, Jobs, Tailor, Apply, Tracker). The Career Profile is stored once per user
    (`profile_store.py`, versioned resume files, per-fact provenance) and reused everywhere; the
    Streamlit app no longer needs the separate API login. Tailoring moved to `pages/5_Tailor.py`;
    `app.py` is Home.
  - **Manual mode** needs no ATS parsing; previews never save anything.
  - **Length:** one bounded length-correction pass, and a hard page limit on freeform.
  - **Custom application answers** come only from the user's approved answer bank.
  - **Sign-in:** Google sign-in (when `[auth]` is configured) and per-user data folders.
- **Deployed (2026-10-13):** website on Vercel, backend on Google Cloud Run, model Groq, for a
  supervised test with no sign-in and one shared workspace (decision 045). Setup and the backend
  update commands: `specs/023-free-test-deployment.md`. The old Streamlit demo is deleted.
- **Not built (specs only):**
  - status sync (`specs/005`);
  - browser Assist mode (`specs/006`) — Assist/Auto still can't fill real JavaScript ATS
    forms (`decisions/012`);
  - LinkedIn, Indeed and Handshake are demo data only.
- **Biggest open risk:** nobody other than the builder has used the full search → tailor → apply
  loop. Next: supervised tests with 2–3 people, then the Sprint 2 review.
- **Where to see it:** the website `apps/web/src/app/` (Home, Career Profile, Jobs, Tailor, Apply,
  Tracker) on the workspace API `apps/api/app/workspace/`. Engine logic lives in tested modules
  under `product/resume_tailorer/` (view logic in `ui/`).
- **Handoff docs:** `HANDOFF-TO-CLAUDE-CODE.md` and `HANDOFF-TO-CODEX.md`, both pointing at the
  same `decisions/` history.

## How this repo works

- Non-code work is committed as files, same as code. Interviews, experiments, pricing models, and usability findings all live here.
- Specs go in `specs/` and are written before the work. When asked to build or produce something non-trivial, check for its spec first. If there is none, draft one and confirm it before starting.
- Meaningful choices get a numbered record in `decisions/`, written when the choice is made, including what was rejected and why.
- Sprint plans and reviews live in `sprints/`. The plan is committed on day one.
- Never put real names, emails, or phone numbers in this repo. Anonymize.

## Tools and conventions

- **Stack:** Python (`resume_tailorer` engine), FastAPI workspace API (`apps/api`), Next.js 16 website (`apps/web`), an LLM through LiteLLM (`product/resume_tailorer/llm/`), pytest and Playwright, reportlab for PDF generation, python-docx for the Word splice pipeline, live job search on Greenhouse, Lever, Ashby and SmartRecruiters.
- **Two separate venvs:** `product/.venv` (core engine + Streamlit) and `apps/api/.venv` (FastAPI backend). Set `PYTHONPATH` to include `product/` when running Streamlit or product tests directly.
- **How work ships:** push to `main` and Vercel redeploys the website. The backend is rebuilt by
  hand on Cloud Run (`cloudbuild.yaml`, then the deploy command in spec 023).
- **Testing and style:** pytest; CI (`.github/workflows/tests.yml`) runs every suite on each push,
  on Python 3.14 with the pinned versions in `product/requirements.txt`. Last full local run
  (2026-10-13): `product/` 1372 passed (1 skipped), `apps/api/` 169 passed, web lint and types clean,
  33 Playwright cases passed. Run fresh checks before claiming anything is done. Web:
  `cd apps/web && npx eslint src e2e && npx tsc --noEmit`; browser tests `npm run test:e2e` (starts its
  own stubbed API and web servers; stop any local dev server in `apps/web` first).
- **Builder runtime:** Node is now `D:/Yang/Software/cursor/NodeJs/node.exe`; the older `_bak/NodeJs` path is absent. Use synthetic scratch data for tests, never `job-copilot-local-data` or the default personal data folder. Preserve `.claude/settings.local.json`.

## Working with me

- Ask before large refactors or before adding a dependency.
- When I am wrong about something technical, say so directly and explain why.
- Show me the plan before executing anything that touches more than a couple of files.

## Voice

Writing other people read (product copy, marketing, memos) sounds like: clear and direct, focused on the job seeker's time saved and confidence; "Stop spending 2 hours tailoring your resume for every application. We do it in 5 minutes."
