# Specification 007: Guided job-application workflow redesign

**Status:** Approved 2026-10-04. Open decisions resolved: 1 = A (per-user profile file), 2 = commit draft work then replace Start Here with Home, 3 = build all phases now; user tests follow.
**Date:** 2026-10-04
**Supersedes the information architecture of:** `specs/004-job-copilot-ui-redesign.md` (visual system and safety rules carry over; see "Retained").

## Outcome

A new job seeker uploads one resume, confirms the important facts, sets job preferences, finds a
real job, understands why it matches, tailors a truthful resume, and reaches the employer's
application page without getting lost or re-entering anything.

After setup the product is a repeat-use command center that answers "what should I do now?" within
ten seconds: jobs worth reviewing, resumes needing approval, applications ready to finish,
follow-ups due, and one best next action.

It is not an autonomous application bot. Nothing is submitted without reliable confirmation, and
no qualification is ever invented.

## Sources

Read in order: `AGENTS.md`, both handoffs, `specs/004`, `decisions/019`–`024`. The competitor
screenshots (AIapply 11, Fast Apply 31, jobcopilot 15, Simplify 14) are design references only.
Competitor visuals, claims, backend design and auto-apply behavior are not copied.

## Verified baseline (2026-10-04)

| Suite | Result |
|---|---|
| `product/` | 824 passed (813 at last commit + 11 from the uncommitted work below) |
| `apps/api/` | 70 passed |

`AGENTS.md` says 786 for `product/`. That is stale; the live number is above.

