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
  - **Discovery:** real Greenhouse results only (36 company boards, no placeholder jobs), with
    goal filters that actually filter (`decisions/020`).
  - **Validation:** blank PDFs and unreviewed made-up claims fail; failed artifacts are never
    handed out.
  - **Regeneration** uses the run's exact resume version.
  - **Connected workspaces:** the five share one career profile and hand the validated resume
    to Launchpad.
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
- **Where to see it:** `product/resume_tailorer/app.py` (Tailoring Studio) and
  `product/resume_tailorer/pages/` (Fact Vault, Job Search, Launchpad, Tracker).
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
- **Testing and style:** pytest; CI (`.github/workflows/tests.yml`) runs both suites on every push, on Python 3.14 with the pinned versions in `product/requirements.txt`. Run both before claiming anything is done: `product/` currently 786 tests, `apps/api/` currently 70.

## Working with me

- Ask before large refactors or before adding a dependency.
- When I am wrong about something technical, say so directly and explain why.
- Show me the plan before executing anything that touches more than a couple of files.

## Voice

Writing other people read (product copy, marketing, memos) sounds like: clear and direct, focused on the job seeker's time saved and confidence; "Stop spending 2 hours tailoring your resume for every application. We do it in 5 minutes."
