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

- **Where we are:** Sprint 1 (tailor) and Sprint 2 (Steps 4–9 job discovery) are both merged on
  `main`. Steps 10–15 (job analysis → tailoring → length control) were audited and rebuilt — see
  `decisions/013-steps-10-15-rebuild-summary.md`. Steps 16-20 (the validated resume artifact
  pipeline: structured validation, immutable artifact versioning, review/regenerate, Streamlit +
  API adapter parity) are built and merged — see `decisions/014` and
  `decisions/015-steps-16-20-build-summary.md`; the one deliberately-deferred piece is the bounded
  correction loop's actual condensation logic (decision 015's "known limitations"). Steps 21–24
  (application modes/submission/status/dashboard) were revised this session — see
  `decisions/016-ats-capability-model-and-hard-submission-safety-gate.md` (a real safety bug: the
  real-submit path could silently record a false "Applied" status; fixed with an explicit
  capability model and a hard gate) and `decisions/017-steps-21-24-revision-summary.md` (full
  rebuild summary: attempt tracking, idempotency, immutable job/fit snapshots, status provenance,
  a full dashboard rebuild). Assist/Auto mode still doesn't work against real ATS forms — see
  `decisions/012-assist-auto-mode-does-not-work-against-real-ats-forms.md` — but the code now says
  so honestly and refuses instead of silently pretending otherwise. Manual mode is the one
  reliable application-submission path today. Separately, the same day, a live-testing session
  (actually uploading a real resume through a real LLM, not just unit tests) found the freeform
  tailoring path's bullet-matching logic (`DiffGenerator._compute_changes`) was seriously broken
  for realistic resumes — truthful content from Education/Skills sections kept getting flagged as
  fabrication, blocking the download. Took three rounds to actually fix (two patches ran out of
  headroom before a proper global-matching rewrite held) — see
  `decisions/018-freeform-diff-bullet-extraction-was-too-narrow.md`, genuinely worth reading in
  full before touching `diff_generator.py` again, since two of the three rounds looked complete
  and weren't.
- **Next build:** (a) wire up the Steps 16-20 correction/condensation loop (decision 015), (b)
  close the freeform/PDF tailoring path's remaining gaps (no repair loop, no hard length gate —
  decision 013), (c) custom/job-specific application question answering (decision 017), (d)
  revisit Assist/Auto mode via real browser automation (decision 012 scoped this out
  deliberately — needs its own conversation before starting), or (e) something else entirely —
  nothing is currently in progress.
- **Where to see it:** `product/resume_tailorer/app.py` (tailor); `pages/2_Job_Search.py`
  (discovery); `pages/3_Applications.py` (application submission + status dashboard).
- **Biggest open risk:** real end-to-end usage by people other than the builder — the tailoring
  and discovery pipelines are verified live against real postings, but the full search → triage →
  tailor → apply loop hasn't been used by anyone else yet.
- **Handoff doc:** `HANDOFF-TO-CODEX.md` — read this when starting a new Codex session, along
  with `decisions/001`, `009`, `012`, `013`, `014`, `015`, `016`, `017`, and `018` for the
  architecture and the most recent work.

## How this repo works

- Non-code work is committed as files, same as code. Interviews, experiments, pricing models, and usability findings all live here.
- Specs go in `specs/` and are written before the work. When asked to build or produce something non-trivial, check for its spec first. If there is none, draft one and confirm it before starting.
- Meaningful choices get a numbered record in `decisions/`, written when the choice is made, including what was rejected and why.
- Sprint plans and reviews live in `sprints/`. The plan is committed on day one.
- Never put real names, emails, or phone numbers in this repo. Anonymize.

## Tools and conventions

- **Stack:** Python (resume_tailorer package), Streamlit for UI, an LLM API for tailoring (see `product/resume_tailorer/llm/`), pytest for testing, reportlab for PDF generation, python-docx + docx2pdf for the DOCX splice pipeline, multiple job board scrapers (Greenhouse live; LinkedIn/Indeed/Handshake limited/demo).
- **Two separate venvs:** `product/.venv` (core engine + Streamlit) and `apps/api/.venv` (FastAPI backend). Set `PYTHONPATH` to include `product/` when running Streamlit or product tests directly.
- **How work ships:** Streamlit app + FastAPI backend run locally; eventual deployment TBD.
- **Testing and style:** pytest for unit and integration tests; extensive fixture-based testing with real job descriptions. Run the full suite (`product/`: currently 695 tests; `apps/api/`: currently 60) before claiming anything is done.

## Working with me

- Ask before large refactors or before adding a dependency.
- When I am wrong about something technical, say so directly and explain why.
- Show me the plan before executing anything that touches more than a couple of files.

## Voice

Writing other people read (product copy, marketing, memos) sounds like: clear and direct, focused on the job seeker's time saved and confidence; "Stop spending 2 hours tailoring your resume for every application. We do it in 5 minutes."
