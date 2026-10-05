# CLAUDE.md

Loaded at the start of every Claude Code session in this repo. Keep it current. It should let
a brand new session act like a colleague who already knows what you are working on and why.

## What I am working on

- **My role:** Product decisions, engineering/coding, and interface design. I'm building the full product end-to-end.
- **What it is:** An automated job application tool that helps job seekers reduce repetitive work by tailoring resumes, searching jobs across multiple boards, and auto-applying.
- **Who it is for:** Job seekers navigating the current job market who want to spend less time on repetitive application tasks.
- **Who uses my work:** Job seekers, starting with peers and word-of-mouth during testing; future go-to-market via online advertising.
- **Why they would use it:** Job applications are tedious and repetitive. This tool automates resume tailoring, job matching, and application submission.

## Current state

- **Where we are:** Sprint 2 (Steps 3–9 job discovery) is in progress, and all 24 spec steps
  exist on `main`. A 2026-09-29 external audit was worked through in full: tasks 1–4 are in
  `decisions/021`, task 6 in `decisions/022`, and task 5 in `decisions/023`.
  - **Discovery:** real Greenhouse, Lever and Ashby results only (63 company boards, no
    placeholder jobs), with goal filters that actually filter (`decisions/020`).
  - **Validation:** blank PDFs and unreviewed made-up claims fail; failed artifacts are never
    handed out.
  - **Regeneration** uses the run's exact resume version.
  - **Weak-spot fixes (2026-10-04, decision 027):** whole-term skill matching
    (`analyzers/term_match.py`), typed bullets and one-line job headers, model fallback and
    length trimming in tailoring, faster search (shared board cache, background warm-up),
    Tailor reviews saved per job, new deploys picked up without a reboot (`code_freshness.py`),
    and Assist as a copy-ready application kit on Apply. Auto is not offered.
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
  - status sync from Gmail (`specs/005` slice 2; slice 1, pasting an email into Tracker, is built);
  - resume upload in the browser helper (`extension/`, spec 006 v0.1 fills the form and never
    submits; not yet tried on a live form). Auto is not offered;
  - LinkedIn, Indeed and Handshake are not offered (no public job API). Live sources:
    Greenhouse, Lever, Ashby and SmartRecruiters.
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

- **Stack:** Python (resume_tailorer package), Streamlit UI with built-in Google sign-in, any LiteLLM-supported model (`product/resume_tailorer/llm/`), pytest, reportlab/PyMuPDF for PDFs, python-docx for the DOCX splice pipeline, Greenhouse live job search (LinkedIn/Indeed/Handshake demo only), FastAPI backend in `apps/api/`.
- **How work ships:** push to `main` → Streamlit Community Cloud redeploys `product/resume_tailorer/app.py`. Multi-user deployment needs the `decisions/023` checklist first (Google OAuth secrets, durable `JOB_COPILOT_DATA_DIR`).
- **Testing and style:** pytest; CI (`.github/workflows/tests.yml`) runs both suites on every push, on Python 3.14 with the pinned versions in `product/requirements.txt`. Run both before claiming anything is done: `product/` currently 1043 tests, `apps/api/` currently 70.

## Working with me

- Ask before large refactors or before adding a dependency.
- When I am wrong about something technical, say so directly and explain why.
- Show me the plan before executing anything that touches more than a couple of files.

## Voice

Writing other people read (product copy, marketing, memos) sounds like: clear and direct, focused on the job seeker's time saved and confidence; "Stop spending 2 hours tailoring your resume for every application. We do it in 5 minutes."
