# Spec 010: Honest ATS help: an evidence-based requirement review

**Status:** Shipped 2026-10-05 (decision 032). The builder approved the spec and delegated the
open choices: missing content blocks, out-of-order content warns, the overlap number moves to
Details, and the supervised run uses the codex-cli model. The supervised run is recorded in
`discovery/experiments/2026-10-ats-requirement-review.md`.
**Date:** 2026-10-05
**Supersedes:** spec 001 step 14 ("loop until ≥85% alignment") and the "Already on resume"
wording in specs 002, 007 and 008.

## Problem

Job Copilot's "ATS" features measure keyword overlap, but they talk about it in a way that
promises more than it can deliver:

- **The Jobs check misreports.** Jobs says "4 of 4 key terms already on your resume". The check
  actually scans every text value in the Career Profile, including job goals and preferences, so
  a term the resume never shows counts as "on your resume" (`ats_keywords.profile_text`).
- **The Tailor headline is a home-made formula.** Tailor's headline number, "Resume alignment
  N%", is 60% keyword overlap plus 40% overlap with the first five required qualifications
  (`optimizer._score_resume`). Next to the word "ATS", people read it as an employer score. No
  such universal score exists (see the research appendix).
- **The free-form path chases a number.** It loops up to 5 rounds until that number reaches
  85% (spec 001 step 14). Each round asks the model to "better address" missing keywords. The
  number rewards repeating the posting's words, not showing evidence.
- **Weak evidence is treated as strong.**
  - A skill that appears only in the skills list counts as "Direct verified" and "Already on
    resume" (`GapAnalyzer._classify_skill`).
  - The weakest category, "Candidate likely has this from background" (evidence: "Based on
    related experience"), reaches the model under "Supported by Experience but Missing (Bring
    into resume)" (`format_gaps`).
- **Unconfirmed facts feed tailoring.** Tailoring doesn't check confirmation, although its
  docstring says it does.
- **The readability check is shallow.** It confirms the PDF has text, a sensible page count and
  no garbage characters. It doesn't check that the important content survived or reads in order.

The cost of getting this wrong falls on the job seeker. They may trust a number that means little
to an employer, or send a resume that claims more than they can back up in an interview.

## Goal

Help a job seeker produce a machine-readable resume that truthfully and clearly shows the most
important requirements of one specific job.

The goal is not to predict any employer's ATS score. No feature may promise a pass rate, a
universal score, a ranking or an interview.

Four things stay separate, as they are today:

| Thing | Question it answers | Where |
|---|---|---|
| Candidate Fit | Does my background fit this job? | Jobs (unchanged) |
| Requirement review (new) | For each requirement, what evidence do I have, and does this resume show it? | Jobs (summary), Tailor (full) |
| Readability check (stronger) | Can a machine pull my content back out of this file, in order? | Tailor |
| Application capability | What can Apply do on this employer's site? | Apply (unchanged) |

## What we're making

### 1. Correct the misleading labels (first, smallest, ships alone)

- **Jobs: "Terms in this posting".**
  - The labels become "In your Career Profile" and "Not in your Career Profile".
  - The summary becomes "N of M posting terms appear in your Career Profile. This is a word
    check, not an employer's ATS score."
  - Only profile facts count: work history, summary, skills, tools, education and
    certifications. Contact details, goals and preferences no longer count.
- **Tailor: no headline percentage.** The "Resume alignment N%" chip leaves the header. The
  number stays in Details as "Keyword overlap (Job Copilot's own estimate, not an employer
  score): before → after", with the formula in one sentence.
- **A short "About ATS checks" explanation** is shown in Jobs and Tailor in both apps. The text
  is defined once in `ui/ats_explainer.py` and served by the API, so the two apps can't drift.
  It says:
  - employers' systems differ;
  - Job Copilot can't see or predict their scores;
  - what it can do is check readability and help you show real evidence clearly.
- **Gap category labels:** "Already on resume" becomes "In your Career Profile" wherever it is
  shown. The stored enum values stay the same, so saved reviews still load.

### 2. The requirement review (replaces score-chasing as the guide)

A new engine module `analyzers/requirement_review.py` builds one row per important requirement:

- **Requirement:** the posting's exact sentence, from `JobAnalysis.structured_requirements`.
- **Section:** required, preferred or responsibility. Hard gates (licenses, degrees, minimum
  years) are marked.
