# Spec 016: Evidence must support the particular claim

**Status:** Approved by the builder on 2026-10-11; detailed implementation plan awaiting review.
**Plan:** `docs/superpowers/plans/2026-10-11-spec-016-truthful-evidence.md`.
**Date:** 2026-10-11
**Baseline:** main at `d577aae`; specs 010–012 and decision 037 remain in force.
**Evidence:** `discovery/experiments/2026-10-11-evidence-upload-and-worker-probes.md`.

## Goal

Help a job seeker make supported experience clearer without assigning a tool to the wrong
role/project or treating a general capability as proof of a named platform. Preserve useful
rewrites, honest evidence labels, the person's source facts and explicit review decisions.

The builder asked for this spec after observing that a Tableau skill does not establish
Tableau use on a particular SQL project, and general analytics does not establish Qualtrics.

## Reproduced problems

1. A synthetic profile has SQL reporting at Example A and Tableau inventory work at Example B.
   The posting names SQL and Tableau. Adding `using Tableau` to the Example A SQL bullet
   produces no issues from either `introduced_unsupported` or `validate_manual_text`.
   Profile-wide evidence has been mistaken for evidence of this relationship.
2. `Experience with analytics platforms such as Qualtrics.` is labeled `direct`, citing
   `Built SQL dashboards and analytics reports.`. Only `Analytics` is recognized in the row.
   Qualtrics is absent from the current vocabulary; generic recognition masks that absence.

These are current deterministic reproductions, not invented model responses. The earlier
real-model browser observations are in the spec-015 release ledger.

## Recommended design

### A. Keep general qualification evidence separate from claim-local evidence

- A requirement can have evidence somewhere in the Career Profile without supporting its
  addition to every bullet. A Tableau passage at Example B may support the candidate's
  Tableau qualification; it must not authorize Tableau in Example A's SQL project.
- Introduce one shared, deterministic claim-local guard used by the Word bullet tailorer,
  free-form change validation, manual editing and final artifact validation/regeneration.
  A prompt instruction alone is insufficient.
- Bind an experience rewrite to its exact original passage and role/project context already
  identified by the pipeline. Use explicit source references, not the first equal string in
  the profile. Duplicate text across roles must not select the wrong source.
- Introducing a named tool into an experience claim requires confirmed evidence tying that
  tool to this particular activity. A skill list, another role, or another project in the
  same role is not enough. Without an unambiguous link, keep the original or block the edit
  with a plain explanation. The person can correct and confirm the relevant source bullet
  in Career Profile, then tailor again; no new fact-authoring interface is required here.
- Preserve an already-present tool in its original truthful passage. Do not require a term
  to be newly added to the posting vocabulary before protecting its attribution: a tool not
  requested by this job can still be wrongly added to a project.
- Skills lists may retain existing listed tools and reorder them. Summary rewrites may not
  turn a skill-list mention into a project/employer-use claim. Apply the appropriate section
  context rather than treating a comma-separated experience sentence as a safe skills list.
- If source context is missing or ambiguous, a newly introduced relationship is not verified.
  Existing calling signatures can gain optional context; absent context must not be a bypass
  for a newly introduced tool-use claim. Original unchanged content remains compatible.

### B. Recognize the named requirement before judging its evidence

- Add Qualtrics to the existing platform vocabulary and cover its explicit name separately
  from generic analytics/survey capabilities. Reuse the existing term matcher and statuses.
- Preserve explicit named platforms in supported syntactic patterns, including `experience
  with X` and `platforms such as X`. Do not import arbitrary fallback keywords as tool names.
  When an explicit product name cannot be classified safely, show `Check yourself` rather
  than claiming that a generic match fully establishes the requirement.
- A generic analytics passage never supports a specific platform. No contextual Qualtrics
  passage means `No evidence`; Qualtrics only in a list means `Mentioned only`; an unconfirmed
  Qualtrics passage means `Unconfirmed`. All remain outside supported rewrite targets.
- Mixed requirements retain per-term statuses and `Partly supported` where appropriate.
  `SQL and Qualtrics` must not become wholly direct evidence when only SQL is supported.
- Handle conjunctions and alternatives explicitly. For `Qualtrics or SurveyMonkey`, show
  which permitted alternative is supported; do not claim experience in both. If the grammar
  cannot be distinguished safely, use the existing check-yourself state.
- `Such as` and `e.g.` can introduce examples rather than mandatory tools. Do not invent a
  hard gate for each example. Show the generic capability and the unevidenced example
  separately (partly supported or check-yourself when needed); never label the named tool
  direct or insert its name into a resume on the strength of generic evidence.
