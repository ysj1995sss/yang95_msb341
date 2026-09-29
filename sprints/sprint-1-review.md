# Sprint 1 Review

**Window:** September 16–28, 2026
**Sessions reviewed:** 8 across 1 project
**Sessions excluded:** 26 from other directories

## When you worked

Work was front-loaded: 4 sessions on Sept 21–22 (peak), then scattered follow-up on Sept 28. The core pipeline and bug fixes were completed early; later days involved validation and hardening.

## Where you got stuck

**Resume design fidelity (Sept 16–19).** Markdown leaked into PDFs, job headers flattened, and MBA/summary sections were lost when converting between formats. Ended by reconciling headers against the profile and applying conservative formatting rules.

**DOCX editing pipeline (Sept 19–22).** Moving from regenerating PDFs to splicing edits into the original DOCX file required reworking the tailoring output. Ended by implementing a master-template splice pipeline that works for both PDF and DOCX.

**Cross-block evidence matching (Sept 21–22).** The diff generator misclassified changes across resume sections (education in a skills header, responsibilities in a different role's bullets). Ended by recognizing education/skills/responsibilities patterns globally instead of per-block.

## What took the most time

Implementing the core resume tailoring pipeline: parsing (PDF/DOCX), Claude-powered tailoring, gap analysis, alignment scoring, validation, and multi-format PDF/DOCX output. Also 9 bugs surfaced during live testing against real job postings—resume fidelity, scoring edge cases, and evidence validation. The bugs required root-cause investigation and architectural fixes, not patches.

## Axis

**Application Architecture.** The work built data models (CareerTruthProfile, JobPosting, ArtifactValidation), a multi-format parsing pipeline, Claude API integration via LiteLLM, database persistence, and a validated-artifact build pattern. The Streamlit UI and API backend share the same pipeline, avoiding the fragmentation that had required downstream fixes.

## Against your plan

**Goal was:** "Build a working MVP with a basic web form that takes a user's resume and a job description, identifies missing or relevant keywords, tailors the resume while keeping the user's experience truthful, and exports a polished one-page PDF."

**Delivered:** Working Streamlit web UI for resume tailoring, resume parsing from PDF/DOCX, job description analysis, keyword alignment scoring, Claude-powered tailoring with evidence validation, PDF export, and DOCX editing with change tracking. The feature meets the goal.

**Note:** The commits show you also shipped job search (Steps 4–9) and application tracking/submission (Steps 21–24) in this sprint—well beyond the stated MVP scope. The tailoring MVP goal was achieved, but the sprint absorbed significantly more work than planned.