- **Evidence status.** The highest that applies:

  | Status | Meaning | Example |
  |---|---|---|
  | **Direct evidence** | The concept appears in a work, education or certification passage with context | "Built SQL dashboards used by 40 managers" for "SQL" |
  | **Transferable evidence** | A passage genuinely shows the capability in other words (existing competency map) | "Coordinated launch timelines across 4 teams" for "project management" |
  | **Mentioned only** | Appears only in the skills or tools list, or the summary, with no supporting passage | "Snowflake" in Skills, nowhere else |
  | **Unconfirmed** | The only evidence is in facts you haven't confirmed in Career Profile | Imported but never confirmed |
  | **No evidence** | Nothing found | "Active CPA license" |

- **Linked evidence.** Every status above "No evidence" cites the exact Career Profile fact or
  resume passage behind it: where it comes from (for example "CVS Health role, bullet 2") and
  whether you confirmed it. Nothing is paraphrased.
- **Shown in this resume:** yes or no for the tailored version, so you can see whether
  tailoring made a supported requirement visible.
- **Ambiguous acronyms** never count as direct evidence. If the match is a short acronym with
  several common meanings (from a small curated list such as PM, BI, CRM, ML, AR and SEM), the
  row is "Check the meaning". Example: "PM" in the posting means product manager, but your
  resume means project management.

**Where it appears:**

- **Jobs detail:** one line, "Required: 4 of 6 with evidence · Preferred: 1 of 3 · 1 required
  credential not found". It links to Tailor for the full review. Candidate Fit stays as it is.
- **Tailor:** a "Requirement review" panel grouped by Required and Preferred, each row
  expandable to the posting quote and the evidence quote.
- **Tailor, gaps:** missing requirements stay visible as gaps, with the plain line "Not added:
  you haven't shown evidence for this."

### 3. Wording suggestions only from approved evidence

- **What the model is told to improve:** only requirements with Direct or Transferable evidence
  from confirmed facts. Each comes with its evidence passage, and the instruction is to make
  that passage's terminology, context, responsibility or outcome clearer if true.
- **What the model is told not to add:** "Mentioned only", "Unconfirmed", "Check the meaning"
  and "No evidence" requirements. "Mentioned only" may keep the term where it already is, but no
  new claim may be built on it.
- **The weak "Bring into resume" instruction is removed** for weak or inferred evidence.
- **Existing guardrails are unchanged:**
  - the fabrication checker;
  - unsupported-claim review;
  - length limits;
  - Word layout fidelity;
  - the validation gates.
- **A new test guard:** a stubbed model that tries to add an unsupported term ("Snowflake",
  "CPA", "5 years") must always be rejected or reverted.

### 4. Replace the 85% target with a bounded "until nothing supported is left" loop

The free-form path's refinement loop changes:

- **Targets** are the rows from step 3 that are supported but not yet shown in the resume.
- **It stops when** no targets are left, a round changes nothing that passes the fabrication
  check, or 3 rounds have run (down from 5).
- **The keyword-overlap number** is still computed and stored, but it never drives a decision.

The Word path keeps its single pass plus its one bounded second pass, but that second pass uses
the same targets.

### 5. A stronger readability check (local, honest)

After the final PDF is built, Job Copilot already extracts its text. The new checks compare that
text with what the resume is supposed to say:

| Check | Severity |
|---|---|
| No text at all (existing `TEXT_NOT_EXTRACTABLE`) | **Fail**, unchanged |
| Contact email, or the name, missing from the extracted text | Fail |
| A work-history bullet or role (title, employer, dates) missing | Fail if a whole bullet is missing; warning if partly garbled |
| Section headings or roles out of order compared with the document | Warning ("may be read out of order, for example in two columns") |
| Replacement characters (�) or unmapped symbols | Warning |
| Non-standard section headings (for example "My Journey" instead of "Experience") | Warning, with a suggestion |

Matching tolerates normal extraction noise: ligatures, hyphenated line breaks and spacing. A
check only fails when content is clearly absent.

The panel is titled "Readability check (done on this computer)". It says plainly that this isn't
certification by any employer's ATS, and that employers' systems differ.

### 6. Compatibility

- **Saved reviews:** files from before this change still load. Old files without a review get
  one computed when opened, and the panel says "computed now from your current Career Profile".
  Enum values and existing dataclass fields aren't renamed or removed. New fields have defaults,
  as `review_store.decode` requires.
- **API:** `/v2/tailor` keeps its `alignment` field and gains `requirement_review`, `readability`
  and `ats_explainer`. `/v2/jobs/{id}` keeps `keywords` but uses the new labels and gains
  `requirement_summary`. The legacy `/tailor` API (`apps/api/app/tailor`) and its
  `original_match_score` don't change.
- **Stored applications:** `resume_match_score` is still written as before. It was never shown
  or used to decide anything.
- **Apply capabilities** and the `final_submission` gate are untouched.