- Required/preferred labels, quoted evidence and source paths remain visible in both apps.
  No score, employer screening prediction or new Candidate Fit decision is introduced.

### C. Explain rejection and enforce it beyond the first model call

- Suggested copy: `Tableau appears elsewhere in your profile, but we can't verify that you
  used it in this project. Keep the original or update this project's facts in Career Profile.`
- AI Word edits revert to the source bullet and retain the rejected text/reason for review.
  Free-form proposals remain reviewable but cannot yield a usable artifact while an unsupported
  claim is included. Manual edits fail before rebuilding; choosing Accept must not override
  the truthfulness gate. Final rebuilt artifacts get the same relationship check.
- Apply/download/helper gates continue to withhold failed artifacts. Preserve the current
  review disposition model; do not remove the ability to reject or revise a proposal.

## Alternatives considered

1. **Scoped deterministic guards and explicit term evidence (recommended):** addresses both
   reproduced failures, preserves legitimate source claims and shares rules across both paths.
2. **Prompt-only correction:** smaller but rejected because current prompts already require
   grounded claims and both AI and manual edits can bypass a textual instruction.
3. **A new semantic matching/model subsystem:** deferred; adds cost and uncertainty without
   resolving source attribution by itself. No new dependency or paid provider here.

## Expected integration points

- `analyzers/requirement_review.py`, `analyzers/ats_keywords.py` and a small shared claim guard.
- `tailorer/docx_bullet_tailorer.py`, `tailorer/optimizer.py`, `artifacts/changes.py`,
  `artifacts/regeneration.py`, `tailoring_service.py` and final content validation as needed.
- Additive evidence/rejection context in existing API/shared views only where necessary.
- Product, API, Streamlit AppTest and browser acceptance tests with synthetic fixtures.

Existing work-bullet matching, including decision 018's global greedy matcher, is not changed.
New saved fields have defaults and review format 2 still loads. Old files without claim-local
metadata must not be retroactively assigned invented provenance; new edits/rebuilds must
validate added relationships or explain unresolved context instead of guessing.

## Acceptance cases

| Case | Expected result |
|---|---|
| Tableau only in Skills; source project uses SQL | No new Tableau project-use claim |
| Tableau in another employer's bullet | Candidate evidence stays valid there; wrong-project rewrite blocked |
| Tableau in a different project under the same role | No relationship inferred from shared employer alone |
| Original project explicitly uses SQL and Tableau | Truthful rephrasing accepted; original facts retained |
| Identical source wording under two employers | Source association remains distinct or fails visibly |
| Posting does not request Tableau, but model/manual edit adds it | Same claim-local protection applies |
| Generic analytics versus Qualtrics requirement | Not direct; Qualtrics gap remains visible |
| Qualtrics only listed / unconfirmed / confirmed in contextual use | Mention / unconfirmed / direct respectively |
| SQL plus unsupported Qualtrics | Partly supported, supported targets do not include Qualtrics |
| Qualtrics or another evidenced platform | Qualified alternative, not evidence of both tools |
| Analytics platforms such as Qualtrics | Explain generic evidence versus example; no invented tool experience or hard gate |
| Unknown explicit platform with only generic analytics evidence | Check yourself, not fully supported |
| AI, refinement, manual edit, Accept and rebuild | Same unsupported relationship cannot escape final gate |
| Existing truthful lists and unchanged/legacy reviews | Load without invented provenance or needless text changes |

## Verification and boundaries

- Before each fix, reproduce a failing test through the corresponding public pipeline, not
  just the new helper. Then verify Word and free-form artifacts, manual rebuilds and API gates.
- Run full product/API suites, lint/types and Playwright; retain exact counts and exit codes.
- After approval/implementation, run synthetic browser scenarios with the existing real
  model when available. Label generated versus deliberately seeded edits. No real resume,
  submission, paid purchase or new account; no assertion that these tests are human research.
- Specs 017 and 018 cover upload source disclosure and batch publication separately.

## Definition of done

- [ ] Every acceptance case passes on both relevant artifact paths and API/manual rebuilds.
- [ ] Wrong-role/project additions are blocked; supported original claims still work.
- [ ] Named-platform requirements no longer inherit support from generic analytics alone.
- [ ] Both frontends explain evidence/rejection consistently; saved review compatibility holds.
- [ ] Full suites and a labeled browser exercise pass; actual evidence and limits are recorded.
- [ ] Decision/handoffs updated after implementation; push only on explicit authorization.

**Review gate:** approve this written spec before the detailed implementation plan and code.