Uncommitted work in the tree from earlier this session (not yet reviewed or committed):
`pages/0_Start_Here.py`, `ui/onboarding.py`, `applications/weekly.py`, section completeness in
`ui/fact_vault.py`, fit badge and "missing" line in `job_search/ui_helpers.py`, a weekly panel in
`applications/streamlit_views.py`. This spec absorbs or replaces each (see "Retained / changed /
removed").

## Audit of the current implementation

What already exists, so we build on it rather than around it:

| Area | Today | Gap against this spec |
|---|---|---|
| Navigation | Five workspaces in a sidebar (`ui/shell.py`, `ui/design_system.py`) plus a four-step ribbon on every page | No Home; ribbon is unrelated to some pages; names are tool-centric |
| Profile | `pages/1_Profile_Review.py` talks to the FastAPI service with a **separate email/password login**; the API must be running. In-process `ResumeParser` already exists and Tailoring Studio uploads its own copy | Two uploads, two stores; Career Profile unusable on the deployed app; no preferences, authorization, links or goals |
| Provenance | API tags each field `resume`/`user_verified` | No "confirmed" or "missing" state; no review-by-exception |
| Goals | Sidebar form on Job Search; held only as widget state (lost on page change) | Not saved or editable as a profile; fixed in the draft Start Here wizard via `job_goals` session key only |
| Jobs | Single-column expander list; form in sidebar; fit, gaps and strong/partial matches already computed (`FitResult`) | No master-detail; hard gates and unknowns not separated from gaps; "Apply" wording |
| Tailor | `app.py`: sidebar inputs, review radios, metrics, downloads; `ui/artifact_review.py` and `ui/tailoring_view.py` already hold pure logic | No review progress, no sticky preview, evidence line shows the bullet (decision 021 open item) |
| Apply | `pages/3_Applications.py`: **free-text Job ID**, free-text PDF path, manual match-score input; mode picker with three equal options; full-width disclosure banner | Raw fields instead of the handoff; no readiness checklist; no "Mark as applied"; banner is large |
| Tracker | `4_Application_Tracker.py` + `applications/streamlit_views.py`: table, filters, detail, status editor, next action | Saved views differ from the six requested; no due-date surfacing |
| Safety | Validation gate, FAIL never downloadable, exact-version regeneration, preview never persists, `ATSCapability.final_submission` gate, answer bank approved-only, per-user folders | None. All preserved unchanged |

Facts that shape the design:

- A "Mark as applied" capability **already exists** underneath: `StatusTracker.update_status`
  (USER source). Staging sets `READY_TO_APPLY`. This redesign adds the explicit button, not a new
  mechanism.
- The answer bank, applications DB and jobs DB are already **per-user SQLite files**
  (`identity.py`). They stay.
- The Career Profile lives only in `st.session_state` plus the API. This is the one place the
  requirement "enter once and reuse" collides with "no new persistence layer". See Open decision 1.

## Retained, changed, removed, deferred

**Retained (unchanged behavior):** Streamlit; every engine (parser, analyzer, gap analysis,
`CandidateFitScorer`, tailoring and DOCX splice, validation, length correction, artifact
pipeline); per-user data folders and Google sign-in; the answer bank; `ATSCapability` gate;
preview-never-persists; the handoffs (`PENDING_TAILOR_JOB_KEY`, `tailoring_session`,
`publish_artifact_handoff`); Atkinson Hyperlegible; semantic colors; Candidate Fit separate from
Resume Alignment.

**Changed:**
- Navigation: five tool-named workspaces become six destinations (below).
- Global four-step ribbon becomes per-page contextual progress.
- Fact Vault becomes Career Profile (same concept, "Verified facts" kept as the product idea).
- Job Discovery becomes a master-detail Jobs workspace.
- Tailoring Studio becomes the Tailor review room.
- Apply Launchpad becomes a readiness and handoff screen.
- Tracker gains the requested saved views, due-date surfacing and the weekly goal panel.

**Removed:**
- The draft `0_Start_Here.py` page and the hard-coded `HOW_IT_WORKS`/`BEFORE_AFTER` copy (folded
  into Home first-time mode; the before/after table is dropped as marketing).
- The free-text Job ID, PDF path and match-score inputs on Apply.
- The percentage completeness bars from the draft (replaced by a defined sections model).
- The four-step ribbon as a global component.

**Deferred (explicitly not in this work):** Assist and Auto availability (blocked on spec 006);
Kanban board; status sync (spec 005); browser extension or autofill; automatic job importing;
LinkedIn/Indeed/Handshake as live sources; React or any framework change; a second scorer or
tailoring engine; new dependencies; streaks or celebratory animation.

## Information architecture

Six destinations in a stable left rail (~240px). User-facing names; file routes may stay.

| # | Destination | Route (internal) | Replaces |
|---|---|---|---|
| 1 | Home | `app.py` becomes Home | (new; absorbs draft Start Here) |
| 2 | Career Profile | `pages/1_Profile_Review.py` | Fact Vault |
| 3 | Jobs | `pages/2_Job_Search.py` | Job Discovery |
| 4 | Tailor | `pages/tailor.py` (moved from `app.py`) | Tailoring Studio |
| 5 | Apply | `pages/3_Applications.py` | Apply Launchpad |
| 6 | Tracker | `pages/4_Application_Tracker.py` | Application Tracker |

Moving the Tailoring Studio out of `app.py` is required so Home can be the entry point. It is a
file move plus import fixes, with no logic change. Existing tests that import it are updated in
the same phase. (`app.py` is the Streamlit Cloud entry point, so the deployed URL still lands on
Home.)

The rail also shows: identity or "local demo" state; compact profile readiness ("3 of 4 required
sections confirmed"); the active job when one is selected; a one-line privacy message; sign-out
when authenticated.

### Journey (user-facing, five milestones)

1. Import career history
2. Confirm important facts
3. Set job goals
4. Choose a real role
5. Prepare the first application

Derived from existing evidence (profile present, confirmations, saved goals, a job selected, a
validated artifact handed off). Never marked complete by navigation alone.

## Destination design

### Home

**First-time mode** (milestones incomplete): one-paragraph product explanation; the five
milestones with progress; **one** dominant next action with the value it unlocks ("Upload a resume
and Job Copilot builds your profile in about a minute"). Other destinations are present in the rail
but not offered as equal cards.

**Returning mode** (all five complete): command center. A single "Your next best action" region
above the fold, then: saved jobs needing review, tailoring drafts awaiting decisions, applications
ready to finish, follow-ups due, weekly goal and progress, concise recent activity, quick actions.

Next-best-action priority (pure function, tested): (1) a failed or blocked artifact on an active
job, (2) follow-up due today or overdue, (3) tailoring draft with unreviewed changes, (4) staged
application ready to finish, (5) saved jobs not yet reviewed, (6) no search yet this week,
(7) none ("You are caught up").

### Career Profile

A reusable passport, in this order: resume source and version; contact; summary; work history;
education; skills and tools; certifications; links; work preferences; work authorization; approved
answer bank.

- **Completeness is defined, not a percentage.** Required sections: contact (name, email),
  work history (at least one role with dates), education (or "none"), skills. Optional: summary,
  certifications, links, preferences, authorization. Display "3 of 4 required sections confirmed"
  and list what is missing. No synthetic percent.
- **Provenance on every fact:** From resume, Edited by you, Confirmed by you, Missing.
- **Review by exception:** a correctly extracted field is never forced into reconfirmation. The
  screen leads with the short list of items needing attention (missing dates, empty required
  fields, low-confidence parses) and a single "Confirm the rest" action.
- **Legally significant answers** (work authorization, sponsorship, criminal history, disability,
  demographic, veteran) are only ever typed or chosen by the user, stored as such, and never
  inferred or drafted. Demographic fields are optional and default to "Prefer not to say".
- Preferences (goals) live here and are the single source for Jobs.

### Jobs

Desktop three-region workspace: filters and saved goals (left) | result rows (middle) | selected
job (right). Below ~1000px: filters, results, details stacked. Streamlit-compatible build: a
left column for filters (collapsed after a search), `st.columns([1.1, 1.4])` for list and detail,
selection held in `st.session_state["selected_job_id"]`.

- Real results only; honest source labels; no placeholder jobs; the latest run stays visible while
  filters change.
- Compact row: role, company, location, work mode, salary if known, source, freshness, quality,
  fit (badge with text, never color alone).
- Detail separates: strong evidence, partial evidence, genuine gaps, **hard gates** (for example
  sponsorship or required clearance conflicts), unknown information.
- Actions stay distinct: Save, Pass, **Prepare application** (replaces "Tailor resume"/"Apply").
- Unknown salary, sponsorship or fit is shown as "Not stated"/"Not assessed", never zero.

### Tailor

Review room for one job. Header: company, role, Candidate Fit, Resume Alignment (always separate),
artifact status. Left: a compact review queue, one change in detail at a time (original, proposed,
why it helps, job requirement, supporting fact, validation status; verbs **Accept change**,
**Edit manually**, **Keep original**). Right: the exact current artifact with page count,
validation and version, sticky on desktop where Streamlit permits. Footer: review progress
("4 of 7 reviewed"), Regenerate, Continue to application.

Kept: "Missing, never added" section; punctuation-only and unchanged items hidden by default;
review controls before preview on mobile; FAIL never styled as downloadable or application-ready;
DOCX fidelity, immutable versions, bounded length correction.

Improvement included: the supporting-fact line shows the real supporting fact (open item in
decision 021/024), taken from the verified profile entry that justified the edit.

### Apply

A readiness and handoff screen for the job and artifact **received through the handoff** (no
free-text Job ID or PDF path). Checklist: selected job; employer URL present and well-formed;
exact resume version and validation; reusable facts ready; unanswered custom questions; mode and
what it can actually do.

Primary action: **Open employer application**. Secondary: **Track this application** (stages as
Ready to apply). After the user finishes externally: **Mark as applied** (explicit; records
`APPLIED`, source USER, timestamp). Opening the employer page is never described as submitted.

Manual is the default and recommended. Assist and Auto render as disabled radio options with a
one-line reason beside them (from `ATSCapability`), not a full-width banner. Preview still never
persists. Approved answer-bank matches and unanswered questions are listed; unanswered ones can be
answered inline (approved-only rule unchanged).

### Tracker

Dense table by default: company, role, status, applied date, next action, due date, Candidate Fit
snapshot, resume version, source, mode. Detail panel: immutable job snapshot, resume used,
answers used, status history and provenance, notes, next action, employer link. Saved views:
**Needs action, Ready to apply, Applied, Interviewing, Waiting, Closed** (map onto existing
`ApplicationStatus`; table below). Weekly goal panel as motivation only: no streaks, no
animation.

| View | Statuses |
|---|---|
| Needs action | any with next-action due today or earlier, plus Preparing |
| Ready to apply | Ready to apply |
| Applied | Applied |
| Interviewing | Recruiter screen, Interview, Final interview, Assessment |
| Waiting | Applied with no activity for 14+ days |
| Closed | Offer, Rejected, Withdrawn |

Board view is deferred until the table and detail are done and tested.

## Navigation and workflow behavior

Contextual progress replaces the global ribbon: Home = journey; Jobs = search and triage;
Tailor = changes reviewed; Apply = readiness checklist; Tracker = lifecycle. Every page has one
primary action, an empty state, a loading state, an actionable failure state, and a next
destination.

Handoffs preserved, and tested end to end with synthetic data:
Career Profile → Jobs (facts and goals) · Jobs → Tailor (exact job and fit snapshot) · Tailor →
Apply (artifact path, SHA-256, version, validation, scores) · Apply → Tracker (application
snapshot) · Tracker → Tailor or employer page. Switching jobs resets description, review state
and artifact (existing `sync_pending_job` behavior, retained and tested).

## State and migrations

No database migrations. No new tables.

New session-state keys (all derived or user-entered, none persisted by this redesign except where
Open decision 1 says): `selected_job_id`, `home_mode` (derived), `weekly_goal` (already added),
`job_goals` (from the draft; becomes the stored preferences).

If Open decision 1 is approved as recommended, one new per-user file is added
(`users/<owner_id>/career_profile.json`) alongside the existing per-user databases, with a
version field, and no change to existing schemas.

## Visual system

Concept: **career operations desk**. The memorable element is the evidence connection:
job requirement → supporting fact → resume change, shown as a visible chain in Jobs detail and
Tailor.

| Token | Value | Contrast on white | Contrast on canvas |
|---|---|---|---|
| ink | `#172033` | 16.3 | 15.0 |
| canvas | `#F3F6FA` | n/a | n/a |
| paper | `#FFFFFF` | n/a | n/a |
| line | `#D7DEE8` | n/a | n/a |
| action | `#2457D6` | 6.2 | 5.7 |
| verified | `#167A5A` | 5.3 | 4.9 |
| review | `#A86108` | 4.8 | **4.4 (fails AA on canvas)** |
| blocked | `#B43A45` | 5.8 | 5.3 |
| muted | `#5D6878` | 5.6 | 5.2 |

Rule: review-amber text is used only on paper; on canvas the darker `#9A5806` is used (measured
before implementation). Status never relies on color alone (text plus a symbol).

Typography stays Atkinson Hyperlegible: titles 36–44px, section 22–28, task 17–20, body 15–16,
metadata 13–14; sentence case; no all-caps labels. Resume preview keeps the resume's own
typography. Layout: 240px rail, up to 1500px for dense workspaces, 2/3 primary and 1/3 context,
structure from borders and background, small control radius, one visually unique primary button
per region. Motion only to confirm accepting a change, saving a fact, moving a status or
completing a milestone; respects `prefers-reduced-motion`.

Limit to be honest about: Streamlit does not allow a fully fixed rail, true sticky columns or
custom focus management everywhere. Where it cannot be done (sticky preview especially), the
fallback is stated per phase and verified in the browser rather than assumed.

## Copy

Plain language about time saved and confidence. Use: "Review this change", "Supported by your …
work", "Missing from your experience; Job Copilot will not add it", "Prepare application", "Open
employer application", "Mark as applied", "No salary was stated", "We could not verify this
claim". Avoid: "Activate AI", "Supercharge", "Autopilot", "Successfully submitted" without
confirmation, and internal terms (artifact pipeline, disposition, provider adapter, capability
model).

## Technical approach

Page files stay thin. Reusable behavior goes under `product/resume_tailorer/ui/`. Pure, tested
view models (no Streamlit import):

| Module (new unless noted) | Responsibility |
|---|---|
| `ui/home_state.py` | first-time vs returning, journey milestones, next-best-action |
| `ui/profile_readiness.py` (extends `ui/fact_vault.py`) | required/optional sections, provenance states, items needing review |
| `ui/job_view.py` | row and detail view models, evidence groups incl. hard gates and unknowns |
| `ui/tailor_progress.py` (extends `ui/tailoring_view.py`) | review progress, queue ordering |
| `ui/apply_readiness.py` | checklist and capability presentation from `ATSCapability` |
| `ui/tracker_views.py` (extends `applications/ui_helpers.py`) | six saved views, due-date logic |
| `ui/design_system.py` (extend) | tokens, `semantic_status`, contextual progress |
| `ui/shell.py` (rewrite) | rail, identity, readiness, active job, context bar |

No business logic moves into rendering code. No second scorer or tailoring engine.

## Implementation plan (reviewable phases; each leaves the app runnable)

Every phase ends with: both suites green, browser check at desktop and 390px width, a commit, and
a rollback point (`git revert` of that phase's commit; phases do not depend on later ones).

| Phase | Scope | Files changed | Files added | Tests |
|---|---|---|---|---|
| 0 | Review and commit or discard the uncommitted draft work; fix equal-height cards | the 7 modified files listed above | none | existing 824 stay green |
| 1 | Shell, rail, tokens, contextual progress; remove global ribbon | `ui/shell.py`, `ui/design_system.py`, `ui/__init__.py`, all pages (header call only) | none | `test_ui_design_system.py` updated; new token and contrast test |
| 2 | Home (first-time and returning), journey, next-best-action; move Tailor out of `app.py` | `app.py` (becomes Home), `pages/tailor.py` (moved content), `tests/*` imports | `ui/home_state.py`, `tests/test_home_state.py` | state selection, priority order, milestone derivation |
| 3 | Career Profile restructure and readiness model (depends on Open decision 1) | `pages/1_Profile_Review.py`, `ui/fact_vault.py` | `ui/profile_readiness.py`, tests | required/optional logic, provenance states, legal-answer rules |
| 4 | Jobs master-detail | `pages/2_Job_Search.py`, `job_search/ui_helpers.py` | `ui/job_view.py`, tests | evidence grouping incl. hard gates, unknown never zero |
| 5 | Tailor review room | `pages/tailor.py`, `ui/tailoring_view.py`, `ui/artifact_review.py` | `ui/tailor_progress.py`, tests | progress counts, verbs, FAIL never ready, real supporting fact |
| 6 | Apply readiness and honest handoff, Mark as applied | `pages/3_Applications.py`, `applications/streamlit_views.py` | `ui/apply_readiness.py`, tests | no free-text job; manual default; assist/auto disabled; opening link ≠ submitted; mark-as-applied writes USER status |
| 7 | Tracker views, due dates, weekly goal | `pages/4_Application_Tracker.py`, `applications/streamlit_views.py`, `applications/weekly.py` | `ui/tracker_views.py`, tests | six views, due logic, 14-day waiting rule |
| 8 | Mobile, accessibility, copy, empty/loading/failure states | CSS in `ui/design_system.py`, copy across pages | none | copy lint test (banned phrases), keyboard/focus checks recorded |
| 9 | Full journey tests and browser verification | none | `tests/test_redesign_journey_e2e.py` | Career Profile → Jobs → Tailor → Apply → Tracker on synthetic data (extends `test_workspace_flow_e2e.py`) |
| 10 | Docs, decision record final, screenshots, deployed smoke test | `README.md`, `AGENTS.md` baseline numbers, handoffs | `decisions/025` update, screenshots under `docs/` (synthetic data) | deployed app opens on Home and does not present local mode as multi-user |

### Browser-verification procedure (every destination)

Run the app with synthetic data (never a real resume). For each of the six destinations capture
and inspect at 1280px and 390px: empty, populated, warning, blocked (FAIL artifact), loading, and
failure states. Record keyboard-only operation of the primary action, visible focus, reading order
on mobile (controls before preview), and no horizontal overflow. Results recorded in the phase
commit message and the final decision update.

## Risks

1. **Streamlit layout limits** (sticky columns, fixed rail, focus management). Mitigation:
   fallbacks stated per phase; verified in browser.
2. **Moving the Tailoring Studio out of `app.py`.** It is the Streamlit Cloud entry point and has
   many imports in tests. Mitigation: isolated in Phase 2 with its own rollback.
3. **Profile persistence** (Open decision 1) affects Phases 3, 4 and acceptance criteria 3 and 4.
4. **Scope.** Ten phases; Phases 1–2 and 6 deliver the most user value and can ship alone.
5. **First real users have not yet touched the current flow.** A redesign before any user test
   risks designing blind. Mitigation: ship Phases 1–2 first, then run the supervised tests the
   Sprint 2 plan already needs.
6. **Review-by-exception depends on parser confidence.** The parser has no confidence value today;
   "needs attention" will use structural checks (missing dates, empty required fields) only.
   Stated as such in the UI; no invented confidence number.

## Acceptance criteria

The 18 criteria from the request apply unchanged. In addition: baseline numbers in `AGENTS.md`
and both handoffs are updated to the verified live counts.

## Open decisions (need your answer before Phase 3)

1. **Where the Career Profile is stored.** Today the API holds it (separate login, must be
   running) and Streamlit holds it only for the session. Requirement 3 ("enter once, reuse")
   cannot be met on the deployed app without one store both can use.
   - **A (recommended):** parse in-process with the existing `ResumeParser`; store the profile,
     provenance and preferences as one versioned JSON file in the user's existing per-user
     folder. Drop the separate API login from the Streamlit flow; keep the API for its own
     clients. This is a new file, not a new database or schema, but it is new persistence, so it
     needs your approval.
   - **B:** keep the API as the only store. No new persistence, but the deployed app needs a
     hosted API and database first (decision 023 checklist) and the double login stays.
   - **C:** session-only. No persistence at all; users re-upload each visit. Rejected: violates
     the outcome.
2. **Is Phase 0 (the draft Start Here work) kept?** Recommended: commit the fit badge and
   "missing" line, the weekly panel and the section model now; delete Start Here when Home lands
   in Phase 2.
3. **Phasing:** recommended to stop for supervised user tests after Phase 2 (and optionally 6).
