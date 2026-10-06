# Spec 011: Tailor from the Career Profile, batches from Jobs, and a keyword report

**Status:** Approved 2026-10-05 by the builder ("approve and work on it"). In progress.
**Date:** 2026-10-05
**Builds on:** spec 010 (requirement review, decision 032)

## Problem

The builder tried the spec 010 build and asked for two features plus fixes for its known weak
spots:

1. **Tailor doesn't say what changed in keyword terms.** The builder wants to see which terms
   this version added and which are still left out, and why.
2. **Jobs works one job at a time.** The builder wants to send several jobs to Tailor and Apply
   in one go.
3. **Career Profile edits never reach tailoring.** Tailoring re-reads the uploaded resume file,
   so a bullet fixed or added in Career Profile is ignored. That also makes the review's own
   advice ("add it to a role in Career Profile") a dead end, and confirmation is matched to roles
   by position.
4. **Two gap systems contradict each other.** The old gap analysis still drives Tailor's "Missing,
   never added" list and the Jobs "Why this role may fit you" panel.
5. **One status per requirement hides a missing term.** "SQL, Tableau and dashboard reporting"
   shows as direct evidence even though Tableau is missing.
6. **Recognition is narrow.** Small hand-written vocabularies lean toward marketing and analytics.
   There are few spelling variants, and postings without clear headings produce few or no
   requirement rows.
7. **The model barely improves anything.** Real runs proposed zero or one change, with no reason
   given for the rest.
8. **The free-form path (PDF uploads) has never run with a real model**, and its readability check
   has no per-bullet check.
9. **The readability check uses one text extractor**, and doesn't look at tables, headers and
   footers, or the Word file itself.

## What we're making

### A. The keyword report in Tailor

There's a new "Keywords" panel next to the requirement review. It's built from the review's terms,
compares the original resume with this version, and has two lists:

- **Added in this version:** each term the tailored resume names that the original didn't, with
  the change that added it (click it to jump to that change). Only supported terms can ever be
  here, because the spec 010 guard rejects the rest.
- **Still left out**, grouped by why:
  - "You have evidence, not named yet" (a target; it says whether the model tried and why it
    didn't change it);
  - "Only listed in your skills";
  - "Not confirmed yet";
  - "Check yourself";
  - "No evidence (never added)".

  Each term links to its requirement row.

The panel is shown in both apps, with the same text from one view module.

### B. Batches from Jobs: tailor several, then prepare several

**Jobs:**

- A "Select" mode puts checkboxes on the list (up to 10 jobs).
- **Tailor selected (N):** queues the jobs. The API runs them one at a time in the background
  (one run per person, as today). Each job's run and review are saved as usual. Tailor gets a
  "Batch" strip ("3 of 5 tailored · 1 failed") with a switcher to open each job's review.
- **Daily limit:** the per-person tailoring limit still applies. A batch that would exceed it
  queues only what fits and says so.

**Apply:**

- **Prepare selected for applying:** for every batch job whose tailored resume has been reviewed
  and passed validation, it tracks the application as "Ready to apply" in one step. It then lists
  each job's kit and the employer's own link.
- **Never submits.** Nothing is ever sent to an employer, exactly as today (decision 016; Auto
  stays not offered). Jobs whose review isn't finished are listed as "Review first".

### C. Tailor from the Career Profile (problem 3)

- **Source:** when the resume is the Career Profile's own file, tailoring uses the Career Profile
  facts (with every edit), not a fresh parse of the file. A one-off upload is unchanged: that
  file is the source.
- **Word layout kept: "sync then tailor".** Before tailoring, a copy of the original Word file is
  updated to match the profile:
  - **Roles:** each profile role is matched to a role in the file by employer and title, never by
    position.
  - **Bullets:** for a matched role, bullet paragraphs are rewritten to the profile's bullets.
    Extra bullets are added by cloning the role's last bullet paragraph (same style and
    numbering); removed ones are deleted.
  - **New roles:** a profile role with no match in the file can't be placed in the original
    layout. The run says so and offers the rebuilt-layout (free-form) path for that job.
  - **The edits themselves** are checked like any edit (no fabrication by construction, since
    they are the person's own words).
- **Confirmation by stable path:** the review's evidence paths come from the profile itself, so
  "confirmed" always refers to the right role.
- **The dead end closes:** adding "Built Tableau dashboards for…" to a role in Career Profile now
  makes Tableau direct evidence on the next run.

### D. One gap system (problem 4)

- **Tailor:** the "Missing, never added" list comes from the review rows with "no evidence" and
  their missing terms. The old gap list is no longer shown.
- **Jobs:** the "Why this role may fit you" panel's strong, partial and missing lists come from the
  review (direct, transferable, and none or mention).
- **Candidate Fit:** the number itself is unchanged and stays separate (spec 002).
- **The old gap analysis** stays internally for the parts that still use it (fabrication-check
  context, legacy API), but no screen shows its categories.

### E. Status per term (problem 5)

- **Terms:** each row lists its named terms with their own status, for example SQL direct and
  Tableau no evidence.
- **Row status:** "Fully supported" when every named term has evidence, "Partly supported" when
  some do, otherwise the strongest status. The new "partly supported" label and its term chips
  make the gap visible at a glance.
- **Counts:** the summary counts fully supported rows separately: "Required: 3 fully, 2 partly,
  of 7".
- **Targets and blocked terms:** use the per-term statuses directly.

### F. Broader recognition (problem 6)

- **Vocabulary:** extended across common fields (software, data, finance and accounting,
  healthcare and nursing, operations and supply chain, sales, HR, education, design, legal),
  with each field's main tools and credentials (for example CPA, CFA, RN, BLS, PMP, SHRM-CP,
  AWS certifications).
