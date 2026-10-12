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

> **Newest state (2026-10-11):** read the specs 016–018 local-fixes update at the top of `HANDOFF-TO-CODEX.md`
> first. The fixes are on `codex/truthful-tailoring-sources-publication`, not merged or pushed.
> It covers the Next.js web app (`apps/web`), specs 009–018, decisions 028–040, how to
> run and test on the builder's PC, and the recommended next work. The notes below are older.

- **Latest fixes:** exact-source project/tool guards across artifact/manual/refinement/final
  paths, named-platform evidence, frozen effective facts/provenance with file-versus-facts
  disclosure, and execution-owned staged batch publication in both apps. Read decisions
  038–040 and `discovery/experiments/2026-10-11-specs-016-018-fixes.md` before changing these.
- **Release gates:** independent final review stopped at the owner spending cap after reporting
  three reproduced/fixed gaps. Live-model Stop drained one passing PDF; Continue's next call
  returned no answer and remains resumable. New live Streamlit/restart checks and actual human
  sessions remain open. Human participants: 0. No push/deployment/new account authorized.
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
- **Deployed:** https://yang95msb341-epxbfpbdegytjwcajjthay.streamlit.app runs in *local
  single-user mode* (no `[auth]` secrets, no durable disk). It is for supervised demos only;
  don't share it as a multi-user product. The deployment checklist is in `decisions/023`.
- **Not built (specs only):**
  - status sync (`specs/005`);
  - browser Assist mode (`specs/006`) — Assist/Auto still can't fill real JavaScript ATS
    forms (`decisions/012`);
  - LinkedIn, Indeed and Handshake are demo data only.
- **Biggest open risk:** nobody other than the builder has used the full search → tailor → apply
  loop. Next: supervised tests with 2–3 people, then the Sprint 2 review.
- **Where to see it:** `product/resume_tailorer/app.py` (Home) and
  `product/resume_tailorer/pages/` (Career Profile, Jobs, Tailor, Apply, Tracker). View logic
  lives in pure, tested modules under `product/resume_tailorer/ui/`.
- **Handoff docs:** `HANDOFF-TO-CLAUDE-CODE.md` and `HANDOFF-TO-CODEX.md`, both pointing at the
  same `decisions/` history.

## How this repo works

- Non-code work is committed as files, same as code. Interviews, experiments, pricing models, and usability findings all live here.
- Specs go in `specs/` and are written before the work. When asked to build or produce something non-trivial, check for its spec first. If there is none, draft one and confirm it before starting.
- Meaningful choices get a numbered record in `decisions/`, written when the choice is made, including what was rejected and why.
- Sprint plans and reviews live in `sprints/`. The plan is committed on day one.
- Never put real names, emails, or phone numbers in this repo. Anonymize.

## Tools and conventions

- **Stack:** Python (resume_tailorer package), Streamlit for UI, an LLM API for tailoring (see `product/resume_tailorer/llm/`), pytest for testing, reportlab for PDF generation, python-docx + docx2pdf for the DOCX splice pipeline, multiple job board scrapers (Greenhouse live; LinkedIn/Indeed/Handshake limited/demo).
- **Two separate venvs:** `product/.venv` (core engine + Streamlit) and `apps/api/.venv` (FastAPI backend). Set `PYTHONPATH` to include `product/` when running Streamlit or product tests directly.
- **How work ships:** push to `main` → Streamlit Community Cloud redeploys `product/resume_tailorer/app.py`. Multi-user deployment needs the `decisions/023` checklist first (Google OAuth secrets, durable `JOB_COPILOT_DATA_DIR`).
- **Testing and style:** pytest; CI (`.github/workflows/tests.yml`) runs both suites on every push, on Python 3.14 with the pinned versions in `product/requirements.txt`. Final local specs-016–018 verification: `product/` 1311 passed (1 skipped), `apps/api/` 148 passed (282 warnings); web lint/types clean and all 23 Playwright cases passed with exit 0. No new remote/Linux CI is claimed for this unpushed branch. Run fresh checks before claiming later changes are done. On Windows the runner may linger after all cases report `ok`; distinguish that from a clean exit.
- **Builder runtime:** Node is now `D:/Yang/Software/cursor/NodeJs/node.exe`; the older `_bak/NodeJs` path is absent. Use synthetic scratch data for tests, never `job-copilot-local-data` or the default personal data folder. Preserve `.claude/settings.local.json`.

## Working with me

- Ask before large refactors or before adding a dependency.
- When I am wrong about something technical, say so directly and explain why.
- Show me the plan before executing anything that touches more than a couple of files.

## Voice

Writing other people read (product copy, marketing, memos) sounds like: clear and direct, focused on the job seeker's time saved and confidence; "Stop spending 2 hours tailoring your resume for every application. We do it in 5 minutes."
