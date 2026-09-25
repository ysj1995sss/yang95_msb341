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

- **Where we are:** Sprint 1 tailor MVP is built. Steps 4–9 job discovery is built (first slice on `main`; dashboard/search-run/quality on PR #2 — see `HANDOFF-TO-CLAUDE-CODE.md`).
- **Next build:** Land PR #2 if still open → smoke Apply → Step 10 → then Sprint 3+ Steps 21–24 (application modes, submission, status dashboard).
- **Where to see it:** `product/resume_tailorer/app.py` (tailor); `pages/2_Job_Search.py` (discovery); `pages/3_Applications.py` (apps scaffolding).
- **Biggest open risk:** End-to-end integration (search + triage + tailor + apply) with real users; application submission not fully wired.
- **Handoff doc:** `HANDOFF-TO-CLAUDE-CODE.md` — read this when starting a new Claude Code session.

## How this repo works

- Non-code work is committed as files, same as code. Interviews, experiments, pricing models, and usability findings all live here.
- Specs go in `specs/` and are written before the work. When asked to build or produce something non-trivial, check for its spec first. If there is none, draft one and confirm it before starting.
- Meaningful choices get a numbered record in `decisions/`, written when the choice is made, including what was rejected and why.
- Sprint plans and reviews live in `sprints/`. The plan is committed on day one.
- Never put real names, emails, or phone numbers in this repo. Anonymize.

## Tools and conventions

- **Stack:** Python (resume_tailorer package), Streamlit for UI, Claude API for LLM, pytest for testing, reportlab for PDF generation, multiple job board scrapers (Greenhouse, LinkedIn, Indeed, Handshake).
- **How work ships:** Streamlit app runs locally; eventual deployment TBD.
- **Testing and style:** pytest for unit and integration tests; extensive fixture-based testing with real job descriptions.

## Working with me

- Ask before large refactors or before adding a dependency.
- When I am wrong about something technical, say so directly and explain why.
- Show me the plan before executing anything that touches more than a couple of files.

## Voice

Writing other people read (product copy, marketing, memos) sounds like: clear and direct, focused on the job seeker's time saved and confidence; "Stop spending 2 hours tailoring your resume for every application. We do it in 5 minutes."
