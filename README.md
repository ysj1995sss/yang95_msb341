# Job Copilot

Job Copilot helps job seekers find relevant roles, tailor truthful resumes, and finish applications with less repetitive work.

**Where to see it:** Run `product/resume_tailorer/app.py` locally with Streamlit. A public deployment URL is not recorded until one is verified.
**Built by:** yang95, MSB 341 Product Management, BYU

## Context

Fill this in during Sprint 1 and keep it current. Every sprint is read against it.

- **My role:** Product decisions, engineering/coding, and interface design. I'm building the full product myself: defining features, writing the code, and designing the user dashboard.
- **What I am working on:** An automated job application tool with a user-friendly dashboard. It asks users about their job goals (company type, industry, job title, timeline, salary expectations, sponsorship needs), finds matching jobs across job boards, analyzes job descriptions against ATS systems, optimizes their resume to match 90% ATS score while maintaining their preferred length, and auto-applies to jobs.
- **Who it is for:** Job seekers in the current job market who want to reduce time spent on repetitive job search and application tasks.
- **Who uses my work:** Job seekers, starting with peers and others who hear about it through word of mouth and Slack during the testing phase. Future go-to-market will include online advertising platforms.

If your situation changes, revise this and note what changed. That is normal; a silent
mismatch between this file and your work is not.

## What is in this repo

| Folder | What lives here |
|---|---|
| `sprints/` | One plan and one review per sprint |
| `discovery/` | Interviews, personas, what you learned about your user |
| `design/` | Flows, screens, usability test notes |
| `product/` | The work itself: code, a pricing model, a copy deck, an automation |
| `specs/` | One spec per piece of work, written before you make it |
| `gtm/` | Launch, channels, copy, experiments |
| `metrics/` | What you measure and what it says |
| `decisions/` | Numbered records of what you decided and why |

Not everyone in this course ships software. An interview, a pricing model, a landing page
draft, and a usability finding are all artifacts, and they get committed like anything else.
Use the folders that fit your role and ignore the rest.

If you build an AI feature, put its eval set in `product/evals/`. A test set is how you know
whether a change to a prompt helped or hurt.

## Running it

The Streamlit product is organized into five evidence-first workspaces:

- **Fact Vault** — upload a resume and distinguish resume-extracted facts from user edits.
- **Job Discovery** — search permitted sources and inspect strong matches, partial evidence, and true gaps.
- **Tailoring Studio** — review each supported resume edit beside validation and download evidence.
- **Apply Launchpad** — stage the job link, resume, and profile; Manual mode is the reliable path today.
- **Application Tracker** — review immutable submission snapshots, provenance, status, and next actions.

Start the local interface:

```powershell
cd product
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH=(Resolve-Path '.').Path
.\.venv\Scripts\python.exe -m streamlit run resume_tailorer\app.py
```

`apps/api/` is a multi-user FastAPI backend around the existing `product/resume_tailorer` engine — auth, persistent per-user profiles/jobs, and HTTP endpoints, modeled on the job-copilot course project's backend architecture but built on top of this repo's more complete tailoring pipeline (full resume parsing, weighted candidate-fit scoring, PDF generation with the validation hard gate).

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `http://localhost:8000/health`. Current baseline (2026-09-29): 786 product tests and 70 API tests, run in CI on every push.

Key endpoints: `POST /profile/upload` (parses a real PDF/DOCX into a full career profile), `POST /jobs/upsert` (dedupe + candidate-fit scoring), `POST /tailor/preview` (job analysis → gap report → LLM tailoring → optimization loop → PDF, requires `LLM_MODEL`/`LLM_API_KEY` in `apps/api/.env`).

The Streamlit interface and FastAPI adapter share product-layer scoring, tailoring, validation, and safety behavior; the UI does not duplicate those systems.

## Sprints

Each sprint:

```bash
/sprint-plan     # day one, then commit the plan
# ...do the work...
/sprint-review   # last day, then commit the report and write your retro
```

## Ground rules

- **Spec before work.** For anything non-trivial, the spec's commit should predate the
  work's commits.
- **Decisions get recorded.** When you make a real choice, write it in `decisions/` with the
  alternatives you rejected.
- **No real customer contact details anywhere in this repo.** Anonymize people in interview
  notes: "dental office manager, Provo" rather than a name and an email.
- **Keep `CLAUDE.md` current.** It is what your agent knows about your work. Stale context
  produces bad output.
