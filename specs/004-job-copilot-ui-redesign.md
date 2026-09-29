# Specification 004: Job Copilot UI redesign

**Status:** Approved design, pending implementation plan  
**Date:** 2026-09-28

## Goal

Turn the existing Streamlit application into a coherent Job Copilot workspace that a new job
seeker can understand and use without knowing the system architecture. The redesign must expose
why a job or resume change is recommended, keep verified facts visibly separate from unverified
requirements, and preserve the user's final control over every resume and application action.

This is a frontend and information-architecture redesign. It does not replace the existing
product models, FastAPI contracts, scoring engine, tailoring engine, artifact pipeline, or ATS
safety gates.

## Source material and precedence

The external `job_copilot_specification_ui_design_prompt.md` is a design reference. Its useful
interaction patterns are adopted where they fit the existing product:

- a verified Fact Vault;
- evidence-backed job-match explanations;
- atomic resume-change review;
- a safe assisted-application launchpad;
- a lifecycle tracker.

Its proposed `backend/` schemas, replacement LLM prompt, new database, and autonomous submission
phases are not implementation instructions. Existing repository decisions and product-layer
interfaces remain authoritative, especially decisions 001, 012, 014, 015, 016, and 017.

## Users and primary job

The primary user is a job seeker who wants to spend less time repeating application work without
allowing AI to invent qualifications or submit applications without reliable confirmation.

The interface must make four questions answerable at a glance:

1. What facts has Job Copilot verified?
2. Why does this role match me, and what is genuinely missing?
3. Exactly what changed in my resume, and what evidence supports it?
4. What do I need to do next to complete or follow up on this application?

## Information architecture

The product is organized into five user-facing workspaces. Existing URLs and session handoffs must
remain functional during migration.

### 1. Fact Vault

Maps to the existing Profile Review functionality.

- Upload or replace a PDF/DOCX resume.
- Show the current resume version and prior versions.
- Group verified contact, education, employment, skills, tools, and certifications.
- Distinguish resume-extracted facts from user-edited facts.
- Show a concise verification summary: verified bullets, skills, and unresolved items.
- Preserve existing FastAPI-backed authentication and profile persistence.
- Do not imply that unsupported job requirements are verified facts.

### 2. Job Discovery

Maps to the existing Job Search page.

- Separate search criteria from results so the feed remains visible while filters change.
- Disclose live, limited, and demo sources before the search action.
- Present each role with company, location, compensation when known, source, quality, and posting
  age.
- Present Candidate Fit as a breakdown rather than a lone score: strong matches, partial matches,
  true gaps, and sponsorship/quality signals.
- Preserve Save, Pass, and Apply actions and the existing Apply-to-Tailor session handoff.
- Never present unknown compensation, sponsorship, or fit as zero or negative.

### 3. Tailoring Studio

Maps to the existing main `app.py` tailoring and artifact-review workflow.

- Use a split desktop layout: change-review deck on the left and resume/report surface on the
  right.
- Show original text, proposed text, reason, job requirement, evidence source, and validation
  status for every meaningful change.
- Offer Accept, Edit manually, and Keep original with consistent vocabulary through regeneration.
- Hide unchanged and punctuation-only changes by default; expose them in advanced review.
- Show unsupported requirements in a visible “Missing, never added” section.
- Keep Candidate Fit separate from Resume Alignment.
- Preserve DOCX/PDF fidelity labels and PASS/WARNING/FAIL download gates.
- A failed artifact must never be styled as application-ready.

### 4. Apply Launchpad

Extracts the submission workflow from the current combined Applications page.

- Lead with Manual mode, the only reliable submission path today.
- Stage the tailored resume, verified application URL, and known reusable profile fields.
- Provide the employer link as the primary completion action.
- Clearly disclose Assist/Auto capability limitations without rendering a wall of warning text.
- Preserve Preview-before-Submit and the hard `ATSCapability.final_submission` safety gate.
- Never visually imply that an application was submitted without reliable confirmation.

### 5. Application Tracker

Extracts the dashboard workflow from the current combined Applications page.

- Provide saved status views, filters, and sorting.
- Show company, role, applied date, mode, status, Candidate Fit at submission, resume version, and
  next action.
- Retain application detail, status provenance, history, and editable next action.
- Prefer a clear table/detail workflow for the first release. A Kanban view is optional and must
  not delay the usable redesign.

## Navigation and workflow state

A persistent product navigation names the five workspaces in user language rather than exposing
raw Streamlit filenames. A compact evidence ribbon communicates progress:

```text
Verified facts  ->  Matched role  ->  Reviewed edits  ->  Application ready
```

Each stage must display an honest state derived from existing data. It is not a decorative stepper
and must not mark a stage complete based only on navigation.

Required existing handoffs:

- Job Discovery Apply -> Tailoring Studio with job description and fit snapshot.
- Tailoring Studio approved artifact -> Apply Launchpad with resume path/version and scores.
- Apply Launchpad manual confirmation -> Application Tracker.

## Visual system

### Design concept