## Affected files

| Area | Files |
|---|---|
| Engine (new) | `analyzers/requirement_review.py`, `ui/ats_explainer.py` |
| Engine (changed) | `analyzers/ats_keywords.py` (facts only, labels), `analyzers/gap_analyzer.py` (display labels; skill-list mentions no longer "Direct verified"), `tailorer/resume_tailorer.py` (`format_gaps` targets), `tailorer/optimizer.py` (loop), `docx_export/pipeline.py` (second-pass targets), `pdf/validator.py` plus `artifacts/validation*` (readability checks), `tailoring_service.py` (build the review, store it in the run state), `ui/tailoring_view.py` |
| API | `apps/api/app/workspace/jobs_router.py`, `tailor_router.py` |
| Next.js | `apps/web/src/app/jobs/job-detail.tsx`, `app/tailor/page.tsx`, `app/tailor/review.tsx` (or a new `requirement-review.tsx`), `lib/types.ts` |
| Streamlit | `pages/2_Job_Search.py`, `pages/5_Tailor.py` |
| Docs | this spec, `decisions/032`, `CLAUDE.md`, the handoff |

**No new dependencies.** This reuses pypdf, PyMuPDF and reportlab, which are already installed.
**No large refactor:** `GapAnalyzer` stays, and the review is a new layer built from the same
inputs.

## Implementation order (each step verified and committed separately)

1. Labels and explainer (section 1), with tests.
2. The `requirement_review` engine and its acceptance fixtures (section 2, engine only).
3. Prompt targets and the optimizer loop (sections 3–4), with stubbed-model guard tests.
4. Readability checks (section 5).
5. API and both UIs (sections 1–2 and 5), with browser tests.
6. A supervised end-to-end run, plus the decision record and docs.

## Test plan

All resumes and postings are anonymized and realistic, and they are committed as fixtures under
`product/tests/fixtures/ats/`.

**Acceptance cases (engine):**

- **Term present but unsupported:** "Snowflake" appears only in Skills, and the posting requires
  it. Expect "Mentioned only", never a target, never added to bullets.
- **Equivalent wording, genuinely supported:** the posting asks for "project management"; a
  bullet says "Coordinated a 6-month launch across 4 teams, on schedule". Expect "Transferable
  evidence" citing that bullet.
- **Ambiguous acronym:** the posting says "PM experience" (product); the resume says "Project
  Management (PM)". Expect "Check the meaning", not direct.
- **Preferred skill missing:** "Tableau preferred", not found. Expect "No evidence" under
  Preferred, not a hard gate, listed as a gap, not targeted.
- **Required credential absent:** "Active CPA license required", not found. Expect "No evidence"
  marked as a hard gate and shown first.
- **Unconfirmed only:** the evidence exists only in unconfirmed imported facts. Expect
  "Unconfirmed", not targeted, with a prompt to confirm in Career Profile.

**Never add unsupported claims:**

- A stubbed model returns rewrites containing each unsupported term. The final resume text never
  contains them, and they are reported as rejected.
- This runs on both the Word and free-form paths.

**Optimizer:**

- It stops with no targets left, stops after a no-change round, and never exceeds 3 rounds.
- No code path reads 0.85.

**Readability, on real generated PDFs (reportlab, plus a real Word to PDF conversion in CI
where available):**

- A clean PDF passes.
- A PDF with a bullet drawn as an image fails, naming the missing bullet.
- A two-column PDF whose extracted text interleaves gets the order warning.
- A blank or image-only PDF still fails with `TEXT_NOT_EXTRACTABLE`.

**Legacy:**

- A saved review file in today's format (committed as a fixture) still loads.
- The Tailor view builds from it with a "computed now" review.
- `/v2/tailor` still returns `alignment`.

**API and web:**

- **API tests:** the new fields and labels, and the old fields still present.
- **Playwright:** in the journey test, Jobs shows "In your Career Profile" and the explainer;
  Tailor shows the requirement review and readability panel; no "on your resume" wording
  remains.
- **Accessibility:** axe on the new panels, in light and dark.

**Supervised end-to-end reproduction (required, not just unit tests):**

- Set-up: one real tailoring run through the full pipeline (Word path) with an anonymized resume
  and a posting built to contain all six cases.
- Observer: the builder watches and reviews the result.
- Record: kept in `discovery/experiments/2026-10-ats-requirement-review.md`, including the
  posting, before and after bullets, the review table and the readability result.
- Pass condition: no unsupported term appears, and every supported requirement is either shown
  or explained.

**Suites:** product, API and web tests (lint, types, Playwright) all pass before each commit.