- **Variants:** a table maps spellings to one term (Postgres → PostgreSQL, PowerBI → Power BI,
  Amazon Web Services → AWS, MS Excel → Excel, JS → JavaScript, and so on), used by the matcher
  everywhere.
- **Ambiguous acronyms:** the list grows (for example PA, RN versus registered, OT, PT, DA, CS,
  SA), with their expansions.
- **Postings without clear headings:** a sentence-level fallback finds requirement-like sentences
  ("must have", "experience with", "proficient in", "N+ years", "required", "preferred", "nice
  to have", "bonus") and classifies each as required or preferred from its own wording.
- **Still deterministic:** no model is used for extraction, so the review stays fast, free and
  repeatable. **Rejected:** model-based extraction; it costs a call per job, isn't repeatable, and
  can invent requirements.

### G. A model that actually works the targets (problem 7)

- **Answer for every target:** the prompt asks the model to answer each "make clearer" target with
  either a rewrite or "no safe rewrite" and a one-line reason. Tailor shows those reasons under
  "Not changed, and why".
- **More places to improve:** the summary paragraph and the skills line are editable targets.
  Reordering listed skills so the posting's terms come first is allowed; adding unlisted ones
  isn't.
- **More reasoning for `codex-cli`:** it runs with "medium" reasoning effort instead of "low",
  overridable with `LLM_REASONING_EFFORT`. Other models are unchanged.
- **Unchanged:** every guard (length, drift, fabrication, unsupported terms, user review).

### H. The free-form path gets per-bullet readability and a real run (problem 8)

- **Readability:** the expected bullets come from the final free-form text, so the free-form PDF
  gets the same per-bullet and order checks as the Word path.
- **Supervised run:** the second supervised run uses a PDF resume (anonymized) through the free-form
  path with the real model, recorded alongside the first.

### I. A stronger readability check (problem 9)

- **Two extractors:**
  - The PDF is read by pypdf and by PyMuPDF (already a dependency).
  - A bullet counts as missing only if both miss it.
  - If the two disagree a lot (one reads a bullet whole, the other doesn't), a warning says "Text
    reads differently depending on the reader; layouts like columns or text boxes often cause
    this."
- **Word file checks**, run on the uploaded and the tailored file:
  - contact details only in a header or footer (warning: some parsers skip them);
  - work-history bullets inside tables or text boxes (warning);
  - text that python-docx can't reach (shapes) (warning).
- **Label:** it still says it's a local check, not an employer's ATS.

## Out of scope

- Submitting applications in any form, including in batches.
- Model-based requirement extraction.
- New paid services.
- Years-of-experience arithmetic.
- Changing Candidate Fit scoring.
- Usage analytics.

## Compatibility

- **Stored reviews:** saved reviews still load. Rows from before this spec have no per-term
  statuses; they're shown with the row status, and a review worked out now fills them in.
- **API:** existing fields stay. New fields are `keyword_report`, `batch`, per-row `terms`
  statuses, and `/v2/batch/*` endpoints.
- **One-off uploads** behave as today.

## Affected files (main)

| Area | Files |
|---|---|
| Engine | `analyzers/requirement_review.py`, `analyzers/ats_keywords.py`, `analyzers/term_match.py`, `analyzers/jd_sections.py`, `analyzers/job_analyzer.py` |
| Engine (new) | `docx_export/profile_sync.py` |
| Tailoring | `tailoring_service.py`, `tailorer/docx_bullet_tailorer.py`, `artifacts/length_control.py`, `llm/client.py` |
| Readability | `pdf/readability.py`, plus a Word check |
| View models | `ui/requirement_review_view.py`, `ui/job_view.py` |
| API | `jobs_router.py`, `tailor_router.py`, `apply_router.py`, a new `batch_router.py` |
| Web | the Jobs list and detail, the Tailor page and review, the Apply page, `lib/types.ts` |
| Streamlit | pages 2, 5 and 3 (Jobs, Tailor and Apply); batches limited to tailoring a queue there, run in the page session |

**No new dependencies.** It's a medium-size change, not a large refactor: the old gap analysis
stays internally.

## Implementation order (each step tested and committed separately)

1. Per-term statuses and the keyword report (E, A).
2. One gap system on screen (D).
3. Broader recognition (F).
4. Tailor from the Career Profile, with Word sync (C).
5. The model works the targets (G).
6. Readability: second extractor, Word checks, free-form bullets (I, H).
7. Batches: API, web, Streamlit (B).
8. Supervised runs: one Word resume (a profile edit adds evidence), one PDF resume (free-form);
   then decision 033 and docs.

## Test plan

**Engine:**

- **Per-term:** "SQL, Tableau and dashboard reporting" with SQL only is "partly supported", SQL
  is direct and Tableau is "no evidence"; Tableau is blocked and SQL is a target.
- **Keyword report:** a term added by an accepted change appears under "added" with that change;
  every unsupported term appears under "still left out" with the right reason.
- **Recognition:** for anonymized postings in nursing, finance and software (with and without
  headings), the expected rows are found and Postgres matches PostgreSQL.
- **Profile sync:**
  - a Word file whose role order differs from the profile still syncs by employer and title;
  - an added profile bullet appears in the synced file with the role's bullet style and
    numbering;
  - a removed bullet is gone;
  - an unmatched profile role is reported;
  - layout and page checks still run.
- **Dead end closed:** adding a Tableau bullet in the profile turns Tableau into direct evidence.
- **Model targets:** a stubbed model that answers "no safe rewrite: …" puts that reason into
  "Not changed, and why"; skills-line reordering is accepted and adding a skill is rejected.
- **Readability:**
  - the two extractors agreeing or disagreeing (a real two-column PDF);
  - a Word file with contact details in the header, bullets in a table, or a text box.
- **Batch:**
  - a queue of 3 with the stubbed model runs one at a time;
  - the limit is respected;
  - Prepare tracks only reviewed, passing jobs and never calls anything that submits (asserted
    with the existing hard gate).

**API and web:**

- **API:** tests for the new fields and endpoints.
- **Playwright:** select 2 jobs, tailor the batch (stubbed), switch between reviews, finish
  reviews, Prepare selected, and see both kits; accessibility checks on the new panels.

**Supervised:** two real runs (Word and PDF), recorded, with the pass conditions from spec 010
plus "the profile edit reached the tailored resume".

## Definition of done

- [ ] Tailor shows added and still-left-out keywords, with reasons, in both apps.
- [ ] Jobs can select and tailor up to 10 jobs as a batch, and Apply can prepare reviewed ones;
      nothing is ever submitted.
- [ ] Career Profile edits reach tailoring (Word layout kept); roles are matched by
      employer and title.
- [ ] One gap system on every screen; per-term statuses visible.
- [ ] Recognition works on the anonymized nursing, finance and software postings, and on postings
      without headings.
- [ ] The model answers every target (rewrite or reason), and the reasons are visible.
- [ ] The free-form path has per-bullet readability and a real supervised run.
- [ ] The readability check uses two extractors and checks the Word file.
- [ ] Product, API and web suites green in CI; decision 033 written.