“Evidence workbench”: a disciplined, readable workspace where recommendations remain visibly
traceable to facts. The interface should feel precise and calm, not like a generic marketing site
or a collection of interchangeable SaaS cards.

### Color tokens

- `ink`: `#17202A` — primary text and navigation
- `action`: `#2457D6` — primary actions, selected navigation, links
- `verified`: `#187A57` — verified facts and passing validation
- `review`: `#B86E12` — warnings and human review
- `blocked`: `#B33A3A` — unsupported claims and failed validation
- `canvas`: `#F5F7FA` — application background
- `paper`: `#FFFFFF` — documents and primary work surfaces
- `line`: `#D9E0E8` — structural separators

Color is semantic. The same state must not change color between screens. Text or iconography must
also communicate status; color alone is insufficient.

### Typography

- Atkinson Hyperlegible is the preferred interface family with system-sans fallback.
- Generated resume previews preserve the artifact's document typography rather than inheriting the
  application font.
- Labels and actions use sentence case.
- Page titles use a 32–40px responsive scale; section headings use 18–22px; body copy uses 15–16px.
- Default prose line length stays below 80 characters.
- Avoid all-caps eyebrows, decorative monospace labels, and one-word headline accents.

### Shape, spacing, and hierarchy

- Use borders and background changes to encode structure, not identical floating cards everywhere.
- Reserve stronger radius and elevation for interactive overlays or focused review items.
- Use an 8px spacing base with 24–32px separation between major regions.
- Primary actions are visually unique within their region; secondary actions do not compete.
- The memorable element is the evidence ribbon, not decorative gradients or animation.

### Motion

- Use motion only to confirm a user-triggered state change such as accepting an edit or saving a
  status.
- Respect `prefers-reduced-motion`.
- Do not animate every card or section on load.

## Responsive behavior

- Desktop Tailoring Studio uses a roughly 55/45 split.
- Below tablet width, review controls stack before document preview.
- Navigation collapses to a compact selector or drawer.
- Tables degrade to readable record summaries rather than horizontal overflow where practical.
- Primary actions become full-width on narrow screens.
- The evidence ribbon may horizontally scroll but must not wrap into an ambiguous sequence.

## Accessibility

- Meet WCAG AA contrast for text and controls.
- Preserve visible keyboard focus.
- Provide text labels for status icons and color states.
- Do not rely on hover for critical evidence or explanations.
- Inputs retain explicit labels even when visually compact.
- Error copy states what failed and what the user can do next.

## Copy principles

- Use user language, not internal architecture terms.
- Actions name the result: “Save changes,” “Keep original,” “Open application,” “Mark as applied.”
- Keep the same action name in the resulting confirmation.
- Explain limitations directly and briefly.
- Never claim a submission, verification, or match fact the product cannot prove.

## Implementation boundaries

- Shared visual tokens and CSS live under `product/resume_tailorer/ui/`.
- Data shaping and display-state mapping remain in pure, testable helpers.
- Streamlit page modules remain thin rendering/adaptation layers.
- Product logic stays in `product/resume_tailorer/`; the UI must not create alternate scoring,
  tailoring, validation, or submission logic.
- No new frontend framework or product dependency is authorized by this specification.
- Existing uncommitted changes in `AGENTS.md` and `HANDOFF-TO-CODEX.md` are user-owned and outside
  this work unless explicitly incorporated later.

## Testing and verification

### Automated

- Unit tests for navigation metadata, semantic status tokens, evidence-ribbon state, display
  transformations, change visibility, and responsive-safe content structures.
- Existing product and API suites remain green.
- Existing safety tests for artifact downloads and ATS submission remain unchanged.

### Browser verification

Verify all five workspaces at desktop and narrow mobile widths:

- navigation and workflow handoffs;
- empty, loading, success, warning, and failure states;
- keyboard-visible actions;
- Tailoring Studio review/regeneration;
- Manual Apply launch and tracker update;
- no clipping or unreadable overflow.

Use anonymized or synthetic data only. Do not upload or commit a real resume during visual testing.

## Acceptance criteria

The redesign is complete when:

1. A new user can identify the five workspaces and the next action without repository knowledge.
2. Verified facts, partial evidence, true gaps, and blocked claims have distinct, consistent
   presentation.
3. Every meaningful resume change exposes its source evidence and has Accept/Edit/Keep controls.
4. Candidate Fit and Resume Alignment are presented as separate measures.
5. Manual application is the clearly recommended reliable path; unsupported real submission is
   never implied.
6. The tracker exposes application status, provenance, resume version, and next action.
7. The interface works at desktop and mobile widths with accessible focus and contrast.
8. Existing workflow, validation, persistence, and safety behavior remains intact.
9. Both full test suites pass and browser verification is recorded before completion.

## Deliberately deferred

- Replacing Streamlit with React or another frontend framework.
- Creating the attachment's alternate `backend/` package or duplicate schemas.
- Replacing the existing LLM prompt or validation pipeline.
- Browser-automated real ATS submission.
- A Kanban tracker if it compromises the completion of the core table/detail experience.