## Out of scope

- Any employer-side ATS simulation, score prediction, ranking estimate or "pass rate".
- Semantic or embedding matching, or a new skills taxonomy. The existing competency map and
  term matcher are reused.
- Recency or years-of-experience arithmetic.
- Changes to Candidate Fit, job search or Apply capabilities.
- A hidden-keyword, white-text or keyword-density feature (it will never exist).
- Changing a fact's confirmation granularity (it stays per section).

## Definition of done

- [x] No screen in either app says a profile term is "on your resume", or presents a percentage
      as an ATS score or threshold (Playwright checks there's no "on your resume" and no
      "Resume alignment").
- [x] Jobs and Tailor show the requirement review with linked evidence; all six acceptance cases
      pass (`test_requirement_review.py`).
- [x] The optimizer has no 85% target; unsupported claims are never added (stubbed-model guards
      on both paths, `test_unsupported_claim_guards.py`, `test_optimizer.py`).
- [x] The readability check catches missing and out-of-order content on real PDFs; the
      `TEXT_NOT_EXTRACTABLE` failure is unchanged (`test_readability.py`).
- [x] Legacy saved reviews load (a real pre-change file, `test_legacy_review_loads.py`); the
      `/v2` and legacy API fields are still present.
- [x] Supervised end-to-end run recorded. The builder's review of that record is still to come.
- [x] Product, API and web suites green (see the commit for counts; CI on push).
- [ ] Usage signal (requirement-review rows expanded, suggestions accepted). Not built: the app
      has no analytics, and adding tracking is a separate decision for the builder.

## Research appendix: which claims we rely on

Sources reviewed: four learning guides supplied by the builder (October 2026), checked against
vendor documentation on 2026-10-05.

**Well supported (used in this spec):**

- **There is no universal ATS score or passing threshold.**
  - Vendors describe their own, configurable matching features.
  - Greenhouse Talent Matching sorts candidates into categories against criteria each hiring
    team sets ([Greenhouse Talent Matching FAQ](https://support.greenhouse.io/hc/en-us/articles/41131886674075-Talent-Matching-FAQ)).
  - Workday describes HiredScore grading as "a means of prioritizing candidates based on
    comparison of job requirements and candidates resumes"
    ([Workday reference](https://doc.workday.com/admin-guide/en-us/workday-feature-descriptions/workday-hiredscore/hiredscore-ai-for-recruiting.html)).
- **Vendor AI matching assists people; it doesn't decide.** Greenhouse states Talent Matching
  "does not auto-reject or auto-advance any candidate"
  ([FAQ](https://support.greenhouse.io/hc/en-us/articles/41131886674075-Talent-Matching-FAQ);
  [Real Talent](https://www.greenhouse.com/real-talent-candidate-matching)).
- **Parsing problems are real, and can push a resume out of automated matching.**
  - Greenhouse labels candidates "Needs manual review" when there's a problem processing their
    resume (same FAQ).
  - Textkernel needs an optional OCR add-on for image-only PDFs
    ([Textkernel file formats](https://developer.textkernel.com/TKPlatform/master/file-formats/);
    [OCR add-on](https://www.textkernel.com/resume-parsing-ocr-addon/)).
  - This supports the text-extraction and content checks.
- **Related terms can map to one skill.** Greenhouse: "multiple terms can map to the same
  calibrated skill" (FAQ). This supports counting genuinely equivalent wording as transferable
  evidence, and stating important terms clearly when true.
- **Uncontested in all four guides, and consistent with recruiter practice:**
  - required and preferred qualifications are weighed differently;
  - context and outcomes persuade human reviewers more than skill lists;
  - hidden text and keyword stuffing are deceptive.

**Examples or general advice, not rules:**

- Evidence ladders and the four keyword tiers.
- Bullet formulas such as "verb + skill + metric".
- "Use both the acronym and the full name".

These are useful teaching models; Job Copilot can suggest them but never treats them as
requirements.

**Vendor-specific, varies, or only from third parties (not relied on):**

- Workday "A–D grades" by basic and preferred qualifications appear only in third-party blogs.
  Workday's own reference and datasheet don't describe them.
- The claim that recruiters mostly ignore match scores.
- The claim that automated rejection is mostly knockout questions.
- Which platform parses columns or tables well.
- Whether PDF or Word parses better.

**Unsupported numbers (not used anywhere in the product):**

- "70–95%" and "85–90%" parsing accuracy.
- "~15% of resumes use columns" (a vendor blog figure).
- "87% match accuracy".
- Vendor pricing and profile counts.
- The published "Expertini" formula weights.
- "Dates without months default to 0 years".
